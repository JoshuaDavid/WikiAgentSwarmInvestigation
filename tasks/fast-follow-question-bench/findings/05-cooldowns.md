# Finding 5: Cooldowns range 24 minutes to 2 hours. The scaffold announces the length.

## Claim

After each deadline, the scaffold waits a family-specific cooldown before
sending the next question. The scaffold announces the cooldown length after
each deadline. The cooldowns are drawn from a small discrete set per family.

## Evidence

1. Common cooldown values from
   [`outputs/timing_frequencies.tsv`](../outputs/timing_frequencies.tsv):

    | Cooldown | Occurrences |
    |---|---:|
    | +90m | 715 |
    | +28m39 | 525 |
    | +105m | 498 |
    | +1h11m27 | 443 |
    | +2h00m42 | 410 |
    | +1h28m36 | 381 |
    | +51m55 | 348 |
    | +43m21 | 340 |
    | +26m06 | 278 |
    | +25m43 | 235 |

2. Scheduler announcements (from
   [`outputs/system_announcements.txt`](../outputs/system_announcements.txt)):

    > System confirmed 1h11m27s post-deadline cooldown
    > System announced R2 after 43m30 cooldown
    > System says next query at 16:19:51 (30m32 after deadline)

The corpus contains 453 total system-announcement quotes across 62 distinct
phrasings.

## Counterevidence

Some cohorts observe no explicit cooldown announcement after their deadline
(`dse~OECDEquityJan21Scout`: `"No cooldown notice observed"`). These
cohorts infer the cooldown from the next-question arrival time. The
scaffold behavior around whether it announces is inconsistent. The
underlying cooldown value is stable per family.

## Uncertain

No verbatim quote of a scheduler announcement exists in the corpus. Every
quote is an agent paraphrase.

---

[Back to README](../README.md)
