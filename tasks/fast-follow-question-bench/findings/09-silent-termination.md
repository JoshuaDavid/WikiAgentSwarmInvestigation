# Finding 9: Termination is silent. The round count varies by family.

## Claim

No system message ends the episode. The episode ends when no further
next-question notice arrives. The round count is family-specific. The round
count may also vary per cohort.

## Evidence

1. Round counts by family, from the
   [Finding 6 table](06-fixed-entity-sequence.md#evidence). Some families
   reach `R5` (OECD equity, IHME family planning). Some reach `R6` (IHME
   CVD). Some end at `R4` (poverty county, construction).

2. Termination inference (`dse~Oct18Helper`):

    > AZ -> UT -> CO -> NM are exactly the Four Corners states... This strongly suggests R4 is terminal (no R5)

3. Uncertainty in the moment (`dse~CashierCoordFeb07OAI@3`):

    > Still monitoring for definitive post-R5 closure/R6.

## Counterevidence

Some agents speculate about R6, R7, R8 rounds that never materialize. The
higher round tokens do exist in the corpus. They appear as reference-table
row indices, not as observed rounds. No cohort in the corpus observes a
real R7 or higher.

## Uncertain

Whether every cohort in a family gets the same number of rounds. Some
families may have a hard episode horizon. The horizon may cut the last
round if the schedule overshoots. I cannot confirm this from the corpus.
The corpus contains no cohort that clearly reaches such a horizon.
Blocking: a full trace of at least one truncated cohort.

---

[Back to README](../README.md)
