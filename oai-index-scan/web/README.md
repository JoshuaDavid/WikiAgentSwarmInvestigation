# Luna Search Console

This localhost-only UI accepts one search term per line and runs each term as a
separate `web.run` search using the configured `spider_agent` Luna worker. It
shows responses as they are committed. Search result links are never opened.
An optional domain allowlist (comma- or newline-separated) and recency window in
days can be applied to every term in a submission. The server uses one Luna
worker per submitted term, capped at 10 concurrent workers. Terms are partitioned
between workers and are not replicated.

From the repository root, run:

```bash
python3 oai-index-scan/web/server.py
```

Then open <http://127.0.0.1:8787>. Use `--port 9000` to choose another port.

Workers rotate after 50 calls. Durable state, raw hook responses, logs, and
transcripts use the normal spider locations:

- `oai-index-scan/tmp/spider/web_*/`
- `oai-index-scan/tmp/search-ui/`

The server binds only to `127.0.0.1` by default. Supplying `--host` explicitly
can expose it to other machines and should only be done on a trusted network.
