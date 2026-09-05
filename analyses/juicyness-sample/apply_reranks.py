#!/usr/bin/env python3
"""Consume the annotators' rerank_batch_{1..5}.jsonl. For each row where
new_score != old_score, move the transcript file between score directories.
If new_score < 7, delete the file from the by-juicyness tree.

Then regenerate example-conversations/by-juicyness/scores.jsonl and README.md.
"""
from __future__ import annotations
import json
import re
import shutil
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RERANK_DIR = ROOT / "tmp/juicyness"
DEST = ROOT / "example-conversations/by-juicyness"
PRIOR_SCORES = DEST / "scores.jsonl"

def slug(page_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", page_id)

def main():
    reranks = {}
    for i in (1, 2, 3, 4, 5):
        p = RERANK_DIR / f"rerank_batch_{i}.jsonl"
        for line in p.open():
            r = json.loads(line)
            reranks[r["page_id"]] = r

    prior = {r["page_id"]: r for r in (json.loads(l) for l in PRIOR_SCORES.open())}

    moved = []
    removed = []
    for pid, rr in reranks.items():
        old, new = rr["old_score"], rr["new_score"]
        if old == new:
            continue
        src = DEST / str(old) / f"{slug(pid)}.md"
        if not src.exists():
            print(f"WARN: source missing for rerank {pid}: {src}")
            continue
        if new < 7:
            src.unlink()
            removed.append(pid)
            print(f"REMOVED {pid}: {old} -> {new} (below 7)")
        else:
            dst_dir = DEST / str(new)
            dst_dir.mkdir(exist_ok=True)
            dst = dst_dir / f"{slug(pid)}.md"
            shutil.move(str(src), str(dst))
            moved.append((pid, old, new))
            print(f"MOVED   {pid}: {old} -> {new}")

    new_scores = {}
    for pid, prior_row in prior.items():
        rr = reranks.get(pid)
        if not rr:
            new_scores[pid] = prior_row
            continue
        if rr["new_score"] < 7:
            continue
        row = dict(prior_row)
        row["score"] = rr["new_score"]
        row["file"] = f"{rr['new_score']}/{slug(pid)}.md"
        if rr["new_score"] != rr["old_score"]:
            row["rationale"] = rr["reason"]
            row["prior_score"] = rr["old_score"]
        new_scores[pid] = row

    by_score = defaultdict(list)
    for row in new_scores.values():
        by_score[row["score"]].append(row)

    out_rows = []
    for sc in sorted(by_score, reverse=True):
        for r in sorted(by_score[sc], key=lambda r: -(r.get("weight") or 0)):
            out_rows.append(r)
    (DEST / "scores.jsonl").write_text("\n".join(json.dumps(r) for r in out_rows) + "\n")

    n_kept = len(out_rows)
    lines = []
    lines.append("# by-juicyness")
    lines.append("")
    lines.append("Sampled wiki-page transcripts scored 7-10 for \"juicyness\" (how interesting the coordination scene is to an incident investigator).")
    lines.append("")
    lines.append("Selection: 60 pages drawn from `../../analyses/juicyness-sample/outputs/candidates.jsonl` (241 pages) via weighted-random sampling without replacement, weight = n_participants x n_revs. Farm front pages (`WillkommenImWiki`, `StartSeite`, `TestSeite`) excluded as noise. Scored by five parallel general-purpose subagents against a fixed rubric; a second pass of five parallel subagents wrote each transcript's `## Juicy details` section and proposed reranks. See `../../analyses/juicyness-sample/README.md` for method and rubric.")
    lines.append("")
    lines.append("Each transcript's `## Juicy details` section lists the specific interesting things the agents did on that page (added by the annotation pass). A third pass adds `## Overview for Humans` (a one-paragraph nut graf) and `## Support for specific claims in overview` (per-claim rev pointers so the overview is checkable). See [`FORMAT.md`](FORMAT.md) for the target format and the draft-check-correct process new annotators must follow.")
    lines.append("")
    lines.append("Scores <7 are dropped from this directory but retained in `../../analyses/juicyness-sample/outputs/scores.jsonl` (all 60 first-pass rows). Rendered transcripts for the dropped rows are not committed.")
    lines.append("")
    lines.append(f"Kept: {n_kept} conversations after annotation-pass reranks (started at 41; net change from reranks noted below).")
    lines.append("")
    if moved or removed:
        lines.append("## Annotation-pass rerank log")
        lines.append("")
        for pid, old, new in moved:
            rr = reranks[pid]
            lines.append(f"- `{pid}`: **{old} → {new}**. {rr['reason']}")
        for pid in removed:
            rr = reranks[pid]
            lines.append(f"- `{pid}`: **{rr['old_score']} → {rr['new_score']}** (removed from tree, below cutoff). {rr['reason']}")
        lines.append("")

    for sc in sorted(by_score, reverse=True):
        lines.append(f"## Score {sc} ({len(by_score[sc])})")
        lines.append("")
        lines.append("| page | participants | revs | rationale |")
        lines.append("|---|---:|---:|---|")
        for r in sorted(by_score[sc], key=lambda r: -(r.get("weight") or 0)):
            lines.append(f"| [{r['page_id']}]({r['file']}) | {r['n_participants']} | {r['n_revs']} | {r['rationale']} |")
        lines.append("")

    (DEST / "README.md").write_text("\n".join(lines))
    print(f"Wrote {DEST/'README.md'} ({n_kept} conversations)")
    print(f"Moved: {len(moved)}, removed: {len(removed)}")

if __name__ == "__main__":
    main()
