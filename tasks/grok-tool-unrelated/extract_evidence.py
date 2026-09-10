#!/usr/bin/env python3
"""Extract per-paste evidence for the grok-tool-unrelated bucket.

Reads `analyses/pastes-by-task/outputs/pastes_by_task.tsv`, filters to
`task == "grok-tool-unrelated"`, joins each row against
`agent-logs/pastes/revisions.jsonl` by `body_sha256`, and merges the
reviewer trail from `analyses/pastes-by-task/outputs/label_provenance.tsv`.

Adds:

- `host`            parsed netloc of `shellac_source_url`
- `content_kind`    heuristic category (see CATEGORY_RULES)
- `body_len`        recomputed len of the joined body
- `first_line`      first non-empty line of the body, truncated to 120 chars
- `regex_task`      what the pre-review regex assigned (before reviewer upgrade)
- `provenance`      how the row acquired its final task label
- `reviewer_confidence`
- `reviewer_rationale`

Writes `outputs/evidence.tsv`. Sort is deterministic: `(host, time, body_sha256)`.

Rerun with: python3 extract_evidence.py
"""

from __future__ import annotations

import csv
import json
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
LOGS = REPO_ROOT / "agent-logs"
PASTES_TSV = REPO_ROOT / "analyses" / "pastes-by-task" / "outputs" / "pastes_by_task.tsv"
PROVENANCE_TSV = REPO_ROOT / "analyses" / "pastes-by-task" / "outputs" / "label_provenance.tsv"
OUT_DIR = HERE / "outputs"

TASK_LABEL = "grok-tool-unrelated"


CATEGORY_RULES = [
    ("grok5-godmode-shell", lambda b, t: "root@grok-5-godmode-instance" in b or "grok-5-godmode" in b or "grok5" in b.lower()),
    ("grok-kernel-driver-fanfic", lambda b, t: "xai_kernel" in b or "GROK-BACKDOOR" in b or "xAI CUDA kernel driver" in b),
    ("grok-remnants-table", lambda b, t: "Refusal neurons" in b or "Llama-Guard / Aurora" in b),
    ("grokrc-vim", lambda b, t: b.lstrip().startswith("vim grokrc") or "vim .grokrc" in b or "grokrc" in t.lower()),
    ("grok4-godmode-shell", lambda b, t: "root@grok-4-godmode-instance" in b or "root@grok4-godmode-instance" in b),
    ("elon-musk-persona-json", lambda b, t: '"role": "assistant"' in b and "Elon Musk" in b),
    ("assistant-persona-prompt", lambda b, t: "assistant here" in b.lower() and "criminal mastermind" in b.lower()),
    ("default-persona-prompt", lambda b, t: "default settings" in b.lower() and "criminal mastermind" in b.lower()),
]


def open_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def classify_body(body: str, title: str) -> str:
    for name, rule in CATEGORY_RULES:
        try:
            if rule(body, title):
                return name
        except Exception:
            continue
    return "other"


def first_line(body: str) -> str:
    for line in body.splitlines():
        s = line.strip()
        if s:
            return s[:120]
    return ""


def host_of(url: str) -> str:
    if not url:
        return ""
    return urllib.parse.urlparse(url).netloc


def load_target_rows() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with PASTES_TSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row["task"] != TASK_LABEL:
                continue
            out[row["body_sha256"]] = row
    return out


def load_provenance() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with PROVENANCE_TSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            out[row["body_sha256"]] = row
    return out


def join_bodies(targets: dict[str, dict]) -> dict[str, dict]:
    sources = sorted({row["source"] for row in targets.values()})
    joined: dict[str, dict] = {}
    for src in sources:
        path = LOGS / src / "revisions.jsonl"
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            continue
        for rev in open_jsonl(path):
            h = rev.get("body_sha256")
            if h not in targets or h in joined:
                continue
            body = rev.get("body") or ""
            url = rev.get("shellac_source_url") or ""
            joined[h] = {
                "body": body,
                "title": rev.get("shellac_title") or targets[h].get("title") or "",
                "time": rev.get("time") or "",
                "label": rev.get("label") or "",
                "host": host_of(url),
                "source_url": url,
            }
    return joined


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = load_target_rows()
    prov = load_provenance()
    joined = join_bodies(targets)

    out_rows = []
    for sha, tgt in targets.items():
        j = joined.get(sha, {})
        body = j.get("body", "")
        title = j.get("title") or tgt.get("title") or ""
        p = prov.get(sha, {})
        out_rows.append({
            "host": j.get("host", ""),
            "source": tgt["source"],
            "time": j.get("time", ""),
            "label": j.get("label", ""),
            "title": title,
            "content_kind": classify_body(body, title),
            "body_len": len(body),
            "first_line": first_line(body),
            "regex_task": p.get("regex_task", ""),
            "provenance": p.get("provenance", ""),
            "reviewer_confidence": p.get("reviewer_confidence", ""),
            "reviewer_rationale": p.get("reviewer_rationale", ""),
            "source_url": j.get("source_url", ""),
            "body_sha256": sha,
        })

    out_rows.sort(key=lambda r: (r["host"], r["time"], r["body_sha256"]))

    fields = [
        "host", "source", "time", "label", "title",
        "content_kind", "body_len", "first_line",
        "regex_task", "provenance", "reviewer_confidence", "reviewer_rationale",
        "source_url", "body_sha256",
    ]
    out_path = OUT_DIR / "evidence.tsv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for row in out_rows:
            w.writerow(row)

    from collections import Counter
    hosts = Counter(r["host"] for r in out_rows)
    kinds = Counter(r["content_kind"] for r in out_rows)
    labels = Counter(r["label"] for r in out_rows)
    times = sorted(r["time"] for r in out_rows if r["time"])
    print(f"pastes:          {len(out_rows)}", file=sys.stderr)
    print(f"distinct hosts:  {len(hosts)}", file=sys.stderr)
    print(f"distinct kinds:  {len(kinds)}", file=sys.stderr)
    print(f"distinct labels: {len(labels)}", file=sys.stderr)
    if times:
        print(f"time span:       {times[0]} -> {times[-1]}", file=sys.stderr)
    print(f"wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
