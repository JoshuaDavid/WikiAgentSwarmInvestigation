# Historical Codex web-reference experiment

Newest results: [the earliest working standalone build and latest hosted
compaction](FIRST_WORKING_AND_COMPACTION.md). May 31's `0.136.0-alpha.2`
passes the completed web-ref checks; its old compaction endpoint returns 404.
Latest hosted refs fail after compaction and also across a normal new turn.

The [initial standalone implementation attempt](INITIAL_STANDALONE.md) could
not reach its ref checks: today's endpoint rejected the old request for
omitting the now-required `model` field.

Follow-up: the [latest-build comparison](LATEST.md) reproduces the hosted
failures on `0.155.0-alpha.3.10`, while standalone search on that same binary
passes both the cross-agent and tool-round-trip reference checks.

Run on September 14, 2026 against the current hosted service, using official
historical Codex binaries and GPT-5.5. Both historical source trees are checked
out in adjacent worktrees. No historical Codex source was modified or rebuilt.

## Builds

| Build | Git commit | Release published (UTC) | Session-header implementation |
|---|---|---|---|
| `0.129.0-alpha.10` | `28700492972ea27351eac9f466f6bf79d56fac98` | 2026-05-06 07:48:13 | Individual thread ID in `session_id` |
| `0.129.0-alpha.12` | `3e89772c142690de92b8e2d9b3e9fe0dbabc1668` | 2026-05-06 21:40:24 | Shared root session ID plus separate `thread_id` |

Source worktrees:

- `../codex-before-session-id`
- `../codex-after-session-id`

Official release metadata is saved in `0.129.0-alpha.10-release.json` and
`0.129.0-alpha.12-release.json`. Downloads came from the corresponding
`openai/codex` GitHub releases. Both tarballs were checked against the SHA-256
digests supplied by the GitHub release API before executing their binaries.

| Archive | SHA-256 |
|---|---|
| alpha.10 ARM64 Linux musl | `6b8950d4691c295148ad2950d3a37417bdb73f04ef2389d2f3747fc84f862ade` |
| alpha.12 ARM64 Linux musl | `72d8482e0a24b57cef9c353ba1fa01c19c9bc6fd1dd6ae4dbf936c3f1e758160` |

## Cross-agent result

Both builds exposed the model-facing tool as `web.run`, with the familiar
`search_query`, `open`, `click`, `ref_id`, and numeric link `id` argument shapes.
The CLI event stream represents hosted operations as `web_search` items.

The completed cross-agent experiments used standard multi-agent mode and
`fork_context:false`, the no-history equivalent supported by that mode.
The parent searched, passed one search ref to each of two children, waited
for both, and then tried the source page refs and link IDs the children returned.

| Observation | alpha.10 | alpha.12 |
|---|---|---|
| Python child opens parent's `turn0search7` | Invalid ref | Invalid ref |
| Mozilla child opens parent's `turn0search0` | Invalid ref | Invalid ref |
| Python child independently opens `https://www.python.org/` | Success, `turn1view0` | Success, `turn1view0` |
| Mozilla child independently opens `https://www.mozilla.org/` | Success, `turn1view0` | Success, `turn1view0` |
| Parent opens either child's `turn1view0` | Invalid ref | Invalid ref |
| Parent clicks either child's `turn1view0`, link 0 | Invalid arguments | Invalid arguments |

Both children produced the identical reference string for different successful
pages. That is a collision of strings across contexts; we did not observe one
child's page overwriting the other's or being substituted in the parent.

Representative child error:

```text
Unable to resolve open call: open({"ref_id":"turn0search7","lineno":null}) due to invalid ref_id argument
```

Reports and evidence:

- [Before-change report](0.129.0-alpha.10/v1/report.txt)
- [After-change report](0.129.0-alpha.12/v1/report.txt)
- [Before-change extracted events](0.129.0-alpha.10/v1/evidence.json)
- [After-change extracted events](0.129.0-alpha.12/v1/evidence.json)
- [Exact experiment prompt](prompt.txt)

## Reference lifetime within one agent

A separate control opens Python.org, reuses the resulting ref within the hosted
browsing sequence, calls the client-handled `update_plan` tool, and then retries
the original ref and the literal URL. No subagent or compaction is involved.

The first control batched some web operations. Its reports show a successful
baseline click and an invalid-ref error after `update_plan`, with a successful
literal-URL control. Because the baseline open was not displayed separately, a
second control uses exactly one open operation per web call.

The unbatched control completed with identical results in both builds:

| Step | Result |
|---|---|
| Open Python.org URL | Real page, `turn0view0` |
| Open that original `turn0view0` immediately | Real page, `turn1view0` |
| Call `update_plan` | `Plan updated` |
| Open the original `turn0view0` again | Invalid ref; error output itself labeled `turn0view0` |
| Open Python.org URL again | Real page, `turn1view0` |

This demonstrates a lifetime limitation across a client-handled tool round
trip in these hosted runs. The cross-agent failures alone therefore cannot
isolate an agent-boundary effect: references also failed within the same agent
after this round trip. The shared-session-header change was insufficient to
preserve refs in this setup. No compaction occurred in either control.

- [Initial before-change control](0.129.0-alpha.10/continuity/report.txt)
- [Initial after-change control](0.129.0-alpha.12/continuity/report.txt)
- [Unbatched control prompt](continuity-unbatched-prompt.txt)
- [Unbatched before-change report](0.129.0-alpha.10/continuity-unbatched/report.txt)
- [Unbatched after-change report](0.129.0-alpha.12/continuity-unbatched/report.txt)

## Compatibility issues and limits

- The initial experimental multi-agent-v2 attempt on both builds failed to
  deliver the task text to children. Their persisted user messages contained
  only the environment context, and they returned readiness messages. One
  follow-up attempt also failed to deliver the task. These attempts did not
  test cross-agent web refs. They are retained in the version directories'
  top-level reports and logs; the completed experiments are under `v1/`.
- Both clients warned that today's model catalog contains an unsupported
  reasoning enum value, `max`. They nevertheless completed the actual hosted
  web experiments using GPT-5.5. The binaries themselves were not patched.
- The two published builds bracket the session-ID change but also contain
  other changes. This is not a test of two binaries differing in precisely
  one commit.
- The hosted API does not expose its full internal web-tool text through the
  CLI event stream. Exact refs and error text here are the agents' recorded
  observations, retained in parent and child reports. The saved event stream
  and rollouts independently record web actions, actual spawn arguments,
  tool-round-trip ordering, and successful completion of the runs.
- These experiments establish behavior of these old clients against today's
  server. They do not recreate the May 2026 server or prove its historical
  schema or state-retention behavior.

## Reproduction artifacts

`run_probe.py` runs a specified binary, saves CLI JSONL events and the final
report, and records start/end times and exit status. `extract_evidence.py`
extracts relevant parent/child events with source filenames and line numbers,
excluding credential files and instruction catalogs. Each experiment has its
own configuration and session storage; shell tools and apps were disabled and
the sandbox was read-only.

The runs used protected temporary copies of the existing ChatGPT login. Those
copies are removed after the experiments; the original login is unchanged.
To reproduce, authenticate the desired experiment home before calling the
runner. For example, the command used for a completed cross-agent run was:

```sh
python3 run_probe.py 0.129.0-alpha.10 v1
```
