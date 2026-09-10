#!/usr/bin/env python3
"""Dump the 'unknown' paste bodies into review batches for subagent triage.

Each batch is a JSON file with { batch_id, notes, pastes: [ {..full body..} ] }
so a subagent can read one file and emit labels for every entry in it.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
AGENT_LOGS = REPO_ROOT / "agent-logs"
CLASSIFIED = HERE / "outputs" / "pastes_by_task.tsv"
BATCH_DIR = HERE / "outputs" / "review_batches"
BATCH_DIR.mkdir(parents=True, exist_ok=True)

PASTE_SOURCES = [
    "pastes", "pastebin-k4be", "anna.fyi", "pastebin.tarcseh.me",
    "paste-linuxiarz", "pastebin.faster-it.de", "pb.dynavirt.com",
    "paste.steamr.com", "paste.smirky.net", "pastie.iem.at",
    "paste.centos.org", "paste.lightcast.com", "pastebin.freepbx.org",
    "p.gaa.st", "pb.psychotic.ninja",
]

N_BATCHES = 4


def main() -> None:
    unknown_shas: list[tuple[str, str, str]] = []
    with CLASSIFIED.open() as f:
        header = f.readline().rstrip("\n").split("\t")
        i_task = header.index("task")
        i_sha = header.index("body_sha256")
        i_src = header.index("source")
        i_time = header.index("time")
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if parts[i_task] == "unknown":
                unknown_shas.append((parts[i_sha], parts[i_src], parts[i_time]))

    print(f"unknown pastes: {len(unknown_shas)}", file=sys.stderr)

    # Load bodies from source revisions.jsonl
    body_by_sha: dict[str, dict] = {}
    for src in PASTE_SOURCES:
        p = AGENT_LOGS / src / "revisions.jsonl"
        if not p.exists():
            continue
        with p.open() as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                sha = r.get("body_sha256")
                if sha and sha not in body_by_sha:
                    r["_src"] = src
                    body_by_sha[sha] = r

    entries = []
    for sha, src, t in unknown_shas:
        r = body_by_sha.get(sha) or {}
        entries.append({
            "body_sha256": sha,
            "source": r.get("_src", src),
            "time": t or r.get("time", ""),
            "label": r.get("label", ""),
            "title": r.get("source_title", "") or r.get("shellac_title", ""),
            "source_url": r.get("source_url", ""),
            "verdict": r.get("verdict"),
            "verdict_rationale": r.get("verdict_rationale"),
            "body": r.get("body", ""),
        })

    entries.sort(key=lambda e: (e["source"] or "", e["time"] or "", e["body_sha256"] or ""))

    per_batch = -(-len(entries) // N_BATCHES)  # ceil div
    for bi in range(N_BATCHES):
        chunk = entries[bi * per_batch:(bi + 1) * per_batch]
        if not chunk:
            continue
        out = BATCH_DIR / f"batch_{bi+1:02d}.json"
        with out.open("w") as f:
            json.dump({
                "batch_id": bi + 1,
                "n_pastes": len(chunk),
                "notes": "Each entry is one paste. Assign a task label. See prompt.",
                "pastes": chunk,
            }, f, ensure_ascii=False, indent=1)
        print(f"wrote {out} ({len(chunk)} pastes)", file=sys.stderr)


if __name__ == "__main__":
    main()
