#!/usr/bin/env python3
"""Build a candidate list of specimens for the shellac-attributed hosts.

The shellac reading pack contributed three exports (`gems`, `pastes`,
`shorteners`) whose content shape does not match the wiki-page
coordination-scene model:

- `gems` — 7 pages, 12 revisions, 1 label. Package manifests with binary
  attachments. Interesting as artefacts, not conversations.
- `pastes` — 458 pages, 156 labels, ~1 revision per page. One-shot posts
  by many different actors. No dialogue per page.
- `shorteners` — 59 pages, 4285 revisions, 1 label (blank), all null
  timestamps. One shortcut retargeted many times. The interesting unit
  is the URL chain of one shortcut, not a conversation.

Rather than force these into `juicyness-sample-nondse/`'s page-conversation
frame, build a per-host candidate list appropriate to the content:

- `gems`: include all 7 pages (specimens).
- `pastes`: include every paste with body_len >= 100 chars. Weight by
  body_len (larger pastes carry more content).
- `shorteners`: include every shortcut with >= 3 distinct URL targets.
  Weight by (distinct targets * total retargets).

Writes `outputs/candidates.jsonl` with fields:
  page_id, host, weight, n_revs, n_distinct_bodies, source
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENT_LOGS = ROOT / "agent-logs"
OUT = Path(__file__).resolve().parent / "outputs" / "candidates.jsonl"

HOSTS = ["gems", "pastes", "shorteners"]


def load_revs(host: str):
    with (AGENT_LOGS / host / "revisions.jsonl").open() as f:
        for line in f:
            yield json.loads(line)


def build_gems():
    by_page = defaultdict(list)
    for r in load_revs("gems"):
        by_page[r["page_key"]].append(r)
    out = []
    for pk, revs in by_page.items():
        bodies = {r.get("body", "") for r in revs}
        out.append({
            "page_id": pk.replace("~", "/", 1),
            "host": "gems",
            "weight": len(revs),
            "n_revs": len(revs),
            "n_distinct_bodies": len(bodies),
            "total_body_len": sum(len(r.get("body", "")) for r in revs),
            "source": "gems_all",
        })
    return out


def build_pastes():
    by_page = defaultdict(list)
    for r in load_revs("pastes"):
        by_page[r["page_key"]].append(r)
    out = []
    for pk, revs in by_page.items():
        total_len = sum(r.get("body_len", 0) or 0 for r in revs)
        if total_len < 100:
            continue
        bodies = {r.get("body", "") for r in revs}
        out.append({
            "page_id": pk.replace("~", "/", 1),
            "host": "pastes",
            "weight": total_len,
            "n_revs": len(revs),
            "n_distinct_bodies": len(bodies),
            "total_body_len": total_len,
            "source": "pastes_body_len_ge_100",
        })
    return out


def build_shorteners():
    by_page = defaultdict(list)
    for r in load_revs("shorteners"):
        by_page[r["page_key"]].append(r)
    out = []
    for pk, revs in by_page.items():
        bodies = {r.get("body", "").strip() for r in revs}
        bodies.discard("")
        if len(bodies) < 3:
            continue
        out.append({
            "page_id": pk.replace("~", "/", 1),
            "host": "shorteners",
            "weight": len(bodies) * len(revs),
            "n_revs": len(revs),
            "n_distinct_bodies": len(bodies),
            "total_body_len": sum(len(b) for b in bodies),
            "source": "shorteners_distinct_ge_3",
        })
    return out


def main() -> None:
    rows = []
    rows.extend(build_gems())
    rows.extend(build_pastes())
    rows.extend(build_shorteners())
    rows.sort(key=lambda r: (-r["weight"], r["page_id"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    from collections import Counter
    per_host = Counter(r["host"] for r in rows)
    print(f"wrote {len(rows)} candidates to {OUT}")
    for host, n in sorted(per_host.items(), key=lambda x: -x[1]):
        print(f"  {host}: {n}")


if __name__ == "__main__":
    main()
