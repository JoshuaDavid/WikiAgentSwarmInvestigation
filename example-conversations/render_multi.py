#!/usr/bin/env python3
"""Render a multi-agent coordination-page full transcript.

For each revision on the page, emit the append-only diff (new lines
introduced vs. the immediately previous revision). Precedes the
transcript with a participant table (per-writer rev count and
mention-in / mention-out totals) and the seed revision body.

Usage:
  python3 render_multi.py PAGE_ID OUT_MD
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "agent-logs"


def load_page(page_id: str):
    seen = {}
    for p in sorted(ROOT.glob("*/revisions.jsonl")):
        for line in p.open():
            r = json.loads(line)
            if r["page_id"] != page_id:
                continue
            rid = r["rev_id"]
            existing = seen.get(rid)
            if existing and existing.get("body") and not r.get("body"):
                continue
            seen[rid] = r
    revs = sorted(seen.values(), key=lambda r: r["time"])
    return revs


def render(page_id: str, out_path: Path):
    revs = load_page(page_id)
    writers = list({r["label"] for r in revs if r.get("label")})

    pats = {w: re.compile(r"(?<![A-Za-z0-9_])" + re.escape(w) + r"(?![A-Za-z0-9_])")
            for w in writers}

    out_by_writer = Counter()
    in_by_writer = Counter()
    rev_by_writer = Counter()
    for r in revs:
        mine = r.get("label") or ""
        if not mine:
            continue
        rev_by_writer[mine] += 1
        body = r.get("body") or ""
        for w in writers:
            if w == mine:
                continue
            if pats[w].search(body):
                out_by_writer[mine] += 1
                in_by_writer[w] += 1

    mutual = {w for w in writers if out_by_writer[w] > 0 and in_by_writer[w] > 0}
    active_or_mentioned = {w for w in writers if out_by_writer[w] > 0 or in_by_writer[w] > 0}

    out = []
    out.append(f"# Coordination page: {page_id}")
    out.append("")
    out.append(f"Wall time: {revs[0]['time']} to {revs[-1]['time']}  ")
    out.append(f"Total revisions: {len(revs)}  ")
    out.append(f"Distinct writers: {len(writers)}  ")
    out.append(f"Participants (mentioned or mentioning at least one other writer): {len(active_or_mentioned)}  ")
    out.append(f"Mutual participants (both mentioned and mentioned back): {len(mutual)}")
    out.append("")

    out.append("## Participants")
    out.append("")
    out.append("| writer | revs | out-mentions | in-mentions |")
    out.append("|---|---:|---:|---:|")
    rows = sorted(writers, key=lambda w: (-rev_by_writer[w], -out_by_writer[w] - in_by_writer[w], w))
    for w in rows:
        out.append(f"| `{w}` | {rev_by_writer[w]} | {out_by_writer[w]} | {in_by_writer[w]} |")
    out.append("")

    out.append(f"## Seed revision (rev {revs[0]['rev_id'].split('@')[-1]}, {revs[0]['time']}, `{revs[0]['label']}`)")
    out.append("")
    out.append("```")
    out.append(revs[0]["body"] or "")
    out.append("```")
    out.append("")

    out.append(f"## Full transcript ({len(revs)} revisions, append-only diffs)")
    out.append("")
    prev = revs[0]["body"] or ""
    for i in range(1, len(revs)):
        r = revs[i]
        body = r.get("body") or ""
        prev_lines = set(prev.split("\n"))
        new_lines = [l for l in body.split("\n") if l not in prev_lines]
        seq = r["rev_id"].split("@")[-1]
        out.append(f"### rev @{seq} — {r['time']} — **{r['label']}**")
        out.append("")
        out.append("```")
        for l in new_lines:
            out.append(l)
        out.append("```")
        out.append("")
        prev = body

    out_path.write_text("\n".join(out))
    print(f"Wrote {out_path}: {len(active_or_mentioned)} participants, {len(mutual)} mutual, {len(revs)} revs")


if __name__ == "__main__":
    _, page_id, out_md = sys.argv
    render(page_id, Path(out_md))
