#!/usr/bin/env python3
"""Generalized Wayback Machine scrape of a stikked instance.

This is a host-parameterized port of scrape/paste_linuxiarz_wayback.py.

Enumerates archived pids via the Wayback CDX API for `<host>/view/*`,
then fetches the most recent 200 snapshot of both `/view/raw/<pid>`
(the paste body) and `/view/<pid>` (an HTML page from which we parse
name, ago, language). Optionally attempts a live `/view/raw/<pid>`
first — some hosts block `/api/paste` but leave `/view/raw` open.

Output: scrape/outputs/<name>/{index.jsonl,bodies.jsonl,manifest.json,
_cdx_cache.json}

Usage:
    python3 scrape/stikked_wayback.py --host https://paste.example.com/
    python3 scrape/stikked_wayback.py --host ... --skip-known-shellac \\
        --corpus-prefix example-slug
    python3 scrape/stikked_wayback.py --host ... --prefer-live
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
    if "gzip" in ce or (body and body[:2] == b"\x1f\x8b"):
        try:
            return gzip.decompress(body)
        except Exception:
            return body
    return body


def fetch(url: str, *, timeout: int = 60) -> tuple[int, dict, bytes, str | None]:
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


def slugify(host: str) -> str:
    slug = re.sub(r"^https?://", "", host.rstrip("/"))
    return re.sub(r"[^a-zA-Z0-9._-]", "-", slug)


def cdx_view_pids(hostname: str, out_dir: Path) -> list[dict]:
    """Return most recent 200 snapshot per distinct pid, from Wayback CDX."""
    cache_path = out_dir / "_cdx_cache.json"
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        if cached.get("rows"):
            print(f"[cdx] using cached response from {cache_path}", file=sys.stderr)
            return cached["rows"]

    url = (
        f"{WB_CDX}?url={hostname}/view/*&output=json"
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
        raise RuntimeError(f"CDX fetch failed after retries for {hostname}")

    rx = re.compile(rf"^https?://{re.escape(hostname)}/view/(?:raw/)?([a-z0-9]+)(?:/diff)?$")
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
DETAIL_RE = re.compile(
    r'<span class="detail by">From ([^,]+), ([^,]+), written in ([^,]+), viewed ([^ ]+) times\.'
)


def make_reply_row_re(host: str) -> re.Pattern:
    hostname = re.sub(r"^https?://", "", host.rstrip("/"))
    return re.compile(
        rf'<tr class="(?:odd|even)">\s*<td class="first"><a href="[^"]*{re.escape(hostname)}/view/([a-z0-9]+)">'
        r'([^<]*)</a></td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>',
        re.DOTALL,
    )


def parse_view_html(html: str, reply_row_re: re.Pattern) -> dict:
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
    for rm in reply_row_re.finditer(html):
        out["replies"].append(
            {"pid": rm.group(1), "title": rm.group(2).strip(),
             "name": rm.group(3).strip(), "lang": rm.group(4).strip()}
        )
    return out


def wb_url(ts: str, orig: str, raw_content: bool = True) -> str:
    suffix = "id_" if raw_content else ""
    return f"https://web.archive.org/web/{ts}{suffix}/{orig}"


def scrape_body(host: str, pid: str, wb_timestamp: str, reply_row_re: re.Pattern,
                prefer_live: bool, sleep: float) -> dict:
    raw_source = "wayback"
    raw_url = wb_url(wb_timestamp, f"{host}view/raw/{pid}", raw_content=True)
    view_url = wb_url(wb_timestamp, f"{host}view/{pid}", raw_content=False)

    rec: dict = {
        "pid": pid,
        "wb_timestamp": wb_timestamp,
        "raw_url": raw_url,
        "view_url": view_url,
        "live_view_raw_url": f"{host}view/raw/{pid}",
        "request_time_utc": utc_now(),
        "raw_status": None,
        "raw_source": None,
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

    # Optionally try live /view/raw first
    if prefer_live:
        live_url = f"{host}view/raw/{pid}"
        status, _hdrs, body, err = fetch(live_url)
        if status == 200 and body:
            rec["raw_body"] = body.decode("utf-8", errors="replace")
            rec["raw_status"] = 200
            rec["raw_source"] = "live_view_raw"
        else:
            rec["raw_status"] = status
            rec["raw_error"] = err
        time.sleep(sleep)

    # Wayback /view/raw if not filled
    if not rec["raw_body"]:
        status, _hdrs, body, err = fetch(raw_url)
        rec["raw_status"] = status
        rec["raw_error"] = err
        if status == 200 and body:
            rec["raw_body"] = body.decode("utf-8", errors="replace")
            rec["raw_source"] = "wayback_view_raw"
        time.sleep(sleep)

    # Wayback /view for title/name
    status, _hdrs, body, err = fetch(view_url)
    rec["view_status"] = status
    rec["view_error"] = err
    if status == 200 and body:
        html = body.decode("utf-8", errors="replace")
        meta = parse_view_html(html, reply_row_re)
        rec["view_title"] = meta["title"]
        rec["view_name"] = meta["name"]
        rec["view_ago"] = meta["ago"]
        rec["view_lang"] = meta["lang"]
        rec["view_hits"] = meta["hits"]
        rec["view_replies"] = meta["replies"]
    time.sleep(sleep)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--name", default=None)
    ap.add_argument("--sleep", type=float, default=2.0)
    ap.add_argument("--sanity", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--prefer-live", action="store_true",
                    help="Attempt live /view/raw before wayback")
    ap.add_argument("--skip-known-shellac", action="store_true")
    ap.add_argument("--corpus-prefix", default=None,
                    help="Prefix under agent-logs/pastes/ for shellac dedup")
    args = ap.parse_args()

    base = args.host if args.host.endswith("/") else args.host + "/"
    slug = args.name or slugify(base)
    hostname = re.sub(r"^https?://", "", base.rstrip("/"))
    out_dir = Path(__file__).resolve().parent / "outputs" / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    index_path = out_dir / "index.jsonl"
    bodies_path = out_dir / "bodies.jsonl"
    manifest_path = out_dir / "manifest.json"
    for p in (index_path, bodies_path, manifest_path):
        if p.exists():
            p.unlink()

    skip_pids: set[str] = set()
    if args.skip_known_shellac and args.corpus_prefix:
        corpus = Path(__file__).resolve().parents[1] / "agent-logs" / "pastes" / "revisions.jsonl"
        with corpus.open() as cf:
            for line in cf:
                r = json.loads(line)
                pid_path = r.get("page_id", "")
                if pid_path.startswith(f"pastes/{args.corpus_prefix}/"):
                    skip_pids.add(pid_path.split("/", 2)[2])
        print(f"[skip] {len(skip_pids)} shellac-known {args.corpus_prefix} pids will be skipped", file=sys.stderr)

    started = utc_now()
    print(f"[scrape] host={base} name={slug} prefer_live={args.prefer_live}", file=sys.stderr)
    print("[cdx] enumerating archived /view/<pid> ...", file=sys.stderr)
    index = cdx_view_pids(hostname, out_dir)
    with index_path.open("w") as f:
        for row in index:
            f.write(json.dumps(row) + "\n")
    print(f"[cdx] distinct pids: {len(index)}", file=sys.stderr)

    fetch_list = [r for r in index if r["pid"] not in skip_pids]
    if args.sanity:
        fetch_list = fetch_list[:3]
    elif args.limit is not None:
        fetch_list = fetch_list[: args.limit]

    reply_row_re = make_reply_row_re(base)
    with bodies_path.open("w") as f:
        for i, row in enumerate(fetch_list):
            rec = scrape_body(base, row["pid"], row["wb_timestamp"], reply_row_re,
                              args.prefer_live, args.sleep)
            rec["iter"] = i
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            title = rec.get("view_title") or ""
            name = rec.get("view_name") or ""
            raw_len = len(rec.get("raw_body") or "")
            src = rec.get("raw_source") or "none"
            print(
                f"[body ] {i+1:4d}/{len(fetch_list)}  pid={row['pid']}  "
                f"raw={rec['raw_status']}({src})  view={rec['view_status']}  "
                f"title={title[:50]!r}  name={name[:20]!r}  raw_len={raw_len}",
                file=sys.stderr,
            )

    manifest = {
        "base": base,
        "name": slug,
        "route": "wayback_view" + ("_prefer_live" if args.prefer_live else ""),
        "wayback_cdx": WB_CDX,
        "user_agent": USER_AGENT,
        "sleep_seconds": args.sleep,
        "started_at": started,
        "finished_at": utc_now(),
        "sanity": args.sanity,
        "limit": args.limit,
        "prefer_live": args.prefer_live,
        "corpus_prefix": args.corpus_prefix,
        "skip_known_shellac": args.skip_known_shellac,
        "index_rows": len(index),
        "body_rows": len(fetch_list),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[scrape] wrote {len(index)} index / {len(fetch_list)} bodies to {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
