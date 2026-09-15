#!/usr/bin/env python3
"""Harvest urlscan.io search hits for every target in targets.py.

Writes:
  outputs/urlscan/hits.jsonl   one row per (target, scan) pair
  outputs/urlscan/totals.tsv   per-target all-time total, window total, rows kept

urlscan's search endpoint answers without an API key at 30 requests per
minute per IP. The result endpoint (full request list) needs a login, so this
script keeps only the search-hit metadata: task URL, page URL, page IP/ASN,
scan time, visibility, and the result link.

Pagination uses `search_after` with the `sort` pair of the last row.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from targets import TARGETS, GENERIC_HOSTS, INCIDENT_WINDOW_START  # noqa: E402
from redact import redact_obj  # noqa: E402

OUT_DIR = os.path.join(HERE, "outputs", "urlscan")
UA = "collusionwiki-research/0.1"
BASE = "https://urlscan.io/api/v1/search/"
PAGE = 100
CAP_PER_TARGET = 1000
SLEEP = 2.2  # 30/min limit; leave headroom


def _get(params: dict) -> dict:
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("x-rate-limit-reset-after", "60")) + 2
                print(f"  429; sleeping {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            body = e.read().decode("utf-8", "replace")[:200]
            print(f"  HTTP {e.code} for {url}: {body}", file=sys.stderr)
            if e.code in (400, 404):
                return {"results": [], "total": -1, "has_more": False, "error": body}
            time.sleep(10)
        except Exception as ex:  # network hiccup
            print(f"  error {ex!r}; retrying", file=sys.stderr)
            time.sleep(10)
    return {"results": [], "total": -1, "has_more": False, "error": "gave up"}


def _query_for(term: str, kind: str) -> str:
    if kind == "host":
        return f"domain:{term}"
    return f'(page.url:"{term}" OR task.url:"{term}")'


def _row(target: str, source: str, r: dict) -> dict:
    t, p, s = r.get("task", {}), r.get("page", {}), r.get("stats", {})
    return {
        "target": target,
        "target_source": source,
        "scan_id": r.get("_id"),
        "time": t.get("time"),
        "task_url": t.get("url"),
        "page_url": p.get("url"),
        "page_domain": p.get("domain"),
        "page_apex": p.get("apexDomain"),
        "page_ip": p.get("ip"),
        "page_asn": p.get("asn"),
        "page_asnname": p.get("asnname"),
        "page_country": p.get("country"),
        "page_server": p.get("server"),
        "page_status": p.get("status"),
        "page_title": p.get("title"),
        "visibility": t.get("visibility"),
        "method": t.get("method"),
        "n_requests": s.get("requests"),
        "n_uniq_ips": s.get("uniqIPs"),
        "result_url": r.get("result"),
    }


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", help="restrict to these targets (repeatable)")
    ap.add_argument("--suffix", default="", help="write hits<suffix>.jsonl / totals<suffix>.tsv")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    hits_path = os.path.join(OUT_DIR, f"hits{args.suffix}.jsonl")
    totals_path = os.path.join(OUT_DIR, f"totals{args.suffix}.tsv")
    targets = [t for t in TARGETS if not args.only or t[0] in args.only]
    seen: set[tuple[str, str]] = set()
    with open(hits_path, "w") as hits, open(totals_path, "w") as totals:
        totals.write("target\tsource\tkind\tquery\tall_time_total\twindow_query\twindow_total\trows_kept\n")
        for term, source, kind in targets:
            q = _query_for(term, kind)
            head = _get({"q": q, "size": 1})
            time.sleep(SLEEP)
            all_total = head.get("total", -1)
            windowed = term in GENERIC_HOSTS or (all_total is not None and all_total > CAP_PER_TARGET)
            wq = f"{q} AND date:>={INCIDENT_WINDOW_START}" if windowed else q
            kept = 0
            window_total = all_total
            search_after = None
            while kept < CAP_PER_TARGET:
                params = {"q": wq, "size": PAGE}
                if search_after:
                    params["search_after"] = search_after
                d = _get(params)
                time.sleep(SLEEP)
                if windowed and search_after is None:
                    window_total = d.get("total", -1)
                rows = d.get("results", [])
                if not rows:
                    break
                for r in rows:
                    key = (term, r.get("_id"))
                    if key in seen:
                        continue
                    seen.add(key)
                    hits.write(json.dumps(redact_obj(_row(term, source, r)), ensure_ascii=False) + "\n")
                    kept += 1
                    if kept >= CAP_PER_TARGET:
                        break
                if not d.get("has_more"):
                    break
                last = rows[-1].get("sort")
                if not last:
                    break
                search_after = ",".join(str(x) for x in last)
            hits.flush()
            totals.write(f"{term}\t{source}\t{kind}\t{q}\t{all_total}\t{wq}\t{window_total}\t{kept}\n")
            totals.flush()
            print(f"{term:45} all={all_total:>7} window={window_total:>7} kept={kept}", file=sys.stderr)


if __name__ == "__main__":
    main()
