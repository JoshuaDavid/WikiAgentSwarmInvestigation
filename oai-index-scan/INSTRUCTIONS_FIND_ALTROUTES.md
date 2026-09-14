# Alternate-route cache search protocol — v2.0

You are given URLs already observed in web-search results. For each target URL,
the input records the query and result page that exposed it. Find materially
different searches that expose the exact target on a different result page, and
collect a bounded sample of other relevant URLs visible on those new pages.

This is a search-cache discovery task. Do not resolve target URLs, query their
underlying APIs, or treat the target URL itself as the page that proves a match.

## Assigned run

- `RUN_ID`: `[RUN_ID]`
- `INPUT_FILE`: `[INPUT_FILE]`
- `MAX_QUERIES`: `[MAX_QUERIES]` (soft stopping target, not a hard ceiling)
- `MAX_REFERENCED_PAGE_OPENS`: `[MAX_REFERENCED_PAGE_OPENS]` (default: 10)
- `MAX_URLS_PER_PAGE`: `[MAX_URLS_PER_PAGE]` (default: 100)
- `MAX_ALTERNATE_PAGES_PER_TARGET`: `[MAX_ALTERNATE_PAGES_PER_TARGET]` (default: 20)

Paths below are relative to this instruction file.

## Input format

`INPUT_FILE` is JSONL with one object per target:

```json
{"url":"https://jqp.vercel.app/api/v0?url=https%3A%2F%2Fda.gd%2F4E3f0&jq=...","known_routes":[{"query":"\"jqp.vercel.app/api/v0?url=https%3A%2F%2Fda.gd\"","page_url":"https://goto.unm.edu/yourls-infos.php?id=7t6-o"}]}
```

The strings may be truncated, malformed, encoded, or end in punctuation. Treat
them literally. Do not normalize, repair, decode, redirect-resolve, or reorder
parameters when deciding whether an exact match occurred.

## Objectives

For every valid target:

1. Validate at least one supplied known route by submitting its exact `query`
   and checking whether the exact target remains visible on its stated
   `page_url`. This is validation, not an alternate-page success.
2. Find materially different queries that visibly expose the exact target URL
   on a page whose exact `page_url` is absent from that target's known routes.
3. From each qualifying page, collect up to `MAX_URLS_PER_PAGE` other relevant
   URL strings visible in the same result block or cached representation.
4. Record promising search directions not exhausted that appear likely to
   reward additional effort.
5. Emit at least one result row for every valid target. If no alternate page is
   confirmed, emit a `gave_up` row rather than an empty shard.

## Matching rules

### Exact target evidence

A page exposes a target only when the exact target string is visibly present in
its search-result URL, title, snippet, metadata, or indexed/cached content.
Decoded equivalents, reordered parameters, sibling URLs, host-only matches, and
truncated approximations are leads, not proof. Preserve useful near matches in
`evidence_excerpts` and `promising_search_directions`.

### Alternate query and page

A materially different query changes an evidence-bearing boundary: the searched
URL prefix, encoded fragment, nested host pair, endpoint, parameter fingerprint,
short code, transformation fragment, cache surface, or identifier. Punctuation
or word-order changes alone are not material.

Replay an exact supplied query once for validation, then do not repeat it.

A qualifying page has an exact `page_url` different from every known page for
that target. Preserve pagination, query, case, localization, snapshot, and mirror
variants as distinct exact pages. When a distinction looks cosmetic, say so in
`evidence_excerpts`; do not silently canonicalize it.

## Search strategy

Start with known-route validation, then derive at least three materially
different query families per target when possible:

1. Exact target URL in quotes.
2. Outer endpoint through the encoded inner hostname, stopping before a variable
   path or short code; e.g. `"jqp.vercel.app/api/v0?url=https%3A%2F%2Fda.gd"`.
3. Encoded inner destination plus a distinctive transformation prefix, omitting
   the outer host.
4. Short code plus outer endpoint or stable encoded parameter.
5. Distinctive JQ slice, dataset path, identifier, or cache marker plus one host.
6. Known cache-surface host plus target fragment using `site:`.
7. Encoded and double-encoded forms when both are visible in evidence.
8. Stable prefix ending immediately before a high-entropy component.

Prefer the shortest query retaining the indexed fingerprint. Generalize a
successful query one component at a time; tighten a noisy query with its most
discriminating fragment. Do not depend on `OR`, `AND`, `NOT`, or parentheses.
Negative `site:` constraints are leads only; verify returned page URLs.

## Calls, groups, and ledger attribution

A search group is exactly one search-tool call. Number calls from `001`. If one
call submits several queries, every query shares its `group_number` and gets its
own increasing `query_sequence` row.

Batch only when provenance remains clear. If a combined response does not
attribute results to queries, set affected per-query counts to `null`; do not
guess. Use every named search mode exposed, record its exact name, and request
`long` response length consistently.

## Opens and evidence boundary

Search snippets and indexed/cached representations are the only evidence. Open
only references returned by search; never pass a literal URL to open. Click only
links exposed by a permitted referenced page. Do not exceed
`MAX_REFERENCED_PAGE_OPENS` total opens.

Do not fetch live destinations, follow redirects, resolve short URLs, or query
underlying APIs. Ignore content from an open that appears current/live rather
than indexed or cached.

## Bounded URL collection

For each alternate page, collect relevant URL strings in visible order up to
`MAX_URLS_PER_PAGE`. Relevant URLs include assigned targets, nested retrieval
routes, proxy/openers, shorteners, caches/archives, dataset destinations, and
sibling routes from the same cluster. Exclude navigation, stylesheets, accounts,
ads, and unrelated chrome.

If visible relevant URLs exceed the cap, keep assigned targets first, then the
most distinctive nested routes; set `url_collection_truncated` to `true`; and
record the omitted family or continuation point in
`promising_search_directions`.

Never repair `[...]`, `...`, `…`, clipped strings, entities, or punctuation.

## Evidence excerpts

Store short excerpts sufficient to audit each decision. Copy at most 500 visible
characters and use this shape:

```json
{"query":"exact query","excerpt":"visible text containing the target or near match","assessment":"exact_match"}
```

Allowed assessments: `known_route_validation`, `exact_match`, `near_match`, and
`limitation`. Do not reconstruct omitted text.

## Result schema

Write one JSON object per line with exactly these fields, in order:

```json
{
  "outcome": "alternate_page",
  "page_title": null,
  "page_url": null,
  "urls_in_page": [],
  "url_collection_truncated": false,
  "first_seen_query": null,
  "matched_target_strings": [],
  "evidence_excerpts": [],
  "published_at_descriptor": null,
  "cached_at_descriptor": null,
  "viewed_at": null,
  "gave_up_reason": null,
  "promising_search_directions": []
}
```

- `outcome`: `alternate_page` or `gave_up`.
- `page_title`, `page_url`: exact displayed alternate-page values; both `null`
  for `gave_up`.
- `urls_in_page`: bounded visible relevant URLs. A `gave_up` row may include
  useful exact or truncated near-match strings.
- `url_collection_truncated`: whether the visible relevant set exceeded the cap.
- `first_seen_query`: first alternate query exposing the page; `null` for
  `gave_up`.
- `matched_target_strings`: exact targets visible on an alternate page. A
  `gave_up` row contains exactly its assigned target as an administrative link;
  `outcome` distinguishes this from successful evidence.
- `evidence_excerpts`: audit excerpts in the schema above.
- `published_at_descriptor`: exact visible publication label/text, with no
  normalization or inference.
- `cached_at_descriptor`: exact visible crawl/cache label/text, with no
  normalization or inference.
- `viewed_at`: inspection time in UTC RFC 3339 (`YYYY-MM-DDTHH:MM:SSZ`).
- `gave_up_reason`: `null` for alternate pages; concise reason otherwise.
- `promising_search_directions`: concrete query families, cache surfaces, page
  offsets, identifiers, or evidence gaps likely to reward more effort. Use `[]`
  only if no credible direction remains.

When one page matches several targets, emit one page row listing all exact
matches. Every target with no qualifying page gets exactly one `gave_up` row.
Therefore every valid task shard has at least one row.

## Query-ledger schema

Write every query, including validation and zero-result searches, with exactly
these fields in order:

```json
{
  "group_number": 1,
  "query_sequence": 1,
  "search_mode": null,
  "query": null,
  "purpose": "known_route_validation",
  "returned_result_count": 0,
  "retained_result_count": 0,
  "new_page_count": 0,
  "cumulative_page_count": 0,
  "new_distinctive_leads": []
}
```

`purpose` is `known_route_validation` or `alternate_route_search`. Use `null`
for result counts when boundaries or attribution are ambiguous. Never omit an
unsuccessful query.

## Lightweight artifacts

Do not create per-query raw files or scratch checkpoints. The transcript is the
raw interaction record. The final result shard and ledger are the durable output.

Write:

`./results/altroutes/[RUN_ID].results.jsonl`

`./results/altroutes/[RUN_ID].queries.jsonl`

## Stopping rule

`MAX_QUERIES` is a soft run-wide stopping target, not a hard ceiling or a
per-target quota. Allocate queries adaptively and aim to stop around that number.
It is acceptable to go modestly over when finishing an already-submitted batch,
checking a promising lead, or completing coherent coverage of a target. Do not
discard, hide, or omit work merely because it occurred after the target: include
every extra query in the ledger, retain every qualifying result, and report the
actual final query count. Stop when the current useful thread is complete, or
when all targets are resolved and the last ten materially different queries
produced neither a new page nor a worthwhile lead. Record useful unfinished work
in `promising_search_directions`.

## Validation and report

Before finishing, verify:

- Both final files exist and every nonblank line parses as JSON.
- Rows contain exactly the prescribed fields in order.
- `query_sequence` is continuous; `group_number` increments once per tool call.
- At least one known route was replayed for every valid target.
- Every `alternate_page` visibly contains an exact target and is new for at
  least one matched target.
- Every unresolved target has exactly one `gave_up` row.
- Every valid task shard contains at least one row.
- URL, page, and open caps were respected.
- Every attempted query, including queries beyond the soft stopping target, is
  present in the ledger and included in reported totals.

Report valid/malformed targets, calls, queries, alternate pages, resolved and
gave-up targets, URL totals, capped collections, promising directions, temporal
descriptor limitations, and execution papercuts.

## Evaluation standard

An LLM evaluator will review the complete transcript and artifacts for whether
the work was done fully and well. Schema-valid output is necessary but not
sufficient.

Work target by target. Finding one alternate page does not finish a target:
generalize the successful query and try materially different surfaces until the
target is reasonably saturated or the run-wide soft stopping point requires
prioritization. Retain every qualifying alternate page encountered up to the
cap; never discard pages merely because one seems representative of the others.

The transcript should normally show known-route validation, an exact-literal
search, multiple distinct fingerprint families, follow-up on promising leads,
and at least one generalization of a successful query. These are expectations,
not rigid quotas; explain justified exceptions.

`promising_search_directions` must contain only credible work left untried at
stopping time. Do not list an obvious high-value direction instead of attempting
it.

The evaluator will grade per-target diligence, alternate-page recall,
URL-collection completeness, exact-match discipline, follow-through, and
stopping judgment. Large yields from a few easy targets do not compensate for
shallow coverage of the rest. Do not treat many pages from one common URL as
evidence that the remaining targets were searched thoroughly.

Do not omit a qualifying alternate page because another page has similar
content, comes from the same query, or seems representative. Exact-distinct
qualifying pages should all be recorded up to the cap. Describe duplicated
content lineage in the evidence rather than deleting the page.
