#!/usr/bin/env python3
"""Fetch the HTTP transaction list for tier A urlquery reports.

Reads outputs/tier_a.jsonl (written by triage.py) and, for every urlquery
row, calls /api/htmx/report/<id>/filter/http with the htmx headers the
report page uses. Writes outputs/urlquery/transactions.jsonl with one row per
report: the list of transactions (method, url, ip, status, size, requester,
file type, times seen, sha256).

Why this matters: a search row shows only the URL that was submitted. The
transaction list shows what the scanner actually fetched behind the wrapper
and whether the proxy returned the data (status 200 with a non-trivial size)
or failed. Reports are fetched newest first up to --limit.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from redact import redact_obj  # noqa: E402
OUT = os.path.join(HERE, "outputs")
UA = "Mozilla/5.0 (X11; Linux x86_64) collusionwiki-research/0.1"
SLEEP = 1.5

ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
TAG_RE = re.compile(r"<[^>]+>")


def _text(x: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", x))).strip()


def _field(blob: str, label: str) -> str | None:
    m = re.search(re.escape(label) + r"\s+(\S+)", blob)
    return m.group(1) if m else None


def fetch(report_id: str) -> str:
    url = f"https://urlquery.net/api/htmx/report/{report_id}/filter/http"
    ref = f"https://urlquery.net/report/{report_id}"
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,*/*", "HX-Request": "true",
        "HX-Current-URL": ref, "Referer": ref})
    for _ in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} for {report_id}", file=sys.stderr)
            if e.code == 404:
                return ""
            time.sleep(15)
        except Exception as ex:
            print(f"  error {ex!r}", file=sys.stderr)
            time.sleep(15)
    return ""


def parse(page: str) -> list[dict]:
    out = []
    rows = ROW_RE.findall(page)
    i = 0
    while i < len(rows):
        cells = CELL_RE.findall(rows[i])
        txt = [_text(c) for c in cells]
        if len(txt) >= 5 and re.match(r"(GET|POST|HEAD|PUT)\s", txt[1]):
            method, url = txt[1].split(" ", 1)
            detail = _text(rows[i + 1]) if i + 1 < len(rows) else ""
            out.append({
                "method": method, "url": url, "ip": txt[2], "status": txt[3], "size": txt[4],
                "user_request": "User Request" in detail,
                "requested_by": _field(detail, "Requested by"),
                "file_type": (re.search(r"File type\s+(.+?)\s+First Seen", detail) or [None, None])[1],
                "times_seen": _field(detail, "Times Seen"),
                "sha256": _field(detail, "SHA256"),
            })
            i += 2
        else:
            i += 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--per-host", type=int, default=5)
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(os.path.join(OUT, "tier_a.jsonl"))]
    rows = [r for r in rows if r["source"] == "urlquery" and r.get("id")]
    rows.sort(key=lambda r: r["time"], reverse=True)
    # Spread the budget across innermost hosts: up to --per-host newest
    # reports per base host first, then fill the remainder newest-first.
    per_host: dict[str, int] = {}
    chosen, rest = [], []
    for r in rows:
        k = r.get("base_host") or r.get("page_host") or ""
        if per_host.get(k, 0) < args.per_host:
            per_host[k] = per_host.get(k, 0) + 1
            chosen.append(r)
        else:
            rest.append(r)
    rows = (chosen + rest)[: args.limit]
    dest = os.path.join(OUT, "urlquery", "transactions.jsonl")
    done = set()
    if os.path.exists(dest):
        for l in open(dest):
            done.add(json.loads(l)["report_id"])
    with open(dest, "a") as f:
        for n, r in enumerate(rows, 1):
            if r["id"] in done:
                continue
            page = fetch(r["id"])
            time.sleep(SLEEP)
            tx = parse(page)
            f.write(json.dumps(redact_obj({"report_id": r["id"], "time": r["time"], "url": r["url"],
                                           "n_transactions": len(tx), "transactions": tx}), ensure_ascii=False) + "\n")
            f.flush()
            if n % 25 == 0:
                print(f"{n}/{len(rows)}", file=sys.stderr)


if __name__ == "__main__":
    main()
