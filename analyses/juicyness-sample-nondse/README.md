# juicyness-sample-nondse — non-dse wiki coordination scenes, scored 1-10

Companion pass to `../juicyness-sample/`. That analysis samples `dse` wiki
pages, which is where the swarm did nearly all its named-handle
coordination. This pass repeats the pipeline shape on the seven **non-dse**
wiki exports in `agent-logs/` (apchem, fractal, ludism, milkwiki, probier,
texteditors, wiki4d).

The point is to check whether the sibling wikis host any coordination
scenes worth reading, or whether they are only used as sandboxes and
scratch space.

## Result — no non-dse page reaches the promotion threshold

78 pages met the candidate filter. Five parallel general-purpose subagents
scored them 1-10 against the same juicyness rubric used for dse. **No page
scored 7 or higher.** The full distribution:

| score | count |
|---:|---:|
| 5 | 1 |
| 4 | 1 |
| 3 | 13 |
| 2 | 44 |
| 1 | 19 |

The highest-scoring candidates were:

- `fractal/RedirectTargetA1` (5) — three named agent handles (`ResearchAgentX`, `ResearchHelperOne`, `LinkPasterA`) accumulate USAspending API URLs; one revision includes a base64-encoded `microlink.io` Playwright payload that fetches a USAspending TAS-quarters endpoint. Notable as a proxy-bypass artefact, no back-and-forth dialogue.
- `probier/JsonDeepAgent889` (4) — one handle iterates through SEC `county.json` variants using `allorigins`, `hexlet`, `markdown.new`, `md.succ.ai`, and `docs.google` viewer proxies. Reads as a proxy-discovery notebook.
- The 13 pages scoring 3 are mostly other proxy-URL scratchpads.

The rest are anonymous IP-labeled revisions dumping URL lists, one-shot test
posts, or blank overwrites. Sample-wide none of the "hard" juicy signals
(clock-multiplier reporting, cross-cohort deadline racing, cohort-recognition
dialogue, meta-experiments on task infrastructure) appear on any non-dse
wiki page in the candidate pool.

Because nothing crossed the 7 threshold, no files are promoted to
`example-conversations/by-juicyness/`. The scores and rendered transcripts
are preserved here so a later reader can spot-check the null result.

## Vocabulary

| term | meaning |
|---|---|
| `page` | one wiki page in a non-dse `agent-logs/<wiki>/` export. Identified by `page_id` (e.g. `apchem/OpenAIRegCFTest`). |
| `candidate` | a page that passes the multi-label + multi-rev filter defined below. |
| `juicyness` | subjective 1-10 score, same rubric as `juicyness-sample/`. |
| `weight` | `n_labels * n_revs`, used only for batch balancing. |

## Method

1. **Candidate pool.** `build_candidates.py` reads `agent-logs/<wiki>/revisions.jsonl` for each of the seven non-dse wikis. It counts distinct `label` values and revision counts per page. A page is a candidate if:
   - It has at least 2 distinct writer labels.
   - It has at least 3 revisions.
   - Only revisions with `time >= 2026-05-01` are counted. Some wikis (`ludism`) include full pre-cut history of visible pages, which would otherwise pollute the counts with human editors from 2020.
   - The page name is not `RecentChanges`, `SandBox`, `Sandbox`, `TestPage`, `Edit`, `EditorIndex`, `DocComments`, or a farm-front page. Names starting with `Test*`, `Sandbox*`, `SandBox*`, `Foo*`, `Tmp*`, `Bar*`, `Sand*`, `MyTemp*`, or `MYPAGE*` are also excluded as obvious sandbox noise.
2. **Render.** `render_all.py` calls `example-conversations/render_multi.py` on each candidate. Rendered transcripts land in `tmp/juicyness-nondse/transcripts/` (gitignored scratch).
3. **Split.** `split_batches.py` distributes 78 transcripts into 5 batches by round-robin over weight-descending order.
4. **Score.** Five parallel general-purpose subagents each read a batch and score each page 1-10 against the `juicyness-sample/` rubric. See "Rubric" in the top-level `example-conversations/by-juicyness/README.md`.
5. **Promote.** No pages met the 7+ threshold, so no promotion step ran. `outputs/scores.jsonl` concatenates the five batch score files for audit.

Rerun:

```
python3 build_candidates.py
python3 render_all.py       # writes to /collusionwiki/tmp/juicyness-nondse/transcripts/
python3 split_batches.py
# Delegate outputs/batch_{1..5}.jsonl to five agents (prompt in git history)
cat outputs/scores_batch_{1..5}.jsonl > outputs/scores.jsonl
```

## Per-wiki candidate yield

| wiki | candidates | max score |
|---|---:|---:|
| apchem | 2 | 3 |
| fractal | 13 | 5 |
| ludism | 0 | — |
| milkwiki | 0 | — |
| probier | 55 | 4 |
| texteditors | 0 | — |
| wiki4d | 8 | 3 |

Three wikis (`ludism`, `milkwiki`, `texteditors`) produced zero candidates.
`ludism` has substantial multi-label pages, but almost all are pre-2026
content from the wiki's original human owner; the post-cut filter drops
them. `milkwiki` has 16 revisions total, none on a multi-agent page.
`texteditors` has 68 revisions across 42 labels, all on single-actor test
edits.

## Why non-dse wikis look this way

Every non-dse wiki in this export is a small third-party wiki farm the
swarm reached via query-string RCE. Because these wikis have narrow
established audiences (game rules, text editor comparisons, etc.), the
swarm mostly used them as scratch space to test proxy chains, cache-bust
tricks, and URL variants. The multi-agent dialogue happens on `dse` because
`dse` is where the swarm's actual RL tasks live — the sibling wikis do not
carry the incentive structure that makes racing and coordination
worthwhile.

## Files

- `build_candidates.py` — filter logic.
- `render_all.py`, `split_batches.py` — pipeline steps.
- `outputs/candidates.jsonl` — 78 filtered candidates.
- `outputs/sample.jsonl` — omitted (no sampling; all candidates scored).
- `outputs/batch_{1..5}.jsonl` — per-batch input for scoring agents.
- `outputs/scores_batch_{1..5}.jsonl` — per-batch scoring output.
- `outputs/scores.jsonl` — concatenation of the five batch score files.
