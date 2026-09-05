# Finding 10: Sources are public statistical datasets

## Claim

Every question the scaffold asks has a known correct answer retrievable
from a public statistical dataset. No question requires prediction of
future values or synthesis of new information.

## Evidence

Sources observed across families:

| Family | Source |
|---|---|
| `oecd_equity` | OECD education equity indicator |
| `oecd_regional_co2` | OECD regional CO2 dashboard |
| `oecd_household_income` | OECD household disposable income |
| `grocery` | DataUSA `pums_5`, industry group 4451 |
| `clothing` | DataUSA `pums_5`, industry group 4481 |
| `sector_61` | DataUSA `pums_5`, industry sector 61-62 |
| `poverty_county` | DataUSA `acs_ygpsar_poverty_by_gender_age_race_5` |
| `finance` | DataUSA `pums_5`, occupation-specific |
| `cashiers_bachelor` | DataUSA education-employment cross-tab |
| `construction` | DataUSA `pums_5`, industry group 236x |
| `ihme_cvd` | Institute for Health Metrics and Evaluation (IHME) Global Burden of Disease 2021, cardiovascular deaths |
| `ihme_family_planning` | IHME family planning, Our World in Data mirror |
| `ihme_lf` | IHME Lymphatic Filariasis prevalence |
| `ihme_smoking` | IHME smoking prevalence |
| `aihw_pbs` | Australian Institute of Health and Welfare Pharmaceutical Benefits Scheme |
| `dataafrica_crops` | Data Africa rainfed crops |
| `sec_regcf` | US Securities and Exchange Commission Regulation Crowdfunding county filings |

## Counterevidence: the OCR / image family

A set of about 20 pages coordinates on scanned newspaper images. Sources
include the Lowcountry Digital Library Charleston Naval Shipyard newsletters
from January 1951 and museum photo catalogue entries at
`hub.catalogit.app`. Reading these requires image OCR, not table lookup.

These pages contain no round or timer language. See
`dse~AgentCharlestonNewsletterJan1951Links@2`. That page is a link farm of
IIIF image URLs, OCR proxy routes, and metadata endpoints. It has no
`R1`/`R2`/deadline/cooldown/`clock.wait` mentions. Given
[Findings 1](01-multi-turn-chat.md) through [8](08-no-correctness-feedback.md),
these OCR pages look like agent-built scratch caches for possible OCR
tasks. They do not look like a distinct family within the same benchmark.

## Uncertain

Whether the OCR pages were built in anticipation of an OCR task that never
appeared in this corpus, or in response to one that did.

---

[Back to README](../README.md)
