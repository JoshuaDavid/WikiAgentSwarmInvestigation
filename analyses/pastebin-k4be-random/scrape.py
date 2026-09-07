#!/usr/bin/env python3
"""Poll pastebin.k4be.pl/api/random and record each response verbatim.

Each iteration writes one JSON line to outputs/responses.jsonl with:
  * request_time_utc, elapsed_seconds since fetch start
  * status, url_final (after redirects, if any)
  * headers (dict)
  * body_text (the raw response body, decoded utf-8 with replace)
  * body_json (parsed JSON if the body parses, else null)
  * error (str or null)

Rerun with: python3 scrape.py [--iters N] [--sleep S]

The default is 100 iterations at 1.0 s between requests. The run also writes
outputs/run_manifest.json with start/end wall clock, iters, sleep, User-Agent,
and the endpoint URL.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "https://pastebin.k4be.pl/api/random"
USER_AGENT = (
    "Automation (investigating OpenAI agent swarm; "
    "contact swarmchasers discord https://discord.gg/RVUnKefG7 / "
    "joshuad93@gmail.com for more info)"
)

OUT_DIR = Path(__file__).parent / "outputs"
RESPONSES_PATH = OUT_DIR / "responses.jsonl"
MANIFEST_PATH = OUT_DIR / "run_manifest.json"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def fetch_once() -> dict:
    """Return a record dict for one API call. Never raises."""
    record: dict = {
        "request_time_utc": utc_now(),
        "status": None,
        "url_final": None,
        "headers": None,
        "body_text": None,
        "body_json": None,
        "error": None,
    }
    req = urllib.request.Request(
        ENDPOINT,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/html;q=0.5",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            record["status"] = resp.status
            record["url_final"] = resp.geturl()
            record["headers"] = dict(resp.headers.items())
            raw = resp.read()
    except urllib.error.HTTPError as e:
        record["status"] = e.code
        record["url_final"] = e.url
        record["headers"] = dict(e.headers.items()) if e.headers else None
        try:
            raw = e.read()
        except Exception:
            raw = b""
        record["error"] = f"HTTPError {e.code} {e.reason}"
    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
        return record

    try:
        record["body_text"] = raw.decode("utf-8", errors="replace")
    except Exception as e:
        record["body_text"] = None
        record["error"] = record["error"] or f"decode: {type(e).__name__}: {e}"

    if record["body_text"] is not None:
        try:
            record["body_json"] = json.loads(record["body_text"])
        except json.JSONDecodeError:
            record["body_json"] = None
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=100)
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Fresh run — overwrite prior responses.
    if RESPONSES_PATH.exists():
        RESPONSES_PATH.unlink()

    start_wall = time.monotonic()
    start_utc = utc_now()
    manifest = {
        "endpoint": ENDPOINT,
        "user_agent": USER_AGENT,
        "iters_requested": args.iters,
        "sleep_seconds": args.sleep,
        "start_utc": start_utc,
        "end_utc": None,
        "iters_completed": 0,
        "responses_file": str(RESPONSES_PATH.name),
    }

    with RESPONSES_PATH.open("w") as fout:
        for i in range(args.iters):
            t0 = time.monotonic()
            rec = fetch_once()
            rec["iter"] = i
            rec["elapsed_seconds"] = round(t0 - start_wall, 3)
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fout.flush()
            manifest["iters_completed"] = i + 1
            # Log a one-line progress marker to stderr.
            j = rec.get("body_json") or {}
            pid = j.get("pid") if isinstance(j, dict) else None
            title = j.get("title") if isinstance(j, dict) else None
            print(
                f"[{i+1:3d}/{args.iters}] status={rec['status']} "
                f"pid={pid} title={title!r}",
                file=sys.stderr,
                flush=True,
            )
            # Sleep to the next tick, absolute clock so slow requests don't skew.
            if i < args.iters - 1:
                target = start_wall + (i + 1) * args.sleep
                remaining = target - time.monotonic()
                if remaining > 0:
                    time.sleep(remaining)

    manifest["end_utc"] = utc_now()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"wrote {manifest['iters_completed']} responses to {RESPONSES_PATH}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
