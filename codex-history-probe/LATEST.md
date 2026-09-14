# Latest-build comparison: hosted versus standalone web search

Tested September 14, 2026 using the newest published build,
`0.155.0-alpha.3.10` (published September 11 at 15:52:58 UTC), with GPT-5.5,
medium reasoning, cached web access, and the same prompts as the historical
experiments. The latest stable release at the time of the check was `0.154.0`.

The latest hosted path reproduced the failures seen with the May builds.
The standalone path passed the same checks on this latest binary.

| Check | Hosted web search | Standalone web search |
|---|---|---|
| Reopen own ref immediately | Works | Works |
| Reopen original ref after `update_plan` | Invalid ref | Works |
| Child opens parent's search ref | Invalid ref | Works |
| Parent opens/clicks child's page ref | Invalid ref/arguments | Works |
| Children independently open literal URLs | Works | Works |
| Child reference strings | Both produce `turn1view0` for different pages | Distinct prefixes across children |

No compaction occurred. The four completed runs exited successfully and their
turn contexts record `gpt-5.5`. Both cross-agent runs spawned exactly two
children with `fork_context:false` using standard multi-agent mode.

## Manual reproduction: refs across user turns

Here, a new turn means a new user message after the previous reply finishes.
No compaction is needed.

1. Start a fresh hosted-search session:

   ```sh
   codex --disable standalone_web_search -m gpt-5.5 -c 'web_search="cached"'
   ```

2. Send this first message:

   ```text
   Use only web.run. Open https://www.python.org/, then in a separate web call
   reopen the exact turnNviewM ref returned by that first call. Report that
   original ref inside a code block and whether both calls returned real page
   content or an error. Do not replace the ref with a URL. Then stop.
   ```

3. Wait for the reply to finish. Copy the ORIGINAL ref it reports (typically
   turn0view0), replace REF below with it, and send this as a new message:

   ```text
   Your first tool call must use web.run to open REF exactly as written.
   Then, in a separate web call, open https://www.python.org/ as a control.
   Use no other tools. Report whether each call returned real page content
   or an error, including the exact error text. Do not substitute a URL for REF.
   ```

Observed on `0.155.0-alpha.3.10`: both first-turn opens succeeded. In the second
turn, the original ref failed with `invalid ref_id argument`, while the URL
still opened. See the [recorded new-turn result](0.155.0-alpha.3.10/hosted-new-turn-ref/report.json).

For a standalone comparison, repeat in a fresh session with `--enable
standalone_web_search` in place of `--disable standalone_web_search`.

## Controlled configuration difference

The hosted and standalone cross-agent configurations match except for:

```toml
[features]
standalone_web_search = false # hosted run; true for standalone run
```

The continuity tests additionally enable this tool in both configurations:

```toml
[tools.update_plan]
enabled = true
```

The latest build disables `update_plan` by default. Initial continuity runs
stopped after the immediate-ref baseline because the tool was unavailable.
Those incomplete attempts are retained under `hosted-continuity/` and
`standalone-continuity/`. The completed controls are in the `*-continuity-plan/`
directories. Their prompts are otherwise unchanged from the historical
unbatched control.

The saved rollouts confirm that the flag selected different execution paths:
hosted runs contain native `web_search_call` records, while standalone runs
contain function calls with `namespace:"web"`, `name:"run"`, and ordinary
function-call outputs containing the returned page text. The standalone source
routes those calls through `alpha/search`.

## Exact continuity results

| Step | Hosted returned ref/result | Standalone returned ref/result |
|---|---|---|
| Open Python.org URL | `turn0view0`, Python page | `turn0view0`, Python page |
| Open original `turn0view0` | `turn1view0`, Python page | `turn1view0`, Python page |
| Call `update_plan` | `Plan updated` | `Plan updated` |
| Open original `turn0view0` again | `turn0view0`, Internal Error / invalid ref | `turn2view0`, Python page |
| Open Python.org URL again | `turn1view0`, Python page | `turn3view0`, Python page |

The standalone function-call outputs themselves preserve all four successful
page results, including the original ref's successful reuse after the plan
update. Hosted exact refs/errors are the model's recorded observations; the
client's native event stream records the web operations and tool ordering but
does not expose the full internal web-tool text.

## Exact cross-agent results

Hosted:

- Parent supplied Python `turn0search7` and Mozilla `turn0search0`.
- Both children got invalid-ref errors, each labeled `turn0view0`.
- Each child's successful literal-URL control produced `turn1view0`.
- Parent open/click operations on `turn1view0` failed.
- The parent initially batched two opens and two clicks without a visible
  payload, then made separate open and click calls to record the errors. It
  remained within the prompt's four-call allowance after the initial search.

Standalone:

- Parent supplied Python `turn0search11` and Mozilla `turn0search0`.
- Python child opened its transferred ref successfully as `turn1view0`; the
  Mozilla child opened its transferred ref as `turn2view0`.
- Their literal-URL controls returned `turn3view0` and `turn4view0`.
- Both children chose link ID 0 on their transferred-ref pages.
- Parent's two opens and two clicks all succeeded in one call, returning
  `turn5view0` through `turn5view3` for the corresponding Python/Mozilla pages.

The Python search result used `test.python.org/about/website/` rather than the
main homepage in both modes. The independent control used `www.python.org`.
This does not change the identity of the references being transferred.

## Reports, logs, and provenance

- [Hosted cross-agent report](0.155.0-alpha.3.10/hosted-v1/report.txt)
- [Standalone cross-agent report](0.155.0-alpha.3.10/standalone-v1/report.txt)
- [Hosted continuity report](0.155.0-alpha.3.10/hosted-continuity-plan/report.txt)
- [Standalone continuity report](0.155.0-alpha.3.10/standalone-continuity-plan/report.txt)

Each run directory also contains `run.json`, `events.jsonl`, and `evidence.json`.
The latter includes parent and child records with source filenames and line
numbers. Temporary login copies were removed after all runs completed.

Official binary source:
[GitHub release](https://github.com/openai/codex/releases/tag/rust-v0.155.0-alpha.3.10).
The ARM64 Linux musl archive was verified against the GitHub release API's
SHA-256 digest before execution:
`07eb6d88c8b1a17ae49c6ff2888a7b19c4d690fcdb64699e4e24346feac94302`.
The binary reports `codex-cli 0.155.0-alpha.3.10`. The corresponding Git commit
is `f5e8906cd6ccfdd6e6f61c8ce44ea6b1ef1912c0`.

The experiments isolate a hosted-versus-standalone difference on the same
latest binary. They do not determine the server's historical behavior, the
date this difference first arose, or behavior for every model/configuration.
