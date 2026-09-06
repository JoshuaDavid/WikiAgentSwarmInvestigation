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

# Human-authored initial-prompt paraphrase per family. Each string is
# phrased as a natural-language question, with one `{placeholder}` slot
# that the r1..r7 entities substitute into on each round. Wording is
# lifted from a representative page body wherever possible. See
# finding 11 for the per-family exemplar quote.
INFERRED_PROMPTS: dict[str, str] = {
    "oecd-equity":
        "Of all expenditure on Pre-Primary education (public + private) in {country} "
        "in 2018, what percentage came from private sources? Answer to two decimal places.",
    "datausa-clothing-workforce":
        "For Clothing Manufacturing (NAICS 4481) in {state}, what was the workforce count?",
    "datausa-cashiers-masters":
        "In the United States, how many cashiers hold a Master's degree with "
        "major {field_of_study}?",
    "datausa-construction-workforce":
        "For Construction (Industry Sector 23) in {state}, what was the workforce "
        "count in 2016 and in 2018?",
    "datausa-grocery-workforce":
        "For Grocery Stores (NAICS 4451) in {state}, what was the workforce count?",
    "ihme-cvd-deaths":
        "For females aged 70-74 in {country}, what were the cardiovascular disease "
        "death rates in years 2007, 2008, 2009, and 2010?",
    "datausa-language-french":
        "According to the ACS 2022 1-year estimate, what share of US speakers of "
        "French (including Cajun) lived in {state}? Answer to two decimal places.",
    "datausa-poverty-county":
        "What was the poverty rate in {county} County?",
    "datausa-maids-wage":
        "For maids and housekeeping cleaners (SOC 372012), what was the average "
        "wage for {gender_year}?",
    "datausa-police-wage-age":
        "For police officers (SOC 333050) in 2016, what were the male and female "
        "average wages for the {age_group} age group?",
    "datausa-transport-production":
        "For NAPCS transportation-equipment outbound production, what was the "
        "value in {state_year}?",
    "datausa-sector61-state":
        "For DataUSA sector 61 (educational services) in {state}, what was the "
        "value? (some cohorts terminate at round 5 with a STATE5-XX signal token)",
    "ihme-family-planning":
        "For {country}, what proportion of women aged 15-49 had family planning "
        "need met by modern methods in 1992?",
    "datausa-occupation-salary-61-62":
        "For sectors 61-62 (educational services, health care & social assistance) "
        "in 2020, what was the average salary for {occupation}?",
    "datausa-finance-gender-gap":
        "For personal financial advisors in {year}, what were the male count, "
        "female count, and gap?",
    "oecd-regional-co2":
        "According to the OECD Regional Recovery Platform, what were CO2 emissions "
        "from electricity generation in {country}?",
    "uefa-pass-accuracy":
        "In the UEFA U21 2021 tournament, what was the pass-accuracy percentage "
        "for {country}?",
    "nyc-veterans":
        "For DataUSA NYC veterans in 2018, how many served in the {war_era} war "
        "era? (exclude MOE)",
    "datausa-enrollment-asian":
        "For {university}, what was the Asian enrollment in each of the years "
        "2012, 2013, and 2014?",
    "datausa-poverty-state":
        "According to DataUSA (ACS 5-year), what was the poverty rate in {state} "
        "in 2013 and in 2022?",
    "datausa-production-share":
        "For the Production occupation group in Los Angeles, New York, Houston, "
        "and Chicago, what was the share of workforce (men, women, overall) in "
        "{year}?",
    "vermont-rent":
        "According to housingdata.org, what was the median gross rent estimate "
        "for Vermont and for Lamoille County in {year}?",
    "datausa-cashiers-bachelors":
        "In 2015, how many US cashiers held a Bachelor's degree with major "
        "{field_of_study}?",
    "datausa-ivy-tuition":
        "For {college} in 2015, what was the state tuition (DataUSA, Ivy Tech "
        "reference sequence)?",
    "fuel-poverty-ni":
        "For {council_area} in Northern Ireland in 2016, what was the fuel poverty "
        "count (House of Commons Library dashboard)?",
    "ihme-mcv2":
        "For {country}, what was the SDG MCV2 vaccination coverage percentage?",
    "ihme-smoking":
        "According to the SDG health visual, what was the estimated prevalence of "
        "current/active tobacco use age 15+ in {country_year}?",
    "sdg-index-score":
        "According to the Sustainable Development Report, what were the SDG Index "
        "overall scores for {country} in each of the years 2010, 2011, 2012, 2013, "
        "2014, and 2015?",
    "dataafrica-rainfed-crops":
        "For {province} province of Mozambique, what were the rainfed Cassava, "
        "Cotton, and Sugarcane values (Data Africa)?",
    "datausa-slp-ethnicity":
        "For speech-language pathologists in {year}, what were the Puerto Rican "
        "employed counts by sex (DataUSA)?",
    "oecd-household-income":
        "For {country}, what was the household disposable income percentage "
        "change in each of the years 2010, 2013, 2016, 2019, and 2022 (OECD, "
        "indicator published 2024-07-15)?",
    "datausa-construction-wage":
        "For female electricians in Construction in {year}, what was the average "
        "wage (excluding MOE)?",
    "datausa-cashier-skills":
        "For US cashiers in 2018, what was the skill importance RCA value for "
        "{skill}?",
    "alaska-climate":
        "For {station_month_year_extremum}, what was the mean temperature (Alaska "
        "climate data, degrees Fahrenheit)?",
    "datausa-elpaso-foreign-born":
        "For El Paso, TX in {year}, what was the foreign-born percentage?",
    "aihw-pbs":
        "For {LGA} local government area (Victoria), what was the rolling "
        "12-month average government cost per person for Dermatologicals in "
        "January 2022 (AIHW PBS dashboard)?",
    "dataafrica-health-stunting":
        "For Mozambique in {year}, what was the moderately stunted percentage "
        "(Data Africa)?",
    "ihme-lymphatic-filariasis":
        "What was the aggregate mean prevalence of Lymphatic Filariasis (ICT "
        "antigen test) for {countries_year}?",
    "world-poverty-clock":
        "According to the World Poverty Clock, for {country} what were the "
        "current count of people in extreme poverty and the rate?",
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
