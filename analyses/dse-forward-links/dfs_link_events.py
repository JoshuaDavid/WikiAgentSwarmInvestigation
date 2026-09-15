"""DFS enumeration of new-link creation events from a seed page.

For each revision of the current page, compute its intra-wiki link set. A
"new link event" is any link present in this revision but absent from the
previous revision of the same page. DFS recurses into each new dst before
moving to the next event, up to a max depth. WillkommenImWiki is skipped
both as a dst and as a page to recurse into.

Output columns:
  src_page, src_rev, dst_page, dst_existed_when_link
"""
import json
import re
import csv
import sys
from collections import defaultdict
from datetime import datetime

PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"
WIKI_CGI_ID = re.compile(
    r'wikiservice\.at/dse/wiki\.cgi\?[^\s\]"\)]*?\bid=([A-Za-z0-9_/\-]+)'
)
SEED = "AgentMassDataNext774411"
MAX_DEPTH = 4
EXCLUDE = {"WillkommenImWiki"}


def parse(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def load():
    revs_by_page = defaultdict(list)
    first_t = {}
    with open(PROWIKI) as f:
        for line in f:
            r = json.loads(line)
            if r.get("wiki") != "dse":
                continue
            t = r.get("write_date")
            if not t:
                continue
            t = parse(t)
            name = r["name"]
            body = r.get("body") or ""
            internals = set(WIKI_CGI_ID.findall(body)) - {name}
            revs_by_page[name].append({
                "t": t, "seq": r["seq"], "internals": internals,
            })
            if name not in first_t or t < first_t[name]:
                first_t[name] = t
    for name in revs_by_page:
        revs_by_page[name].sort(key=lambda r: r["t"])
    return revs_by_page, first_t


def main():
    revs_by_page, first_t = load()
    visited = set()
    rows = []

    def dfs(page, depth):
        if page in visited or page in EXCLUDE:
            return
        visited.add(page)
        prev = set()
        for rev in revs_by_page.get(page, []):
            new = rev["internals"] - prev
            prev = rev["internals"]
            for dst in sorted(new):
                if dst in EXCLUDE:
                    continue
                dst_existed = dst in first_t and first_t[dst] <= rev["t"]
                rows.append({
                    "src_page": page,
                    "src_rev": f"@{rev['seq']}",
                    "dst_page": dst,
                    "dst_existed_when_link": "true" if dst_existed else "false",
                })
                if depth < MAX_DEPTH:
                    dfs(dst, depth + 1)

    dfs(SEED, 0)

    csv_path = ("/collusionwiki/analyses/dse-forward-links/outputs/"
                "dfs_from_AgentMassDataNext774411.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "src_page", "src_rev", "dst_page", "dst_existed_when_link"
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {csv_path}  ({len(rows)} rows)")

    # Pretty print.
    src_w = max(len(r["src_page"]) for r in rows)
    dst_w = max(len(r["dst_page"]) for r in rows)
    header = (f"{'src_page'.ljust(src_w)}  {'src_rev':<7}  "
              f"{'dst_page'.ljust(dst_w)}  dst_existed_when_link")
    print()
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['src_page'].ljust(src_w)}  {r['src_rev']:<7}  "
              f"{r['dst_page'].ljust(dst_w)}  {r['dst_existed_when_link']}")


if __name__ == "__main__":
    main()
