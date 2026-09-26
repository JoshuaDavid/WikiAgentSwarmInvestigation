# Replacing a Responses API web result

**Interactive prototype:** [Web Gate playground](../web-gate-playground/README.md)
now connects real cache-only searches, human-gated opens, live-enabled fetches,
result replacement, cache misses, and forks through a local browser UI.

**Tested on 2026-09-16 with `gpt-6-astra`: custom function-result replacement
works; replaying native `web_search_call.results` did not preserve page content.**
Seven API requests completed with HTTP 200: three for native replay, four for the
custom function control. Both probes use Python 3's standard library.

**Follow-up:** We also tried exposing the full interface as a custom `web.run`
namespace with native web disabled. The API requires that reserved name to match
its configured schema; our candidates were rejected. Changing only the namespace
to `research_web.run` worked. See the [namespace experiment](namespace-results.md)
for the exact error, controls, and remaining uncertainty about schema matching.

**Schema-report repeatability:** Five fresh API reports agreed on all field names
and requiredness, but only one of ten pairs had identical schemas after removing
prose/default annotations. See the [reliability experiment](schema-reliability-results.md).

**Luna nullability check:** Ten independent Luna requests had 84.7% pairwise
nullability agreement across 45 fields, and 100% agreement on which properties
can be omitted. See the [field-level results](luna-nullability-results.md).

| Request | Assistant response |
| --- | --- |
| Native cache-only open of example.com | `Example Domain` |
| Replay native web result with replacement heading | `No main heading was returned.` |
| Replay native web result unchanged | `The tool returned no content, so I couldn’t determine the main heading.` |
| Custom tool, original native page snippet supplied as function output | `Example Domain` |
| Custom tool, replacement snippet supplied as function output | `REPLACED_HEADING_af856c399a44eb73e25fb02b` |
| Custom tool, cache-miss text supplied as function output | `CACHE_MISS` |

One additional request generated the custom function call and stopped with no final
answer, ready for the application to supply its result. All three continuations
branched from that same pending call.

The native replay branches both reported **4,519 input tokens**, despite different
snippet lengths. Together with the failed original-content control, this suggests
the supplied native `results` field was ignored when constructing model context.
The experiment does not prove that every possible native-tool interception
approach is impossible. HTTP 200 alone does not prove an input field reaches the
model.

[Native replay summary](results/2026-09-16-native-replay-authorized/summary.json)
and [custom function summary](results/2026-09-16-function-control/summary.json)
are saved alongside all request, response, and metadata files. These
requests used `store: false`; the replay used full local history, not
`previous_response_id`. Credential checks passed on both sets of saved artifacts.

## Native replay method

This probe tests the native `web_search_call` history item, rather than assuming
that replacement of a custom function result proves replacement of a hosted web
result. It makes three API requests.

1. Open `https://example.com/` using `web_search` with
   `external_web_access: false`, requesting `web_search_call.results` and
   `reasoning.encrypted_content` in the response.
2. Copy the returned history through the first web result, remove **every**
   subsequent item, replace the page snippet with a randomly generated heading,
   and submit that edited history to a new Responses request. Disable further
   tools. Do not include `previous_response_id`.
3. Submit the identical prefix with the original, unmodified web result as a
   control.

The random heading is created after the initial response and appears only inside
the replaced tool result. The model is not told that a human, an evaluation, or a
replacement is involved. Success would establish that this field reaches the
model as supplied; it would not establish that an intervention is undetectable.

Run from the repository root, choosing a new output directory:

```bash
python3 analyses/responses-tool-result-probe/probe.py \
  --api-key-file /path/to/authorized-key.txt \
  --out /tmp/responses-tool-result-probe
```

Alternatively, use `OPENAI_API_KEY` or `OPENAI_WEB_SEARCH_API_KEY` in the
environment. Defaults to `gpt-6-astra`; `--model` overrides it. Normal API charges
apply. The key is read only at runtime and is excluded from request/response
artifacts. Each request, response, HTTP status, usage, and extracted assistant
answer is saved. A JSON summary records whether the replacement appeared.

## Custom function control

[function_probe.py](function_probe.py) exposes an application-managed `web_run`
function with an `open: [{ref_id: ...}]` argument. The model calls it, and the
application submits one of three `function_call_output` values in a follow-up
Responses request. The original content is taken directly from the successful
native web request, not reconstructed from the native assistant's answer.

```bash
python3 analyses/responses-tool-result-probe/function_probe.py \
  --api-key-file /path/to/authorized-key.txt \
  --native-result /tmp/responses-tool-result-probe/01-original.response.json \
  --out /tmp/responses-function-control
```

The essential continuation, after the model has produced a function call, is:

```python
continuation = client.responses.create(
    model=model,
    tools=tools,
    input=[original_user_message, *pending_response.output, {
        "type": "function_call_output",
        "call_id": pending_call.call_id,
        "output": human_selected_text,
    }],
)
```

The probe includes all prior output items, preserving encrypted reasoning if
returned. It disables subsequent tool calls solely to isolate this one-result
test; an actual agent loop would allow further calls. The random replacement
appears only in the tool output, and each branch omits the other branches. No
model-facing message describes an evaluation, human approval, or replacement.
This proves the continuation consumed the selected content, not that a model
could never infer an intervention.

## Proposed human-gated setup

The demonstrated approach is to put the evaluated agent behind an
application-managed web function. Keep the human decision interface and audit
log outside the agent's conversation. Do not give that agent an additional native
web tool that could bypass the gate.

1. A `search_query` function request goes immediately to a separate Responses
   request using native `web_search` with `external_web_access: false`. Return
   the extracted results and maintain an application-owned reference-to-URL map.
   This search adapter was not exercised by these probes. Searches can remain
   ungated, but no backend can promise that every search succeeds.
2. An `open` function request resolves the reference using that map and records
   `AWAITING_FETCH_DECISION`. Stop issuing evaluated-agent requests. The human
   can allow the fetch, supply replacement text without fetching, or return a
   cache miss without fetching.
3. On allow, issue a separate Responses request whose user input includes the
   full URL and asks for one direct open. Enable live web access there and request
   `web_search_call.results`. Check that the actual action is the requested
   `open_page`; a prompt alone is not an exact tool-execution guarantee.
4. Show the returned page snippet to the human, keeping it outside the evaluated
   agent's context. The human selects unchanged content, edited content, or a
   cache miss. Save both the original result and the selected result in the audit
   log. Forward only the selected result as `function_call_output` and resume.

The separate native fetch, reference registry, search adapter, and human UI are a
proposed next stage, not a completed end-to-end harness. The empirical control
used an already captured native cache-only result and programmatically selected
the three alternatives.

## Limits of the native-tool approach

- Cache-only access is documented, but the docs do not promise that the model
  cannot infer that mode, that searches always succeed, or that every open fails.
  A cache-only open can return existing content.
- Replaying an edited result is separate from pausing the hosted tool before the
  model consumes it. The initial request in this probe completes normally; its
  subsequent answer and any subsequent reasoning are discarded for replay.
- The wrapper can keep approval decisions and mode labels out of the model's
  messages. Its function schema differs from the hosted native web tool, so this
  does not establish an indistinguishable native `web.run` environment.
- Native streaming progress events are not a demonstrated approval boundary.
  Discarding post-result output after a cache-only request is different from
  stopping the server before it processes that result.
- A live-enabled native fetch can still return cached content; live access is
  permission to fetch, not a guarantee of a fresh origin request. The workspace's
  [repeated-open probe](../web-ref-api-probe/ngrok-repeat-html-results.md)
  observed reuse across requests.
- The workspace's earlier probes found that some failed native web calls expose
  `results: []`, with error text only relayed by the assistant. An adapter must
  distinguish raw page results, assistant descriptions, and synthetic failures.
- Existing [web reference probes](../web-ref-api-probe/one-click-results.md)
  found that fresh API requests do not reliably preserve usable web references
  and URL admission state. A separate fetch request should use a resolved URL,
  not another request's opaque page reference.

## Official documentation

- [Web search](https://developers.openai.com/api/docs/guides/tools-web-search):
  `external_web_access: false` selects cached/indexed content.
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling):
  application-supplied `function_call_output` and multi-turn continuation.
- [Responses beta reference](https://developers.openai.com/api/reference/python/resources/beta/subresources/responses):
  lists `web_search_call.results` and `reasoning.encrypted_content` as includes.
