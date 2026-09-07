#!/usr/bin/env python3
"""Generic stikked-instance scrape.

Behaviour is a direct port of scrape/pastebin_k4be.py parameterized on
`--host`. Works on any stikked deployment where `/lists` returns the paged
paste index and `/api/paste/<pid>` returns the JSON body.

Output goes to `scrape/outputs/<name>/`, where `<name>` is either the
value of `--name` or a slug derived from the host.

Usage:
    python3 scrape/stikked_scrape.py --host https://paste.example.com/
    python3 scrape/stikked_scrape.py --host https://paste.example.com/ --name my-alias
    python3 scrape/stikked_scrape.py --host https://... --sleep 2.0 --sanity
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

USER_AGENT = (
    "Automation (investigating OpenAI agent swarm; "
    "contact swarmchasers discord https://discord.gg/RVUnKefG7 / "
    "joshuad93@gmail.com for more info)"
)
DEFAULT_SLEEP = 1.0


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def fetch(url: str, *, timeout: int = 30) -> tuple[int, dict, bytes, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers.items()), resp.read(), None
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        return e.code, dict(e.headers.items()) if e.headers else {}, body, f"HTTPError {e.code} {e.reason}"
    except Exception as e:
        return 0, {}, b"", f"{type(e).__name__}: {e}"


def make_row_re(base: str) -> re.Pattern:
    """Match a stikked `/lists` row for the given base URL.

    Some deployments use `<tr class="odd|even">`, others use bare `<tr>` (no
    class). Some emit 4 `<td>` cells (title, name, lang, ago); others emit 5
    (title, name, lang, hidden-timestamp, ago) or more. Match the row
    container loosely and then grab title/name/language from the first three
    `<td>` cells and the last one as ago-text.
    """
    escaped = re.escape(base.rstrip("/"))
    return re.compile(
        r'<tr(?:\s+class="[^"]*")?\s*>\s*'
        rf'<td class="first"><a href="{escaped}/view/([a-z0-9]+)">'
        r'([^<]*)</a></td>\s*'
        r'<td[^>]*>([^<]*)</td>\s*'   # name
        r'<td[^>]*>([^<]*)</td>'      # language
        r'(?:\s*<td[^>]*>[^<]*</td>)*'  # any intermediate cells (hidden ts etc.)
        r'\s*<td[^>]*>([^<]*)</td>\s*</tr>',  # ago-text (last cell)
        re.DOTALL,
    )


def parse_list_page(html_bytes: bytes, row_re: re.Pattern) -> list[dict]:
    html = html_bytes.decode("utf-8", errors="replace")
    return [
        {
            "pid": m.group(1),
            "title": m.group(2).strip(),
            "name": m.group(3).strip(),
            "lang": m.group(4).strip(),
            "ago_text": m.group(5).strip(),
        }
        for m in row_re.finditer(html)
    ]


def slugify(host: str) -> str:
    slug = re.sub(r"^https?://", "", host.rstrip("/"))
    slug = re.sub(r"[^a-zA-Z0-9._-]", "-", slug)
    return slug


def scrape_index(base: str, sleep: float, sanity: bool, max_offset_stop: int = 10000) -> list[dict]:
    row_re = make_row_re(base)
    all_rows: list[dict] = []
    seen_pids: set[str] = set()
    offset = 0
    while True:
        url = f"{base}lists" if offset == 0 else f"{base}lists/{offset}"
        status, _hdrs, body, err = fetch(url)
        if err or status != 200:
            print(f"[index] fetch failed at offset={offset}: status={status} err={err}", file=sys.stderr)
            break
        rows = parse_list_page(body, row_re)
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
        print(
            f"[index] offset={offset:4d}  parsed={len(rows):2d}  new={added:2d}  total={len(all_rows)}",
            file=sys.stderr,
        )
        if sanity and offset >= 15:
            break
        if len(rows) < 15 or offset >= max_offset_stop:
            break
        offset += 15
        time.sleep(sleep)
    return all_rows


def scrape_bodies(base: str, index_rows: list[dict], sleep: float, sanity: bool) -> list[dict]:
    out: list[dict] = []
    if sanity:
        index_rows = index_rows[:3]
    for i, row in enumerate(index_rows):
        url = f"{base}api/paste/{row['pid']}"
        t0 = time.monotonic()
        status, hdrs, body, err = fetch(url)
        text = body.decode("utf-8", errors="replace") if body else ""
        # Some stikked hosts emit PHP deprecation warnings after the JSON
        # response. Use raw_decode to parse just the leading JSON object.
        body_json = None
        if text:
            try:
                body_json = json.loads(text)
            except json.JSONDecodeError:
                try:
                    body_json, _end = json.JSONDecoder().raw_decode(text.lstrip())
                except (json.JSONDecodeError, ValueError):
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
        title = None
        if isinstance(body_json, dict):
            title = body_json.get("title")
        print(
            f"[body ] {i+1:4d}/{len(index_rows)}  pid={row['pid']}  status={status}  "
            f"title={title!r} err={err}",
            file=sys.stderr,
        )
        target = t0 + sleep
        remaining = target - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="Base URL, e.g. https://paste.example.com/")
    ap.add_argument("--name", default=None, help="Output directory name (default: derived from host)")
    ap.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)
    ap.add_argument("--sanity", action="store_true")
    args = ap.parse_args()

    base = args.host if args.host.endswith("/") else args.host + "/"
    slug = args.name or slugify(base)
    out_dir = Path(__file__).resolve().parent / "outputs" / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    index_path = out_dir / "index.jsonl"
    bodies_path = out_dir / "bodies.jsonl"
    manifest_path = out_dir / "manifest.json"
    for p in (index_path, bodies_path, manifest_path):
        if p.exists():
            p.unlink()

    started = utc_now()
    print(f"[scrape] host={base}  name={slug}", file=sys.stderr)
    index_rows = scrape_index(base, args.sleep, args.sanity)
    with index_path.open("w") as f:
        for r in index_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    body_rows = scrape_bodies(base, index_rows, args.sleep, args.sanity)
    with bodies_path.open("w") as f:
        for r in body_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "base": base,
        "name": slug,
        "user_agent": USER_AGENT,
        "sleep_seconds": args.sleep,
        "started_at": started,
        "finished_at": utc_now(),
        "sanity": args.sanity,
        "index_rows": len(index_rows),
        "body_rows": len(body_rows),
        "index_file": index_path.name,
        "bodies_file": bodies_path.name,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[scrape] wrote {len(index_rows)} index / {len(body_rows)} bodies to {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
