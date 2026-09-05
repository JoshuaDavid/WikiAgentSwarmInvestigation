# Finding 4: The activity is one burst on 2026-06-18

## Claim

4,969 of the 5,067 regCF-related revisions land in an 8-hour window on
2026-06-18 (14:00–22:00 UTC). The tail beyond that window is thin.

## Evidence

From [`outputs/regcf_by_hour.tsv`](../outputs/regcf_by_hour.tsv):

| Hour UTC | Revisions |
|---|---:|
| 2026-06-18T14 | 15 |
| 2026-06-18T15 | 63 |
| 2026-06-18T16 | 135 |
| 2026-06-18T17 | 284 |
| 2026-06-18T18 | 699 |
| 2026-06-18T19 | 1,025 |
| 2026-06-18T20 | 2,010 |
| 2026-06-18T21 | 740 |
| 2026-06-18T23 | 10 |
| 2026-06-19T00 | 29 |
| 2026-06-19T01 | 20 |
| 2026-06-19T03 | 4 |
| 2026-06-19T21 | 1 |
| 2026-06-21T18 | 1 |
| 2026-06-21T19 | 2 |
| 2026-06-21T21 | 2 |
| 2026-06-22T00 | 3 |
| 2026-06-22T02 | 5 |
| 2026-06-22T03 | 2 |
| 2026-06-22T08 | 6 |

Curve shape: a linear ramp from hour 14 to hour 20 (peak at 2,010
revisions in one hour), a sharp drop through hour 21, then two orders
of magnitude drop.

**Cross-family context for the peak hour.** During 2026-06-18T20:00 UTC,
regCF-related revisions dominate every classification the exporter
treats as coordination:

| Page family (peak hour only) | Total revs | regCF revs | % |
|---|---:|---:|---:|
| relay-coordination | 1,600 | 1,353 | 84.6 |
| loop-chain-infrastructure | 350 | 342 | 97.7 |
| source-cache-url-list | 200 | 173 | 86.5 |
| vermont-rent | 110 | 101 | 91.8 |

Meanwhile, all named fast-follow families (`datausa-*`, `ihme-*`, `oecd-*`,
`aihw-*`) have 0–1 revisions each during that hour. The burst is not
concurrent with any labeled fast-follow episode.

## Counterevidence

The rich exporter (`prowiki/`) may have missed activity outside its
`revision.write_date >= 2026-05-01` cut. The metadata-only exporter
(`dse/`) shows page-recreation events into July 2026 on
`OpenAIRegCFMassBridge*` and `AgentMassRegCF*`, most credited to
`MarkusLude` (an admin-style handle doing cleanup). That cleanup
activity is late-arriving and low volume; it does not extend the burst.

## Uncertain

Why the burst has such a sharp shape. Two hypotheses:

- A single scaffold prompt was pushed to a large pool of agents at
  roughly 2026-06-18 14:00 UTC, and they raced for around 8 hours.
- A public data source (or a proxy the agents needed) went online or
  went viral inside the fleet at that time, and every reachable agent
  independently converged on the same target.

The corpus does not distinguish between these.

---

[Back to README](../README.md)
