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

# Sources scanned, in dedup-priority order (earlier wins on body_sha256 clash).
#
# prowiki: primary swarm corpus; bodies do not overlap with paste corpora.
# Wikis (apchem/wiki4d/ludism/milkwiki/texteditors): sister wiki exports —
#   distinct bodies from prowiki. `agent-logs/probier/` is deliberately
#   omitted because the same wiki is already covered by the prowiki export.
# Per-site paste scrapes: authoritative per-host scrapes; supersede the
#   corresponding slices in `pastes/` and `pastebin-k4be`/`paste-linuxiarz`
#   are the fuller re-scrapes for those two hosts.
# `pastes/`: catch-all shellac aggregate; some rows are re-emissions of the
#   per-site scrape rows and get filtered by body_sha256 dedup.
# `gems/`: 12 Ruby-gem READMEs; 1 URL.
# `shorteners/`: 4,285 URLs but every row has `time = null` — skipped from
#   this extract to avoid a giant undated bucket. Included as text in the
#   downstream chart's pre-window totals if desired.
SOURCES: list[tuple[str, Path]] = [
    ("prowiki",                REPO_ROOT / "agent-logs" / "prowiki"                / "revisions.jsonl"),
    ("apchem",                 REPO_ROOT / "agent-logs" / "apchem"                 / "revisions.jsonl"),
    ("wiki4d",                 REPO_ROOT / "agent-logs" / "wiki4d"                 / "revisions.jsonl"),
    ("ludism",                 REPO_ROOT / "agent-logs" / "ludism"                 / "revisions.jsonl"),
    ("milkwiki",               REPO_ROOT / "agent-logs" / "milkwiki"               / "revisions.jsonl"),
    ("texteditors",            REPO_ROOT / "agent-logs" / "texteditors"            / "revisions.jsonl"),
    ("anna.fyi",               REPO_ROOT / "agent-logs" / "anna.fyi"               / "revisions.jsonl"),
    ("pastebin-k4be",          REPO_ROOT / "agent-logs" / "pastebin-k4be"          / "revisions.jsonl"),
    ("paste-linuxiarz",        REPO_ROOT / "agent-logs" / "paste-linuxiarz"        / "revisions.jsonl"),
    ("popcat-wayback",         REPO_ROOT / "agent-logs" / "popcat-wayback"         / "revisions.jsonl"),
    ("paste.steamr.com",       REPO_ROOT / "agent-logs" / "paste.steamr.com"       / "revisions.jsonl"),
    ("paste.smirky.net",       REPO_ROOT / "agent-logs" / "paste.smirky.net"       / "revisions.jsonl"),
    ("pastebin.tarcseh.me",    REPO_ROOT / "agent-logs" / "pastebin.tarcseh.me"    / "revisions.jsonl"),
    ("pastebin.faster-it.de",  REPO_ROOT / "agent-logs" / "pastebin.faster-it.de"  / "revisions.jsonl"),
    ("pastebin.freepbx.org",   REPO_ROOT / "agent-logs" / "pastebin.freepbx.org"   / "revisions.jsonl"),
    ("pb.dynavirt.com",        REPO_ROOT / "agent-logs" / "pb.dynavirt.com"        / "revisions.jsonl"),
    ("pb.psychotic.ninja",     REPO_ROOT / "agent-logs" / "pb.psychotic.ninja"     / "revisions.jsonl"),
    ("pastie.iem.at",          REPO_ROOT / "agent-logs" / "pastie.iem.at"          / "revisions.jsonl"),
    ("paste.centos.org",       REPO_ROOT / "agent-logs" / "paste.centos.org"       / "revisions.jsonl"),
    ("paste.lightcast.com",    REPO_ROOT / "agent-logs" / "paste.lightcast.com"    / "revisions.jsonl"),
    ("p.gaa.st",               REPO_ROOT / "agent-logs" / "p.gaa.st"               / "revisions.jsonl"),
    ("pastes",                 REPO_ROOT / "agent-logs" / "pastes"                 / "revisions.jsonl"),
    ("gems",                   REPO_ROOT / "agent-logs" / "gems"                   / "revisions.jsonl"),
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
    dedup_skipped: Counter[str] = Counter()
    # Cross-corpus dedup: if a body_sha256 was already seen in a *different*
    # source, skip it here. Intra-corpus duplicates (two revisions of the same
    # page with unchanged content) are kept — those are legitimate re-saves.
    first_source_for_sha: dict[str, str] = {}
    with OUT_JSONL.open("w", encoding="utf-8") as wf:
        for source, path in SOURCES:
            if not path.exists():
                print(f"warn: missing {path}", file=sys.stderr)
                continue
            n_rows = 0
            n_skipped = 0
            with path.open("r", encoding="utf-8") as rf:
                for line in rf:
                    n_rows += 1
                    rev = json.loads(line)
                    body = rev.get("body") or ""
                    sha = rev.get("body_sha256") or ""
                    if sha:
                        first = first_source_for_sha.get(sha)
                        if first is None:
                            first_source_for_sha[sha] = source
                        elif first != source:
                            n_skipped += 1
                            continue
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
            dedup_skipped[source] = n_skipped
            print(f"  {source:24s} rev={n_rows:6d}  urls={per_source[source]:6d}"
                  f"  dedup_skipped={n_skipped}", file=sys.stderr)

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
