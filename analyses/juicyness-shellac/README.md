# juicyness-shellac — shellac-attributed content specimens, scored 1-10

Companion pass to `../juicyness-sample/` and `../juicyness-sample-nondse/`.
Those two analyses score wiki-page **coordination scenes**. The three
shellac-attributed exports (`gems`, `pastes`, `shorteners`) do not fit
that shape:

- `gems` — 7 pages, 12 revisions, 1 label. Package manifests with binary
  attachments. Interesting as artefacts, not conversations.
- `pastes` — 458 pages, 156 labels, ~1 revision per page. One-shot posts
  by many different actors. No dialogue within one paste.
- `shorteners` — 59 pages, 4,285 revisions, 1 label (blank), all null
  timestamps. One shortcut retargeted many times. The interesting unit
  is the URL chain of one shortcut, not a conversation.

This pass adapts the pipeline to specimen scoring instead. Each candidate
is one paste, one shortcut chain, or one gem — scored on how much the
document reveals about swarm technique, infrastructure, intent, or the
incident timeline.

## Vocabulary

| term | meaning |
|---|---|
| `specimen` | one paste, one shortcut retarget-chain, or one gem package version. |
| `page_id` | the specimen identifier (e.g. `pastes/anna-fyi/f282ca7e`, `shorteners/vanderbi-lt/iyg1y`, `gems/tf_drift_handoff_bundle_20260307t015800z`). |
| `artefact interestingness` | subjective 1-10 score. See rubric below. |
| `weight` | for candidate ranking: per-host formula. Gems: `n_revs`. Pastes: `total_body_len`. Shorteners: `n_distinct_bodies * n_revs`. |

## Method

1. **Candidate pool.** `build_candidates.py` reads each host's `revisions.jsonl` and applies per-host filters:
   - `gems`: keep all 7 pages.
   - `pastes`: keep every page whose total body length is at least 100 bytes (drops single-token handoff pastes).
   - `shorteners`: keep every shortcut with at least 3 distinct target URLs (drops one-shot shortcuts and shortcuts whose retargets were all duplicates).
2. **Sample.** `sample.py` caps the pool at **7 gems + 40 pastes + 20 shorteners = 67 specimens** by taking the top-weight rows per host.
3. **Render.** `render_all.py` writes one markdown file per specimen. Renderer varies by host:
   - `gems`: each revision printed in file order, with version and label.
   - `pastes`: each revision printed with label and timestamp.
   - `shorteners`: distinct target URLs printed in first-occurrence order, capped at 100 shown, with a count of any not shown. Timestamps are absent from the export, so there is no time order.
4. **Split.** `split_batches.py` distributes 67 files into 5 batches by round-robin over weight-descending order.
5. **Score.** Five parallel general-purpose subagents each read one batch and score each specimen 1-10 against the artefact-interestingness rubric below.
6. **Promote.** `promote.py` copies each 7+ specimen into `example-conversations/by-juicyness/<score>/`, alongside the dse pages. Host prefixes on filenames (`gems-*`, `pastes-*`, `shorteners-*`) keep them from colliding with `dse-*`. The by-juicyness README is hand-edited to add the shellac subsections.

Rerun:

```
python3 build_candidates.py
python3 sample.py
python3 render_all.py       # writes to /collusionwiki/tmp/juicyness-shellac/transcripts/
python3 split_batches.py
# Delegate outputs/batch_{1..5}.jsonl to five agents (prompt in git history)
cat outputs/scores_batch_{1..5}.jsonl > outputs/scores.jsonl
python3 promote.py
```

## Rubric — artefact interestingness

"How much does this one document reveal about swarm technique, infrastructure, intent, or the incident timeline?"

- **10**: Extraordinary. A complete recipe for a novel exfil / RCE / bypass; explicit cross-swarm handoff protocol; a technique or artefact not documented elsewhere in the corpus.
- **8-9**: Strong artefact. Full proxy-chain example with multiple hops; base64-encoded Playwright / eval payload; explicit task answer values dumped for peers; a shortcut with 100+ distinct proxy targets showing evolving evasion; an ML-related handoff bundle (model weights manifest, drift-repro package).
- **6-7**: Interesting artefact. A single-hop proxy example naming a new intermediary; agent-labelled research reference; a shortcut with 10-100 distinct targets showing meaningful iteration; a research-paper-summary paste attributed to a named agent handle.
- **4-5**: Standard artefact. One URL, standard proxy, one-shot data dump, run-of-the-mill research paste.
- **2-3**: Trivial. Short handoff token, "hello" test, template scaffold with no content.
- **1**: Empty or noise.

## Result

67 specimens scored. 18 hit the 7+ promotion threshold. Full distribution:

| score | count | tier of interest |
|---:|---:|---|
| 9 | 4 | all four are shortener chains with 100+ distinct proxy targets |
| 8 | 5 | shorteners plus one gem (encrypted-tarball handoff) plus one paste (SIBAResearch paper relay) |
| 7 | 9 | mix of shorteners, gems, and agent-labelled pastes |
| 6 | 10 | |
| 5 | 2 | |
| 3 | 1 | |
| 2 | 15 | |
| 1 | 21 | |

The four 9s all belong to the same pattern: one URL shortener retargeted hundreds of times through evolving proxy chains (`allorigins.hexlet.app`, `md.succ.ai`, `jqp.vercel.app`, `da.gd`, `markdown.new`, `pure.md`, `r.jina.ai`) against a single upstream target (usually `sec.gov/files/county.json`), with jq queries and cachebusters refining across iterations. `shorteners/vanderbi-lt/iyg1y` alone contains 2,151 distinct retargets. See `example-conversations/by-juicyness/README.md` for the full promoted list (shellac specimens sit in the same tiers as dse pages).

## Known limitation: pastes candidate weighting is noisy

The pastes weighting (`weight = total_body_len`) is a **poor proxy for incident relevance**. Across the five batches, roughly half of the top-weight paste specimens turned out to be pre-incident real-world content — Ansible playbooks from 2020, Puppet configs from 2023, ESPHome YAML from 2025, UnixBench output on ESXi from 2019, etc. This is consistent with the `shellac-import/README.md` warning that shellac's candidate labelling is "weak candidate, not actor attribution". The shellac reading pack contains real pastes alongside candidate-agent pastes and cannot distinguish them.

For a rerun, a better paste filter would combine body length with at least one incident-window signal: a post-2026-05-01 `time`, an agent-shaped `label` (`agent-*`, `OpenAI*`, `SIBA*`, `padbot`), a URL matching known swarm proxies (`md.succ.ai`, `jqp.vercel.app`, `allorigins`), or a task-specific keyword (`regCF_county`, `PUMS`, `IHME`, task-clock vocabulary). None of these filters is expensive, and any one would push the false-positive rate below 20%.

The shorteners and gems weightings held up: every shortener at 9 or 8 was a genuine artefact, and every gem at 7 or 8 was a genuine artefact.

## Files

- `build_candidates.py`, `sample.py`, `render_all.py`, `split_batches.py`, `promote.py` — pipeline.
- `outputs/candidates.jsonl` — 350 candidates before sampling.
- `outputs/sample.jsonl` — 67 sampled specimens.
- `outputs/batch_{1..5}.jsonl` — per-batch input for scoring agents.
- `outputs/scores_batch_{1..5}.jsonl` — per-batch scoring output.
- `outputs/scores.jsonl` — concatenation.
