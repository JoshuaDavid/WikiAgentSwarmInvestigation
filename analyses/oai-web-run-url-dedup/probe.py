"""Run a probe suite against the OpenAI web.run open API.

A probe consists of:
    - name       : id used for output filenames
    - description: one-liner
    - steps      : list of dicts, each either
        {"kind": "seed",  "path": "/p1", "value": "V1"}       # direct HTTP write to scratchpad
        {"kind": "sleep", "seconds": 30}
        {"kind": "fetch", "label": "L", "url": "https://.../p1", "external": true}

For each fetch we record:
    - request timing
    - full response JSON (raw)
    - which server-side requests landed in the scratchpad's request log during that fetch

Output: one JSON file per probe under outputs/raw/<name>.json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

BASE = "https://oai-scratchpad-cache-versioning-demo.ngrok.io"
DB = Path("/collusionwiki/demo-scratchpad/probes.db")
OUT = Path(__file__).parent / "outputs" / "raw"

def api_key() -> str:
    k = os.environ.get("OPENAI_WEB_SEARCH_API_KEY")
    if not k:
        k = Path("/tmp/swarmchasers.txt").read_text().strip()
    return k


def db_max_id() -> int:
    with sqlite3.connect(str(DB)) as c:
        row = c.execute("SELECT COALESCE(MAX(id), 0) FROM requests").fetchone()
    return row[0]


def db_rows_after(max_id: int) -> list[dict[str, Any]]:
    with sqlite3.connect(str(DB)) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT * FROM requests WHERE id > ? ORDER BY id ASC", (max_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def seed(path: str, value: str) -> None:
    from urllib.parse import quote
    url = f"http://127.0.0.1:35981{path}?set-html={quote(value, safe='')}"
    subprocess.run(["curl", "-sS", url], check=True, stdout=subprocess.DEVNULL)


def oai_fetch(url: str, external: bool = True) -> dict[str, Any]:
    key = api_key()
    payload = {
        "model": "gpt-5.6-luna",
        "tools": [{
            "type": "web_search",
            "search_context_size": "high",
            "external_web_access": external,
        }],
        "tool_choice": "required",
        "include": ["web_search_call.action.sources", "web_search_call.results"],
        "input": (
            "Use the web tool to open this exact URL and return its contents. "
            "Do not substitute another URL or perform a general search. URL: " + url
        ),
    }
    t0 = time.time()
    r = subprocess.run(
        [
            "curl", "-sS", "--fail-with-body",
            "https://api.openai.com/v1/responses",
            "-H", f"Authorization: Bearer {key}",
            "-H", "Content-Type: application/json",
            "--data-binary", json.dumps(payload),
        ],
        capture_output=True,
        text=True,
    )
    elapsed = time.time() - t0
    return {
        "elapsed_s": round(elapsed, 3),
        "returncode": r.returncode,
        "stderr": r.stderr[:500],
        "body": (json.loads(r.stdout) if r.stdout.startswith("{") else {"raw": r.stdout[:2000]}),
    }


def extract_snippet(resp: dict[str, Any]) -> dict[str, Any]:
    """Pull the parts of a response that matter for cache-hit detection."""
    body = resp.get("body", {})
    calls = [o for o in body.get("output", []) if o.get("type") == "web_search_call"]
    msgs = [o for o in body.get("output", []) if o.get("type") == "message"]
    call_info: list[dict[str, Any]] = []
    for c in calls:
        action = c.get("action") or {}
        results = c.get("results") or []
        r0 = results[0] if results else {}
        snippet = r0.get("snippet") or ""
        # `Crawled: today` / `Crawled: 3d ago` etc — the freshness stamp OAI puts in
        m = re.search(r"Crawled:\s*([^;]+);", snippet)
        crawled = m.group(1).strip() if m else None
        call_info.append({
            "action_type": action.get("type"),
            "action_url": action.get("url"),
            "result_url": r0.get("url"),
            "crawled": crawled,
            "snippet_head": snippet[:400],
        })
    msg_text = ""
    for m in msgs:
        for c in (m.get("content") or []):
            if c.get("type") == "output_text":
                msg_text += c.get("text", "")
    return {"calls": call_info, "message_text": msg_text[:1000]}


def run_probe(probe: dict[str, Any]) -> dict[str, Any]:
    name = probe["name"]
    print(f"=== probe: {name} ===", file=sys.stderr)
    steps_out: list[dict[str, Any]] = []
    for step in probe["steps"]:
        kind = step["kind"]
        if kind == "seed":
            print(f"  seed  {step['path']} = {step['value'][:30]!r}", file=sys.stderr)
            seed(step["path"], step["value"])
            steps_out.append({"kind": "seed", **step, "ts": time.time()})
        elif kind == "sleep":
            print(f"  sleep {step['seconds']}s", file=sys.stderr)
            time.sleep(step["seconds"])
            steps_out.append({"kind": "sleep", **step})
        elif kind == "fetch":
            label = step["label"]
            url = step["url"]
            ext = step.get("external", True)
            print(f"  fetch [{label}] {url} ext={ext}", file=sys.stderr)
            before = db_max_id()
            resp = oai_fetch(url, external=ext)
            server_hits = db_rows_after(before)
            snip = extract_snippet(resp)
            print(f"    -> {resp['elapsed_s']}s, server_hits={len(server_hits)}, "
                  f"crawled={[c['crawled'] for c in snip['calls']]}", file=sys.stderr)
            steps_out.append({
                "kind": "fetch",
                "label": label,
                "url": url,
                "external": ext,
                "elapsed_s": resp["elapsed_s"],
                "server_hits": server_hits,
                "extracted": snip,
                "response": resp["body"],
            })
        else:
            raise ValueError(f"unknown step kind: {kind}")
    return {"name": name, "description": probe.get("description", ""), "steps": steps_out}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite", help="path to probe suite JSON")
    parser.add_argument("--only", help="run only probes whose name matches this regex")
    parser.add_argument("--run-id", default=None, help="unique run id substituted into {RID} in urls/paths/values (default: timestamp)")
    parser.add_argument("--tag", default="", help="tag appended to output filenames to disambiguate reruns")
    args = parser.parse_args()

    rid = args.run_id or f"r{int(time.time())}"
    OUT.mkdir(parents=True, exist_ok=True)
    suite_text = Path(args.suite).read_text().replace("{RID}", rid)
    suite = json.loads(suite_text)
    only_re = re.compile(args.only) if args.only else None
    for probe in suite:
        if only_re and not only_re.search(probe["name"]):
            continue
        tag_suffix = f"__{args.tag}" if args.tag else ""
        out_path = OUT / f"{probe['name']}{tag_suffix}.json"
        if out_path.exists():
            print(f"skip (exists): {out_path.name}", file=sys.stderr)
            continue
        probe["_rid"] = rid
        result = run_probe(probe)
        result["run_id"] = rid
        out_path.write_text(json.dumps(result, indent=2))
        print(f"  wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
