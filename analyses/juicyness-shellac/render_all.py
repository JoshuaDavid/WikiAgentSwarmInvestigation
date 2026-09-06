#!/usr/bin/env python3
"""Render shellac-attributed specimens for scoring.

Different renderer per host because the shapes are different:

- gems: one revision per file, labelled by version. Render all revs
  in file order (there is no other order — timestamps are null).
- pastes: usually one revision per page. Render each revision with
  label and body.
- shorteners: many revisions per page, all timestamps null. Render as
  an ordered list of distinct target URLs (dedupe body, keep first-
  occurrence order). Cap displayed distinct URLs at 100.

Writes markdown to /collusionwiki/tmp/juicyness-shellac/transcripts/.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENT_LOGS = ROOT / "agent-logs"
SAMPLE = Path(__file__).resolve().parent / "outputs" / "sample.jsonl"
OUT_DIR = Path("/collusionwiki/tmp/juicyness-shellac/transcripts")


def slug(page_id: str) -> str:
    host, name = page_id.split("/", 1)
    return f"{host}-{name.replace('/', '-')}"


def load_revs(host: str, page_id: str):
    revs = []
    with (AGENT_LOGS / host / "revisions.jsonl").open() as f:
        for line in f:
            r = json.loads(line)
            if r["page_id"] == page_id:
                revs.append(r)
    return revs


def render_gems(page_id, revs, out):
    out.write(f"# gems specimen: {page_id}\n\n")
    out.write(f"Total revisions: {len(revs)}\n\n")
    for i, r in enumerate(revs, 1):
        out.write(f"## rev {i} — version {r.get('name','?')} — label `{r.get('label','') or '<blank>'}`\n\n")
        body = r.get("body", "")
        out.write("> " + body.replace("\n", "\n> ") + "\n\n")


def render_paste(page_id, revs, out):
    out.write(f"# paste specimen: {page_id}\n\n")
    labels = sorted({r.get("label", "") or "<blank>" for r in revs})
    out.write(f"Labels: {', '.join(f'`{l}`' for l in labels)}\n")
    out.write(f"Revisions: {len(revs)}\n\n")
    for i, r in enumerate(revs, 1):
        out.write(f"## rev {i} — label `{r.get('label','') or '<blank>'}` — {r.get('time') or '(no timestamp)'}\n\n")
        body = r.get("body", "") or ""
        out.write("> " + body.replace("\n", "\n> ") + "\n\n")


def render_shortener(page_id, revs, out):
    out.write(f"# shortener specimen: {page_id}\n\n")
    out.write(f"Total revisions: {len(revs)} (all timestamps null in export)\n")
    labels = sorted({r.get("label", "") or "<blank>" for r in revs})
    out.write(f"Labels: {', '.join(f'`{l}`' for l in labels)}\n\n")
    seen = []
    seen_set = set()
    for r in revs:
        b = (r.get("body", "") or "").strip()
        if not b or b in seen_set:
            continue
        seen_set.add(b)
        seen.append(b)
    out.write(f"## Distinct target URLs, first-occurrence order ({len(seen)} distinct)\n\n")
    for i, b in enumerate(seen[:100], 1):
        out.write(f"{i}. `{b[:400]}`\n")
    if len(seen) > 100:
        out.write(f"\n... plus {len(seen) - 100} more distinct URLs (not shown).\n")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_ok = 0
    with SAMPLE.open() as f:
        for line in f:
            r = json.loads(line)
            page_id = r["page_id"]
            host = r["host"]
            revs = load_revs(host, page_id)
            out_path = OUT_DIR / f"{slug(page_id)}.md"
            with out_path.open("w") as out:
                if host == "gems":
                    render_gems(page_id, revs, out)
                elif host == "pastes":
                    render_paste(page_id, revs, out)
                elif host == "shorteners":
                    render_shortener(page_id, revs, out)
            n_ok += 1
    print(f"rendered {n_ok} to {OUT_DIR}")


if __name__ == "__main__":
    main()
