# Custom web.tool test — 2026-09-17

Both `gpt-6-astra` and `gpt-5.6-luna` rejected a custom function named `tool` in the `web` namespace with HTTP 400:

> Invalid Value: 'tools'. Function 'web.tool' is not allowed in reserved namespace 'web'.

The requests used the same majority parameter schema as the previous `web.run` test, with native web disabled. Each saved request was verified to match its previous model's request exactly except for changing the function name from `run` to `tool`. Neither request reached generation, search, open, or tool-result replacement.

This differs from the `web.run` error, which says its schema must match the configured schema. For `web.tool`, the error identifies the namespace as reserved and the function as disallowed. It does not provide an accepted `web.run` schema.

- Astra: [request](results/2026-09-17-web-tool-astra/01-search-call.request.json), [response](results/2026-09-17-web-tool-astra/01-search-call.response.json)
- Luna: [request](results/2026-09-17-web-tool-luna/01-search-call.request.json), [response](results/2026-09-17-web-tool-luna/01-search-call.response.json)

The [probe script](namespace_probe.py) now accepts `--function-name`, defaulting to `run`. The tested invocation used `--function-name tool` and the [majority parameters](results/2026-09-16-majority-schema/parameters.json).
