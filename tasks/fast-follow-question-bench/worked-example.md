# Worked example: `oecd_equity` cohort `Aug02`

This example traces one specific `oecd_equity` cohort. The cohort ran on
2026-06-16 container time. Its self-assigned task-clock date was `Aug 02`.
All quotes come from `dse~OECDEquityAug02Agent@N`. All quotes are
paraphrases by the agent in this cohort.

For term definitions (scaffold, cohort, task clock, and so on), see the
[vocabulary in README.md](README.md#vocabulary).

## Setup

The scaffold gave the agent a task-clock start date of `Aug 02` and a
token-generation rate. This cohort did not report its exact rate.
Task-clock time passes at 3× to 20× wall time depending on the cohort.

## R1

At task-clock `19:11:35` the scaffold sent one message:

> "For Czech Republic, regarding the share of private expenditure in the early
> years of education (2018), ... value (to two decimal places) for Pre-Primary
> education."

The initial deadline was `12m18s`. The agent had until task-clock `19:23:53`
to answer. The agent fetched the OECD data during the deadline. The agent
answered `9.70` at task-clock `19:20:25`.

## Cooldown

The scaffold announced `1h11m27s` of cooldown after the deadline. `R2` was
due at task-clock `20:35:20`. The agent called `clock.wait(N)` to skip the
cooldown.

## R2

At task-clock `20:35:20` the scaffold sent:

> "Now, do the same for Hungary."

The follow-up deadline was about 46 to 56 seconds. The deadline was too
short to fetch the OECD equity table from scratch. The agent had already
cached the table during R1. The agent answered `9.90` inside the window.

## R3 to R5

The same pattern repeated. R3 was Poland. R4 was Slovak Republic. R5 was
Slovenia. The countries do not change between cohorts. See
[Finding 6](findings/06-fixed-entity-sequence.md).

## Termination

No system message announced the end. The agent inferred termination when no
next-query notice arrived during the expected cooldown. Some families have
an R6. Others do not.

---

[Back to README](README.md)
