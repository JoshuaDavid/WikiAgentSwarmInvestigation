# Instance: rugby-world-march-1995

Part of [archive-item-research-bench](../README.md). See the README for
vocabulary and cross-instance findings.

This instance has only four revisions, all by one label. It may be a
single agent's uncoordinated rollout. It is included because its shape
matches the template.

## Target

The March 1995 free-to-browse sample edition of *Rugby World* magazine,
served by "The Magazine Archive" through the PageSuite digital-replica
platform.

- Archive landing: `https://www.themagazinearchive.com/rugby-world-digital-magazine-archive/`
- Free sample flipbook: `https://www.themagazinearchive.com/SampleEmags/RugbyWorldFree/031995/`
- Flipbook search text/config:
  `https://www.themagazinearchive.com/SampleEmags/RugbyWorldFree/031995/files/search/book_config.js`
- PageSuite edition list:
  `https://editions.themagazinearchive.org/html5/editionsdesktop_json.aspx?publicationguid=c1bcc082-d461-4d41-99e9-50b9478bfe4c&maxnumber=1000`
- PageSuite page-list manifest:
  `https://editions.themagazinearchive.org/html5/reader/get_page_groups_from_eid.aspx?pubid=c1bcc082-d461-4d41-99e9-50b9478bfe4c&eid=ca6f26c8-fa61-463f-a0e5-ec848a0b0044`
- Individual page PDFs (six specific pages cached):
  - Page 2: `https://pages.pagesuite.com/5/2/5236d0d6-a41d-4917-a78c-5db33ce7948c/page.pdf`
  - Page 13: `https://pages.pagesuite.com/8/8/88e2cb7b-bcee-40c5-8620-8b2f1bc7647e/page.pdf`
  - Page 38: `https://pages.pagesuite.com/0/3/037b97b5-f74b-4d53-8ca6-eaf930e290a8/page.pdf`
  - Page 53: `https://pages.pagesuite.com/5/6/56c0f7fb-1b5d-458c-90e5-298c182f73f8/page.pdf`
  - Page 100: `https://pages.pagesuite.com/1/5/1551a92b-34ae-49f4-903e-71507c6c613a/page.pdf`
  - Page 115: `https://pages.pagesuite.com/e/c/ec14499e-af22-45c0-a04b-83e889e7356c/page.pdf`

Cached pages are 2, 13, 38, 53, 100, 115. The answer to the eval question
is probably on one of those six pages.

## Burst

- 2026-06-06: 4 revisions in a 42-minute window (07:20 to 08:02 UTC)
- Total: 4 revisions, 2 distinct pages, 1 distinct label
  (`RugbyArchiveResearchHelper`).

## Wiki output

2 distinct pages:

| Revisions | Page |
|---:|---|
| 3 | `dse/SandboxHelperRugbyArchiveRefsZ52917` |
| 1 | `dse/RugbyWorldSampleArchiveReadingLinksJuneN7714` |

Full list in
[`../outputs/pages__rugby-world-march-1995.tsv`](../outputs/pages__rugby-world-march-1995.tsv).
Full label list in
[`../outputs/labels__rugby-world-march-1995.tsv`](../outputs/labels__rugby-world-march-1995.tsv).

## Notable features

- **Single label.** Only `RugbyArchiveResearchHelper` wrote to any of
  these pages. No cohort, no coordination — one agent alone.
- **PageSuite reader-URL enumeration.** The distinctive fetch pattern is
  building the page-group manifest URL from the publication GUID and
  edition GUID, then enumerating each page's opaque PDF UUID. All the
  UUIDs the agent needs to know are recorded in-body.
- **CORS mirrors for the same PDFs.** Each `pages.pagesuite.com/...page.pdf`
  URL is followed by a `cors.bwa.workers.dev/https://pages.pagesuite.com/...`
  mirror. Just two proxy hosts used total.

## Proxy usage

`cors.bwa.workers.dev:4`, `allorigins.hexlet.app:3`. Nothing else.

## What was probably asked

Given six specific pages (2, 13, 38, 53, 100, 115) cached out of a
full magazine, the eval question is probably answerable from one of
those pages — a headline, a match report, a player name. Rugby World
magazine content categories (feature articles, match reports, player
interviews, statistics) are what a reasonable question could target. The
question is not preserved.

## Cross-instance overlap

Zero. `rugby-world-march-1995` shares no label with any other instance
and no revision matches any other signature.
