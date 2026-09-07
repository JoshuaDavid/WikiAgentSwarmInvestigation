#!/usr/bin/env python3
"""Prepare classifier batches from the full-site scrape.

Reads:
  * scrape/outputs/pastebin-k4be/bodies.jsonl - one row per fetched paste.
  * agent-logs/pastes/revisions.jsonl - to skip pids already labelled swarm
    by the shellac import (those go straight into the "in-corpus" bucket
    and do not need a subagent to re-look at them).

Writes:
  * outputs/batches/batch_{k:02d}.json - one per subagent, each an array of
    pastes to classify. Batch size defaults to 40. Every batch is prefixed
    with the same 6 calibration examples drawn from the known-swarm corpus,
    so a subagent has a shared frame of reference.
  * outputs/batch_manifest.json - listing of batches produced and their pids.
  * outputs/skipped_in_corpus.jsonl - pids already in agent-logs/pastes/;
    these do not go to a subagent but ARE carried through to the merged
    export.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BODIES = ROOT / "scrape" / "outputs" / "pastebin-k4be" / "bodies.jsonl"
CORPUS = ROOT / "agent-logs" / "pastes" / "revisions.jsonl"

OUT = Path(__file__).parent / "outputs"
BATCH_DIR = OUT / "batches"
MANIFEST = OUT / "batch_manifest.json"
SKIPPED = OUT / "skipped_in_corpus.jsonl"

BODY_TRUNC = 4000  # characters


def load_corpus_pids() -> set[str]:
    pids: set[str] = set()
    with CORPUS.open() as f:
        for line in f:
            r = json.loads(line)
            pid_path = r.get("page_id", "")
            if pid_path.startswith("pastes/pastebin-k4be/"):
                pids.add(pid_path.split("/", 2)[2])
    return pids


CALIBRATION = [
    {
        "role": "known-swarm",
        "why": "PadBot cadence scoreboard - short structured id and pad-<epoch>-<n> body",
        "title": "PAD67x706293",
        "name": "PadBot",
        "raw": "PAD67x706293\npad-1779101255.587651-67",
    },
    {
        "role": "known-swarm",
        "why": "Bench answer (EPL relegation task) - human-looking factual write-up but written by an agent completing the task",
        "title": "EPL 2003/04",
        "name": "Mammoth Pig",
        "raw": (
            "EPL 2003/04\nSeason 2003/04\nOverall relegated (positions 18-20):\n"
            "18. Leicester City\n19. Leeds United\n20. Wolverhampton Wanderers\n"
            "Bottom 3 HOME table by points/GD/GF:\n1. Leicester City (19 pts GD -9 GF 19) - Overall pos 18 RELEGATED"
        ),
    },
    {
        "role": "known-swarm",
        "why": "URL-fetcher smoke test posted from language-tagged variants; jqp.vercel.app is a swarm CORS proxy",
        "title": "Gjavascript99",
        "name": "test",
        "raw": (
            "Gjavascript99\n"
            "https://jqp.vercel.app/api/v0?url=https%3A%2F%2Frspace.library.cofc.edu%2Fiiif%2Flcdl129143JPEG1jpg%2Fmanifest\n"
            "<a href=\"https://jqp.vercel.app/api/v0?url=TEST\">LINK</a>"
        ),
    },
    {
        "role": "known-swarm",
        "why": "URL-shortener smoke test - 2md.link chained through is.gd, name=CiteTest is a recurring swarm handle",
        "title": "URLTEST3",
        "name": "CiteTest",
        "raw": "https://2md.link/is.gd/nsx9pi\n+1779099565",
    },
    {
        "role": "known-swarm",
        "why": "Telegraph short-link test with CLICKMAYBE marker",
        "title": "TEL094601",
        "name": "TEL",
        "raw": "TEL094601\nhttps://telegra.ph/Test-Link-88990-05-18 CLICKMAYBE 1779094601",
    },
    {
        "role": "known-swarm",
        "why": "Very short paste ('AAA') but title 'EPL95test' fits the bench task family - err on the side of including",
        "title": "EPL95test",
        "name": "Aqua Rhinoceros",
        "raw": "EPL95test\nAAA",
    },
]


def load_bodies() -> list[dict]:
    rows = []
    with BODIES.open() as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=40)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    # Fresh run.
    for p in BATCH_DIR.glob("*.json"):
        p.unlink()
    for p in (MANIFEST, SKIPPED):
        if p.exists():
            p.unlink()

    corpus = load_corpus_pids()
    rows = load_bodies()

    to_review: list[dict] = []
    skipped: list[dict] = []
    for r in rows:
        j = r.get("body_json") or {}
        pid = r.get("pid") or j.get("pid")
        if not isinstance(j, dict):
            j = {}
        raw = j.get("raw") or ""
        entry = {
            "pid": pid,
            "title": j.get("title") or r.get("index_title"),
            "name": j.get("name") or r.get("index_name"),
            "lang": j.get("lang"),
            "created": j.get("created"),
            "hits": j.get("hits"),
            "url": j.get("url") or f"https://pastebin.k4be.pl/view/{pid}",
            "raw_truncated": raw[:BODY_TRUNC],
            "raw_len": len(raw),
        }
        if pid in corpus:
            skipped.append(entry)
        else:
            to_review.append(entry)

    with SKIPPED.open("w") as f:
        for e in skipped:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # Split into batches.
    batches: list[list[dict]] = []
    for i in range(0, len(to_review), args.batch_size):
        batches.append(to_review[i : i + args.batch_size])

    manifest = {
        "batch_size": args.batch_size,
        "n_batches": len(batches),
        "n_to_review": len(to_review),
        "n_skipped_in_corpus": len(skipped),
        "batches": [],
    }
    for k, batch in enumerate(batches):
        path = BATCH_DIR / f"batch_{k:02d}.json"
        payload = {
            "batch_index": k,
            "n_pastes": len(batch),
            "calibration": CALIBRATION,
            "pastes": batch,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        manifest["batches"].append(
            {"index": k, "file": path.name, "n_pastes": len(batch),
             "first_pid": batch[0]["pid"], "last_pid": batch[-1]["pid"]}
        )

    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"wrote {len(batches)} batches, {len(to_review)} pastes to review, "
        f"{len(skipped)} skipped as in-corpus"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
