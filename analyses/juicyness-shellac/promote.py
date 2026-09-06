#!/usr/bin/env python3
"""Copy specimens scoring 7+ into example-conversations/by-shellac/.

Writes a per-score README.md summarising what's there.
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCORES_DIR = HERE / "outputs"
TXN = Path("/collusionwiki/tmp/juicyness-shellac/transcripts")
DEST = ROOT / "example-conversations" / "by-shellac"


def slug(page_id: str) -> str:
    host, name = page_id.split("/", 1)
    return f"{host}-{name.replace('/', '-')}"


def main() -> None:
    scores = []
    with (SCORES_DIR / "scores.jsonl").open() as f:
        for line in f:
            scores.append(json.loads(line))

    sample = {r["page_id"]: r for r in (json.loads(l) for l in
              (SCORES_DIR / "sample.jsonl").open())}

    per_tier = {}
    for s in scores:
        pid = s["page_id"]
        score = s["score"]
        if score < 7:
            continue
        per_tier.setdefault(score, []).append(s)
        tier_dir = DEST / str(score)
        tier_dir.mkdir(parents=True, exist_ok=True)
        src = TXN / f"{slug(pid)}.md"
        dst = tier_dir / f"{slug(pid)}.md"
        shutil.copy(src, dst)

    DEST.mkdir(parents=True, exist_ok=True)
    lines = ["# by-shellac\n"]
    lines.append("Individual content specimens from the shellac-attributed hosts (`gems`, `pastes`, `shorteners`), scored 7+ on the artefact-interestingness rubric. See `analyses/juicyness-shellac/README.md` for method.\n")
    total = sum(len(v) for v in per_tier.values())
    lines.append(f"Kept: {total} specimens across {len(per_tier)} tiers.\n")
    for tier in sorted(per_tier.keys(), reverse=True):
        rows = per_tier[tier]
        lines.append(f"## Score {tier} ({len(rows)})\n")
        lines.append("| specimen | host | rationale |")
        lines.append("|---|---|---|")
        for s in rows:
            info = sample.get(s["page_id"], {})
            link_name = slug(s["page_id"])
            lines.append(f"| [{s['page_id']}]({tier}/{link_name}.md) | `{s['host']}` | {s['rationale']} |")
        lines.append("")
    (DEST / "README.md").write_text("\n".join(lines))
    print(f"promoted {total} specimens across tiers {sorted(per_tier)}")


if __name__ == "__main__":
    main()
