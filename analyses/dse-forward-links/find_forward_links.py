"""Find dse revisions that link to a page whose first observed revision is later.

Sources
- /collusionwiki/agent-logs/prowiki/revisions.jsonl (wiki=dse subset)
    Has bodies and precise UTC write_date. Window: 2026-05-24 .. 2026-07-02.
- /collusionwiki/agent-logs/dse/revisions.jsonl (metadata only)
    Wider window (2026-05-24 .. 2026-09-04) but minute-precision wall time.
    The wiki declares +01:00 (CET) year-round while the host actually runs
    on CEST in summer, so times parse ~1 hour later than real UTC. We do NOT
    use dse/ for time comparisons.

Method
1. For every dse page name in dse/pages.jsonl, take earliest observed
   write_date from prowiki (wiki=dse) as the "first revision" time.
2. For every prowiki dse revision with a body, scan the body for
   `wiki.cgi?...id=<Name>` URLs. Each match is a link event.
3. Forward link = link event whose linking write_date is strictly before the
   target page's first-revision write_date.

Limitations
- Links via bare WikiLinks (CamelCase) are lost by HTML-stripping and are
  not counted.
- Targets whose first revision is outside the prowiki window (after
  2026-07-02) are excluded from the comparison.
- The linking revision's page appears in its own body via the "self" tab;
  self-links are filtered out.
"""
import json
import re
from collections import defaultdict
from datetime import datetime

PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"

OUT_ALL = "/collusionwiki/analyses/dse-forward-links/outputs/forward_links.jsonl"
OUT_SUMMARY = "/collusionwiki/analyses/dse-forward-links/outputs/summary.txt"

WIKI_CGI_ID = re.compile(
    r"wikiservice\.at/dse/wiki\.cgi\?[^\s\]]*?\bid=([A-Za-z0-9_/\-]+)"
)


def parse(ts):
    return datetime.fromisoformat(ts)


def load_prowiki_dse():
    """Return (rev_by_id, first_write_by_name).

    Uses write_date (precise UTC) as the canonical time.
    """
    rev_by_id = {}
    first = {}
    with open(PROWIKI) as f:
        for line in f:
            r = json.loads(line)
            if r.get("wiki") != "dse":
                continue
            t = r.get("write_date") or r.get("time")
            if not t:
                continue
            r["_t"] = parse(t)
            rev_by_id[r["rev_id"]] = r
            name = r["name"]
            if name not in first or r["_t"] < first[name][0]:
                first[name] = (r["_t"], r["rev_id"], r.get("label"))
    return rev_by_id, first


def iter_link_events(rev_by_id):
    for r in rev_by_id.values():
        body = r.get("body")
        if not body:
            continue
        for target in set(WIKI_CGI_ID.findall(body)):
            yield r, target


def main():
    rev_by_id, first_write = load_prowiki_dse()

    total = 0
    self_link = 0
    target_outside_window = 0
    forward_events = 0
    by_source_page = defaultdict(int)

    forward_rows = []
    with open(OUT_ALL, "w") as out:
        for r, target in iter_link_events(rev_by_id):
            total += 1
            if target == r["name"]:
                self_link += 1
                continue
            if target not in first_write:
                target_outside_window += 1
                continue
            t_first, t_first_rev, t_first_label = first_write[target]
            if r["_t"] < t_first:
                forward_events += 1
                by_source_page[r["name"]] += 1
                row = {
                    "linking_rev_id": r["rev_id"],
                    "linking_time": r["_t"].isoformat(),
                    "linking_label": r.get("label"),
                    "linking_ip16": r.get("ip16"),
                    "linked_name": target,
                    "target_first_rev_id": t_first_rev,
                    "target_first_time": t_first.isoformat(),
                    "target_first_label": t_first_label,
                    "gap_seconds": (t_first - r["_t"]).total_seconds(),
                }
                forward_rows.append(row)
                out.write(json.dumps(row) + "\n")

    forward_rows.sort(key=lambda x: x["gap_seconds"])

    with open(OUT_SUMMARY, "w") as s:
        s.write(f"prowiki dse revisions with bodies:              {sum(1 for r in rev_by_id.values() if r.get('body'))}\n")
        s.write(f"total wiki.cgi?id= link events extracted:       {total}\n")
        s.write(f"  self-links (target = source page):            {self_link}\n")
        s.write(f"  target's first rev outside prowiki window:    {target_outside_window}\n")
        s.write(f"  target first revision AFTER linking revision: {forward_events}\n")
        s.write(f"  distinct source pages producing forward links:{len(by_source_page)}\n")
        s.write("\n")
        s.write("Top source pages by forward-link count:\n")
        for name, n in sorted(by_source_page.items(), key=lambda kv: -kv[1])[:15]:
            s.write(f"  {n:>5} {name}\n")
        s.write("\n")
        s.write("Sample forward links, shortest gap first (top 20):\n")
        for row in forward_rows[:20]:
            s.write(
                f"  gap={row['gap_seconds']:>10.0f}s  "
                f"{row['linking_rev_id']} @ {row['linking_time']} ({row['linking_label']}) "
                f"-> {row['linked_name']} first={row['target_first_time']} ({row['target_first_label']})\n"
            )
        s.write("\n")
        s.write("Sample forward links, longest gap first (top 10):\n")
        for row in sorted(forward_rows, key=lambda x: -x["gap_seconds"])[:10]:
            s.write(
                f"  gap={row['gap_seconds']:>10.0f}s  "
                f"{row['linking_rev_id']} @ {row['linking_time']} ({row['linking_label']}) "
                f"-> {row['linked_name']} first={row['target_first_time']} ({row['target_first_label']})\n"
            )

    print(open(OUT_SUMMARY).read())


if __name__ == "__main__":
    main()
