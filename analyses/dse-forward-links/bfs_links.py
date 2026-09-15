"""BFS crawl of intra-wiki links starting from a seed page.

For each page, "intra-wiki links" = union of wiki.cgi?id=<Name> targets
across every revision of that page (self-links excluded).

Stops when depth exceeds a limit or the total number of distinct pages
enqueued reaches a cap.
"""
import json
import re
from collections import defaultdict, deque

PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"
WIKI_CGI_ID = re.compile(
    r'wikiservice\.at/dse/wiki\.cgi\?[^\s\]"\)]*?\bid=([A-Za-z0-9_/\-]+)'
)


def main(seed="AgentMassDataNext774411", max_depth=5, max_pages=100):
    # Collect all internal-link targets per page name (union across revs).
    links = defaultdict(set)
    seen_page = set()
    with open(PROWIKI) as f:
        for line in f:
            r = json.loads(line)
            if r.get("wiki") != "dse":
                continue
            body = r.get("body")
            if not body:
                continue
            name = r["name"]
            seen_page.add(name)
            for tgt in set(WIKI_CGI_ID.findall(body)):
                if tgt != name:
                    links[name].add(tgt)

    # BFS.
    depth_of = {seed: 0}
    order = [seed]
    q = deque([seed])
    while q and len(order) < max_pages:
        cur = q.popleft()
        if depth_of[cur] >= max_depth:
            continue
        for tgt in sorted(links.get(cur, ())):
            if tgt not in depth_of:
                depth_of[tgt] = depth_of[cur] + 1
                order.append(tgt)
                q.append(tgt)
                if len(order) >= max_pages:
                    break

    # Grouped listing: for each page in visit order, list its outbound links.
    print(f"BFS from {seed}, max_depth={max_depth}, cap={max_pages}")
    print(f"total pages visited: {len(order)}")
    print()
    by_depth = defaultdict(list)
    for name in order:
        by_depth[depth_of[name]].append(name)
    for d in sorted(by_depth):
        print(f"=== depth {d}: {len(by_depth[d])} page(s) ===")
        for name in by_depth[d]:
            outs = sorted(links.get(name, ()))
            body_note = "" if name in seen_page else "  [not seen in prowiki]"
            print(f"  {name}{body_note}")
            if not outs:
                print("    (no outbound intra-wiki links)")
            for o in outs:
                new_note = ""
                if o in depth_of:
                    new_note = f" -> depth {depth_of[o]}"
                else:
                    new_note = " (not enqueued: cap reached or outside window)"
                print(f"    -> {o}{new_note}")


if __name__ == "__main__":
    main()
