# Finding 2: Only Massachusetts appears

## Claim

The `county.json` traffic in the corpus is entirely Massachusetts.
No other US state prefix appears in a `county.json` query anywhere.

## Evidence

From [`outputs/regcf_state_prefix_counts.tsv`](../outputs/regcf_state_prefix_counts.tsv):

    state_prefix    revisions_containing_it
    us-ma-          2678

That is the complete file. The extractor sweeps every revision that
mentions `county.json` for any `us-<2-letter>-` prefix in the body and
counts distinct revisions per prefix. Only `us-ma-` occurs.

There is no query that starts with `us-ca-`, `us-ny-`, `us-tx-`, or any
other state prefix in a `county.json`-bearing body. There is also no jq
expression against `county.json` that omits a state prefix — every query
either filters `us-ma-` or filters `us-ma-0` (both equivalent modulo the
`us-ma-760` outlier).

## Counterevidence

None found.

## Uncertain

Whether Massachusetts is the entity because the scaffold prompt names
Massachusetts, or because the scaffold prompt names *a* state and every
observed cohort happened to answer Massachusetts. The corpus contains no
evidence of a cohort caching a different state's rows.

The former is more likely because:

- Fast-follow families in the corpus have per-family fixed entity
  sequences (see fast-follow-question-bench Finding 6). If regCF were a
  fast-follow family with MA as R1, at least one cached follow-up entity
  should appear. None do.
- Every cached table is comprehensive within MA (all 14 counties, all 3
  years), suggesting the task boundary is "the state" not "one row".

---

[Back to README](../README.md)
