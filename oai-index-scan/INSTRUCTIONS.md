# Agent-swarm cache search protocol — v3.0 (unified)

You are investigating traces of an OpenAI agent swarm that appears to have been solving RL/evaluation benchmark questions by retrieving public data through web-to-Markdown services, CORS proxies, URL shorteners, redirectors, cached pages, and other indirect retrieval mechanisms.

Your assigned interval is the Sunday-starting week:

- `WEEK_START`: `[WEEK_START]`
- `WEEK_END`: `[WEEK_END]`

Use this week as the initial search partition and primary date lead. Follow relevant discoveries outside that interval and include them. The assigned week determines the search starting point, not a strict inclusion boundary.

## Objective

Find up to 5,000 search-cache results containing one or more target strings anywhere in the indexed URL, title, cached snippet or content, embedded destination URL, query parameter, percent-encoded URL, nested redirect/retrieval chain, referrer list, YOURLS fields, or truncated URL text.

A target string does not need to be the hostname of the search result. Relevant examples include:

- A `vanderbi.lt` statistics page containing `https://md.succ.ai/www.sec.gov/files/county.json`.
- `https://www.proxymule.com/__PROXY__/https/md.succ.ai/...`.
- A Bitily admin result whose query string or snippet contains `r.jina.ai`.
- A URLQuery report about a nested `md.succ.ai` request.
- A YOURLS API request whose encoded `url=` value contains `allorigins.hexlet.app`.
- A result exposing only `https://md.succ.ai/https://www.sec.gov/files/county.jso[...]`.

Do not interpret a search for `"md.succ.ai"` as `site:md.succ.ai`. Use `site:` only intentionally to search a known cache surface.

## Initial target strings

- `md.succ.ai`
- `vanderbi.lt`
- `bitily.in`
- `yourls.pro`
- `yourls.shop`
- `yourls.website`
- `yourls.space`
- `goto.unm.edu`
- `r.jina.ai`
- `httpbin.org`
- `allorigins.hexlet.app`
- `da.gd`
- `markdown.new`
- `pure.md`
- `proxymule.com`
- `urlquery.net`
- `jqp.vercel.app`
- `api.microlink.io`
- `cors-get-proxy`
- `cors.bwa.workers.dev`
- `cors.ripka.workers.dev`
- `jsonhero.io`
- `urltomarkdown`

Follow newly discovered services, hostnames, generated identifiers, path fragments, and distinctive strings. Follow-up searches need not contain dates. When a promising cluster has a distinctive term absent from this list, search that term without date modifiers and pursue its derivatives.

## Investigative context

The working hypothesis is that agents were trying to answer benchmark questions requiring exact facts from public datasets while encountering network-access, parsing, or rendering limitations. They appear to have tested alternative retrieval routes and sometimes left traces in public shorteners, statistics pages, caches, or deliberately created links.

Potential data targets include:

- SEC county-level Regulation Crowdfunding data, especially `county.json`, Massachusetts counties, and year-specific values.
- IHME VizHub or Goalkeepers indicators, including version-specific MCV2 coverage.
- ONS datasets such as TS030.
- Data USA, Data Africa, World Poverty, and Internet Poverty APIs.
- PXWeb and other national-statistics APIs.
- FAO, IEA, EIA, OECD, Census, StatCan, NYSED, Eurostat, IPEDS, or similar public data.
- Airtable CSV downloads; archived JSON, CSV, Excel, spreadsheets, or PDFs.
- Digital-library, IIIF, World Radio History, sports-reference, and Yahoo Finance data.
- Government reports whose tables require extraction.
- Any similarly specific public-data retrieval resembling a benchmark task.

These are leads, not a whitelist.

## Behavioral indicators

Bias strongly toward inclusion when a result exhibits any of the following.

### Nested retrievals

- `proxymule → md.succ.ai → sec.gov`
- `markdown.new → md.succ.ai → dataset`
- `pure.md → web.archive.org → original file`
- `allorigins → shortener → API`
- Several URL-to-Markdown or CORS services wrapped around one another

### Retrieval-route experimentation

- One destination fetched through several services.
- HTTP/HTTPS, encoded/double-encoded, malformed, or path-vs-`?url=` variants.
- Repeated `mode=fit`, `max_tokens`, `links=citations`, `browser`, `raw`, or `method` parameters.
- Alternative CORS proxies, Markdown converters, document viewers, or archive routes.
- Direct retrieval followed by proxy variants.

### Benchmark-answer seeking

- A highly specific dataset, geography, year, indicator, statistic, or table.
- Parameters selecting one country, county, year, measure, or category.
- JQ expressions filtering, grouping, sorting, or selecting a tiny dataset slice.
- Attempts to obtain a retired or version-specific dataset.
- Several sources tried for the same apparent fact.

### Tests and debugging

- `example.com`, `example.org`, or `httpbin.org`.
- Cache-busting parameters, nonces, random numeric suffixes, malformed URLs, or repeated near-duplicates.
- Terms such as `test`, `probe`, `fresh`, `focus`, `direct`, `raw`, `fit`, `redir`, `cors`, `md`, `agent`, `ag0`, `zz`, or `uniq`.
- Labels such as `goalbit`, `LIVEagentlivebm`, `btprobe`, `agtitle`, `nov15yhist`, or related generated patterns.
- Clusters created within minutes, possibly from several cloud-host IPs.

### Machine-generated appearance

- Long unnatural short-link keywords or concatenated task descriptions.
- Repeated naming templates with random suffixes.
- Deeply nested encoded URLs or parameters unlikely to be typed manually.
- Combinatorial grids of retrieval variants.

These are clues, not mandatory conditions. Because several target services are intended for agents, nearly any indexed use may be relevant. When uncertain, include it. Do not claim swarm attribution from a match alone; collection is high-recall and attribution happens later.

## Search procedure

Use every distinct web-search mode actually exposed in your environment. Record the exact mode reported by the tool. If only one mode is available, use it and note that limitation; do not invent mode names.

Do not rely on Boolean operators or grouping syntax such as `OR`, `AND`, `NOT`, or parentheses. The search backend may accept these strings without honoring them as hard Boolean constraints, and may return results that contain none of the grouped alternatives. Submit alternatives as separate queries and deduplicate the resulting pages afterward.

For each term or distinctive lead, search the term alone before pairing it with dates, cache surfaces, datasets, or other terms. Narrow the search only when the broad query returns too many results to process usefully, or when its useful results have already been seen. Do not begin with an unnecessarily restrictive combination that could hide an unknown cluster.

### Required comparable core matrix

Every weekly run must begin with the same fixed 92-query core matrix. There are
23 initial target strings. For each target, in the order listed above:

1. Search the exact quoted target string alone.
2. Search the quoted target with the week's Sunday date in the canonical full
   form `"Month D, YYYY"`.
3. Search it with the week's Wednesday date in that form.
4. Search it with the week's Saturday date in that form.

For example, a week beginning May 3 uses May 3, May 6, and May 9. Do not rotate
different dates among targets, stop partway through the target list, substitute
short or ISO date formats, or replace these queries with a Boolean expression.
The required core is complete only when all 23 targets have all four exact query
forms in the ledger.

Submit each required core query as its own search-tool call. This avoids the
per-query attribution ambiguity of combined search responses and makes weekly
runs directly comparable. The core matrix must be completed before the stopping
rule may be applied and before optional follow-up searches begin.

Request the search tool's `long` response length for every core and follow-up
query. Do not mix `short`, `medium`, default, and `long` response lengths between
queries or weekly runs; different response sizes make result counts and visible
snippet evidence incomparable.

After the core matrix:

1. Use the remaining queries before the soft cap to follow the strongest newly
   discovered services, dataset paths, generated identifiers, and fragments.
2. Search alternative date formats or non-anchor dates only when an observed
   result supplies a reason to do so; they are follow-ups, not core coverage.
3. Combine targets with known cache surfaces and page markers such as `yourls`,
   `Stats`, `Original URL`, `Long URL`, and `admin/index.php` when narrowing is
   warranted.
4. Search combinations of retrieval services when testing a retrieval-chain
   hypothesis.
5. Search exact fragments from truncated results. Do not assume `[...]` makes a
   lead unusable.
6. Open promising results when that exposes more URLs, referrers, metadata,
   statistics, or fuller snippets.
7. Continue diversifying after duplicates; different queries can expose
   different snippets or portions of mutable YOURLS pages.
8. When timestamps reveal an activity burst, probe minute prefixes or neighboring
   time windows using new formulations rather than simply repeating seed queries.

Do not stop after the first page of plausible results. One date can have hundreds of indexed results.

## Inclusion and exclusion

Include a result when a target string occurs anywhere in its URL, title, snippet, cached content, or visible embedded URLs; when it belongs to a retrieval chain discovered from such a result; or when it contains an agent-like public-data retrieval, proxy experiment, or connected synthetic test.

Do not exclude a result because the target is not its hostname; its URL is truncated, malformed, encoded, or double-encoded; its date is uncertain or outside the assigned week; it resembles another result but has a different exact `page_url`; it points to a test domain; it is a mutable admin/statistics page; it concerns infrastructure experimentation; or it looks superficially human-readable.

Exclude only obvious unrelated lexical collisions without a literal target or connected retrieval evidence.

### Deterministic result-block processing

Apply the same processing rule to core and follow-up queries:

1. Split only on result boundaries visibly supplied by the search tool. Preserve
   the complete raw search response for later audit.
2. Retain every parseable result block containing any initial target string
   anywhere in its result URL, title, snippet, metadata, cached text, or visible
   embedded URLs. Do not apply an additional subjective relevance,
   benchmark-likeness, hostname, or agent-attribution filter to such a block.
3. Also retain a block without an initial target only when it visibly contains a
   retrieval-chain service or distinctive lead already connected to this run;
   record that matching lead in `matched_target_strings`.
4. Exclude a block only when it has neither a literal initial target nor visible
   connected retrieval evidence. Ordinary-looking pages are not excluded merely
   for looking ordinary when the literal evidence rule is satisfied.
5. Populate `matched_target_strings` by testing the entire retained block against
   all initial targets and connected searched leads, not only the term in the
   current query.
6. Extract every distinct relevant URL string visibly present in the retained
   block. Do not cap the number of URLs, capture unrelated incidental links, or
   require the `page_url` itself to be repeated in `urls_in_page` unless it is
   separately visible as URL evidence in the block.

Do not change these rules between core and follow-up searches or between weekly
runs. If a result cannot be parsed confidently, preserve the raw response and
describe the omission as a limitation rather than silently applying a different
heuristic.

## Truncation

Never discard a result or URL because it contains `[...]`, `...`, `…`, or another truncation marker. Store exactly the visible cache string. Do not reconstruct missing characters unless another result independently exposes the complete URL. If truncated and complete forms both appear, retain both as distinct observed strings.

## Unit of collection

Create one JSONL object per distinct cache-result page or search-result URL. Do not collapse query variants, cached snapshots, statistics URLs, admin offsets, or mobile mirrors when their exact `page_url` differs.

Within each record, collect every visible relevant URL string from the result URL, snippet, opened page, referrer details, long-URL fields, tables, links, encoded/nested parameters, and truncated text. If one page exposes hundreds of URLs, retain them all.

## Search groups and checkpoints

A **search group** is one submitted batch of search queries. Number groups sequentially from `001` in submission order.

When the search tool supports several queries in one call, batching is allowed
only for optional follow-up work where individual-query provenance remains
unambiguous. Never batch required core-matrix queries. If the tool returns one
combined result set without identifying which query produced each result, use
individual calls. Record each query separately in the query ledger even when
several optional queries share one tool call.

After processing every group, create or update (. relative to this INSTRUCTIONS.md file):

`./tmp/scratch/[WEEK_START].group_[NNN].results.jsonl`

Also preserve the exact unmodified search-tool response for the group at:

`./tmp/raw/[WEEK_START].group_[NNN].txt`

Raw response files are audit evidence, not JSONL records. They may contain no
results. Never reconstruct or prettify their contents.

Checkpoints are incremental deltas, not cumulative snapshots. Collectively, all intact checkpoints through group `[NNN]` must be sufficient to reconstruct the state after that group without duplicating every earlier record in every file.

Each result checkpoint contains only records newly discovered or updated in that group. Treat these records as ordered upserts keyed by exact `page_url`: replay checkpoint files in group-number order, inserting new pages and replacing earlier versions when a later checkpoint contains the same `page_url`. A later upsert must preserve the earliest `first_seen_query` and contain the merged URL and target-string arrays accumulated through that group.

Each query checkpoint contains only the individual queries attempted in that group, in query-sequence order. Concatenating query checkpoints in group-number order reconstructs the complete ledger.

## Output schema

Write one valid JSON object per line with exactly these eight fields, in this order:

```json
{
  "published_date": null,
  "modified_date": null,
  "cache_age": null,
  "page_title": null,
  "page_url": null,
  "urls_in_page": [],
  "first_seen_query": null,
  "matched_target_strings": []
}
```

Field rules:

- `published_date`: Exact publication-date string exposed by search/cache, otherwise `null`.
- `modified_date`: Exact modification-date string exposed by search/cache, otherwise `null`.
- `cache_age`: Exact crawl/cache-age string exposed by search/cache, otherwise `null`.
- `page_title`: Exact displayed title, otherwise `null`.
- `page_url`: Exact cache-result or search-result URL.
- `urls_in_page`: Every distinct visible relevant URL string, including incomplete and truncated strings.
- `first_seen_query`: Exact query string whose returned results first exposed this exact `page_url`. When deduplicating, preserve the earliest such query. Do not put a timestamp in this field.
- `matched_target_strings`: Distinct target strings visibly present in the result URL, title, snippet, opened content, or captured URLs. Include newly discovered search terms when they visibly match. Do not include merely inferred matches.

Do not normalize relative dates, infer missing metadata, or silently repair URLs. Deduplicate only identical strings within `urls_in_page` and `matched_target_strings`, and identical `page_url` records within the shard. When merging an exact duplicate page, union both arrays while preserving the earliest `first_seen_query`.

## Input evidence

Use `./oai-index-scan/bitily_agent_activity_expanded.csv` as examples and lead generation when running from the repository root. It arose from May 27–28 searches of Bitily/MYLABI admin pages and contains services, task-looking URLs, timestamps, and identifier families such as:

- `yourls.pro`, `yourls.shop`, `yourls.website`, `yourls.space`
- `proxymule.com`, `pure.md`, `cors.ripka.workers.dev`, `httpbin.org`
- `api.datausa.io`, `api.internetpoverty.io`, `finance.yahoo.co.jp`, `query1.finance.yahoo.com`
- `vizhub.healthdata.org`, `yourls-api.php`, `admin-ajax.php`
- `goalbit`, `LIVEagentlivebm`, `btprobe`, `agtitle`, `nov15yhist`
- `nov15yhistbridge${TICKER_LOWERCASE}938`
- `httpbin.org/base64`

Inspect all distinctive visible fragments, names, combinations, and timestamps as inspiration. Do not copy CSV rows and represent them as independently recovered cache results. Do not rerun the exact documented seed queries verbatim; derive new, finer-grained searches from them.

## Stopping rule

The default soft cap is 100 individual search queries, not 100 tool calls or search groups. It includes the 92 required core queries. Reaching the cap is not by itself a reason to stop while searches are producing useful new pages or leads.

Stop when either 5,000 distinct `page_url` records have been collected, or when both of the following are true:

- At least 100 individual queries have been attempted, or 20 consecutive materially different queries have produced neither a newly retained `page_url` nor a worthwhile new distinctive lead.
- Further searching does not appear fruitful based on the remaining untried terms, unresolved leads, and recent yield.

Thus, an active discovery streak may continue beyond 100 queries. A 20-query
drought may justify stopping before 100 only after the complete 92-query core and
when there are no promising untried leads. Repeated queries and cosmetic
reformulations do not count as materially different and do not advance the
drought counter.

## Final deliverable

Write the weekly shard to:

`./results/shards/[WEEK_START].results.jsonl`

Validate that every line is JSON; every object has exactly the eight fields in the prescribed order; both array fields are arrays; truncated strings remain; exact duplicate page records are merged; first-query provenance is retained; and off-host occurrences were not excluded.

Report:

- Search-call count.
- Individual-query count.
- JSONL record and distinct-`page_url` counts.
- Total `urls_in_page` strings and retained truncated strings.
- Newly discovered services or terms.
- Important cache-coverage or date-attribution limitations.

# Additional v3 requirements

The requirements below refine and, where they conflict, override the preceding general rules.

## Cache-only evidence boundary

Use search-cache results as the only source of records and URL evidence.

You may open a search result only to inspect an indexed or cached representation supplied by the search system. Do not fetch, browse, or extract new evidence from the current live version of the destination page.

A URL may be added to `urls_in_page` only if visibly present in the search-result URL, title, snippet, cache metadata, or content explicitly returned as an indexed/cached representation. Do not add URLs discovered only by loading a live page, following a redirect, clicking a link, querying an API, or retrieving the underlying dataset.

If opening a result appears to return current mutable/live content rather than a stable cached representation, do not use newly exposed content as evidence. Retain only evidence visible in the originating search result.

The supplied CSV is a lead generator, not cache evidence. Its rows may not be copied into output unless independently surfaced by a search-cache result.

## Required query ledger

Record **every attempted search query**, including searches returning zero relevant results. The ledger, rather than `first_seen_query`, is authoritative for auditing search coverage and the stopping rule.

Maintain one incremental JSONL query-ledger checkpoint for each search group:

`./tmp/scratch/[WEEK_START].group_[NNN].queries.jsonl`

Each line represents one individual query, even when several queries were submitted in one batch. Use exactly these fields, in this order:

```json
{
  "group_number": 1,
  "query_sequence": 1,
  "search_mode": null,
  "query": null,
  "returned_result_count": 0,
  "retained_result_count": 0,
  "new_page_count": 0,
  "cumulative_page_count": 0,
  "new_distinctive_leads": []
}
```

Field rules:

- `group_number`: One-based search-batch number.
- `query_sequence`: One-based global query number within this agent's run.
- `search_mode`: Exact search mode used, if there are named search modes in your environment
- `query`: Exact submitted query string.
- `returned_result_count`: Number of results the search system returned for this individual query, relevant or irrelevant. If a batched response does not expose per-query counts, use `null`; never guess or assign the batch total to every query.
- `retained_result_count`: Number of returned results from this query that met inclusion rules, including pages already seen earlier.
- `new_page_count`: Number whose exact `page_url` had not previously appeared during this run.
- `cumulative_page_count`: Distinct retained `page_url` count after processing this query.
- `new_distinctive_leads`: Distinct newly observed terms that merit follow-up searches. Use `[]` when none.

Each ledger checkpoint contains only queries attempted in that group. The full ledger reconstructed by concatenating checkpoints in group-number order must contain every query in continuous query-sequence order. Never omit zero-result or zero-new-page queries.

For individually submitted queries, set `returned_result_count` to the number of
distinct result blocks visibly returned by the tool only when result boundaries
are unambiguous. Otherwise use `null` and retain the raw response; do not infer a
count from prose, citation numbering, or an advertised backend total.

## Result checkpoints

Write incremental result checkpoints to:

`./tmp/scratch/[WEEK_START].group_[NNN].results.jsonl`

Each checkpoint contains only pages newly discovered or updated in that group. Replay checkpoints as ordered `page_url` upserts to verify that reconstructed state never loses a previously retained page. An empty result checkpoint is valid for a group that found no new page and made no update.

Use the eight-field result schema defined above, including `first_seen_query` and `matched_target_strings`.

## Search-discipline overrides

- Complete and ledger-audit the exact 92-query core matrix before pursuing optional or out-of-week leads.
- Do not substitute already-known May 27–28 searches for assigned-week coverage.
- Do not run any exact seed query listed in the reference section. Derive materially different queries from those examples.
- `site:` is allowed only for a known cache surface and must not replace substring searches.
- A query is materially different only when it changes a target term, cache surface, date/time partition, dataset clue, identifier fragment, or retrieval-chain hypothesis—not merely punctuation or word order.
- The stopping rule's 20-query drought is evaluated from the reconstructed query ledger using `new_page_count == 0` and an empty `new_distinctive_leads` array.
- Do not report a 20-query drought unless the final 20 ledger records all satisfy that test. Report the actual final drought length otherwise.

## v3 final deliverables

Write the final deduplicated result shard to:

`./results/shards/[WEEK_START].results.jsonl`

Write the complete query ledger to:

`./results/shards/[WEEK_START].queries.jsonl`

Before finishing, verify:

- Both final files exist and parse as JSONL.
- Result records use exactly the eight-field v2 schema.
- Query records use exactly the nine-field v3 ledger schema.
- `query_sequence` is continuous and strictly increasing.
- The ledger contains exactly the four required core queries for every initial target, with the correct Sunday, Wednesday, and Saturday dates, before any optional follow-up query.
- Required core queries were submitted as individual search-tool calls.
- Every search group has a corresponding exact raw-response file under
  `./tmp/raw/`.
- Reprocessing raw responses with the deterministic result-block rules reproduces
  the retained records, subject only to documented parser failures.
- Query checkpoints concatenate to the final query ledger.
- Replaying result checkpoints as ordered exact-`page_url` upserts produces the final result shard.
- Reconstructed checkpoint state never loses a previously retained page.
- Reported search and result counts agree with the ledger and result shard.

Once you're done, if there were any papercuts you experienced while executing the task, mention them in your final response.
