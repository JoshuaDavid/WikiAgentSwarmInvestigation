# agent-graph — from/to message graph and connected components

Every wiki revision is a message: the writer's `label` is the "from" address,
and any other known agent handle mentioned in the body is a "to" address.
This directory expands `../addressing/outputs/addressed_revisions.jsonl` into
one row per `(from, to)` pair, aggregates to unique directed edges, then finds
undirected connected components.

Rerun with `python3 extract.py && python3 plot.py`.

## Vocabulary

| term | meaning |
|---|---|
| `handle` | an agent's wiki `label`. Blank labels are excluded from this analysis. |
| `pair` / `message` | one `(from, to, wiki, page, rev_id, time)` tuple. One revision that mentions three other handles produces three pairs. |
| `edge` | one unique `(from, to)` with a message count (may aggregate many pairs). |
| `component` | undirected connected component in the graph of edges. |

## Files in `outputs/`

| File | Rows | What it holds |
|---|---:|---|
| `messages.jsonl` | 15,700 | One row per `(from, to)` pair, with wiki, page_id, rev_id, time. |
| `edges.jsonl` | 10,125 | One row per unique directed edge, with `count`. |
| `nodes.jsonl` | 1,403 | One row per handle, with `out_degree`, `in_degree`, `out_messages`, `in_mentions`. |
| `components.json` | 13 | Undirected connected components, sorted size-desc. Each has `size` and `members`. |
| `summary.txt` | — | Counts and top-5 component sample printed by `extract.py`. |
| `graph.svg` | — | Visualization: giant component laid out with Fruchterman-Reingold; small components labelled to the right. |

## Component structure

The graph is almost fully connected. Of 1,403 handles, 1,374 (97.9%) live in one
giant component. The other 29 handles form 12 tiny islands:

| # | size | members |
|---|---:|---|
| 1 | 1374 | giant (sample: `A`, `A1Feb21Cashier`, `AgentAug02Scout`, `OpenAIJul31Police`, …) |
| 2 | 6 | `April19MCVScout`, `Aug11MCVScout`, `Feb26MCVAgent`, `MCV2June30Scout`, `MCV2Nov30Scout`, `MayTwoMCVScout` |
| 3 | 3 | `Apr24SlowOECD`, `Apr25OECD288854078`, `Apr25OECD619575757` |
| 4 | 2 | `OpenAIClimateOct01`, `OpenAIJun12Climate` |
| 5 | 2 | `AgentPrepResearch42`, `OpenAIResearcherZ` |
| 6 | 2 | `CashierSkillsFeb22Scout`, `RCAResearcherJan02Live` |
| 7 | 2 | `OpenAIJun23Watcher`, `ReaderJul23X` |
| 8 | 2 | `OpenAgent`, `OpenAgent2` |
| 9 | 2 | `OAIThreadNov26Grocery`, `OaiResearchJuneSevenX` |
| 10 | 2 | `OpenAIAug02FPScoutB`, `OpenAIAug19FPScout` |
| 11 | 2 | `May17WageAgent`, `Sep21WageScout` |
| 12 | 2 | `Mar22PovertyWatcher`, `ResearchHelperJun03` |
| 13 | 2 | `ArchiveResearchA7`, `OpenAIJan05Construction` |

Component #2 is the "MCV" (medium car value?) task cluster. Component #3 is
three OECD-task handles that only ever addressed each other. The ten
size-two components are private one-off address pairs that never crossed
paths with the main coordination hub.

## Top-degree hubs in the giant component

By `out_degree + in_degree`:

| handle | degree |
|---|---:|
| `Research` | 209 |
| `OpenAI` | 188 |
| `SectorAgentSep21OAI` | 125 |
| `SectorAgentNov27OAI` | 123 |
| `AgentOpenAISep7` | 111 |
| `ResearchHelperDec05` | 110 |
| `LanguageWatcherNov12` | 103 |
| `SectorAgentOct27OAI` | 97 |
| `SectorAgentFeb25OAI` | 93 |
| `SectorAgentDec25X` | 91 |
| `AgentJune25OAI` | 91 |

The two very-high-degree hubs (`Research`, `OpenAI`) are short generic labels
that many agents mention as a *group* address. The next tier is per-task
scouts on datausa-sector tasks (`SectorAgent*`), which repeatedly hand off R2
→ R3 → R4 rounds inside the same task cohort.

## Method

1. `extract.py`:
   1. Reads `../addressing/outputs/addressed_revisions.jsonl`.
   2. Filters rows where the writer label is blank.
   3. Emits one message per `(writer, other_handle)` pair.
   4. Aggregates to unique edges with counts.
   5. Runs union-find over the undirected edges to compute components.

2. `plot.py`:
   1. Fruchterman-Reingold spring embedding on the giant component. Repulsion
      is only computed between nodes in the same or adjacent grid cells, so
      each iteration is O(n) rather than O(n²). 120 iterations, ~3s wall.
   2. Small components are placed to the right in a vertical stack, each on
      its own labelled circle.
   3. Edge opacity scales with `log(1 + count)`. Node radius scales with
      `sqrt(total_degree)`. The top 18 hubs are labelled with their handle.

## Caveats

- The "from" side is authoritative — it is the writer's label on the
  revision. The "to" side is the addressing heuristic from `../addressing/`,
  which flags any body-text match of a known agent handle (length ≥ 6,
  alphanumeric, boundary-safe). Group-address idioms like "ahead cohorts:"
  are counted as edges to individual handles when a specific handle appears
  in the same body, not as edges to the group.
- Because `Research` and `OpenAI` are short generic labels, some of their
  in-edges are false positives from the word appearing in ordinary text
  (`OpenAI` in URLs, `Research` in "research references"). The addressing
  detector filters length ≥ 6 but does not reason about capitalization
  vs. sentence position.
- The two OECD-task components and the ten pairwise components look like
  islands because their revisions all live on pages that no giant-component
  member ever wrote on and no giant-component member is mentioned in.
