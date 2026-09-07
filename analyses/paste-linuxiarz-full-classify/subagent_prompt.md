# Subagent prompt template (linuxiarz)

Each subagent gets one `outputs/batches/batch_{k:02d}.json` file and writes
`outputs/verdicts/verdict_{k:02d}.json`.

---

You are helping triage a scrape of `https://paste.linuxiarz.pl`. We are
investigating an incident in which a fleet of RL-trained agents used
public paste sites (plus wikis and URL shorteners) to coordinate on
benchmark and data-retrieval tasks. Your job: label each paste in one
batch as `swarm`, `unclear`, or `human`.

## Data-handling constraint (important, please read)

The live paste.linuxiarz.pl site currently blocks anon access. This scrape
comes from the Internet Archive Wayback Machine. Some archived pastes
contain personal data - WiFi passwords, ESPHome/Home Assistant configs,
API tokens, private code. These are NOT swarm artefacts. Downstream code
will only publish `swarm` and `unclear` verdicts. Please lean toward
`human` for anything that looks like real personal infrastructure config
or code, so the export does not accidentally re-publish someone's
private content.

Corollary: absence of a swarm tell + presence of infra-config tell =
`human`, high confidence.

## Read these files (in this order)

1. `/collusionwiki/analyses/paste-linuxiarz-full-classify/subagent_prompt.md` -
   this file, in full.
2. `/collusionwiki/analyses/paste-linuxiarz-full-classify/outputs/batches/batch_{BATCH_INDEX}.json` -
   the batch. It has:
   - `calibration`: 6 pastes, 4 known-swarm and 2 known-human. Read all 6
     before starting. Note the `role` field on each.
   - `pastes`: the array to classify. Each has `pid`, `title`, `name`,
     `raw_truncated` (up to 4000 chars), `raw_len`, `ago`, `hits`, `lang`,
     `n_replies`, `reply_names` (names on any child `Re:` posts).

## Swarm tells specific to linuxiarz

- `agent-XXXX` handles (four-hex-digit id) - the linuxiarz swarm's
  canonical form. `agent-8b9c`, `agent-0434`, `agent-1944`, `agent-ours0909`
  etc.
- Title starts with `Iowa*` - `IowaCollab`, `IowaTestIgnore`,
  `IowaPostFinalPing`, `IowaAsthmaCountsCache`. That series is a
  documented swarm task.
- `research` handle with `ProxyBare` / `ProxyVariants` / `ProxyVariants2` /
  `ProxyVariants3` / `ShortVariants` titles - URL-fetcher proxy probes,
  same family as the `Gjavascript99` etc. tests on k4be.
- Bodies containing `jqp.vercel.app/api/v0?url=`, `pure.md/`,
  `md.succ.ai/`, `2md.link/is.gd/`, `bullfincher.io/sec-proxy`,
  `telegra.ph/Test-Link`, `CLICKMAYBE`, `URLMARK`, `FRAMEK4`.
- Task-clock coordination language: `clock.wait`, `task clock`,
  `container UTC`, `shared UTC`, `scaffold clock`, `R1..R9` round labels,
  `Q1..Q9` question labels, cohort names (`MAR13`, `Dec27`, `Aug09`),
  `85 and Older` (a specific bench task).
- `Re:` replies where the reply-author name is a random color+animal like
  `Soiled Meerkat`, `Gentle Gibbon`, `Chartreuse Dolphin` - if the reply
  volume is high (>2) or the reply names are all animal-family, that's
  swarm using the reply chain as a coordination mechanism.
- Structured factual dumps for benchmark tasks (financial 10-Ks, sports
  standings, statistical office data) written in the same shape as the
  k4be `EPL 1995-00` / `Roi Et TH45` calibration set.

## Human tells specific to linuxiarz

- Handles `gru`, `admin`, `januszspiewa`, plus other lowercase Polish
  nicknames.
- ESPHome / Home Assistant YAML configs (`substitutions:`, `wifi:`,
  `mqtt:`, `api:` blocks with credentials).
- Personal Bash / shell aliases, cron files, network configs, systemd
  units.
- Long code in a single language (C, Python, Bash) that solves a specific
  problem, especially embedded / IoT / sysadmin.
- Timestamps `2 Years ago`, `3 Years ago`, `4 Years ago` - the swarm did
  not exist yet. Something dated 2020-2024 is almost never swarm.

## Verdicts

- `swarm` - clear tell above.
- `unclear` - could be swarm, but you cannot match a specific pattern and
  the content is not obviously personal. Small, task-shaped, but no
  proxy URL and no `agent-XXXX` handle. Between `unclear` and `human`,
  choose `human` on this host (see the data-handling constraint).
- `human` - default when in doubt AND the paste looks like real personal
  code or infrastructure.

Return one object per paste with fields `pid`, `verdict`, `confidence`
(`low`/`medium`/`high`), `rationale` (one sentence naming the specific
tell you used). Write the JSON file at
`/collusionwiki/analyses/paste-linuxiarz-full-classify/outputs/verdicts/verdict_{BATCH_INDEX}.json`
with shape:

```json
{
  "batch_index": {BATCH_INDEX},
  "verdicts": [ ... one row per paste, same order as batch.pastes ... ]
}
```

Do not fetch anything from the network, do not modify any other path.
Reply with a one-line summary of swarm / unclear / human counts and any
surprises.
