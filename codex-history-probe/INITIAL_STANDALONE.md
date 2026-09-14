# Attempt to run the initial standalone implementation

Tested on September 14, 2026 with GPT-5.5 and today's search service.

The earliest published build found containing the May 26 standalone extension
is `0.135.0-alpha.1`, published May 27 at 18:34:58 UTC. Its source commit is
`676a2212a7c7260e05f1283d446c11962af87ac3`. The May 26 tags `rust-v0.134.0`
and `rust-v0.134.0-alpha.4` do not contain the introduction commit.

This release contains the original implementation plus two May 26 follow-ups:
the direct-caller restriction and a schema-compaction fix. It precedes the
May 29 fix that sends a model in standalone search requests.

## Observed failure

The original implementation could not complete the first open against today's
service. Its first call was:

```json
{"open":[{"ref_id":"https://www.python.org/"}],"response_length":"short"}
```

The client logged HTTP 400 with this error:

```json
{
  "error": {
    "message": "Missing required parameter: 'model'.",
    "type": "invalid_request_error",
    "param": "model",
    "code": "missing_required_parameter"
  }
}
```

The model saw `aborted` rather than a page reference and stopped the dependent
steps. The CLI process exited 0, which does not indicate that the tool call
succeeded. The continuity experiment therefore did not reach the reference
checks. The cross-agent experiment was not run after this prerequisite failed.

The result matches the source: this release sets `SearchRequest.model` to
`None`, which is omitted from the serialized request. The
[May 29 follow-up](https://github.com/openai/codex/commit/1f93706e994d3f39a9155dff5d41c4141dc67c4c)
states that the endpoint now requires a model and changes the extension to
send the effective model.

This establishes current incompatibility of the initial client implementation.
It does not establish whether it worked against the May 26 server, and it
provides no live result about the initial implementation's ref sharing.

## Artifacts

- [Model's report](0.135.0-alpha.1/standalone-continuity/report.txt)
- [Actual client-side server errors](0.135.0-alpha.1/standalone-continuity/server-errors.txt)
- [Extracted events](0.135.0-alpha.1/standalone-continuity/evidence.json)
- [Run metadata](0.135.0-alpha.1/standalone-continuity/run.json)
- [Official release](https://github.com/openai/codex/releases/tag/rust-v0.135.0-alpha.1)

The official ARM64 Linux musl archive was verified before execution against
the GitHub release API's SHA-256 digest:
`bb1cc31b62f2e71afd1089602187c1a7307d85a803d9512aab82fcf1c8d2cebf`.
The binary reports `codex-cli 0.135.0-alpha.1`. No client code, request payloads,
or server responses were patched. Temporary login copies were removed.
