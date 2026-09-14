# Root and named-agent web hook test

This fixture records hook payloads for separate `web.run` search and open calls made by:

1. the root Codex session;
2. the custom `web_probe_agent` in `../agents/web-probe-agent.toml`.

`raw-hook-events.jsonl` contains the unmodified JSON objects delivered to the hook on stdin.
`summary.jsonl` contains a compact projection of the identity and tool-input fields.

After the recorded run, the active `.codex/hooks.json` manifest is copied here as
`hooks.test.json` and removed from the active location. To rerun the test, copy it back to
`.codex/hooks.json`, clear the two result files, and start a fresh trusted Codex session with
hook trust enabled.
