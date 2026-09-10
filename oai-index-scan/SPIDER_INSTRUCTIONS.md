# Search-cache spider protocol — v1.0

## Purpose

Traverse URLs exposed by existing search-cache results without repeatedly searching, opening, or emitting the same pages. This is a second-stage process: discovery runs governed by `INSTRUCTIONS.md` produce seed shards; this protocol expands those seeds through the search system.

The spider uses search-cache results as its evidence boundary. It does not use `curl`, direct HTTP clients, browser navigation, APIs, redirects, or live destination pages as evidence.

## Inputs and scope

Seed the frontier from every string in `urls_in_page` in one or more source shard files:

`./results/shards/*.results.jsonl`

Optionally restrict the source shards explicitly for a particular run. Record the selected files in the run manifest. Never modify a source shard.

Only enqueue strings that are complete absolute `http://` or `https://` URLs. Preserve truncated or malformed strings as observed evidence, but mark them ineligible rather than guessing missing content. URLs obtained from an opened search representation may be enqueued under the same rule.

## Run identity and files

Assign each spider run a stable `RUN_ID`, such as `all_shards_2026-09-10_v1`. All paths are relative to `./oai-index-scan` when invoked from the repository root.

Write working state under:

`./tmp/spider/[RUN_ID]/`

Write finalized outputs under:

`./results/spider/[RUN_ID]/`

Required working files:

- `manifest.json`: run ID, creation time, source shards, limits, and protocol version.
- `events.jsonl`: append-only authoritative event ledger.
- `frontier.jsonl`: latest materialized state for every queue key; replace atomically after replaying events.
- `pages.jsonl`: one materialized record per exact independently surfaced `page_url`.
- `raw/search_[NNNNNN].txt`: exact raw response for every search call.
- `raw/open_[NNNNNN].txt`: exact raw response for every open call.
- `queries.jsonl`: one record per individual search query, including zero-result queries.

On completion, copy the manifest, event ledger, materialized frontier, pages, query ledger, and raw directory to the finalized output directory. Preserve working files for audit unless explicitly instructed otherwise.

## Two identities: evidence and queue control

Never overwrite or normalize the observed URL string. Store it as `observed_url` exactly as exposed.

For queue deduplication only, derive `queue_key` conservatively:

1. Parse a complete absolute HTTP(S) URL.
2. Lowercase the scheme and hostname.
3. Remove the default port (`:80` for HTTP or `:443` for HTTPS).
4. Normalize an empty path to `/`.
5. Remove only the fragment beginning with `#`.
6. Preserve username, password, path spelling, path slash, percent encoding, query string, parameter order, duplicate parameters, and empty parameters exactly.

Do not treat HTTP and HTTPS as equal. Do not decode or re-encode percent escapes. Do not remove tracking parameters, sort parameters, resolve dot segments, follow redirects, infer trailing slashes, or merge truncated strings with complete ones.

Several exact `observed_url` values may map to one `queue_key`. Retain all variants and all provenance, but search/open the queue key only once unless a recorded retry policy applies.

## Required ancestry paths

Every discovered URL, including every URL still awaiting its first spider attempt, must have at least one reconstructible path explaining how the spider reached it. Store paths as parent pointers in the event ledger rather than duplicating a complete path array in every frontier row.

Assign every distinct discovery occurrence a stable `discovery_id`. A discovery stores:

- `discovery_id`;
- `parent_discovery_id`, or `null` for a root;
- `root_kind`: `search_term` or `url`;
- `root_value`: the exact originating search term or URL;
- `hop_depth` (`0` for the root);
- `traversal_depth` (`0` for every seed URL, increasing only when an opened page exposes a child);
- `observed_url` and `queue_key`;
- the immediate `source_page_url`, source file, query, and raw-response identifier when applicable.

For a URL seeded from an existing shard, use the source record's exact `first_seen_query` as a `search_term` root when available. Represent the source result page as the next node and the URL from its `urls_in_page` array as its child. If no originating query is available, use the source record's exact `page_url` as a `url` root. For a child found by opening a surfaced page, set its parent to the discovery occurrence whose search/open operation produced that page.

Before placing an eligible URL in `pending`, append its `discovered` or `child_discovered` event with a valid root or parent pointer. A pending frontier row without reconstructible ancestry is invalid and must not be claimed. Parent chains must be acyclic and must terminate at the declared root.

Queue-key deduplication does not discard alternate paths. The frontier may select the earliest valid discovery as `primary_discovery_id`, but it must also retain every distinct supporting `discovery_id`. Thus one queue item is processed once while all known ways of reaching it remain auditable.

At minimum, each materialized `frontier.jsonl` row must contain:

```json
{
  "queue_key": "https://example.com/path?a=1",
  "state": "pending",
  "primary_discovery_id": "d00000001",
  "supporting_discovery_ids": ["d00000001"],
  "observed_urls": ["https://example.com/path?a=1#section"],
  "minimum_hop_depth": 1,
  "minimum_traversal_depth": 0,
  "attempt_count": 0
}
```

The IDs in `supporting_discovery_ids` are the authoritative links to complete ancestry and provenance in `events.jsonl`.

## Frontier states

Each queue key has exactly one current state:

- `pending`: eligible and not yet claimed.
- `searching`: assigned to a search group.
- `not_surfaced`: no matching independent result was found.
- `embedded_only`: search results mentioned the URL, but none used it as their displayed destination.
- `surfaced`: at least one independent search-result reference matched and awaits opening.
- `opening`: matching references are assigned to an open group.
- `opened`: at least one matching reference was opened successfully.
- `expanded`: eligible child URLs from the opened representation have been recorded.
- `failed_retryable`: a transient search/open failure may be retried.
- `failed_terminal`: an ineligible URL or exhausted retry policy will not be retried.

State is materialized by replaying `events.jsonl`; never infer completed work merely from file names or agent reports. A later event may advance a state but must not erase earlier observations or provenance.

## Append-only event ledger

Write one JSON object per event with these fields:

```json
{
  "event_sequence": 1,
  "event_time": "2026-09-10T00:00:00Z",
  "run_id": "all_shards_2026-09-10_v1",
  "event_type": "discovered",
  "discovery_id": "d00000001",
  "parent_discovery_id": "d00000000",
  "root_kind": "search_term",
  "root_value": "urltomarkdown",
  "hop_depth": 1,
  "queue_key": "https://example.com/path?a=1",
  "observed_url": "https://example.com/path?a=1#section",
  "source_page_url": "https://cache.example/result",
  "source_file": "./results/shards/2026-05-17.results.jsonl",
  "search_sequence": null,
  "open_sequence": null,
  "details": {}
}
```

Use monotonically increasing `event_sequence` values within the run. Required event types are:

- `ancestry_root`
- `source_page_observed`
- `discovered`
- `marked_ineligible`
- `search_claimed`
- `search_completed`
- `embedded_mention_seen`
- `independent_result_surfaced`
- `open_claimed`
- `open_completed`
- `child_discovered`
- `expanded`
- `retry_scheduled`
- `failed_terminal`

Append and flush the relevant completion events before considering an operation complete. If interrupted after an operation but before its completion event, retain the raw response and reconcile it before retrying.

`ancestry_root` creates a non-queueable search-term or URL root. `source_page_observed` creates a non-queueable intermediate node for an existing shard result. These events have a `discovery_id` but may have `observed_url` or `queue_key` set to `null` when the node is a search term. They exist only to make ancestry explicit and are not frontier work. Events that create no ancestry node may set `discovery_id`, `parent_discovery_id`, `root_kind`, `root_value`, and `hop_depth` to `null`, but must identify the affected `queue_key` and operation. `discovered` and `child_discovered` events must populate all applicable ancestry fields.

## Seeding and provenance

For every source record, emit a `discovered` event for every eligible exact URL and retain:

- source shard path;
- source record's `page_url`;
- source record's `first_seen_query`;
- exact observed URL;
- derived queue key.

Also create or reference the root and intermediate source-page discovery nodes needed to reconstruct the path described above. Identical root or intermediate nodes may be shared; do not emit a separate copy for every child.

Repeated discoveries add provenance events but not duplicate frontier work. Do not enqueue the source record's `page_url` unless it is also visibly present in `urls_in_page` or the run explicitly elects to seed page URLs.

## Searching frontier items

Process `pending` items in deterministic first-discovery order, with `queue_key` as a tie-breaker.

1. Append `search_claimed` events before submitting a tool call.
2. Search the complete observed URL first. If exact-URL search is ineffective, a later retry may use one distinctive term or a conservative `site:` plus path token query. Record the exact query strategy.
3. Multiple queries may be submitted in one tool call when supported. Each query remains a distinct ledger record and counts separately toward limits.
4. Save the complete raw response before parsing it.
5. Classify each returned result:
   - **independent match**: its displayed destination URL equals an observed URL or queue key, allowing only the queue-key normalization rules above;
   - **embedded mention**: the desired URL occurs only in its title, snippet, content, or visible embedded URLs;
   - **unrelated**: neither condition holds.
6. Append one `independent_result_surfaced` event per distinct matching `page_url` and retain the temporary search-result reference for the immediate open phase.
7. If there is no independent match, record `embedded_only` when at least one embedded mention exists; otherwise record `not_surfaced`.

Do not infer that a URL is independently indexed merely because its text appears in another result. Failure to surface is not proof that the live URL is unavailable or absent from every cache.

## Opening surfaced results

Search-result references are temporary tool identifiers, not durable URLs. Open them during the same active tool context in which they were returned whenever possible.

1. Append `open_claimed` before opening.
2. Batch several matching references in one open call when supported.
3. Save the exact raw open response before parsing it.
4. Verify that the opened representation corresponds to the independently surfaced destination.
5. If the representation appears to be current mutable/live content rather than content supplied through the search system's indexed representation, record the ambiguity and do not use newly exposed URLs as cache evidence.
6. Otherwise extract every visibly present relevant absolute URL, preserving its exact string and provenance. Emit `child_discovered` events; queue only complete eligible URLs.
7. Append `expanded` only after all child discoveries from that representation are durably recorded.

If references expire before opening, re-search the already-known queue key solely to obtain fresh references. Record this as a reference-refresh retry; do not count it as discovery of a new URL or page.

## Page deduplication

`pages.jsonl` contains one record per exact independently surfaced `page_url`, regardless of how many queue items or queries exposed it. On repeated exposure:

- retain the earliest discovery and query;
- union exact parent queue keys and observed URL variants;
- union extracted child URLs without changing their spelling;
- retain every raw search/open response identifier;
- preserve failures and later successful attempts in the event ledger.

Do not merge two different exact `page_url` strings merely because their content, redirect destination, canonical tag, or queue key appears equivalent.

## Query ledger schema

Write one line per individual query:

```json
{
  "query_sequence": 1,
  "search_call_sequence": 1,
  "search_mode": "exact tool-reported mode or null",
  "query": "https://example.com/path?a=1",
  "query_strategy": "exact_url",
  "queue_keys": ["https://example.com/path?a=1"],
  "returned_result_count": 0,
  "independent_match_count": 0,
  "embedded_mention_count": 0,
  "new_page_count": 0,
  "new_queue_key_count": 0,
  "raw_response": "raw/search_000001.txt"
}
```

Record the exact search mode reported by the tool. If the tool exposes only one mode, use it and note that limitation; never invent mode names. Do not rely on Boolean operators or parentheses as hard constraints.

## Concurrency and crash safety

Use one coordinator as the sole writer to `events.jsonl`, or funnel worker results through one coordinator. Workers must never independently materialize shared frontier state.

Before dispatch, the coordinator appends claim events containing a unique operation ID and the exact queue keys. A queue key with an unexpired claim cannot be claimed again. On restart:

1. replay the complete event ledger;
2. reconcile claimed operations with saved raw responses;
3. finish parsing recoverable raw responses;
4. mark stale claims retryable only when no completed raw response exists;
5. rebuild `frontier.jsonl` and `pages.jsonl` atomically.

This provides at-least-once operation attempts but exactly-once materialized queue work. Duplicate tool responses may exist; duplicate final queue items and pages may not.

## Retry policy

Retries are allowed only for tool errors, expired references, incomplete/truncated tool responses, or a deliberately different fallback query strategy. Default maximums:

- exact search: one attempt;
- fallback search: one attempt;
- reference refresh: one attempt;
- open: two attempts including the first.

Record the reason and prior operation ID for every retry. Do not retry `not_surfaced` or `embedded_only` with cosmetic punctuation or word-order changes.

## Limits and stopping

Set limits in `manifest.json`; recommended defaults are 1,000 individual search queries, 1,000 open references, and traversal depth 3. Ancestry `hop_depth` counts the search-term/URL root and source-page nodes used to reconstruct provenance. Independently, seeds have `traversal_depth` 0 and children first exposed by opening a seed have `traversal_depth` 1. Apply spider depth limits only to `traversal_depth`.

Stop when any of these holds:

- no `pending`, `surfaced`, or retryable items remain;
- a configured hard query/open/depth limit is reached;
- 50 consecutive processed queue keys produce neither a new independently surfaced page nor a new eligible queue key, and further traversal does not feel fruitful.

If the spider is on a productive branch, a soft search/open limit may be exceeded only when the manifest explicitly marks it soft. Never exceed a hard limit. Report the unprocessed frontier size and reason when stopping before exhaustion.

## Validation before finalization

Replay `events.jsonl` from an empty state and verify:

- every materialized frontier row is reproducible from events;
- every query has a raw search response and ledger row;
- every completed open has a raw open response;
- no queue key has been searched twice without a recorded retry reason;
- no search-result reference was treated as durable provenance;
- every page record was independently surfaced, not merely embedded;
- every child URL is visibly supported by a saved opened representation;
- all observed spellings and provenance survive queue-key deduplication;
- every frontier item, especially every `pending` item, has at least one acyclic parent chain ending in an exact search-term or URL root;
- final counts agree across the manifest summary, frontier, pages, and ledger.

## Final report

Report:

- source shards and seed counts (exact observed URLs and unique queue keys);
- eligible and ineligible seed counts;
- individual searches, tool calls, opens, retries, and failures;
- independently surfaced pages, embedded-only URLs, and not-surfaced URLs;
- new child URLs and unique queue keys by depth;
- duplicate work avoided through queue and page deduplication;
- remaining frontier and stopping reason;
- search-mode and cache/live-content limitations;
- any protocol papercuts or ambiguous cases.
