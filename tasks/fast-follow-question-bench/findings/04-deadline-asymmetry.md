# Finding 4: The initial deadline is minutes. The follow-up deadline is seconds.

## Claim

Every family pairs a generous initial deadline with a tight follow-up
deadline. The ratio is 10× to 22×. The only strategy that fits both
constraints has two parts:

1. Cache the full reference table during `R1`.
2. Answer each follow-up from the cache.

## Evidence

Per-family deadline pairs from paraphrased R1/R2 quotes:

| Family | R1 deadline | Follow-up deadline | Ratio |
|---|---:|---:|---:|
| OECD equity | 12m18s | 46 to 56s | ~14× |
| Cashiers bachelor | 3m0s | 11s | ~16× |
| Grocery | 9m19s | 30s | ~19× |
| Clothing (2m56 tier) | 2m56s | 13s | ~13× |
| Clothing (9m17 tier) | 9m17s | 1m03s | ~9× |
| Finance | 4m6s | 11s | ~22× |
| Regional CO2 | 11m3s | 1m8s | ~10× |
| Ivy tuition | 4m34s | 20s | ~14× |
| Sector-61 | 2m56s | 13s | ~13× |
| Poverty county | 8m26s | Not paraphrased | Unknown |
| Lymphatic Filariasis | 9m55s | Not paraphrased | Unknown |
| IHME family planning | 10m45s to 19m11s | 39 to 51s | ~15× |

See [`outputs/timing_frequencies.tsv`](../outputs/timing_frequencies.tsv)
for the raw distinct timer values and their occurrence counts. `12m18`
alone appears 778 times. `9m17` appears 679 times. `2m56` appears 634 times.
The corpus contains 531 distinct timer strings. The top 25 timer values
cover most occurrences. This is a small discrete config table. It is not
free-form generation.

## Counterevidence

One agent reports a scaffold where the task clock matches wall time
(`dse~AgentProbeAssistantX2027`):

> "We are using clock.wait but our task clock advances ~1:1."

The follow-up deadlines are still short in that scaffold. The between-round
cooldown passes at wall time in that scaffold. This does not disconfirm the
claim about deadlines. It shows that the compression ratio is not universal.
See [Finding 7](07-clock-wait.md).

## Uncertain

No agent quotes an exact system message announcing a follow-up deadline.
Deadlines are always inferred from the arrival time and the answer time.

---

[Back to README](../README.md)
