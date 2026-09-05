#!/usr/bin/env python3
"""Weighted random sample without replacement from candidates.jsonl.

Uses Efraimidis-Spirakis A-Res: draw u ~ Uniform(0,1) for each item,
compute key = u ** (1/weight), take the top-K keys. This is exact
weighted sampling without replacement.

Writes outputs/sample.jsonl (60 rows) and prints them.
"""
from __future__ import annotations
import json
import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
IN = HERE / "outputs/candidates.jsonl"
OUT = HERE / "outputs/sample.jsonl"

SEED = 20260905
K = 60

def main():
    rng = random.Random(SEED)
    rows = [json.loads(l) for l in IN.open()]

    keyed = []
    for r in rows:
        u = rng.random()
        key = math.log(u) / r["weight"]
        keyed.append((key, r))
    keyed.sort(key=lambda kr: -kr[0])
    picked = [kr[1] for kr in keyed[:K]]

    with OUT.open("w") as f:
        for r in picked:
            f.write(json.dumps(r) + "\n")

    print(f"Sampled {len(picked)} of {len(rows)}, seed={SEED}")
    print(f"Weight range in sample: {min(r['weight'] for r in picked)} - {max(r['weight'] for r in picked)}")
    print()
    print("Sample (page_id | participants | revs | weight | source):")
    for r in sorted(picked, key=lambda r: -r["weight"]):
        print(f"  {r['weight']:>5}  {r['n_participants']:>3}p x {r['n_revs']:>3}r  [{r['source']:12s}]  {r['page_id']}")

if __name__ == "__main__":
    main()
