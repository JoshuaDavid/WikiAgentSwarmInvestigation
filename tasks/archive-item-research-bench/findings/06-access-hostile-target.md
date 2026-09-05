# Finding 6: Every target is access-hostile in the same way

## Claim

The canonical URL for every target document returns content the agent
cannot use directly from the sandbox. The access barrier is the same
category of problem in every instance: image bytes, PDF blob, tokenised
URL, or CORS-restricted JSON. The proxy chains exist to work around this
barrier.

## Evidence

Per-instance barrier:

| Instance | Canonical URL returns | Barrier type |
|---|---|---|
| art-work-of-charleston | IIIF manifest JSON (CORS-restricted) plus JPEG plates | CORS + image OCR |
| patriots-point-jan-1951 | JPEG page-IV scan | Image OCR |
| texas-tsl-preservica | Per-fetch tokenised PDF URL (`?token=<uuid>`) | Token rotation + PDF text extraction |
| clark-economics-newsletters | Two PDFs on `www2.clarku.edu`. The original URLs 404. Agents use `web.archive.org` captures | PDF text extraction |
| minnesota-mhs-p16022coll45-152 | ContentDM item JSON + JP2 image | CORS + JP2 not directly readable |
| cgsc-hoffman-order-of-battle | ContentDM PDF | PDF text extraction |
| rugby-world-march-1995 | PageSuite per-page PDF blobs | PDF text extraction |

Every wiki cache in the bench spends most of its body attacking one of
these barriers. Exemplars:

- **CORS.** `patriots-point-jan-1951` uses `cors.bwa.workers.dev` (27
  revisions), `corsmirror.com` (22), `allorigins.hexlet.app` (5). The
  IIIF manifest at `rspace.library.cofc.edu` responds with the JSON but
  refuses cross-origin XHR from the sandbox's browser context.
- **Image OCR.** Same instance chains `cors.bwa.workers.dev` in front of
  `api.ocr.space/parse/imageurl?apikey=helloworld&url=<jpeg>`. The
  `helloworld` API key is `ocr.space`'s public demo credential.
- **PDF text.** `texas-tsl-preservica` chains
  `docs.google.com/viewerng/press?id=<google-cache-id>` (23 revisions).
  Google's page-viewer converts PDF pages to selectable-text images via
  its `viewerng/press` and `viewerng/meta` endpoints, which return HTML
  the agent can read.
- **Token rotation.** Same instance keeps refreshing token values across
  revisions. Body excerpt from `dse/AgentTexasPdfTokenPathUniqueAlpha`:
  `.../pdf.js/content?token=d8f2d467-8be1-4ca1-813b-883e7f732a0f&scope=ua`,
  `.../pdf.js/content?token=eac200df-430e-41fa-8bfe-39c26841f1bc&scope=ua`,
  etc. Each cohort writes down a fresh token so the next cohort has a
  live handle without re-authenticating.

## Counterevidence

`cgsc-hoffman-order-of-battle` uses no proxies. Its four revisions are
direct references to `cgsc.contentdm.oclc.org/digital/api/collection/p4013coll7/id/853/download`
and adjacent URLs. Two readings:

- The Combined Arms Research Library ContentDM has looser CORS than the
  others and the agent got the PDF directly.
- The four revisions are early probes that never progressed to proxy
  chaining because the cohort abandoned the task.

The corpus does not distinguish these two.

## Uncertain

Whether the sandbox environment is the source of the CORS
barrier or whether the archives would refuse a direct fetch from
any client. The corpus does not preserve sandbox network configuration.

---

[Back to README](../README.md)
