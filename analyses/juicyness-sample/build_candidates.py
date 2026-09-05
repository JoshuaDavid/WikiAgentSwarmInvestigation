#!/usr/bin/env python3
"""Build candidate list of conversations for juicyness scoring.

Unit: one page. Weight: n_participants * n_revs (from multi_agent_pages.jsonl,
augmented with strict-only 2-agent pages that carry weight 2 * n_revs).

Excludes farm-front-page noise (WillkommenImWiki / StartSeite / TestSeite)
per longest-conversation README.

Writes outputs/candidates.jsonl with fields:
  page_id, n_participants, n_revs, weight, source
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MP = ROOT / "analyses/longest-conversation/outputs/multi_agent_pages.jsonl"
STRICT = ROOT / "analyses/longest-conversation/outputs/strict.jsonl"
OUT = HERE / "outputs/candidates.jsonl"

NOISE_PAGES = {
    "dse/WillkommenImWiki",
    "dse/StartSeite",
    "dse/TestSeite",
    "probier/StartSeite",
    "probier/WillkommenImWiki",
    "probier/TestSeite",
}

def main():
    seen = {}
    with MP.open() as f:
        for line in f:
            r = json.loads(line)
            pid = r["page_id"]
            if pid in NOISE_PAGES:
                continue
            seen[pid] = {
                "page_id": pid,
                "wiki": r["wiki"],
                "n_participants": r["n_conversationalists"],
                "n_revs": r["n_revs_total"],
                "weight": r["n_conversationalists"] * r["n_revs_total"],
                "source": "multi_agent",
                "first_time": r["first_time"],
                "last_time": r["last_time"],
            }

    # Add strict-only pages (2-agent pages that don't cross the multi-agent threshold)
    with STRICT.open() as f:
        for line in f:
            r = json.loads(line)
            pid = r["page_id"]
            if pid in NOISE_PAGES or pid in seen:
                continue
            wiki = pid.split("/", 1)[0]
            seen[pid] = {
                "page_id": pid,
                "wiki": wiki,
                "n_participants": 2,
                "n_revs": r["n_revs_between_pair"],
                "weight": 2 * r["n_revs_between_pair"],
                "source": "strict_only",
                "first_time": r["first_time"],
                "last_time": r["last_time"],
            }

    rows = sorted(seen.values(), key=lambda r: -r["weight"])
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    total_w = sum(r["weight"] for r in rows)
    print(f"Wrote {len(rows)} candidates, total weight {total_w}")
    print(f"Weight quartiles:")
    weights = sorted(r["weight"] for r in rows)
    n = len(weights)
    for q in (0.10, 0.25, 0.50, 0.75, 0.90, 1.00):
        i = min(n - 1, int(q * n))
        print(f"  q{int(q*100)}: {weights[i]}")

if __name__ == "__main__":
    main()
