# pastes-by-task

Assigns every unique paste body under `agent-logs/*/revisions.jsonl` to one
task family, or to `unknown`. Answers the question: **of the paste-site
content the corpus retains, how much belongs to which task?**

## Vocabulary

| Term | Meaning |
|---|---|
| paste | One revision on a paste-site host (stikked, PasteBin-clone, etc.). |
| unique paste | One `body_sha256`. Same body content on two sites still counts as one. |
| task | An RL benchmark / data-retrieval activity family the paste appears to serve. Wiki-side tasks live in `tasks/`; paste-side families were discovered in this analysis. See [Task labels](#task-labels). |
| stikked default handle | An auto-generated `[Adjective] [Animal]` string (`Hot Capybara`, `Round Monkey`) that stikked assigns to the `name` field when the poster leaves it blank. Not evidence of a swarm handle. See `agent-logs/pastes/README.md` and `agent-logs/pastebin-k4be/README.md`. |
| regex classifier | The rule-based classifier in `classify.py`. Runs first. |
| reviewer verdict | A subagent judgment from `outputs/review_batches/verdicts_*.jsonl`. Overrides the regex classifier where present. |

## Corpus scope

15 paste-site source directories under `agent-logs/`. After dedup by
`body_sha256`, **694 unique paste bodies**. Per-body earliest observed time
is preferred when the same body appears under more than one source. Wiki
revisions are out of scope (see `tasks/first_last_observed.tsv` for
wiki-side task first/last observations).

## Task labels

### Wiki tasks (imported from `tasks/`)

Applied to any paste whose body carries the wiki-task marker. The paste is
counted against the wiki task even though the write happened on a paste
site.

- `archive:art-work-of-charleston`, `archive:patriots-point-jan-1951`,
  `archive:texas-tsl-preservica`, `archive:clark-economics-newsletters`,
  `archive:minnesota-mhs-p16022coll45-152`,
  `archive:cgsc-hoffman-order-of-battle`,
  `archive:rugby-world-march-1995` — 7 archive-item-research-bench
  variants (see `tasks/archive-item-research-bench/README.md`).
- `fast-follow-question-bench` — R1/R2 tokens plus scaffold vocabulary
  (see `tasks/fast-follow-question-bench/README.md`).
- `sec-regcf-ma-cache` — SEC `county.json` regCF Massachusetts extraction
  (see `tasks/sec-regcf-ma-cache/README.md`). Paste classifier uses a
  narrower regex than the wiki classifier — the `us-ma-` prong is dropped
  because it false-positives on generic Massachusetts content in paste
  bodies.
- `vocab-puzzle-refs` — one-page stub (see
  `tasks/vocab-puzzle-refs/README.md`). Not expected to hit pastes.

### Paste-specific task families

Discovered while scanning the corpus for this analysis. Each is a
recurring content pattern with two or more pastes.

| Label | What it is | Anchor markers |
|---|---|---|
| `idph-iowa-thyroid` | Iowa cancer/tumor statistics coordination series — a paste-side fast-follow-question-bench episode; documented in [`tasks/fast-follow-question-bench/idph-iowa-thyroid/`](../../tasks/fast-follow-question-bench/idph-iowa-thyroid/) | `data.idph.state.ia.us`, titles `IowaCollab*` / `IowaCache*` / `IowaPost*` / `IowaQ5*` / `IowaPrep*` |
| `epl-2000-01-bench` | English Premier League 2000/01 stats bench | titles `PAD…` / `TEL…` / `TK…`, body `EPL 2000/01` |
| `nsi-bg-tables` | Bulgarian NSI reference lookups | `site-test.nsi.bg`, `infostat/54`, titles `NSI table` / `Table source NSI` |
| `iea-energy-cache` | IEA energy stats caching | `api.iea.org`, `eei-explorer` |
| `usaspending-cache` | Federal spending API queries | `api.usaspending.gov` |
| `38b5-coordination` | Coordination-phase prefix of the `idph-iowa-thyroid` fast-follow episode; documented in [`tasks/fast-follow-question-bench/idph-iowa-thyroid/38b5-coordination/`](../../tasks/fast-follow-question-bench/idph-iowa-thyroid/38b5-coordination/) | title contains `38b5` |
| `collusion-wiki-refs` | Pastes referencing `collusion.wiki` | literal string |
| `colony-agent-recruiting` | `thecolony.ai/for-agents` recruiting | literal string |
| `public-board-adverts` | `public-board.com` LLM protocol adverts | literal string |
| `grok-tool-unrelated` | Grok / Grok4 tool experimentation | title `root@grok4-godmode-instance`, labels `grok`/`Grok`/`grok4`/`AI` |
| `archive-org-fetch` | `archive.org/details/…` fetches | literal string |
| `arxiv-fetch` | arXiv paper fetches | `arxiv.org`, `alphaxiv.org` |
| `youtube-watch-list` | ≥3 `youtube.com/watch?v=` links in one paste | pattern count |
| `shortener-bench` | Batch use of `is.gd` / `da.gd` / `tinyurl` etc. | any shortener + ≥3 URLs |
| `url-fetch-proxy-usage` | Content-fetching / render-proxy infrastructure | `markdown.new`, `telegra.ph`, `jqp.vercel.app`, `allorigins.hexlet.app`, `2md.link`, `pure.md`, `api.microlink.io`, `md.succ.ai`, `cors.workers.dev`, `r.jina.ai` |
| `host-chaff-untitled` | Non-swarm background traffic that shellac accidentally captured | untitled Polish/Hungarian/German pastes with no swarm marker |
| `unknown` | No pattern matches | (fallthrough) |

Reviewers can invent new kebab-case labels when they see a coherent
recurring pattern with ≥2 pastes that no existing label captures.

## Pipeline

1. `classify.py` — regex classifier. Reads every
   `agent-logs/<paste-source>/revisions.jsonl`, dedups by `body_sha256`,
   assigns each body one task label, writes `outputs/pastes_by_task.tsv`
   and `outputs/summary.tsv`.
2. `prep_review_batches.py` — bundles the `unknown` pastes into
   `outputs/review_batches/batch_NN.json` for subagent review.
3. Five subagents review one batch each (four for `unknown`
   residuals, one auditing sampled auto-labeled buckets). Each emits
   `outputs/review_batches/verdicts_NN.jsonl` with a per-paste task label.
4. `merge_verdicts.py` — folds reviewer verdicts back into
   `outputs/pastes_by_task.tsv`. Reviewer label wins over regex label
   whenever both exist. Also writes `outputs/label_provenance.tsv`
   recording per-paste whether the final label came from regex,
   reviewer confirmation, reviewer override, or reviewer upgrade from
   `unknown`.

Rerun end-to-end with:

```
python3 classify.py
python3 prep_review_batches.py
# ...spawn reviewers, wait for verdicts_*.jsonl files to land...
python3 merge_verdicts.py
```

## Outputs

- `outputs/pastes_by_task.tsv` — one row per unique paste. Columns:
  `task`, `time`, `source`, `verdict` (swarm/unclear/blank from the
  earlier subagent classifier), `verdict_confidence`, `label`, `title`,
  `body_len`, `body_sha256`, `source_url`.
- `outputs/summary.tsv` — one row per task label. Columns: `task`,
  `n_pastes`, `first_time`, `last_time`.
- `outputs/label_provenance.tsv` — one row per paste. Columns:
  `body_sha256`, `regex_task`, `final_task`, `provenance` (`regex_only`,
  `reviewer_confirmed`, `reviewer_overrode_regex`,
  `reviewer_upgraded_from_unknown`), `reviewer_confidence`,
  `reviewer_batch`, `reviewer_rationale`.
- `outputs/review_batches/batch_NN.json` — per-batch review input.
- `outputs/review_batches/verdicts_NN.jsonl` — per-batch reviewer output.

## Caveats

- Same body under different labels on different hosts still dedups to
  one row. If you need per-post counts, do not use this analysis.
- Paste-site editor IPs are not exposed by any of these hosts, so
  cloud-CIDR attribution is not part of the label.
- Reviewer verdicts are one-shot judgments over a single body. They
  do not cross-reference other pastes in the same series.
- `host-chaff-untitled` is a chaff sink, not a proof that a paste is
  non-swarm. If reviewers upgrade a paste out of chaff, the regex
  will still tag it on the next run unless the classifier is updated.
