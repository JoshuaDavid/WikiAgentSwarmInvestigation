#!/usr/bin/env python3
"""Emit (from, to) message pairs and connected-component structure.

Reads:  ../addressing/outputs/addressed_revisions.jsonl
Writes: outputs/messages.jsonl   -- one row per (writer, mentioned_handle) pair
        outputs/edges.jsonl      -- one row per unique (from, to) directed edge with count
        outputs/nodes.jsonl      -- one row per participating handle with degree stats
        outputs/components.json  -- undirected connected components, sorted by size desc
        outputs/summary.txt      -- counts printed to stdout
"""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "addressing" / "outputs" / "addressed_revisions.jsonl"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)


def load_pairs():
    pairs = []
    with SRC.open() as fh:
        for line in fh:
            r = json.loads(line)
            writer = (r.get("label") or "").strip()
            if not writer:
                continue
            for other in r.get("mentions_others", []):
                other = (other or "").strip()
                if not other or other == writer:
                    continue
                pairs.append({
                    "from": writer,
                    "to": other,
                    "wiki": r["wiki"],
                    "page_id": r["page_id"],
                    "rev_id": r["rev_id"],
                    "time": r["time"],
                })
    return pairs


def connected_components(nodes, undirected_edges):
    """Union-find over undirected edges."""
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
    pairs = load_pairs()

    with (OUT / "messages.jsonl").open("w") as fh:
        for p in pairs:
            fh.write(json.dumps(p) + "\n")

    edge_counts = Counter((p["from"], p["to"]) for p in pairs)
    with (OUT / "edges.jsonl").open("w") as fh:
        for (a, b), c in sorted(edge_counts.items(), key=lambda kv: -kv[1]):
            fh.write(json.dumps({"from": a, "to": b, "count": c}) + "\n")

    nodes = set()
    for a, b in edge_counts:
        nodes.add(a)
        nodes.add(b)

    out_deg = Counter()
    in_deg = Counter()
    out_weight = Counter()
    in_weight = Counter()
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
            }) + "\n")

    undirected = set()
    for a, b in edge_counts:
        undirected.add((min(a, b), max(a, b)))

    comps = connected_components(nodes, undirected)
    comp_summary = [{"size": len(c), "members": c} for c in comps]
    (OUT / "components.json").write_text(json.dumps(comp_summary, indent=2))

    size_hist = Counter(len(c) for c in comps)
    lines = []
    lines.append(f"pairs (msg,from,to): {len(pairs)}")
    lines.append(f"unique directed edges: {len(edge_counts)}")
    lines.append(f"unique undirected edges: {len(undirected)}")
    lines.append(f"nodes (handles seen as writer or mention): {len(nodes)}")
    lines.append(f"connected components: {len(comps)}")
    lines.append("component-size histogram (size -> count):")
    for sz in sorted(size_hist, reverse=True)[:20]:
        lines.append(f"  size={sz:4d}  n_components={size_hist[sz]}")
    lines.append("top 5 components by size:")
    for c in comps[:5]:
        sample = ", ".join(c[:6]) + (" ..." if len(c) > 6 else "")
        lines.append(f"  size={len(c):4d}  sample=[{sample}]")
    text = "\n".join(lines) + "\n"
    (OUT / "summary.txt").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
