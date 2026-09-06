#!/usr/bin/env python3
"""Copy specimens scoring 7+ into example-conversations/by-juicyness/<score>/.

Shellac specimens sit alongside dse pages in the pooled by-juicyness/
directory. Their filenames are host-prefixed (`gems-*`, `pastes-*`,
`shorteners-*`) so they do not collide with the `dse-*` files.

Does NOT rewrite the by-juicyness/README.md — that file is edited by hand
because it mixes shellac and dse tables per tier.
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCORES_DIR = HERE / "outputs"
TXN = Path("/collusionwiki/tmp/juicyness-shellac/transcripts")
DEST = ROOT / "example-conversations" / "by-juicyness"


def slug(page_id: str) -> str:
    host, name = page_id.split("/", 1)
    return f"{host}-{name.replace('/', '-')}"


def main() -> None:
    with (SCORES_DIR / "scores.jsonl").open() as f:
        scores = [json.loads(l) for l in f]

    per_tier = {}
    for s in scores:
        if s["score"] < 7:
            continue
        per_tier.setdefault(s["score"], []).append(s)
        tier_dir = DEST / str(s["score"])
        tier_dir.mkdir(parents=True, exist_ok=True)
        src = TXN / f"{slug(s['page_id'])}.md"
        dst = tier_dir / f"{slug(s['page_id'])}.md"
        shutil.copy(src, dst)

    total = sum(len(v) for v in per_tier.values())
    print(f"promoted {total} shellac specimens into {DEST} across tiers {sorted(per_tier)}")
    print("NOTE: by-juicyness/README.md is hand-edited; add shellac subsections manually.")


if __name__ == "__main__":
    main()
