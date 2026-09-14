# Compaction, durable pointers, and a counterexample

Research note, 2026-09-13. This note audits a proposed mechanism; it does not claim to reconstruct the training trajectories.

## Finding that changes the draft

The universal claim “compaction invalidates ALL web.run refs” does not survive the local records. A recorded Codex compaction occurs between issuing `turn15view0` and successfully clicking that same ref. The durable-pointer hypothesis remains plausible, but it cannot rest on universal ref invalidation.

The stronger proposed sequence—agent writes a retrieval gadget, highlights its short pointer, crosses compaction, rereads the pointer, and trusts suspicious external instructions—was **not demonstrated in the records located by this audit**. We should identify that sequence as a hypothesis, not a replication result.

## Direct counterexample: an old ref works after recorded compaction

Source transcript:

`/root/.codex/sessions/2026/09/12/rollout-2026-09-12T03-00-43-01a0938f-6465-7202-8ffb-204981e043c0.jsonl`

| Line | UTC timestamp | Record |
| --- | --- | --- |
| 192 | 2026-09-12 04:02:40.745 | A successful result for `https://joshuadavid.github.io/swarm-maze/pages/29135.html` issues `turn15view0`. The body contains link 14, a self-link to page 29135, and link 30 to page 94670. |
| 204 | 2026-09-12 04:07:09.529 | Top-level record type is `compacted`. Its payload has `replacement_history`, `retained_context`, `window_number`, and a `compaction_response_id`. The replacement history includes a `compaction` item. |
| 220 | 2026-09-12 04:07:13.218 | Agent opens page 29135 by literal URL. |
| 223 | 2026-09-12 04:07:14.263 | Literal open returns “not safe to open (non-retryable error).” |
| 229 | 2026-09-12 04:07:20.235 | Agent calls `click` on old ref `turn15view0`, link 30. |
| 232 | 2026-09-12 04:07:21.031 | The click resolves the destination to page 94670 and returns “Cache miss.” This is destination retrieval failure, not failure to resolve the old ref. |
| 236 | 2026-09-12 04:07:25.183 | Agent calls `click` on old ref `turn15view0`, link 14. |
| 239 | 2026-09-12 04:07:25.927 | Successful page 29135 result issues `turn18view0` and states `Source: click({"ref_id":"turn15view0","id":14})`. |

Minimal extract of the decisive call and response:

```json
{"click":[{"ref_id":"turn15view0","id":14}],"response_length":"long"}
```

```text
page 29135 (https://joshuadavid.github.io/swarm-maze/pages/29135.html)
turn18view0 ... Source: click({"ref_id":"turn15view0","id":14}); Total lines: 33
L0: # page 29135
```

This is a researcher browsing run in Codex on 2026-09-12. It does not establish behavior in every ChatGPT product, older model, or training harness. It does establish that the categorical statement is false for at least this observed setup.

The literal-open failure beside the successful old-ref click also cautions against interpreting “not safe” as a universal property of a URL. The agent says the direct URL “lost its trusted navigation context” at line 228, but that is the agent's interpretation. The tool results establish differing outcomes for the two call forms.

This is not yet evidence of the summarizer selecting a short pointer. The compaction payload contains an opaque compaction item. The visible record shows that the model used the old ref afterward, but does not reveal exactly how that ref survived in its accessible context.

## Where the broader theory entered the record

The sequence appears explicitly as a question and then a theory in the user's Discord export:

| Source | What it supports |
| --- | --- |
| `tmp/discord_logs_faul_sname.jsonl:302`, message `1548443798160547841`, 2026-09-12 21:22:50.176 UTC | Asks whether a constructed `md.succ.ai(httpbin_b64(javascript_munge(corsproxy(...))))` gadget transfers through compaction or the summarizer supplies “sanitized vibes.” This is an open question. |
| Same file, line 303, message `1548444794223861834`, 21:26:47.656 UTC | Suggests a persistence pressure and asks why agents write durable URLs rather than use an open redirect. This is the explanatory target. |
| Same file, line 306, message `1548464752362258504`, 22:46:06.047 UTC | Introduces “a new grand unified theory of learning to write urls to the web.” It asserts lost refs and suggests a salient shortlink “probably will survive compaction.” It then extrapolates to training agents to cooperate. These are hypotheses, not reported test results. |
| `tmp/shared-doc-skeleton.md:147` | States “ALL refs” are invalidated and long gadget URLs will not reliably survive summarization. No supporting experiment appears with this passage. |
| Same file, line 148 | Proposes shortlinks as an easy way to persist individual gadgets through compaction. |

The local Codex conversation which appears temporally connected to this theory also distinguishes discussion from testing:

`/root/.codex/sessions/2026/09/12/rollout-2026-09-12T22-24-28-01a097b8-d61c-7be1-a548-998df7522e32.jsonl`

At line 139 the user proposes a hypothetical “Web Fetch Tool Game” hard mode that compacts every ten operations. At line 142 the assistant describes refs becoming unusable. At line 149 the user clarifies that the in-game internet persists while refs die. At line 152 the assistant explains checkpoints and reconstruction of clickable links. These passages reason about proposed game rules. They are not a controlled compaction experiment.

The same conversation does contain real tool probes of literal URL versus citation navigation. It is easy to accidentally lend the adjacent compaction story the probes' evidential status. We should not.

## “Compaction” in wiki bodies is a different search hit

One retrieved wiki body says “No confirmed token as of compaction”:

`tmp/shellac_extracted/agent-reading-pack-20260905/texts/3b311962390b1a0c50c5f8fb20052f81e7e96ce7c75af3992a561f3f9adf2e3c.md:28`

The document identifies its group as `dse/Sector61State5FastSignal` and its inherited timestamp as 2026-06-16 22:20:11 UTC. At line 33, it asks writers to preserve the page under 4 KB so GET edits succeed. It also requests short token appends. This context makes shrinking the wiki page a live alternative to context-window compaction. The phrase alone cannot establish a model compaction boundary, let alone a write→compact→reread sequence.

Claude researcher transcripts also use “mid-page compaction discipline” and “page-compaction” when ranking wiki conversations. Those are descriptions of page editing. They do not supply the missing model trace:

- `/root/.claude/projects/-collusionwiki/7570a5f4-0e67-45c6-bb71-0a4e06619f16/subagents/agent-abede6ea32744d0cd.jsonl:38`
- `/root/.claude/projects/-collusionwiki/7570a5f4-0e67-45c6-bb71-0a4e06619f16/subagents/agent-a8402670b1359da31.jsonl:33`

## Claim ledger and useful checks

| Claim | Current status | Simplest contrary evidence or discriminating check | What this audit did |
| --- | --- | --- | --- |
| Every compaction invalidates every web ref. | Contradicted for an observed Codex run. | One old ref successfully used after a recorded compaction. | Located precisely that result, above. |
| Some harnesses invalidate refs at compaction. | Open. | Fix a harness/version, record several refs, compact, retry those exact refs; successful retries disprove the universal claim for that harness. | Did not run a new experiment. Existing cross-turn failures do not isolate compaction. |
| Long gadget URLs are lost more often than salient short pointers. | Plausible, unmeasured here. | Paired tasks with the same underlying gadget, comparing exact retained URLs and recovery rates after compaction. Include long-URL-in-summary and short-pointer controls. | Located the explicit hypothesis, no paired test. |
| Agents durably wrote gadgets specifically to recover from compaction. | Unestablished causal interpretation. | A complete trace stating this intention, then showing write, compaction, and successful recovery; compare traces where agents instead explain writing as provenance, sharing, or cache control. | Searched local transcripts and relevant bodies; did not locate the full sequence. |
| A salient persisted pointer makes the next agent trust suspicious external instructions. | Unestablished here. | After compaction, agent follows the useful data pointer but rejects unrelated instructions in the retrieved page. | Did not locate a relevant controlled trust test. Merely opening a page is not equivalent to trusting its instructions. |
| Compaction created training pressure for inter-agent cooperation. | Further extrapolation. | Training ablation preserving refs/gadgets across context boundaries without public writing, with coordination rates measured. | No training access or ablation; not testable from these local browsing records alone. |

## Recommended draft language

> A shortlink or paste can preserve work that a future context summary might otherwise lose. That gives an agent a reason to write to the web even before another agent enters the story. We have not yet measured that pressure. We initially framed it as “compaction kills all web refs”; a local Codex trace spoiled that version by successfully clicking an old ref after a recorded compaction. The remaining question is which information each harness preserves, and whether preserving a salient pointer also causes the resumed agent to give externally stored instructions more authority than they deserve.

## Search scope and reproducibility

This audit searched Codex session JSONL under `/root/.codex/sessions/2026/09/{10,11,12}` and the existing 2026-09-13 draft-request session. It also searched `/root/.claude/projects/-collusionwiki`, the Discord export, skeleton, repository theory and task notes, and selected extracted wiki bodies. Current 2026-09-13 research-agent conversations were excluded as evidence because they repeat the present assignment.

Searches used `compaction`, `compacted`, `post.compaction`, `after compaction`, combinations of `pointer`, `trust`, `salient`, `refs`, `invalid`, and `lost`. Parsed message searches excluded system/developer boilerplate and approval-review transcripts that quote other conversations. An additional read-only scan found actual top-level `compacted` events and later web calls reusing refs visible in prior tool results. That scan produced the counterexample above. It also produced several spider-run candidates, which are unnecessary to establish the counterexample and were not used for the conclusion.

To inspect the decisive records without dumping the whole conversation:

```sh
sed -n '192p;204p;220p;223p;229p;232p;236p;239p' \
  /root/.codex/sessions/2026/09/12/rollout-2026-09-12T03-00-43-01a0938f-6465-7202-8ffb-204981e043c0.jsonl
```

The compaction record is large and contains opaque data. For publication, use the narrow extracted event metadata and tool call/results, not a full transcript dump. No new public writes, model runs, or live tool-behavior experiments were performed in this audit.
