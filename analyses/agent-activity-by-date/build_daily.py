#!/usr/bin/env python3
"""Bucket every revision in agent-logs/prowiki/revisions.jsonl by UTC day.

Two output tables:

  outputs/daily_totals.tsv     date, revisions
  outputs/daily_by_variant.tsv date, task, variant, revisions

The task/variant classifier is the one from tasks/first_last_observed.py.
A revision that matches more than one task is counted in each of them
(same policy as first_last_observed.py). A revision that matches no task
is counted as ("unclassified", "(none)").

Rerun with:
    python3 analyses/agent-activity-by-date/build_daily.py
"""
from __future__ import annotations
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
REV_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"
PAGES_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "pages.jsonl"
OUT_DIR = HERE / "outputs"

# --- classifiers (lifted from tasks/first_last_observed.py) ------------------

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


R_TOKEN = re.compile(r"\b[RGQC][1-9]\b")
FAST_FOLLOW_MARKERS = re.compile(
    r"(clock\.wait|cooldown|task[-\s]?clock|scaffold[-\s]?clock|deadline|"
    r"cohort|sequence|timer|Now,?\s+do\s+the\s+same|initial\s+prompt|"
    r"tier|cadence|projected|followup)",
    re.IGNORECASE,
)
HUB_FAMILIES = {
    "relay-coordination", "off_store_unclassified", "mixed-task", "unknown",
    "probe-test", "source-cache-url-list", "source-or-unclassified",
}
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


def is_regcf(body: str) -> bool:
    return ("regCF" in body) or ("us-ma-" in body) or ("county.json" in body)


VOCAB_PAGE_ID = "dse/AgentVocabPuzzleRefsJun20"


def load_page_family() -> dict[str, str]:
    m: dict[str, str] = {}
    with PAGES_PATH.open() as f:
        for line in f:
            p = json.loads(line)
            m[p["page_key"]] = p.get("page_family", "") or ""
    return m


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page_family = load_page_family()

    totals: dict[str, int] = defaultdict(int)
    # (task, variant, date) -> count
    by_variant: dict[tuple[str, str, str], int] = defaultdict(int)

    n_rev = 0
    with REV_PATH.open() as rf:
        for line in rf:
            rev = json.loads(line)
            t = rev.get("time") or ""
            if not t:
                continue
            date = t[:10]
            body = rev.get("body") or ""
            body_lc = body.lower()
            totals[date] += 1
            n_rev += 1

            matched = False

            for inst in match_archive_instances(body_lc):
                by_variant[("archive-item-research-bench", inst, date)] += 1
                matched = True

            if is_fast_follow(body):
                fam = page_family.get(rev.get("page_key", ""), "") or "unknown"
                if fam in FAST_FOLLOW_FAMILIES:
                    variant = fam
                elif fam in HUB_FAMILIES:
                    variant = f"(hub:{fam})"
                else:
                    variant = f"(other:{fam})"
                by_variant[("fast-follow-question-bench", variant, date)] += 1
                matched = True

            if is_regcf(body):
                by_variant[("sec-regcf-ma-cache", "(no variants)", date)] += 1
                matched = True

            if rev.get("page_id") == VOCAB_PAGE_ID:
                by_variant[("vocab-puzzle-refs", "(no variants)", date)] += 1
                matched = True

            if not matched:
                by_variant[("unclassified", "(none)", date)] += 1

    with (OUT_DIR / "daily_totals.tsv").open("w") as f:
        f.write("date\trevisions\n")
        for date in sorted(totals):
            f.write(f"{date}\t{totals[date]}\n")

    with (OUT_DIR / "daily_by_variant.tsv").open("w") as f:
        f.write("date\ttask\tvariant\trevisions\n")
        for (task, variant, date), n in sorted(by_variant.items()):
            f.write(f"{date}\t{task}\t{variant}\t{n}\n")

    print(f"wrote {OUT_DIR / 'daily_totals.tsv'}  ({len(totals)} dates, {n_rev} revs)",
          file=sys.stderr)
    print(f"wrote {OUT_DIR / 'daily_by_variant.tsv'}  ({len(by_variant)} rows)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
