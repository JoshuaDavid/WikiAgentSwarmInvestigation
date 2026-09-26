# Repeated opens of the same HTML URL

Tested on 2026-09-16 starting at 10:08:10 UTC, using ngrok and the Responses
API's `web_search` tool. Models: `gpt-5.5` (resolved to `gpt-5.5-2026-04-23`)
and `gpt-6-astra`, both with low reasoning effort.

## Result

**Each unchanged HTML URL received only one GET, although all three web opens
returned its content successfully.** Every repeated result contained the exact
random marker generated for the first HTTP response.

| Model | Three opens in one API response | One open in each of three user turns |
|---|---|---|
| GPT-5.5 | 3 successful web calls, 1 total target GET | 3 successful web calls, target GET counts 1, 0, 0 |
| GPT-6-Astra | 3 successful web calls, 1 total target GET | 3 successful web calls, target GET counts 1, 0, 0 |

Across both models: eight API requests, twelve verified web open actions, and
four target GETs. All twelve web calls returned page content containing the
correct marker in the raw `web_search_call.results`, not just in the model's
final answer.

Thus the repeated results reused the original fetched content without making
another request to the origin. This happened even though the server sent
`Cache-Control: no-store, no-cache, max-age=0` and `Pragma: no-cache`.
The experiment does not establish the internal cache location, scope, or
expiration time.

## Method

- Reused the [binary repeat experiment](ngrok-repeat-binary-results.md) with
  `--response-kind html`. The server returned `text/html; charset=utf-8`.
- Used fresh unpredictable paths for each model and scenario. Each URL remained
  identical across its three opens, without changed query strings or refs.
- The server generated a new random `PROBE_MARKER_…` for every GET. The values
  were absent from requests to the models. A refetch would generate a different
  marker and an additional server log entry.
- The same-turn test requested three sequential web calls, each opening the
  full URL, and verified all three recorded `open_page` actions.
- In the cross-turn test, only the first user message contained the URL. Two
  subsequent URL-free messages requested a new open of that exact URL.
  `previous_response_id` preserved the conversation history. All three API
  responses recorded a new open action for the same full URL.
- Later-turn wording said to repeat regardless of the earlier result, since
  the earlier HTML calls succeeded. Otherwise the procedure matched the binary
  variant, apart from fresh URLs, titles, and response content.
- One separate health-check request verified the tunnel. It is the fifth HTTP
  request in the complete log; the other four are experiment targets.
- Observed for ten additional seconds after the final API call, then stopped
  ngrok and the local server. No later target requests were observed.

## Evidence and reproduction

- [Complete HTTP request log](results/2026-09-16-ngrok-repeat-html/http-events.jsonl)
- [Per-call summaries and returned markers](results/2026-09-16-ngrok-repeat-html/summary.json)
- [Audit](results/2026-09-16-ngrok-repeat-html/audit.json)
- [GPT-5.5 requests and responses](results/2026-09-16-ngrok-repeat-html/gpt-5.5/)
- [GPT-6-Astra requests and responses](results/2026-09-16-ngrok-repeat-html/gpt-6-astra/)
- [Repeat-test script](ngrok-repeat-binary-probe.py), with the adjacent
  [HTTP/ngrok harness](ngrok-blind-get-probe.py).

Requires Python 3, configured ngrok, and `OPENAI_WEB_SEARCH_API_KEY` in the
environment. From the repository root:

```bash
python3 analyses/web-ref-api-probe/ngrok-repeat-binary-probe.py \
  --response-kind html \
  --out "/tmp/ngrok-repeat-html-$(date +%s)"
```
