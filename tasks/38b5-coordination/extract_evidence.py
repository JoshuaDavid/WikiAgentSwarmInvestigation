#!/usr/bin/env python3
"""Extract every empirical fact quoted in this task's README.

Reads:
- `analyses/pastes-by-task/outputs/pastes_by_task.tsv` (filter to task label)
- `agent-logs/<source>/revisions.jsonl` (bodies)

Writes `outputs/evidence.tsv`. Rerun with: python3 extract_evidence.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TSV_IN = REPO / "analyses" / "pastes-by-task" / "outputs" / "pastes_by_task.tsv"
LOGS = REPO / "agent-logs"
OUT_DIR = HERE / "outputs"
TASK = "38b5-coordination"

TAG_RE = re.compile(r"\b(38b5[a-z]*)\b", re.IGNORECASE)
THREAD_ID_RE = re.compile(r"\b(38b5[0-9a-f]{6,})\b", re.IGNORECASE)
TS_RE = re.compile(r"(?:ts=|time )?(178164[0-9]{4}(?:\.[0-9]+)?)")
CADENCE_RE = re.compile(r"(\d{1,2}m\d{2})|(\d{1,2}:\d{2}:\d{2})")
QROUND_RE = re.compile(r"\b[QR]([1-6])\b")
AGE_RE = re.compile(r"\b(15-24|25-44|45-64|65-84|85\+|85 and Older)\b")
QUESTION_MARK_RE = re.compile(r"\?")


def open_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def load_rows() -> list[dict]:
    rows: list[dict] = []
    with TSV_IN.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row.get("task") == TASK:
                rows.append(row)
    return rows


def build_body_index(rows: list[dict]) -> dict[str, dict]:
    wanted = {r["body_sha256"] for r in rows}
    sources = sorted({r["source"] for r in rows})
    idx: dict[str, dict] = {}
    for src in sources:
        p = LOGS / src / "revisions.jsonl"
        if not p.exists():
            continue
        for rev in open_jsonl(p):
            sha = rev.get("body_sha256")
            if sha in wanted and sha not in idx:
                idx[sha] = rev
    return idx


def extract_fields(body: str, title: str) -> dict:
    tags = sorted(set(m.group(1).lower() for m in TAG_RE.finditer(body + " " + title)))
    thread_ids = sorted(set(m.group(1).lower() for m in THREAD_ID_RE.finditer(body)))
    epochs = sorted(set(m.group(1) for m in TS_RE.finditer(body)))
    q_rounds = sorted(set(QROUND_RE.findall(body)))
    ages = sorted(set(AGE_RE.findall(body)))
    asks_question = bool(QUESTION_MARK_RE.search(body))
    return {
        "tags_38b5": ",".join(tags),
        "thread_ids": ",".join(thread_ids),
        "epochs_ts": ",".join(epochs),
        "q_rounds": ",".join(q_rounds),
        "age_groups": ",".join(ages),
        "asks_question": "yes" if asks_question else "no",
    }


def paste_id(rev: dict) -> str:
    page = rev.get("page_id") or ""
    if "/" in page:
        return page.split("/", 1)[1]
    return page


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    idx = build_body_index(rows)
    out_rows: list[list] = []
    missing = 0
    for row in rows:
        sha = row["body_sha256"]
        rev = idx.get(sha)
        if rev is None:
            missing += 1
            continue
        body = rev.get("body") or ""
        title = row.get("title") or ""
        fields = extract_fields(body, title)
        one_line = " || ".join(body.strip().split("\n"))[:280]
        out_rows.append([
            row.get("time") or "",
            row.get("source") or "",
            paste_id(rev),
            rev.get("source_url") or "",
            title,
            row.get("label") or "",
            sha,
            rev.get("body_len") or len(body),
            fields["tags_38b5"],
            fields["thread_ids"],
            fields["epochs_ts"],
            fields["q_rounds"],
            fields["age_groups"],
            fields["asks_question"],
            one_line,
        ])
    out_rows.sort(key=lambda r: (r[0] or "", r[6]))
    header = [
        "time",
        "source",
        "paste_id",
        "source_url",
        "title",
        "label",
        "body_sha256",
        "body_len",
        "tags_38b5",
        "thread_ids",
        "epochs_ts",
        "q_rounds",
        "age_groups",
        "asks_question",
        "body_oneline",
    ]
    out_path = OUT_DIR / "evidence.tsv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(header)
        for r in out_rows:
            w.writerow(r)
    distinct_labels = sorted({r[5] for r in out_rows})
    distinct_sources = sorted({r[1] for r in out_rows})
    times = [r[0] for r in out_rows if r[0]]
    print(
        f"[38b5-coordination] rows={len(out_rows)} missing_bodies={missing} "
        f"distinct_labels={len(distinct_labels)} distinct_sources={len(distinct_sources)} "
        f"first_time={min(times) if times else '-'} last_time={max(times) if times else '-'}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
