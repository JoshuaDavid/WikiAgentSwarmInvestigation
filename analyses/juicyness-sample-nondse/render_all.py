#!/usr/bin/env python3
"""Render every candidate transcript for the non-dse juicyness pass.

Runs `example-conversations/render_multi.py PAGE_ID OUT_MD` once per
candidate in `outputs/candidates.jsonl`. Output filenames use
`<wiki>-<name-with-slashes-hyphenated>.md`, so a fractal page named
`EN/DataUSAQueryBridge927` becomes `fractal-EN-DataUSAQueryBridge927.md`.

Writes to /collusionwiki/tmp/juicyness-nondse/transcripts/.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATES = HERE / "outputs" / "candidates.jsonl"
RENDER = ROOT / "example-conversations" / "render_multi.py"
OUT_DIR = Path("/collusionwiki/tmp/juicyness-nondse/transcripts")


def slug(page_id: str) -> str:
    wiki, name = page_id.split("/", 1)
    return f"{wiki}-{name.replace('/', '-')}"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    fail = 0
    with CANDIDATES.open() as f:
        for line in f:
            r = json.loads(line)
            page_id = r["page_id"]
            out_path = OUT_DIR / f"{slug(page_id)}.md"
            try:
                subprocess.run(
                    ["python3", str(RENDER), page_id, str(out_path)],
                    check=True, capture_output=True, text=True,
                )
                ok += 1
            except subprocess.CalledProcessError as e:
                fail += 1
                print(f"FAIL {page_id}: {e.stderr}", file=sys.stderr)
    print(f"rendered {ok} ok, {fail} failed to {OUT_DIR}")


if __name__ == "__main__":
    main()
