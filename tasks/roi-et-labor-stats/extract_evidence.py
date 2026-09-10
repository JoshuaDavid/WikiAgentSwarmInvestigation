#!/usr/bin/env python3
"""Regenerate outputs/evidence.tsv for the roi-et-labor-stats task family.

Reads analyses/pastes-by-task/outputs/pastes_by_task.tsv, filters to
task == 'roi-et-labor-stats', joins each row against the corresponding
agent-logs/<source>/revisions.jsonl by body_sha256, and writes a
per-paste TSV. Sort is deterministic by (time, source, body_sha256).
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LABELS_TSV = REPO / "analyses" / "pastes-by-task" / "outputs" / "pastes_by_task.tsv"
AGENT_LOGS = REPO / "agent-logs"
OUT_TSV = Path(__file__).resolve().parent / "outputs" / "evidence.tsv"

TARGET_TASK = "roi-et-labor-stats"

BURST1_TITLE_SEG = re.compile(r"^ROIETA (\d{4}) (\d+) (\d{4}) (\d+) (\d{4}) (\d+)$")
BURST1_TITLE_FULL = re.compile(r"^Roi Et province \(TH45\) male studies Q2 2013-2021$")
BURST2_TITLE_SEG = re.compile(r"^ROIETA(\d)\s+(\d{4})\s+(\d+)\s+(\d{4})\s+(\d+)\s+(\d{4})\s+(\d+)$")
BURST2_TITLE_FULL = re.compile(r"^ROIETA(\d)\s+fulldata\s+(\d+(?:\s+\d+)*)$")


def load_target_rows() -> list[dict]:
    rows = []
    with LABELS_TSV.open() as f:
        header = f.readline().rstrip("\n").split("\t")
        for line in f:
            d = dict(zip(header, line.rstrip("\n").split("\t")))
            if d["task"] == TARGET_TASK:
                rows.append(d)
    return rows


def index_bodies(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """Return { (source, body_sha256) -> revision }.

    Every (source, body_sha256) key in the roi-et-labor-stats slice of
    `pastes_by_task.tsv` is unique — the classifier has already deduped.
    Later duplicates in the source file overwrite earlier ones, which is
    harmless: the fields used downstream are byte-identical.
    """
    by_source: dict[str, set[str]] = {}
    for r in rows:
        by_source.setdefault(r["source"], set()).add(r["body_sha256"])
    out: dict[tuple[str, str], dict] = {}
    for source, wanted in by_source.items():
        path = AGENT_LOGS / source / "revisions.jsonl"
        with path.open() as f:
            for line in f:
                d = json.loads(line)
                sha = d.get("body_sha256")
                if sha in wanted:
                    out[(source, sha)] = d
    return out


def classify_subgroup(title: str, body: str) -> tuple[str, str]:
    """Return (subgroup, subgroup_detail).

    Subgroups:
    - burst1-segment  ROIETA <yyyy> <n> <yyyy> <n> <yyyy> <n>  (title carries data)
    - burst1-fulldata Roi Et province (TH45) male studies Q2 2013-2021 (full table in body)
    - burst2-segment  ROIETA<idx> <yyyy> <n> <yyyy> <n> <yyyy> <n>  (title carries data, body=x)
    - burst2-fulldata ROIETA<idx> fulldata <n> <n>  (title carries pair of yearly values, body=x)
    - other
    """
    if BURST1_TITLE_FULL.match(title):
        return "burst1-fulldata", ""
    if BURST1_TITLE_SEG.match(title):
        m = BURST1_TITLE_SEG.match(title)
        years = f"{m.group(1)}-{m.group(5)}"
        return "burst1-segment", f"years={years}"
    if BURST2_TITLE_FULL.match(title):
        m = BURST2_TITLE_FULL.match(title)
        return "burst2-fulldata", f"idx={m.group(1)} values={m.group(2)}"
    if BURST2_TITLE_SEG.match(title):
        m = BURST2_TITLE_SEG.match(title)
        return "burst2-segment", f"idx={m.group(1)} years={m.group(2)}-{m.group(6)}"
    return "other", ""


def main() -> None:
    label_rows = load_target_rows()
    bodies = index_bodies(label_rows)

    label_rows.sort(key=lambda r: (r["time"], r["source"], r["body_sha256"]))

    OUT_TSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "time",
        "source",
        "source_url",
        "paste_id",
        "label",
        "label_source",
        "title",
        "body_sha256",
        "body_len",
        "body_repr",
        "subgroup",
        "subgroup_detail",
    ]

    subgroup_counts: dict[str, int] = {}
    with OUT_TSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        for r in label_rows:
            key = (r["source"], r["body_sha256"])
            d = bodies.get(key, {})
            body = d.get("body") or ""
            title = r["title"]
            subgroup, detail = classify_subgroup(title, body)
            subgroup_counts[subgroup] = subgroup_counts.get(subgroup, 0) + 1
            source_url = r["source_url"] or d.get("source_url") or d.get("shellac_source_url") or ""
            paste_id = source_url.rsplit("/", 1)[-1] if source_url else (d.get("page_id") or "").rsplit("/", 1)[-1]
            body_short = body if len(body) <= 120 else body[:117] + "..."
            body_repr = body_short.replace("\n", "\\n").replace("\t", "\\t")
            w.writerow({
                "time": r["time"],
                "source": r["source"],
                "source_url": source_url,
                "paste_id": paste_id,
                "label": r["label"],
                "label_source": d.get("label_source") or "",
                "title": title,
                "body_sha256": r["body_sha256"],
                "body_len": r["body_len"],
                "body_repr": body_repr,
                "subgroup": subgroup,
                "subgroup_detail": detail,
            })

    sources = sorted({r["source"] for r in label_rows})
    labels = sorted({r["label"] for r in label_rows})
    times = sorted(r["time"] for r in label_rows)
    print(f"{TARGET_TASK}: {len(label_rows)} paste rows", file=sys.stderr)
    print(f"  sources: {', '.join(sources)}", file=sys.stderr)
    print(f"  distinct labels: {len(labels)}", file=sys.stderr)
    print(f"  time range: {times[0]} -> {times[-1]}", file=sys.stderr)
    print("  subgroup counts:", file=sys.stderr)
    for k in sorted(subgroup_counts, key=lambda x: -subgroup_counts[x]):
        print(f"    {subgroup_counts[k]:4d}  {k}", file=sys.stderr)
    print(f"  wrote {OUT_TSV.relative_to(REPO)}", file=sys.stderr)


if __name__ == "__main__":
    main()
