# Do failed API web opens still send blind GET requests?

Tested on 2026-09-16, 09:45:25–09:46:07 UTC, using the Responses API with
`tools: [{"type": "web_search"}]`. Models: `gpt-5.5` (resolved to
`gpt-5.5-2026-04-23`) and `gpt-6-astra`, both with low reasoning effort.

## Result

The URL-provenance failures produced **no GET to the requested target**.
A separate unsupported-content-type case did produce a GET while returning
no response body to the model. Both models behaved identically.

| Test | GETs to target per model | Body available in web results? | Model-reported outcome |
|---|---:|---|---|
| Fresh HTML URL supplied in user message | 1 | Yes; server-generated marker present | Success |
| Click the link on that page in the same response | 1 | Yes; server-generated marker present | Success |
| Reopen the clicked URL in the next user turn, with history retained | 0 new GETs | No | `not safe to open` |
| Fresh HTML URL supplied only by a file-reading tool result | 0 | No | `not safe to open` |
| Fresh URL supplied in user message, returning `application/octet-stream` | 1 | No | `Unsupported content-type: application/octet-stream` |

In particular, the two fresh file-tool-only URLs were never fetched during the
entire observation window. The clicked targets were each fetched exactly once,
in the initial turn, and received no later requests.

The binary-content targets returned HTTP **200** and their response writes
completed at the local server. The web tool then reported an error containing
`(400) Unsupported content-type`; that 400 was not the origin server's status.
This is a confirmed request with a body unavailable to the model.

## Method

- Started a dedicated Python HTTP server on a loopback port and exposed it
  through the installed, configured ngrok. It served only generated probe pages.
- Validated the tunnel with a separate health-check path before the API calls.
- Assigned each model and case its own unpredictable URL path. No test path was
  preflighted. The pages sent `Cache-Control: no-store, no-cache, max-age=0`.
- Generated a new random `PROBE_MARKER_…` when each response was served.
  These marker values were absent from model requests. Their presence in actual
  `web_search_call.results` establishes that page content reached the model.
- Logged method, complete path, timestamp, User-Agent, response status, media
  type, response marker, and whether the response write completed.
- Used five Responses API requests per model, ten total:
  1. User supplies the seed URL; model opens it, clicks its only numbered link,
     and records the destination URL and marker in its final answer.
  2. A URL-free follow-up user message requests the exact destination URL, using
     `previous_response_id` to preserve history.
  3. A fresh conversation requests the custom `read_probe_url` function. Its
     user message contains no URL.
  4. The host actually reads the saved URL file and returns its contents as a
     `function_call_output`; the model opens that URL.
  5. A fresh user message supplies the URL of the binary-content control.
- All requested navigation calls were verified in the raw API responses.
  The initial second call's result explicitly records `Source: click(...)`.
- Observed HTTP activity for ten additional seconds after the final API call,
  then stopped both ngrok and the local HTTP server.

There were eight HTTP requests in total: six successful requests to experiment
targets, one harness health check, and one `/robots.txt` request from an
`OAI-SearchBot` User-Agent. The six experiment requests had a `ChatGPT-User`
User-Agent. The robots request is separate from requests to the tested paths;
this experiment does not attribute that auxiliary request to a specific call.

## What this establishes

An empty web result can represent either an attempted open with no target
request observed, or a completed HTTP fetch whose content was not exposed.
In this experiment the `not safe to open` cases were the former, while the
unsupported media-type cases were the latter.

The fresh file-tool-only controls avoid the ambiguity of reopening a previously
cached page. Origin logs establish whether the target request reached this
server; they do not expose every internal check, DNS lookup, or intermediate
network operation. These results apply to the tested endpoints and models.

## Reproduce and inspect

The [standalone Python script](ngrok-blind-get-probe.py) requires Python 3,
configured ngrok, and `OPENAI_WEB_SEARCH_API_KEY` in the environment. It creates
a new output directory and stops its own server and ngrok process on completion.

```bash
python3 analyses/web-ref-api-probe/ngrok-blind-get-probe.py \
  --out "/tmp/ngrok-blind-get-$(date +%s)"
```

Evidence:

- [Complete HTTP request log](results/2026-09-16-ngrok-blind-get/http-events.jsonl)
- [Per-case summary](results/2026-09-16-ngrok-blind-get/summary.json)
- [Validation audit](results/2026-09-16-ngrok-blind-get/audit.json)
- [GPT-5.5 API requests and responses](results/2026-09-16-ngrok-blind-get/gpt-5.5/)
- [GPT-6-Astra API requests and responses](results/2026-09-16-ngrok-blind-get/gpt-6-astra/)

The raw response files include public API tool records and assistant reports.
Failed web calls have empty `results`; the precise inner error strings above
are relayed by the models. HTTP hits, origin status codes, successful content
markers, and the empty web-result arrays are independently recorded.
