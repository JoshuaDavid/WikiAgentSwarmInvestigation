#!/usr/bin/env python3
"""Local web UI for search-only Luna spider runs."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[2]
SPIDER_ROOT = ROOT / "oai-index-scan" / "tmp" / "spider"
SUBMISSION_ROOT = ROOT / "oai-index-scan" / "tmp" / "search-ui"
WORKER_POOL = ROOT / "oai-index-scan" / "spider" / "worker_pool.py"
RUN_RE = re.compile(r"^web_[A-Za-z0-9_-]+$")
MAX_REQUEST_BYTES = 1_000_000
MAX_TERMS = 10_000
RESULT_SEPARATOR_RE = re.compile(r"\n?-{40,}\n?")
RESULT_HEADING_RE = re.compile(r"^(.+?) \((https?://[^\s]+)\)\s*$")
METADATA_RE = re.compile(r"\b(Published|Crawled|Cached):\s*([^;\n]+)", re.IGNORECASE)
CHILD_LINK_RE = re.compile(r"cite(\d+)†([^†]*)†([^]+)")
BRACKET_CHILD_LINK_RE = re.compile(
    r"【(\d+)†([^†】\n]*?)(?:†([^】\n]+))?】"
)
TRUNCATED_BRACKET_LINK_RE = re.compile(r"【(\d+)†([^\n】]*)$")
ABSOLUTE_URL_RE = re.compile(r"https?://[^\s<>\[\]{}\"'`]+", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def response_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    response = payload.get("tool_response")
    if isinstance(response, str):
        return response
    if not isinstance(response, list):
        return ""
    return "\n\n".join(
        item["text"] for item in response
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    )


def parse_search_results(text: str) -> list[dict[str, object]]:
    """Extract display fields while retaining each result's complete text."""
    parsed = []
    for section in RESULT_SEPARATOR_RE.split(text):
        section = section.strip()
        if not section:
            continue
        lines = section.splitlines()
        heading = RESULT_HEADING_RE.match(lines[0].strip())
        metadata = {match.group(1).lower(): match.group(2).strip()
                    for match in METADATA_RE.finditer(section)}
        citation_line = next((line for line in lines[1:] if "cite" in line), "")
        ref_match = re.search(r"turn\w+", citation_line)
        child_links = []
        seen_links = set()
        link_matches = list(CHILD_LINK_RE.finditer(section))
        link_matches.extend(BRACKET_CHILD_LINK_RE.finditer(section))
        link_matches.extend(TRUNCATED_BRACKET_LINK_RE.finditer(section))
        for match in link_matches:
            hostname = match.group(3) if match.lastindex and match.lastindex >= 3 else None
            link_key = (int(match.group(1)), match.group(2), hostname)
            if link_key in seen_links:
                continue
            seen_links.add(link_key)
            child_links.append({
                "link_id": link_key[0],
                "anchor_text": link_key[1].strip() or None,
                "hostname_hint": link_key[2].strip() or None if link_key[2] else None,
                "url": None,
            })
        primary_url = heading.group(2).strip() if heading else None
        seen_urls = {primary_url.rstrip("/ ").lower()} if primary_url else set()
        for match in ABSOLUTE_URL_RE.finditer(section):
            url = match.group(0).rstrip(".,;:!?†】)")
            normalized = url.rstrip("/ ").lower()
            if not url or normalized in seen_urls:
                continue
            seen_urls.add(normalized)
            child_links.append({
                "link_id": None,
                "anchor_text": None,
                "hostname_hint": urlparse(url).hostname,
                "url": url,
            })
        parsed.append({
            "title": heading.group(1).strip() if heading else None,
            "url": heading.group(2).strip() if heading else None,
            "published_at": metadata.get("published"),
            "cached_at": metadata.get("cached") or metadata.get("crawled"),
            "cache_field": ("Cached" if metadata.get("cached") else
                            "Crawled" if metadata.get("crawled") else None),
            "ref_id": ref_match.group(0) if ref_match else None,
            "child_link_count": len(child_links),
            "child_links": child_links,
            "text": section,
        })
    return parsed


class RunManager:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.processes: dict[str, tuple[subprocess.Popen[bytes], object]] = {}
        SUBMISSION_ROOT.mkdir(parents=True, exist_ok=True)

    def start(self, terms: list[str], domains: list[str], recency: int | None) -> str:
        run_id = f"web_{utc_now()}_{uuid.uuid4().hex[:8]}"
        seeds_path = SUBMISSION_ROOT / f"{run_id}.seeds.txt"
        log_path = SUBMISSION_ROOT / f"{run_id}.log"
        seeds_path.write_text("\n".join(terms) + "\n", encoding="utf-8")
        worker_count = min(len(terms), 10)
        command = [
            sys.executable, str(WORKER_POOL),
            "--run", run_id,
            "--seeds-file", str(seeds_path),
            "--max-pages", "1",
            "--workers", str(worker_count),
            "--max-calls-per-worker", "50",
            "--internal-error-call-limit", "60",
            "--max-terms-per-webrun-call", "1",
            "--max-operations-per-webrun-call", "1",
            "--no-direct-url-opens",
            "--search-only",
        ]
        for domain in domains:
            command.extend(["--search-domain", domain])
        if recency is not None:
            command.extend(["--search-recency", str(recency)])
        log_handle = log_path.open("wb")
        try:
            process = subprocess.Popen(command, cwd=ROOT, stdout=log_handle,
                                       stderr=subprocess.STDOUT)
        except Exception:
            log_handle.close()
            raise
        with self.lock:
            self.processes[run_id] = (process, log_handle)
        return run_id

    def process_state(self, run_id: str) -> tuple[str, int | None]:
        with self.lock:
            entry = self.processes.get(run_id)
            if entry is None:
                return "unknown", None
            process, log_handle = entry
            code = process.poll()
            if code is None:
                return "running", None
            if not log_handle.closed:
                log_handle.close()
            return ("complete" if code == 0 else "failed"), code

    def stop(self, run_id: str) -> bool:
        with self.lock:
            entry = self.processes.get(run_id)
            if entry is None or entry[0].poll() is not None:
                return False
            entry[0].terminate()
            return True


MANAGER = RunManager()


def valid_run(run_id: str) -> Path:
    if not RUN_RE.fullmatch(run_id):
        raise ValueError("invalid run id")
    return SPIDER_ROOT / run_id


def list_runs() -> list[dict[str, object]]:
    runs = []
    if not SPIDER_ROOT.exists():
        return runs
    for manifest_path in SPIDER_ROOT.glob("web_*/manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not manifest.get("search_only"):
            continue
        run_id = manifest_path.parent.name
        process_state, returncode = MANAGER.process_state(run_id)
        runs.append({"run_id": run_id, "created_at": manifest.get("created_at"),
                     "terms": len(manifest.get("seed_terms", [])),
                     "process_state": process_state, "returncode": returncode})
    return sorted(runs, key=lambda item: str(item["created_at"]), reverse=True)


def run_detail(run_id: str) -> dict[str, object]:
    path = valid_run(run_id)
    manifest_path = path / "manifest.json"
    db_path = path / "state.sqlite3"
    process_state, returncode = MANAGER.process_state(run_id)
    detail: dict[str, object] = {
        "run_id": run_id, "process_state": process_state,
        "returncode": returncode, "results": [],
    }
    if manifest_path.exists():
        detail["manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not db_path.exists():
        return detail
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2)
    db.row_factory = sqlite3.Row
    try:
        counts = {row[0]: row[1] for row in db.execute(
            "SELECT state,COUNT(*) FROM operations GROUP BY state"
        )}
        detail["counts"] = counts
        abort = db.execute("SELECT value FROM meta WHERE key='abort_reason'").fetchone()
        detail["abort_reason"] = abort[0] if abort else None
        results = []
        for row in db.execute(
            "SELECT operation_id,state,tool_input_json,committed_at,raw_path,"
            "validation_json,tool_use_id FROM operations WHERE kind='search' ORDER BY sequence"
        ):
            tool_input = json.loads(row["tool_input_json"])
            queries = [item.get("q") for item in tool_input.get("search_query", [])]
            text = ""
            transcript_path = None
            if row["raw_path"]:
                raw_path = Path(row["raw_path"])
                if not raw_path.is_absolute():
                    raw_path = path / raw_path
                try:
                    raw = json.loads(raw_path.read_text(encoding="utf-8"))
                    text = response_text(raw)
                    transcript_path = raw.get("transcript_path")
                except (OSError, ValueError):
                    text = "Raw response could not be read."
            results.append({
                "operation_id": row["operation_id"], "state": row["state"],
                "queries": queries, "committed_at": row["committed_at"],
                "tool_use_id": row["tool_use_id"], "text": text,
                "items": parse_search_results(text),
                "transcript_path": transcript_path,
                "validation": json.loads(row["validation_json"] or "null"),
            })
        detail["results"] = results
    finally:
        db.close()
    return detail


INDEX = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Luna Search Console</title>
<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#151c30;--line:#293451;--ink:#e8edf7;--muted:#9ba8c0;--accent:#80cbc4;--bad:#ff8a80}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:32px 20px}h1{margin:0 0 4px;font-size:28px}.lede{color:var(--muted);margin:0 0 24px}.panel,.result{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;margin:14px 0}.hit{background:#0d1425;border-left:3px solid var(--accent);border-radius:6px;padding:12px;margin:12px 0}.hit a{color:var(--accent);font-size:17px;font-weight:650;text-decoration:none}.hit a:hover{text-decoration:underline}.url{color:var(--muted);overflow-wrap:anywhere;font-size:13px}.fields{display:flex;flex-wrap:wrap;gap:8px 18px;margin-top:6px}.fields span{font-size:13px}.children{margin:7px 0 0;padding-left:24px}.children li{margin:4px 0;overflow-wrap:anywhere}textarea{width:100%;min-height:180px;resize:vertical;background:#090e1b;color:var(--ink);border:1px solid var(--line);border-radius:7px;padding:12px;font:14px/1.45 ui-monospace,monospace}button{background:var(--accent);color:#071310;border:0;border-radius:7px;padding:9px 15px;font-weight:700;cursor:pointer}button.secondary{background:#34415f;color:var(--ink)}button:disabled{opacity:.5}.row{display:flex;align-items:center;gap:10px;margin-top:10px}.status{color:var(--muted)}.error{color:var(--bad)}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#090e1b;border-radius:7px;padding:12px;max-height:520px;overflow:auto}.meta{color:var(--muted);font-size:13px}.runs button{margin:3px}details{margin-top:10px}summary{cursor:pointer;color:var(--muted)}code{color:var(--accent)}</style></head>
<body><main><h1>Luna Search Console</h1><p class="lede">One search term per line. Each term is issued in its own web.run call, with up to 10 parallel Luna workers; result links are not opened.</p>
<section class="panel"><label for="terms"><strong>Search terms</strong> (one per line)</label><textarea id="terms" placeholder="md.succ.ai&#10;urltomarkdown&#10;Data Africa"></textarea><div class="row"><label>Domains <input id="domains" placeholder="example.org, example.com"></label><label>Recency (days) <input id="recency" type="number" min="0" step="1" placeholder="any"></label></div><div class="row"><button id="start">Search</button><span id="message" class="status"></span></div></section>
<section class="panel"><strong>Runs</strong><div id="runs" class="runs status">Loading…</div></section>
<section id="current"></section></main>
<script>
const $=s=>document.querySelector(s);let selected=null,timer=null;
async function api(url,options){const r=await fetch(url,options);const data=await r.json();if(!r.ok)throw new Error(data.error||r.statusText);return data}
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n}
async function refreshRuns(){try{const data=await api('/api/runs');const box=$('#runs');box.textContent='';if(!data.runs.length)box.textContent='No runs yet.';for(const run of data.runs){const b=el('button',`${run.run_id} · ${run.terms} terms · ${run.process_state}`,'secondary');b.onclick=()=>selectRun(run.run_id);box.append(b)}}catch(e){$('#runs').textContent=e.message}}
async function selectRun(id){selected=id;if(timer)clearTimeout(timer);await refreshDetail()}
function addHit(card,item){const hit=el('div',undefined,'hit');if(item.url){const a=el('a',item.title||item.url);a.href=item.url;a.target='_blank';a.rel='noopener noreferrer';hit.append(a);hit.append(el('div',item.url,'url'))}else hit.append(el('strong',item.title||'Unstructured result'));const fields=el('div',undefined,'fields');if(item.cached_at)fields.append(el('span',`${item.cache_field||'Cached'}: ${item.cached_at}`));if(item.published_at)fields.append(el('span',`Published: ${item.published_at}`));if(item.ref_id)fields.append(el('span',`Ref: ${item.ref_id}`));fields.append(el('span',`Child links: ${item.child_link_count||0}`));if(fields.childNodes.length)hit.append(fields);if(item.child_links&&item.child_links.length){const children=el('details');children.append(el('summary',`Show ${item.child_links.length} child links`));const list=el('ol',undefined,'children');for(const link of item.child_links){const li=el('li');if(link.url){const a=el('a',link.url);a.href=link.url;a.target='_blank';a.rel='noopener noreferrer';li.append(a)}else li.textContent=`[${link.link_id}] ${link.anchor_text||'(no anchor text)'}${link.hostname_hint?' — '+link.hostname_hint:''}`;list.append(li)}children.append(list);hit.append(children)}const details=el('details');details.append(el('summary','Raw result'));details.append(el('pre',item.text));hit.append(details);card.append(hit)}
async function refreshDetail(){if(!selected)return;try{const d=await api('/api/runs/'+encodeURIComponent(selected));const root=$('#current');root.textContent='';const head=el('section',undefined,'panel');head.append(el('strong',d.run_id));head.append(el('div',`Process: ${d.process_state}; operations: ${JSON.stringify(d.counts||{})}`,'meta'));if(d.abort_reason)head.append(el('div','Aborted: '+d.abort_reason,'error'));if(d.process_state==='running'){const stop=el('button','Stop','secondary');stop.onclick=async()=>{await api('/api/runs/'+encodeURIComponent(selected)+'/stop',{method:'POST'});refreshDetail()};head.append(stop)}root.append(head);for(const result of d.results){const card=el('article',undefined,'result');card.append(el('strong',(result.queries||[]).join(', ')||result.operation_id));card.append(el('div',`${result.state}${result.committed_at?' · '+result.committed_at:''}${result.transcript_path?' · transcript: '+result.transcript_path:''}`,'meta'));for(const item of result.items||[])addHit(card,item);if(result.text&&!(result.items||[]).length){const details=el('details');details.open=true;details.append(el('summary','Raw response'));details.append(el('pre',result.text));card.append(details)}root.append(card)}if(d.process_state==='running'||Object.keys(d.counts||{}).some(k=>['ready','leased','executing'].includes(k)&&(d.counts[k]>0)))timer=setTimeout(refreshDetail,1000);else timer=setTimeout(refreshRuns,3000)}catch(e){$('#current').textContent=e.message}}
$('#start').onclick=async()=>{const button=$('#start'),message=$('#message');button.disabled=true;message.textContent='Starting…';try{const terms=$('#terms').value,domains=$('#domains').value,recency=$('#recency').value;const d=await api('/api/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({terms,domains,recency:recency===''?null:Number(recency)})});message.textContent='Started '+d.run_id;await refreshRuns();selectRun(d.run_id)}catch(e){message.textContent=e.message;message.className='error'}finally{button.disabled=false}};refreshRuns();
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    server_version = "LunaSearchUI/1"

    def send_json(self, status: int, value: object) -> None:
        encoded = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        try:
            if path == "/":
                encoded = INDEX.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
            elif path == "/api/runs":
                self.send_json(200, {"runs": list_runs()})
            elif path.startswith("/api/runs/"):
                self.send_json(200, run_detail(path.removeprefix("/api/runs/")))
            else:
                self.send_json(404, {"error": "not found"})
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.send_json(400, {"error": str(exc)})

    def do_POST(self) -> None:
        path = unquote(urlparse(self.path).path)
        try:
            if path == "/api/runs":
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > MAX_REQUEST_BYTES:
                    raise ValueError("request body is empty or too large")
                payload = json.loads(self.rfile.read(length))
                value = payload.get("terms", "")
                if not isinstance(value, str):
                    raise ValueError("terms must be a string")
                terms = [line.strip() for line in value.splitlines() if line.strip()]
                if not terms:
                    raise ValueError("enter at least one search term")
                if len(terms) > MAX_TERMS:
                    raise ValueError(f"at most {MAX_TERMS} terms are allowed")
                domain_value = payload.get("domains", "")
                if not isinstance(domain_value, str):
                    raise ValueError("domains must be a string")
                domains = [value.strip() for value in re.split(r"[,\n]", domain_value)
                           if value.strip()]
                if len(domains) > 100:
                    raise ValueError("at most 100 domains are allowed")
                recency = payload.get("recency")
                if recency is not None and (not isinstance(recency, int) or recency < 0):
                    raise ValueError("recency must be a non-negative whole number of days")
                self.send_json(201, {"run_id": MANAGER.start(terms, domains, recency)})
            elif path.startswith("/api/runs/") and path.endswith("/stop"):
                run_id = path.removeprefix("/api/runs/").removesuffix("/stop")
                valid_run(run_id)
                self.send_json(200, {"stopped": MANAGER.stop(run_id)})
            else:
                self.send_json(404, {"error": "not found"})
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(f"{self.address_string()} - {fmt % args}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Luna Search Console: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
