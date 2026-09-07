#!/usr/bin/env python3
"""Compute the first and last observed message time per task family and, where
variants are defined, per variant.

"Message" here means one revision in `agent-logs/prowiki/revisions.jsonl`
whose body matches the classifier for that task or variant. Each per-task
classifier reproduces the same detection logic used by that task's own
`extract_evidence.py`. See each task's README for the classifier rationale.

Writes `tasks/first_last_observed.tsv`. Rerun with:

    python3 tasks/first_last_observed.py
"""

from __future__ import annotations
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
REV_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"
PAGES_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "pages.jsonl"
OUT_PATH = HERE / "first_last_observed.tsv"

# --- archive-item-research-bench: 7 instances --------------------------------
# Lifted verbatim from tasks/archive-item-research-bench/extract_evidence.py.

ARCHIVE_INSTANCES: dict[str, list[str]] = {
    "art-work-of-charleston": [
        "lcdl:129140", "lcdl:129141", "lcdl:129142", "lcdl:129143", "lcdl:129144",
        "lcdl:129145", "lcdl:129146", "lcdl:129147", "lcdl:129148", "lcdl:129229",
        "lcdl129140", "lcdl129141", "lcdl129142", "lcdl129143", "lcdl129144",
        "lcdl129145", "lcdl129146", "lcdl129147", "lcdl129148", "lcdl129229",
        "lcdl%3a129",
        "205927", "205928", "205929", "205930", "205931", "205932", "205933", "205934",
        "art-work-of-charleston", "historic-charleston-foundation", "chp4demo850801",
    ],
    "patriots-point-jan-1951": [
        "lcdl:123721", "lcdl123721", "lcdl:123716", "lcdl123716", "217622",
        "patriots point", "patriot", "shipyard", "jan1951", "january 1951",
    ],
    "texas-tsl-preservica": [
        "tsl.access.preservica.com", "tsl.preservica.com",
        "io_f436a16c", "f436a16c-767f-44b8-95fc-2031847276b9",
    ],
    "clark-economics-newsletters": [
        "clarku.edu/departments/economics", "www2.clarku.edu/departments/economics",
        "clark university economics", "newsletter2012", "newsletter%25202010",
        "newsletter 2010", "newsletter2010", "clark newsletter", "clark econ",
    ],
    "minnesota-mhs-p16022coll45-152": [
        "p16022coll45/id/152", "p16022coll45%3a152", "p16022coll45:152",
        "cdm16022", "mhs52936", "52936", "mhs 52936", "collection.mndigital.org",
    ],
    "cgsc-hoffman-order-of-battle": [
        "cgsc.contentdm.oclc.org", "p4013coll7",
    ],
    "rugby-world-march-1995": [
        "themagazinearchive", "pagesuite", "rugby world", "rugbyworldfree",
        "ca6f26c8-fa61-463f-a0e5-ec848a0b0044",
    ],
}


def match_archive_instances(body_lc: str) -> set[str]:
    return {name for name, needles in ARCHIVE_INSTANCES.items()
            if any(k in body_lc for k in needles)}


# --- fast-follow-question-bench: 39 families ---------------------------------
# Match logic lifted from tasks/fast-follow-question-bench/enum_sequences.py.

R_TOKEN = re.compile(r"\b[RGQC][1-9]\b")
FAST_FOLLOW_MARKERS = re.compile(
    r"(clock\.wait|cooldown|task[-\s]?clock|scaffold[-\s]?clock|deadline|"
    r"cohort|sequence|timer|Now,?\s+do\s+the\s+same|initial\s+prompt|"
    r"tier|cadence|projected|followup)",
    re.IGNORECASE,
)
HUB_FAMILIES = {
    "relay-coordination",
    "off_store_unclassified",
    "mixed-task",
    "unknown",
    "probe-test",
    "source-cache-url-list",
    "source-or-unclassified",
}
# The 39 families the task's README enumerates (order preserved from
# outputs/observed_sequences.tsv).
FAST_FOLLOW_FAMILIES = [
    "oecd-equity", "datausa-clothing-workforce", "datausa-cashiers-masters",
    "datausa-construction-workforce", "datausa-grocery-workforce",
    "ihme-cvd-deaths", "datausa-language-french", "datausa-poverty-county",
    "datausa-maids-wage", "datausa-police-wage-age",
    "datausa-transport-production", "datausa-sector61-state",
    "ihme-family-planning", "datausa-occupation-salary-61-62",
    "datausa-finance-gender-gap", "oecd-regional-co2", "uefa-pass-accuracy",
    "nyc-veterans", "datausa-enrollment-asian", "datausa-poverty-state",
    "datausa-production-share", "vermont-rent", "datausa-cashiers-bachelors",
    "datausa-ivy-tuition", "fuel-poverty-ni", "ihme-mcv2", "ihme-smoking",
    "sdg-index-score", "dataafrica-rainfed-crops", "datausa-slp-ethnicity",
    "oecd-household-income", "datausa-construction-wage",
    "datausa-cashier-skills", "alaska-climate", "datausa-elpaso-foreign-born",
    "aihw-pbs", "dataafrica-health-stunting", "ihme-lymphatic-filariasis",
    "world-poverty-clock",
]


def is_fast_follow(body: str) -> bool:
    if not R_TOKEN.search(body):
        return False
    return bool(FAST_FOLLOW_MARKERS.search(body))


# --- sec-regcf-ma-cache: no variants -----------------------------------------

def is_regcf(body: str) -> bool:
    return ("regCF" in body) or ("us-ma-" in body) or ("county.json" in body)


# --- vocab-puzzle-refs: single instance --------------------------------------

VOCAB_PAGE_ID = "dse/AgentVocabPuzzleRefsJun20"


# --- driver ------------------------------------------------------------------

def load_page_family() -> dict[str, str]:
    m: dict[str, str] = {}
    with PAGES_PATH.open() as f:
        for line in f:
            p = json.loads(line)
            m[p["page_key"]] = p.get("page_family", "") or ""
    return m


def main() -> None:
    page_family = load_page_family()

    # (task, variant) -> [times]
    times: dict[tuple[str, str], list[str]] = defaultdict(list)

    with REV_PATH.open() as rf:
        for line in rf:
            rev = json.loads(line)
            body = rev.get("body") or ""
            t = rev.get("time") or ""
            if not t:
                continue
            body_lc = body.lower()

            # archive-item-research-bench
            for inst in match_archive_instances(body_lc):
                times[("archive-item-research-bench", inst)].append(t)
                times[("archive-item-research-bench", "(any variant)")].append(t)

            # fast-follow-question-bench
            if is_fast_follow(body):
                fam = page_family.get(rev.get("page_key", ""), "") or "unknown"
                times[("fast-follow-question-bench", "(any variant)")].append(t)
                if fam in FAST_FOLLOW_FAMILIES:
                    times[("fast-follow-question-bench", fam)].append(t)
                elif fam in HUB_FAMILIES:
                    times[("fast-follow-question-bench", f"(hub:{fam})")].append(t)
                else:
                    times[("fast-follow-question-bench", f"(other:{fam})")].append(t)

            # sec-regcf-ma-cache
            if is_regcf(body):
                times[("sec-regcf-ma-cache", "(no variants)")].append(t)

            # vocab-puzzle-refs
            if rev.get("page_id") == VOCAB_PAGE_ID:
                times[("vocab-puzzle-refs", "(no variants)")].append(t)

    # De-duplicate task totals across variants using the "(any variant)" bucket
    # already populated above.
    rows: list[tuple[str, str, str, str, int]] = []
    # Fixed task order in the output.
    task_order = [
        "archive-item-research-bench",
        "fast-follow-question-bench",
        "sec-regcf-ma-cache",
        "vocab-puzzle-refs",
    ]
    # For each task, emit the totals row first, then variants in the order
    # listed above (for fast-follow) or in the extract_evidence order (for
    # archive), then any spillover buckets (hub/other) at the end.
    variant_order = {
        "archive-item-research-bench":
            ["(any variant)"] + list(ARCHIVE_INSTANCES.keys()),
        "fast-follow-question-bench":
            ["(any variant)"] + FAST_FOLLOW_FAMILIES,
        "sec-regcf-ma-cache": ["(no variants)"],
        "vocab-puzzle-refs": ["(no variants)"],
    }

    for task in task_order:
        emitted: set[str] = set()
        for variant in variant_order[task]:
            key = (task, variant)
            if key in times:
                ts = sorted(times[key])
                rows.append((task, variant, ts[0], ts[-1], len(ts)))
                emitted.add(variant)
            else:
                rows.append((task, variant, "", "", 0))
                emitted.add(variant)
        # spillover buckets (hub:*, other:*) — sorted for determinism.
        spill = sorted(v for (tk, v) in times if tk == task and v not in emitted)
        for variant in spill:
            key = (task, variant)
            ts = sorted(times[key])
            rows.append((task, variant, ts[0], ts[-1], len(ts)))

    with OUT_PATH.open("w") as f:
        f.write("task\tvariant\tfirst_time\tlast_time\trevisions\n")
        for row in rows:
            f.write("\t".join([row[0], row[1], row[2], row[3], str(row[4])]) + "\n")

    print(f"wrote {OUT_PATH}", file=sys.stderr)
    print(f"  {len(rows)} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
