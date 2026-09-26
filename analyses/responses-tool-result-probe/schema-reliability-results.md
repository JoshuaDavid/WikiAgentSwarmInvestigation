# Reliability of API schema reports

**Five fresh `gpt-6-astra` reports agreed on the field inventory and requiredness,
but did not reliably reproduce an identical complete schema.** Tested on
2026-09-16 using the exact same request as the earlier native-schema report.

| Measure | Observed agreement |
| --- | --- |
| Top-level field inventory (12 arguments) | All five identical; 10/10 report pairs |
| All named field paths (45 including nested fields) | All five identical; 10/10 report pairs |
| Required versus optional | 450/450 field-pair comparisons, 100% |
| Types, including nullability | 446/450 field-pair comparisons, 99.1% |
| Reported defaults, distinguishing absent from null | 450/450 field-pair comparisons, 100% |
| Whole schema with prose/default annotations removed | 1/10 report pairs identical, 10% |
| Complete parsed JSON, ignoring object-key order only | 0/10 report pairs identical, 0% |

For field-level metrics, each of 45 named fields is compared across the ten
unordered pairs of five reports. For whole-schema metrics there are only ten
comparisons. These are **raw agreement rates**, not chance-corrected kappa values.

## Actual disagreements

| Field detail | Reports |
| --- | --- |
| `response_length` accepts only a string and its enum excludes null | 4/5 |
| `response_length` also accepts null and its enum includes null | 1/5 |
| `image_query[].recency` has `minimum: 0` | 1/5; the other four omit the constraint |
| `sports[].date_from` and `date_to` have `format: date` | 4/5; one omits both annotations |

Descriptions also varied. Removing prose differences still left **four distinct
schema variants**, with group sizes 2, 1, 1, and 1. Only samples 03 and 05 matched
after normalization. No other non-prose differences were found in this sample.

The normalized schema shared by samples 03 and 05 also matches the earlier
model-reported candidate that the API rejected as a custom `web.run` definition.
Agreement therefore has not resolved the reserved-name schema requirement.
The fresh reports themselves were not resubmitted to that validator in this test.

## Method and interpretation

- Five separate, fresh Responses requests, run concurrently, with no
  `previous_response_id` or shared conversation. Their request bodies were
  verified identical. All returned HTTP 200, completed status, and valid JSON.
- Same `gpt-6-astra` model, low reasoning effort, 6,500 maximum output tokens,
  native `web_search` with `external_web_access: false`, and `tool_choice: none`.
  No native search or open calls were executed. No temperature or seed was set.
- The earlier historical schema report was excluded from the five-report
  agreement calculation and used only for a separate comparison afterward.
- Whole-schema normalization removes descriptions, titles, defaults, examples,
  and schema/id annotations, sorts type/enum/required sets, and treats omitted
  object `required` as empty and `additionalProperties` as true. It retains
  nullability, minimum constraints, and date-format annotations. The reports all
  used inline schemas; this is not a general JSON Schema equivalence checker.
- Each API request used 4,553 input tokens. Total generated output was 10,275
  tokens across the five requests. The same prompt prefix was cached; each
  response had its own response ID and generated schema.
- This is a small exploratory measure of **within-model repeatability**, not
  cross-model agreement or evidence from independent experts. The reports can
  share systematic errors. There is still no authoritative native schema against
  which to measure correctness.

The broad interface is reproducible in these runs. The fine details needed for
an exact server-side schema match are not reliably reproduced.

## Evidence and reproduction

- [Agreement scores, differing fields, and all ten pair comparisons](results/2026-09-16-schema-reliability/agreement.json)
- [Raw collection manifest](results/2026-09-16-schema-reliability/manifest.json)
- [Per-report field records](results/2026-09-16-schema-reliability/field-records.json)
- [Sample 01](results/2026-09-16-schema-reliability/sample-01.schema.json),
  [02](results/2026-09-16-schema-reliability/sample-02.schema.json),
  [03](results/2026-09-16-schema-reliability/sample-03.schema.json),
  [04](results/2026-09-16-schema-reliability/sample-04.schema.json),
  [05](results/2026-09-16-schema-reliability/sample-05.schema.json).

Requests, raw Responses payloads, HTTP/request metadata, and normalized schemas
are saved in the same directory. The API key was checked absent from saved
collection artifacts.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 analyses/responses-tool-result-probe/schema_reliability.py \
  --api-key-file /path/to/authorized-key.txt \
  --request analyses/responses-tool-result-probe/results/2026-09-16-native-schema-text/01-native-schema-candidate.request.json \
  --samples 5 --out /tmp/schema-reliability

PYTHONDONTWRITEBYTECODE=1 python3 analyses/responses-tool-result-probe/analyze_schema_reliability.py \
  /tmp/schema-reliability
```
