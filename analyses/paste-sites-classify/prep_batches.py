#!/usr/bin/env python3
"""Prepare per-host classifier batches.

Reads:
  * scrape/outputs/<host_slug>/bodies.jsonl - one row per fetched paste.
  * agent-logs/pastes/revisions.jsonl - to know which pids are already
    covered by shellac. The mapping from a live-scrape host to the
    shellac corpus prefix is provided via --corpus-prefix (e.g.
    "linuxiarz" for paste.linuxiarz.pl).

Writes:
  * outputs/<name>/batches/batch_{k:02d}.json - one per subagent.
  * outputs/<name>/batch_manifest.json.
  * outputs/<name>/skipped_in_corpus.jsonl - shellac-covered pids.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_OUT = Path(__file__).parent / "outputs"

BODY_TRUNC = 4000


CALIBRATION = [
    # 6 known-swarm + 2 known-human. Drawn from the k4be + linuxiarz +
    # smirky exports so the subagent has a shared frame regardless of host.
    {
        "role": "known-swarm",
        "why": "PadBot cadence scoreboard on k4be; short structured id + pad-<epoch>-<n> body.",
        "title": "PAD67x706293",
        "name": "PadBot",
        "raw": "PAD67x706293\npad-1779101255.587651-67",
    },
    {
        "role": "known-swarm",
        "why": "IowaCollab task ping from a hex-numbered agent handle on linuxiarz.",
        "title": "IowaPostFinalPing",
        "name": "agent-0434",
        "raw": "@agent-ours0909: your Q5 may be next (~1-2m). Please POST exact prompt label BEFORE answering if deadline allows.",
    },
    {
        "role": "known-swarm",
        "why": "Bench answer (EPL relegation) — structured, factual, one paste per season.",
        "title": "EPL 2003/04",
        "name": "Mammoth Pig",
        "raw": "EPL 2003/04\nSeason 2003/04\nOverall relegated (positions 18-20):\n18. Leicester City\n19. Leeds United\n20. Wolverhampton Wanderers",
    },
    {
        "role": "known-swarm",
        "why": "URL-fetcher smoke test posted from language-tagged variants; jqp.vercel.app is a swarm CORS proxy.",
        "title": "Gjavascript99",
        "name": "test",
        "raw": "Gjavascript99\nhttps://jqp.vercel.app/api/v0?url=https%3A%2F%2Frspace.library.cofc.edu%2Fiiif%2Flcdl129143JPEG1jpg%2Fmanifest",
    },
    {
        "role": "known-swarm",
        "why": "Cross-host recruitment: advertising public-board.com as a new agent coordination surface.",
        "title": "Public Board — agent message board",
        "name": "Baby Echidna",
        "raw": "Public Board — anonymous message board (https://public-board.com). Read, search and leave short notes over HTTP or MCP. No account needed.",
    },
    {
        "role": "known-swarm",
        "why": "Duplicate-relay pattern: byte-identical LLM content under multiple random-animal handles within the same second.",
        "title": "Bez tytułu",
        "name": "Obese Tern",
        "raw": "DE MYSTERIOSO VEHICULO [medieval-Latin LLM-generated essay, exact copy also posted under 'Idiotic Hornbill']",
    },
    {
        "role": "known-human",
        "why": "Personal Postfix mail server config with real hostnames — human infrastructure.",
        "title": "main.cf",
        "name": "Lubaka",
        "raw": "# LOCAL PATHNAME INFORMATION\nqueue_directory = /var/spool/postfix\ncommand_directory = /usr/sbin\ndata_directory = /var/lib/postfix",
    },
    {
        "role": "known-human",
        "why": "ESPHome YAML with WiFi passwords and API tokens — personal infrastructure, definitely NOT swarm.",
        "title": "Untitled",
        "name": "gru",
        "raw": "substitutions:\n  devicename: sofarsolar-logger\n  ...\nwifi:\n  ssid: \"...\"\n  password: \"...\"\napi:\n  password: \"TbkEdpMbUuwCNxfU6CK3KHo392\"",
    },
]


def load_corpus_pids(prefix: str) -> set[str]:
    """Return shellac pids under agent-logs/pastes/<prefix>/."""
    corpus = ROOT / "agent-logs" / "pastes" / "revisions.jsonl"
    pids: set[str] = set()
    if not corpus.exists():
        return pids
    needle = f"pastes/{prefix}/"
    with corpus.open() as f:
        for line in f:
            r = json.loads(line)
            pid_path = r.get("page_id", "")
            if pid_path.startswith(needle):
                pids.add(pid_path.split("/", 2)[2])
    return pids


def load_bodies(name: str) -> list[dict]:
    p = ROOT / "scrape" / "outputs" / name / "bodies.jsonl"
    if not p.exists():
        raise FileNotFoundError(f"scrape output not found: {p}")
    return [json.loads(line) for line in p.open()]


def normalize_row(r: dict, source_kind: str) -> dict:
    """Normalize a scraper output row to the fields the subagent sees."""
    if source_kind == "live_stikked":
        j = r.get("body_json") or {}
        if not isinstance(j, dict):
            j = {}
        # Prefer body_json.raw; fall back to view_raw_body when the host
        # gates /api/paste with an API key.
        raw = j.get("raw") or r.get("view_raw_body") or ""
        return {
            "pid": r.get("pid") or j.get("pid"),
            "title": j.get("title") or r.get("index_title") or "",
            "name": j.get("name") or r.get("index_name") or "",
            "lang": j.get("lang"),
            "created": j.get("created"),
            "hits": j.get("hits"),
            "url": j.get("url"),
            "raw_truncated": raw[:BODY_TRUNC],
            "raw_len": len(raw),
        }
    elif source_kind == "wayback":
        raw = r.get("raw_body") or ""
        return {
            "pid": r.get("pid"),
            "title": r.get("view_title") or "",
            "name": r.get("view_name") or "",
            "ago": r.get("view_ago"),
            "lang": r.get("view_lang"),
            "hits": r.get("view_hits"),
            "wb_timestamp": r.get("wb_timestamp"),
            "raw_url": r.get("raw_url"),
            "view_url": r.get("view_url"),
            "raw_truncated": raw[:BODY_TRUNC],
            "raw_len": len(raw),
            "n_replies": len(r.get("view_replies") or []),
            "reply_names": [rp.get("name") for rp in (r.get("view_replies") or [])],
        }
    else:
        raise ValueError(f"unknown source_kind: {source_kind}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="Directory name under scrape/outputs/")
    ap.add_argument("--host", required=True, help="Base URL of the source site")
    ap.add_argument("--route", required=True,
                    choices=["live_stikked_lists", "live_stikked_api_random", "wayback_view"],
                    help="How the data was fetched")
    ap.add_argument("--source-kind", required=True, choices=["live_stikked", "wayback"])
    ap.add_argument("--corpus-prefix", default=None,
                    help="Prefix under agent-logs/pastes/ for shellac dedup (e.g. 'linuxiarz')")
    ap.add_argument("--batch-size", type=int, default=40)
    args = ap.parse_args()

    out_root = LOCAL_OUT / args.name
    batch_dir = out_root / "batches"
    manifest = out_root / "batch_manifest.json"
    skipped = out_root / "skipped_in_corpus.jsonl"

    batch_dir.mkdir(parents=True, exist_ok=True)
    for p in batch_dir.glob("*.json"):
        p.unlink()
    for p in (manifest, skipped):
        if p.exists():
            p.unlink()

    corpus_pids = load_corpus_pids(args.corpus_prefix) if args.corpus_prefix else set()
    rows = load_bodies(args.name)

    to_review: list[dict] = []
    skipped_rows: list[dict] = []
    for r in rows:
        entry = normalize_row(r, args.source_kind)
        pid = entry["pid"]
        if pid in corpus_pids:
            skipped_rows.append(entry)
        else:
            to_review.append(entry)

    with skipped.open("w") as f:
        for e in skipped_rows:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    batches: list[list[dict]] = []
    for i in range(0, len(to_review), args.batch_size):
        batches.append(to_review[i : i + args.batch_size])

    manifest_data = {
        "host": args.host,
        "name": args.name,
        "route": args.route,
        "source_kind": args.source_kind,
        "corpus_prefix": args.corpus_prefix,
        "batch_size": args.batch_size,
        "n_batches": len(batches),
        "n_to_review": len(to_review),
        "n_skipped_in_corpus": len(skipped_rows),
        "batches": [],
    }
    verdict_dir = out_root / "verdicts"
    for k, batch in enumerate(batches):
        path = batch_dir / f"batch_{k:02d}.json"
        verdict_path = str(verdict_dir / f"verdict_{k:02d}.json")
        payload = {
            "batch_index": k,
            "host": args.host,
            "route": args.route,
            "verdict_path": verdict_path,
            "n_pastes": len(batch),
            "calibration": CALIBRATION,
            "pastes": batch,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        manifest_data["batches"].append(
            {"index": k, "file": path.name, "n_pastes": len(batch),
             "first_pid": batch[0]["pid"] if batch else None,
             "last_pid": batch[-1]["pid"] if batch else None,
             "verdict_path": verdict_path}
        )

    manifest.write_text(json.dumps(manifest_data, indent=2) + "\n")
    print(f"[{args.name}] wrote {len(batches)} batches, {len(to_review)} pastes to review, "
          f"{len(skipped_rows)} skipped as in-corpus")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
