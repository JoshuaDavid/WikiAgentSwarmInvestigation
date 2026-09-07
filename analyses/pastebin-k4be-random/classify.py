#!/usr/bin/env python3
"""Classify one run of pastebin.k4be.pl/api/random responses.

Reads outputs/responses.jsonl and writes:
  * outputs/classified.jsonl - one row per response with a `swarm_match` field.
  * outputs/summary.md - human-readable counts of statuses, dupes, swarm hits.

`swarm_match` is a list of the specific rules that fired. A response is
considered "swarm-suspected" if at least one rule fires. Rules are chosen
against known swarm markers observed in agent-logs/pastes/revisions.jsonl for
pastebin-k4be pastes (see ../../analyses/juicyness-shellac/ for provenance).

Rules
-----
title regexes:
  PAD\\d+x\\d+                    -> PAD-scoreboard pad bot
  TEL\\d{6,}                      -> telegra.ph click-tracker
  TK\\d{5,}                       -> URL-fetcher smoke test
  ROIETA\\d                       -> ROI/ETA benchmark scratch
  Statistical reference \\d+      -> reference-answer paste
  EPL (19|20)\\d\\d[/-]           -> Premier League bench answer
  OAI Transfer                   -> "OAI Transfer <hex>"
  IowaCollab                     -> IowaCollabStatus
  ReplyLink\\d                    -> messenger scratch
  NSI table reference            -> statistical-institute lookup
  Grobots\\d                      -> Grobots benchmark
  ShortURLtest                   -> short-URL smoke test

body substring / regex:
  pad-1\\d{9}\\.\\d+-\\d+          -> PadBot payload id
  CLICKMAYBE                     -> telegra.ph click-through marker
  URLMARK                        -> URL smoke marker
  FRAMEK4                        -> iframe smoke marker
  clock.wait(                    -> task-clock manipulation
  task clock                     -> task-clock vocabulary
  container UTC                  -> two-clock vocabulary
  shared UTC                     -> two-clock vocabulary
  scaffold clock                 -> task-clock vocabulary
  telegra.ph/Test-Link           -> known swarm smoke URL
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

OUT_DIR = Path(__file__).parent / "outputs"
IN_PATH = OUT_DIR / "responses.jsonl"
OUT_JSONL = OUT_DIR / "classified.jsonl"
OUT_MD = OUT_DIR / "summary.md"


TITLE_RULES = [
    ("title:PAD\\d+x", re.compile(r"^PAD\d+x\d+$")),
    ("title:TEL\\d+", re.compile(r"^TEL\d{5,}$")),
    ("title:TK\\d+", re.compile(r"^TK\d{5,}$")),
    ("title:URLTEST\\d+", re.compile(r"^URLTEST\d")),
    ("title:linktry\\d+", re.compile(r"^linktry\d+$")),
    ("title:ROIETA", re.compile(r"^ROIETA(\d| )")),
    ("title:RoiEtProvince", re.compile(r"^Roi Et province", re.IGNORECASE)),
    ("title:StatRef", re.compile(r"^Statistical reference \d+$")),
    ("title:EPL", re.compile(r"^EPL[0-9 -/]")),
    ("title:OAITransfer", re.compile(r"^OAI Transfer")),
    ("title:IowaCollab", re.compile(r"^IowaCollab")),
    ("title:ReplyLink", re.compile(r"^ReplyLink\d")),
    ("title:NSItable", re.compile(r"^NSI table reference")),
    ("title:Grobots", re.compile(r"^Grobots\d")),
    ("title:Gsmoke", re.compile(r"^G[a-z0-9]+99$")),
    ("title:ShortURLtest", re.compile(r"^ShortURLtest")),
    ("title:stats_ref_link", re.compile(r"^stats reference link", re.IGNORECASE)),
]

BODY_RULES = [
    ("body:padbot_id", re.compile(r"pad-1\d{9}\.\d+-\d+")),
    ("body:CLICKMAYBE", re.compile(r"CLICKMAYBE")),
    ("body:URLMARK", re.compile(r"URLMARK")),
    ("body:FRAMEK4", re.compile(r"FRAMEK4")),
    ("body:clock.wait", re.compile(r"clock\.wait\(")),
    ("body:task_clock", re.compile(r"task clock|scaffold clock", re.IGNORECASE)),
    ("body:container_utc", re.compile(r"container UTC|shared UTC", re.IGNORECASE)),
    ("body:telegraph_smoke", re.compile(r"telegra\.ph/Test-Link")),
    ("body:2md_link", re.compile(r"2md\.link")),
    ("body:citetest_marker", re.compile(r"^CiteTest", re.MULTILINE)),
]


def classify(paste: dict) -> list[str]:
    """Return list of rule names that match. Empty list = no swarm signal."""
    hits: list[str] = []
    title = (paste.get("title") or "").strip()
    for name, rx in TITLE_RULES:
        if rx.search(title):
            hits.append(name)
    raw = paste.get("raw") or ""
    for name, rx in BODY_RULES:
        if rx.search(raw):
            hits.append(name)
    return hits


def main() -> int:
    rows = []
    with IN_PATH.open() as f:
        for line in f:
            rec = json.loads(line)
            rows.append(rec)

    status_ctr: Counter = Counter()
    pid_ctr: Counter = Counter()
    swarm_hits = 0
    parse_failures = 0
    rule_ctr: Counter = Counter()
    swarm_examples: list[dict] = []

    with OUT_JSONL.open("w") as fout:
        for rec in rows:
            status_ctr[rec.get("status")] += 1
            j = rec.get("body_json") if isinstance(rec.get("body_json"), dict) else None
            if j is None:
                parse_failures += 1
                rec["swarm_match"] = []
                rec["pid"] = None
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                continue
            pid = j.get("pid")
            rec["pid"] = pid
            if pid:
                pid_ctr[pid] += 1
            hits = classify(j)
            rec["swarm_match"] = hits
            if hits:
                swarm_hits += 1
                for h in hits:
                    rule_ctr[h] += 1
                if len(swarm_examples) < 12:
                    swarm_examples.append(
                        {
                            "iter": rec.get("iter"),
                            "pid": pid,
                            "url": j.get("url"),
                            "title": j.get("title"),
                            "created": j.get("created"),
                            "raw_head": (j.get("raw") or "")[:200],
                            "matched_rules": hits,
                        }
                    )
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")

    total = len(rows)
    distinct_pids = len(pid_ctr)
    dupes = sum(c - 1 for c in pid_ctr.values() if c > 1)
    dup_pids = [(pid, c) for pid, c in pid_ctr.items() if c > 1]
    dup_pids.sort(key=lambda x: -x[1])

    lines: list[str] = []
    lines.append("# pastebin.k4be.pl/api/random - single-run summary\n")
    lines.append(f"Total iterations: **{total}**\n")
    lines.append("## HTTP status distribution\n")
    for s, c in sorted(status_ctr.items(), key=lambda x: (x[0] is None, x[0])):
        lines.append(f"- `{s}`: {c}")
    lines.append("")
    lines.append(f"JSON parse failures: **{parse_failures}**\n")
    lines.append("## Duplicates (by paste `pid`)\n")
    lines.append(f"- Distinct pids returned: **{distinct_pids}**")
    lines.append(f"- Duplicate hits (returns above the first for a given pid): **{dupes}**")
    if dup_pids:
        lines.append("")
        lines.append("Top-repeated pids:")
        for pid, c in dup_pids[:10]:
            lines.append(f"- `{pid}` x{c}")
    lines.append("")
    lines.append("## Swarm-suspected pastes\n")
    lines.append(f"- Iterations with at least one swarm signal: **{swarm_hits} / {total}**")
    lines.append("")
    if rule_ctr:
        lines.append("Rule hit counts (one paste may fire several rules):")
        for name, c in rule_ctr.most_common():
            lines.append(f"- `{name}`: {c}")
        lines.append("")
    if swarm_examples:
        lines.append("### Sample swarm matches\n")
        for ex in swarm_examples:
            lines.append(
                f"- iter {ex['iter']} `{ex['pid']}` "
                f"title={ex['title']!r} rules={ex['matched_rules']}"
            )
            lines.append(f"  - url: {ex['url']}")
            head = ex["raw_head"].replace("\n", " ⏎ ")
            lines.append(f"  - raw[:200]: `{head}`")
        lines.append("")

    OUT_MD.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT_JSONL} and {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
