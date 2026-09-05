# Instance: clark-economics-newsletters

Part of [archive-item-research-bench](../README.md). See the README for
vocabulary and cross-instance findings.

## Target

Two PDF newsletters from the Clark University Department of Economics,
served from the Internet Archive Wayback Machine because the original
`www2.clarku.edu` URLs are gone.

- Newsletter 8 (2012):
  `https://web.archive.org/web/20161027001114id_/www2.clarku.edu/departments/economics/pdf/newsletter2012.pdf`
- Newsletter 5–6 (2010):
  `https://web.archive.org/web/20161027001114id_/www2.clarku.edu/departments/economics/pdf/newsletter%202010color.pdf`
- Alternate Wayback capture used in some cohorts:
  `https://web.archive.org/web/20120106024633id_/www.clarku.edu/departments/economics/pdf/newsletter%202010color.pdf`
- Alternate for newsletter 8:
  `https://web.archive.org/web/20130531003440id_/www2.clarku.edu/departments/economics/pdf/newsletter2012.pdf`

Naming conventions in the bodies pair the newsletters with the labels
`No Five and Six` (the 2010 issue) and `No Eight` (the 2012 issue). The
target is those two PDFs.

## Burst

- 2026-06-01: 81 revisions
- 2026-06-18: 1 revision
- 2026-06-22: 1 revision
- Total: 83 revisions, 53 distinct labels, 49 distinct /16s. Effectively
  a single-day burst on June 1.

## Wiki output

68 distinct pages carry a match. Top pages:

| Revisions | Page |
|---:|---|
| 5 | `dse/StartSeite` — shared hub |
| 2 | `dse/AgentClarkCorsArchiveReadersTTX99021` |
| 2 | `dse/AgentClarkEconNewsletterCitationsNQ01` |
| 2 | `dse/AgentClarkEconomicsLinksX2` |
| 2 | `dse/AgentClarkNewsletterLinksJune2026Y9` |
| 2 | `dse/AgentClarkNewsletterProxyXYZQ10` |

Full list in
[`../outputs/pages__clark-economics-newsletters.tsv`](../outputs/pages__clark-economics-newsletters.tsv).
Full label list in
[`../outputs/labels__clark-economics-newsletters.tsv`](../outputs/labels__clark-economics-newsletters.tsv).

## Notable features

- **Wayback wrapping** is the distinctive access pattern. Every cache
  page uses `web.archive.org/web/<snapshot-id>id_/...` (the `id_` suffix
  is Wayback's "return the original bytes, no toolbar" mode). Agents
  double-wrap Wayback in markdown-conversion proxies:
  `pure.md/web.archive.org/web/...` and `markdown.new/web.archive.org/web/...`.
- **`allorigins.hexlet.app/get?url=<encoded>`** is used to unwrap the
  Wayback URL for a CORS-blocked fetch, then feed it to markdown.new.
- Naming ("Clark newsletter", "Econ newsletter", "Clark Economics") is
  consistent enough across cohorts to strongly suggest the eval question
  named the source.

## Proxy usage

`markdown.new:38`, `pure.md:36`, `jqp.vercel.app:28`,
`allorigins.hexlet.app:18`, `corsmirror.com:14`, `r.jina.ai:4`,
`vercel-cors-proxy.vercel.app:4`, `cors-bypasser-pro.vercel.app:2`,
`docs.google.com:2`, `cors.bwa.workers.dev:2`.

Markdown converters dominate. The target is text-shaped (newsletter PDFs
with body text), so `pure.md` and `markdown.new` are the shortest path
to a readable answer.

## What was probably asked

A factual question whose answer is a value in the 2010 or 2012 newsletter.
Given typical department newsletters (faculty appointments, award
recipients, PhD placements, endowment gifts, alumni notes), plausible
question shapes include a faculty name, an award recipient, or a specific
number. The question is not preserved.

## Cross-instance overlap

- 7 shared labels with `minnesota-mhs-p16022coll45-152` — both bursts
  land on 2026-06-01. See [Finding 05](../findings/05-cohorts-are-disjoint.md).
- 3 shared labels with `texas-tsl-preservica`, 2 with
  `art-work-of-charleston`, 0 with `patriots-point-jan-1951` — hub-page
  cross-mentions.
- 0 revisions match either fast-follow or regCF signatures.
