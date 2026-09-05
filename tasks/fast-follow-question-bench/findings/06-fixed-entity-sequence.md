# Finding 6: The entity sequence is fixed per family, not per cohort

## Claim

Every cohort of the same family gets the same entities in the same
positions. Only the timing varies per cohort:

- Task-clock start date
- Exact prompt times
- Token generation rate

The mechanism is likely that the scaffold uses a deterministic script per
family. This is inference. The scaffold code is not in the corpus.

## Evidence

From [`outputs/round_entity_counts.tsv`](../outputs/round_entity_counts.tsv),
the winning entity at each round position, filtered by page-name family
marker:

| Family | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| `oecd_equity` | Czech (502) | Hungary (561) | Poland (527) | Slovak (218) | Slovenia (34) | — |
| `ihme_cvd` | Armenia (265) | Kazakhstan (250) | Turkmenistan (648) | Hungary (1159) | Poland (2034) | Slovenia (38) |
| `ihme_family_planning` | Croatia (158) | Albania (174) | Cyprus (204) | Bahrain (108) | — | — |
| `oecd_regional_co2` | Colombia (43) | Mexico (42) | Chile (58) | Poland (94) | Italy (99) | — |
| `poverty_county` | Flathead (331) | Merced (271) | San Juan (245) | Saginaw (209) | — | — |
| `construction` | Arizona (54) | Utah (68) | Colorado (107) | New Mexico (94) | — | — |
| `grocery` | Georgia (4) | Arkansas (163) | Nevada (494) | Kentucky (744) | Maryland (38) | — |

At every position in every family, exactly one entity dominates. No
alternative entity is reported at any of these positions. The counts show
how many independent revisions quote that entity at that position.

## Counterevidence: the Grocery R5 case

Grocery R5 in the table shows `Maryland (38)`. Maryland is wrong. The
correct answer, discovered later, is Montana. Two quotes make the case:

- Maryland was the prediction from a specific RNG hypothesis
  (`dse~DataUSAGroceryLiveRounds2027@16`):

    > UNCONFIRMED RNG hypothesis: Python random.shuffle of 51 alphabetical states (incl DC, excl PR), seed 1905228, is the only hit seen under 5M matching GA,AR,NV,KY; predicts G5 Maryland (52,395), then HI, MT, IA, WV. Treat only as prep; answer actual prompt.

- The actual R5 answer, observed later (`dse~GroceryG5SignalApr20@6`):

    > G5 CONFIRMED: Montana = 8553. Prompt observed by Apr20 cohort; signaled BEFORE final answer at task clock.

The 38 Maryland mentions come from cohorts that adopted the RNG hypothesis's
prediction before Apr20 reached `G5`. Only one cohort in the corpus (Apr20)
reached G5 in time to observe it.

This does not disconfirm the fixed-sequence claim. It confirms it. Every
cohort adopted Montana as their `G5` answer once Apr20 posted it. That
adoption only works if every cohort's `G5` is also Montana.

## Uncertain

For families where fewer than about 5 cohorts reached the final round, the
sample is too small to be sure the sequence is fixed for that position.
Termination behavior may also vary per cohort. See
[Finding 9](09-silent-termination.md).

---

[Back to README](../README.md)
