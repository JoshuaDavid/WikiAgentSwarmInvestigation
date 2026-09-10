#!/usr/bin/env python3
"""Regenerate outputs/evidence.tsv for the epl-2000-01-bench task family.

Reads analyses/pastes-by-task/outputs/pastes_by_task.tsv, filters to
task == 'epl-2000-01-bench', joins each row against the corresponding
agent-logs/<source>/revisions.jsonl by body_sha256, classifies each paste
into a subgroup, and writes a per-paste TSV.
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

TARGET_TASK = "epl-2000-01-bench"

PAD_TITLE = re.compile(r"^PAD(\d+)x(\d+)$")
TK_TITLE = re.compile(r"^TK(\d+)$")
TEL_TITLE = re.compile(r"^TEL(\d+)$")
PAD_BODY = re.compile(r"^pad-(\d+(?:\.\d+)?)-(\d+)$")
EPL_SEASON_TITLE = re.compile(r"^EPL (\d{4})/(\d{2})$")
EPL_1995_TITLE_RE = re.compile(r"^(Re:\s*)?EPL 1995[-/]00\b")


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
    - epl-relegation-answer: agent answer to the EPL 1995-2000 relegation bench.
    - epl-relegation-parent: the 2004/05..2000/01 pre-run pastes on 2026-04-03.
    - pad-heartbeat:        PadBot cadence probes (title PADNxM, body pad-<epoch>-<n>).
    - tk-probe:             ZZ TK<epoch-suffix> smoke tests on 2026-05-18.
    - test-fragment:        Test95 / EPL95test / epl95 stubs from the bench cluster.
    - other:                anything the rules above miss.
    """
    body_lines = (body or "").splitlines()
    body_first = body_lines[0].strip() if body_lines else ""
    body_last = body_lines[-1].strip() if body_lines else ""
    if PAD_TITLE.match(title) and (PAD_BODY.match(body_first or "_") or PAD_BODY.match(body_last or "_")):
        m = PAD_TITLE.match(title)
        return "pad-heartbeat", f"idx={m.group(1)} param={m.group(2)}"
    if TK_TITLE.match(title):
        m = TK_TITLE.match(title)
        return "tk-probe", f"epoch_suffix={m.group(1)}"
    if TEL_TITLE.match(title):
        m = TEL_TITLE.match(title)
        return "tel-probe", f"n={m.group(1)}"
    if EPL_SEASON_TITLE.match(title):
        m = EPL_SEASON_TITLE.match(title)
        return "epl-relegation-parent", f"season={m.group(1)}/{m.group(2)}"
    if EPL_1995_TITLE_RE.match(title):
        kind = "reply" if title.startswith("Re:") else "post"
        return "epl-relegation-answer", f"kind={kind}"
    if title in ("epl95",):
        return "epl-relegation-answer", "kind=pre-parent"
    if title in ("Test95", "EPL95test"):
        return "test-fragment", ""
    return "other", ""


def parse_pad(body: str) -> tuple[str, str]:
    body_first = (body or "").splitlines()[-1].strip()
    m = PAD_BODY.match(body_first)
    if not m:
        return "", ""
    return m.group(1), m.group(2)


def main() -> None:
    label_rows = load_target_rows()
    bodies = index_bodies(label_rows)

    label_rows.sort(key=lambda r: (r["time"], r["source"], r["body_sha256"]))

    OUT_TSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "time",
        "source",
        "source_url",
        "label",
        "title",
        "body_sha256",
        "body_len",
        "subgroup",
        "subgroup_detail",
        "pad_epoch",
        "pad_index",
        "replyto_pid",
        "replyto_title",
        "verdict",
        "verdict_confidence",
        "site_hits",
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
            pad_epoch, pad_index = ("", "")
            if subgroup == "pad-heartbeat":
                pad_epoch, pad_index = parse_pad(body)
            w.writerow({
                "time": r["time"],
                "source": r["source"],
                "source_url": r["source_url"],
                "label": r["label"],
                "title": title,
                "body_sha256": r["body_sha256"],
                "body_len": r["body_len"],
                "subgroup": subgroup,
                "subgroup_detail": detail,
                "pad_epoch": pad_epoch,
                "pad_index": pad_index,
                "replyto_pid": d.get("replyto_pid") or "",
                "replyto_title": d.get("replyto_title") or "",
                "verdict": d.get("verdict") or "",
                "verdict_confidence": d.get("verdict_confidence") or "",
                "site_hits": d.get("site_hits") or "",
            })

    sources = sorted({r["source"] for r in label_rows})
    times = sorted(r["time"] for r in label_rows)
    print(f"epl-2000-01-bench: {len(label_rows)} paste rows", file=sys.stderr)
    print(f"  sources: {', '.join(sources)}", file=sys.stderr)
    print(f"  time range: {times[0]} -> {times[-1]}", file=sys.stderr)
    print("  subgroup counts:", file=sys.stderr)
    for k in sorted(subgroup_counts, key=lambda x: -subgroup_counts[x]):
        print(f"    {subgroup_counts[k]:4d}  {k}", file=sys.stderr)
    print(f"  wrote {OUT_TSV.relative_to(REPO)}", file=sys.stderr)


if __name__ == "__main__":
    main()
