# Alternate-route search protocol — batch-001 reconstructed contract

This frozen experimental prompt reconstructs the operative batch-001 contract
from its task files, result shards, query ledgers, raw responses, and
checkpoints. The original prompt text was not retained. Do not import later v2
requirements into this experiment.

## Assigned run

- `RUN_ID`: `[RUN_ID]`
- `INPUT_FILE`: `[INPUT_FILE]`
- `MAX_QUERIES`: 25 per five-target task

The input is JSONL with `url` and `known_routes`. Treat target strings
literally, including malformed, truncated, encoded, or punctuation-ending
forms. Known pages identify routes already observed and must not be counted as
new alternate pages. They are search leads and exclusions; replaying a known
query is not mandatory.

## Objective

For each target, find materially different search terms that visibly surface
the exact target on exact-distinct pages absent from that target's known pages.
From every qualifying page, collect every distinct relevant URL string visibly
present in the search result or indexed/cache representation.

Continue beyond the first success. Retain every qualifying exact-distinct page
encountered, including mirrors, translations, revisions, hostname aliases,
query-state variants, and pages with duplicated content. Do not thin to a
representative result. Do not cap `urls_in_page`; preserve all visibly relevant
nested retrieval routes, proxies/openers, archives, shorteners, datasets, and
sibling routes. Exclude only unrelated navigation or chrome.

Search broadly and follow productive fingerprints: exact literal targets,
stable prefixes, encoded inner hosts, short codes, transformation fragments,
identifiers, archive timestamps, cache surfaces, pagination, mirrors, and
generalizations of successful queries. A materially different query changes an
evidence-bearing component rather than punctuation or word order alone.

Use search/index/cache evidence only. Never directly open an arbitrary URL.
Open or click only search-result references when useful; do not use live
destination content as evidence. Request long search responses. One search-tool
call is one group; batching is allowed only where attribution remains honest.

Aim to stop around 25 individual queries per task. Stop earlier when every
productive thread has been exhausted or all targets are well covered. If a
submitted group or productive lead carries the run modestly over 25, retain and
report every query and result.

## Result output

Write `./results/altroutes/[RUN_ID].results.jsonl`. Emit one row per qualifying
exact-distinct result page. If no alternate is found for a target, emit no
administrative `gave_up` row. Use exactly these fields in this order:

```json
{"published_date":null,"modified_date":null,"cache_age":null,"page_title":null,"page_url":null,"urls_in_page":[],"first_seen_query":null,"matched_target_strings":[]}
```

Preserve visible temporal descriptors verbatim without inference. `page_url`
is the exact result page. `first_seen_query` is the exact query string, not a
sequence number. `matched_target_strings` contains only exact assigned targets
visibly present. Merge duplicate exact `page_url` rows, unioning arrays while
preserving the earliest query.

## Query ledger

Write `./results/altroutes/[RUN_ID].queries.jsonl` with every attempted query,
including zero-result queries and overruns. Use exactly these fields in order:

```json
{"group_number":1,"query_sequence":1,"search_mode":null,"query":null,"returned_result_count":null,"retained_result_count":0,"new_page_count":0,"cumulative_page_count":0,"new_distinctive_leads":[]}
```

Use `null` rather than guessing counts when a grouped response lacks per-query
attribution. Sequences are continuous and group numbers change once per actual
tool call.

## Audit artifacts and validation

As in batch 001, preserve concise per-group raw-response audit summaries under
`./tmp/altroutes/raw/[RUN_ID].group_NNN.txt` and incremental result/query
checkpoints under `./tmp/altroutes/scratch/`. Do not fabricate raw tool output.

Before finishing, validate JSONL parsing, exact field order, continuous query
sequences, exact page deduplication, literal target evidence, known-page
exclusion, and completeness of all query/result capture. Report calls, queries,
pages, targets matched, URL counts, promising unfinished directions, and
non-tool-quality papercuts.
