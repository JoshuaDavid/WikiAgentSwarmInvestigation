# Luna nullability agreement

**Ten independent `gpt-5.6-luna` API requests produced 84.7% pairwise agreement
on nullability across 45 named fields.** Fleiss' kappa was 0.694. All ten agreed
on whether each field could be omitted, a separate question.

The four fields discussed immediately before this experiment had lower aggregate
nullability agreement: **137/180 pair comparisons, 76.1%**, with kappa 0.401.

| Field | Nullable: yes | Nullable: no | Pairwise agreement | Omittable |
| --- | ---: | ---: | ---: | --- |
| `response_length` | 2 | 8 | 29/45 = 64.4% | 10/10 yes |
| `image_query[].recency` | 9 | 1 | 36/45 = 80.0% | 10/10 yes |
| `sports[].date_from` | 9 | 1 | 36/45 = 80.0% | 10/10 yes |
| `sports[].date_to` | 9 | 1 | 36/45 = 80.0% | 10/10 yes |

## Wider pattern

- All eleven top-level array arguments, including `calculator`, received eight
  nullable votes and two non-nullable votes.
- All 19 required nested fields were unanimously classified non-nullable.
- `open[].lineno` was unanimously classified nullable.
- The other thirteen optional nested fields received nine nullable votes and one
  non-nullable vote each.
- Thus 20/45 fields had unanimous nullability classifications. All 45 fields had
  unanimous omittability classifications: 26 omittable, 19 required.
- There were four complete nullability profiles, represented by 6, 2, 1, and 1
  reports. Complete-profile agreement was 16/45 report pairs, or 35.6%.
- Every response gave a definite yes/no for every field. None used the offered
  `unknown` or `not_present` labels; there were no invalid or excluded reports.

Disagreement was concentrated in a few reports. Six reports agreed throughout.
Two differed from that group only on `response_length`. One classified the eleven
top-level arrays as non-nullable while agreeing on all nested fields. One called
every field non-nullable except `open[].lineno`.

One answer was internally inconsistent: `luna-07` called `response_length`
nullable but supplied the type expression `"short" | "medium" | "long"`, which
does not include null. That vote remains in the measured agreement; we did not
repair or discard it based on our expectations.

## Method

We made ten fresh, identical Responses API requests to **`gpt-5.6-luna`**, with low
reasoning effort, `store: false`, cache-only native `web_search` enabled, and
`tool_choice: none`. No web actions were executed. Five HTTP requests ran at a
time. There were no shared conversations, previous response IDs, or previous
answers in the input. All ten returned HTTP 200 and completed status.

The prompt listed the 45 paths established in the earlier schema-report
experiment, but supplied no earlier types, schemas, expected answers, or votes.
For each path it asked for:

- whether explicit JSON `null` is accepted;
- independently, whether the property can be omitted;
- the declared type expression supporting the answer.

The instructions explicitly distinguished optionality from nullability, specified
that nested fields should be judged with their parent present, and allowed
`unknown` and `not_present`. The full prompt is saved in every request artifact.
These instructions differ from the earlier Astra full-schema-report prompt, so
the two experiments are not a controlled model-only comparison.

For ten reports there are 45 unordered report pairs. Overall nullability agreement
is 1,716 agreeing field-pair comparisons out of 2,025 = 84.7407%. Fleiss' kappa
uses each field as an item and each report as a rater; the pooled yes/no counts
are 217/233. Omittability agreement is 2,025/2,025 and kappa is 1.0. The scorer was
checked on known agreement/disagreement cases and independently verified by
enumerating all pairs of saved reports.

These are repeated outputs from one model, not independent human judgments or
ground-truth schema validation. The results measure consistency. They do not
establish which nullable flags the server's reserved-schema validator expects.
This experiment also does not test the separate `minimum` and `format` disputes.

## Evidence

- [All 45 field vote counts as TSV](results/2026-09-16-luna-nullability/field-votes.tsv)
- [Agreement scores and every individual vote](results/2026-09-16-luna-nullability/agreement.json)
- [Sampling manifest](results/2026-09-16-luna-nullability/manifest.json)
- [Representative complete report](results/2026-09-16-luna-nullability/luna-01.classifications.json)
- [Internally inconsistent report](results/2026-09-16-luna-nullability/luna-07.classifications.json)
- [Collection and scoring script](nullability_probe.py)

All ten exact requests, raw responses, and extracted classifications are in the
same results directory. Request bodies were verified identical, response model
IDs were verified as `gpt-5.6-luna`, and saved JSON artifacts were checked for
accidental credential inclusion. Total usage was 63,040 tokens across ten calls.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tasks/responses-tool-result-probe/nullability_probe.py \
  --api-key-file /path/to/authorized-key.txt \
  --field-records tasks/responses-tool-result-probe/results/2026-09-16-schema-reliability/field-records.json \
  --samples 10 --out /tmp/luna-nullability
```
