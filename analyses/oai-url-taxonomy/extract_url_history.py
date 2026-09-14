#!/usr/bin/env python3
"""Per-URL history across ALL shards, not just the first shard.

Requirement: `extract_urls.py` only recorded the earliest shard where each URL
appeared. That is not the same as the earliest crawl date, because
  (a) the same URL can appear in later shards whose cached pages were
      crawled EARLIER than the page recorded on the first-shard row;
  (b) the first-shard row may be a researcher writeup whose crawl date
      reflects when the article was crawled, not when the swarm did the
      underlying activity.

This script scans every result row of every shard and records, for each
distinct URL, the full list of (shard, line, cache_age, first_page_url)
sightings. The minimum crawl date across all sightings is the earliest
observable trace of that URL.
"""

import glob
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta

SHARD_GLOB = "/collusionwiki/oai-index-scan/results/shards/*.results.jsonl"
OUT_PATH = "/collusionwiki/analyses/oai-url-taxonomy/outputs/urls_history.jsonl"

# Same credential redactor as extract_urls.py — keep outputs push-safe.
_CRED_PARAMS = (
    "api_key", "apikey", "api\\_key",
    "X-Amz-Credential", "X-Amz-Signature", "X-Amz-Security-Token",
    "AWSAccessKeyId", "aws_access_key_id", "aws_secret_access_key",
    "signature", "access_token", "token", "auth",
)
_CRED_RE = re.compile(
    r"([?&;]|%26|%3B)(" + "|".join(re.escape(p) for p in _CRED_PARAMS) + r")(=|%3D)([^&;#\s]+)",
    re.IGNORECASE,
)
_AKIA_RE = re.compile(r"AKIA[0-9A-Z]{16}")


def redact(url: str) -> str:
    if not url: return url
    url = _CRED_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}REDACTED", url)
    url = _AKIA_RE.sub("AKIAREDACTEDREDACT01", url)
    return url


def parse_cage(s):
    """Approximate timedelta from a cache_age string; None if unknown."""
    if not s:
        return None
    s = s.strip().lower().replace("crawled:", "").strip()
    if s in ("", "(none)", "none"):
        return None
    if s == "today":
        return timedelta(0)
    if s == "yesterday":
        return timedelta(days=1)
    if s == "last week":
        return timedelta(days=7)
    if s == "last month":
        return timedelta(days=30)
    if s == "last year":
        return timedelta(days=365)
    m = re.match(r"(\d+(?:\.\d+)?)\s+(day|days|week|weeks|month|months|year|years)\s+ago", s)
    if not m:
        return None
    n = float(m.group(1))
    unit = m.group(2)
    if unit.startswith("day"):
        return timedelta(days=n)
    if unit.startswith("week"):
        return timedelta(days=n * 7)
    if unit.startswith("month"):
        return timedelta(days=n * 30.44)
    if unit.startswith("year"):
        return timedelta(days=n * 365.25)
    return None


def shard_date(name):
    return datetime.strptime(name.split(".")[0], "%Y-%m-%d")


RESEARCHER_HOSTS = {
    "labs.zenity.io", "news.routley.io", "webofmike.com",
    "metr.org", "aiagentallowlist.com", "www.aiagentallowlist.com",
    "huggingface.co", "cdn.openai.com",
}


def is_researcher(url: str) -> bool:
    try:
        from urllib.parse import urlsplit
        h = urlsplit(url).netloc.lower()
        if h.startswith("www."):
            h = h[4:]
        return h in RESEARCHER_HOSTS
    except Exception:
        return False


def main():
    shards = sorted(glob.glob(SHARD_GLOB))
    print(f"scanning {len(shards)} shards", file=sys.stderr)

    # For each URL: list of dicts describing every sighting
    sightings = defaultdict(list)

    for shard in shards:
        shard_name = os.path.basename(shard)
        sdate = shard_date(shard_name)
        with open(shard) as f:
            for line_no, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                page_url = redact(row.get("page_url", ""))
                cache_age = (row.get("cache_age") or "").strip()
                delta = parse_cage(cache_age)
                crawl_dt = (sdate - delta) if delta is not None else None
                fsq = row.get("first_seen_query", "")
                urls = row.get("urls_in_page") or []
                for u in urls:
                    if not isinstance(u, str):
                        continue
                    u = redact(u)
                    sightings[u].append({
                        "shard": shard_name,
                        "line": line_no,
                        "cache_age": cache_age,
                        "crawl": crawl_dt.strftime("%Y-%m-%d") if crawl_dt else None,
                        "first_page_url": page_url,
                        "fsq": fsq,
                        "is_researcher_page": is_researcher(page_url),
                    })

    print(f"distinct URLs seen: {len(sightings)}", file=sys.stderr)

    with open(OUT_PATH, "w") as out:
        for u, sights in sightings.items():
            # Compute earliest crawl date over ALL sightings, and separately
            # over non-researcher sightings.
            def earliest(pred):
                dates = [s["crawl"] for s in sights if s["crawl"] and pred(s)]
                return min(dates) if dates else None

            earliest_any = earliest(lambda s: True)
            earliest_nonresearcher = earliest(lambda s: not s["is_researcher_page"])
            n_researcher = sum(1 for s in sights if s["is_researcher_page"])

            rec = {
                "url": u,
                "occurrence_count": len(sights),
                "earliest_crawl_any": earliest_any,
                "earliest_crawl_nonresearcher": earliest_nonresearcher,
                "n_researcher_sightings": n_researcher,
                "n_nonresearcher_sightings": len(sights) - n_researcher,
                "first_shard": min(s["shard"] for s in sights),
                "sightings": sights,
            }
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"wrote {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
