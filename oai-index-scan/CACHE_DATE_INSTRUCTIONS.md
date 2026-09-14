# Search-cache entry dating protocol — v1.0

## Purpose

Estimate when an already-searchable item entered the search cache by repeatedly
observing the cache's relative-age label (for example, `3 days ago`). Preserve
the observations and the exact retrieval times, then narrow the possible entry
time by interval intersection and transition probes.

This protocol dates **entry into the observed search cache**. It does not date
publication, page creation, modification, the first live crawl by another
system, or the first time an item could have been found by some other query.

This is a companion to `SPIDER_INSTRUCTIONS.md`. Spider output supplies
candidate result identities and provenance; dating runs observe selected exact
results over time. Dating must not rewrite spider evidence.

## Important limitation

A search performed today with a historical date in its query is still a search
of today's index. It is not an as-of search and cannot establish whether the
result was searchable on that historical date. Binary search is valid only over
real observations made at known times, or over a genuine versioned/as-of cache
whose historical semantics have been independently verified.

## Time model

Represent all machine times as integer Unix milliseconds and also store their
UTC ISO-8601 rendering. Do not derive bounds from the calendar date alone.

For a renderer independently established to display

```text
floor((retrieval_time - entry_time) / unit) units ago
```

an observation of integer `n` at time `t` implies the half-open entry interval

```text
(t - (n + 1) * unit, t - n * unit]
```

The lower bound is exclusive and the upper bound inclusive. For example, `3
days ago` retrieved at `2026-09-11T12:00:00Z` implies an entry after September
7 at 12:00 UTC and no later than September 8 at 12:00 UTC, assuming a fixed
24-hour day and floor semantics.

Never silently assume that the displayed label uses this model. A provider may
round rather than floor, use calendar boundaries, local time, coarse promotion
thresholds, or reuse stale metadata. Record the model as `unverified` until a
transition or control item establishes it. Bounds calculated under an
unverified model are hypotheses, not findings.

Treat units as follows:

- `second`, `minute`, `hour`, `day`, and `week` may use fixed durations only
  after the provider's behavior has been calibrated. A fixed week is seven
  fixed days.
- `month` and `year` are not fixed durations. Do not convert them to 30 or 365
  days. Retain the raw label and use observed transitions or a documented
  provider-specific calendar model.
- `today`, `yesterday`, `just now`, bare dates, and provider-specific labels
  require separately documented semantics.

## Inputs and identity

Each target must have a stable `target_id` and:

- the exact `page_url` displayed by the search result;
- the exact query that reliably surfaces it;
- any search domain, recency, or mode parameters;
- originating shard, spider run, page, and raw-response identifiers;
- enough stable title, URL, or snippet material to detect result substitution.

Do not merge different exact `page_url` strings. If one page is exposed by
several queries, one target may retain several query recipes, but observations
from different cache providers or search modes must be separate series.

## Run identity and files

Assign a stable `RUN_ID`, for example `cache_dates_2026-09-11_v1`. Paths below
are relative to `./oai-index-scan`.

Write working state under:

`./tmp/cache-dating/[RUN_ID]/`

Write finalized output under:

`./results/cache-dating/[RUN_ID]/`

Required files:

- `manifest.json`: protocol version, creation time, provider/search mode,
  renderer model and its evidence, target sources, limits, and stop policy.
- `targets.jsonl`: immutable target identities and exact search recipes.
- `events.jsonl`: append-only authoritative ledger.
- `observations.jsonl`: one materialized row per completed retrieval.
- `estimates.jsonl`: latest materialized estimate per target and series.
- `schedule.jsonl`: pending and completed probe plans.
- `raw/search_[NNNNNN].json` for direct Responses calls, or `.txt` for Codex
  worker calls: exact response for every search, including calls with no result
  or an ambiguous match.

Materialized files must be reproducible by replaying `events.jsonl`. Replace
them atomically; never edit away an earlier observation.

## Observation schema

Store one record per retrieval attempt:

```json
{
  "observation_id": "o00000001",
  "target_id": "t00000001",
  "series_id": "web-default",
  "retrieved_at_unix_ms": 1789128000000,
  "retrieved_at_utc": "2026-09-11T12:00:00.000Z",
  "clock_source": "system_utc",
  "clock_uncertainty_ms": 1000,
  "query": "exact submitted query",
  "search_mode": "exact tool-reported mode or null",
  "result_page_url": "https://example.com/result",
  "match_status": "exact",
  "cache_field": "Crawled",
  "raw_cache_age": "3 days ago",
  "parsed_value": 3,
  "parsed_unit": "day",
  "renderer_model": "floor_fixed_duration_v1",
  "implied_lower_unix_ms": 1788782400000,
  "implied_lower_inclusive": false,
  "implied_upper_unix_ms": 1788868800000,
  "implied_upper_inclusive": true,
  "raw_response": "raw/search_000001.txt"
}
```

Capture retrieval time immediately before submitting and immediately after
receiving the response. If the tool does not expose its own retrieval time, use
the midpoint as `retrieved_at_unix_ms` and half the elapsed call duration plus
clock uncertainty as `clock_uncertainty_ms`. Expand the implied interval by
that uncertainty. Do not use the time at which a human later inspected the
saved response.

Preserve `raw_cache_age` exactly. Parse only an unambiguous label associated
with the exact matched result. Allowed `match_status` values are `exact`,
`missing`, `ambiguous`, `substituted`, and `tool_error`. Only `exact`
observations constrain the estimate.

## Event ledger

Every event contains monotonically increasing `event_sequence`, event time,
run ID, event type, target/series IDs when applicable, operation ID, and
details. Required event types are:

- `target_registered`
- `probe_scheduled`
- `search_claimed`
- `search_completed`
- `observation_recorded`
- `estimate_updated`
- `model_flagged`
- `probe_cancelled`
- `target_completed`

Append `search_claimed` before the call. Save and flush the raw response before
`search_completed`. An interrupted claim with a complete raw response must be
reconciled before retrying.

## Initial observation

1. Submit the target's exact search recipe and save the complete raw response.
2. Require the same exact result identity and stable signature used at target
   registration.
3. Record the exact relative-age field and retrieval-time envelope.
4. If the model supports the label, calculate its implied entry interval.
5. Intersect that interval with all earlier valid observations in the same
   series. Never average endpoints.
6. If the intersection is empty, preserve both observations and flag the model,
   result identity, provider stability, and clock as suspect. Do not discard the
   inconvenient observation.

An integer fixed-duration `days ago` observation already gives a window no
wider than approximately 24 hours. Coarse `weeks ago` can give a seven-day
window. Month labels generally require empirical transitions before they yield
defensible day bounds.

## Transition-guided binary search

The unknown sub-unit phase can be narrowed only by making new observations as
real time passes. It cannot be narrowed by issuing many identical searches at
the same instant.

For a current candidate entry interval `(L, U]` and a floor fixed-duration
label, choose a future retrieval time whose predicted label-transition boundary
corresponds as closely as possible to the midpoint `M = (L + U) / 2`.
Concretely, choose an integer label boundary `k` and schedule near
`probe_time = M + k * unit`, selecting the earliest practical future value.

Probe once just before and once just after the planned time when budget allows.
The observed side of the label transition tells whether the entry time lies
before or after the tested midpoint. Record the actual times, not merely the
planned time. Intersect the new implied interval with `(L, U]`, recompute the
midpoint, and repeat.

With one well-timed binary decision per day, a one-day interval can ideally
shrink by roughly one bit per day: about 12 hours, 6 hours, 3 hours, and so on.
This is an ideal bound, not a guarantee. Search refresh lag, label caching,
coarse update cadence, missed probe times, and clock uncertainty set a
practical floor. Default to stopping at one-day precision unless finer timing
answers a concrete research question.

Do not count these as binary decisions:

- a missing or substituted result;
- a repeated label that was observed far from the predicted boundary;
- a query with changed search mode, domain, recency, or provider;
- a relative age taken from a different result block;
- a historical date included merely as query text.

## Month-to-day strategy

For a raw month label, first monitor until its label changes. Bracket the real
transition using a last observation with the old label and first observation
with the new label. Daily observations can locate that transition to roughly a
day; more frequent probes near the predicted transition can tighten it.

Only after observing enough transitions to identify the provider's rule may a
calendar-month model be declared. Keep the original month-label evidence even
then. If the rule remains ambiguous, report only the empirical transition
bracket and do not claim an entry date.

## Search stability and negative observations

Search ranking and cache membership are mutable. A result failing to surface
does not mean it had not yet entered the cache, has left the cache, or was absent
at any earlier time. Negative observations never move an entry-time endpoint
unless the provider offers independently verified complete as-of membership
queries.

If several exact results satisfy the query, match by exact `page_url` plus the
registered stable signature. Mark the observation ambiguous if identity cannot
be established. Changes in the displayed `Crawled`/`Cached` field may represent
a recrawl; start a new `series_id` rather than intersecting pre- and post-recrawl
observations when a discontinuity is detected.

## Concurrency and scheduling

Use one coordinator as sole writer to the ledger and schedule. Workers may
perform searches, but each operation must have a unique durable claim and only
the coordinator may commit its observation.

Order due probes by planned time, then target ID. A probe remains useful after a
small scheduling miss, but its actual retrieval envelope controls the math.
Never backdate it to the planned time. Limit concurrent probes when provider
rate limits or response latency would make timestamps incomparable.

## Stopping and status

Configure per-target goals in the manifest. Recommended defaults are:

- stop immediately once the intersection width is at most 86,400,000 ms;
- pursue sub-day precision only when explicitly enabled;
- stop finer probing when the estimate width is at most four times the combined
  clock and observed renderer-update uncertainty;
- pause after three consecutive missing, ambiguous, or substituted results;
- start a new series on evidence of recrawl or renderer-rule change.

Estimate statuses are `unverified_model`, `monitoring`, `bounded`, `conflict`,
`recrawled`, `lost`, and `complete`. Only `bounded` or `complete` estimates with
a verified model may be stated as cache-entry bounds.

## Validation before finalization

Replay the event ledger from an empty state and verify:

- every observation has a raw response and exact retrieval-time envelope;
- every constraining observation matches the registered exact result;
- raw age labels were preserved and parsed without month/year shortcuts;
- all bounds use one documented renderer model and series;
- every estimate equals the intersection of its valid implied intervals;
- endpoint inclusivity and clock uncertainty were retained;
- empty intersections are reported as conflicts rather than repaired;
- every completed probe in the schedule has one terminal event;
- reported precision equals `upper_unix_ms - lower_unix_ms`, not a rounded
  calendar description.

## Final report

For every target report the provider/search mode, exact result identity, raw
observations, renderer-model confidence, UTC and Unix-ms bounds, interval width,
number of useful binary decisions, missing/ambiguous probes, recrawl evidence,
and stopping reason. Clearly distinguish a measured bound from a model-dependent
hypothesis.

Also report aggregate search calls, targets by status, scheduled probes still
pending, conflicts, and operational papercuts.

## Reference implementation

`cache_dating/orchestrator.py` implements the durable scheduler and launches the
existing hook-governed Codex worker pool. A minimal run is:

```bash
python3 oai-index-scan/cache_dating/orchestrator.py init \
  --run example --model-verified
python3 oai-index-scan/cache_dating/orchestrator.py add-target \
  --run example --target-id t1 --query 'distinctive exact query' \
  --page-url 'https://example.com/exact-result'
python3 oai-index-scan/cache_dating/orchestrator.py run \
  --run example --workers 4
python3 oai-index-scan/cache_dating/orchestrator.py status --run example
```

Targets can also be registered in one atomic bulk operation from JSONL whose
nonblank lines contain exactly `target_id`, `query`, and `page_url`:

```json
{"target_id":"t1","query":"first distinctive query","page_url":"https://example.com/a"}
{"target_id":"t2","query":"second distinctive query","page_url":"https://example.com/b"}
```

```bash
python3 oai-index-scan/cache_dating/orchestrator.py add-target \
  --run example --targets-jsonl ./targets.jsonl
```

The entire file is validated before the target and schedule files are changed.

By default, `run` sends one direct `gpt-5.6-luna` Responses API request per due
target and requests structured `web_search_call.results`. Every request fixes
the tool configuration to `external_web_access: false`. The API key is read at
call time from `/tmp/swarmchasers.txt`; override that location with
`--api-key-file`. The key is never copied into manifests, events, raw responses,
or worker logs.

Pass `--backend codex` to use the earlier hook-governed top-level Codex
`spider_agent` pool instead. This fallback retains the rendered-text parser and
does not offer the same typed result boundary. Observations from different
backends are never intersected; after a backend change the active estimate uses
only observations from the newest backend while preserving the older evidence.

Later invocations launch only probes whose scheduled transition time has
arrived. Use `run --wait` for a continuously running scheduler, or invoke `run`
periodically from a service or cron job. `--force` is primarily for recovering
or testing a pending probe; forcing a midpoint probe early usually adds little
or no timing information.

Each completed probe prints a concise stdout summary containing match status,
relative cache age, implied bounds, returned-result count, and raw-response
path, followed by aggregate batch counts. A missing match also prints up to five
candidate result URLs to expose page-identity mistakes. Pass `--show-raw` to
print complete search responses as well; they are always saved regardless.

Do not pass `--model-verified` merely to obtain a `complete` status. It asserts
that the provider's floor/fixed-duration behavior has been independently
calibrated as required above. Without it, observations and hypothetical bounds
are retained but reported as `unverified_model`.
