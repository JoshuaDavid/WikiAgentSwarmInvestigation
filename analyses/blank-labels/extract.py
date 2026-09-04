#!/usr/bin/env python3
"""Extract non-stub blank-label revisions from revisions.jsonl.

The prowiki wiki farm has 899 revisions with an empty `label` field. All of
them are on the `probier` sandbox wiki. Of those, ~541 are the ProWiki
new-page stub ("Describe the new page here.") — auto-written when a page is
created but before the agent submits real content. The remaining ~358 are
what we want: sandbox writes where the agent chose not to set a username
but did submit real content.

Output: outputs/blank_nonstub.jsonl — one row per non-stub blank-label
revision, verbatim (no field selection).
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
IN_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"
OUT_PATH = HERE / "outputs" / "blank_nonstub.jsonl"

STUB = "Describe the new page here."


def main() -> None:
    n_scanned = 0
    n_blank = 0
    n_stub = 0
    n_written = 0
    with IN_PATH.open("r", encoding="utf-8") as rf, OUT_PATH.open("w", encoding="utf-8") as wf:
        for line in rf:
            n_scanned += 1
            rev = json.loads(line)
            if rev.get("label") != "":
                continue
            n_blank += 1
            body = rev.get("body") or ""
            if body == STUB:
                n_stub += 1
                continue
            wf.write(line if line.endswith("\n") else line + "\n")
            n_written += 1

    print(f"scanned: {n_scanned}", file=sys.stderr)
    print(f"blank-label rows: {n_blank}", file=sys.stderr)
    print(f"stub-only ('{STUB}'): {n_stub}", file=sys.stderr)
    print(f"non-stub blank-label rows written: {n_written}", file=sys.stderr)
    print(f"wrote {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
