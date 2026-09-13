# wiki-traffic-jun-21-22

Stacked column chart: revisions per UTC minute across 2026-06-21 and
2026-06-22, one segment per wiki.

## Vocabulary

| Term | Meaning |
|---|---|
| minute bucket | UTC minute, floor-aligned. 2,880 buckets across the 48-hour window. |
| wiki | One of `dse`, `fractal`, `probier`, `dorfwiki`, `apchem`, `ludism`, `milkwiki`, `texteditors`, `wiki4d`. The nine wiki-shaped exports under `agent-logs/`. |
| revision | One row in the source `revisions.jsonl` with a `time` value that normalises to a UTC instant inside the window. |
| stack order | Bottom → top of each bar is by wiki total, largest first. `dse` sits at the bottom because it dominates. |

## Data plumbing

Sources — one per wiki. `probier` and `dorfwiki` are extracted from the
prowiki export by filtering on the `wiki` field; the other seven have
their own standalone directory:

| Wiki | Source path | Row filter |
|---|---|---|
| `dse` | `agent-logs/dse/revisions.jsonl` | — |
| `fractal` | `agent-logs/fractal/revisions.jsonl` | — |
| `probier` | `agent-logs/prowiki/revisions.jsonl` | `wiki == probier` |
| `dorfwiki` | `agent-logs/prowiki/revisions.jsonl` | `wiki == dorfwiki` |
| `apchem` | `agent-logs/apchem/revisions.jsonl` | — |
| `ludism` | `agent-logs/ludism/revisions.jsonl` | — |
| `milkwiki` | `agent-logs/milkwiki/revisions.jsonl` | — |
| `texteditors` | `agent-logs/texteditors/revisions.jsonl` | — |
| `wiki4d` | `agent-logs/wiki4d/revisions.jsonl` | — |

Source timestamps are stored with a mix of TZ offsets (`+00:00`,
`+01:00`, `-04:00`, `-05:00`, `Z`). Every row is normalised to UTC before
minute-bucketing.

## Files

| File | What it holds |
|---|---|
| `build_and_plot.py` | Reads the nine sources, buckets by (minute, wiki), writes both outputs. |
| `outputs/wiki_traffic_by_minute.tsv` | `minute_utc`, `wiki`, `revisions`. Long-format row per non-zero (minute, wiki) cell in the window. |
| `outputs/wiki_traffic_stacked_by_wiki.svg` | The chart. 2,880 one-minute bars; grey vertical lines mark each hour; a darker line marks the day boundary at 2026-06-22 00:00 UTC. |

## Reading it

- **Active wikis in window (6):** `dse` (1,550), `fractal` (303),
  `probier` (192), `wiki4d` (42), `texteditors` (16), `dorfwiki` (6).
- **Silent wikis in window (3):** `apchem`, `ludism`, `milkwiki`. Listed
  in the chart legend as a footnote.
- **Total:** 2,109 revisions across the 48-hour window.
- **Peak minute:** the tallest bar sits in the small hours of
  2026-06-22 UTC and reaches ~20 revisions in one minute.

## Rerun

```
python3 analyses/wiki-traffic-jun-21-22/build_and_plot.py
```
