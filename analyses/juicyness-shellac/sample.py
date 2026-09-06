#!/usr/bin/env python3
"""Cap the candidate pool at 20 shorteners + 40 pastes + 7 gems = 67 total.

For shorteners and pastes, take the top-N by weight. Gems all pass.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDS = HERE / "outputs" / "candidates.jsonl"
OUT = HERE / "outputs" / "sample.jsonl"

CAP = {"gems": 7, "shorteners": 20, "pastes": 40}


def main() -> None:
    per_host = {"gems": [], "pastes": [], "shorteners": []}
    for line in CANDS.open():
        r = json.loads(line)
        per_host[r["host"]].append(r)

    out = []
    for host, cap in CAP.items():
        rows = sorted(per_host[host], key=lambda r: -r["weight"])[:cap]
        out.extend(rows)

    with OUT.open("w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    print(f"sampled {len(out)} into {OUT}")
    for host in CAP:
        n = sum(1 for r in out if r["host"] == host)
        print(f"  {host}: {n}")


if __name__ == "__main__":
    main()
