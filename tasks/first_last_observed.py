#!/usr/bin/env python3
"""Compute the first and last observed message time per task family and, where
variants are defined, per variant, across every corpus in `agent-logs/`.

"Message" means one revision whose body matches the classifier for that task
or variant. Each per-task classifier reproduces the same detection logic used
by that task's own `extract_evidence.py`. See each task's README for the
classifier rationale.

Sources: every `agent-logs/<name>/revisions.jsonl`, with the aggregate
`pastes/` export skipped so its rows do not double-count the per-site paste
scrapes (`pastebin-k4be/`, `anna.fyi/`, ...).

Deduplication: same `rev_id` observed in more than one source (e.g.
`dse~PageName@N` appears in both `prowiki/` and `dse/`) is counted once and
attributed to its earliest observed timestamp.

Bodies from wiki exports are base64-decoded per `body_encoding`; paste bodies
are raw UTF-8.

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
AGENT_LOGS = REPO_ROOT / "agent-logs"
OUT_PATH = HERE / "first_last_observed.tsv"

# Sources to skip. `pastes/` is an aggregate export whose rows are
# already present under the per-site paste dirs; including it would
# double-count. `pastes-evidence-index/` is an index over `pastes/`,
# not a distinct corpus.
SKIP_SOURCES = {"pastes", "pastes-evidence-index"}

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


# --- vocab-puzzle-refs: single dse page --------------------------------------

VOCAB_PAGE_ID = "dse/AgentVocabPuzzleRefsJun20"


# --- driver ------------------------------------------------------------------

def decode_body(rev: dict) -> str:
    # Every `agent-logs/*/revisions.jsonl` in this repo stores the body as
    # raw text — `body_encoding` names the content encoding (`ascii`,
    # `raw_utf8`, `html_stripped_utf8`, `wiki_source_utf8`, ...), not a
    # base64 wrapper. Older exporter documentation still describes the
    # ascii/utf8/latin1 fields as base64-encoded, but the current export
    # files decode cleanly as raw text.
    return rev.get("body") or ""


def load_page_family_map() -> dict[str, str]:
    """page_key -> page_family across every source that populates it.

    Multiple sources classify the same page_key (e.g. `dse/StartSeite` is in
    both `dse/pages.jsonl` and `prowiki/pages.jsonl`). Prowiki carries the
    fine-grained fast-follow taxonomy (`oecd-equity`, `datausa-*`, ...);
    other sources fall back to `off_store_unclassified` for the same page.
    Prefer specific family labels; only accept `off_store_unclassified` when
    no other classification exists.
    """
    m: dict[str, str] = {}
    for pages_path in sorted(AGENT_LOGS.glob("*/pages.jsonl")):
        src = pages_path.parent.name
        if src in SKIP_SOURCES:
            continue
        with pages_path.open() as f:
            for line in f:
                if not line.strip():
                    continue
                p = json.loads(line)
                fam = p.get("page_family") or ""
                if not fam:
                    continue
                key = p.get("page_key") or p.get("page_id")
                if not key:
                    continue
                existing = m.get(key)
                if existing is None or (
                    existing == "off_store_unclassified" and fam != "off_store_unclassified"
                ):
                    m[key] = fam
    return m


def iter_revisions():
    """Yield (source_name, revision_dict) across every enabled source."""
    for rev_path in sorted(AGENT_LOGS.glob("*/revisions.jsonl")):
        src = rev_path.parent.name
        if src in SKIP_SOURCES:
            continue
        with rev_path.open() as f:
            for line in f:
                if not line.strip():
                    continue
                yield src, json.loads(line)


def main() -> None:
    page_family = load_page_family_map()

    # Two passes:
    # 1) Collect the earliest observed timestamp per rev_id across all
    #    sources. `dse/`, `fractal/`, `probier/` carry no body text
    #    themselves — only prowiki/apchem/paste-* have the body — but they
    #    do carry the earlier recent-changes-window timestamps we need.
    # 2) Classify each rev_id exactly once, using whichever source has a
    #    non-empty body for it. Attribute the match to the earliest time
    #    from pass 1.

    seen_rev: dict[str, str] = {}  # rev_id -> earliest_time
    for _, rev in iter_revisions():
        rid = rev.get("rev_id")
        t = rev.get("time") or ""
        if not rid or not t:
            continue
        prev = seen_rev.get(rid)
        if prev is None or t < prev:
            seen_rev[rid] = t

    times: dict[tuple[str, str], list[str]] = defaultdict(list)
    classified: set[str] = set()

    for _, rev in iter_revisions():
        rid = rev.get("rev_id")
        if not rid or rid in classified:
            continue
        body = decode_body(rev)
        if not body:
            continue
        classified.add(rid)
        body_lc = body.lower()

        matches: set[tuple[str, str]] = set()

        for inst in match_archive_instances(body_lc):
            matches.add(("archive-item-research-bench", inst))
            matches.add(("archive-item-research-bench", "(any variant)"))

        if is_fast_follow(body):
            fam = page_family.get(rev.get("page_key", "")) or ""
            if not fam:
                fam = page_family.get(rev.get("page_id", "")) or "unknown"
            matches.add(("fast-follow-question-bench", "(any variant)"))
            if fam in FAST_FOLLOW_FAMILIES:
                matches.add(("fast-follow-question-bench", fam))
            elif fam in HUB_FAMILIES:
                matches.add(("fast-follow-question-bench", f"(hub:{fam})"))
            else:
                matches.add(("fast-follow-question-bench", f"(other:{fam})"))

        if is_regcf(body):
            matches.add(("sec-regcf-ma-cache", "(no variants)"))

        if rev.get("page_id") == VOCAB_PAGE_ID:
            matches.add(("vocab-puzzle-refs", "(no variants)"))

        if not matches:
            continue
        t_earliest = seen_rev.get(rid) or rev.get("time") or ""
        if not t_earliest:
            continue
        for key in matches:
            times[key].append(t_earliest)

    rows: list[tuple[str, str, str, str, int]] = []
    task_order = [
        "archive-item-research-bench",
        "fast-follow-question-bench",
        "sec-regcf-ma-cache",
        "vocab-puzzle-refs",
    ]
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
            else:
                rows.append((task, variant, "", "", 0))
            emitted.add(variant)
        spill = sorted(v for (tk, v) in times if tk == task and v not in emitted)
        for variant in spill:
            ts = sorted(times[(task, variant)])
            rows.append((task, variant, ts[0], ts[-1], len(ts)))

    with OUT_PATH.open("w") as f:
        f.write("task\tvariant\tfirst_time\tlast_time\trevisions\n")
        for row in rows:
            f.write("\t".join([row[0], row[1], row[2], row[3], str(row[4])]) + "\n")

    print(f"wrote {OUT_PATH}", file=sys.stderr)
    n_hits = sum(len(v) for k, v in times.items() if k[1] == "(any variant)" or k[1].startswith("(no"))
    print(f"  {len(rows)} rows, {n_hits} classified revision-hits (task totals)", file=sys.stderr)


if __name__ == "__main__":
    main()
