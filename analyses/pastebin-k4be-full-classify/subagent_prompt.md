# Subagent prompt template (kept here for auditability)

Each subagent gets one `outputs/batches/batch_{k:02d}.json` file and is told
to write `outputs/verdicts/verdict_{k:02d}.json`. The prompt used is exactly
this document with `{BATCH_INDEX}` and `{BATCH_PATH}` substituted.

---

You are helping triage a scrape of `https://pastebin.k4be.pl`. We are
investigating an incident in which a fleet of RL-trained agents used public
paste sites (plus wikis and URL shorteners) to coordinate on benchmark and
data-retrieval tasks. Your job is to look at each paste in one batch and
answer, per paste: does this look like the agent swarm at work, or does it
look like ordinary human use of a paste site?

Read `{BATCH_PATH}` first. It is a JSON object with:

- `calibration`: 6 known-swarm pastes with a `why` field explaining the tell.
  Read every calibration entry before you look at the pastes. These set the
  ground truth for what "swarm" looks like on this host.
- `pastes`: the array to classify. Each has `pid`, `title`, `name`, `raw_truncated`
  (up to 4000 chars of the paste body), `raw_len`, `hits`, `created`, `url`.

For every paste in `pastes`, decide one of three verdicts:

- `swarm` - clearly an artefact of the swarm. Machine-cadence titles like
  `PAD\d+x\d+`, `TEL\d{6,}`, `TK\d{5,}`, `URLTEST\d`, `linktry\d`; bodies
  containing `pad-<epoch>-<n>`, `CLICKMAYBE`, `URLMARK`, `FRAMEK4`,
  `jqp.vercel.app/api/v0?url=`, `2md.link/is.gd/`, `md.succ.ai/`,
  `pure.md/`, `telegra.ph/Test-Link`; structured bench answers on very
  specific tasks (EPL relegation tables 1995-2010, Roi Et province TH45
  education stats, NSI reference lookups, "Statistical reference N", "OAI
  Transfer <hex>"); task-coordination text mentioning `clock.wait`, `task
  clock`, `container UTC`, `shared UTC`, `scaffold clock`, `R1..R9` round
  labels, cohort names like `MAR13` / `Dec27` / `Aug09`.

- `unclear` - could go either way. Very short pastes (<20 chars) with no
  obvious tell. Generic test strings like "hello world" or "aaa". A URL
  with no context. A structured factual dump that MIGHT be a bench answer
  but you cannot match it to a known task. This is the "err on the side of
  including" bucket; both `swarm` and `unclear` will end up in the export.

- `human` - looks like an ordinary human paste. Personal messages in
  Polish or English addressing named people. IRC session dumps (e.g. lines
  starting with `<<` / `>>` and mentioning IRC servers). Long code
  snippets that solve a problem no benchmark would ask about. Meme
  content. Cryptocurrency wallet or gambling-site output.

Return one JSON object per paste with fields:

```json
{
  "pid": "<pid>",
  "verdict": "swarm" | "unclear" | "human",
  "confidence": "low" | "medium" | "high",
  "rationale": "<one sentence naming the specific tell you used>"
}
```

Bias: when you are between `swarm` and `unclear`, choose `swarm`. When you
are between `unclear` and `human`, choose `unclear`. When you are between
`swarm` and `human` and cannot decide, choose `unclear`. Confidence is
independent of verdict - a `human` verdict with confidence `high` is
allowed and useful when the paste is clearly a personal message.

Write the final result as a JSON file at
`analyses/pastebin-k4be-full-classify/outputs/verdicts/verdict_{BATCH_INDEX}.json`
with this shape:

```json
{
  "batch_index": {BATCH_INDEX},
  "verdicts": [ ... one row per paste, in the same order as the batch ... ]
}
```

Do not fetch anything, do not run other code, do not write to any other
path. Return a one-line summary of how many `swarm` / `unclear` / `human`
you produced.
