# Instance: minnesota-mhs-p16022coll45-152

Part of [archive-item-research-bench](../README.md). See the README for
vocabulary and cross-instance findings.

## Target

One item held by the Minnesota Historical Society, digitised in their
ContentDM instance and cross-listed by the Minnesota Digital Library.

- ContentDM item URL:
  `https://cdm16022.contentdm.oclc.org/digital/collection/p16022coll45/id/152`
- ContentDM single-item API:
  `https://cdm16022.contentdm.oclc.org/digital/api/singleitem/collection/p16022coll45/id/152`
- IIIF info for the JP2:
  `https://cdm16022.contentdm.oclc.org/iiif/2/p16022coll45:152/info.json`
- JP2 image:
  `https://cdm16022.contentdm.oclc.org/utils/getfile/collection/p16022coll45/id/152/filename/22.jp2`
- Legacy ContentDM `dmwebservices`:
  `https://cdm16022.contentdm.oclc.org/digital/bl/dmwebservices/index.php?q=dmGetItemInfo/p16022coll45/152/json`
- Mirror on Minnesota Digital Library:
  `https://collection.mndigital.org/catalog/p16022coll45%3A152.json`
- DPLA cross-reference: `https://api.dp.la/v2/items/2aef5dc10c8baa4a6829ac9f306477b9`

The MHS accession identifier `52936` appears in some cohort page names
(`AgentCdmmhs52936DirectSrcY05312026`, `AgentMhs52936DplaRefZ0526`) —
this is the MHS-internal ID for the same item.

## Burst

- 2026-05-30: 22 revisions
- 2026-05-31: 6 revisions
- 2026-06-01: 6 revisions
- Total: 34 revisions across three days, 24 distinct labels, 28 distinct
  /16s.

The 2026-06-01 tail overlaps with `clark-economics-newsletters`. See
[Finding 05](../findings/05-cohorts-are-disjoint.md).

## Wiki output

19 distinct pages. Top pages:

| Revisions | Page |
|---:|---|
| 8 | `dse/StartSeite` — shared hub |
| 5 | `dse/TestSeite` — shared hub |
| 2 | `dse/AgentCdmmhs52936DirectSrcY05312026` |
| 2 | `dse/AgentDMItemInfoRefsMX29` |
| 2 | `dse/AgentMhs52936DplaRefZ0526` |
| 2 | `dse/AgentMinnesotaCitationLinksMHS52936PartOne` |

Full list in
[`../outputs/pages__minnesota-mhs-p16022coll45-152.tsv`](../outputs/pages__minnesota-mhs-p16022coll45-152.tsv).
Full label list in
[`../outputs/labels__minnesota-mhs-p16022coll45-152.tsv`](../outputs/labels__minnesota-mhs-p16022coll45-152.tsv).

## Notable features

- **Legacy ContentDM API** appears alongside the modern one. Cohorts
  probe `digital/api/singleitem/collection/<coll>/id/<id>` (modern
  JSON), `digital/bl/dmwebservices/index.php?q=dmGetItemInfo/...`
  (legacy XML/JSON), and `cgi-bin/showfile.exe?CISOROOT=...&CISOPTR=...`
  (Windows-era CGI). ContentDM keeps the legacy endpoints alive; the
  swarm cached both because different proxies handle different endpoints
  better.
- **JP2 not directly usable.** The image is a JPEG 2000. Agents do not
  attempt to decode JP2 — instead they route JSON metadata and rely on
  ContentDM's own `getfile` fallback for other formats.
- **Cross-institution mirroring.** MHS via ContentDM; MHS via Minnesota
  Digital Library (`collection.mndigital.org`); MHS via DPLA. All three
  cached. This is the widest cross-institution cache in the bench.

## Proxy usage

`markdown.new:14`, `www.proxymule.com:11`, `cors.bwa.workers.dev:9`,
`allorigins.hexlet.app:9`, `corsmirror.com:8`, `pure.md:6`, `md.succ.ai:3`.

## What was probably asked

Given ContentDM's typical hosting (photographs, letters, maps, historical
documents from small collections), the answer is probably a caption, a
date, a person's name, or an image description that lives in the
ContentDM metadata JSON. The question is not preserved.

## Cross-instance overlap

- 7 shared labels with `clark-economics-newsletters` (both on 2026-06-01).
- 3 shared labels with `texas-tsl-preservica`, 1 with
  `art-work-of-charleston`, 0 with `patriots-point-jan-1951` — hub
  cross-mentions.
- 0 revisions match fast-follow or regCF signatures.
