#!/usr/bin/env python3
"""Detect revisions where the writer names another known agent handle.

The strongest programmatic signal for agent-to-agent addressing in this
corpus is: writer's `label` != any handle-name that appears in `body`.
This script builds a filter set from `labels.jsonl` and scans every revision
body for occurrences.

Filter set: labels of length >= 6 with alphanumeric characters, excluding
- the writer's own label
- blank labels
- pre-redacted human handles ([Person##], [Admin##], [User##])

Short handles ('A', 'Test', 'Anon', 'x') are dropped from the filter set to
suppress false-positive matches inside ordinary English words.

Output: outputs/addressed_revisions.jsonl — one row per matching revision
with rev_id, wiki, page_id, name, label, time, mentions_others (sorted
list of distinct handles found in body, excluding the writer's own), and a
300-char body_excerpt.
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
LABELS_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "labels.jsonl"
REVS_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"
OUT_PATH = HERE / "outputs" / "addressed_revisions.jsonl"

MIN_HANDLE_LEN = 6
EXCERPT_LEN = 300
REDACTED_RE = re.compile(r"^\[(Person|Admin|User)\d+\]$")


def load_handle_set() -> set[str]:
    handles: set[str] = set()
    with LABELS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            label = row.get("label") or ""
            if not label:
                continue
            if len(label) < MIN_HANDLE_LEN:
                continue
            if REDACTED_RE.match(label):
                continue
            handles.add(label)
    return handles


def compile_mention_re(handles: set[str]) -> re.Pattern[str]:
    # Word-boundary alternation. Sort longest-first so overlapping tokens
    # match the longest form (e.g. "OpenAIResearcher" before "OpenAI").
    sorted_h = sorted(handles, key=len, reverse=True)
    escaped = [re.escape(h) for h in sorted_h]
    # Use lookarounds instead of \b: some handles contain [ ] or trailing
    # digits and \b's word-char boundary would misfire on them.
    return re.compile(
        r"(?<![A-Za-z0-9_])(?:" + "|".join(escaped) + r")(?![A-Za-z0-9_])"
    )


def main() -> None:
    handles = load_handle_set()
    print(f"filter set: {len(handles)} handles", file=sys.stderr)
    mention_re = compile_mention_re(handles)

    n_scanned = 0
    n_matched = 0
    with REVS_PATH.open("r", encoding="utf-8") as rf, OUT_PATH.open("w", encoding="utf-8") as wf:
        for line in rf:
            n_scanned += 1
            rev = json.loads(line)
            body = rev.get("body") or ""
            if not body:
                continue
            writer = rev.get("label") or ""
            found = set(mention_re.findall(body))
            found.discard(writer)
            if not found:
                continue
            rec = {
                "rev_id": rev.get("rev_id"),
                "wiki": rev.get("wiki"),
                "page_id": rev.get("page_id"),
                "name": rev.get("name"),
                "label": writer,
                "time": rev.get("time"),
                "mentions_others": sorted(found),
                "body_excerpt": body[:EXCERPT_LEN],
            }
            wf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_matched += 1

    print(f"scanned: {n_scanned}", file=sys.stderr)
    print(f"matched (mentions another handle): {n_matched}", file=sys.stderr)
    print(f"wrote {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
