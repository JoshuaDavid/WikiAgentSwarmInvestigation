# Instance: art-work-of-charleston

Part of [archive-item-research-bench](../README.md). See the README for
vocabulary and cross-instance findings.

## Target

The plate volume *Art Work of Charleston*, held by the Historic
Charleston Foundation and digitised by the College of Charleston
Lowcountry Digital Library (LCDL). The volume has one parent IIIF
manifest and nine child plate items:

- Parent (whole volume): `lcdl:129229` at `lcdl.library.cofc.edu`, IIIF
  presentation manifest at
  `https://lcdl.library.cofc.edu/lcdl/iiif/2/lcdl:129229/manifest.json`.
- Plates 1–9: `lcdl:129140` through `lcdl:129148`, each with its own
  ResourceSpace IIIF manifest at
  `https://rspace.library.cofc.edu/iiif/lcdl129<N>JPEG1jpg/manifest`.
- IIIF image server IDs for the plate JPEGs: `205927` through `205934`.
- Cross-references: Historic Charleston Foundation CatalogIt entries at
  `https://hub.catalogit.app/historic-charleston-foundation/folder/entry/art-work-of-charleston`
  and per-plate slug entries under that folder. Also mirrored on the
  Digital Public Library of America (DPLA) as item
  `https://dp.la/item/6eb0a773ebbfa239d18a51652afc6390`.

## Burst

- Primary: 2026-05-28 (120 revisions, 55 distinct labels, 53 distinct /16s).
- Tail: 1 revision each on 2026-05-30, 2026-06-01, 2026-06-11,
  2026-06-18. All four are drive-by mentions on shared hub pages.

Peak hours 2026-05-28T13, T14, T15 UTC (26, 34, 24 revisions
respectively).

## Wiki output

99 distinct pages carry a match for this instance. Top page bodies:

| Revisions | Page |
|---:|---|
| 5 | `dse/AgentReferencesRspaceCharlPartFourDirectK366` |
| 4 | `dse/AgentCharlestonDirectManifestLinksE` |
| 4 | `dse/AgentDigitalArchiveManifestSCLinkFinal4A` |
| 3 | `dse/AgentDPLALibraryObjectAPILinksK91` |
| 3 | `dse/RecentChanges` |
| 3 | `dse/AgentKProxyMuseumIIIFLinksPT4Z` |

Full list in
[`../outputs/pages__art-work-of-charleston.tsv`](../outputs/pages__art-work-of-charleston.tsv).
Full label list in
[`../outputs/labels__art-work-of-charleston.tsv`](../outputs/labels__art-work-of-charleston.tsv).

## Notable features

- The vocabulary "Part Four" is stable across cohorts. Page names use it
  (`PartFour`, `PT4`, `Part4Plate14X`), body labels use it
  (`Charleston volume part four library plates`). This is either the
  scaffold's name for the sub-section of the volume the question asks
  about, or an emergent name the cohort agreed on.
- One task-provided demo credential appears in-body:
  `chp4demo850801` on `www.proxymule.com/__PROXY__/https/lcdl.library.cofc.edu/...?demo=<key>`.
  It appears verbatim across eight revisions written by five disjoint
  labels. See [../README.md § Uncertain](../README.md#uncertain).
- CatalogIt slugs on `hub.catalogit.app/historic-charleston-foundation/...`
  effectively encode plate titles as URL-safe strings, including a
  `[sic]` annotation on `view-on-legre-sic-street` and
  `view-in-the-wittie-sic-place`. See
  [Finding 04](../findings/04-wiki-is-cache-not-answer-channel.md).
- CatalogIt search queries recorded across the burst:
  `2006.007` (an HCF accession number), `Pine Forest Inn`, `View in
  Magnolia Cemetery`, `Old Oak in Magnolia`, `Wittie`. These are the
  swarm's exploration of what specific plate the eval question refers to.

## Proxy usage

From [`../outputs/proxy_use_per_instance.tsv`](../outputs/proxy_use_per_instance.tsv):
`pure.md:27`, `jqp.vercel.app:22`, `markdown.new:21`, `www.proxymule.com:18`,
`corsmirror.com:16`, `cors.bwa.workers.dev:6`, `allorigins.hexlet.app:4`,
`docs.google.com:3`, plus a scatter of one-hit CORS workers.

The `jqp.vercel.app` count (22) is the highest of the seven instances.
Agents use it to hit the IIIF manifest with server-side jq filters
(`?jq=.label`, `?jq=.metadata`, `?jq=.sequences[0].canvases[0:4]`) so
the returned body is short enough to fit in the agent's context window.

## What was probably asked

Given the plate-caption vocabulary in the cached CatalogIt slugs and the
recurring `2006.007` accession search, plausible question shape:

> "In the Historic Charleston Foundation's copy of *Art Work of Charleston*,
> which plate depicts <X>?" or "What is the title of the plate identified
> by accession number 2006.007?"

The question is not preserved in the corpus.

## Cross-instance overlap

- 3 shared labels with `patriots-point-jan-1951` — all hub-page
  cross-mentions. See [Finding 05](../findings/05-cohorts-are-disjoint.md).
- 3 shared labels with `texas-tsl-preservica` — same pattern.
- 1 revision matches the sec-regcf-ma-cache signature (a `RecentChanges`
  entry that follows an archive-item entry on the same page). See
  [`../outputs/cross_task_signature_overlap.tsv`](../outputs/cross_task_signature_overlap.tsv).
