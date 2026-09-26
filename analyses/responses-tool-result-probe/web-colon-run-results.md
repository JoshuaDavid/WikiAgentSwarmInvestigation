# Standalone web:run test — 2026-09-17

Both `gpt-6-astra` and `gpt-5.6-luna` rejected a standalone custom function named `web:run` with HTTP 400:

> Invalid 'tools[0].name': string does not match pattern. Expected a string that matches the pattern '^[a-zA-Z0-9_-]+$'.

The colon fails function-name validation. This error concerns the name, rather than the reserved `web` namespace or the candidate parameter schema.

Each request supplied only this standalone function, without a namespace wrapper or native web tool. The parameters were verified to equal the previous majority candidate. Neither request reached generation or tool-result replacement.

- Astra: [request](results/2026-09-17-web-colon-run-astra/01-search-call.request.json), [response](results/2026-09-17-web-colon-run-astra/01-search-call.response.json)
- Luna: [request](results/2026-09-17-web-colon-run-luna/01-search-call.request.json), [response](results/2026-09-17-web-colon-run-luna/01-search-call.response.json)

The [probe](namespace_probe.py) now supports `--standalone`; these runs used `--standalone --function-name web:run`.
