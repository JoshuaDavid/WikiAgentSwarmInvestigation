"""Vibe check: pick 5 random dse pages, look at their surroundings, and
try to classify each into one of the coordination patterns.

For each sampled page, report:
- revision count and time span
- distinct editor labels
- outbound intra-wiki targets (union across revs)
- inbound intra-wiki links (pages that reference this one)
- naming-convention neighbours (dse pages sharing the same first-10-char
  prefix; a proxy for the linked-list / chunk / slot family)
- external hosts referenced
- a suggested pattern tag

Pattern tags:
  single-page-conv   many revs on this page, few internal links, chatty
  hub-and-slots      one/two revs, many internal links, forward-heavy
  linked-list        few revs, 1-2 internal links, one is forward
  chunked-continuation  name has integer suffix and siblings exist
  rendezvous         well-known name (StartSeite/WillkommenImWiki/TestSeite/RecentChanges)
  beacon-side-channel   external counter/pixel/beacon host present
  singleton          1-2 revs, no internal links, no siblings
  mixed              matches more than one strongly
"""
import json
import random
import re
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"
DSE_PAGES = "/collusionwiki/agent-logs/dse/pages.jsonl"
DSE_REVS = "/collusionwiki/agent-logs/dse/revisions.jsonl"

WIKI_CGI_ID = re.compile(
    r'wikiservice\.at/dse/wiki\.cgi\?[^\s\]"\)]*?\bid=([A-Za-z0-9_/\-]+)'
)
URL_RE = re.compile(r'https?://[^\s\]"\)]+')
BEACON_HOSTS = re.compile(
    r"(counter|hits?\.|pixel|beacon|counterapi|counter-api|ping|"
    r"pinggy|blob\.core\.windows|counter\.)")
RENDEZVOUS = {"StartSeite", "WillkommenImWiki", "TestSeite", "RecentChanges",
              "SandBox", "Sandbox", "TestSandbox"}


def parse(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def main(seed=17):
    random.seed(seed)
    all_names = [json.loads(l)["name"] for l in open(DSE_PAGES)]
    sample = random.sample(all_names, 5)

    # Load all body-bearing dse revs from prowiki (for outbound extraction).
    revs_by_page = defaultdict(list)
    inbound = defaultdict(set)
    label_by_page = defaultdict(set)
    ext_hosts_by_page = defaultdict(set)
    with open(PROWIKI) as f:
        for line in f:
            r = json.loads(line)
            if r.get("wiki") != "dse":
                continue
            body = r.get("body") or ""
            name = r["name"]
            label_by_page[name].add(r.get("label"))
            outs = set(WIKI_CGI_ID.findall(body)) - {name}
            revs_by_page[name].append({
                "seq": r["seq"], "t": r.get("write_date"),
                "internals": outs, "body_len": len(body),
                "label": r.get("label"),
            })
            for tgt in outs:
                inbound[tgt].add(name)
            for u in URL_RE.findall(body):
                if "wikiservice.at" in u:
                    continue
                try:
                    h = urlparse(u).hostname
                    if h:
                        ext_hosts_by_page[name].add(h)
                except Exception:
                    pass

    # rev metadata from dse (for pages without bodies)
    dse_meta = defaultdict(list)
    with open(DSE_REVS) as f:
        for line in f:
            r = json.loads(line)
            dse_meta[r["name"]].append((r["seq"], r["time"], r.get("label"),
                                          r.get("change_summary")))

    # Precompute prefix map for neighbour check.
    prefix_neighbours = defaultdict(list)
    for n in all_names:
        prefix_neighbours[n[:10]].append(n)

    for name in sample:
        print("=" * 80)
        print(f"PAGE: {name}")
        pw_revs = revs_by_page.get(name, [])
        dse_rows = dse_meta.get(name, [])
        n_revs_pw = len(pw_revs)
        n_revs_dse = len(dse_rows)
        print(f"  revisions in prowiki (with bodies): {n_revs_pw}")
        print(f"  revisions in dse (metadata):         {n_revs_dse}")
        if dse_rows:
            first_seq, first_t, first_label, _ = min(dse_rows,
                                                    key=lambda r: r[1])
            last_seq, last_t, _, _ = max(dse_rows, key=lambda r: r[1])
            print(f"  first observed: {first_t}  by {first_label}")
            print(f"  last observed:  {last_t}")
        labels = label_by_page[name] | {r[2] for r in dse_rows}
        print(f"  distinct editor labels: {len(labels)}: "
              f"{sorted(l for l in labels if l)[:8]}"
              f"{' ...' if len(labels) > 8 else ''}")

        # Outbound intra-wiki (union across revs).
        outs = set()
        for r in pw_revs:
            outs |= r["internals"]
        print(f"  outbound intra-wiki targets ({len(outs)}): "
              f"{sorted(outs)[:6]}"
              f"{' ...' if len(outs) > 6 else ''}")

        ins = inbound.get(name, set())
        print(f"  inbound intra-wiki links from ({len(ins)}): "
              f"{sorted(ins)[:6]}"
              f"{' ...' if len(ins) > 6 else ''}")

        neigh = [n for n in prefix_neighbours[name[:10]] if n != name]
        print(f"  naming-neighbours (share first 10 chars) ({len(neigh)}): "
              f"{sorted(neigh)[:6]}"
              f"{' ...' if len(neigh) > 6 else ''}")

        ext_hosts = ext_hosts_by_page.get(name, set())
        beacon = {h for h in ext_hosts if BEACON_HOSTS.search(h)}
        print(f"  external hosts ({len(ext_hosts)}): "
              f"{sorted(ext_hosts)[:6]}"
              f"{' ...' if len(ext_hosts) > 6 else ''}")
        if beacon:
            print(f"    !! beacon-shaped hosts: {sorted(beacon)}")

        # Try a pattern tag.
        tags = []
        if name in RENDEZVOUS:
            tags.append("rendezvous")
        if beacon:
            tags.append("beacon-side-channel")
        if neigh and re.search(r"\d+$", name):
            tags.append("chunked-continuation")
        if n_revs_dse >= 8 and len(outs) <= 2:
            tags.append("single-page-conv")
        if n_revs_pw <= 3 and len(outs) >= 8:
            tags.append("hub-and-slots")
        if n_revs_pw <= 3 and 1 <= len(outs) <= 3:
            tags.append("linked-list-node?")
        if not tags:
            if n_revs_dse <= 2 and len(outs) == 0:
                tags.append("singleton")
            else:
                tags.append("unclassified")
        print(f"  >> pattern tag(s): {tags}")
        print()


if __name__ == "__main__":
    main()
