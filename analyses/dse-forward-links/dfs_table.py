"""DFS from a seed page emitting a row per (src_rev, outbound_link) pair.

Columns:
    src_page                 page containing the outbound wiki.cgi?id= link
    src_rev                  the revision seq of src_page that contains it
    dst_page                 the linked-to page name
    dst_existed_when_link    True iff dst_page has an observed revision
                              strictly earlier than the src_rev's write_date

DFS visits each page at most once. When first visited, all of its
(rev, link) rows are emitted. Recurse into each destination in ascending
name order, subject to a depth cap.
"""
import csv
import json
import re
import sys
from collections import defaultdict

PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"
WIKI_CGI_ID = re.compile(
    r'wikiservice\.at/dse/wiki\.cgi\?[^\s\]"\)]*?\bid=([A-Za-z0-9_/\-]+)'
)


def main(seed="AgentMassDataNext774411", max_depth=4, out_path=None):
    revs = defaultdict(list)         # page name -> list of (seq, write_date, links)
    first_write = {}                 # page name -> earliest write_date
    with open(PROWIKI) as f:
        for line in f:
            r = json.loads(line)
            if r.get("wiki") != "dse":
                continue
            wd = r.get("write_date")
            if not wd:
                continue
            name = r["name"]
            body = r.get("body") or ""
            links = sorted(set(WIKI_CGI_ID.findall(body)) - {name})
            revs[name].append((r["seq"], wd, links))
            if name not in first_write or wd < first_write[name]:
                first_write[name] = wd
    for name in revs:
        revs[name].sort(key=lambda x: x[1])

    rows = []
    visited = set()

    def existed(dst, at_write_date):
        wd = first_write.get(dst)
        return wd is not None and wd < at_write_date

    def dfs(page, depth):
        if page in visited or depth > max_depth:
            return
        visited.add(page)
        # Emit rows for every (rev, link) of this page.
        for seq, wd, links in revs.get(page, ()):
            for link in links:
                rows.append({
                    "src_page": page,
                    "src_rev": f"@{seq}",
                    "src_rev_time": wd,
                    "dst_page": link,
                    "dst_existed_when_link": existed(link, wd),
                })
        # Recurse into unique outbound destinations (any rev), sorted.
        union = sorted({l for _, _, links in revs.get(page, ()) for l in links})
        for dst in union:
            dfs(dst, depth + 1)

    dfs(seed, 0)

    if out_path:
        with open(out_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "src_page", "src_rev", "dst_page", "dst_existed_when_link"
            ], extrasaction="ignore")
            w.writeheader()
            for row in rows:
                w.writerow(row)

    # Pretty-print an aligned table to stdout.
    widths = {
        "src_page": max(len("src_page"),
                        max((len(r["src_page"]) for r in rows), default=0)),
        "src_rev": max(len("src_rev"),
                       max((len(r["src_rev"]) for r in rows), default=0)),
        "dst_page": max(len("dst_page"),
                        max((len(r["dst_page"]) for r in rows), default=0)),
        "dst_existed_when_link": len("dst_existed_when_link"),
    }
    header = (f"{'src_page':<{widths['src_page']}}  "
              f"{'src_rev':<{widths['src_rev']}}  "
              f"{'dst_page':<{widths['dst_page']}}  "
              f"{'dst_existed_when_link'}")
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['src_page']:<{widths['src_page']}}  "
            f"{row['src_rev']:<{widths['src_rev']}}  "
            f"{row['dst_page']:<{widths['dst_page']}}  "
            f"{row['dst_existed_when_link']}"
        )
    print(f"\ntotal rows: {len(rows)}, distinct src pages: {len(visited)}")


if __name__ == "__main__":
    seed = sys.argv[1] if len(sys.argv) > 1 else "AgentMassDataNext774411"
    out = sys.argv[2] if len(sys.argv) > 2 else (
        f"/collusionwiki/analyses/dse-forward-links/outputs/"
        f"dfs_table_{seed}.csv"
    )
    main(seed, max_depth=4, out_path=out)
