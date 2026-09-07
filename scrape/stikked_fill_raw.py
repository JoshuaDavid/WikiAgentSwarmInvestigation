#!/usr/bin/env python3
"""Fill empty raw bodies in an existing scrape by fetching /view/raw/<pid>.

Some stikked hosts return "Invalid API key" or "The API has been disabled"
on /api/paste even when /api/random works. In that case the earlier scrape
has full metadata (title, name, hits) from /view/<pid>-parsed sources OR
partial JSON body_json BUT `raw` is None/empty.

This script re-reads `scrape/outputs/<name>/bodies.jsonl`, for each row
where `body_json.raw` is empty/missing, fetches
`<base>/view/raw/<pid>` and writes back the same rows with a new
`view_raw_body` field. Downstream code prefers `body_json.raw` when
present, falling back to `view_raw_body`.

Usage:
    python3 scrape/stikked_fill_raw.py --host <base> --name <slug>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

USER_AGENT = (
    "Automation (investigating OpenAI agent swarm; "
    "contact swarmchasers discord https://discord.gg/RVUnKefG7 / "
    "joshuad93@gmail.com for more info)"
)


def fetch(url: str, timeout: int = 30) -> tuple[int, bytes, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), None
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        return e.code, body, f"HTTPError {e.code} {e.reason}"
    except Exception as e:
        return 0, b"", f"{type(e).__name__}: {e}"


def raw_body_missing(row: dict) -> bool:
    j = row.get("body_json") or {}
    if not isinstance(j, dict):
        j = {}
    raw = j.get("raw")
    return not raw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()

    base = args.host if args.host.endswith("/") else args.host + "/"
    bodies_path = Path(__file__).resolve().parent / "outputs" / args.name / "bodies.jsonl"
    if not bodies_path.exists():
        print(f"not found: {bodies_path}", file=sys.stderr)
        return 1
    rows = [json.loads(l) for l in bodies_path.open()]
    filled = 0
    for i, row in enumerate(rows):
        if not raw_body_missing(row):
            continue
        pid = row.get("pid")
        if not pid:
            continue
        url = f"{base}view/raw/{pid}"
        t0 = time.monotonic()
        status, body, err = fetch(url)
        if status == 200 and body:
            text = body.decode("utf-8", errors="replace")
            row["view_raw_body"] = text
            row["view_raw_status"] = status
            filled += 1
            print(
                f"[fill] {i+1:4d}/{len(rows)}  pid={pid}  status={status}  "
                f"raw_len={len(text)}",
                file=sys.stderr,
            )
        else:
            row["view_raw_body"] = None
            row["view_raw_status"] = status
            row["view_raw_error"] = err
            print(
                f"[fill] {i+1:4d}/{len(rows)}  pid={pid}  status={status}  err={err}",
                file=sys.stderr,
            )
        # Rate limit
        target = t0 + args.sleep
        remaining = target - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)

    with bodies_path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[fill] rewrote {bodies_path} ({filled}/{len(rows)} rows filled)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
