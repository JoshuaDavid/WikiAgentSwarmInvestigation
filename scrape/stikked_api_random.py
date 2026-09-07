#!/usr/bin/env python3
"""Scrape a stikked instance whose /lists index is disabled but /api/random works.

Enumerates pids by two routes and takes the union:

  1. Poll /api/random until convergence (no new pid in the last `stop_after`
     draws) OR max iterations reached.
  2. Query the Wayback Machine CDX for `<host>/view/*` archived snapshots.

For each pid, fetch /api/paste/<pid> once against the live site. Wayback
is used only for enumeration, not for body fetch — the live site is
authoritative when it responds.

Output: scrape/outputs/<name>/{index.jsonl,bodies.jsonl,manifest.json}.

Usage:
    python3 scrape/stikked_api_random.py --host https://paste.example.com/
    python3 scrape/stikked_api_random.py --host https://... --max-draws 400
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = (
    "Automation (investigating OpenAI agent swarm; "
    "contact swarmchasers discord https://discord.gg/RVUnKefG7 / "
    "joshuad93@gmail.com for more info)"
)
WB_CDX = "https://web.archive.org/cdx/search/cdx"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def _maybe_gunzip(headers: dict, body: bytes) -> bytes:
    ce = (headers.get("Content-Encoding") or headers.get("content-encoding") or "").lower()
    if "gzip" in ce or body[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(body)
        except Exception:
            return body
    return body


def fetch(url: str, *, timeout: int = 30) -> tuple[int, dict, bytes, str | None]:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            hdrs = dict(resp.headers.items())
            return resp.status, hdrs, _maybe_gunzip(hdrs, body), None
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        hdrs = dict(e.headers.items()) if e.headers else {}
        return e.code, hdrs, _maybe_gunzip(hdrs, body), f"HTTPError {e.code} {e.reason}"
    except Exception as e:
        return 0, {}, b"", f"{type(e).__name__}: {e}"


def parse_json_lenient(text: str) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            obj, _ = json.JSONDecoder().raw_decode(text.lstrip())
            return obj if isinstance(obj, dict) else None
        except (json.JSONDecodeError, ValueError):
            return None


def slugify(host: str) -> str:
    slug = re.sub(r"^https?://", "", host.rstrip("/"))
    return re.sub(r"[^a-zA-Z0-9._-]", "-", slug)


def enumerate_via_api_random(base: str, sleep: float, max_draws: int, stop_after: int) -> tuple[set[str], list[dict]]:
    """Poll /api/random until no new pid in the last `stop_after` draws."""
    seen: set[str] = set()
    log: list[dict] = []
    since_last_new = 0
    for i in range(max_draws):
        t0 = time.monotonic()
        status, _hdrs, body, err = fetch(f"{base}api/random")
        text = body.decode("utf-8", errors="replace") if body else ""
        j = parse_json_lenient(text)
        pid = j.get("pid") if isinstance(j, dict) else None
        new_pid = False
        if pid and pid not in seen:
            seen.add(pid)
            new_pid = True
            since_last_new = 0
        else:
            since_last_new += 1
        log.append({"iter": i, "status": status, "pid": pid, "new": new_pid,
                    "distinct_so_far": len(seen), "err": err})
        if (i + 1) % 25 == 0:
            print(
                f"[random] {i+1:4d}/{max_draws} distinct={len(seen):3d} "
                f"since_last_new={since_last_new}",
                file=sys.stderr,
            )
        if since_last_new >= stop_after:
            print(f"[random] converged after {i+1} draws, no new pid in last {stop_after}", file=sys.stderr)
            break
        target = t0 + sleep
        remaining = target - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
    return seen, log


def enumerate_via_wayback(host: str) -> set[str]:
    """CDX for <host>/view/* -> distinct pids."""
    # host like https://paste.example.com/
    hostname = re.sub(r"^https?://", "", host.rstrip("/"))
    url = (
        f"{WB_CDX}?url={hostname}/view/*&output=json"
        f"&fl=original,statuscode&filter=statuscode:200&collapse=urlkey"
    )
    data = None
    for attempt in range(1, 4):
        status, _hdrs, body, err = fetch(url, timeout=90)
        if status == 200 and body:
            try:
                data = json.loads(body)
                break
            except json.JSONDecodeError:
                pass
        print(f"[wayback] attempt {attempt} status={status} err={err}", file=sys.stderr)
        time.sleep(5 * attempt)
    if not data:
        return set()
    rx = re.compile(r"/view/(?:raw/)?([a-z0-9]+)(?:/diff)?$")
    seen: set[str] = set()
    for row in data[1:]:
        m = rx.search(row[0])
        if m:
            seen.add(m.group(1))
    return seen


def scrape_bodies(base: str, pids: list[str], sleep: float) -> list[dict]:
    out: list[dict] = []
    for i, pid in enumerate(pids):
        url = f"{base}api/paste/{pid}"
        t0 = time.monotonic()
        status, hdrs, body, err = fetch(url)
        text = body.decode("utf-8", errors="replace") if body else ""
        j = parse_json_lenient(text)
        rec = {
            "pid": pid,
            "request_time_utc": utc_now(),
            "status": status,
            "headers": hdrs,
            "body_text": text,
            "body_json": j,
            "error": err,
        }
        out.append(rec)
        title = j.get("title") if isinstance(j, dict) else None
        print(
            f"[body ] {i+1:4d}/{len(pids)}  pid={pid}  status={status}  title={title!r} err={err}",
            file=sys.stderr,
        )
        target = t0 + sleep
        remaining = target - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--name", default=None)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--max-draws", type=int, default=400,
                    help="Cap on /api/random draws")
    ap.add_argument("--stop-after", type=int, default=100,
                    help="Stop after this many draws without a new pid")
    ap.add_argument("--skip-wayback", action="store_true")
    args = ap.parse_args()

    base = args.host if args.host.endswith("/") else args.host + "/"
    slug = args.name or slugify(base)
    out_dir = Path(__file__).resolve().parent / "outputs" / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    index_path = out_dir / "index.jsonl"
    bodies_path = out_dir / "bodies.jsonl"
    manifest_path = out_dir / "manifest.json"
    random_log_path = out_dir / "random_draw_log.jsonl"
    for p in (index_path, bodies_path, manifest_path, random_log_path):
        if p.exists():
            p.unlink()

    started = utc_now()
    print(f"[scrape] host={base} name={slug}", file=sys.stderr)

    print("[phase] /api/random enumeration", file=sys.stderr)
    api_pids, draw_log = enumerate_via_api_random(base, args.sleep, args.max_draws, args.stop_after)
    with random_log_path.open("w") as f:
        for row in draw_log:
            f.write(json.dumps(row) + "\n")

    if args.skip_wayback:
        wb_pids: set[str] = set()
    else:
        print("[phase] wayback CDX enumeration", file=sys.stderr)
        wb_pids = enumerate_via_wayback(base)
        print(f"[wayback] wayback-only pids: {len(wb_pids - api_pids)}, overlap: {len(wb_pids & api_pids)}", file=sys.stderr)

    all_pids = sorted(api_pids | wb_pids)
    index_rows = [
        {"pid": p, "seen_via_api_random": p in api_pids, "seen_via_wayback": p in wb_pids}
        for p in all_pids
    ]
    with index_path.open("w") as f:
        for r in index_rows:
            f.write(json.dumps(r) + "\n")

    print(f"[phase] /api/paste/<pid> for {len(all_pids)} pids", file=sys.stderr)
    body_rows = scrape_bodies(base, all_pids, args.sleep)
    with bodies_path.open("w") as f:
        for r in body_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "base": base,
        "name": slug,
        "user_agent": USER_AGENT,
        "route": "live_stikked_api_random_plus_wayback",
        "sleep_seconds": args.sleep,
        "started_at": started,
        "finished_at": utc_now(),
        "max_draws": args.max_draws,
        "stop_after": args.stop_after,
        "api_random_draws": len(draw_log),
        "api_random_pids": len(api_pids),
        "wayback_pids": len(wb_pids),
        "union_pids": len(all_pids),
        "index_rows": len(index_rows),
        "body_rows": len(body_rows),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[scrape] wrote {len(index_rows)} index / {len(body_rows)} bodies to {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
