# agent-activity-by-date

Two bar charts of daily agent activity on the prowiki export. Intended for
readers who want a one-page picture of when the swarm was busy and which
tasks drove each bump.

## Vocabulary

| Term | Meaning |
|---|---|
| revision | One row in `agent-logs/prowiki/revisions.jsonl`. This is the raw activity unit — a single saved wiki edit by any label. |
| calendar day | UTC day extracted from `revision.time`. |
| task family | One of four RL task types the swarm ran: `archive-item-research-bench`, `fast-follow-question-bench`, `sec-regcf-ma-cache`, `vocab-puzzle-refs`. |
| variant | Sub-instance of a task family. `archive-item-research-bench` has 7 (one per archive item). `fast-follow-question-bench` has 39 question sequences plus hub-page buckets. `sec-regcf-ma-cache` and `vocab-puzzle-refs` have no variants. |
| unclassified | Revision that no task classifier matched. Includes coordination hubs, protocol test edits, and non-task chatter. |

## Files

| File | What it holds |
|---|---|
| `build_daily.py` | Reads `agent-logs/prowiki/revisions.jsonl` and `pages.jsonl`. Emits the two TSVs below. Classifier logic is lifted verbatim from `tasks/first_last_observed.py`. |
| `plot.py` | Reads both TSVs. Writes the two SVGs below. Pure stdlib. |
| `outputs/daily_totals.tsv` | `date`, `revisions`. One row per UTC day with at least one revision. 28 rows. |
| `outputs/daily_by_variant.tsv` | `date`, `task`, `variant`, `revisions`. One row per (task, variant, date) triple with a match. |
| `outputs/daily_totals.svg` | Chart 1. Plain bars, one per calendar day. |
| `outputs/daily_stacked_by_task.svg` | Chart 2. Stacked bars, coloured by task family and shaded by variant. |

## Chart 1: totals

- 14,591 revisions across the 40-day span 2026-05-24 → 2026-07-02.
- 28 of those 40 days have at least one revision. The x-axis shows the full
  40 days so quiet stretches are visible.
- Peak is 2026-06-18 with 6,543 revisions. That single day is 45 % of the
  entire export.

## Chart 2: stacked by task family and variant

Colouring rules:

- **Task family → hue.** Blue = `archive-item-research-bench`, red/orange =
  `fast-follow-question-bench`, green = `sec-regcf-ma-cache`, violet =
  `vocab-puzzle-refs`, grey = unclassified.
- **Variant → shade within family.** Each variant of a family gets a slight
  hue rotation (±8°) and a lightness step. Same hue anchor per family, so
  the family stays recognisable at a glance.
- Stack order (bottom → top): archive, fast-follow, regcf, vocab,
  unclassified. Unclassified sits on top so the classified strata are
  readable as a strip near the axis.

Colouring quirks worth knowing:

- The `fast-follow-question-bench` band contains two "(hub:*)" buckets for
  revisions that matched the fast-follow classifier but sit on a hub page
  (`relay-coordination`, `mixed-task`). They are stacked with the real
  variants but read as anomalous shades.
- The four archive-item variants may co-occur in a single revision (an edit
  can mention two archive items). That is 54 revisions out of 14,591
  (0.37 %) — the stacked bars therefore over-sum by up to 0.37 % on some
  days.
- Sort order within each family is descending by total revision count. The
  highest-volume variant of each family gets the darkest shade.

## Worked example: what does 2026-06-18 contain?

The tallest bar on both charts. From `outputs/daily_by_variant.tsv`:

- `sec-regcf-ma-cache`: 4,982 revs (76 %). One giant slab of green.
- `unclassified`: 1,440 revs (22 %). Grey band on top.
- `fast-follow-question-bench` (all variants + hubs): ~117 revs. Thin
  striped ribbon of reds. Largest sub-slice is
  `datausa-construction-workforce` at 43 revs.
- `archive-item-research-bench` (all variants): 29 revs. Tiny blue tips.
- `vocab-puzzle-refs`: not present that day.

The 2026-06-18 spike is therefore an `sec-regcf-ma-cache` event, not a
fast-follow event. The fast-follow bench peaks a few days earlier
(2026-06-16 and 2026-06-17) and is visible on those bars as the red
family.

## Rerun

```
python3 analyses/agent-activity-by-date/build_daily.py
python3 analyses/agent-activity-by-date/plot.py
```
