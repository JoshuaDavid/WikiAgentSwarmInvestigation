#!/usr/bin/env python3
"""Split sample into 5 batches by round-robin over weight-sorted order,
so each agent sees a similar mix of big/small scenes.

Emits outputs/batch_{1..5}.jsonl.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
IN = HERE / "outputs/sample.jsonl"
OUT_DIR = HERE / "outputs"

def slug(page_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", page_id)

def main():
    rows = [json.loads(l) for l in IN.open()]
    rows.sort(key=lambda r: -r["weight"])
    batches = [[] for _ in range(5)]
    for i, r in enumerate(rows):
        r = dict(r)
        r["transcript_file"] = f"tmp/juicyness/transcripts/{slug(r['page_id'])}.md"
        batches[i % 5].append(r)
    for i, batch in enumerate(batches, 1):
        out = OUT_DIR / f"batch_{i}.jsonl"
        with out.open("w") as f:
            for r in batch:
                f.write(json.dumps(r) + "\n")
        print(f"batch {i}: {len(batch)} rows, weight range {min(r['weight'] for r in batch)} - {max(r['weight'] for r in batch)}")

if __name__ == "__main__":
    main()
