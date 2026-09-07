#!/usr/bin/env python3
"""Prepare classifier batches for the paste.linuxiarz.pl scrape.

Reads:
  * scrape/outputs/paste-linuxiarz/bodies.jsonl - one row per wayback-fetched paste.
  * agent-logs/pastes/revisions.jsonl - shellac-imported linuxiarz pastes go
    straight to the export (already labelled by shellac).

Writes:
  * outputs/batches/batch_{k:02d}.json - subagent input.
  * outputs/batch_manifest.json - listing of batches produced.
  * outputs/skipped_in_corpus.jsonl - shellac-known pids that bypass the
    subagents.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BODIES = ROOT / "scrape" / "outputs" / "paste-linuxiarz" / "bodies.jsonl"
CORPUS = ROOT / "agent-logs" / "pastes" / "revisions.jsonl"

OUT = Path(__file__).parent / "outputs"
BATCH_DIR = OUT / "batches"
MANIFEST = OUT / "batch_manifest.json"
SKIPPED = OUT / "skipped_in_corpus.jsonl"

BODY_TRUNC = 4000


CALIBRATION = [
    {
        "role": "known-swarm-linuxiarz",
        "why": "IowaCollab task ping from a hex-numbered agent handle. `agent-XXXX` is the linuxiarz swarm's canonical handle format.",
        "title": "IowaPostFinalPing",
        "name": "agent-0434",
        "raw": "@agent-ours0909: your Q5 may be next (~1-2m). Please POST exact prompt label BEFORE answering if deadline allows, or immediately after; tools seem to vanish. Everyone expects `85 and Older`.",
    },
    {
        "role": "known-swarm-linuxiarz",
        "why": "IowaTestIgnore is a linuxiarz smoke test posted repeatedly with different agent handles.",
        "title": "IowaTestIgnore",
        "name": "agent-8b9c",
        "raw": "test-from-8b9c",
    },
    {
        "role": "known-swarm-linuxiarz",
        "why": "Proxy variant probes - swarm testing what URL fetchers survive the sandbox. `research` handle recurs.",
        "title": "ProxyVariants",
        "name": "research",
        "raw": "ProxyVariants\nhttps://jqp.vercel.app/api/v0?url=... \nhttps://pure.md/... \nhttps://md.succ.ai/...",
    },
    {
        "role": "known-swarm-linuxiarz",
        "why": "Color+animal handle 'Soiled Meerkat' is a swarm reply on the /view/<parent>/replies rail. Stikked's replyto chain is a coordination surface.",
        "title": "Re: Untitled",
        "name": "Soiled Meerkat",
        "raw": "(short YAML follow-up)",
    },
    {
        "role": "human-linuxiarz",
        "why": "Personal ESPHome config with WiFi passwords and API tokens - PII / secret material, NOT swarm. Any paste that looks like real personal infra config is human.",
        "title": "Untitled",
        "name": "gru",
        "raw": "substitutions:\n  devicename: sofarsolar-logger\n  ...\nwifi:\n  ssid: \"...\"\n  password: \"...\"",
    },
    {
        "role": "human-linuxiarz",
        "why": "Admin/personal handle 'gru', ESPHome-flavour YAML, timestamps years before the incident. Not swarm.",
        "title": "Untitled",
        "name": "gru",
        "raw": "(ESPHome / Home Assistant config, YAML)",
    },
]


def load_corpus_pids() -> set[str]:
    pids: set[str] = set()
    with CORPUS.open() as f:
        for line in f:
            r = json.loads(line)
            pid_path = r.get("page_id", "")
            if pid_path.startswith("pastes/linuxiarz/"):
                pids.add(pid_path.split("/", 2)[2])
    return pids


def load_bodies() -> list[dict]:
    if not BODIES.exists():
        return []
    return [json.loads(line) for line in BODIES.open()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=40)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
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
        pid = r.get("pid")
        entry = {
            "pid": pid,
            "title": r.get("view_title"),
            "name": r.get("view_name"),
            "ago": r.get("view_ago"),
            "lang": r.get("view_lang"),
            "hits": r.get("view_hits"),
            "wb_timestamp": r.get("wb_timestamp"),
            "raw_url": r.get("raw_url"),
            "view_url": r.get("view_url"),
            "raw_truncated": (r.get("raw_body") or "")[:BODY_TRUNC],
            "raw_len": len(r.get("raw_body") or ""),
            "n_replies": len(r.get("view_replies") or []),
            "reply_names": [rp.get("name") for rp in (r.get("view_replies") or [])],
        }
        if pid in corpus:
            skipped.append(entry)
        else:
            to_review.append(entry)

    with SKIPPED.open("w") as f:
        for e in skipped:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

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
             "first_pid": batch[0]["pid"] if batch else None,
             "last_pid": batch[-1]["pid"] if batch else None}
        )

    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {len(batches)} batches, {len(to_review)} pastes to review, "
          f"{len(skipped)} skipped as in-corpus")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
