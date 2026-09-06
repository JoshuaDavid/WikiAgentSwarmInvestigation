#!/usr/bin/env python3
"""Split the 67 shellac specimens into 5 batches by round-robin."""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLE = HERE / "outputs" / "sample.jsonl"
TXN = Path("/collusionwiki/tmp/juicyness-shellac/transcripts")
OUT = HERE / "outputs"

N_BATCHES = 5


def slug(page_id: str) -> str:
    host, name = page_id.split("/", 1)
    return f"{host}-{name.replace('/', '-')}"


def main() -> None:
    rows = [json.loads(l) for l in SAMPLE.open()]
    rows.sort(key=lambda r: -r["weight"])
    batches = [[] for _ in range(N_BATCHES)]
    for i, r in enumerate(rows):
        p = TXN / f"{slug(r['page_id'])}.md"
        assert p.exists(), p
        batches[i % N_BATCHES].append({
            "page_id": r["page_id"],
            "host": r["host"],
            "weight": r["weight"],
            "n_revs": r["n_revs"],
            "n_distinct_bodies": r["n_distinct_bodies"],
            "transcript_path": str(p),
        })
    for i, b in enumerate(batches, 1):
        (OUT / f"batch_{i}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in b) + "\n"
        )
        hosts = {}
        for r in b:
            hosts[r["host"]] = hosts.get(r["host"], 0) + 1
        print(f"batch_{i}: {len(b)} files, mix={hosts}")


if __name__ == "__main__":
    main()
