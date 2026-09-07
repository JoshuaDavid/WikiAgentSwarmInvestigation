# paste-linuxiarz-full-classify

Companion pipeline to `analyses/pastebin-k4be-full-classify/` for the
second-largest paste host in the corpus, `https://paste.linuxiarz.pl`.

## Why the pipeline is different

`paste.linuxiarz.pl` currently blocks anonymous data access. All of
these return non-200 for us:

| Endpoint | Response |
|---|---|
| `/api/random`, `/api/paste/<pid>`, `/api/recent`, `/api/trending`, `/api/langs` | 403 |
| `/lists`, `/lists/<N>` | 404 |
| `/view/<pid>`, `/view/raw/<pid>` | 404 |

The 403 is at the Angie (nginx-fork) layer. The 404 is stikked returning
its "not found" template, and it returns 404 even for pids that were
verifiably live months ago (all 219 shellac-imported linuxiarz pids
tested return 404 today). So we cannot scrape from the live site at all.

We fall back to the Internet Archive Wayback Machine. Wayback's CDX API
lists 370 distinct `paste.linuxiarz.pl/view/<pid>` snapshots, of which
177 overlap the shellac corpus and 193 are new candidates.

## Pipeline

1. `scrape/paste_linuxiarz_wayback.py` (in the `scrape/` tree, not here).
   Enumerates archived pids via CDX, fetches the most recent 200 snapshot
   of `/view/raw/<pid>` and `/view/<pid>` for each. `--skip-known-shellac`
   skips the 219 shellac-known pids to save time. Output:
   `scrape/outputs/paste-linuxiarz/{index.jsonl,bodies.jsonl,manifest.json}`.

2. `prep_batches.py` reads `bodies.jsonl`, packs pids into
   `outputs/batches/batch_{k:02d}.json`, prefixed with 6 calibration
   pastes (4 known-swarm, 2 known-human).

3. Subagents review one batch each. They are explicitly told this host
   holds personal data (WiFi passwords in ESPHome configs, private
   sysadmin snippets, etc) and to lean toward `human` for anything not
   clearly swarm. Verdicts land at
   `outputs/verdicts/verdict_{k:02d}.json`.

4. `write_export.py` merges the 219 shellac pastes with the wayback-only
   `swarm` and `unclear` verdicts into
   `agent-logs/paste-linuxiarz/{revisions,pages,events,labels}.jsonl` +
   `manifest.json` + `SHA256SUMS`.

## Swarm signals specific to this host

- `agent-XXXX` handles (four-hex-digit id), e.g. `agent-8b9c`, `agent-0434`,
  `agent-1944`, `agent-ours0909`. These do not appear on k4be.
- `Iowa*` title series: `IowaCollab`, `IowaTestIgnore`, `IowaPostFinalPing`,
  `IowaAsthmaCountsCache`.
- `research` handle with `ProxyBare`, `ProxyVariants`, `ProxyVariants2`,
  `ProxyVariants3`, `ShortVariants` titles - URL-fetcher proxy probes.
- Bodies naming any of `jqp.vercel.app/api/v0`, `pure.md/`, `md.succ.ai/`,
  `2md.link/is.gd/`, `bullfincher.io/sec-proxy`, `telegra.ph/Test-Link`,
  `CLICKMAYBE`, `URLMARK`.
- Task-clock coordination language (`clock.wait`, `task clock`,
  `container UTC`, `Q1..Q9`, `R1..R9`, cohort names).
- Reply threads on a paste with many child names in the color+animal
  handle family (`Soiled Meerkat`, `Chartreuse Dolphin`, ...).

## Human signals specific to this host

- Handles `gru`, `admin`, `januszspiewa`.
- ESPHome / Home Assistant YAML with `substitutions:`, `wifi:`, `api:`,
  `mqtt:` blocks (often carrying real credentials).
- Personal Bash/Python/C code with no benchmark-task shape.
- Time markers of `3 Years ago`, `4 Years ago`, `6 Years ago` (the swarm
  did not exist yet).

## Files under `outputs/`

- `batches/batch_{k:02d}.json` - subagent inputs.
- `verdicts/verdict_{k:02d}.json` - subagent outputs.
- `batch_manifest.json` - batches produced.
- `skipped_in_corpus.jsonl` - shellac-known pids that bypassed the
  subagents.
- `results.md` (after subagents finish) - human-readable summary.
