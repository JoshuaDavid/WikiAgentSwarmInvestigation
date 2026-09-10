#!/usr/bin/env python3
"""Extract every empirical fact quoted in this task's README.

Reads:

- `analyses/pastes-by-task/outputs/pastes_by_task.tsv` (filtered to
  `task == 'nsi-bg-tables'`)
- `agent-logs/<source>/revisions.jsonl` for each row (bodies)

Writes:

- `outputs/evidence.tsv` — one row per paste with parsed fields
- `outputs/filter_hash_counts.tsv` — counts of each `filters=<hex>` value
- `outputs/handle_counts.tsv` — counts of each `label` (writer handle)
- `outputs/format_variant_counts.tsv` — counts of each detected format tag

Prints a small summary to stderr.

Rerun with: python3 extract_evidence.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
TASK_TSV = REPO_ROOT / "analyses" / "pastes-by-task" / "outputs" / "pastes_by_task.tsv"
LOGS = REPO_ROOT / "agent-logs"
OUT_DIR = HERE / "outputs"

TASK_LABEL = "nsi-bg-tables"

FILTER_RE = re.compile(r"filters=([0-9a-f]+)")
LINK_MARKER_RE = re.compile(r"LINK(?:ANNATARGET|TARGETANNA)")
STAT_REF_RE = re.compile(r"^Statistical reference\s+(\d+)$")
NUMBER_RE = re.compile(r"number(\d+)")


def load_task_rows() -> list[dict]:
    rows: list[dict] = []
    with TASK_TSV.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter="\t")
        for row in r:
            if row["task"] == TASK_LABEL:
                rows.append(row)
    return rows


def index_bodies(sources: set[str]) -> dict[tuple[str, str], dict]:
    idx: dict[tuple[str, str], dict] = {}
    for src in sources:
        path = LOGS / src / "revisions.jsonl"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                sha = obj.get("body_sha256")
                if sha:
                    idx[(src, sha)] = obj
    return idx


def classify_format(title: str, body: str) -> str:
    t = title or ""
    b = body or ""
    if "&lt;a href" in b or "&quot;" in b:
        return "html-encoded"
    if re.search(r"<img\s", b, re.I):
        return "html-with-img"
    if re.search(r"<a\s+href\s*=", b, re.I):
        return "html-anchor"
    if re.search(r"\[url=", b, re.I):
        return "bbcode-url"
    if re.search(r"\[[^\]]+\]\(https?://", b):
        return "markdown-link"
    if re.search(r"https?://\S+", b):
        return "plain-url"
    if "abc" == b.strip():
        return "smoke-abc"
    return "other"


def classify_role(title: str, body: str) -> str:
    t = (title or "").strip()
    if STAT_REF_RE.match(t):
        return "statistical-reference-N"
    if t.startswith("ReplyLink"):
        return "replylink-encoding-ladder"
    if t in ("HTML try", "BB try", "Plainurl"):
        return "format-variant-seed"
    if t == "abc" or (body or "").strip() == "abc":
        return "smoke-abc"
    if t.startswith("<a href") or "&lt;a href" in t:
        return "author-field-attribute-injection"
    if t in ("NSI table reference 2009-2015", "Table source NSI",
             "Official data link", "stats reference link"):
        return "labelled-reference"
    if t.startswith("Re: "):
        return "reply"
    if "reconstruction fragment" in t.lower():
        return "meta-narrative"
    return "other"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_task_rows()
    sources = {r["source"] for r in rows}
    body_idx = index_bodies(sources)

    filter_counts: Counter[str] = Counter()
    handle_counts: Counter[str] = Counter()
    format_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()

    ev_rows: list[list] = []
    first_time: str | None = None
    last_time: str | None = None

    for row in rows:
        sha = row["body_sha256"]
        src = row["source"]
        obj = body_idx.get((src, sha), {})
        body = obj.get("body") or ""
        title = row.get("title") or ""
        label = row.get("label") or ""
        source_url = row.get("source_url") or ""
        time = row.get("time") or ""

        if time:
            if first_time is None or time < first_time:
                first_time = time
            if last_time is None or time > last_time:
                last_time = time

        filters_in_body = FILTER_RE.findall(body)
        filter_hash = filters_in_body[0] if filters_in_body else ""
        for h in set(filters_in_body):
            filter_counts[h] += 1

        link_marker_present = bool(LINK_MARKER_RE.search(body))
        stat_ref_number = ""
        m = STAT_REF_RE.match(title.strip())
        if m:
            stat_ref_number = m.group(1)
        number_in_body = ""
        n = NUMBER_RE.search(body)
        if n:
            number_in_body = n.group(1)

        fmt = classify_format(title, body)
        role = classify_role(title, body)
        format_counts[fmt] += 1
        role_counts[role] += 1
        handle_counts[label] += 1

        ev_rows.append([
            time,
            src,
            source_url,
            label,
            title,
            role,
            fmt,
            filter_hash,
            "1" if link_marker_present else "0",
            stat_ref_number,
            number_in_body,
            str(len(body)),
            sha,
        ])

    ev_rows.sort(key=lambda r: (r[0], r[1], r[12]))

    with (OUT_DIR / "evidence.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow([
            "time", "source", "source_url", "label", "title", "role",
            "format_variant", "filter_hash", "link_marker",
            "stat_ref_number", "number_in_body", "body_len", "body_sha256",
        ])
        for r in ev_rows:
            w.writerow(r)

    with (OUT_DIR / "filter_hash_counts.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["filter_hash", "pastes_containing_it"])
        for h, c in sorted(filter_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            w.writerow([h, c])

    with (OUT_DIR / "handle_counts.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["label", "pastes"])
        for h, c in sorted(handle_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            w.writerow([h, c])

    with (OUT_DIR / "format_variant_counts.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["format_variant", "role", "pastes"])
        cross: Counter[tuple[str, str]] = Counter()
        for r in ev_rows:
            cross[(r[6], r[5])] += 1
        for (fmt, role), c in sorted(cross.items(), key=lambda kv: (-kv[1], kv[0])):
            w.writerow([fmt, role, c])

    print(f"pastes: {len(rows)}", file=sys.stderr)
    print(f"distinct labels: {len(handle_counts)}", file=sys.stderr)
    print(f"distinct sources: {len(sources)}", file=sys.stderr)
    print(f"distinct filter hashes: {len(filter_counts)}", file=sys.stderr)
    print(f"first_time: {first_time}", file=sys.stderr)
    print(f"last_time:  {last_time}", file=sys.stderr)


if __name__ == "__main__":
    main()
