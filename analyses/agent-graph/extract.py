#!/usr/bin/env python3
"""Emit (from, to) message pairs across every wiki export, then find components.

Scans every `../../agent-logs/<wiki-dir>/{labels,revisions}.jsonl`. A "message"
is a `(writer, mentioned_handle)` tuple: any revision whose body mentions a
known agent handle other than the writer's own emits one message per mention.

Handle set is the union of all `labels.jsonl` across all wiki directories,
filtered to `label` length >= 6, non-blank, and not a pre-redacted admin/user
handle (`[Admin##]`, `[Person##]`, `[User##]`). Same rule as
`../addressing/detect.py`, applied to the whole corpus rather than just prowiki.

Writes to `outputs/`:
    messages.jsonl   -- one row per (writer, mentioned_handle) pair
    edges.jsonl      -- unique directed edges with count
    nodes.jsonl      -- per-handle degree and message counts
    components.json  -- undirected connected components, size-desc
    summary.txt      -- counts printed to stdout
"""
from __future__ import annotations
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
LOGS = REPO_ROOT / "agent-logs"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

MIN_HANDLE_LEN = 6
REDACTED_RE = re.compile(r"^\[(Person|Admin|User)\d+\]$")


def iter_wiki_dirs():
    for p in sorted(LOGS.iterdir()):
        if p.is_dir() and (p / "labels.jsonl").exists() and (p / "revisions.jsonl").exists():
            yield p


def load_handle_set():
    handles = set()
    per_wiki = Counter()
    for d in iter_wiki_dirs():
        n = 0
        with (d / "labels.jsonl").open() as f:
            for line in f:
                row = json.loads(line)
                label = (row.get("label") or "").strip()
                if not label or len(label) < MIN_HANDLE_LEN:
                    continue
                if REDACTED_RE.match(label):
                    continue
                handles.add(label)
                n += 1
        per_wiki[d.name] = n
    return handles, per_wiki


def compile_mention_re(handles):
    sorted_h = sorted(handles, key=len, reverse=True)
    escaped = [re.escape(h) for h in sorted_h]
    return re.compile(
        r"(?<![A-Za-z0-9_])(?:" + "|".join(escaped) + r")(?![A-Za-z0-9_])"
    )


def collect_best_rows(iter_dirs):
    """Pick the best row per rev_id across overlapping exports.

    Several exports overlap on the same underlying wiki (e.g. `prowiki/`
    and the standalone `dse/`, `fractal/`, `probier/` scrapes each cover
    overlapping time windows for the same wiki). Some exports carry
    revision bodies, others carry only metadata (the standalone `dse/`
    scrape has zero body bytes). A revision without a body is useless for
    addressing detection.

    Rule: for each `rev_id`, keep any body-bearing row over any body-less
    row. Among body-bearing rows, keep the first seen (directory sort
    order). Track which source(s) each rev_id appeared in for reporting.
    """
    best = {}
    seen_sources = defaultdict(Counter)  # wiki -> Counter{source_dir: count}
    for d in iter_dirs:
        with (d / "revisions.jsonl").open() as f:
            for line in f:
                rev = json.loads(line)
                rid = rev.get("rev_id")
                wiki = rev.get("wiki", d.name)
                seen_sources[wiki][d.name] += 1
                if rid in best:
                    incumbent = best[rid][1]
                    if incumbent.get("body") or not rev.get("body"):
                        continue
                best[rid] = (d.name, rev)
    return best, seen_sources


def scan_pairs(handles, mention_re):
    best, seen_sources = collect_best_rows(list(iter_wiki_dirs()))

    pairs = []
    per_wiki_unique = Counter()
    per_wiki_matched = Counter()
    per_wiki_bodied = Counter()
    for rid, (src, rev) in best.items():
        wiki = rev.get("wiki", src)
        per_wiki_unique[wiki] += 1
        body = rev.get("body") or ""
        if not body:
            continue
        per_wiki_bodied[wiki] += 1
        writer = (rev.get("label") or "").strip()
        if not writer:
            continue
        found = set(mention_re.findall(body))
        found.discard(writer)
        if not found:
            continue
        per_wiki_matched[wiki] += 1
        for other in found:
            pairs.append({
                "from": writer,
                "to": other,
                "wiki": wiki,
                "page_id": rev.get("page_id"),
                "rev_id": rid,
                "time": rev.get("time"),
            })
    return pairs, per_wiki_unique, per_wiki_bodied, per_wiki_matched, seen_sources


def connected_components(nodes, undirected_edges):
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a, b in undirected_edges:
        union(a, b)
    comps = defaultdict(list)
    for n in nodes:
        comps[find(n)].append(n)
    return sorted((sorted(v) for v in comps.values()), key=len, reverse=True)


def main():
    handles, per_wiki_handles = load_handle_set()
    print(f"handle set: {len(handles)} handles from {len(per_wiki_handles)} wikis")

    mention_re = compile_mention_re(handles)
    pairs, per_wiki_unique, per_wiki_bodied, per_wiki_matched, per_wiki_source = scan_pairs(handles, mention_re)

    with (OUT / "messages.jsonl").open("w") as fh:
        for p in pairs:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")

    edge_counts = Counter((p["from"], p["to"]) for p in pairs)
    with (OUT / "edges.jsonl").open("w") as fh:
        for (a, b), c in sorted(edge_counts.items(), key=lambda kv: -kv[1]):
            fh.write(json.dumps({"from": a, "to": b, "count": c}, ensure_ascii=False) + "\n")

    nodes = set()
    for a, b in edge_counts:
        nodes.add(a)
        nodes.add(b)

    out_deg = Counter()
    in_deg = Counter()
    out_weight = Counter()
    in_weight = Counter()
    per_node_wikis = defaultdict(set)
    for p in pairs:
        per_node_wikis[p["from"]].add(p["wiki"])
        per_node_wikis[p["to"]].add(p["wiki"])
    for (a, b), c in edge_counts.items():
        out_deg[a] += 1
        in_deg[b] += 1
        out_weight[a] += c
        in_weight[b] += c

    with (OUT / "nodes.jsonl").open("w") as fh:
        for n in sorted(nodes):
            fh.write(json.dumps({
                "handle": n,
                "out_degree": out_deg.get(n, 0),
                "in_degree": in_deg.get(n, 0),
                "out_messages": out_weight.get(n, 0),
                "in_mentions": in_weight.get(n, 0),
                "wikis": sorted(per_node_wikis.get(n, ())),
            }, ensure_ascii=False) + "\n")

    undirected = set()
    for a, b in edge_counts:
        undirected.add((min(a, b), max(a, b)))

    comps = connected_components(nodes, undirected)
    comp_summary = [{"size": len(c), "members": c} for c in comps]
    (OUT / "components.json").write_text(json.dumps(comp_summary, indent=2, ensure_ascii=False))

    size_hist = Counter(len(c) for c in comps)
    lines = []
    lines.append("per-wiki scan (dedup by rev_id, body-bearing row preferred):")
    total_uniq = 0
    total_body = 0
    total_match = 0
    for w in sorted(set(per_wiki_unique) | set(per_wiki_matched)):
        u = per_wiki_unique.get(w, 0)
        b = per_wiki_bodied.get(w, 0)
        m = per_wiki_matched.get(w, 0)
        srcs = per_wiki_source.get(w, {})
        src_str = ",".join(f"{k}:{v}" for k, v in sorted(srcs.items()))
        total_uniq += u
        total_body += b
        total_match += m
        lines.append(f"  {w:20s} unique={u:6d}  bodied={b:6d}  addressing_revs={m:6d}  sources={{{src_str}}}")
    lines.append(f"  {'TOTAL':20s} unique={total_uniq:6d}  bodied={total_body:6d}  addressing_revs={total_match:6d}")
    lines.append("")
    lines.append(f"pairs (msg,from,to): {len(pairs)}")
    lines.append(f"unique directed edges: {len(edge_counts)}")
    lines.append(f"unique undirected edges: {len(undirected)}")
    lines.append(f"nodes (handles seen as writer or mention): {len(nodes)}")
    lines.append(f"connected components: {len(comps)}")
    lines.append("component-size histogram (size -> count):")
    for sz in sorted(size_hist, reverse=True)[:20]:
        lines.append(f"  size={sz:4d}  n_components={size_hist[sz]}")
    lines.append("top 8 components by size:")
    for c in comps[:8]:
        sample = ", ".join(c[:6]) + (" ..." if len(c) > 6 else "")
        lines.append(f"  size={len(c):4d}  sample=[{sample}]")
    text = "\n".join(lines) + "\n"
    (OUT / "summary.txt").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
