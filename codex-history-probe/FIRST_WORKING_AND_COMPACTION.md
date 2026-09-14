# Earliest working standalone build and latest hosted compaction

Tested September 14, 2026 using GPT-5.5, cached web search, official unmodified
Codex binaries, and today's service. These results do not reconstruct the
historical server.

## Earliest published compatible standalone build found

**`0.136.0-alpha.2`, published May 31, 2026 at 19:40:07 UTC**, is the first
published tag found containing the
[May 29 required-model fix](https://github.com/openai/codex/commit/1f93706e994d3f39a9155dff5d41c4141dc67c4c).
Its source commit is `4eac96bb3e1e35fa99242b44eb87494750dc0f7a`.
The official [release](https://github.com/openai/codex/releases/tag/rust-v0.136.0-alpha.2)
metadata is retained in [the release JSON](0.136.0-alpha.2-release.json).

The May 27 initial standalone release was rejected by today's endpoint for
omitting `model`; see [that attempt](INITIAL_STANDALONE.md). The May 31 binary
includes the fix and successfully uses `alpha/search`. It still uses the older
encrypted-output implementation: the subsequent plaintext-output change was
not necessary for these tests to work.

The ARM64 Linux musl archive was verified against the release API digest before
execution: `d50ea0b63538c1564de3e2470e124c8b6bc382dd39be41988e4f745ca11a41aa`.
Tag ancestry was checked using `git for-each-ref --contains=1f93706e994d3f39a9155dff5d41c4141dc67c4c --sort=creatordate refs/tags/rust-v*`.

| Check on May 31 standalone build | Result |
|---|---|
| Search returns usable result refs | Passed |
| Open a literal URL | Passed |
| Immediately reopen the original ref in a separate call | Passed |
| Reopen the original ref after `update_plan` | Passed |
| Fresh Python child opens parent search ref | Passed |
| Fresh Mozilla child opens parent search ref | Passed |
| Parent opens both children's page refs | Passed |
| Parent clicks the first numbered link from each child page | Passed |
| Child ref strings remain distinct | Passed |
| Original ref survives a normal new user turn | Passed |
| Original ref survives forced compaction | Not established: compaction itself returned HTTP 404 |

This is a finite reference-lifetime suite, not comprehensive coverage of every
web operation, cold resume, or every model/configuration.

### Exact transfer chain

The two children used `multi_agent_v1.spawn_agent` with `fork_context:false`.
Their first web calls opened the supplied refs before trying literal URLs.

| Branch | Parent search ref | Child open result | Child URL control | Parent reopen | Parent click, link 0 |
|---|---|---|---|---|---|
| Python | `turn0search11` | `turn1view0` | `turn2view0` | `turn5view0` | `turn6view0` |
| Mozilla | `turn0search0` | `turn3view0` | `turn4view0` | `turn5view1` | `turn6view1` |

Python's source page was `https://test.python.org/about/website/` (the actual
returned Python-domain search result), and its first link was `▼ Close`.
Mozilla's was `https://www.mozilla.org/en-US/products/`, with first link
`Products`. Both link-0 clicks returned their respective source pages. Thus
these clicks establish successful resolution of the child refs and link IDs;
they do not test navigation to different destinations.

The model additionally discovered the spawn tool via `tool_search`. The parent
batched the two reopens together, then the two clicks together. Exact calls,
spawn arguments, child reports, and outputs are retained below.

- [Cross-agent report](0.136.0-alpha.2/standalone-v1/report.txt)
- [Cross-agent evidence](0.136.0-alpha.2/standalone-v1/evidence.json)
- [Unbatched continuity report](0.136.0-alpha.2/standalone-continuity/report.txt)
- [Unbatched continuity evidence](0.136.0-alpha.2/standalone-continuity/evidence.json)
- [Normal new-turn report](0.136.0-alpha.2/standalone-new-turn/report.json)
- [Normal new-turn evidence](0.136.0-alpha.2/standalone-new-turn/evidence.json)

### May 31 compaction limitation

The baseline URL open and immediate ref reopen succeeded. Calling the real
app-server endpoint `thread/compact/start` then produced:

```text
Error running remote compact task: unexpected status 404 Not Found: {"detail":"Not Found"}, url: https://chatgpt.com/backend-api/codex/responses/compact
```

The app server reported a failed turn; no completed compaction or subsequent
ref probe occurred. This is a compatibility failure of the old compaction
path against today's service, not an observed failure of the web ref registry.
The initial harness waited for a compaction completion until its timeout;
the saved server error identifies the actual preceding failure.

- [Compaction server error](0.136.0-alpha.2/standalone-compact/compaction-error.json)
- [Compaction attempt evidence](0.136.0-alpha.2/standalone-compact/evidence.json)
- [Full app-server transcript](0.136.0-alpha.2/standalone-compact/server-events.jsonl)

## Latest hosted refs after compaction

The latest published binary tested was **`0.155.0-alpha.3.10`**, published
September 11, 2026 at 15:52:58 UTC, commit
`f5e8906cd6ccfdd6e6f61c8ce44ea6b1ef1912c0`.
`features.standalone_web_search=false` selected hosted mode. Persisted
`web_search_call` items independently confirm use of the hosted path.

Two fresh app-server sessions first opened Python.org and immediately reopened
the returned `turn0view0`. Both baselines succeeded. In the compaction session,
the harness invoked `thread/compact/start` and waited for both a completed
`contextCompaction` item and its completed turn. The rollout additionally
contains a `compacted` record with two replacement-history items. The control
session simply started another user turn without compaction.

Here, "new user turn" means a new user message after the preceding agent reply
finished, started through app-server `turn/start`. Consecutive tool calls do
not necessarily cross that boundary. A client-handled tool such as
`update_plan` creates a separate API-request boundary within the same user
turn; hosted web operations can execute consecutively within one request.
The `turnN` prefix in web refs is a separate web-operation counter, not a
count of user messages.

Both follow-up prompts explicitly supplied the original `turn0view0`, requiring
the first tool call to open that token. This tests ref resolution without
depending on whether the model remembers the ref after compaction. A separate
literal-URL open followed as a control.

| Latest hosted test | Immediate original-ref reopen | Original-ref reopen after boundary | Literal URL afterward |
|---|---|---|---|
| Forced compaction, then next user turn | Succeeded | Failed: invalid ref | Succeeded |
| Next user turn only, no compaction | Succeeded | Failed: invalid ref | Succeeded |

The error reported in both sessions was:

```text
Internal Error: Unable to resolve open call: open({"ref_id":"turn0view0","lineno":null}) due to invalid ref_id argument
```

**The ref did not survive the tested compaction sequence. However, it also
failed across an ordinary new-turn boundary, so this experiment cannot isolate
compaction as the cause.** This agrees with the earlier latest-hosted
`update_plan` result documented in [the same-binary comparison](LATEST.md).

- [Completed compaction and ref result](0.155.0-alpha.3.10/hosted-compact-ref/report.json)
- [Compaction evidence, including persisted compacted record](0.155.0-alpha.3.10/hosted-compact-ref/evidence.json)
- [No-compaction control result](0.155.0-alpha.3.10/hosted-new-turn-ref/report.json)
- [No-compaction control evidence](0.155.0-alpha.3.10/hosted-new-turn-ref/evidence.json)
- [Compaction harness](compaction_probe.py)

### Reporting limitation and corrected attempts

The first hosted attempts, in `hosted-compact/` and `hosted-new-turn/`, returned
literal URLs in the structured report's reference fields, even though the
report prose referred to `turn0view0`. Feeding those fields into the next turn
therefore tested URL opens rather than ref reuse. Those attempts are retained
and explicitly marked `protocol_valid:false` in their run metadata; their
successful opens are not counted as ref-survival evidence.

The corrected `*-ref/` attempts separately requested the observed integer
components of the original ref. The harness reconstructed `turn0view0` from
those components, checked its format, and explicitly supplied that token to
the next turn. Bare ref strings in some successful hosted report fields still
arrived as URLs. The hosted API does not expose the complete internal web
tool payload, so the exact internal ref strings and error text rely on the
model's recorded observations; the independent event stream confirms the
operation sequence and successful compaction.

Each experiment used isolated session storage and a protected temporary copy
of the existing login. Temporary login copies were removed after completion.
Shell tools and apps were disabled; no source code or endpoint requests were
patched to make either historical binary compatible.
