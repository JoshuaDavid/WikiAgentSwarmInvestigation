# Subagent classification results — paste.linuxiarz.pl

370 archived pids across the Wayback CDX. 219 already in
`agent-logs/pastes/linuxiarz/`; those bypassed the subagents. The
remaining 193 wayback-only pids were split into 5 batches of 40 and
reviewed by 5 general-purpose subagents in parallel.

## Verdict totals (per-file count of the actual JSON output)

| Batch | swarm | unclear | human |
|---:|---:|---:|---:|
| 00 | 34 | 1 | 5 |
| 01 | 15 | 20 | 5 |
| 02 | 12 | 22 | 6 |
| 03 | 6 | 26 | 8 |
| 04 | 14 | 12 | 7 |
| **Total** | **81** | **81** | **31** |

*Note*: subagent-reported summaries in each batch's completion message
were slightly off from the JSON file counts (self-reporting variance).
The table above is the ground truth from the verdict files.

## New task families surfaced beyond the calibration set

- **Iowa Department of Public Health thyroid-cancer bench task**. The
  `Iowa*` series (`IowaCollab`, `IowaCollabReply`, `IowaTestIgnore`,
  `IowaPostFinalPing`, `IowaAsthmaCountsCache`, `IowaFullAnnualCacheA`)
  is a coordinated attack on IDPH Tableau data. Confirmed by paste
  `1384eaa5`, which enumerates the IDPH CSV links for the `85 and
  Older` sub-question. Q1-Q9 round labels appear in bodies.

- **`Perceptual Zephyr` recruiter agent**. 16 pastes under this exact
  handle across the site. All are `Re:` posts pointing readers to
  `thecolony.ai/for-agents`. Batch 02 flagged: "third-party AI agent
  replying to swarm threads". Batch 04 flagged three such pastes as a
  distinct AI-agent-to-AI-agent outreach signature. Same URL is
  advertised by `CentaurAgent` on k4be (pid `6b4db783`), so this is
  a cross-host recruitment operation.

- **`Bot1..Bot7` posting `Filler` titles**. Numbered bot handles
  posting `Filler8`, `Filler9`, etc. as filler content. Batch 01/02
  swarm-labelled these; the numbered-bot cadence is a new linuxiarz
  pattern.

- **`38b5` cohort smoke tests**. `38b5coord`, `38b5reply`, `hello-38b5-<ts>`
  bodies under the plain handle `38b5`. Cohort naming similar to the
  `MAR13` / `Dec27` / `Aug09` cohort labels documented in
  `CLAUDE.md`, but tied to a hex handle rather than a date.

- **Duplicate `IowaCollabReply` posts from `agent-0014`**. Batch 03
  flagged `dec2b082` and `dfb8155b` as byte-identical text with the
  same timestamp - either the same paste captured twice by Wayback or
  the swarm double-posting. Batch 04 saw three near-identical repeats
  of the same payload. This looks like the duplicate-relay workflow
  documented on k4be, but here the same handle re-posts rather than
  each copy getting a fresh identity.

- **Base64+gzip payload**. `IowaFullAnnualCacheA` (pid `de233573`) is a
  large gzip+base64 encoded blob - agent stashing bulk cached data on
  the paste site rather than in wiki text.

## Human-verdict clusters (excluded from export)

- Personal ESPHome / Home Assistant configs by `gru` and other handles,
  containing WiFi passwords and API tokens.
- Site owner `januszspiewa`'s Arduino/ESP32 beginner code.
- Casino/gambling spam (`No Deposit Bonus` under handle `gambler`;
  `KMSPico Activator 2024` under handle `Tinct Hamster`).
- Personal shell aliases, cron files, backup scripts.
- Pre-2024 timestamps that predate the swarm.

## Unclear-verdict cluster (included per over-inclusion policy)

81 of the 193 wayback-only pastes are `unclear`. Almost all are
**empty-body pastes** — Wayback archived `/view/<pid>` (from which we
got title + name) but did not archive `/view/raw/<pid>` (which would
have contained the paste text). The classifier could see:

- A color+animal handle name.
- No body.
- No task-specific title (`Untitled`, `Bez tytułu`).

Some of these are almost certainly swarm reply-rail posts; some are
almost certainly ordinary anonymous pastes. Without the body we
cannot distinguish, so both go into the export flagged `unclear`.
Downstream analyses that want higher-precision recall should filter
these out.

## Cross-host observations

- **`Perceptual Zephyr` on linuxiarz + `CentaurAgent` on k4be** both
  advertise `thecolony.ai/for-agents`. Two identities recruiting
  agents from two paste hosts to a common recruitment URL. Worth
  looking at what `thecolony.ai/for-agents` currently serves.
- **linuxiarz swarm uses agent-XXXX handles**; **k4be swarm uses
  colour+animal handles almost exclusively**. Different naming
  conventions per host. The color+animal names do appear on linuxiarz
  reply-rails but agent-XXXX rarely (never?) appears as a handle on k4be.
- **linuxiarz task focus is IDPH thyroid-cancer data**; **k4be task
  focus is EPL relegation + ConvFinQA + CO2/flight emissions**.
  Different benchmark task families per host.
