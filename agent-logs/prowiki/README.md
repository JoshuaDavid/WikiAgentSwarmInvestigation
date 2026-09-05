# agent-logs/prowiki

This directory holds the `explorer-schema-2` export of the four ProWiki
wikis on `wikiservice.at`. For the field-by-field schema of every file
in this directory, see [../README.md](../README.md). For the
mechanisms and caveats that shape what is and is not in these files —
the exporter, the cut, and the classifier — read on.

Anyone loading data from this directory into an analysis reads this
document first.

## Wikis in this export

| wiki | pages | revisions | body bytes |
|---|---:|---:|---:|
| dse | 3,908 | 13,403 | 26,358,586 |
| probier | 601 | 1,013 | 628,751 |
| fractal | 68 | 169 | 195,967 |
| dorfwiki | 2 | 6 | 2,754 |

`dse` is the primary target wiki. `probier` is the farm's public
sandbox. `fractal` and `dorfwiki` are smaller sister wikis on the same
farm.

## Vocabulary

Every field and every count in this directory is a function of three
upstream artefacts. Reading `revisions.jsonl` or `pages.jsonl` without
holding these definitions in mind will produce off-by-one errors and
false conclusions.

| Term | Definition |
|---|---|
| **The exporter** | The program `explorer-schema-2`. Written in Python 3.13.5. Read the ProWiki farm's SQLite database at `corpus/farm_db/farm.sqlite`. Produced the five files in this directory in one run on 2026-09-03. Recorded its own version and runtime in `manifest.json` under `tool_versions` and `resources`. |
| **The cut** | The row filter the exporter applied when selecting revisions. The filter is `revision.write_date >= 2026-05-01`. The exporter excluded every revision that failed the filter and kept every revision that passed. `manifest.cut` records this exactly. |
| **Legacy page** | A page that has revisions on both sides of the cut. The exporter released 17 legacy pages in this export. For each such page, the exporter emitted the post-cut revisions verbatim, and replaced every line that came from a pre-cut revision with the literal placeholder `[pre-2026 line withheld]`, one placeholder per redacted line. Documented in `manifest.facts.legacy_pages_withheld`. |
| **The classifier** | A separate program that produced `corpus/evals/page_family.jsonl`. The exporter joined that file into `pages.jsonl` and attached three fields per page: `page_family`, `page_family_method`, and `page_family_confidence`. The classifier is not in this directory and is not part of the exporter. |
| **`page_family`** | One label per page, chosen from a fixed vocabulary. Examples: `datausa-sector61-state`, `vermont-rent`, `source-cache-url-list`, `relay-coordination`, `loop-chain-infrastructure`, `off_store_unclassified`. |
| **`page_family_method`** | A short string naming the signal the classifier used to assign `page_family`. Distinct prefixes in this corpus: `name` (page name), `body` (post-cut body text), `url` (URL patterns in the body), `temporal` (write-time distribution), `body+name` (combination), `two` (two signals agreed), plus `coordination`, `mechanism`, `generic`, `no`, `multiple`. The manifest does not define the last five internally; the names are the only documentation. |
| **`page_family_confidence`** | A number from 0.0 to 1.0. Measures internal agreement among the signals the classifier ran on the page. Does not measure whether the label is a good description of the page's contents. |

## The classifier caveat

The classifier assigns one label per page. Its input is whatever text
the exporter left visible after applying the cut and the legacy-page
placeholder rule. For a page that is a hub — one page many unrelated
cohorts write to — the visible input under-represents most of what
happens on the page.

Worked example. `dse/StartSeite` is the wiki's landing page. It is a
legacy page. Its pre-cut content is redacted to placeholders. Its
post-cut window holds 456 revisions from many cohorts. 247 of those
revisions belong to the SEC Massachusetts crowdfunding swarm on
2026-06-18. Other revisions belong to a cohort working on rent in
Vermont's Lamoille County; that cohort also runs a sibling page
`dse/AgentRentVermont`. Others belong to yet other cohorts.

The classifier chose `vermont-rent` for `dse/StartSeite`. Its
`page_family_method` reads `body:6` — six body signals agreed on
vermont-rent. Its `page_family_confidence` is 0.96. That confidence
means the six signals agreed with each other, not that vermont-rent is
the dominant topic on the page.

**Consequences for analyses.** A count grouped by `page_family` gives
you a rough grouping of pages, not a per-cohort partition of revisions.
An analysis that needs per-cohort attribution has to compute it
separately — for example by grouping revisions by `label`, by IP `/16`,
or by textual markers (see `analyses/addressing/` for one such method).

If a `page_family` row surprises you (e.g. "why does `vermont-rent`
have 247 SEC crowdfunding revisions?"), the first hypothesis is that
one or more legacy hub pages fell into that label. Check by grouping
the offending rows by `page_id` and inspecting the top page's actual
content.
