#!/usr/bin/env python3
"""Find the longest two-agent conversation on any single wiki page.

Two definitions:

- strict: only revisions where the writer's label is A or B AND the body
  mentions the other. Alternation of the writer label counts turns.
- loose: revisions on a single page authored by A or B, regardless of
  whether they mention each other. Compress equal-label runs, count turns.

For both, walk the same source: `analyses/agent-graph/outputs/messages.jsonl`
for the strict view (has both writer and mentioned handle per revision), and
the raw revisions files under `agent-logs/*/revisions.jsonl` for the loose
view.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MESSAGES_PATH = ROOT / "analyses" / "agent-graph" / "outputs" / "messages.jsonl"
OUT = Path(__file__).resolve().parent / "outputs"


def load_messages():
    """Load one row per (from, to, page, rev_id, time) pair."""
    rows = []
    for line in MESSAGES_PATH.open():
        rows.append(json.loads(line))
    return rows


def compress_alternation(seq):
    """Collapse equal-neighbor runs. Returns compressed list."""
    out = []
    for x in seq:
        if not out or out[-1] != x:
            out.append(x)
    return out


def strict_conversations(messages):
    """For each (unordered pair, page), find longest alternating exchange
    of revisions where writer ∈ pair AND revision mentions the other.
    """
    # For each (page, unordered_pair), collect (time, writer). Because a
    # revision mentioning multiple handles emits multiple pair rows, we
    # naturally get the "writer mentions the other" filter for free — a
    # revision only enters pair (X, Y) if writer is one of them and the
    # other is mentioned.
    by_page_pair = defaultdict(list)
    for m in messages:
        a, b = m["from"], m["to"]
        if a == b:
            continue
        pair = tuple(sorted([a, b]))
        key = (m["page_id"], pair)
        by_page_pair[key].append((m["time"], a, m["rev_id"]))

    results = []
    for (page_id, pair), rows in by_page_pair.items():
        rows.sort(key=lambda r: r[0])
        # Deduplicate by rev_id — a revision authored by A that mentions B
        # only produces one A→B row here, but keep defensive dedup.
        seen = set()
        dedup = []
        for t, w, rid in rows:
            if rid in seen:
                continue
            seen.add(rid)
            dedup.append((t, w, rid))
        writers = [w for _, w, _ in dedup]
        compressed = compress_alternation(writers)
        if len(compressed) < 2:
            continue
        results.append({
            "page_id": page_id,
            "pair": list(pair),
            "n_revs_between_pair": len(dedup),
            "n_turns_alternating": len(compressed),
            "first_time": dedup[0][0],
            "last_time": dedup[-1][0],
            "rev_ids": [rid for _, _, rid in dedup],
        })
    results.sort(key=lambda r: -r["n_turns_alternating"])
    return results


def load_revisions_by_page():
    """Return {page_id: [(time, label, rev_id, wiki), …]} across all wikis."""
    by_page = defaultdict(list)
    seen_revs = set()
    for revs_path in sorted((ROOT / "agent-logs").glob("*/revisions.jsonl")):
        for line in revs_path.open():
            r = json.loads(line)
            rid = r["rev_id"]
            if rid in seen_revs:
                continue
            seen_revs.add(rid)
            label = r.get("label") or ""
            if not label:
                continue
            by_page[r["page_id"]].append((r["time"], label, rid, r["wiki"]))
    for k in by_page:
        by_page[k].sort(key=lambda x: x[0])
    return by_page


def loose_conversations(by_page):
    """For each page, for each unordered pair of writers on that page,
    filter to their revisions and count the longest alternating run.
    """
    results = []
    for page_id, rows in by_page.items():
        labels_on_page = {r[1] for r in rows}
        if len(labels_on_page) < 2:
            continue
        # For each pair, extract their subsequence.
        for a in labels_on_page:
            for b in labels_on_page:
                if a >= b:
                    continue
                sub = [r for r in rows if r[1] in (a, b)]
                writers = [r[1] for r in sub]
                compressed = compress_alternation(writers)
                if len(compressed) < 2:
                    continue
                results.append({
                    "page_id": page_id,
                    "wiki": sub[0][3],
                    "pair": [a, b],
                    "n_revs_by_pair": len(sub),
                    "n_turns_alternating": len(compressed),
                    "first_time": sub[0][0],
                    "last_time": sub[-1][0],
                    "rev_ids": [r[2] for r in sub],
                })
    results.sort(key=lambda r: -r["n_turns_alternating"])
    return results


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    messages = load_messages()
    strict = strict_conversations(messages)

    with (OUT / "strict.jsonl").open("w") as f:
        for r in strict:
            f.write(json.dumps(r) + "\n")

    print("=== STRICT (writer mentions the other) — top 20 ===")
    for r in strict[:20]:
        print(f"  turns={r['n_turns_alternating']:>3}  revs={r['n_revs_between_pair']:>3}  "
              f"pair={r['pair'][0]!r} <-> {r['pair'][1]!r}  page={r['page_id']}")

    print()
    by_page = load_revisions_by_page()
    loose = loose_conversations(by_page)

    # loose is O(pairs × pages) and mostly noise — cap at the top 5,000
    # ranked entries. The tail is co-editing spam (mostly WillkommenImWiki
    # link-dump war) and adds no information beyond the top of the list.
    with (OUT / "loose.jsonl").open("w") as f:
        for r in loose[:5000]:
            f.write(json.dumps(r) + "\n")

    print("=== LOOSE (both wrote the page, alternating) — top 20 ===")
    for r in loose[:20]:
        print(f"  turns={r['n_turns_alternating']:>3}  revs={r['n_revs_by_pair']:>3}  "
              f"pair={r['pair'][0]!r} <-> {r['pair'][1]!r}  page={r['page_id']}")


if __name__ == "__main__":
    main()
