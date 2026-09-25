# Can an application own the exact name web.run?

Tested through the Responses API on 2026-09-16 with `gpt-6-astra`.

**A custom namespace works, but the exact `web.run` name triggers a schema-match
requirement. No tested candidate satisfied it.** The error does not establish a
blanket prohibition: it explicitly leaves open the possibility that the server's
configured schema would be accepted.

A subsequent [five-report reliability test](schema-reliability-results.md) found
stable field inventories and requiredness but inconsistent fine details. It did
not produce an authoritative schema or resolve the matching requirement.

```text
Invalid Value: 'tools'. Function 'web.run' is reserved for use by this model and must match the configured schema.
```

## Direct comparison

[web-run.source.txt](web-run.source.txt) captures the web tool declaration exposed
in the current Codex session. [build_web_tool.py](build_web_tool.py) converts the
declaration into [web-run.tool.json](web-run.tool.json), a namespace named `web`
with a function named `run`. It preserves all 11 declared argument groups, nested
field names, enum values, optionality, and descriptions. The generated JSON Schema
uses `strict: false` to retain optional fields. This is a reconstruction of the
visible declaration, not an export of the API server's canonical JSON Schema.

| Definition | Outcome |
| --- | --- |
| `web.run`, reconstructed session interface | HTTP 400, reserved-schema error |
| Identical definition with only namespace changed to `research_web` | HTTP 200, application receives function calls |

The renamed control completed four requests:

1. The model called `research_web.run` with
   `{"search_query":[{"q":"IANA example domains"}],"response_length":"short"}`.
2. After receiving a controlled search-result fixture, it called the same function
   with `{"open":[{"ref_id":"turn0search0"}],"response_length":"short"}`.
3. A continuation supplied a generated heading only in `function_call_output`;
   the model returned that exact heading.
4. An alternative continuation from the same pending open supplied a cache miss;
   the model returned `CACHE_MISS`.

The evaluated requests enabled **only** the custom namespace. There was no
`web_search` or `web_search_preview` tool, and no native web calls appeared in the
responses. No search or fetch was performed by these fixtures. The successful
control proves that the namespace format and the reconstructed schema are valid
custom-tool definitions; it does not satisfy the request for the exact name.

[Rejected web.run response](results/2026-09-16-web-run-namespace/01-search-call.response.json)
and [successful renamed control](results/2026-09-16-research-web-control/summary.json).

## Investigating “must match the configured schema”

One separate request enabled native `web_search` with cache-only access, disabled
tool execution with `tool_choice: none`, and asked the model to describe its web
argument interface. Its [reported candidate](results/2026-09-16-native-schema-text/candidate-parameters.json)
differs from the current session's declaration: it includes `calculator`, nullable
optional fields, integer types, and a required `sports[].tool` field.

That report is generated text, **not an authoritative schema export**. It may
omit or invent details. We tested it rather than treating it as ground truth.

| Candidate supplied as web.run | Outcome |
| --- | --- |
| Model-reported native argument schema | Same reserved-schema HTTP 400 |
| Candidate with metadata/annotations removed | Same error |
| Candidate using a Pydantic-style nullable representation | Same error |
| Definition omitting parameters, to test whether the server supplies them | Same error |

[Candidate rejection](results/2026-09-16-web-native-candidate/01-search-call.response.json)
and [representation-variant results](results/2026-09-16-web-schema-variants/summary.json).

These failures do not identify which field is mismatched, whether descriptions
participate in the comparison, or what canonicalization the server performs.
The successful renamed control isolates the problem to the reserved identity and
its additional validation, rather than ordinary namespace support.

The initial schema-report attempt with JSON mode also returned HTTP 400 because
native web search cannot be combined with JSON mode. A plain-text retry succeeded.
Across this follow-up there were 11 API requests: five completed responses, five
reserved-schema rejections, and one JSON-mode compatibility rejection.

## Reproduce

```bash
python3 tasks/responses-tool-result-probe/build_web_tool.py

PYTHONDONTWRITEBYTECODE=1 python3 tasks/responses-tool-result-probe/namespace_probe.py \
  --api-key-file /path/to/authorized-key.txt \
  --out /tmp/web-namespace-check

PYTHONDONTWRITEBYTECODE=1 python3 tasks/responses-tool-result-probe/namespace_probe.py \
  --namespace research_web \
  --api-key-file /path/to/authorized-key.txt \
  --out /tmp/web-namespace-control
```

The first command that calls the API is expected to fail with the captured
schema-match error. The renamed control makes four requests. The script saves a
pending-open state and all request/response artifacts. It can test a different
argument schema with `--parameters /path/to/schema.json`.

The [official function-calling documentation](https://developers.openai.com/api/docs/guides/function-calling#defining-namespaces)
documents the namespace mechanism. The reserved `web.run` behavior above is an
empirical observation; the documentation we found does not specify how to export
or satisfy the server's configured schema.
