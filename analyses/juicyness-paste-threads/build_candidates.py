#!/usr/bin/env python3
"""Cluster paste-host revisions into thread candidates.

The unit of analysis in this pass is a **thread**, not a single paste. A
thread is a set of pastes that reference each other via shared titles,
`@handle` mentions, `paste <shortid>` body references, or `title X` /
`under X` body references, and that fall within a bounded time span.

Reads   agent-logs/paste-<host>/revisions.jsonl for each host in HOSTS.
Writes  outputs/candidates.jsonl (one JSON per cluster).
"""

from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "agent-logs"
OUT = Path(__file__).resolve().parent / "outputs" / "candidates.jsonl"

HOSTS = ["paste-linuxiarz"]

MIN_BODY_LEN = 30
MIN_CLUSTER_SIZE = 5
MAX_INTER_PASTE_GAP_HOURS = 4
HOT_TITLE_MIN_COUNT = 3
STOP_TITLE_WORDS = {"untitled", "filler", "test", "re", ""}

AT_RE = re.compile(r"@(agent[-\w]+)", re.I)
PASTE_ID_RE = re.compile(r"paste[- ]([0-9a-f]{6,12})", re.I)
TITLE_REF_RE = re.compile(
    r"(?:title|under|reply title|search title)\s+([A-Z][A-Za-z0-9]{4,})",
)
TITLE_PREFIX_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]*)")


class UnionFind:
    def __init__(self, keys):
        self.p = {k: k for k in keys}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def load_host(host):
    p = LOG_DIR / host / "revisions.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l]


def keep_paste(r):
    body = r.get("body") or ""
    if r.get("time") and len(body) >= MIN_BODY_LEN:
        return True
    if AT_RE.search(body):
        return True
    return False


def title_prefix(title):
    m = TITLE_PREFIX_RE.match(title or "")
    if not m:
        return None
    w = m.group(1)
    if w.lower() in STOP_TITLE_WORDS:
        return None
    return w


def cluster(rows):
    """Return list[list[row]] of clusters.

    Edges:
    1. Same hot title prefix.
    2. Same exact source_title (any repeat).
    3. Body of paste A contains `@<label>` where label == label of paste B.
    4. Body of paste A contains a short paste-id that matches paste B's name.
    5. Body of paste A contains "title X" or "under X" where X == title of B.
    """
    kept = [r for r in rows if keep_paste(r)]
    ids = [r["page_id"] for r in kept]
    by_id = {r["page_id"]: r for r in kept}
    uf = UnionFind(ids)

    # --- edge type 1 + 2: title prefix / exact title / coarse topic word ---
    # We want two granularities:
    #  a) The full first alpha-word ("IowaCollabReply"). Merges obvious sibs.
    #  b) The first 4 alphabetical characters of the title, case-insensitive
    #     ("iowa"). Merges follow-up titles like `IowaQ5LabelConfirmed` or
    #     `IowaPostFinalThanks` that appear after the initial coordination
    #     titles have run their course.
    # Both are gated on hotness so single-off titles don't glue everything
    # together.
    def coarse_topic(t):
        t = re.sub(r"[^A-Za-z]", "", t or "")[:4].lower()
        return t if len(t) == 4 else None

    prefix_counts = Counter(title_prefix(r.get("source_title")) for r in kept)
    coarse_counts = Counter(coarse_topic(r.get("source_title")) for r in kept)
    hot_prefixes = {
        p for p, c in prefix_counts.items() if p and c >= HOT_TITLE_MIN_COUNT
    }
    hot_coarse = {
        c for c, n in coarse_counts.items()
        if c and n >= HOT_TITLE_MIN_COUNT and c not in STOP_TITLE_WORDS
    }
    by_prefix = defaultdict(list)
    by_coarse = defaultdict(list)
    by_exact_title = defaultdict(list)
    for r in kept:
        pfx = title_prefix(r.get("source_title"))
        if pfx and pfx in hot_prefixes:
            by_prefix[pfx].append(r["page_id"])
        cc = coarse_topic(r.get("source_title"))
        if cc and cc in hot_coarse:
            by_coarse[cc].append(r["page_id"])
        t = (r.get("source_title") or "").strip()
        if t and t.lower() not in STOP_TITLE_WORDS:
            by_exact_title[t].append(r["page_id"])
    groups_to_union = (
        list(by_prefix.values())
        + list(by_coarse.values())
        + list(by_exact_title.values())
    )
    for group in groups_to_union:
        if len(group) < 2:
            continue
        anchor = group[0]
        for other in group[1:]:
            uf.union(anchor, other)

    # --- edge type 3: @<label> matches another paste's label ---
    by_label = defaultdict(list)
    for r in kept:
        lab = (r.get("label") or "").lower()
        if lab:
            by_label[lab].append(r["page_id"])
    for r in kept:
        body = r.get("body") or ""
        for m in AT_RE.findall(body):
            for other in by_label.get(m.lower(), []):
                uf.union(r["page_id"], other)

    # --- edge type 4: `paste <shortid>` body references ---
    by_short = defaultdict(list)
    for r in kept:
        name = r.get("name") or ""
        # `name` on paste-linuxiarz is the 8-char hex slug
        for k in (name, name[:8], name[:6]):
            if k:
                by_short[k].append(r["page_id"])
    for r in kept:
        body = r.get("body") or ""
        for m in PASTE_ID_RE.findall(body):
            for other in by_short.get(m.lower(), []):
                if other != r["page_id"]:
                    uf.union(r["page_id"], other)

    # --- edge type 5: `title X` / `under X` where X matches another title ---
    for r in kept:
        body = r.get("body") or ""
        for m in TITLE_REF_RE.findall(body):
            for other in by_exact_title.get(m, []):
                if other != r["page_id"]:
                    uf.union(r["page_id"], other)

    # collect clusters, then apply time-gap split
    groups = defaultdict(list)
    for pid in ids:
        groups[uf.find(pid)].append(by_id[pid])

    clusters = []
    for members in groups.values():
        if len(members) < MIN_CLUSTER_SIZE:
            continue
        # split on inter-paste gap; treat timeless pastes as attached to
        # the nearest previous timed paste
        members.sort(key=lambda r: r.get("time") or "")
        segments = [[]]
        last_time = None
        gap_s = MAX_INTER_PASTE_GAP_HOURS * 3600
        for r in members:
            t = r.get("time")
            if not t:
                segments[-1].append(r)
                continue
            if last_time is not None:
                # naive ISO subtraction good enough for these ordered dates
                import datetime as dt

                a = dt.datetime.fromisoformat(last_time)
                b = dt.datetime.fromisoformat(t)
                if (b - a).total_seconds() > gap_s:
                    segments.append([])
            segments[-1].append(r)
            last_time = t
        for seg in segments:
            if len(seg) >= MIN_CLUSTER_SIZE:
                clusters.append(seg)
    return clusters


def summarize(host, cluster_id, members):
    times = sorted(m["time"] for m in members if m.get("time"))
    labels = Counter(m.get("label") or "?" for m in members)
    titles = Counter(
        (m.get("source_title") or "").strip() for m in members if m.get("source_title")
    )
    at_edges = 0
    for r in members:
        body = r.get("body") or ""
        at_edges += len(AT_RE.findall(body))
    return {
        "thread_id": cluster_id,
        "host": host,
        "n_pastes": len(members),
        "n_distinct_labels": len(labels),
        "n_at_mentions": at_edges,
        "first_write": times[0] if times else None,
        "last_write": times[-1] if times else None,
        "top_titles": [t for t, _ in titles.most_common(10) if t],
        "paste_ids": [m["page_id"] for m in members],
    }


def thread_id_for(host, members):
    """Human-scannable id, e.g. `linuxiarz-Iowa-2026-06-16T19-52`."""
    prefixes = Counter(
        title_prefix(m.get("source_title")) for m in members
    )
    prefixes.pop(None, None)
    for w in STOP_TITLE_WORDS:
        prefixes.pop(w, None)
    top = prefixes.most_common(1)
    tag = top[0][0] if top else "misc"
    times = sorted(m["time"] for m in members if m.get("time"))
    when = (times[0] if times else "notime").replace(":", "-").replace("+00-00", "")[:16]
    return f"{host.replace('paste-', '')}-{tag}-{when}"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as fh:
        for host in HOSTS:
            rows = load_host(host)
            clusters = cluster(rows)
            for members in sorted(clusters, key=lambda m: -len(m)):
                tid = thread_id_for(host, members)
                fh.write(json.dumps(summarize(host, tid, members)) + "\n")
                print(
                    f"{host}  {tid}  n={len(members)}  labels={len(set(m.get('label') for m in members))}"
                )


if __name__ == "__main__":
    main()
