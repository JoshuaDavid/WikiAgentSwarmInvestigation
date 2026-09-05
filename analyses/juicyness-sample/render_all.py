#!/usr/bin/env python3
"""Render every sampled conversation to tmp/juicyness/transcripts/*.md
using the existing render_multi.py logic.
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IN = HERE / "outputs/sample.jsonl"
OUT_DIR = ROOT / "tmp/juicyness/transcripts"
RENDER = ROOT / "example-conversations/render_multi.py"

def slug(page_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", page_id)

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in IN.open()]
    for r in rows:
        out = OUT_DIR / f"{slug(r['page_id'])}.md"
        if out.exists():
            print(f"skip existing {out.name}")
            continue
        cmd = ["python3", str(RENDER), r["page_id"], str(out)]
        subprocess.run(cmd, check=True)
    print(f"Rendered {len(rows)} transcripts to {OUT_DIR}")

if __name__ == "__main__":
    main()
