#!/usr/bin/env python3
"""Extract every empirical fact quoted in this task's README.

Reads the two exports that mention `dse/AgentVocabPuzzleRefsJun20`:

- `agent-logs/prowiki/revisions.jsonl` (bodies present)
- `agent-logs/prowiki/events.jsonl`
- `agent-logs/dse/revisions.jsonl` (metadata only, longer window)

Writes the following files under outputs/:

- `vocab_page_body.txt`         verbatim body of the one saved revision
- `vocab_page_lifecycle.tsv`    every event on the page across both exports
- `raceloop_family.tsv`         all revisions by any `RaceLoop\\d+` label
- `vocab_url_hits_by_wiki.tsv`  cross-corpus URL search, one row per wiki
- `vocab_page_crossrefs.tsv`    every other revision that names the page or the label

Rerun with: python3 extract_evidence.py
"""

from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
LOGS = REPO_ROOT / "agent-logs"
OUT_DIR = HERE / "outputs"

PAGE_ID = "dse/AgentVocabPuzzleRefsJun20"
LABEL_RE = re.compile(r"^RaceLoop\d+$")

URL_PATTERNS = [
    "vocabulary.com",
    "wordfinderapi",
    "word.tips",
    "1word.ws",
    "word-of-the-day",
    "letters=quasi",
]


def open_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def write_tsv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(header)
        for row in rows:
            w.writerow(row)


def dump_page_body() -> None:
    for rev in open_jsonl(LOGS / "prowiki" / "revisions.jsonl"):
        if rev.get("page_id") != PAGE_ID:
            continue
        body = rev.get("body") or ""
        (OUT_DIR / "vocab_page_body.txt").write_text(body, encoding="utf-8")
        return
    (OUT_DIR / "vocab_page_body.txt").write_text("", encoding="utf-8")


def dump_lifecycle() -> None:
    rows: list[list] = []
    for rev in open_jsonl(LOGS / "prowiki" / "revisions.jsonl"):
        if rev.get("page_id") != PAGE_ID:
            continue
        rows.append([
            "prowiki",
            "revision",
            rev.get("time") or "",
            rev.get("label") or "",
            rev.get("ip16") or "",
            rev.get("change_summary") or "",
            len(rev.get("body") or ""),
        ])
    for ev in open_jsonl(LOGS / "prowiki" / "events.jsonl"):
        if ev.get("page") != "AgentVocabPuzzleRefsJun20":
            continue
        rows.append([
            "prowiki",
            ev.get("event_type") or "",
            ev.get("time") or "",
            ev.get("actor_label") or "",
            ev.get("ip16") or "",
            ev.get("change_summary") or "",
            "",
        ])
    for rev in open_jsonl(LOGS / "dse" / "revisions.jsonl"):
        if rev.get("page_id") != PAGE_ID:
            continue
        rows.append([
            "dse-metadata",
            "revision",
            rev.get("time") or "",
            rev.get("label") or "",
            rev.get("ip16") or "",
            rev.get("change_summary") or "",
            "",
        ])
    rows.sort(key=lambda r: (r[2], r[0], r[1]))
    write_tsv(
        OUT_DIR / "vocab_page_lifecycle.tsv",
        ["source", "kind", "time", "label", "ip16", "change_summary", "body_len"],
        rows,
    )


def dump_raceloop_family() -> None:
    rows: list[list] = []
    for rev in open_jsonl(LOGS / "prowiki" / "revisions.jsonl"):
        label = rev.get("label") or ""
        if not LABEL_RE.match(label):
            continue
        rows.append([
            rev.get("time") or "",
            label,
            rev.get("ip16") or "",
            rev.get("page_id") or "",
            rev.get("change_summary") or "",
            len(rev.get("body") or ""),
        ])
    rows.sort()
    write_tsv(
        OUT_DIR / "raceloop_family.tsv",
        ["time", "label", "ip16", "page_id", "change_summary", "body_len"],
        rows,
    )


def dump_url_hits_by_wiki() -> None:
    wikis = sorted(
        d for d in os.listdir(LOGS)
        if (LOGS / d / "revisions.jsonl").exists()
    )
    rows: list[list] = []
    for wiki in wikis:
        # First check whether this export ships bodies at all.
        has_body = False
        for rev in open_jsonl(LOGS / wiki / "revisions.jsonl"):
            has_body = bool(rev.get("body"))
            break
        pattern_hits = {pat: 0 for pat in URL_PATTERNS}
        page_hits: set[str] = set()
        for rev in open_jsonl(LOGS / wiki / "revisions.jsonl"):
            body = (rev.get("body") or "").lower()
            if not body:
                continue
            hit_here = False
            for pat in URL_PATTERNS:
                if pat in body:
                    pattern_hits[pat] += 1
                    hit_here = True
            if hit_here:
                page_hits.add(rev.get("page_id") or "")
        rows.append([
            wiki,
            "yes" if has_body else "no",
            len(page_hits),
            sum(pattern_hits.values()),
            ",".join(f"{k}={v}" for k, v in sorted(pattern_hits.items()) if v),
        ])
    write_tsv(
        OUT_DIR / "vocab_url_hits_by_wiki.tsv",
        ["wiki", "bodies_available", "distinct_pages", "total_rev_hits", "per_pattern"],
        rows,
    )


def dump_crossrefs() -> None:
    """Every other revision that mentions the page name or the label."""
    rows: list[list] = []
    needles = ["AgentVocabPuzzleRefsJun20", "RaceLoop603"]
    for rev in open_jsonl(LOGS / "prowiki" / "revisions.jsonl"):
        body = rev.get("body") or ""
        pid = rev.get("page_id") or ""
        label = rev.get("label") or ""
        for n in needles:
            if n in body and not (n == "AgentVocabPuzzleRefsJun20" and pid == PAGE_ID):
                if n == "RaceLoop603" and label == "RaceLoop603":
                    continue
                rows.append([
                    rev.get("time") or "",
                    pid,
                    label,
                    n,
                ])
    write_tsv(
        OUT_DIR / "vocab_page_crossrefs.tsv",
        ["time", "page_id", "label", "needle"],
        rows,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dump_page_body()
    dump_lifecycle()
    dump_raceloop_family()
    dump_url_hits_by_wiki()
    dump_crossrefs()


if __name__ == "__main__":
    main()
