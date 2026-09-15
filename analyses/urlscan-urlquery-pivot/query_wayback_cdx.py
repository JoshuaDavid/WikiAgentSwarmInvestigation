#!/usr/bin/env python3
"""Pull Wayback Machine capture lists for the wrapper and shortener hosts.

A capture of a wrapper URL such as ``md.succ.ai/https://www.sec.gov/...``
exists only if someone asked the Wayback Machine to save it. The agents used
web.archive.org (209 URL occurrences in the wiki corpus, many with the
``id_`` replay flag), so captures inside the incident window are candidate
agent activity with a second-resolution timestamp.

Writes:
  outputs/wayback/hits.jsonl   one row per capture: timestamp, url, status,
                               mimetype, length, digest, target
  outputs/wayback/totals.tsv   per-target capture count and date span

The CDX API is ``https://web.archive.org/cdx/search/cdx``. One request per
target, ``from=2026-02`` onward, up to CAP rows, one request per second.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from redact import redact_obj  # noqa: E402

OUT_DIR = os.path.join(HERE, "outputs", "wayback")
UA = "collusionwiki-research/0.1"
CDX = "https://web.archive.org/cdx/search/cdx"
CAP = 5000
SLEEP = 1.0

# Hosts whose Wayback history is dominated by the swarm's window, or where a
# capture of any URL is interesting. Prefix match on the host.
HOSTS = [
    "md.succ.ai", "markdown.new", "pure.md", "jqp.vercel.app", "proxymule.com",
    "cors.bwa.workers.dev", "cors.ripka.workers.dev", "api.cors.lol", "corsmirror.com",
    "test.cors.workers.dev", "proxy.corsfix.com", "md.dhr.wtf", "webcrawlerapi.com",
    "markdown.microlink.io", "text.microlink.io", "html.microlink.io",
    "allorigins.hexlet.app", "api.allorigins.win", "cors.hypnguyen.workers.dev",
    "cloudflare-cors-anywhere.hanpengchen.workers.dev", "cors-get-proxy.sirjosh.workers.dev",
    "platform.lemino.ai", "httpbingo.org", "httpbun.com", "deelay.me",
    "vanderbi.lt", "bitily.in", "app.bitily.in", "yourls.pro", "yourls.shop",
    "yourls.website", "yourls.space", "yourls.biz", "yourls.pl", "goto.unm.edu",
    "uoft.me", "u.ethz.ch", "rmn.re", "lnkr.click", "2dd.pl", "t.mdcdev.me",
    "url.popcat.xyz", "kodak.love", "zapro.si", "klickhier.at",
    "api.counterapi.dev", "countapi.mileshilliard.com",
    "wikiservice.at", "tmcleod.org", "texteditors.org", "usemod.org",
    "netzwerkgegengewalt.org", "schulwiki.org", "dorfwiki.org",
    "thrill-data.com", "whssgr.com", "whssgrgupkar.com", "whstrustpkl.com",
]

# Hosts with a large unrelated history. Only captures whose path carries a
# wrapped URL or the swarm's data endpoints are pulled.
PATH_TARGETS = [
    ("r.jina.ai", "r.jina.ai/http*"),
    ("httpbin.org", "httpbin.org/base64/*"),
    ("eu.httpbin.org", "eu.httpbin.org/base64/*"),
    ("api.microlink.io", "api.microlink.io/?url=*"),
    ("web.archive.org", "web.archive.org/web/*id_/https://www.sec.gov/files/county.json*"),
    ("sec.gov", "www.sec.gov/files/county.json*"),
    ("investor.gov", "www.investor.gov/files/county.json*"),
    ("data.idph.state.ia.us", "data.idph.state.ia.us/t/IDPH-DataViz/*"),
    ("viz.aihw.gov.au", "viz.aihw.gov.au/t/Public/views/PBS*"),
    ("vizhub.healthdata.org", "vizhub.healthdata.org/lbd/api/*"),
    ("api.datausa.io", "api.datausa.io/tesseract/*"),
]


def fetch(url_pattern: str, since: str) -> list[list[str]]:
    params = {
        "url": url_pattern, "matchType": "prefix" if url_pattern.endswith("*") else "prefix",
        "from": since, "output": "json", "limit": CAP,
        "fl": "timestamp,original,statuscode,mimetype,length,digest",
    }
    q = CDX + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(q, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read().decode("utf-8", "replace")
            if not body.strip():
                return []
            data = json.loads(body)
            return data[1:] if data and data[0] and data[0][0] == "timestamp" else data
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(30 * (attempt + 1))
                continue
            print(f"  HTTP {e.code} for {url_pattern}", file=sys.stderr)
            return []
        except Exception as ex:
            print(f"  error {ex!r} for {url_pattern}; retrying", file=sys.stderr)
            time.sleep(15)
    return []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="202602")
    ap.add_argument("--only", action="append")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    targets = [(h, h.rstrip("/") + "/*") for h in HOSTS] + PATH_TARGETS
    if args.only:
        targets = [t for t in targets if t[0] in args.only]
    with open(os.path.join(OUT_DIR, "hits.jsonl"), "w") as hits, open(os.path.join(OUT_DIR, "totals.tsv"), "w") as totals:
        totals.write("target\tpattern\tcaptures\tfirst\tlast\n")
        for target, pattern in targets:
            rows = fetch(pattern, args.since)
            time.sleep(SLEEP)
            ts = [r[0] for r in rows]
            for r in rows:
                hits.write(json.dumps(redact_obj({
                    "target": target, "timestamp": r[0], "url": r[1], "status": r[2],
                    "mimetype": r[3], "length": r[4], "digest": r[5],
                }), ensure_ascii=False) + "\n")
            hits.flush()
            totals.write(f"{target}\t{pattern}\t{len(rows)}\t{min(ts) if ts else ''}\t{max(ts) if ts else ''}\n")
            totals.flush()
            print(f"{target:45} captures={len(rows):>5} {min(ts) if ts else '':>14} .. {max(ts) if ts else ''}", file=sys.stderr)


if __name__ == "__main__":
    main()
