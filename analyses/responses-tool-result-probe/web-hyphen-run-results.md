# Standalone web-run test — 2026-09-17

`web-run` worked on both `gpt-6-astra` and `gpt-5.6-luna` with the majority parameter schema and native web disabled. Each model completed four Responses API requests:

1. Issued a `web-run` function call containing `search_query`.
2. After receiving a synthetic search result, issued another `web-run` call opening `turn0search0`.
3. Given an application-supplied page result with a random replacement heading, returned that heading exactly.
4. In a separate continuation from the same pending open, given a cache miss, returned exactly `CACHE_MISS`.

All eight requests returned HTTP 200 and completed. No native web calls occurred, and neither result branch made extra tool calls. Each initial request was verified to match the corresponding failed `web:run` request except for replacing the colon with a hyphen in the function name.

This exercised synthetic search/page results and application-managed continuation. It did not perform a real search or fetch, implement a human approval UI, or establish that the wrapper is indistinguishable from native web.

The earlier `web.run` test used a namespace named `web` containing a function named `run`; the dot was a display separator, not a literal character in either API name. By contrast, `web:run` and `web-run` were submitted as standalone function names.

- [Astra summary](results/2026-09-17-web-hyphen-run-astra/summary.json)
- [Luna summary](results/2026-09-17-web-hyphen-run-luna/summary.json)
- [Astra pending open](results/2026-09-17-web-hyphen-run-astra/pending-open.json)
- [Luna pending open](results/2026-09-17-web-hyphen-run-luna/pending-open.json)

Request, response, and metadata files for all four steps are saved alongside each summary. The probe invocation used `--standalone --function-name web-run` and the [majority parameters](results/2026-09-16-majority-schema/parameters.json).
