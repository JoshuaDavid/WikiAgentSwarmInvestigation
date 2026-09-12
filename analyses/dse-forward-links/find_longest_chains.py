"""Find the longest A -> B -> C -> ... chains of at-creation forward links.

Node = a page. Edge = A points to B iff A's first revision (@1) contains a
wiki.cgi?id=B URL and B's first revision is strictly later than A's. The
"forward at creation" graph. Find longest simple paths.
"""
import json
import re
from collections import defaultdict

PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"
WIKI_CGI_ID = re.compile(
    r"wikiservice\.at/dse/wiki\.cgi\?[^\s\]]*?\bid=([A-Za-z0-9_/\-]+)"
)


def main():
    first_rev = {}
    with open(PROWIKI) as f:
        for line in f:
            r = json.loads(line)
            if r.get("wiki") != "dse":
                continue
            t = r.get("write_date")
            if not t:
                continue
            name = r["name"]
            if name not in first_rev or t < first_rev[name]["write_date"]:
                first_rev[name] = {
                    "write_date": t,
                    "body": r.get("body") or "",
                    "label": r.get("label"),
                }

    # Build the DAG. Edges only go forward in time by construction.
    edges = defaultdict(list)
    for name, info in first_rev.items():
        targets = set(WIKI_CGI_ID.findall(info["body"])) - {name}
        for tgt in targets:
            if tgt in first_rev and first_rev[tgt]["write_date"] > info["write_date"]:
                edges[name].append(tgt)

    # Longest path from each node via DP (times are strictly increasing).
    # Sort nodes by write_date descending -> process leaves first.
    ordered = sorted(first_rev.keys(), key=lambda n: first_rev[n]["write_date"],
                     reverse=True)
    best_len = {n: 1 for n in first_rev}
    best_next = {n: None for n in first_rev}
    for n in ordered:
        for tgt in edges.get(n, ()):
            if best_len[tgt] + 1 > best_len[n]:
                best_len[n] = best_len[tgt] + 1
                best_next[n] = tgt

    # Recover paths from each node.
    def path_from(n):
        p = []
        while n is not None:
            p.append(n)
            n = best_next[n]
        return p

    ranked = sorted(first_rev.keys(), key=lambda n: -best_len[n])
    print("Top 15 longest at-creation forward chains:")
    seen_starts = set()
    for start in ranked:
        if best_len[start] < 2:
            break
        p = path_from(start)
        # Avoid printing tails of already-printed longer paths.
        key = tuple(p)
        if any(key == tuple(path_from(s))[i:i + len(key)]
               for s in seen_starts
               for i in range(len(path_from(s)) - len(key) + 1)):
            continue
        seen_starts.add(start)
        print(f"\n  length={best_len[start]}")
        for i, n in enumerate(p):
            t = first_rev[n]["write_date"]
            label = first_rev[n]["label"]
            print(f"    {'  ' * i}-> {n}@1 {t} ({label})")
        if len(seen_starts) >= 15:
            break


if __name__ == "__main__":
    main()
