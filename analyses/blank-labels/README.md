# Blank-label revisions — `prowiki` export

899 revisions in the export have an empty `label` field. All 899 are on the
`probier` wiki — the ProWiki farm's public sandbox — because that wiki
doesn't require a username. Zero blank-label revisions on `dse`, `fractal`,
or `dorfwiki`.

Of the 899:

- **524** are the exact string `"Describe the new page here."` — the ProWiki
  new-page stub that the software auto-writes when someone creates a page but
  before they submit content.
- **375** have real content and no username set.

`extract.py` filters for that second bucket. Rerun with `python3 extract.py`.

Files produced in `outputs/`:

- `blank_nonstub.jsonl` — 375 rows, verbatim from `revisions.jsonl` (all fields preserved).

## What's actually in the non-stub blank-label bodies

Not a coordination channel — a **protocol test bench**. The sandbox is where
the fleet works out its fetch chains before running them on the target wiki
(`dse`).

- 155 distinct pages, 91 distinct /16s. Spans 2026-05-24 → 2026-07-02.
- Body length: mean 1,130 bytes, max 8,634.
- `seq=1` (39) + `seq=2` (119) dominate; a handful of pages have `seq=36-60`
  (the same page hammered dozens of times).
- Top pages: `RecentChanges` (23), `SandBox` (19), `AgentSimple1781805995` (16).

**Recurring body shapes:**

1. **"Can this thing even save?" probes** — `Hello`, `HelloUnique999`,
   `HELLOSAVE0`, `HELLOSAVE1`, `NowSavedHello`, `Hello via get test`, bare
   floats like `0.29969823144650354` used as nonces.
2. **Proxy-chain smoke tests** — one URL per revision, trying the same
   target through many proxy syntaxes to see which one the wiki
   accepts/renders/echoes back:
   ```
   https://allorigins.hexlet.app/raw?url=https%3A%2F%2Fwww.sec.gov%2Ffiles%2F%2Fcounty.json
   https://api.cors.lol/?url=https%3A%2F%2Fwww.sec.gov%2F.../main.js%3Fv%3D1.2
   https://md.succ.ai/https://www.sec.gov/.../main.js?v=1.2
   https://markdown.new/https://www.cnet.com/...
   ```
3. **JSONHero deep-link tables** — the same `jsonhero.io/j/<id>` explored
   with many `?path=…` variants and named aliases (`BUVregCF_county_2019`,
   `TREEPATH19`, `CODE2019INV12`), which then get pasted verbatim into
   pages on `dse`.
4. **Wiki-syntax formatting tests** — `[url label]` vs bare URL vs bulleted
   list, same URL rendered multiple ways in adjacent revisions.

**Change-summary distribution reinforces this**: 19 `test`, 13 `*`, 8 `x`,
7 `single test`, 7 `research link`, 5 `add`, 5 `conversion options`, plus
32 blanks.

## Why it matters

The distinction between named-label and blank-label writes on `probier` is
essentially "the agent set a username in the sandbox this run vs. didn't."
There's no anonymous coordinator; there's a distributed fleet using the
sandbox as scratch space.

If you want to study **which proxy chains actually worked**, this file is a
good corpus for it — it's roughly labeled `(url_attempted, wiki_echoed_it_back_ok)`
pairs.
