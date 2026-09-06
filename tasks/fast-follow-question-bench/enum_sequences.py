#!/usr/bin/env python3
"""Enumerate every distinct question sequence observed in fast-follow.

The fast-follow scaffold assigns one entity sequence per family. A
family is defined by (dataset, initial-prompt template). This script
groups every fast-follow revision by the exporter's `page_family` label
and reports one row per family with the most-common R1..R7 entity guess
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

# Human-authored one-line prompt shape per family. Each string paraphrases
# the scaffold's initial prompt using vocabulary lifted verbatim from at
# least one representative page in that family. See finding 11 for the
# per-family exemplar quote.
INFERRED_PROMPTS: dict[str, str] = {
    "oecd-equity":
        "OECD, share of private expenditure in early years of education, 2018, per country",
    "datausa-clothing-workforce":
        "DataUSA clothing manufacturing (NAICS 4481) workforce, per state",
    "datausa-cashiers-masters":
        "DataUSA cashiers with a Master's degree, count of workers per field of study",
    "datausa-construction-workforce":
        "DataUSA construction (Industry Sector 23) workforce, years 2016 and 2018, per state",
    "datausa-grocery-workforce":
        "DataUSA grocery stores (NAICS 4451) workforce, per state (uses G1..G6 round prefix)",
    "ihme-cvd-deaths":
        "IHME cardiovascular deaths, female age 70-74, years 2007-2010, per country",
    "datausa-language-french":
        "DataUSA ACS 2022, French (including Cajun), share of US speakers per state",
    "datausa-poverty-county":
        "DataUSA county poverty rate, per county",
    "datausa-maids-wage":
        "DataUSA maids and housekeeping cleaners (SOC 372012) wage, per (gender, year) combination",
    "datausa-police-wage-age":
        "DataUSA police officers (SOC 333050) wage year 2016, per age group",
    "datausa-transport-production":
        "DataUSA NAPCS transportation-equipment outbound production, per (state, year)",
    "datausa-sector61-state":
        "DataUSA sector 61 (educational services), per state (uses STATE5-XX terminal token)",
    "ihme-family-planning":
        "IHME SDG family planning need met with modern methods, women 15-49, year 1992, per country",
    "datausa-occupation-salary-61-62":
        "DataUSA occupation average salary, sectors 61-62, year 2020, per detailed occupation",
    "datausa-finance-gender-gap":
        "DataUSA personal financial advisors, male vs female count, year 2022",
    "oecd-regional-co2":
        "OECD Regional Recovery Platform, CO2 emissions from electricity generation, per country",
    "uefa-pass-accuracy":
        "UEFA U21 2021 pass-accuracy percentage, per team",
    "nyc-veterans":
        "DataUSA NYC veterans 2018, count per war era (some cohorts use Q1..Q5)",
    "datausa-enrollment-asian":
        "DataUSA Asian enrollment years 2012-14, per university",
    "datausa-poverty-state":
        "DataUSA state poverty rate 2013 and 2022 (uses Q1..Q3 round prefix)",
    "datausa-production-share":
        "DataUSA production-occupation share of workforce by city and gender, per year",
    "vermont-rent":
        "housingdata.org Vermont/Lamoille median gross rent estimate, per year",
    "datausa-cashiers-bachelors":
        "DataUSA cashiers with a Bachelor's degree, count of workers per field of study, year 2015",
    "datausa-ivy-tuition":
        "DataUSA Ivy Tech state tuition year 2015, per community college",
    "fuel-poverty-ni":
        "House of Commons Library fuel poverty dashboard, Northern Ireland 2016, per council area",
    "ihme-mcv2":
        "IHME SDG MCV2 vaccination coverage, per country",
    "ihme-smoking":
        "IHME SDG smoking prevalence age 15+, United States, year 1990 (follow-up varies year or country)",
    "sdg-index-score":
        "Sustainable Development Report SDG Index overall score, years 2010-2015, per country",
    "dataafrica-rainfed-crops":
        "Data Africa Mozambique rainfed crops, per province",
    "datausa-slp-ethnicity":
        "DataUSA speech-language pathologists, Puerto Rican employed, per (gender, year)",
    "oecd-household-income":
        "OECD household disposable income percentage change 2010/2013/2016/2019/2022 (July 2024 vintage), per country",
    "datausa-construction-wage":
        "DataUSA construction female electricians, Average Wage exclude MOE, per year",
    "datausa-cashier-skills":
        "DataUSA cashiers skill importance (RCA), year 2018, per skill",
    "alaska-climate":
        "Alaska climate, station-month-year extreme mean temperature, per (station, month, year, extremum)",
    "datausa-elpaso-foreign-born":
        "DataUSA El Paso TX foreign-born percentage, per year",
    "aihw-pbs":
        "AIHW PBS Dermatologicals, Victoria LGAs, January 2022 rolling 12-month average government cost per person, per LGA",
    "dataafrica-health-stunting":
        "Data Africa Mozambique moderately stunted percentage, per year",
    "ihme-lymphatic-filariasis":
        "IHME lymphatic filariasis, ICT antigen prevalence year 2007, aggregate over Ethiopia, Nigeria, Kenya, Sudan",
    "world-poverty-clock":
        "World Poverty Clock count and rate, per country (uses Q1..Q7 round prefix)",
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
        for rnd in range(1, 8):
            top = fam_rounds[fam][rnd].most_common(1)
            seq.append(top[0][0] if top else "")
        rows.append(
            {
                "id": len(rows) + 1,
                "family": fam,
                "num_occurrences": count,
                "inferred_prompt": INFERRED_PROMPTS.get(fam, ""),
                "r1": seq[0],
                "r2": seq[1],
                "r3": seq[2],
                "r4": seq[3],
                "r5": seq[4],
                "r6": seq[5],
                "r7": seq[6],
            }
        )

    fieldnames = [
        "id",
        "family",
        "num_occurrences",
        "inferred_prompt",
        "r1",
        "r2",
        "r3",
        "r4",
        "r5",
        "r6",
        "r7",
    ]
    with (OUT / "observed_sequences.tsv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        w.writeheader()
        for row in rows:
            w.writerow(row)

    missing_prompt = [row["family"] for row in rows if not row["inferred_prompt"]]
    if missing_prompt:
        print(f"WARNING: {len(missing_prompt)} families have no inferred_prompt: {missing_prompt}")

    print(f"Distinct fast-follow families observed: {len(rows)}")
    for row in rows:
        print(
            f"  {row['id']:2d} {row['num_occurrences']:5d} rev  "
            f"{row['family']:38s}  r1={row['r1'] or '?'}"
        )


if __name__ == "__main__":
    main()
