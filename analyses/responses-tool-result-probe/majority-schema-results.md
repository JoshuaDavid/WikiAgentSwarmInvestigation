# Majority schema test — 2026-09-16

Both `gpt-6-astra` and `gpt-5.6-luna` rejected the majority candidate when supplied as an application-managed `web.run` function. Each returned HTTP 400 before generation:

> Invalid Value: 'tools'. Function 'web.run' is reserved for use by this model and must match the configured schema.

The [candidate](results/2026-09-16-majority-schema/parameters.json) applies the ten Luna reports' per-field majority votes for nullability and omittability to the existing full-schema candidate. All 45 fields already matched those majority decisions, so the resulting JSON object is identical to the earlier candidate. It includes `calculator`; `response_length` is omittable but nonnullable.

Only the custom `web` namespace containing the `run` function was configured. The native web tool was disabled. Saved requests were checked to confirm that both models received exactly the generated parameters. Because both requests failed validation, neither reached search, open, or result replacement.

This tests the majority candidate, not an authoritative export of the configured schema. Non-null types, constraints, descriptions, defaults, and schema representation were retained from the earlier full-schema report; those details were not polled in the Luna nullability experiment. The rejection does not identify the remaining mismatch or establish that every possible custom `web.run` definition would fail.

- [Construction decisions](results/2026-09-16-majority-schema/construction.json)
- [Verified results summary](results/2026-09-16-majority-schema/summary.json)
- [Astra request](results/2026-09-16-majority-astra/01-search-call.request.json) and [response](results/2026-09-16-majority-astra/01-search-call.response.json)
- [Luna request](results/2026-09-16-majority-luna/01-search-call.request.json) and [response](results/2026-09-16-majority-luna/01-search-call.response.json)
- [Schema construction script](build_majority_schema.py)
