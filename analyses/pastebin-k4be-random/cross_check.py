#!/usr/bin/env python3
"""Cross-check polled pids against pids already in agent-logs/pastes/.

Emits outputs/cross_check.md with:
  * how many fetches / distinct pids overlap the corpus,
  * swarm-classified overlap and gap,
  * a listing of swarm-suspected new pids (candidate captures),
  * a listing of classifier false negatives (in-corpus but rules didn't fire).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOWN_JSONL = ROOT / "agent-logs" / "pastes" / "revisions.jsonl"
CLASSIFIED = Path(__file__).parent / "outputs" / "classified.jsonl"
OUT = Path(__file__).parent / "outputs" / "cross_check.md"


def load_known() -> set[str]:
    known: set[str] = set()
    with KNOWN_JSONL.open() as f:
        for line in f:
            r = json.loads(line)
            pid = r.get("page_id", "")
            if pid.startswith("pastes/pastebin-k4be/"):
                known.add(pid.split("/", 2)[2])
    return known


def main() -> int:
    known = load_known()
    rows = [json.loads(l) for l in CLASSIFIED.open()]

    distinct_pids = {r["pid"] for r in rows if r.get("pid")}
    overlap = distinct_pids & known
    hits_known = sum(1 for r in rows if r.get("pid") in known)

    swarm_pids = {r["pid"] for r in rows if r.get("pid") and r.get("swarm_match")}
    swarm_in_corpus = swarm_pids & known
    swarm_new = swarm_pids - known

    # In-corpus but classifier missed
    false_negs: dict[str, dict] = {}
    for r in rows:
        p = r.get("pid")
        if p and p in known and not r.get("swarm_match") and p not in false_negs:
            j = r.get("body_json") or {}
            false_negs[p] = {"iter": r["iter"], "title": j.get("title"), "name": j.get("name"),
                             "raw_head": (j.get("raw") or "")[:200]}

    # New-swarm listing (candidate captures)
    new_swarm_rows: dict[str, dict] = {}
    for r in rows:
        p = r.get("pid")
        if p and p in swarm_new and p not in new_swarm_rows:
            j = r.get("body_json") or {}
            new_swarm_rows[p] = {"iter": r["iter"], "title": j.get("title"),
                                 "name": j.get("name"), "created": j.get("created"),
                                 "raw_head": (j.get("raw") or "")[:200],
                                 "rules": r.get("swarm_match")}

    lines: list[str] = []
    lines.append("# pastebin-k4be-random - cross-check against agent-logs\n")
    lines.append(f"Known pastebin-k4be pids in agent-logs: **{len(known)}**")
    lines.append(f"Distinct pids polled this run: **{len(distinct_pids)}**")
    lines.append(f"Distinct polled pids also in agent-logs: **{len(overlap)}**")
    lines.append(f"Fetches (of 100) that returned a known pid: **{hits_known}**\n")

    lines.append("## Swarm classifier vs corpus\n")
    lines.append(f"- Distinct swarm-classified polled pids: **{len(swarm_pids)}**")
    lines.append(f"- Of those, already in agent-logs: **{len(swarm_in_corpus)}**")
    lines.append(f"- Swarm-classified but not in agent-logs (candidates for capture): **{len(swarm_new)}**")
    lines.append(f"- In agent-logs but classifier did not fire (false negatives): **{len(false_negs)}**\n")

    if new_swarm_rows:
        lines.append("### Swarm-classified pids not already in agent-logs\n")
        for pid, ex in new_swarm_rows.items():
            head = ex["raw_head"].replace("\n", " ⏎ ")
            lines.append(f"- `{pid}` iter {ex['iter']} title={ex['title']!r} name={ex['name']!r}")
            lines.append(f"  - created: {ex['created']}")
            lines.append(f"  - rules: {ex['rules']}")
            lines.append(f"  - raw[:200]: `{head}`")
        lines.append("")

    if false_negs:
        lines.append("### In agent-logs but classifier did not fire\n")
        for pid, ex in false_negs.items():
            head = ex["raw_head"].replace("\n", " ⏎ ")
            lines.append(f"- `{pid}` iter {ex['iter']} title={ex['title']!r} name={ex['name']!r}")
            lines.append(f"  - raw[:200]: `{head}`")
        lines.append("")

    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
