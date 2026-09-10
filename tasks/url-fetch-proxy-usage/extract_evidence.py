#!/usr/bin/env python3
"""Extract per-paste evidence for the url-fetch-proxy-usage task family.

Reads the pastes-by-task classifier output and joins each row against the
matching paste-source revisions.jsonl to recover the body. Emits one TSV
row per paste with proxy-usage columns.
"""

import csv
import json
import os
import re
import sys
from collections import Counter
from urllib.parse import unquote, urlparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TSV_IN = os.path.join(ROOT, "analyses/pastes-by-task/outputs/pastes_by_task.tsv")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
OUT_TSV = os.path.join(OUT_DIR, "evidence.tsv")

TASK_LABEL = "url-fetch-proxy-usage"

SOURCE_TO_REVISIONS = {
    "pastes": os.path.join(ROOT, "agent-logs/pastes/revisions.jsonl"),
    "pastebin-k4be": os.path.join(ROOT, "agent-logs/pastebin-k4be/revisions.jsonl"),
    "anna.fyi": os.path.join(ROOT, "agent-logs/anna.fyi/revisions.jsonl"),
}

PROXY_PATTERNS = [
    ("markdown.new", re.compile(r"markdown\.new", re.I)),
    ("telegra.ph", re.compile(r"telegra\.ph", re.I)),
    ("jqp.vercel.app", re.compile(r"jqp\.vercel\.app", re.I)),
    ("allorigins.hexlet.app", re.compile(r"allorigins\.hexlet\.app", re.I)),
    ("workers.dev", re.compile(r"\.workers\.dev", re.I)),
    ("2md.link", re.compile(r"2md\.link", re.I)),
    ("api.microlink.io", re.compile(r"api\.microlink\.io", re.I)),
    ("md.succ.ai", re.compile(r"md\.succ\.ai", re.I)),
    ("r.jina.ai", re.compile(r"r\.jina\.ai", re.I)),
    ("pure.md", re.compile(r"pure\.md", re.I)),
    ("corsproxy.io", re.compile(r"corsproxy\.io", re.I)),
    ("docs.google.com/viewer", re.compile(r"docs\.google\.com/viewer", re.I)),
    ("cdn.putput.io", re.compile(r"cdn\.putput\.io", re.I)),
]

TARGET_EXTRACTORS = [
    re.compile(r"markdown\.new/(?:https?://)?([a-z0-9.\-]+)", re.I),
    re.compile(r"allorigins\.hexlet\.app/[a-z]+\?url=([^&\s\"'<>]+)"),
    re.compile(r"jqp\.vercel\.app/api/v0\?url=([^&\s\"'<>]+)"),
    re.compile(r"md\.succ\.ai/(https?://[^\s\"'<>]+)"),
    re.compile(r"r\.jina\.ai/(https?://[^\s\"'<>]+)"),
    re.compile(r"\.workers\.dev/\?(https?://[^\s\"'<>]+)"),
    re.compile(r"docs\.google\.com/viewer\?url=(https?://[^&\s\"'<>]+)", re.I),
]

TITLE_SERIES = [
    ("TEL_series", re.compile(r"^TEL\d")),
    ("TK_series", re.compile(r"^TK\d")),
    ("SFTEST_RefQ_series", re.compile(r"^(SFTEST|Ref(Q\d|NX\d?|XY\d?))")),
    ("Ghtml_probe_series", re.compile(r"^G(html|xml|bbcode|markdown|url|latex|php|javascript|robots)\d")),
    ("Proxy_series", re.compile(r"Proxy|ProxyTest|ptest", re.I)),
    ("URLTEST_series", re.compile(r"^URLTEST\d?")),
    ("URLMARK_series", re.compile(r"^URLMARK\d?")),
    ("linktry_series", re.compile(r"linktry", re.I)),
]


def classify_title(title):
    for name, pat in TITLE_SERIES:
        if pat.search(title or ""):
            return name
    return "other"


HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]*\.)+[a-z]{2,}$", re.I)


def target_host(url):
    if url.startswith("http"):
        p = urlparse(url)
        return p.netloc
    if HOST_RE.match(url):
        return url
    return ""


def extract_targets(body):
    hosts = []
    for pat in TARGET_EXTRACTORS:
        for m in pat.finditer(body):
            raw = m.group(1)
            raw = unquote(raw)
            host = target_host(raw)
            if host and host not in ("example.com",):
                hosts.append(host)
    return hosts


def load_target_rows():
    rows = []
    with open(TSV_IN, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row["task"] == TASK_LABEL:
                rows.append(row)
    return rows


def load_bodies(rows):
    wanted = {(r["source"], r["body_sha256"]) for r in rows}
    by_source = {}
    for src, _ in wanted:
        by_source.setdefault(src, set()).add(_)
    bodies = {}
    for src, hashes in by_source.items():
        path = SOURCE_TO_REVISIONS[src]
        with open(path) as f:
            for line in f:
                d = json.loads(line)
                h = d.get("body_sha256")
                if h in hashes and (src, h) not in bodies:
                    bodies[(src, h)] = d
    return bodies


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = load_target_rows()
    bodies = load_bodies(rows)

    out_rows = []
    proxy_counter = Counter()
    target_host_counter = Counter()
    for row in rows:
        rev = bodies.get((row["source"], row["body_sha256"]), {})
        body = rev.get("body") or ""
        proxies = sorted(name for name, pat in PROXY_PATTERNS if pat.search(body))
        proxy_counter.update(proxies)
        target_hosts = extract_targets(body)
        for h in target_hosts:
            target_host_counter[h] += 1
        out_rows.append({
            "time": row["time"],
            "source": row["source"],
            "source_url": row["source_url"],
            "label": row["label"],
            "title": row["title"],
            "title_series": classify_title(row["title"]),
            "body_sha256": row["body_sha256"],
            "body_len": row["body_len"],
            "proxies_matched": ",".join(proxies) if proxies else "",
            "target_hosts": ",".join(sorted(set(target_hosts))),
        })

    out_rows.sort(key=lambda r: (r["time"], r["source"], r["body_sha256"]))
    fieldnames = [
        "time", "source", "source_url", "label", "title", "title_series",
        "body_sha256", "body_len", "proxies_matched", "target_hosts",
    ]
    with open(OUT_TSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    times = [r["time"] for r in out_rows if r["time"]]
    sources = Counter(r["source"] for r in out_rows)
    print(f"pastes: {len(out_rows)}", file=sys.stderr)
    print(f"sources: {dict(sources)}", file=sys.stderr)
    print(f"first_time: {min(times)}", file=sys.stderr)
    print(f"last_time: {max(times)}", file=sys.stderr)
    print(f"proxies (by paste-count): {dict(proxy_counter.most_common())}",
          file=sys.stderr)
    print(f"target hosts (aggregated): {dict(target_host_counter.most_common())}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
