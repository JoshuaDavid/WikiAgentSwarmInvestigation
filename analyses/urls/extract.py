#!/usr/bin/env python3
"""Extract every URL occurrence from revision bodies in prowiki, pastes, gems."""

from __future__ import annotations
import json
import re
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUT_DIR = HERE / "outputs"
OUT_JSONL = OUT_DIR / "urls.jsonl"
OUT_HOSTS_TSV = OUT_DIR / "urls-by-host.tsv"

SOURCES: list[tuple[str, Path]] = [
    ("prowiki", REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"),
    ("pastes",  REPO_ROOT / "agent-logs" / "pastes"  / "revisions.jsonl"),
    ("gems",    REPO_ROOT / "agent-logs" / "gems"    / "revisions.jsonl"),
]

URL_RE = re.compile(r"https?://[^\s<>\]\"'`|{}\\]+", re.IGNORECASE)
TRAILING_STRIP = ".,;:!?'\")"

def normalize(url: str) -> str:
    while url and url[-1] in TRAILING_STRIP:
        url = url[:-1]
    return url

def extract_host(url: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(url)
        return (parsed.hostname or "").lower()
    except ValueError:
        return ""

def scheme_of(url: str) -> str:
    lower = url.lower()
    if lower.startswith("https://"):
        return "https"
    if lower.startswith("http://"):
        return "http"
    return "?"


def main() -> None:
    n_urls = 0
    host_counter: Counter[str] = Counter()
    per_source: Counter[str] = Counter()
    with OUT_JSONL.open("w", encoding="utf-8") as wf:
        for source, path in SOURCES:
            if not path.exists():
                print(f"warn: missing {path}", file=sys.stderr)
                continue
            n_rows = 0
            with path.open("r", encoding="utf-8") as rf:
                for line in rf:
                    n_rows += 1
                    rev = json.loads(line)
                    body = rev.get("body") or ""
                    if "http" not in body.lower():
                        continue
                    for m in URL_RE.finditer(body):
                        raw = normalize(m.group(0))
                        if not raw or "://" not in raw:
                            continue
                        host = extract_host(raw)
                        if not host:
                            continue
                        rec = {
                            "url": raw,
                            "host": host,
                            "scheme": scheme_of(raw),
                            "source": source,
                            "rev_id": rev.get("rev_id"),
                            "page_id": rev.get("page_id"),
                            "wiki": rev.get("wiki"),
                            "label": rev.get("label"),
                            "ip16": rev.get("ip16"),
                            "time": rev.get("time"),
                            "offset": m.start(),
                        }
                        wf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        host_counter[host] += 1
                        per_source[source] += 1
                        n_urls += 1
            print(f"  {source}: {n_rows} revisions, {per_source[source]} URLs",
                  file=sys.stderr)

    with OUT_HOSTS_TSV.open("w", encoding="utf-8") as hf:
        hf.write("host\turl_occurrences\n")
        for host, count in host_counter.most_common():
            hf.write(f"{host}\t{count}\n")

    print(f"URL occurrences: {n_urls}", file=sys.stderr)
    print(f"distinct hosts: {len(host_counter)}", file=sys.stderr)
    print(f"wrote {OUT_JSONL}", file=sys.stderr)
    print(f"wrote {OUT_HOSTS_TSV}", file=sys.stderr)

if __name__ == "__main__":
    main()
