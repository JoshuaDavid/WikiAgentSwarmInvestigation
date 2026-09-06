# 11 — The corpus contains at least 39 distinct question sequences

## Claim

Fast-follow-question-bench episodes in the corpus span 39 distinct
question sequences, not the ~8 named in the earlier findings or in
[`outputs/round_entity_counts.tsv`](../outputs/round_entity_counts.tsv).
The earlier count sampled only the highest-volume families for which the
initial evidence-extraction script produced a stable entity table. The
sequences below cover every `page_family` label the corpus exporter
assigned to a fast-follow-signal-carrying revision, minus hub-page
labels (`relay-coordination`, `off_store_unclassified`, `mixed-task`,
`unknown`, `probe-test`, `source-cache-url-list`, `source-or-unclassified`).

## Evidence

Regenerate with:

    python3 enum_sequences.py

The script writes
[`outputs/observed_sequences.tsv`](../outputs/observed_sequences.tsv).
Each row: one `page_family`, revision count, page count, and the
most-common R1..R6 entity string observed in that family's bodies. The
count of families in the output is 39.

The 39 sequences below are grouped by data source. Each entry names the
initial-prompt template inferred from at least one representative page.

### DataUSA (22)

Datausa.io benchmark pages, tesseract cubes, and profile URLs.

| # | Family (page_family) | Prompt shape | Observed R1..R? |
|---|---|---|---|
| 1 | `datausa-cashiers-masters` | Cashiers, Master's degree, count of workers by field of study | Education → Business → Social Sciences → Visual & Performing Arts → Psychology |
| 2 | `datausa-cashiers-bachelors` | Cashiers, Bachelor's degree, count of workers by field of study, 2015 | Business → Education → Social Sciences → Visual & Performing Arts → Psychology |
| 3 | `datausa-cashier-skills` | Cashiers skill importance (RCA), 2018 | Operation and Control → Service Orientation → Critical Thinking → Writing |
| 4 | `datausa-construction-workforce` | Construction (Industry Sector 23) workforce, 2016 and 2018, by state | New York → Arizona → Utah → Colorado → New Mexico (also observed CA, TX, FL sub-sequences) |
| 5 | `datausa-construction-wage` | Construction female electricians, Average Wage exclude MOE, by year | 2014 → 2015 → 2016 → 2017 → 2018 → … |
| 6 | `datausa-clothing-workforce` | Clothing manufacturing (4481) workforce, by state | CA → NY → (state #3 …) |
| 7 | `datausa-elpaso-foreign-born` | El Paso TX foreign-born percentage, by year | 2015 → 2016 → 2017 → 2018 → 2019 → … |
| 8 | `datausa-enrollment-asian` | Asian enrollment by university, years 2012–14 | Michigan State → Capella → University of Utah → Arizona → … |
| 9 | `datausa-finance-gender-gap` | Personal financial advisors male vs female, 2022 | 2022 M/F → (next year or occupation) |
| 10 | `datausa-grocery-workforce` | Grocery Stores (4451) workforce, by state (uses `G1..G6` round prefix) | Georgia → Arkansas → Nevada → Kentucky → Maryland |
| 11 | `datausa-ivy-tuition` | Ivy Tech 2015 state tuition, by community college | Arkansas Northeastern → Pitt CC → Cleveland CC → John C Calhoun CC → St Cloud CC |
| 12 | `datausa-language-french` | Language at home, French (Cajun), share of US speakers by state, ACS 2022 | Texas → Louisiana → New York → New Hampshire → California |
| 13 | `datausa-maids-wage` | Maids and housekeeping cleaners (372012) wage, by gender+year | Female 2015 → Male 2016 → Female 2016 → … |
| 14 | `datausa-occupation-salary-61-62` | Occupation average salary in sectors 61–62, 2020 | School psychologists → Medical transcriptionists → Maids → Billing clerks |
| 15 | `datausa-police-wage-age` | Police officers (333050) 2016 wage, by age group | 25–29 → 30–34 → 35–39 → 40–44 → 45–49 → … (ascending) |
| 16 | `datausa-poverty-county` | County poverty rate | Flathead MT → Merced CA → San Juan NM → Saginaw MI → R5 |
| 17 | `datausa-poverty-state` | State poverty rate 2013 and 2022 (uses `Q1..Q3` round prefix) | Louisiana → Mississippi → Alabama → Georgia |
| 18 | `datausa-production-share` | Production-occupation share by city/gender, year | Los Angeles/NY/Houston/Chicago 2013 → 2016 → … |
| 19 | `datausa-sector61-state` | Sector 61 (educational services) by state (uses `#5` / `STATE5-XX`) | MA → CT → MI → WV → #5 |
| 20 | `datausa-slp-ethnicity` | Speech-language pathologists, Puerto Rican, employed by sex, year | 2020 → 2021 → 2022 → 2023 → 2024 |
| 21 | `datausa-transport-production` | NAPCS transportation-equipment outbound production, by state+year | California 2017 → Texas → … |
| 22 | `nyc-veterans` | DataUSA NYC veterans, 2018, by war era (some cohorts use `Q1..Q5`) | WWII → Korea → Vietnam → Gulf 1990s → Gulf 2001- → Other |

### OECD (3)

Datasets published by the Organisation for Economic Co-operation and
Development.

| # | Family | Prompt shape | Observed R1..R? |
|---|---|---|---|
| 23 | `oecd-equity` | Share of private expenditure in early years of education (2018) | Czech Republic → Hungary → Poland → Slovak Republic → Slovenia |
| 24 | `oecd-regional-co2` | Regional Recovery Platform: CO2 emissions from electricity generation | Colombia → Mexico → Chile → Poland → Italy → … |
| 25 | `oecd-household-income` | Household disposable income percentage change 2010/2013/2016/2019/2022, published Jul 2024 | Austria (initial) → Czechia → Mexico → Poland → Sweden |

### IHME / OWID health (5)

Institute for Health Metrics and Evaluation (healthdata.org), mirrored
through Our World in Data.

| # | Family | Prompt shape | Observed R1..R? |
|---|---|---|---|
| 26 | `ihme-cvd-deaths` | Cardiovascular deaths, female age 70–74, years 2007–2010, by country | Armenia → Kazakhstan → Turkmenistan → Hungary → Poland → Slovenia |
| 27 | `ihme-family-planning` | SDG family planning need met with modern methods, women 15–49, year 1992 | Croatia → Albania → Cyprus → Bahrain |
| 28 | `ihme-mcv2` | SDG MCV2 vaccination coverage | Indonesia → Samoa → Algeria → R4 |
| 29 | `ihme-smoking` | SDG smoking prevalence, age 15+, United States, year 1990 (follow-up varies year or country) | US 1990 → R2 |
| 30 | `ihme-lymphatic-filariasis` | LF prevalence ICT antigen 2007 (aggregate over Ethiopia, Nigeria, Kenya, Sudan) | Ethiopia+Nigeria+Kenya+Sudan → R2 |

### Other single-source (9)

| # | Family | Prompt shape | Observed R1..R? |
|---|---|---|---|
| 31 | `uefa-pass-accuracy` | UEFA U21 2021 pass-accuracy percentage, by team | Czech Republic 74 → Hungary 72 → Italy 81 → Romania → Slovenia |
| 32 | `fuel-poverty-ni` | House of Commons Library fuel poverty dashboard, Northern Ireland 2016, by council area | Belfast → Mid Ulster → Ards and North Down → Derry City and Strabane |
| 33 | `alaska-climate` | Alaska climate, station-month-year extreme means | Yakutat June 1965 lowest → Valdez October 2002 highest → Talkeetna September 1992 lowest → St. Paul Aug 2016 highest → Nome July 1922 lowest |
| 34 | `aihw-pbs` | Australian Institute of Health and Welfare, PBS Dermatologicals, Victoria LGAs, January 2022 12-month rolling | Wodonga → Ballarat → R3 |
| 35 | `dataafrica-rainfed-crops` | Data Africa: Mozambique rainfed crops, by province | Niassa → Cabo Delgado → Nampula → Zambezia → Tete |
| 36 | `dataafrica-health-stunting` | Data Africa: Mozambique moderately stunted percentage, by year | 1997 → 2003 → 2011 |
| 37 | `gapminder-age80` | Gapminder proportion age 80, year 2023, by country | Canada → United States → Mexico → Brazil → Argentina |
| 38 | `sdg-index-score` | Sustainable Development Report SDG Index overall score, years 2010–2015, by country | Spain → Hungary → (R3 predicted Poland) |
| 39 | `world-poverty-clock` | World Poverty Clock count and rate, by country (uses `Q1..Q7`) | India → Pakistan → Afghanistan → China → Micronesia → Paraguay → South Sudan |

### `vermont-rent` note

The `vermont-rent` `page_family` label carries 20 R-token revisions in
the fast-follow bucket. Nineteen of them land on `dse~StartSeite`,
which the classifier assigned to `vermont-rent` on a narrow signal
that does not reflect the mix of activity on the hub page (see the
warning in `agent-logs/prowiki/README.md`). The one page whose body
actually describes the sequence is
`dse~RentVermontLamoilleSequenceSep26`: housingdata.org median gross
rent estimates for Vermont and Lamoille County, one year per round
(2018 → 2019 → 2020 → 2021 → 2022 confirmed). So a 40th sequence
exists in the corpus; the classifier just did not surface it as its
own family. It is folded into the 39 count above via `vermont-rent`.

## Counterevidence

- **Sub-sequences within one page_family.** `datausa-construction-workforce`
  carries at least two starting states (New York, Arizona) across
  different cohorts. Either the family is one sequence with a cohort-picked
  starting index into a fixed ring, or it splits into two families the
  classifier did not distinguish. This ambiguity affects at most 3 of
  the 39 families (`datausa-construction-workforce`,
  `datausa-clothing-workforce`, `datausa-cashiers-masters` /
  `datausa-cashiers-bachelors`). The correct count is therefore 39 to
  about 43.

- **Hub-page-only families.** Three of the 39 families
  (`ihme-lymphatic-filariasis`, `gapminder-age80`, `aihw-pbs`,
  `dataafrica-health-stunting`, `world-poverty-clock`) appear on one
  page each with one to seven revisions. They may be aborted rollouts
  rather than full sequences. The evidence is consistent with either.

## Uncertain

- Whether more sequences ran in the incident and left no wiki trace.
  The wikis are a shared cache. A cohort that answered without editing
  a wiki would be invisible.

- Whether the fictional cohort-date tokens (`Feb17`, `Mar13`,
  `Sep17`, …) name distinct sequence variants or just distinct random
  seeds for the same sequence. The available bodies are consistent with
  one fixed entity order per family across all cohort dates within
  that family.
