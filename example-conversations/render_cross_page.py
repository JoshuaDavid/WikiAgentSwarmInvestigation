#!/usr/bin/env python3
"""Render a two-agent conversation that spans multiple wiki pages.

Same selection rule as `render.py` (writer is A or B AND body mentions
the other), but scans a list of pages, interleaves the picked revisions
by time, and marks page transitions in the output.

Usage:
  python3 render_cross_page.py AGENT_A AGENT_B OUT_MD PAGE_ID [PAGE_ID ...]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "agent-logs"


def load_revs():
    seen = {}
    for p in sorted(ROOT.glob("*/revisions.jsonl")):
        for line in p.open():
            r = json.loads(line)
            rid = r["rev_id"]
            existing = seen.get(rid)
            if existing and existing.get("body") and not r.get("body"):
                continue
            seen[rid] = r
    return seen


def compress(seq):
    o = []
    for x in seq:
        if not o or o[-1] != x:
            o.append(x)
    return o


def render(a: str, b: str, out_path: Path, pages: list[str]):
    revs = load_revs()

    a_pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(a) + r"(?![A-Za-z0-9_])")
    b_pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(b) + r"(?![A-Za-z0-9_])")

    # For each page, keep the ordered list of that page's revs so we can
    # compute per-page append-only diffs (prev is the previous rev on the
    # SAME page, not the previous rev in the interleaved timeline).
    page_revs = {p: sorted(
        (r for r in revs.values() if r["page_id"] == p),
        key=lambda r: r["time"],
    ) for p in pages}

    picked = []  # (time, rev, page_id, page_prev_body)
    for page_id in pages:
        prev_body = ""
        for r in page_revs[page_id]:
            body = r.get("body") or ""
            lbl = r.get("label") or ""
            is_pick = (lbl == a and b_pat.search(body)) or (lbl == b and a_pat.search(body))
            if is_pick:
                picked.append((r["time"], r, page_id, prev_body))
            prev_body = body

    picked.sort(key=lambda x: x[0])

    labels_in_order = [p[1]["label"] for p in picked]
    turns = len(compress(labels_in_order))

    out = []
    out.append(f"# Cross-page conversation: {a} <-> {b}")
    out.append("")
    out.append("Pages, in the order the pair first bidirectionally exchanged on each:")
    out.append("")
    first_time_per_page = {}
    for t, r, page_id, _ in picked:
        first_time_per_page.setdefault(page_id, t)
    for page_id in sorted(first_time_per_page, key=lambda p: first_time_per_page[p]):
        page_picks = [p for p in picked if p[2] == page_id]
        out.append(f"- `{page_id}` — first pair-message {first_time_per_page[page_id]}, {len(page_picks)} pair-messages")
    out.append("")
    out.append(f"Total pair-messages across all pages: {len(picked)}  ")
    out.append(f"Alternating turns (interleaved by time): {turns}  ")
    out.append(f"Wall time: {picked[0][0]} to {picked[-1][0]}")
    out.append("")
    out.append("Selection rule: revisions on any of these pages whose writer is one of the two AND whose body mentions the other. Rows below are interleaved by time across pages; each block shows only lines added vs. the immediately previous revision on the *same page* (append-only diff, per page).")
    out.append("")

    current_page = None
    for t, r, page_id, prev_body in picked:
        if page_id != current_page:
            out.append(f"---")
            out.append(f"### On page: `{page_id}`")
            out.append("")
            current_page = page_id
        body = r["body"] or ""
        prev_lines = set(prev_body.split("\n"))
        new_lines = [l for l in body.split("\n") if l not in prev_lines]
        seq = r["rev_id"].split("@")[-1]
        out.append(f"#### rev @{seq} — {r['time']} — **{r['label']}**")
        out.append("")
        out.append("```")
        for l in new_lines:
            out.append(l)
        out.append("```")
        out.append("")

    out_path.write_text("\n".join(out))
    print(f"Wrote {out_path}: {turns} turns / {len(picked)} pair-messages across {len(pages)} pages")


if __name__ == "__main__":
    args = sys.argv[1:]
    a, b, out_md = args[:3]
    pages = args[3:]
    render(a, b, Path(out_md), pages)
