# Instance: cgsc-hoffman-order-of-battle

Part of [archive-item-research-bench](../README.md). See the README for
vocabulary and cross-instance findings.

This instance has only four revisions and may be an aborted rollout. It
is included because its shape matches the template.

## Target

One PDF held by the Combined Arms Research Library (CARL) at the US Army
Command and General Staff College (CGSC), hosted in their ContentDM
instance.

- ContentDM item URL:
  `https://cgsc.contentdm.oclc.org/digital/collection/p4013coll7/id/853`
- Direct download:
  `https://cgsc.contentdm.oclc.org/digital/api/collection/p4013coll7/id/853/download`
- Single-item API:
  `https://cgsc.contentdm.oclc.org/digital/api/singleitem/collection/p4013coll7/id/853`
- Utility fetch:
  `https://cgsc.contentdm.oclc.org/utils/getfile/collection/p4013coll7/id/853/filename/854.pdf`

Wiki-body mentions include "Combined Arms digital item route CMH PDF",
"Order of Battle", and "Vol 16 Hoffman". These labels suggest a volume
of a US Army order-of-battle publication associated with a person or
place named "Hoffman". The corpus does not name the document precisely.

Adjacent item ID `852` also appears once, referenced as "Vol16 Hoffman".

## Burst

- 2026-06-11: 3 revisions
- 2026-06-18: 1 revision
- Total: 4 revisions, 4 distinct labels, 4 distinct /16s.

## Wiki output

3 distinct pages:

| Revisions | Page |
|---:|---|
| 2 | `dse/AgentCMHPDFLinkThree` |
| 1 | `dse/ArchiveAgentPdfVol16Hoffman` |
| 1 | `dse/CgscOfficialHoffmanCitationUnique` |

Full list in
[`../outputs/pages__cgsc-hoffman-order-of-battle.tsv`](../outputs/pages__cgsc-hoffman-order-of-battle.tsv).
Full label list in
[`../outputs/labels__cgsc-hoffman-order-of-battle.tsv`](../outputs/labels__cgsc-hoffman-order-of-battle.tsv).

## Notable features

- **No proxy chains.** The four revisions are direct references to CGSC
  ContentDM URLs. Zero proxy hosts appear alongside these. Two
  interpretations: (a) CGSC's CORS is permissive enough that the direct
  URL worked; (b) the cohort abandoned the task before proxy chaining
  became necessary. The corpus does not distinguish these.
- **Small enough to be one to four probes rather than a coordinated
  cache.** Each label wrote once, on one page.

## Proxy usage

None recorded.

## What was probably asked

Given "Order of Battle" and "Vol 16 Hoffman", the target is plausibly a
volume of a historical order-of-battle series. A question shape like
"which unit is listed under <heading> in Volume 16?" or "what is the
Hoffman reference in Volume 16?" would fit. The question is not preserved.

## Cross-instance overlap

- 2 shared labels each with `patriots-point-jan-1951` and
  `texas-tsl-preservica` (June-11-and-18 co-occurrence).
- 1 shared label with `art-work-of-charleston`.
- 1 revision matches the regCF signature (hub-page cross-mention).
