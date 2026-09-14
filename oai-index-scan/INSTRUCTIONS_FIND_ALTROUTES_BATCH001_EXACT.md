# Alternate-route cache search protocol — v1.0

You are investigating URLs already known to appear in web-search results. For
each target URL, you are given one or more search queries that surface it and
the exact search-result pages on which it was observed. Your job is to find new
search routes to the same target URL, require those routes to expose a different
result page, and collect the other relevant URLs exposed on each new page.

This is a search-cache discovery task. Do not test whether target URLs resolve,
fetch their live contents, or treat the target URL itself as the result page.

## Assigned run

- `RUN_ID`: `[RUN_ID]`
- `INPUT_FILE`: `[INPUT_FILE]`
- `MAX_QUERIES`: `[MAX_QUERIES]`

Paths below are relative to this instruction file.

## Input format

Read the assigned targets from `INPUT_FILE`. The input is JSONL with one object
per target URL and exactly this shape:

```json
{
  "url": "https://jqp.vercel.app/api/v0?url=https%3A%2F%2Fda.gd%2F4E3f0&jq=...",
  "known_routes": [
    {
      "query": "\"jqp.vercel.app/api/v0?url=https%3A%2F%2Fda.gd\"",
      "page_url": "https://goto.unm.edu/yourls-infos.php?id=7t6-o"
    }
  ]
}
```

Rules for the input:

- `url` is the exact target string. Do not silently normalize, decode, repair,
  truncate, or redirect-resolve it.
- `known_routes` contains search routes already demonstrated to expose that
  target. A target may have several known queries and several known pages.
- Treat all listed `query` values as already attempted. Do not submit them
  unchanged.
- Treat all listed `page_url` values as known pages. Rediscovering one does not
  satisfy the alternate-page objective, though it must still be recorded in the
  query ledger.
- Reject malformed input records explicitly in the final report rather than
  guessing their intended structure.

## Objectives

For every valid input target, find:

1. One or more materially different search queries that visibly surface the
   exact target URL on a result page whose exact `page_url` is absent from that
   target's `known_routes`.
2. Every other relevant URL string visibly surfaced in the same result block or
   cached representation of each newly discovered page.

Continue looking after the first success when other materially distinct cache
surfaces or page URLs remain plausible. A target is not complete merely because
a new query returns an already-known page.

## Definitions

### Exact target match

A result surfaces a target only when the exact target string is visibly present
in the result URL, title, snippet, cache metadata, or indexed/cached content.
Matching only the target host, decoded destination, short code, or a sibling URL
is a lead, not confirmation.

If the search system visibly truncates the target, preserve the truncated string
as evidence but do not claim an exact-target success unless another result block
or cached representation exposes the complete target independently.

### Alternate search query

A query is alternate when it differs materially from every known query for that
target. Material differences include changing the searched URL boundary,
encoded fragment, nested host pair, path or parameter fingerprint, cache-surface
constraint, short code, transformation fragment, or another evidence-bearing
identifier. Punctuation changes, reordered words, quote removal, or adding a
generic word do not by themselves make a query materially different.

### Different page

A page is different only when its exact search-result `page_url` differs from
every known `page_url` for that target. Different query text or a different
snippet for the same exact page does not qualify.

Query-string variants, statistics paths, cached snapshots, admin offsets, and
mobile mirrors count as different pages when their exact `page_url` differs.
Preserve them separately; do not infer that they are equivalent aliases.

### Other URLs on the new page

For a qualifying new page, collect every distinct relevant URL visibly present
in its result block or indexed/cached representation, not only the assigned
target. This includes complete, encoded, nested, malformed, and visibly
truncated URLs. Exclude ordinary navigation, stylesheet, image, account, and
advertising links unless they participate in a retrieval route or expose another
assigned target.

## Search strategy

Work target by target, but reuse a discovery across all targets it exactly
matches. Start from the supplied evidence and systematically change which stable
portion of the URL is searched.

Useful query families include:

1. The exact target URL in quotes.
2. The outer service and endpoint through the beginning of the encoded inner
   host, stopping before a variable short code or destination path. For example:
   `"jqp.vercel.app/api/v0?url=https%3A%2F%2Fda.gd"`.
3. The encoded inner destination plus a distinctive transformation or parameter
   prefix, omitting the outer host.
4. A unique short code plus the outer endpoint or a stable encoded parameter.
5. A distinctive JQ slice, generated identifier, dataset path, or cache marker
   paired with one route host.
6. A known cache surface combined with a target fragment using `site:`. Use this
   only to probe a plausible result-page host; do not substitute it for broad
   substring searches.
7. Encoded and double-encoded forms when the known evidence visibly contains
   both forms.
8. Truncated-prefix searches that stop immediately before a high-entropy or
   frequently varying component.

Prefer the shortest query that retains the route's distinctive indexed
fingerprint. When a narrow exact query succeeds, generalize it one component at
a time to discover sibling pages. When a broad query produces unrelated
collisions, restore the most discriminating path or encoded fragment.

Do not rely on Boolean operators or grouping syntax such as `OR`, `AND`, `NOT`,
or parentheses. Submit alternatives as separate queries. A negative `site:`
filter may be tried as a lead, but do not assume the backend enforces it; verify
the returned page URLs directly.

## Search procedure

Use every distinct web-search mode actually exposed in your environment and
record the exact mode reported by the tool. If only one mode is available, use
it and note that limitation. Request the tool's `long` response length for every
query so visible evidence is comparable.

For each target:

1. Record all known queries and known page URLs before searching.
2. Derive an initial queue containing at least three materially different query
   families when the target structure permits it.
3. Submit queries individually whenever the search response would otherwise
   make query-to-result attribution ambiguous.
4. Inspect every returned result block for the exact target string.
5. When the target appears on a new exact `page_url`, retain that page and every
   relevant URL visible in the same block.
6. Search distinctive new cache surfaces, identifiers, paths, and sibling route
   fragments exposed by successful results.
7. Search other relevant URLs from new pages when they plausibly lead to another
   page exposing an assigned target.
8. Continue until the stopping rule is met. Do not stop merely because a query
   rediscovers a known page.

Never claim success based only on the search query itself. The target must be
visible in a returned result block or indexed/cached representation.

## Cache-only evidence boundary

Use search-cache results as the only source of records and URL evidence.

You may open a search result only by using a reference returned by the search
tool, and only to inspect an indexed or cached representation supplied by the
search system. Never pass an arbitrary or literal URL to an open operation.
Click only links exposed by a permitted referenced page.

Do not fetch, browse, or extract evidence from the current live destination,
follow redirects, query underlying APIs, or resolve short URLs. If opening a
result appears to return mutable/live content rather than a stable cached
representation, ignore newly exposed content and retain only evidence visible in
the originating search result.

## Deterministic result-block processing

Apply these rules to every query:

1. Split only on result boundaries visibly supplied by the search tool. Preserve
   the complete raw search response for audit.
2. Test the entire result block against every assigned target URL, not only the
   target that motivated the query.
3. A page qualifies for the result shard when it visibly contains at least one
   exact assigned target and its exact `page_url` is new for at least one matched
   target.
4. Populate `matched_target_strings` with every exact assigned target visibly
   present in the retained block.
5. Extract every distinct relevant URL visibly present in the retained block,
   including all matched targets and other retrieval-route URLs.
6. If a result matches only a partial or truncated target, preserve it in the raw
   response and query ledger but do not retain it as a successful alternate page.
7. If a new query returns a page already known for one target but new for another
   matched target, retain the page and list only the targets for which the block
   provides exact visible evidence.
8. Do not apply a subjective agent-attribution or benchmark-likeness filter after
   the exact-target rule is satisfied.

## Truncation

Never repair `[...]`, `...`, `…`, clipped query strings, or malformed URLs.
Store exactly the visible string. If complete and truncated forms both appear,
retain both as distinct observed strings. A truncated occurrence alone is not
proof that the complete assigned target appeared.

## Search groups and checkpoints

A search group is one submitted batch of search queries. Number groups
sequentially from `001` in submission order.

After every group, preserve the exact unmodified search-tool response at:

`./tmp/altroutes/raw/[RUN_ID].group_[NNN].txt`

Write newly discovered or updated result records at:

`./tmp/altroutes/scratch/[RUN_ID].group_[NNN].results.jsonl`

Write every attempted query, including zero-result and duplicate-only queries,
at:

`./tmp/altroutes/scratch/[RUN_ID].group_[NNN].queries.jsonl`

Result checkpoints are ordered upserts keyed by exact `page_url`. A later upsert
must preserve the earliest `first_seen_query` and union `urls_in_page` and
`matched_target_strings`. Query checkpoints are append-only. Replaying all
checkpoints in group order must reproduce both final files.

## Result output schema

Use the same result format as `INSTRUCTIONS.md`. Write one valid JSON object per
line with exactly these eight fields, in this order:

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

- `published_date`: Exact publication-date string exposed by search/cache,
  otherwise `null`.
- `modified_date`: Exact modification-date string exposed by search/cache,
  otherwise `null`.
- `cache_age`: Exact crawl/cache-age string exposed by search/cache, otherwise
  `null`.
- `page_title`: Exact displayed title, otherwise `null`.
- `page_url`: Exact new cache-result or search-result URL.
- `urls_in_page`: Every distinct relevant URL visibly present on this result,
  including assigned targets, other URLs, and incomplete/truncated strings.
- `first_seen_query`: Exact alternate query whose returned results first exposed
  this exact `page_url` during this run.
- `matched_target_strings`: Every exact assigned target URL visibly present in
  the result block. Do not put hosts, partial fragments, or inferred targets here.

Do not normalize dates or URLs. Deduplicate only identical strings within the two
arrays and identical `page_url` records within the run.

## Query-ledger schema

Use the same query-ledger format as `INSTRUCTIONS.md`. Write one object per
individual query with exactly these nine fields, in this order:

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

Count result blocks only when boundaries are unambiguous; otherwise use `null`
for `returned_result_count`. `retained_result_count` includes qualifying pages
already retained earlier in this run. `new_page_count` counts exact `page_url`
values first retained by that query. Never omit unsuccessful queries.

## Stopping rule

The query budget is `MAX_QUERIES` individual queries across all targets. Allocate
queries adaptively, but attempt at least three materially different query
families per valid target unless the total budget makes that impossible.

Stop when either:

- every valid target has at least one confirmed alternate page and the last ten
  materially different queries produced no new qualifying page or worthwhile
  lead; or
- the query budget is exhausted.

Do not report a target as successful when searches only rediscovered its known
pages. Report such a target as unresolved and list the query families attempted.

## Final deliverables

Write the final deduplicated result shard to:

`./results/altroutes/[RUN_ID].results.jsonl`

Write the complete query ledger to:

`./results/altroutes/[RUN_ID].queries.jsonl`

Before finishing, verify:

- Both final files exist and every line parses as JSON.
- Result records contain exactly the eight fields in the prescribed order.
- Query records contain exactly the nine fields in the prescribed order.
- `query_sequence` is continuous and strictly increasing.
- Every retained page visibly contains an exact assigned target URL.
- Every retained page is different from all known pages for at least one target
  in its `matched_target_strings`.
- Every assigned target present in a retained block appears in
  `matched_target_strings`.
- `urls_in_page` includes the matched target and all other relevant URLs visibly
  exposed by the result block.
- Known queries were not resubmitted unchanged.
- Every search group has a corresponding raw-response file.
- Replaying result checkpoints and concatenating query checkpoints reproduces
  the final deliverables.
- Reported counts agree with the final files and ledger.

Report:

- Valid and malformed input-target counts.
- Search-call and individual-query counts.
- Targets with at least one alternate page and unresolved targets.
- Number of distinct alternate pages.
- Total and distinct `urls_in_page` strings, including other URLs found alongside
  the assigned targets.
- New cache surfaces, query families, route hosts, and identifiers discovered.
- Targets for which only known pages or truncated evidence were found.
- Important search-cache, truncation, and attribution limitations.

Once you are done, mention any execution papercuts in your final response.

