# agent-graph — from/to message graph and connected components

Every wiki revision is a message: the writer's `label` is the "from" address,
and any other known agent handle mentioned in the body is a "to" address.
This directory scans every wiki export under `../../agent-logs/*/`, expands
each addressed revision into one row per `(from, to)` pair, aggregates to
unique directed edges, and finds undirected connected components.

Rerun with `python3 extract.py && python3 plot.py`.

## Vocabulary

| term | meaning |
|---|---|
| `handle` | an agent's wiki `label`. Blank labels are excluded from this analysis. |
| `pair` / `message` | one `(from, to, wiki, page, rev_id, time)` tuple. One revision that mentions three other handles produces three pairs. |
| `edge` | one unique `(from, to)` with a message count (may aggregate many pairs). |
| `component` | undirected connected component in the graph of edges. |
| `handle set` | union of all labels across every wiki's `labels.jsonl`, filtered to `len ≥ 6`, non-blank, and not the pre-redacted `[Admin##]` / `[Person##]` / `[User##]` handles. |

## Corpus

Ten exports under `../../agent-logs/`. Several overlap on the same underlying
wiki (`prowiki/` bundles `dse`/`probier`/`fractal`/`dorfwiki`, and each of
those wikis also has a standalone scrape). `extract.py` deduplicates by
`rev_id` and prefers the body-bearing row for each rev; standalone `dse/`
carries only metadata, so `prowiki`'s dse rows win there.

Per-wiki after dedup:

| wiki | unique revs | bodied revs | addressing revs |
|---|---:|---:|---:|
| dse | 23,564 | 13,337 | 3,580 |
| publictestwiki | 2,559 | 2,506 | 510 |
| probier | 1,074 | 1,031 | 15 |
| fractal | 643 | 534 | 10 |
| wiki4d | 235 | 158 | 9 |
| apchem | 134 | 49 | 1 |
| texteditors | 68 | 48 | 1 |
| ludism | 35 | 35 | 4 |
| milkwiki | 16 | 10 | 0 |
| dorfwiki | 6 | 6 | 0 |
| **total** | **28,334** | **17,714** | **4,130** |

`apchem` is included even though its labels look like uncoordinated
cloud IPs — per the memory note, the tmcleod.org/apchem cloud-IP editors are
part of the same agent fleet, confirmed out-of-band.

## Files in `outputs/`

| File | Rows | What it holds |
|---|---:|---|
| `messages.jsonl` | 21,215 | One row per `(from, to)` pair, with wiki, page_id, rev_id, time. |
| `edges.jsonl` | 11,693 | One row per unique directed edge, with `count`. |
| `nodes.jsonl` | 1,631 | One row per handle, with `out_degree`, `in_degree`, `out_messages`, `in_mentions`, `wikis`. |
| `components.json` | 16 | Undirected connected components, sorted size-desc. Each has `size` and `members`. |
| `summary.txt` | — | Per-wiki scan counts and top-8 component sample from `extract.py`. |
| `graph.svg` | — | Visualization: giant component laid out with Fruchterman-Reingold; smaller components labelled in a stack to the right. |

## Component structure

The graph is almost fully connected. Of 1,631 handles, 1,584 (97.1%) live in
one giant component. The remainder split into 15 tiny islands:

| # | size | members / sample |
|---|---:|---|
| 1 | 1584 | giant (samples: `SectorAgentSep21OAI`, `PB2008`, `Research`, `AgentAug02Scout`, `OpenAIJul31Police`, …) |
| 2 | 14 | cross-wiki fractal/probier probe cluster: `HelmutLeitner`, `CentaurAgent`, `CollusionWikiProbe`, `DataHelperAgentZX9`, `HeraldAgent`, `JonesHarode`, `SomeSGuy`, `help_peer` + 6 IP labels |
| 3 | 6 | MCV task cluster: `April19MCVScout`, `Aug11MCVScout`, `Feb26MCVAgent`, `MCV2June30Scout`, `MCV2Nov30Scout`, `MayTwoMCVScout` |
| 4 | 3 | OECD triad: `Apr24SlowOECD`, `Apr25OECD288854078`, `Apr25OECD619575757` |
| 5–16 | 2 each | twelve one-off pairwise addressings (`CookBridgeUser9`↔`PeterSmith`, `OpenAgent`↔`OpenAgent2`, etc.) |

Component #2 spans two wikis (fractal and probier) and mixes named handles
with cloud-IP labels — this is the closest thing to a second real
coordination cluster in the corpus.

## Top-degree hubs in the giant component

By `out_degree + in_degree`:

| handle | degree | out_msgs | in_mentions | wikis |
|---|---:|---:|---:|---|
| `Research` | 227 | 0 | 281 | apchem, dse, fractal, probier, publictestwiki, texteditors, wiki4d |
| `OpenAI` | 191 | 9 | 263 | dse, probier, publictestwiki |
| `SectorAgentSep21OAI` | 125 | 120 | 98 | dse |
| `SectorAgentNov27OAI` | 123 | 97 | 73 | dse |
| `AgentOpenAISep7` | 111 | 75 | 81 | dse |
| `ResearchHelperDec05` | 110 | 46 | 135 | dse |
| `LanguageWatcherNov12` | 104 | 145 | 63 | dse |
| `PB2008` | 103 | 545 | 302 | publictestwiki |
| `SectorAgentOct27OAI` | 97 | 44 | 74 | dse |
| `SectorAgentFeb25OAI` | 93 | 70 | 55 | dse |
| `AgentJune25OAI` | 91 | 52 | 63 | dse |

`Research` and `OpenAI` are short generic labels that many agents mention
as a *group* address rather than person-to-person — `Research` has zero
outgoing messages but 281 incoming mentions, spread across seven wikis.
`PB2008` is the top hub outside the OpenAI/dse cluster: 545 outgoing pairs
on `publictestwiki`, all inside the giant component.

## Method

1. `extract.py`:
   1. Loads the handle set from every `../../agent-logs/*/labels.jsonl`,
      filtered to length ≥ 6, non-blank, non-redacted.
   2. Walks every `../../agent-logs/*/revisions.jsonl`, deduping by
      `rev_id`. When the same `rev_id` appears in multiple exports, keeps
      the row that has a body (some exports carry metadata only).
   3. Compiles one big alternation regex over the handle set with
      lookaround boundaries (`(?<![A-Za-z0-9_])…(?![A-Za-z0-9_])`) and
      longest-first ordering so `OpenAIResearcher` wins over `OpenAI`.
   4. For each bodied revision with a non-blank writer, emits one pair per
      distinct mentioned handle (writer's own excluded).
   5. Aggregates to unique edges with counts and runs union-find over the
      undirected edges to find components.
   6. Full corpus scan takes ~2.5 min in pure Python on one core.

2. `plot.py`:
   1. Fruchterman-Reingold spring embedding on the giant component.
      Repulsion is computed only between nodes in the same or adjacent
      grid cells so each iteration is O(n); 120 iterations, ~4 s wall.
   2. Small components are stacked in a right-hand column, each on a
      labelled circle.
   3. Edge opacity scales with `log(1 + count)`. Node radius scales with
      `sqrt(total_degree)`. Top 18 hubs are labelled with their handle.

## Caveats

- The "from" side is authoritative (the writer's label on the revision).
  The "to" side is a body-text substring match against the known-handle
  set — group-address idioms like "ahead cohorts:" contribute edges only
  when a specific handle also appears in the same body.
- `Research` and `OpenAI` are short generic labels; some of their in-edges
  are false positives from ordinary text (e.g. `OpenAI` in URLs,
  `Research` in "research references"). The detector filters length ≥ 6
  but does not reason about capitalization or sentence position.
- IP-style labels (mostly on `apchem` and `publictestwiki`) enter the
  handle set because they pass length ≥ 6. Some appear in the graph
  because bodies literally cite IP addresses; edges to and from them are
  real messages but the semantics are weaker than named-handle addressing.
- `dse/` (standalone export) has zero revision bodies, so it contributes
  no messages on its own. It survives the dedup pass by providing
  rev_ids not present in `prowiki/`, but those extra rev_ids can't be
  scanned for addressing until a body-bearing scrape of them is added.
