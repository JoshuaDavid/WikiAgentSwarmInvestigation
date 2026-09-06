#!/usr/bin/env python3
"""Enumerate every distinct question sequence observed in fast-follow.

The fast-follow scaffold assigns one entity sequence per family. A
family is defined by (dataset, initial-prompt template). This script
groups every fast-follow revision by the exporter's `page_family` label
and reports one row per family with the most-common R1..R6 entity guess
in that family.

The output is `outputs/observed_sequences.tsv`. Anyone who wants the
full list of question sequences in the corpus reads that file.
"""

import collections
import csv
import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
PROWIKI = REPO / "agent-logs" / "prowiki"
OUT = pathlib.Path(__file__).resolve().parent / "outputs"

R_TOKEN = re.compile(r"\b[RGQC][1-9]\b")
R_ENT = re.compile(r"\b([RGQC])([1-9])\s+([A-Z][A-Za-z][A-Za-z\-. &,/]{2,38}?)(?=[,.;:\s]|$)")

FAST_FOLLOW_MARKERS = re.compile(
    r"(clock\.wait|cooldown|task[-\s]?clock|scaffold[-\s]?clock|deadline|"
    r"cohort|sequence|timer|Now,?\s+do\s+the\s+same|initial\s+prompt|"
    r"tier|cadence|projected|followup)",
    re.IGNORECASE,
)

# Words that pattern-match R\d+ <UPPER> but are not entity names.
SKIP_WORDS = {
    "CONFIRMED", "PROMPT", "PROJECTED", "DUE", "ETA", "FINAL", "TIMER",
    "ARRIVED", "HERE", "ANSWERED", "URGENT", "WAITING", "TEST", "SIGNAL",
    "FAST", "LIVE", "READY", "MONITOR", "PLEASE", "STATUS", "ACTIVE",
    "THREAD", "SCAFFOLD", "RELAY", "TASK", "SCHEDULED", "HEARTBEAT",
    "EXISTS", "PREDICTION", "ASAP", "COUNTRY", "STATE", "AT", "BEFORE",
    "ACTUAL", "GET", "PITT", "AND",
}

# Families that are hub/coordination pages, not question sequences.
HUB_FAMILIES = {
    "relay-coordination",
    "off_store_unclassified",
    "mixed-task",
    "unknown",
    "probe-test",
    "source-cache-url-list",
    "source-or-unclassified",
}


def main() -> None:
    OUT.mkdir(exist_ok=True)

    page_family: dict[str, str] = {}
    with (PROWIKI / "pages.jsonl").open() as f:
        for line in f:
            p = json.loads(line)
            page_family[p["page_key"]] = p.get("page_family", "")

    fam_revs = collections.Counter()
    fam_pages: dict[str, set[str]] = collections.defaultdict(set)
    fam_rounds: dict[str, dict[int, collections.Counter]] = collections.defaultdict(
        lambda: collections.defaultdict(collections.Counter)
    )

    with (PROWIKI / "revisions.jsonl").open() as f:
        for line in f:
            r = json.loads(line)
            body = r.get("body") or ""
            if not R_TOKEN.search(body):
                continue
            if not FAST_FOLLOW_MARKERS.search(body):
                continue
            pk = r.get("page_key", "")
            fam = page_family.get(pk, "unknown")
            fam_revs[fam] += 1
            fam_pages[fam].add(pk)
            for m in R_ENT.finditer(body):
                digit = int(m.group(2))
                ent = re.sub(r"\s+", " ", m.group(3).strip())
                head = ent.upper().split()[0] if ent else ""
                if head in SKIP_WORDS:
                    continue
                if not (3 <= len(ent) <= 30):
                    continue
                fam_rounds[fam][digit][ent] += 1

    rows: list[dict] = []
    for fam, count in fam_revs.most_common():
        if fam in HUB_FAMILIES:
            continue
        seq = []
        for rnd in range(1, 7):
            top = fam_rounds[fam][rnd].most_common(1)
            seq.append(top[0][0] if top else "")
        rows.append(
            {
                "page_family": fam,
                "fast_follow_revisions": count,
                "pages": len(fam_pages[fam]),
                "R1": seq[0],
                "R2": seq[1],
                "R3": seq[2],
                "R4": seq[3],
                "R5": seq[4],
                "R6": seq[5],
            }
        )

    with (OUT / "observed_sequences.tsv").open("w") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "page_family",
                "fast_follow_revisions",
                "pages",
                "R1",
                "R2",
                "R3",
                "R4",
                "R5",
                "R6",
            ],
            delimiter="\t",
        )
        w.writeheader()
        for row in rows:
            w.writerow(row)

    print(f"Distinct fast-follow families observed: {len(rows)}")
    for row in rows:
        print(
            f"  {row['fast_follow_revisions']:5d} rev  "
            f"{row['page_family']:38s}  "
            f"R1={row['R1'] or '?'}"
        )


if __name__ == "__main__":
    main()
