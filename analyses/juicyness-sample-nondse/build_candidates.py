#!/usr/bin/env python3
"""Build a candidate list of coordination scenes for the non-dse wiki exports.

The main `juicyness-sample/` analysis targets `dse/` and reads from
`analyses/longest-conversation/outputs/multi_agent_pages.jsonl` (dse-only).

The non-dse wiki exports have essentially no username-based dialogue —
`agent-graph/outputs/messages.jsonl` records only 47 non-dse messages in
total, vs. 15,857 for dse. So the strict "who mentioned whom" filter used
for dse produces almost nothing here.

Instead, treat any page in a non-dse wiki export with at least 2 distinct
writer labels AND at least 3 revisions as a candidate coordination scene.
Exclude the obvious noise pages: `RecentChanges`, `SandBox`, `TestPage`,
farm-front pages, and anything named `Test*` / `Sandbox*` / `Foo*` /
`Tmp*` / `Bar*`.

Writes `outputs/candidates.jsonl` with fields:
  page_id, wiki, n_labels, n_revs, weight (= n_labels * n_revs), source
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENT_LOGS = ROOT / "agent-logs"
OUT = Path(__file__).resolve().parent / "outputs" / "candidates.jsonl"

WIKIS = ["apchem", "fractal", "ludism", "milkwiki", "probier",
         "texteditors", "wiki4d"]

NOISE_NAME_PREFIXES = ("Test", "Sandbox", "SandBox", "Foo", "Tmp",
                       "Bar", "Sand", "MyTemp", "MYPAGE")
NOISE_NAMES = {"RecentChanges", "StartSeite", "WillkommenImWiki",
               "TestSeite", "SandBox", "Sandbox", "TestPage",
               "Edit", "EditorIndex", "DocComments"}


def is_noise(page_key: str) -> bool:
    name = page_key.split("~", 1)[1] if "~" in page_key else page_key
    tail = name.rsplit("/", 1)[-1]
    if tail in NOISE_NAMES:
        return True
    for pref in NOISE_NAME_PREFIXES:
        if tail.startswith(pref):
            return True
    return False


POST_CUT = "2026-05-01"


def main() -> None:
    rows = []
    for wiki in WIKIS:
        by_page = defaultdict(lambda: {"labels": set(), "revs": 0,
                                       "first": None, "last": None})
        rev_path = AGENT_LOGS / wiki / "revisions.jsonl"
        if not rev_path.exists():
            print(f"missing: {rev_path}")
            continue
        with rev_path.open() as f:
            for line in f:
                r = json.loads(line)
                t = r.get("time")
                # Only count post-cut revisions for candidate scoring: some
                # wikis (ludism) include full pre-cut history of visible pages,
                # which pollutes the label/rev counts with human editors from
                # 2020.
                if t is None or t < POST_CUT:
                    continue
                d = by_page[r["page_key"]]
                d["labels"].add(r.get("label", "") or "<blank>")
                d["revs"] += 1
                if d["first"] is None or t < d["first"]:
                    d["first"] = t
                if d["last"] is None or t > d["last"]:
                    d["last"] = t
        for page_key, d in by_page.items():
            if is_noise(page_key):
                continue
            if len(d["labels"]) < 2 or d["revs"] < 3:
                continue
            page_id = page_key.replace("~", "/", 1)
            rows.append({
                "page_id": page_id,
                "wiki": wiki,
                "n_labels": len(d["labels"]),
                "n_revs": d["revs"],
                "weight": len(d["labels"]) * d["revs"],
                "source": "nondse_multi_label",
                "first_time": d["first"],
                "last_time": d["last"],
            })

    rows.sort(key=lambda r: (-r["weight"], r["page_id"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    from collections import Counter
    per_wiki = Counter(r["wiki"] for r in rows)
    print(f"wrote {len(rows)} candidates to {OUT}")
    for wiki, n in sorted(per_wiki.items(), key=lambda x: -x[1]):
        print(f"  {wiki}: {n}")


if __name__ == "__main__":
    main()
