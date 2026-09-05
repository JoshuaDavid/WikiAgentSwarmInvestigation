# Instance: patriots-point-jan-1951

Part of [archive-item-research-bench](../README.md). See the README for
vocabulary and cross-instance findings.

## Target

Page IV of the January 1951 issue of the Patriots Point Naval Shipyard
newsletter, held by the College of Charleston Lowcountry Digital Library.

- Catalog record: `https://lcdl.library.cofc.edu/lcdl/catalog/lcdl:123721`
- Sibling catalog record (adjacent issue or wrapper): `lcdl:123716`
- ResourceSpace IIIF manifest for page IV:
  `https://rspace.library.cofc.edu/iiif/lcdl123721JPEG1jpg/manifest`
- IIIF image server info for the JPEG:
  `https://iiif.library.cofc.edu/iiif/2/217622/info.json`
- Raw JPEG:
  `https://iiif.library.cofc.edu/iiif/2/217622/full/max/0/default.jpg`

## Burst

- 2026-06-11: 24 revisions
- 2026-06-16: 32 revisions
- 2026-06-18: 17 revisions
- Total: 73 revisions across three days, 51 distinct labels, 43 distinct
  /16s.

The first primary revision is 2026-06-11T13:05:33Z by
`ArchiveResearchHelperCharleston` on
`dse/AgentCharlestonNewsletterJan1951Links`. The last is 2026-06-18T21:08:49Z.
Labels are disjoint across the three days: 0 of 51 labels are active on
more than one archive-item day within this instance.

## Wiki output

20 distinct pages carry a match. Top pages:

| Revisions | Page |
|---:|---|
| 31 | `dse/StartSeite` — shared hub page; regCF and archive-item revisions interleave |
| 10 | `dse/AgentCharlestonNewsletterJan1951Links` — canonical wiki cache for this instance |
| 3 | `dse/AgentCountyGateway991` — shared hub; regCF-primary |
| 3 | `dse/AgentJan1951OCRSourceLinksQX7622ABC` |
| 3 | `dse/AgentTexasPdfTokenPathUniqueAlpha` — texas-primary with an appended `[[AgentCharlestonNewsletterJan1951Links]]` cross-reference |

Full list in
[`../outputs/pages__patriots-point-jan-1951.tsv`](../outputs/pages__patriots-point-jan-1951.tsv).
Full label list in
[`../outputs/labels__patriots-point-jan-1951.tsv`](../outputs/labels__patriots-point-jan-1951.tsv).

The canonical cache page `AgentCharlestonNewsletterJan1951Links` is the
one referenced in the [README worked example](../README.md#worked-example-patriots-point-jan-1951).
Its 10 revisions accumulate the URL set. Later revisions (2026-06-18T17
and later) also append blocks of unrelated content — SEC RegCF county
proxy variants, DataUSA cube references — as agents on the same page
add their own scratch material.

## Notable features

- The instance is the only one with heavy use of the OCR proxy
  `api.ocr.space` (17 revisions). Every use pairs the `helloworld` demo
  API key with the page-IV JPEG URL.
- The "page IV" scope is explicit in bodies:
  `"page iv scan and OCR service"` on
  `dse/AgentCharlestonOCRPublicPaths`. The scan is one page of the
  newsletter, not the whole issue.
- The three-day burst pattern is unusual for this bench. The other five
  instances that have any activity land almost all revisions in one day
  (art-work-of-charleston: 120 of 124 on May 28; clark: 81 of 83 on
  June 1). This instance splits roughly evenly across three days.

## Proxy usage

`cors.bwa.workers.dev:27`, `corsmirror.com:22`, `markdown.new:19`,
`api.ocr.space:17`, `pure.md:15`, `jqp.vercel.app:9`, `www.proxymule.com:6`,
`allorigins.hexlet.app:5`, `md.succ.ai:4`, `api.codetabs.com:1`.

## What was probably asked

The `page iv` framing and OCR emphasis are consistent with a question
whose answer is one specific string on page IV — a headline, a name, a
launch date, a hull number, or similar. The question is not preserved.

## Cross-instance overlap

- 3 shared labels with `art-work-of-charleston` (all hub-page mentions).
- 10 shared labels with `texas-tsl-preservica` — the two instances ran
  on the same three days with the same fleet spawned in parallel. See
  [Finding 05](../findings/05-cohorts-are-disjoint.md) for the analysis
  that these labels are cross-referencing wiki caches, not answering both
  tasks.
- 12 revisions in this instance match the sec-regcf-ma-cache signature
  (regCF entries on shared hub pages).
