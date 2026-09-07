#!/usr/bin/env python3
"""Full-site scrape of https://pastebin.k4be.pl.

The site runs stikked (see tmp/stikked-src/). `/api/random` samples uniformly
from all unexpired non-private pastes; `/lists/{offset}` paginates the same
set 15 rows at a time. This script paginates `/lists/` to collect every pid
on the server today, then fetches `/api/paste/{pid}` once per pid for the
full JSON body (title, name, raw, created, hits, expire, ...).

Idempotent. Rerun deletes and rewrites the two output files. Output goes to
scrape/outputs/pastebin-k4be/ (not agent-logs/) because a downstream step
filters this dump down to only agent-authored pastes before writing into
agent-logs/pastebin-k4be/. See analyses/pastebin-k4be-full-classify/ for
that step.

Usage:
    python3 scrape/pastebin_k4be.py                # full scrape, ~7 min
    python3 scrape/pastebin_k4be.py --sanity       # 2 list pages + 3 bodies
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://pastebin.k4be.pl"
USER_AGENT = (
    "Automation (investigating OpenAI agent swarm; "
    "contact swarmchasers discord https://discord.gg/RVUnKefG7 / "
    "joshuad93@gmail.com for more info)"
)
SLEEP = 1.0

OUT_DIR = Path(__file__).resolve().parent / "outputs" / "pastebin-k4be"
INDEX_JSONL = OUT_DIR / "index.jsonl"      # one row per (pid, title, name, ago_text)
BODIES_JSONL = OUT_DIR / "bodies.jsonl"    # one row per /api/paste/{pid} response
MANIFEST = OUT_DIR / "manifest.json"


# ---------- utilities ----------


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def fetch(url: str) -> tuple[int, dict, bytes, str | None]:
    """Return (status, headers_dict, raw_bytes, error_or_None). Never raises."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, dict(resp.headers.items()), resp.read(), None
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        return e.code, dict(e.headers.items()) if e.headers else {}, body, f"HTTPError {e.code} {e.reason}"
    except Exception as e:
        return 0, {}, b"", f"{type(e).__name__}: {e}"


# ---------- /lists parsing ----------

ROW_RE = re.compile(
    r'<tr class="(?:odd|even)">\s*'
    r'<td class="first"><a href="https://pastebin\.k4be\.pl/view/([a-z0-9]+)">'
    r'([^<]*)</a></td>\s*'
    r'<td>([^<]*)</td>\s*'      # name
    r'<td>([^<]*)</td>\s*'      # language
    r'<td>([^<]*)</td>',         # "N days ago" text
    re.DOTALL,
)


def parse_list_page(html_bytes: bytes) -> list[dict]:
    html = html_bytes.decode("utf-8", errors="replace")
    rows = []
    for m in ROW_RE.finditer(html):
        pid, title, name, lang, ago = m.groups()
        rows.append(
            {
                "pid": pid,
                "title": title.strip(),
                "name": name.strip(),
                "lang": lang.strip(),
                "ago_text": ago.strip(),
            }
        )
    return rows


# ---------- driver ----------


def scrape_index(sanity: bool) -> list[dict]:
    """Paginate /lists/{offset} until a page has no rows. Returns list of index rows."""
    all_rows: list[dict] = []
    seen_pids: set[str] = set()
    offset = 0
    while True:
        url = f"{BASE}/lists" if offset == 0 else f"{BASE}/lists/{offset}"
        status, _hdrs, body, err = fetch(url)
        if err or status != 200:
            print(f"list fetch failed at offset={offset}: status={status} err={err}", file=sys.stderr)
            break
        rows = parse_list_page(body)
        if not rows:
            break
        added = 0
        for r in rows:
            if r["pid"] in seen_pids:
                continue
            seen_pids.add(r["pid"])
            r["list_offset"] = offset
            all_rows.append(r)
            added += 1
        print(f"[index] offset={offset:4d}  parsed={len(rows):2d}  new={added:2d}  total={len(all_rows)}", file=sys.stderr)
        if sanity and offset >= 15:
            break
        # If this page had fewer than 15 rows, it's the last one.
        if len(rows) < 15:
            break
        offset += 15
        time.sleep(SLEEP)
    return all_rows


def scrape_bodies(index_rows: list[dict], sanity: bool) -> list[dict]:
    """For every pid, fetch /api/paste/{pid} and record it."""
    out: list[dict] = []
    if sanity:
        index_rows = index_rows[:3]
    for i, row in enumerate(index_rows):
        url = f"{BASE}/api/paste/{row['pid']}"
        t0 = time.monotonic()
        status, hdrs, body, err = fetch(url)
        text = body.decode("utf-8", errors="replace") if body else ""
        try:
            body_json = json.loads(text) if text else None
        except json.JSONDecodeError:
            body_json = None
        rec = {
            "pid": row["pid"],
            "index_title": row.get("title"),
            "index_name": row.get("name"),
            "index_ago_text": row.get("ago_text"),
            "request_time_utc": utc_now(),
            "status": status,
            "headers": hdrs,
            "body_text": text,
            "body_json": body_json,
            "error": err,
        }
        out.append(rec)
        j = body_json or {}
        title = j.get("title") if isinstance(j, dict) else None
        print(
            f"[body ] {i+1:3d}/{len(index_rows)}  pid={row['pid']}  status={status}  "
            f"title={title!r} err={err}",
            file=sys.stderr,
        )
        # Absolute-clock pacing.
        target = t0 + SLEEP
        remaining = target - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sanity", action="store_true", help="hit 2 list pages + 3 bodies")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for p in (INDEX_JSONL, BODIES_JSONL, MANIFEST):
        if p.exists():
            p.unlink()

    started_at = utc_now()
    index_rows = scrape_index(sanity=args.sanity)
    with INDEX_JSONL.open("w") as f:
        for r in index_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    body_rows = scrape_bodies(index_rows, sanity=args.sanity)
    with BODIES_JSONL.open("w") as f:
        for r in body_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "base": BASE,
        "user_agent": USER_AGENT,
        "sleep_seconds": SLEEP,
        "started_at": started_at,
        "finished_at": utc_now(),
        "sanity": args.sanity,
        "index_rows": len(index_rows),
        "body_rows": len(body_rows),
        "index_file": INDEX_JSONL.name,
        "bodies_file": BODIES_JSONL.name,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {len(index_rows)} index rows and {len(body_rows)} bodies to {OUT_DIR}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
