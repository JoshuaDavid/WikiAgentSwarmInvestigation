#!/usr/bin/env python3
"""Extract quoted evidence for every finding in this task's README.

Reads /collusionwiki/agent-logs/prowiki/revisions.jsonl and pages.jsonl.
Writes the following files under outputs/:

- regcf_revision_summary.tsv    aggregate counts (revisions, pages, labels, span)
- regcf_by_hour.tsv             hour-of-day distribution
- regcf_state_prefix_counts.tsv us-<state>- prefix counts in county.json queries
- regcf_pages_by_family.tsv     revision counts by page_family classification
- regcf_top_labels.tsv          top-N writer labels
- regcf_narrative_lines.txt     de-duplicated plain-text narrative lines

A revision is counted as "regCF-related" if its body contains `regCF` or
`us-ma-` or `county.json`. All three are near-synonyms in this cut: the
overlap is >99%.

Rerun with: python3 extract_evidence.py
"""

from __future__ import annotations
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
REV_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"
PAGES_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "pages.jsonl"
OUT_DIR = HERE / "outputs"

STATE_PREFIX_RE = re.compile(r"us-([a-z]{2})-")

# A body line is "narrative" if it is not a URL, is not URL-encoded, and is
# not a wiki link `[...]`. It must be 20-250 chars. This is deliberately
# strict to filter out the huge amount of URL-list churn in this cluster.
def is_narrative(line: str) -> bool:
    line = line.strip()
    if not (20 <= len(line) <= 250):
        return False
    if "http" in line or "%" in line or "[" in line:
        return False
    return True


def is_regcf(body: str) -> bool:
    return ("regCF" in body) or ("us-ma-" in body) or ("county.json" in body)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    page_family: dict[str, str] = {}
    with PAGES_PATH.open("r", encoding="utf-8") as pf:
        for line in pf:
            p = json.loads(line)
            page_family[p.get("page_id") or ""] = p.get("page_family") or "unknown"

    rev_ids: list[str] = []
    labels: Counter[str] = Counter()
    pages: Counter[str] = Counter()
    by_hour: Counter[str] = Counter()
    state_prefix_pages: Counter[str] = Counter()  # counts per-revision, not per-hit
    fam_regcf: Counter[str] = Counter()
    fam_total: Counter[str] = Counter()
    narrative: set[str] = set()
    first_time: str | None = None
    last_time: str | None = None

    with REV_PATH.open("r", encoding="utf-8") as rf:
        for line in rf:
            rev = json.loads(line)
            body = rev.get("body") or ""
            pid = rev.get("page_id") or ""
            fam = page_family.get(pid, "unknown")
            fam_total[fam] += 1

            if not is_regcf(body):
                continue

            fam_regcf[fam] += 1
            rev_ids.append(rev.get("rev_id") or "")
            labels[rev.get("label") or ""] += 1
            pages[pid] += 1

            t = rev.get("time") or ""
            if t:
                by_hour[t[:13]] += 1
                if first_time is None or t < first_time:
                    first_time = t
                if last_time is None or t > last_time:
                    last_time = t

            if "county.json" in body:
                for prefix in set(STATE_PREFIX_RE.findall(body)):
                    state_prefix_pages[prefix] += 1

            for raw in body.split("\n"):
                if is_narrative(raw):
                    narrative.add(raw.strip())

    # --- summary ---
    with (OUT_DIR / "regcf_revision_summary.tsv").open("w", encoding="utf-8") as f:
        f.write("metric\tvalue\n")
        f.write(f"regcf_revisions\t{len(rev_ids)}\n")
        f.write(f"regcf_distinct_pages\t{len(pages)}\n")
        f.write(f"regcf_distinct_labels\t{len(labels)}\n")
        f.write(f"regcf_first_time\t{first_time or ''}\n")
        f.write(f"regcf_last_time\t{last_time or ''}\n")
        f.write(f"labels_with_one_regcf_rev\t{sum(1 for c in labels.values() if c == 1)}\n")

    # --- hour distribution ---
    with (OUT_DIR / "regcf_by_hour.tsv").open("w", encoding="utf-8") as f:
        f.write("hour_utc\trevisions\n")
        for h, c in sorted(by_hour.items()):
            f.write(f"{h}\t{c}\n")

    # --- state prefix counts in county.json queries ---
    with (OUT_DIR / "regcf_state_prefix_counts.tsv").open("w", encoding="utf-8") as f:
        f.write("state_prefix\trevisions_containing_it\n")
        for prefix, c in state_prefix_pages.most_common():
            f.write(f"us-{prefix}-\t{c}\n")

    # --- page-family breakdown ---
    with (OUT_DIR / "regcf_pages_by_family.tsv").open("w", encoding="utf-8") as f:
        f.write("page_family\tregcf_revisions\ttotal_revisions\tpct_of_family\n")
        for fam in sorted(fam_regcf, key=lambda k: -fam_regcf[k]):
            tot = fam_total.get(fam, 0)
            pct = (fam_regcf[fam] / tot * 100) if tot else 0.0
            f.write(f"{fam}\t{fam_regcf[fam]}\t{tot}\t{pct:.1f}\n")

    # --- top labels ---
    with (OUT_DIR / "regcf_top_labels.tsv").open("w", encoding="utf-8") as f:
        f.write("label\tregcf_revisions\n")
        for lbl, c in labels.most_common(50):
            f.write(f"{lbl}\t{c}\n")

    # --- narrative lines ---
    with (OUT_DIR / "regcf_narrative_lines.txt").open("w", encoding="utf-8") as f:
        f.write(f"# {len(narrative)} distinct plain-text lines across regCF-related revisions\n")
        f.write("# (filtered to lines that are not URLs, not URL-encoded, and not [wiki-link])\n\n")
        for line in sorted(narrative):
            f.write(line + "\n")

    # --- stderr summary ---
    import sys
    print(f"regcf revisions: {len(rev_ids)} / {sum(fam_total.values())} total", file=sys.stderr)
    print(f"regcf labels: {len(labels)}", file=sys.stderr)
    print(f"regcf pages: {len(pages)}", file=sys.stderr)
    print(f"span: {first_time} to {last_time}", file=sys.stderr)
    print(f"top state prefixes: {state_prefix_pages.most_common(5)}", file=sys.stderr)


if __name__ == "__main__":
    main()
