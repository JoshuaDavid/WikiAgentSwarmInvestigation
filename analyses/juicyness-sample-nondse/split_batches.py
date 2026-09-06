#!/usr/bin/env python3
"""Split the rendered non-dse transcripts into 5 balanced batches.

Round-robin over weight-descending order, so each subagent sees a mix
of large and small scenes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDS = HERE / "outputs" / "candidates.jsonl"
TXN = Path("/collusionwiki/tmp/juicyness-nondse/transcripts")
OUT = HERE / "outputs"

N_BATCHES = 5


def slug(page_id: str) -> str:
    wiki, name = page_id.split("/", 1)
    return f"{wiki}-{name.replace('/', '-')}"


def main() -> None:
    rows = [json.loads(l) for l in CANDS.open()]
    rows.sort(key=lambda r: -r["weight"])
    batches = [[] for _ in range(N_BATCHES)]
    for i, r in enumerate(rows):
        path = TXN / f"{slug(r['page_id'])}.md"
        assert path.exists(), path
        batches[i % N_BATCHES].append({
            "page_id": r["page_id"],
            "wiki": r["wiki"],
            "weight": r["weight"],
            "n_revs": r["n_revs"],
            "n_labels": r["n_labels"],
            "transcript_path": str(path),
        })
    for i, b in enumerate(batches, 1):
        (OUT / f"batch_{i}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in b) + "\n"
        )
        print(f"batch_{i}: {len(b)} files, weight_total={sum(r['weight'] for r in b)}")


if __name__ == "__main__":
    main()
