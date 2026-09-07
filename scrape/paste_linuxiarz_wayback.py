#!/usr/bin/env python3
"""Wayback-based scrape of https://paste.linuxiarz.pl.

The live site currently blocks all data endpoints for unauthenticated
users:

  * `/api/*`     -> HTTP 403 (Angie / nginx level ACL)
  * `/lists`, `/lists/N`, `/view/<pid>`, `/view/raw/<pid>` -> HTTP 404

The 404s look intentional. Even shellac-known pids that were live months
ago now return 404. We fall back to the Internet Archive Wayback Machine,
which retains snapshots of `/lists/N` (through 2026-09-04) and
`/view/<pid>` (~370 distinct pids).

Pipeline:

1. CDX enumerate every archived `paste.linuxiarz.pl/view/*` URL. Collapse
   by urlkey to one row per distinct pid, keep the most recent snapshot
   with statuscode 200.
2. For each pid: fetch the archived `/view/raw/{pid}` via
   `https://web.archive.org/web/{ts}id_/https://paste.linuxiarz.pl/view/raw/{pid}`
   for the paste body (no wayback HTML wrapping), plus
   `/view/{pid}` for title + name.
3. Emit outputs to scrape/outputs/paste-linuxiarz/{index.jsonl,bodies.jsonl,
   manifest.json}.

Considerate throttling: 2s between Wayback fetches (they explicitly ask
for slow crawlers). Same User-Agent as the k4be scrape so the operator
can trace requests to the same investigator.

The archived pastes may contain personal data (WiFi passwords, private
configs). Downstream classifiers must lean toward `human` for anything
that is not clearly a swarm artefact so we do not accidentally re-publish
someone else's private content.

Usage:
    python3 scrape/paste_linuxiarz_wayback.py            # full run
    python3 scrape/paste_linuxiarz_wayback.py --sanity   # 3 pids
    python3 scrape/paste_linuxiarz_wayback.py --limit N  # first N pids
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

BASE_LIVE = "https://paste.linuxiarz.pl"
WB_CDX = "https://web.archive.org/cdx/search/cdx"
USER_AGENT = (
    "Automation (investigating OpenAI agent swarm; "
    "contact swarmchasers discord https://discord.gg/RVUnKefG7 / "
    "joshuad93@gmail.com for more info)"
)
SLEEP = 2.0  # Wayback: keep it slow.

OUT_DIR = Path(__file__).resolve().parent / "outputs" / "paste-linuxiarz"
INDEX_JSONL = OUT_DIR / "index.jsonl"     # one row per (pid, wb_timestamp)
BODIES_JSONL = OUT_DIR / "bodies.jsonl"   # one row per fetched paste
MANIFEST = OUT_DIR / "manifest.json"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def _maybe_gunzip(headers: dict, body: bytes) -> bytes:
    # Wayback's id_ playback preserves the original response body, which for
    # stikked was gzip-encoded on the wire. urllib does not auto-decompress.
    ce = (headers.get("Content-Encoding") or headers.get("content-encoding") or "").lower()
    if "gzip" in ce or (body[:2] == b"\x1f\x8b"):
        try:
            return gzip.decompress(body)
        except Exception:
            return body
    return body


def fetch(url: str, *, timeout: int = 60) -> tuple[int, dict, bytes, str | None]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
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


def cdx_view_pids() -> list[dict]:
    """Return list of {pid, wb_timestamp} for the most recent 200 snapshot per pid."""
    # Cache the CDX response between reruns so a flaky Wayback doesn't force a re-fetch.
    cache_path = OUT_DIR / "_cdx_cache.json"
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        if cached.get("rows"):
            print(f"[cdx] using cached response from {cache_path}", file=sys.stderr)
            return cached["rows"]

    url = (
        f"{WB_CDX}?url=paste.linuxiarz.pl/view/*&output=json"
        f"&fl=original,timestamp,statuscode&filter=statuscode:200&collapse=urlkey"
    )
    data = None
    for attempt in range(1, 6):
        status, _hdrs, body, err = fetch(url, timeout=120)
        if status == 200 and body:
            try:
                data = json.loads(body)
                break
            except json.JSONDecodeError:
                pass
        wait = 5 * attempt
        print(f"[cdx] attempt {attempt} status={status} err={err}, retrying in {wait}s", file=sys.stderr)
        time.sleep(wait)
    if data is None:
        raise RuntimeError("CDX fetch failed after retries")
    # rows: [original, timestamp, statuscode], skip header row
    rx = re.compile(r"^https?://paste\.linuxiarz\.pl/view/(?:raw/)?([a-z0-9]+)(?:/diff)?$")
    latest: dict[str, str] = {}
    for row in data[1:]:
        m = rx.match(row[0])
        if not m:
            continue
        pid = m.group(1)
        ts = row[1]
        if pid not in latest or ts > latest[pid]:
            latest[pid] = ts
    rows = [{"pid": pid, "wb_timestamp": ts} for pid, ts in latest.items()]
    cache_path.write_text(json.dumps({"rows": rows, "cached_at": utc_now()}, indent=2))
    return rows


TITLE_RE = re.compile(r'<h1 class="pagetitle right">([^<]+)</h1>', re.DOTALL)
# "From <name>, <ago>, written in <lang>, viewed <hits> times."
DETAIL_RE = re.compile(
    r'<span class="detail by">From ([^,]+), ([^,]+), written in ([^,]+), viewed ([^ ]+) times\.'
)
# Reply table rows: pid + name + language (swarm handles surface here)
REPLY_ROW_RE = re.compile(
    r'<tr class="(?:odd|even)">\s*<td class="first"><a href="[^"]*/view/([a-z0-9]+)">'
    r'([^<]*)</a></td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>',
    re.DOTALL,
)


def parse_view_html(html: str) -> dict:
    """Extract title, name, ago, lang, hits, and replies from an archived /view/<pid> page."""
    out = {"title": "", "name": "", "ago": "", "lang": "", "hits": "", "replies": []}
    m = TITLE_RE.search(html)
    if m:
        out["title"] = m.group(1).strip()
    m = DETAIL_RE.search(html)
    if m:
        out["name"] = m.group(1).strip()
        out["ago"] = m.group(2).strip()
        out["lang"] = m.group(3).strip()
        out["hits"] = m.group(4).strip()
    for rm in REPLY_ROW_RE.finditer(html):
        out["replies"].append(
            {
                "pid": rm.group(1),
                "title": rm.group(2).strip(),
                "name": rm.group(3).strip(),
                "lang": rm.group(4).strip(),
            }
        )
    return out


def wb_url(ts: str, orig: str, raw_content: bool = True) -> str:
    """Build Wayback playback URL. `id_` gets the raw asset; without it, Wayback wraps."""
    suffix = "id_" if raw_content else ""
    return f"https://web.archive.org/web/{ts}{suffix}/{orig}"


def scrape_body(pid: str, wb_timestamp: str) -> dict:
    """Fetch archived /view/raw/<pid> plus /view/<pid> for title/name."""
    raw_url = wb_url(wb_timestamp, f"{BASE_LIVE}/view/raw/{pid}", raw_content=True)
    view_url = wb_url(wb_timestamp, f"{BASE_LIVE}/view/{pid}", raw_content=False)

    rec: dict = {
        "pid": pid,
        "wb_timestamp": wb_timestamp,
        "raw_url": raw_url,
        "view_url": view_url,
        "request_time_utc": utc_now(),
        "raw_status": None,
        "raw_error": None,
        "raw_body": None,
        "view_status": None,
        "view_error": None,
        "view_title": None,
        "view_name": None,
        "view_ago": None,
        "view_lang": None,
        "view_hits": None,
        "view_replies": None,
    }

    # /view/raw first (this is the paste body).
    status, _hdrs, body, err = fetch(raw_url)
    rec["raw_status"] = status
    rec["raw_error"] = err
    if status == 200:
        rec["raw_body"] = body.decode("utf-8", errors="replace")
    time.sleep(SLEEP)

    # /view/<pid> for title + name (HTML page)
    status, _hdrs, body, err = fetch(view_url)
    rec["view_status"] = status
    rec["view_error"] = err
    if status == 200:
        html = body.decode("utf-8", errors="replace")
        meta = parse_view_html(html)
        rec["view_title"] = meta["title"]
        rec["view_name"] = meta["name"]
        rec["view_ago"] = meta["ago"]
        rec["view_lang"] = meta["lang"]
        rec["view_hits"] = meta["hits"]
        rec["view_replies"] = meta["replies"]
    time.sleep(SLEEP)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sanity", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument(
        "--skip-known-shellac",
        action="store_true",
        help="Skip pids already covered by agent-logs/pastes/linuxiarz/*",
    )
    args = ap.parse_args()

    skip_pids: set[str] = set()
    if args.skip_known_shellac:
        corpus = Path(__file__).resolve().parents[1] / "agent-logs" / "pastes" / "revisions.jsonl"
        with corpus.open() as cf:
            for line in cf:
                r = json.loads(line)
                pid_path = r.get("page_id", "")
                if pid_path.startswith("pastes/linuxiarz/"):
                    skip_pids.add(pid_path.split("/", 2)[2])
        print(f"[skip] {len(skip_pids)} shellac-known linuxiarz pids will be skipped", file=sys.stderr)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for p in (INDEX_JSONL, BODIES_JSONL, MANIFEST):
        if p.exists():
            p.unlink()

    started = utc_now()
    print("[cdx] enumerating archived /view/<pid> ...", file=sys.stderr)
    index = cdx_view_pids()
    with INDEX_JSONL.open("w") as f:
        for row in index:
            f.write(json.dumps(row) + "\n")
    print(f"[cdx] distinct pids: {len(index)}", file=sys.stderr)

    fetch_list = [r for r in index if r["pid"] not in skip_pids]
    if args.sanity:
        fetch_list = fetch_list[:3]
    elif args.limit is not None:
        fetch_list = fetch_list[: args.limit]

    with BODIES_JSONL.open("w") as f:
        for i, row in enumerate(fetch_list):
            rec = scrape_body(row["pid"], row["wb_timestamp"])
            rec["iter"] = i
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            title = rec.get("view_title") or ""
            name = rec.get("view_name") or ""
            raw_len = len(rec.get("raw_body") or "")
            print(
                f"[body ] {i+1:3d}/{len(fetch_list)}  pid={row['pid']}  "
                f"raw={rec['raw_status']}  view={rec['view_status']}  "
                f"title={title[:50]!r}  name={name[:20]!r}  raw_len={raw_len}",
                file=sys.stderr,
            )

    manifest = {
        "base": BASE_LIVE,
        "route": "wayback_machine",
        "wayback_cdx": WB_CDX,
        "user_agent": USER_AGENT,
        "sleep_seconds": SLEEP,
        "started_at": started,
        "finished_at": utc_now(),
        "sanity": args.sanity,
        "limit": args.limit,
        "index_rows": len(index),
        "body_rows": len(fetch_list),
        "index_file": INDEX_JSONL.name,
        "bodies_file": BODIES_JSONL.name,
        "notes": [
            "Live paste.linuxiarz.pl blocks all data endpoints (403/404) as of 2026-09-07.",
            "Wayback archives cover ~370 distinct pids; 193 of those are not in the shellac corpus.",
            "Some archived pastes contain personal data (WiFi/API passwords, private ESPHome configs). Downstream classifier must lean human on anything that is not clearly a swarm artefact.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {len(index)} index rows and {len(fetch_list)} bodies to {OUT_DIR}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
