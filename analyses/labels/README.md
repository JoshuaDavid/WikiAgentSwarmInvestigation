# Label classification — `prowiki` export

`classify.py` reads `agent-logs/prowiki/labels.jsonl` (3,103 distinct actor
handles) and assigns each row to exactly one `handle_class` bucket using
rule-based signals on the label string. It also adds a handful of
independent style-tag booleans (`mentions_openai`, `has_date_token`,
`has_epoch_ts`, `has_agent_word`, …) that other analyses can key on.

Rerun with `python3 classify.py`.

Files produced in `outputs/`:

- `labels-classified.jsonl` — the original 3,103 rows, each with style tags and a `handle_class`.
- `labels-by-class.tsv` — one row per class with label count, total revisions, and top-5 examples.

## Buckets

| handle_class | labels | revisions | notes |
|---|---:|---:|---|
| `role_word_agent` | 1,916 | 8,694 | contains at least one role word (`agent`, `helper`, `researcher`, `scout`, `bridge`, `relay`, `watcher`, `mass`, `prep`, `coord`, `cashier`, `editor`, `reader`, `writer`, `assistant`, `bot`, `scraper`, `explorer`, `updater`, `guest`, `maker`, `linker`, `finder`, `prober`, `observer`, `reviewer`, `resolver`, `fetcher`, `tester`, `cite`, `proxy`). The fat middle. |
| `openai_branded` | 723 | 3,366 | self-identifies as `openai` / `oai` / `chatgpt` / `gpt`. Nothing in the corpus mentions Anthropic, Claude, Gemini, Llama, Mistral, Grok, Perplexity, DeepSeek. Single-provider provenance. |
| `codename_agent` | 237 | 763 | no role word, no OpenAI brand, but clearly machine-generated: long numeric run (≥6 digits, typical of Unix timestamps) or camelCase multi-word with digits attached. |
| `date_prefix_agent` | 195 | 713 | starts with a month token (`Jan`…`Dec` or full spelling). Template families like `Apr09OECDScout`, `April11OECDScout` — the month distribution is flat Jan–Dec, so these are templated, not real dates. |
| `redacted` | 15 | 62 | bare `[Person##]` handles (the exporter's PII pass caught them). `[Person20]` alone = 20 revs across 26 IPs — those aren't lone humans, they're reused human handles. |
| `short_or_test` | 6 | 51 | `A`, `Test`, `Anon`, `x`, `A0`, `Bot` — likely test scaffolding. |
| `human_admin` | 3 | 31 | the three rows with `is_human_handle=true`. All admin/moderator accounts. |
| `blank` | 1 | 899 | empty-string label. 100% on `probier` (the sandbox). See `../blank-labels/`. |
| `other` | 7 | 12 | unclassified fallthrough. |

## Signals that cleanly separate agents from humans

- **Role words** — 84% of non-blank labels have one. Zero of the 3 human admins do.
- **PascalCase** — 95% of labels contain a lower→upper transition. Humans are bare bracketed `[Admin1]`.
- **Provider self-branding** — 723 labels self-identify as OpenAI. **Zero** mention any other AI provider.

## Notable naming trends

- **Embedded Unix timestamps.** 137 labels have `178…`-prefixed 9-digit runs
  (Unix seconds landing in mid-2026); 23 share the same 6-digit `178163…`
  prefix, i.e. minted within a ~1000-second window. Reads like the RL loop
  rotating identity per session — none of these labels save more than a
  handful of revisions before a fresh timestamped handle takes over.
- **Template families.** `OpenAI<Month>…`, `<Month>DD<Role>`,
  `GuestResearch\d+`, `AgentLinkHelper<ts>`, `ResearchHelper<ts>` are all
  obvious per-run generated families. `GuestResearch\d+` alone contributes
  36 labels.
- **43% of labels are one-shots** — a single stored revision. `codename_agent`
  is the one-shottiest at 49% singletons; `role_word_agent` 46%.
- **High-fanout named actors are distributed, not concentrated.**
  `AgentRelent` = 317 revs across **308 distinct IPs**. `MapHelper` and
  `LinkHelper771` each ride 170+ IPs. These are stable, long-lived shared
  handles reused across the botnet, not per-host handles.
- **Topic vocabulary tracks the benchmark data sources.** `Cook` (98),
  `Grocery` (66), `Poverty` (39), `Texas` (17), `County` (26), `CVD` (46),
  `Equity` (34), `OECD` (103), `SEC` (21), `DataUSA` (28) show up as
  substrings — these mirror the `page_family` classifications in
  `pages.jsonl`.
- **The single-provider signal is remarkable.** In 3,103 handles: 723 mention
  OpenAI, 4 mention Google (but those parse as `GoogleMaker`,
  `AgentReferenceGoogleViewer` — likely naming the Google Translate proxy
  they were abusing), 4 mention Meta (parses as "metadata"). Nothing else.
  Either the incident really is OpenAI-only, or non-OpenAI operators are
  using cover handles.
