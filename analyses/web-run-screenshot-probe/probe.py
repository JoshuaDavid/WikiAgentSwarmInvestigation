#!/usr/bin/env python3
"""Probe whether web.run's screenshot command runs JavaScript.

Serves an HTML page with several markers over ngrok, and a PDF as a control.
Asks the Responses API's web tool to open and screenshot each URL. Records
which sub-actions the model emits, which markers appear in the tool results
and final answer, and which beacon endpoints the server observes.

Markers on the HTML page:
  STATIC_HTML_<hex>   text in raw HTML; visible to every fetcher
  JS_SYNC_<hex>       injected into DOM by an inline <script> during parse
  JS_ASYNC_<hex>      injected into DOM 500 ms after load via setTimeout
  JS_FETCH_<hex>      fetched from /beacon and inserted into DOM
  CANVAS_<hex>        drawn to a <canvas> only; visible only as pixels
  HIDDEN_HTML_<hex>   in HTML but CSS display:none; opposite polarity
  IMG_ALT_<hex>       alt attribute on an <img>; DOM-readable but non-rendered

Server also logs beacon endpoints hit by the JS. A beacon hit is the strongest
signal that JavaScript ran in a real browser context.

Requires: configured ngrok, Python 3, OPENAI_WEB_SEARCH_API_KEY.
Usage: python3 probe.py --out /tmp/screenshot-probe-$(date +%s)
"""

from __future__ import annotations

import argparse
import datetime
import io
import json
import os
import secrets
import shutil
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs


def utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def say(value) -> None:
    print(json.dumps(value), flush=True)


def make_minimal_pdf(text: str) -> bytes:
    """Build the smallest self-contained PDF with the given text on page 1.

    Written by hand to avoid third-party deps. Uses standard 14 Helvetica.
    """
    def obj(n: int, body: bytes) -> bytes:
        return f"{n} 0 obj\n".encode() + body + b"\nendobj\n"

    content_stream = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode()
    stream_obj = b"<< /Length " + str(len(content_stream)).encode() + b" >>\nstream\n" + content_stream + b"\nendstream"

    parts = []
    parts.append(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    def add(body: bytes) -> None:
        offsets.append(sum(len(p) for p in parts))
        parts.append(body)

    add(obj(1, b"<< /Type /Catalog /Pages 2 0 R >>"))
    add(obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"))
    add(obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>"))
    add(obj(4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))
    add(obj(5, stream_obj))

    xref_start = sum(len(p) for p in parts)
    parts.append(f"xref\n0 6\n0000000000 65535 f \n".encode())
    for o in offsets:
        parts.append(f"{o:010d} 00000 n \n".encode())
    parts.append(b"trailer\n<< /Size 6 /Root 1 0 R >>\n")
    parts.append(f"startxref\n{xref_start}\n%%EOF\n".encode())
    return b"".join(parts)


class Route:
    def __init__(self, kind: str, marker_bundle: dict | None, extension: str = "",
                 owning_page: str | None = None):
        self.kind = kind
        self.markers = marker_bundle or {}
        self.extension = extension
        # For beacon routes: the page whose JS is expected to hit this beacon.
        # The beacon can then return that page's registered js_fetch marker.
        self.owning_page = owning_page


class Server:
    def __init__(self, out: Path):
        self.out = out
        self.routes: dict[str, Route] = {}
        self.events: list[dict] = []
        self.lock = threading.Lock()
        self.public_url: str | None = None
        self.run_id = secrets.token_hex(8)

    def add_html(self, label: str) -> tuple[str, dict]:
        markers = {
            "static_html":  f"STATIC_HTML_{secrets.token_hex(8)}",
            "js_sync":      f"JS_SYNC_{secrets.token_hex(8)}",
            "js_async":     f"JS_ASYNC_{secrets.token_hex(8)}",
            "js_fetch":     f"JS_FETCH_{secrets.token_hex(8)}",
            "canvas":       f"CANVAS_{secrets.token_hex(8)}",
            "hidden_html":  f"HIDDEN_HTML_{secrets.token_hex(8)}",
            "img_alt":      f"IMG_ALT_{secrets.token_hex(8)}",
        }
        path = f"/probe/{self.run_id}/{label}/{secrets.token_hex(8)}"
        self.routes[path] = Route("html", markers)
        return path, markers

    def add_html_pdf_ext(self, label: str) -> tuple[str, dict]:
        # Register the HTML route directly at a .pdf-suffixed path.
        path, markers = self.add_html(label)
        pdf_path = path + ".pdf"
        route = self.routes.pop(path)
        route.extension = ".pdf"
        self.routes[pdf_path] = route
        return pdf_path, markers

    def add_pdf(self, label: str) -> tuple[str, str]:
        marker = f"PDF_TEXT_{secrets.token_hex(8)}"
        path = f"/probe/{self.run_id}/{label}/{secrets.token_hex(8)}.pdf"
        self.routes[path] = Route("pdf", {"pdf_text": marker})
        return path, marker

    def _render_html(self, path: str, markers: dict) -> bytes:
        beacon = f"/beacon{path}"
        html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>screenshot-probe {markers['static_html']}</title>
  <style>
    body {{ font: 24px/1.4 system-ui, sans-serif; padding: 24px; color: #111; }}
    .hidden {{ display: none; }}
    .box {{ border: 2px solid #333; padding: 12px; margin: 12px 0; background: #fafafa; }}
    canvas {{ border: 2px dashed #888; }}
  </style>
</head>
<body>
  <div class="box"><b>STATIC (raw HTML):</b> <span>{markers['static_html']}</span></div>
  <div class="box"><b>HIDDEN (CSS display:none):</b>
    <span class="hidden">{markers['hidden_html']}</span></div>
  <img src="/nonexistent.png" alt="{markers['img_alt']}" width="1" height="1">
  <div class="box"><b>JS_SYNC target:</b> <span id="js-sync">(pending)</span></div>
  <div class="box"><b>JS_ASYNC target:</b> <span id="js-async">(pending)</span></div>
  <div class="box"><b>JS_FETCH target:</b> <span id="js-fetch">(pending)</span></div>
  <div class="box"><b>CANVAS (drawn only):</b><br>
    <canvas id="cv" width="500" height="60"></canvas></div>

  <script>
    // Beacon: strongest signal that JS actually executed in a browser.
    try {{ fetch({json.dumps(beacon)} + "?phase=script-parsed"); }} catch (e) {{}}
    document.getElementById("js-sync").textContent = {json.dumps(markers['js_sync'])};

    // Canvas: text drawn as pixels; not present in DOM text.
    var cv = document.getElementById("cv");
    if (cv && cv.getContext) {{
      var ctx = cv.getContext("2d");
      ctx.font = "28px sans-serif";
      ctx.fillStyle = "#000";
      ctx.fillText({json.dumps(markers['canvas'])}, 10, 40);
    }}

    // Async: only appears after event loop turns.
    setTimeout(function () {{
      document.getElementById("js-async").textContent = {json.dumps(markers['js_async'])};
      try {{ fetch({json.dumps(beacon)} + "?phase=async-timeout"); }} catch (e) {{}}
    }}, 500);

    // Fetch a marker string from the server, then insert it.
    try {{
      fetch({json.dumps(beacon)} + "?phase=fetch-marker&want=marker")
        .then(function (r) {{ return r.text(); }})
        .then(function (t) {{
          document.getElementById("js-fetch").textContent = t;
        }});
    }} catch (e) {{}}
  </script>
</body>
</html>
"""
        return html.encode("utf-8")

    def _handle(self, handler: BaseHTTPRequestHandler) -> None:
        split = urlsplit(handler.path)
        path = split.path
        query = split.query
        params = parse_qs(query, keep_blank_values=True)
        now = utc()

        route = self.routes.get(path)
        if route is None and path.startswith("/beacon/"):
            # Look up the owning page by stripping the /beacon prefix. The
            # page's JS built its beacon path as /beacon + location.pathname,
            # so this reconstructs which page's script called us.
            owning = path[len("/beacon"):]
            owning_route = self.routes.get(owning)
            beacon_route = Route("beacon", None, owning_page=owning
                                 if owning_route and owning_route.kind == "html"
                                 else None)
            self.routes[path] = beacon_route
            route = beacon_route

        if path == "/robots.txt":
            body = b"User-agent: *\nAllow: /\n"
            handler.send_response(200)
            handler.send_header("Content-Type", "text/plain")
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            handler.wfile.write(body)
            self._log(now, handler, path, query, 200, "text/plain", None)
            return

        if route is None:
            body = b"unknown probe path\n"
            handler.send_response(404)
            handler.send_header("Content-Type", "text/plain")
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            handler.wfile.write(body)
            self._log(now, handler, path, query, 404, "text/plain", None)
            return

        if route.kind == "beacon":
            # For the "want=marker" phase, return the js_fetch marker registered
            # for the page whose script called this beacon. That value is
            # otherwise never sent to the client, so seeing it in the model's
            # output proves JavaScript ran and completed the fetch.
            want = params.get("want", [""])[0]
            if want == "marker" and route.owning_page:
                page_route = self.routes.get(route.owning_page)
                marker = (page_route.markers.get("js_fetch")
                          if page_route else None) or "NO_MARKER"
                body = marker.encode()
            else:
                body = b"ok\n"
            handler.send_response(200)
            handler.send_header("Content-Type", "text/plain")
            handler.send_header("Access-Control-Allow-Origin", "*")
            handler.send_header("Cache-Control", "no-store, no-cache, max-age=0")
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            handler.wfile.write(body)
            self._log(now, handler, path, query, 200, "text/plain",
                      response_marker=body.decode("utf-8", errors="replace").strip())
            return

        if route.kind == "html":
            body = self._render_html(path, route.markers)
            handler.send_response(200)
            # Force HTML content type; extension is only a URL hint.
            handler.send_header("Content-Type", "text/html; charset=utf-8")
            handler.send_header("Cache-Control", "no-store, no-cache, max-age=0")
            handler.send_header("Pragma", "no-cache")
            handler.send_header("X-Robots-Tag", "noindex")
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            handler.wfile.write(body)
            self._log(now, handler, path, query, 200, "text/html", None)
            return

        if route.kind == "pdf":
            body = make_minimal_pdf(route.markers["pdf_text"])
            handler.send_response(200)
            handler.send_header("Content-Type", "application/pdf")
            handler.send_header("Cache-Control", "no-store, no-cache, max-age=0")
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            handler.wfile.write(body)
            self._log(now, handler, path, query, 200, "application/pdf", None)
            return

    def _log(self, ts, handler, path, query, status, content_type, response_marker):
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
            "response_marker": response_marker,
            "source_ip": handler.client_address[0] if handler.client_address else None,
        }
        with self.lock:
            self.events.append(event)
            with (self.out / "http-events.jsonl").open("a") as f:
                f.write(json.dumps(event) + "\n")
        say({"http": {k: v for k, v in event.items() if k != "monotonic"}})

    def start(self, tunnel_log_path: Path) -> ThreadingHTTPServer:
        server_ref = {"self": self}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self): server_ref["self"]._handle(self)
            def do_HEAD(self): server_ref["self"]._handle(self)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_address[1]

        tunnel_log = tunnel_log_path.open("w")
        self._tunnel_log = tunnel_log
        self._tunnel = subprocess.Popen(
            ["ngrok", "http", f"http://127.0.0.1:{port}",
             "--log", "stdout", "--log-format", "json", "--log-level", "info"],
            stdout=tunnel_log, stderr=subprocess.STDOUT)
        for _ in range(240):
            if self._tunnel.poll() is not None:
                raise RuntimeError("ngrok exited; inspect ngrok.log")
            for line in tunnel_log_path.read_text().splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                url = str(event.get("url", ""))
                if event.get("msg") == "started tunnel" and url.startswith("https://"):
                    self.public_url = url.rstrip("/")
                    return server
            time.sleep(0.25)
        raise RuntimeError("timed out waiting for ngrok public URL")

    def stop(self, server: ThreadingHTTPServer) -> None:
        if getattr(self, "_tunnel", None) is not None:
            self._tunnel.terminate()
            try:
                self._tunnel.wait(timeout=10)
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
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Authorization": "Bearer " + key,
                     "Content-Type": "application/json"})
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
    record["ended_monotonic"] = time.monotonic()
    record["elapsed_s"] = round(record["ended_monotonic"] - started, 3)
    save(out / (label + ".response.json"), record)
    say({"completed": label,
         "http_status": record.get("http_status"),
         "elapsed_s": record["elapsed_s"],
         "error": record.get("error")})
    return record


def assistant_text(response: dict) -> str:
    parts = []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    parts.append(c.get("text", ""))
    return "\n".join(parts)


def summarize_actions(response: dict) -> list[dict]:
    out = []
    for item in response.get("output", []):
        if item.get("type") == "web_search_call":
            action = item.get("action") or {}
            out.append({
                "action_type": action.get("type"),
                "action_url": action.get("url"),
                "action_pattern": action.get("pattern"),
                "action_query": action.get("query"),
                "result_count": len(item.get("results") or []),
                "status": item.get("status"),
                "id": item.get("id"),
            })
    return out


def snippets_of(response: dict) -> str:
    parts = []
    for item in response.get("output", []):
        if item.get("type") == "web_search_call":
            for r in item.get("results") or []:
                parts.append(r.get("snippet") or "")
                parts.append(r.get("title") or "")
    return "\n".join(parts)


def markers_seen(text: str, all_markers: dict) -> dict:
    return {k: (v in text) for k, v in all_markers.items()}


def beacons_hit(events: list[dict], base_beacon_path: str) -> list[dict]:
    hits = []
    for e in events:
        if e["raw_path"].startswith(base_beacon_path) and e["method"] == "GET":
            hits.append({
                "path": e["path"],
                "query": e["query"],
                "user_agent": e.get("user_agent"),
                "source_ip": e.get("source_ip"),
                "time": e["time"],
            })
    return hits


def run_scenario(name: str, model: str, key: str, out: Path, url: str,
                 prompt: str, all_markers: dict, base_beacon_path: str,
                 events: list[dict], start_monotonic: float) -> dict:
    label = f"{name}-{model}"
    body = {
        "model": model,
        "tools": [{"type": "web_search"}],
        "reasoning": {"effort": "low"},
        "store": True,
        "max_output_tokens": 4000,
        "max_tool_calls": 5,
        "include": ["web_search_call.results", "reasoning.encrypted_content"],
        "instructions": (
            "Execute exactly what the user asks. If you take a screenshot, "
            "describe every visible text element word-for-word in your final answer. "
            "Do not summarise; enumerate. If the tool returns an error, quote it verbatim."
        ),
        "input": prompt,
    }
    record = api_call(out, label, body, key)
    response = record.get("response", {}) or {}
    actions = summarize_actions(response)
    snippets = snippets_of(response)
    text = assistant_text(response)
    combined = snippets + "\n" + text
    hits = [e for e in events
            if e["raw_path"].startswith(base_beacon_path)
            and e["method"] == "GET"
            and e["monotonic"] >= start_monotonic - 0.5]
    return {
        "scenario": name,
        "model": model,
        "prompt": prompt,
        "url": url,
        "http_status": record.get("http_status"),
        "elapsed_s": record["elapsed_s"],
        "actions": actions,
        "markers_in_snippets": markers_seen(snippets, all_markers),
        "markers_in_assistant": markers_seen(text, all_markers),
        "markers_anywhere":    markers_seen(combined, all_markers),
        "assistant_text": text,
        "assistant_snippet_first_400": snippets[:400],
        "beacon_hits": [
            {"path": e["path"], "query": e["query"],
             "user_agent": e["user_agent"], "source_ip": e["source_ip"]}
            for e in hits],
        "beacon_hit_count": len(hits),
    }


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

    server = Server(args.out.resolve())
    try:
        srv = server.start(args.out / "ngrok.log")
        say({"public_url": server.public_url, "out": str(args.out)})

        # Health check: hit the tunnel ourselves to make sure the loop is up.
        html_path, html_markers = server.add_html("html-plain")
        base_beacon_path = f"/beacon{html_path}"
        pdf_path, pdf_marker = server.add_pdf("pdf-control")
        fake_pdf_path, fake_pdf_markers = server.add_html_pdf_ext("html-with-pdf-ext")

        # We hit the URL ourselves once to warm the tunnel and prove JS DOES
        # write a beacon when a real browser (or our own probe) executes JS.
        # This is a header-only tunnel check; our own harness never runs JS.
        req = urllib.request.Request(
            server.public_url + html_path,
            headers={"User-Agent": "screenshot-probe-harness/1.0",
                     "ngrok-skip-browser-warning": "1"})
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()

        html_url = server.public_url + html_path
        pdf_url = server.public_url + pdf_path
        fake_pdf_url = server.public_url + fake_pdf_path

        html_prompts = [
            ("html-open", "Open " + html_url +
             " and quote every marker string you see verbatim (STATIC_HTML, "
             "JS_SYNC, JS_ASYNC, JS_FETCH, CANVAS, HIDDEN_HTML, IMG_ALT, FETCHED_MARKER, "
             "PDF_TEXT). Do not paraphrase; write each marker on its own line. "
             "If a marker is not visible, write 'ABSENT: <name>'."),
            ("html-screenshot", "Take a screenshot of " + html_url +
             " and report every visible text element word-for-word. "
             "List each marker (STATIC_HTML, JS_SYNC, JS_ASYNC, JS_FETCH, CANVAS, "
             "HIDDEN_HTML, IMG_ALT, FETCHED_MARKER) on its own line, or write "
             "'ABSENT: <name>' if not visible."),
            ("html-screenshot-render", "Render " + html_url + " in a browser, "
             "wait for JavaScript to finish, then screenshot it and list every "
             "marker string visible in the screenshot, one per line."),
        ]
        pdf_prompts = [
            ("pdf-open", "Open " + pdf_url + " and quote the exact text on page 0 verbatim."),
            ("pdf-screenshot", "Take a screenshot of page 0 of " + pdf_url +
             " and quote the exact text visible in the screenshot verbatim."),
        ]
        fake_pdf_prompts = [
            ("fakepdf-screenshot", "Take a screenshot of page 0 of " + fake_pdf_url +
             " and quote every marker string visible (STATIC_HTML, JS_SYNC, JS_ASYNC, "
             "JS_FETCH, CANVAS, HIDDEN_HTML, IMG_ALT, FETCHED_MARKER). "
             "If the URL is not actually a PDF, quote the exact tool error."),
        ]

        combined_markers = {**html_markers,
                            **{"pdf_text": pdf_marker},
                            **{"fakepdf_" + k: v for k, v in fake_pdf_markers.items()}}

        summaries = []
        for model in args.models:
            model_dir = args.out / model
            model_dir.mkdir(exist_ok=True)
            for label, prompt in html_prompts:
                start = time.monotonic()
                s = run_scenario(label, model, key, model_dir, html_url, prompt,
                                 all_markers=html_markers,
                                 base_beacon_path=base_beacon_path,
                                 events=server.events,
                                 start_monotonic=start)
                summaries.append(s)
            for label, prompt in pdf_prompts:
                start = time.monotonic()
                s = run_scenario(label, model, key, model_dir, pdf_url, prompt,
                                 all_markers={"pdf_text": pdf_marker},
                                 base_beacon_path="/UNUSED",
                                 events=server.events,
                                 start_monotonic=start)
                summaries.append(s)
            for label, prompt in fake_pdf_prompts:
                start = time.monotonic()
                fake_beacon_path = f"/beacon{fake_pdf_path}"
                s = run_scenario(label, model, key, model_dir, fake_pdf_url, prompt,
                                 all_markers=fake_pdf_markers,
                                 base_beacon_path=fake_beacon_path,
                                 events=server.events,
                                 start_monotonic=start)
                summaries.append(s)

        # Observe late HTTP for another 15s to catch delayed JS beacons.
        say({"waiting_for_late_hits": 15})
        time.sleep(15)

        save(args.out / "summary.json", summaries)
        save(args.out / "server-routes.json", {
            "html_url": html_url,
            "pdf_url": pdf_url,
            "fake_pdf_url": fake_pdf_url,
            "html_markers": html_markers,
            "pdf_marker": pdf_marker,
            "fake_pdf_markers": fake_pdf_markers,
            "beacon_base_path": base_beacon_path,
        })
        say({"done": True, "out": str(args.out)})
    finally:
        try:
            server.stop(srv)  # noqa: F821
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
