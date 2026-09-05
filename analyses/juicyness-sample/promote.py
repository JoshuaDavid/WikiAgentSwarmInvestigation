#!/usr/bin/env python3
"""Consume scores_batch_{1..5}.jsonl. For every conversation scoring 7+,
copy its transcript to example-conversations/by-juicyness/<score>/<slug>.md
and write example-conversations/by-juicyness/README.md as an index.
"""
from __future__ import annotations
import json
import re
import shutil
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCORES_DIR = HERE / "outputs"
TRANSCRIPTS = ROOT / "tmp/juicyness/transcripts"
SAMPLE = HERE / "outputs/sample.jsonl"
DEST = ROOT / "example-conversations/by-juicyness"

def slug(page_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", page_id)

def main():
    sample = {r["page_id"]: r for r in (json.loads(l) for l in SAMPLE.open())}
    scores = {}
    for i in (1, 2, 3, 4, 5):
        p = SCORES_DIR / f"scores_batch_{i}.jsonl"
        if not p.exists():
            print(f"WARN: {p.name} missing")
            continue
        for line in p.open():
            r = json.loads(line)
            scores[r["page_id"]] = r

    missing_score = [pid for pid in sample if pid not in scores]
    if missing_score:
        print(f"WARN: {len(missing_score)} sampled pages have no score: {missing_score}")

    promoted = defaultdict(list)
    for pid, s in scores.items():
        sc = int(s["score"])
        if sc < 7:
            continue
        src = TRANSCRIPTS / f"{slug(pid)}.md"
        if not src.exists():
            print(f"WARN: {src.name} missing on disk for {pid}")
            continue
        dst_dir = DEST / str(sc)
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / f"{slug(pid)}.md"
        shutil.copy2(src, dst)
        meta = sample.get(pid, {})
        promoted[sc].append({
            "page_id": pid,
            "score": sc,
            "rationale": s.get("rationale", ""),
            "n_participants": meta.get("n_participants"),
            "n_revs": meta.get("n_revs"),
            "weight": meta.get("weight"),
            "first_time": meta.get("first_time"),
            "last_time": meta.get("last_time"),
            "file": f"{sc}/{slug(pid)}.md",
        })

    n_kept = sum(len(v) for v in promoted.values())
    n_scored = len(scores)
    n_below = n_scored - n_kept
    print(f"Promoted {n_kept} / {n_scored} conversations (dropped {n_below} scoring <7).")
    for sc in sorted(promoted, reverse=True):
        print(f"  score {sc}: {len(promoted[sc])} conversations")

    DEST.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for sc in sorted(promoted, reverse=True):
        for r in promoted[sc]:
            all_rows.append(r)
    (DEST / "scores.jsonl").write_text("\n".join(json.dumps(r) for r in all_rows) + "\n")

    lines = []
    lines.append("# by-juicyness")
    lines.append("")
    lines.append("Sampled wiki-page transcripts scored 7-10 for \"juicyness\" (how interesting the coordination scene is to an incident investigator).")
    lines.append("")
    lines.append("Selection: 60 pages drawn from `analyses/juicyness-sample/outputs/candidates.jsonl` (231 pages) via weighted-random sampling without replacement, weight = n_participants x n_revs. Farm front pages (`WillkommenImWiki`, `StartSeite`, `TestSeite`) excluded as noise. Scored by five parallel general-purpose subagents against a fixed rubric. See `analyses/juicyness-sample/README.md` for method and rubric.")
    lines.append("")
    lines.append("Scores <7 are dropped from this directory but retained in `scores.jsonl` (all 60 rows). Rendered transcripts for the dropped rows are not committed.")
    lines.append("")
    lines.append(f"Kept: {n_kept} of {n_scored} scored.")
    lines.append("")
    for sc in sorted(promoted, reverse=True):
        lines.append(f"## Score {sc} ({len(promoted[sc])})")
        lines.append("")
        lines.append("| page | participants | revs | rationale |")
        lines.append("|---|---:|---:|---|")
        for r in sorted(promoted[sc], key=lambda r: -(r["weight"] or 0)):
            lines.append(f"| [{r['page_id']}]({r['file']}) | {r['n_participants']} | {r['n_revs']} | {r['rationale']} |")
        lines.append("")
    (DEST / "README.md").write_text("\n".join(lines))
    print(f"Wrote {DEST/'README.md'} and {DEST/'scores.jsonl'}")

if __name__ == "__main__":
    main()
