# Repeated opens of the same application/octet-stream URL

Tested on 2026-09-16, 09:52:44–09:53:23 UTC, through ngrok and the Responses
API's `web_search` tool. Models: `gpt-5.5` (resolved to `gpt-5.5-2026-04-23`)
and `gpt-6-astra`, using low reasoning effort.

## Result

**Only the first open of each URL produced an HTTP GET to the target.**
Both models made all requested repeated web calls, and all calls reported
`Unsupported content-type: application/octet-stream`.

| Model | Three opens in one API response | One open in each of three user turns |
|---|---|---|
| GPT-5.5 | 3 web calls, 1 total target GET | 3 web calls, target GET counts 1, 0, 0 |
| GPT-6-Astra | 3 web calls, 1 total target GET | 3 web calls, target GET counts 1, 0, 0 |

Across both models: eight API requests, twelve verified web open actions, and
four target GETs. Each target GET received HTTP 200 with a completed response
write. Every web call returned an empty `results` array; no response marker
was available to the models.

The behavior is consistent with caching or reuse of the original error.
The experiment does not establish the internal mechanism, cache scope, or
expiration time. It establishes that these immediate repeated opens did not
produce additional requests to the origin, including across user turns.

## Method

- Used a dedicated local HTTP server behind ngrok. The server exposed only
  generated probe content and recorded every incoming request.
- Assigned each model two fresh unpredictable URLs: one for the same-turn
  test and one for the cross-turn test. Each scenario used its exact unchanged
  URL for all three opens, without query-string changes or opaque references.
- Both targets returned `Content-Type: application/octet-stream`, a new random
  response marker per GET, and `Cache-Control: no-store, no-cache, max-age=0`.
- The same-turn user message explicitly requested three sequential open calls,
  including repetitions after errors. The recorded API response contains three
  `open_page` actions for the identical URL.
- In the cross-turn test, the URL appeared only in the first user message.
  Two later URL-free user messages requested a new open of that same URL.
  `previous_response_id` chained the three responses, preserving the original
  user URL in history. Each response records a new open action for that URL.
- A separate health-check path verified the ngrok tunnel. It accounts for the
  fifth HTTP request in the log; the four remaining requests are test targets.
- Observed for ten additional seconds after the last API call, then stopped
  the tunnel and local server. No later target requests were observed.

The precise unsupported-content-type error strings are relayed by the models;
the actual open actions, empty result arrays, origin status codes, and GET
counts are independently recorded in the saved API responses and server log.

## Evidence and reproduction

- [HTTP request log](results/2026-09-16-ngrok-repeat-binary/http-events.jsonl)
- [Per-call summaries](results/2026-09-16-ngrok-repeat-binary/summary.json)
- [Audit](results/2026-09-16-ngrok-repeat-binary/audit.json)
- [GPT-5.5 requests and responses](results/2026-09-16-ngrok-repeat-binary/gpt-5.5/)
- [GPT-6-Astra requests and responses](results/2026-09-16-ngrok-repeat-binary/gpt-6-astra/)
- [Repeat-test script](ngrok-repeat-binary-probe.py), using the adjacent
  [HTTP/ngrok harness](ngrok-blind-get-probe.py).

Requires Python 3, configured ngrok, and `OPENAI_WEB_SEARCH_API_KEY` in the
environment. From the repository root:

```bash
python3 analyses/web-ref-api-probe/ngrok-repeat-binary-probe.py \
  --out "/tmp/ngrok-repeat-binary-$(date +%s)"
```
