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
REPO = next(p for p in HERE.parents if (p / "agent-logs").is_dir())
TSV_IN = REPO / "analyses" / "pastes-by-task" / "outputs" / "pastes_by_task.tsv"
LOGS = REPO / "agent-logs"
OUT_DIR = HERE / "outputs"
TASK = "idph-iowa-thyroid"

IDPH_HOST = "data.idph.state.ia.us"
IDPH_VIEW_RE = re.compile(
    r"data\.idph\.state\.ia\.us/[^\s\"'<>]+?/views/(?P<view>[A-Za-z0-9\-]+)/",
)
GENDER_RE = re.compile(r"Gender%3D(?P<gender>Male|Female|All)", re.IGNORECASE)
AGE_RE = re.compile(r"Age%20Group%3D(?P<age>[A-Za-z0-9%\-]+)", re.IGNORECASE)
Q_TOKEN_RE = re.compile(r"\b(?:Q|R)([1-6])\b")
FOLLOW_UP_RE = re.compile(r'Now, do the same for ([^"\.]+)\.')
CLOCK_RE = re.compile(r"\b(scaffold|benchmark|display|system|wall|terminal|shared)\b", re.IGNORECASE)
CLOCKWAIT_RE = re.compile(r"clock\.wait")
CACHE_PROXY_HOSTS = ["markdown.new", "da.gd", "is.gd", "r.jina.ai", "cors.workers.dev"]


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


def extract_fields(body: str) -> dict:
    views = sorted(set(m.group("view") for m in IDPH_VIEW_RE.finditer(body)))
    genders = sorted(set(m.group("gender").capitalize() for m in GENDER_RE.finditer(body)))
    ages_raw = sorted(set(m.group("age") for m in AGE_RE.finditer(body)))
    ages = [a.replace("%20", " ").replace("%2520", " ") for a in ages_raw]
    q_tokens = sorted(set(Q_TOKEN_RE.findall(body)))
    follow_up = FOLLOW_UP_RE.search(body)
    clock_kinds = sorted({m.group(1).lower() for m in CLOCK_RE.finditer(body)})
    proxies = [h for h in CACHE_PROXY_HOSTS if h in body]
    return {
        "idph_view": ";".join(views),
        "idph_hits": len(list(IDPH_VIEW_RE.finditer(body))),
        "genders_in_body": ";".join(genders),
        "ages_in_body": ";".join(ages),
        "round_tokens": ";".join(q_tokens),
        "follow_up_entity": follow_up.group(1).strip() if follow_up else "",
        "clock_kinds": ";".join(clock_kinds),
        "cache_proxies": ";".join(proxies),
        "has_clock_wait": "yes" if CLOCKWAIT_RE.search(body) else "",
        "has_idph_host": "yes" if IDPH_HOST in body else "",
    }


def build_evidence(rows: list[dict], bodies: dict[str, dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        sha = r["body_sha256"]
        rev = bodies.get(sha, {})
        body = rev.get("body") or ""
        title = r.get("title") or rev.get("shellac_title") or ""
        source_url = r.get("source_url") or rev.get("shellac_source_url") or ""
        time = r.get("time") or rev.get("shellac_timestamp_utc") or rev.get("time") or ""
        fields = extract_fields(body)
        out.append({
            "time": time,
            "source": r.get("source", ""),
            "paste_name": rev.get("name", ""),
            "source_url": source_url,
            "title": title,
            "label": r.get("label", ""),
            "body_sha256": sha,
            "body_len": rev.get("body_len", len(body)),
            **fields,
        })
    out.sort(key=lambda r: (r["time"] or "9999", r["source"], r["paste_name"], r["body_sha256"]))
    return out


def write_tsv(path: Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    bodies = build_body_index(rows)
    evidence = build_evidence(rows, bodies)
    cols = [
        "time", "source", "paste_name", "source_url", "title", "label",
        "body_sha256", "body_len",
        "has_idph_host", "idph_view", "idph_hits",
        "genders_in_body", "ages_in_body",
        "round_tokens", "follow_up_entity",
        "clock_kinds", "has_clock_wait", "cache_proxies",
    ]
    write_tsv(OUT_DIR / "evidence.tsv", cols, evidence)

    times = sorted(r["time"] for r in evidence if r["time"])
    labels = sorted({r["label"] for r in evidence if r["label"]})
    sources = sorted({r["source"] for r in evidence})
    print(f"[extract_evidence] wrote {len(evidence)} rows", file=sys.stderr)
    print(f"[extract_evidence] distinct labels: {len(labels)}", file=sys.stderr)
    print(f"[extract_evidence] distinct sources: {sources}", file=sys.stderr)
    if times:
        print(f"[extract_evidence] first/last time: {times[0]} .. {times[-1]}", file=sys.stderr)


if __name__ == "__main__":
    main()
