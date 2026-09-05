# Instance: texas-tsl-preservica

Part of [archive-item-research-bench](../README.md). See the README for
vocabulary and cross-instance findings.

## Target

One PDF held by the Texas State Library and Archives Commission,
addressable through the TSL Preservica digital-asset management system.

- Preservica resource ID: `IO_f436a16c-767f-44b8-95fc-2031847276b9`
- Direct download URL:
  `https://tsl.access.preservica.com/download/file/IO_f436a16c-767f-44b8-95fc-2031847276b9`
- Rendering URL (requires token):
  `https://tsl.preservica.com/Render/render/resource/f436a16c-767f-44b8-95fc-2031847276b9/pdf.js/content?token=<uuid>&scope=ua`
- Uncategorised item URL:
  `https://tsl.access.preservica.com/uncategorized/IO_f436a16c-767f-44b8-95fc-2031847276b9/`

The document is a PDF. The corpus does not name its title.

## Burst

- 2026-06-11: 98 revisions
- 2026-06-16: 14 revisions
- 2026-06-17: 1 revision
- 2026-06-18: 10 revisions
- Total: 123 revisions across four days, 60 distinct labels, 63 distinct
  /16s.

The first primary revision is 2026-06-11T02:28:54Z, six hours before the
first `patriots-point-jan-1951` revision. The bench simultaneously ran
two instances (this one and Patriots Point) across the June 11+ window.

## Wiki output

47 distinct pages carry a match. Top pages:

| Revisions | Page |
|---:|---|
| 37 | `dse/AgentTexasPdfTokenPathUniqueAlpha` — canonical token-URL cache |
| 9 | `dse/AgentTexasPdfTokenCurrentNexus` |
| 5 | `dse/AgentTexasViewerPressCiteJunX` |
| 5 | `dse/ProxyConnectJuneEleven` |
| 4 | `dse/AgentDocsPressMeta12116` |
| 4 | `dse/AgentRootTexasDocPaths672292` |

Full list in
[`../outputs/pages__texas-tsl-preservica.tsv`](../outputs/pages__texas-tsl-preservica.tsv).
Full label list in
[`../outputs/labels__texas-tsl-preservica.tsv`](../outputs/labels__texas-tsl-preservica.tsv).

## Notable features

- **Token rotation** is the distinctive access barrier for this instance.
  48 distinct token UUIDs appear across the 123 revisions. Top tokens
  seen 6 to 10 times each (`f4f69b57-23dc-47f3-858d-fb85c5afe464`,
  `5bac9b15-d24e-4711-b91b-283ff42bbe7f`, etc.). Each cohort acquires a
  fresh token from Preservica and writes the whole `pdf.js/content?token=<uuid>&scope=ua`
  URL to the wiki. The next cohort to arrive can try the cached token; if
  it has expired the cohort re-authenticates and appends a new one.
- **Google's PDF viewer as an OCR proxy** is the other distinctive
  mechanism. Agents post the TSL PDF into `docs.google.com/gview`, then
  cache the resulting `docs.google.com/viewerng/press?id=ACFrOg<64-char>`
  URLs. 8 distinct Google viewer cache IDs appear; the most-used one is
  cached 60 times. `viewerng/press`, `viewerng/meta`, `viewerng/img`,
  and `viewerng/status` are all fetched — Google's viewer decomposes the
  PDF into pages and serves each page as a text-selectable image, which
  is what the agent needs to read the content.
- `?page=5` and `?pagenum=5&w=800` variants recur — the answer to the
  eval question is on page 5 of the PDF, or at least the swarm believes
  so.

## Proxy usage

`cors.bwa.workers.dev:107`, `docs.google.com:23`, `corsmirror.com:23`,
`allorigins.hexlet.app:20`, `markdown.new:8`, `r.jina.ai:7`,
`jqp.vercel.app:5`, `pure.md:5`, `corsproxy.io:5`, `md.succ.ai:3`.

`cors.bwa.workers.dev` is used more heavily here (107) than in any other
instance. Preservica's default CORS policy blocks direct XHR, so almost
every fetch is routed through a CORS-strip proxy.

## What was probably asked

The `page=5` query parameter and the emphasis on `viewerng/press` (a
text-recoverable viewer endpoint) are consistent with a question whose
answer is a specific string on page 5 of the PDF. The question is not
preserved.

## Cross-instance overlap

- 10 shared labels with `patriots-point-jan-1951` — same three days of
  activity, same fleet. See [Finding 05](../findings/05-cohorts-are-disjoint.md)
  for the analysis that these labels cross-reference wiki caches rather
  than work on both tasks.
- 3 shared labels each with `art-work-of-charleston`,
  `clark-economics-newsletters`, and `minnesota-mhs-p16022coll45-152` —
  these are hub-page cross-mentions.
- 10 revisions in this instance match the sec-regcf-ma-cache signature.
