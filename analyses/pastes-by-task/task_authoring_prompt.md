# Task-dir authoring prompt

You are creating one new task directory under `/collusionwiki/tasks/` for a paste-side task family that the `analyses/pastes-by-task/` classifier assigned 10 or more pastes to.

## Inputs you have

- `/collusionwiki/analyses/pastes-by-task/outputs/pastes_by_task.tsv` — per-paste labels. Filter to the rows where `task` == your assigned label. Columns include `body_sha256`, `time`, `source`, `title`, `label`, `source_url`.
- `/collusionwiki/agent-logs/<source>/revisions.jsonl` — where the paste bodies live. Look up bodies by `body_sha256`.
- `/collusionwiki/analyses/pastes-by-task/README.md` — the classifier README with a one-line description of your task family under "Paste-specific task families".
- `/collusionwiki/tasks/archive-item-research-bench/`, `/collusionwiki/tasks/fast-follow-question-bench/`, `/collusionwiki/tasks/sec-regcf-ma-cache/`, `/collusionwiki/tasks/vocab-puzzle-refs/` — reference layouts you must match.
- `/collusionwiki/CLAUDE.md` — prose style guide you must follow.

## Deliverables (create all three)

```
/collusionwiki/tasks/<your-task-label>/
├── README.md
├── extract_evidence.py
└── outputs/
    └── evidence.tsv          (one row per paste, columns you decide)
```

### `README.md` — required sections

Follow `CLAUDE.md` prose rules strictly: active voice, short sentences (≤20 words), one fact per sentence, no decorative words, define jargon before use, vertical lists for >3 items.

1. **Opening paragraph.** What the paste-family is, and who this document is for. Say up front whether it is a swarm-run RL task (like fast-follow-question-bench), a coordinated non-RL activity (like sec-regcf-ma-cache), an infrastructure pattern (like url-fetch-proxy-usage), a chaff bucket (host-chaff-untitled), or an unrelated background pattern (grok-tool-unrelated). Do not over-claim. If unsure, say "unclear" and list what would resolve it.
2. **Vocabulary table** (if any project-invented terms show up). Define each term once.
3. **Where the evidence lives.** List the paste sources involved. Reference `pastes_by_task.tsv`. Give total paste count, distinct source count, time span (first_time → last_time).
4. **Content pattern.** What the pastes contain. Include one full concrete example (see rule 3 of the style guide) — pick a representative paste, quote its title, its label, its source, and a short excerpt of its body (up to 20 lines, redact anything obviously sensitive). Format like:
   ```
   > title:  <exact title>
   > label:  <exact label>
   > source: <source>
   > body (first N lines):
   >   <verbatim excerpt>
   ```
5. **Handles that participated** (top 5-10 with counts). If the labels are almost all `[Adjective] [Animal]` defaults, say so and skip the list.
6. **Time distribution** — describe the burst shape. Point-in-time burst? Steady low rate? Multi-day campaign? Concrete numbers.
7. **Cross-references.** If the task overlaps with a wiki task in `tasks/`, link both directions. If the pastes reference URLs that also appear on wikis, name the wiki page(s).
8. **What is provable / what is not.** Explicitly separate observations from inferences.
9. **Regenerate evidence** — one-line instruction: `python3 extract_evidence.py`.

Length must track complexity. A rich task like `epl-2000-01-bench` may run to a few screens; a probe pattern like `paste-site-probe` may be one screen.

### `extract_evidence.py`

Self-contained Python 3 script. No CLI args required. Behavior:
- Reads `analyses/pastes-by-task/outputs/pastes_by_task.tsv`, filters to `task == <your-label>`.
- For each matched paste, opens the corresponding `agent-logs/<source>/revisions.jsonl` and finds the row by `body_sha256`.
- Writes `outputs/evidence.tsv` with per-paste columns (choose columns useful for this task family — at minimum: `time`, `source`, `source_url`, `label`, `title`, `body_sha256`, `body_len`, and any task-specific fields you extract from the body like `data_range`, `question_asked`, `handle_family`, etc.).
- Print a small summary to stderr (count, distinct labels, distinct sources, first/last time).

The script must be idempotent — running twice produces byte-identical `evidence.tsv`. Sort deterministically.

### `outputs/evidence.tsv`

Product of `extract_evidence.py`. Commit it alongside the script.

## Constraints

- **Do not touch other task directories.** Only create files inside `/collusionwiki/tasks/<your-label>/`.
- **Do not modify** `analyses/pastes-by-task/` or `agent-logs/` — read-only.
- **Do not commit.** The caller will commit after all subagents finish.
- Follow `CLAUDE.md` — this includes: no emojis, do not create files beyond the three listed above, no comments in code unless necessary per the rule.
- Reminder from an earlier finding: on stikked paste sites, `[Adjective] [Animal]` labels (e.g. `Hot Capybara`) are the default auto-generated `name` for untitled anonymous pastes. Do not treat that label shape as evidence of a swarm handle.

## Output

When done, print a short summary (≤150 words): number of pastes examined, what you learned, and any surprises (e.g. two labels merged, one paste didn't fit, a new sub-pattern surfaced).
