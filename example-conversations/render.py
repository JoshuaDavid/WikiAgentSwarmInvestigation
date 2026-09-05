#!/usr/bin/env python3
"""Render a transcript file for a (page_id, agent_a, agent_b) conversation.

For each revision on the page whose writer is A or B AND whose body mentions
the other agent's handle (word-boundary match), print the diff of newly added
lines vs. the previous shown revision.

Usage:
  python3 render.py PAGE_ID AGENT_A AGENT_B OUT_MD
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


def render(page_id: str, a: str, b: str, out_path: Path):
    revs = load_revs()
    page = [r for r in revs.values() if r["page_id"] == page_id]
    page.sort(key=lambda r: r["time"])

    a_pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(a) + r"(?![A-Za-z0-9_])")
    b_pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(b) + r"(?![A-Za-z0-9_])")

    picked = []
    for r in page:
        body = r.get("body") or ""
        if r["label"] == a and b_pat.search(body):
            picked.append(r)
        elif r["label"] == b and a_pat.search(body):
            picked.append(r)

    turns = len(compress([r["label"] for r in picked]))
    first_time = picked[0]["time"] if picked else "-"
    last_time = picked[-1]["time"] if picked else "-"

    out = []
    out.append(f"# Conversation: {a} <-> {b}")
    out.append("")
    out.append(f"Page: `{page_id}`  ")
    out.append(f"Wall time: {first_time} to {last_time}  ")
    out.append(f"Turns: {turns} alternating, from {len(picked)} revisions.  ")
    out.append("Selection rule: revisions on this page whose writer is one of the two AND whose body mentions the other. All rows in the transcript below pass that filter.")
    out.append("")
    out.append("Each `## rev` block shows only the paragraphs *added* in that revision (append-only diff vs. the immediately preceding shown revision). Paragraphs are reproduced verbatim from the wiki `body` field. Some appended paragraphs may be signed by other handles (sibling runs whose text the saving agent posted).")
    out.append("")

    prev = ""
    for r in picked:
        body = r["body"] or ""
        prev_lines = set(prev.split("\n"))
        new_lines = [l for l in body.split("\n") if l not in prev_lines]
        seq = r["rev_id"].split("@")[-1]
        out.append(f"## rev @{seq} — {r['time']} — **{r['label']}**")
        out.append("")
        out.append("```")
        for l in new_lines:
            out.append(l)
        out.append("```")
        out.append("")
        prev = body

    out_path.write_text("\n".join(out))
    print(f"Wrote {out_path}: {turns} turns / {len(picked)} revs")


if __name__ == "__main__":
    _, page_id, a, b, out_md = sys.argv
    render(page_id, a, b, Path(out_md))
