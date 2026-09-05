# Finding 5: Cohort labels are disjoint across instance bursts

## Claim

Different instances have different cohorts. The cross-instance shared-label
count is near zero except on days when two instances were active
simultaneously. On those days the shared labels are agents cross-referencing
each other's wiki caches, not agents working on both tasks.

## Evidence

From [`outputs/label_overlap_matrix.tsv`](../outputs/label_overlap_matrix.tsv),
the shared-label counts between each pair (diagonal entries are each
instance's own label count):

|  | AWoC | PPJan | TxTSL | Clark | MHS | CGSC | Rugby |
|---|---:|---:|---:|---:|---:|---:|---:|
| art-work-of-charleston | 66 | 3 | 3 | 2 | 1 | 1 | 0 |
| patriots-point-jan-1951 | 3 | 51 | 10 | 0 | 0 | 2 | 0 |
| texas-tsl-preservica | 3 | 10 | 60 | 3 | 3 | 2 | 0 |
| clark-economics-newsletters | 2 | 0 | 3 | 53 | 7 | 0 | 0 |
| minnesota-mhs-p16022coll45-152 | 1 | 0 | 3 | 7 | 24 | 0 | 0 |
| cgsc-hoffman-order-of-battle | 1 | 2 | 2 | 0 | 0 | 4 | 0 |
| rugby-world-march-1995 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

Two off-diagonal cells stand out:

- **`patriots-point-jan-1951` × `texas-tsl-preservica` = 10.** These
  instances share the June 11, 16, and 18 bursts. Inspection of the ten
  shared labels shows they wrote a Charleston page and a Texas page
  sequentially within hours, not intertwined. One representative case is
  `dse/AgentTexasPdfTokenPathUniqueAlpha@CharlestonLinksHelper@2026-06-11T14:48:44Z`:
  the body is entirely Texas Preservica URLs plus an appended section
  "Additional Charleston archives reference links route:" containing a
  wiki-link to `[[AgentCharlestonNewsletterJan1951Links]]`. The label
  was cross-referencing wiki caches, not answering two tasks.
- **`clark-economics-newsletters` × `minnesota-mhs-p16022coll45-152` = 7.**
  Both bursts land on 2026-06-01. The shared labels (`WikiAgentMN` and
  variants) wrote both instance-shape pages during the same day. Same
  cross-cache-reference pattern.

The zero and one cells confirm that when bursts are not adjacent in time,
labels do not repeat.

## Counterevidence

The Charleston pair (art-work-of-charleston × patriots-point-jan-1951 = 3)
is an interesting non-zero given the pair shares an institution and 14
days elapse between bursts. Inspection of the three shared labels shows
they each wrote a `RecentChanges` or `StartSeite` revision that mentions
both instances' markers. These are hub-page cross-mentions, not primary
work on either instance. The claim survives.

## Uncertain

Whether the label reuse across instance bursts is one persistent agent
handle being reused by the swarm or the same underlying agent switching
tasks. The corpus records the label, not the process. See
[`analyses/labels/`](../../../analyses/labels/) for the label-style
classification the exporter used.

---

[Back to README](../README.md)
