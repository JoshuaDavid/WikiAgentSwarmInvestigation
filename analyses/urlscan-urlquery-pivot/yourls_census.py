#!/usr/bin/env python3
"""Census of YOURLS instances and keywords seen in the harvested scans.

YOURLS is the self-hosted shortener the swarm used to park links (bitily.in,
vanderbi.lt, yourls.pro, 2dd.pl, ...). Every YOURLS install exposes two
things without login: the API at ``/yourls-api.php`` and a public stats page
at ``/<keyword>+`` that prints the long URL, the creation timestamp, the
click count and the top referrers. The creation timestamp is submitter-side
time, which no scanner row gives us.

This script:
  1. reads outputs/rows.jsonl and outputs/wayback/hits.jsonl, keeps every URL
     whose path looks like YOURLS (``yourls-api.php``, ``/admin/``,
     ``/<keyword>+``), and groups them by host;
  2. for every (host, keyword) pair, fetches ``https://<host>/<keyword>+``
     once, parses the stats page, and records what it says;
  3. writes outputs/yourls/instances.tsv and outputs/yourls/keywords.jsonl.

Fetches are read-only GETs, one per second, capped by --limit.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import glob
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
from redact import redact_obj  # noqa: E402

OUT = os.path.join(HERE, "outputs")
DEST = os.path.join(OUT, "yourls")
UA = "collusionwiki-research/0.1"
SLEEP = 1.0
INCIDENT_START = "2026-03-01"

API_RE = re.compile(r"yourls-api\.php", re.I)
ADMIN_RE = re.compile(r"/admin/(?:index|tools|plugins|info)\.php", re.I)
STATS_RE = re.compile(r"^/([A-Za-z0-9_\-]{1,64})\+$")
KEYWORD_PARAM_RE = re.compile(r"[?&](?:keyword|shorturl)=([A-Za-z0-9_\-]{1,64})", re.I)
KNOWN_YOURLS = {"bitily.in", "app.bitily.in", "vanderbi.lt", "yourls.pro", "yourls.shop",
                "yourls.website", "yourls.space", "yourls.biz", "yourls.pl", "goto.unm.edu",
                "uoft.me", "u.ethz.ch", "rmn.re", "lnkr.click", "2dd.pl", "t.mdcdev.me",
                "url.popcat.xyz", "kodak.love", "zapro.si", "klickhier.at", "sho.rt",
                "ativar.abre.bio", "easylinkref.com", "linkrutgon.net"}


def _host(u: str) -> str:
    h = urllib.parse.urlsplit(u).netloc.lower().split("@")[-1].split(":")[0]
    return h[4:] if h.startswith("www.") else h


def collect() -> dict[str, dict]:
    inst: dict[str, dict] = {}
    urls: list[tuple[str, str, str]] = []
    for p in glob.glob(os.path.join(OUT, "rows.jsonl")):
        for l in open(p):
            d = json.loads(l)
            urls.append((d["url"], d["time"], d["source"]))
    for p in glob.glob(os.path.join(OUT, "wayback", "hits.jsonl")):
        for l in open(p):
            d = json.loads(l)
            urls.append((d["url"], d["timestamp"], "wayback"))
    for u, t, src in urls:
        uu = u if u.lower().startswith(("http://", "https://")) else "https://" + u
        sp = urllib.parse.urlsplit(uu)
        h = _host(uu)
        if not h:
            continue
        is_api, is_admin = bool(API_RE.search(sp.path)), bool(ADMIN_RE.search(sp.path))
        m = STATS_RE.match(sp.path)
        kw = m.group(1) if m else None
        km = KEYWORD_PARAM_RE.search(sp.query)
        if km:
            kw = kw or km.group(1)
        if not (is_api or is_admin or kw or h in KNOWN_YOURLS):
            continue
        e = inst.setdefault(h, {"host": h, "rows": 0, "api": 0, "admin": 0, "keywords": collections.Counter(),
                                "first": t, "last": t, "sources": set()})
        e["rows"] += 1; e["api"] += is_api; e["admin"] += is_admin; e["sources"].add(src)
        e["first"] = min(e["first"], t); e["last"] = max(e["last"], t)
        if kw:
            e["keywords"][kw] += 1
        elif h in KNOWN_YOURLS and sp.path.count("/") == 1 and re.fullmatch(r"/[A-Za-z0-9_\-]{1,64}", sp.path):
            e["keywords"][sp.path[1:]] += 1
    return inst


def fetch_stats(host: str, keyword: str) -> dict:
    url = f"https://{host}/{urllib.parse.quote(keyword)}+"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    out = {"host": host, "keyword": keyword, "stats_url": url}
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            out["http"] = r.status
            chunks, deadline = [], time.monotonic() + 20
            while time.monotonic() < deadline and sum(len(c) for c in chunks) < 300_000:
                c = r.read(32_768)
                if not c:
                    break
                chunks.append(c)
            body = b"".join(chunks).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        out["http"] = e.code
        return out
    except Exception as ex:
        out["http"] = None; out["error"] = repr(ex)[:120]
        return out
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    text = re.sub(r"\s+", " ", text)
    out["is_yourls"] = ("YOURLS" in body) or ("yourls" in body.lower())
    m = re.search(r"(?:Long URL|Original URL)[:\s]+(https?://\S+)", text)
    out["long_url"] = m.group(1) if m else None
    m = re.search(r"(?:Short URL created on|Created on|created)[:\s]+([A-Za-z]+ \d{1,2},? \d{4}(?: @ [\d:]+ ?[ap]?m?)?|\d{4}-\d{2}-\d{2}[ T][\d:]+)", text)
    out["created"] = m.group(1) if m else None
    m = re.search(r"(\d[\d,]*) (?:clicks?|hits?)\b", text)
    out["clicks"] = m.group(1) if m else None
    m = re.search(r"Top 5 referrers?(.{0,300})", text)
    out["referrers"] = m.group(1).strip()[:300] if m else None
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=150, help="max stats pages to fetch")
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()
    os.makedirs(DEST, exist_ok=True)
    inst = collect()
    with open(os.path.join(DEST, "instances.tsv"), "w") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["host", "rows", "api_rows", "admin_rows", "distinct_keywords", "first", "last", "sources", "top_keywords"])
        for e in sorted(inst.values(), key=lambda e: -e["rows"]):
            w.writerow([e["host"], e["rows"], e["api"], e["admin"], len(e["keywords"]), e["first"][:16], e["last"][:16],
                        ",".join(sorted(e["sources"])), "; ".join(f"{k} ({n})" for k, n in e["keywords"].most_common(8))])
    print(f"{len(inst)} candidate YOURLS hosts", file=sys.stderr)
    if args.no_fetch:
        return
    # Round-robin across hosts, swarm-window hosts first, and give up on a
    # host after two consecutive 404s so a dead instance with many keywords
    # does not eat the budget.
    order = sorted(inst.values(), key=lambda e: (e["last"] < INCIDENT_START, -e["rows"]))
    queues = {e["host"]: [k for k, _ in e["keywords"].most_common(12)] for e in order}
    dead: dict[str, int] = collections.Counter()
    fetched = 0
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    with open(os.path.join(DEST, "keywords.jsonl"), "w") as f:
        while fetched < args.limit and any(queues.values()):
            progressed = False
            for e in order:
                h = e["host"]
                if not queues[h] or dead[h] >= 2 or fetched >= args.limit:
                    continue
                k = queues[h].pop(0)
                # DNS resolution is not covered by socket timeouts, so the
                # fetch runs in a worker thread with a hard deadline.
                progressed = True
                fut = pool.submit(fetch_stats, h, k)
                try:
                    row = fut.result(timeout=30)
                except concurrent.futures.TimeoutError:
                    row = {"host": h, "keyword": k, "stats_url": f"https://{h}/{k}+", "http": None, "error": "timeout"}
                time.sleep(SLEEP)
                fetched += 1
                dead[h] = dead[h] + 1 if row.get("http") in (404, None) else 0
                f.write(json.dumps(redact_obj(row), ensure_ascii=False) + "\n")
                f.flush()
                print(f"{h:28} {k:28} http={row.get('http')} yourls={row.get('is_yourls')} created={row.get('created')} clicks={row.get('clicks')}", file=sys.stderr)
            if not progressed:
                break  # every host with keywords left is dead


if __name__ == "__main__":
    main()
