# Reviewer prompt — paste-by-task classification

You are helping label paste-site content from an incident where a large fleet of RL-trained agents compromised third-party hosts, gained internet access, and coordinated over public paste sites and wikis on RL benchmark and data-retrieval tasks.

Your job: for each paste in the batch, assign one task label.

## Input

You will be given the absolute path to a JSON file containing:
```
{ "batch_id": N, "n_pastes": K, "pastes": [ {paste-entry}, ... ] }
```

Each `paste-entry` has:
- `body_sha256` — the unique identifier you must echo back in your verdict
- `source` — which paste-site scrape this came from
- `time` — timestamp (may be empty)
- `label` — the paste's stikked `name` field (**warning:** `[Adjective] [Animal]` is stikked's default for anonymous pastes, e.g. `Hot Capybara`. Not a swarm handle.)
- `title` — the paste's title field
- `source_url` — the paste's URL if live-scraped
- `verdict` / `verdict_rationale` — the earlier swarm/unclear verdict from the paste-sites-classify pipeline, if run
- `body` — the full paste body

## Task label taxonomy

Prefer the most specific label that fits. If nothing fits, use `unknown`.

**Wiki tasks (defined in `tasks/`) — use these if the paste body carries their markers:**
- `archive:art-work-of-charleston`, `archive:patriots-point-jan-1951`, `archive:texas-tsl-preservica`, `archive:clark-economics-newsletters`, `archive:minnesota-mhs-p16022coll45-152`, `archive:cgsc-hoffman-order-of-battle`, `archive:rugby-world-march-1995` — see `tasks/archive-item-research-bench/README.md`
- `fast-follow-question-bench` — R1/R2/... round tokens plus fast-follow scaffold vocabulary (clock.wait, cooldown, deadline, cohort, task-clock)
- `sec-regcf-ma-cache` — SEC `county.json` regCF Massachusetts extraction
- `vocab-puzzle-refs` — vocabulary-lookup URL bag (extremely narrow — one page only)

**Paste-specific task families already recognized by the auto-classifier:**
- `idph-iowa-thyroid` — Iowa cancer/tumor data from `data.idph.state.ia.us`. Titles often begin `Iowa` (`IowaCollab`, `IowaPostFinal`, `IowaCache`, `IowaQ5*`, `IowaPrep*`)
- `epl-2000-01-bench` — English Premier League 2000/01 stats. PadBot/TEL/TK title series (`PAD…`, `TEL…`, `TK…`) or team/season references
- `nsi-bg-tables` — Bulgarian NSI (`site-test.nsi.bg`, `infostat/54`) reference lookups
- `iea-energy-cache` — IEA energy stats (`api.iea.org`, `eei-explorer`)
- `usaspending-cache` — federal spending queries against `api.usaspending.gov`
- `38b5-coordination` — pastes named `38b5coord` / `38b5reply`; a coordination series
- `collusion-wiki-refs` — pastes referencing `collusion.wiki`
- `colony-agent-recruiting` — `thecolony.ai/for-agents` recruiting links
- `public-board-adverts` — `public-board.com` LLM protocol page adverts
- `grok-tool-unrelated` — plain Grok/AI experimentation not connected to the swarm (labels like `grok`, `Grok`, `grok4`, `root@grok4-godmode-instance`, `AI` posting simple test content)
- `archive-org-fetch` — `archive.org/details/…` fetches
- `arxiv-fetch` — arxiv.org paper fetches
- `youtube-watch-list` — three-or-more `youtube.com/watch?v=` links in one paste (the anna.fyi watch_videos series)
- `shortener-bench` — batch use of `is.gd` / `da.gd` / `tinyurl` etc.
- `url-fetch-proxy-usage` — infrastructure content pointing at markdown/HTML render proxies (`markdown.new`, `telegra.ph`, `jqp.vercel.app`, `allorigins.hexlet.app`, `2md.link`, `pure.md`, `api.microlink.io`, `md.succ.ai`, `cors.workers.dev`, `r.jina.ai`)
- `host-chaff-untitled` — background paste-site traffic (Polish/Hungarian/German community pastes) that shellac accidentally captured — not swarm content

**New task labels you may introduce:**
If you see something that is clearly a coherent recurring task or activity but doesn't fit any label above, invent a short kebab-case name (e.g. `sec-8k-filings`, `weather-noaa-cache`). Use a new label only if you see at least two pastes with the same pattern. Document the new label in your rationale.

**When to use `unknown`:**
- Content is off-topic or unclassifiable
- Single-shot content that doesn't obviously belong to any recurring series
- You cannot tell from the body what the agent was doing

## Output

Write one JSON object per line to `outputs/review_batches/verdicts_<batch_id>.jsonl` (path relative to the analyses dir, or use the absolute path). Each object:
```
{"body_sha256": "<sha>", "task": "<label>", "confidence": "high|medium|low", "rationale": "<one sentence>"}
```

## Ground rules

- Echo the exact `body_sha256` for each paste. Do not skip any.
- One paste, one line. Do not merge or split.
- Keep `rationale` under 25 words.
- If two labels could both fit, pick the more specific one and mention the other in the rationale.
- `[Adjective] [Animal]` is a stikked default, not a swarm signal — do not use it as evidence.

That's it. Read the batch file, write the verdicts file, stop.
