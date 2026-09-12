"""Find A -> B -> C chains where each first revision creates a forward link.

Definitions:
- "Page P forward-linked at creation to Q" means P's first revision (@1)
  contains a wiki.cgi?id=Q URL and Q's first revision was written strictly
  later than P's first revision.

A chain is a page A whose @1 forward-links to B, where B's @1 forward-links
to some C. C need not be a leaf; longer chains are just chains-of-chains.
"""
import json
import re
from collections import defaultdict

PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"
WIKI_CGI_ID = re.compile(
    r"wikiservice\.at/dse/wiki\.cgi\?[^\s\]]*?\bid=([A-Za-z0-9_/\-]+)"
)


def main():
    # 1. First-revision body for each page (in prowiki dse).
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
                    "rev_id": r["rev_id"],
                }

    # 2. Outbound forward-link targets from each page's @1.
    forward_out = {}
    for name, info in first_rev.items():
        targets = set(WIKI_CGI_ID.findall(info["body"])) - {name}
        f = []
        for t in targets:
            if t not in first_rev:
                continue
            if first_rev[t]["write_date"] > info["write_date"]:
                f.append(t)
        if f:
            forward_out[name] = f

    # 3. Chains: A in forward_out, some B in forward_out[A] also in forward_out.
    chains = []
    for a, bs in forward_out.items():
        for b in bs:
            if b in forward_out:
                for c in forward_out[b]:
                    chains.append((a, b, c))

    print(f"pages whose @1 has >=1 forward link: {len(forward_out)}")
    print(f"A -> B -> C chains (A@1 forward-links B; B@1 forward-links C): {len(chains)}")
    print()
    print("distinct A pages that start a chain:", len({a for a, _, _ in chains}))
    print("distinct B (middle) pages:          ", len({b for _, b, _ in chains}))
    print("distinct C (tail) pages:            ", len({c for _, _, c in chains}))
    print()
    if not chains:
        print("No chains found.")
        return
    print("First 30 chains, oldest A first:")
    chains.sort(key=lambda x: first_rev[x[0]]["write_date"])
    for a, b, c in chains[:30]:
        ta = first_rev[a]["write_date"]
        tb = first_rev[b]["write_date"]
        tc = first_rev[c]["write_date"]
        print(f"  {a}@1 {ta}")
        print(f"    -> {b}@1 {tb}")
        print(f"       -> {c}@1 {tc}")

    # 4. Any deeper chains (A -> B -> C -> D)?
    deeper = []
    for a, b, c in chains:
        if c in forward_out:
            for d in forward_out[c]:
                deeper.append((a, b, c, d))
    print()
    print(f"4-level chains A->B->C->D: {len(deeper)}")
    for chain in deeper[:10]:
        print("  " + " -> ".join(chain))


if __name__ == "__main__":
    main()
