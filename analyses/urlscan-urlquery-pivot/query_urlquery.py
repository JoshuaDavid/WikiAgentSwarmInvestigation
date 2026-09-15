#!/usr/bin/env python3
"""Harvest urlquery.net search rows for every target in targets.py.

Writes:
  outputs/urlquery/hits.jsonl   one row per (target, report) pair
  outputs/urlquery/totals.tsv   per-target rows kept and date span

urlquery.net has no public JSON search API. Its search page loads rows from
the htmx endpoint /api/htmx/search/. The endpoint answers 204 (no body)
unless the request carries the htmx headers and a Referer for the search
page, so this script sends the same headers a browser sends. Rows come back
newest first, 96 per page, addressed by offset.

Each row holds: scan date (minute resolution), detection counts, the scanned
URL, the resolved IP with ASN, and the report id.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from targets import TARGETS, GENERIC_HOSTS, INCIDENT_WINDOW_START  # noqa: E402
from redact import redact_obj  # noqa: E402

OUT_DIR = os.path.join(HERE, "outputs", "urlquery")
UA = "Mozilla/5.0 (X11; Linux x86_64) collusionwiki-research/0.1"
BASE = "https://urlquery.net/api/htmx/search/"
PAGE = 96
MAX_PAGES = 25  # 2,400 rows per target
SLEEP = 1.5

ROW_RE = re.compile(r'<tr class="border-t[^"]*">(.*?)</tr>', re.S)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
HREF_RE = re.compile(r'href="([^"]+)"')
TAG_RE = re.compile(r"<[^>]+>")


def _text(cell: str) -> str:
    return html.unescape(TAG_RE.sub("", cell)).strip()


def _fetch(term: str, offset: int) -> str:
    params = {"q": term, "limit": PAGE, "offset": offset, "view": "list", "type": "reports"}
    url = BASE + "?" + urllib.parse.urlencode(params)
    referer = "https://urlquery.net/search?" + urllib.parse.urlencode({"q": term})
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,*/*",
        "HX-Request": "true",
        "HX-Current-URL": referer,
        "HX-Target": "search_results",
        "HX-Trigger": "search_query",
        "Referer": referer,
    }
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                if r.status == 204:
                    return ""
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} for {term} offset={offset}", file=sys.stderr)
            time.sleep(15)
        except Exception as ex:
            print(f"  error {ex!r}; retrying", file=sys.stderr)
            time.sleep(15)
    return ""


def _parse(page: str) -> list[dict]:
    rows = []
    for raw in ROW_RE.findall(page):
        cells = CELL_RE.findall(raw)
        if len(cells) < 4:
            continue
        links = HREF_RE.findall(raw)
        report = next((l for l in links if l.startswith("/report/")), None)
        ip_asn = _text(cells[3])
        m = re.match(r"([0-9a-fA-F.:]+)\s*#?(\d+)?\s*(.*)", ip_asn)
        rows.append({
            "date": _text(cells[0]),
            "detections": _text(cells[1]),
            "url": _text(cells[2]),
            "ip": m.group(1) if m else ip_asn,
            "asn": ("AS" + m.group(2)) if (m and m.group(2)) else None,
            "asnname": m.group(3).strip() if m else None,
            "report_id": report.split("/")[-1] if report else None,
            "report_url": ("https://urlquery.net" + report) if report else None,
        })
    return rows


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", help="restrict to these targets (repeatable)")
    ap.add_argument("--source", action="append", help="restrict to targets with this source (repeatable)")
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES)
    ap.add_argument("--start-page", type=int, default=0, help="first page index (0-based) to fetch")
    ap.add_argument("--suffix", default="", help="write hits<suffix>.jsonl / totals<suffix>.tsv")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    hits_path = os.path.join(OUT_DIR, f"hits{args.suffix}.jsonl")
    totals_path = os.path.join(OUT_DIR, f"totals{args.suffix}.tsv")
    targets = [t for t in TARGETS if (not args.only or t[0] in args.only) and (not args.source or t[1] in args.source)]
    with open(hits_path, "w") as hits, open(totals_path, "w") as totals:
        totals.write("target\tsource\tkind\trows_kept\tnewest\toldest\tstopped_by\n")
        for term, source, kind in targets:
            seen: set[str] = set()
            kept = 0
            newest = oldest = None
            stopped = "empty_page"
            for page_no in range(args.start_page, args.start_page + args.max_pages):
                page = _fetch(term, page_no * PAGE)
                time.sleep(SLEEP)
                rows = _parse(page)
                if not rows:
                    break
                for row in rows:
                    key = row["report_id"] or (row["date"] + row["url"])
                    if key in seen:
                        continue
                    seen.add(key)
                    row.update({"target": term, "target_source": source})
                    hits.write(json.dumps(redact_obj(row), ensure_ascii=False) + "\n")
                    kept += 1
                    newest = newest or row["date"]
                    oldest = row["date"]
                if term in GENERIC_HOSTS and rows[-1]["date"][:10] < INCIDENT_WINDOW_START:
                    stopped = "before_window"
                    break
                if len(rows) < PAGE:
                    stopped = "last_page"
                    break
            else:
                stopped = "page_cap"
            hits.flush()
            totals.write(f"{term}\t{source}\t{kind}\t{kept}\t{newest}\t{oldest}\t{stopped}\n")
            totals.flush()
            print(f"{term:45} kept={kept:>5} {newest} .. {oldest} ({stopped})", file=sys.stderr)


if __name__ == "__main__":
    main()
