# Finding 3: The proxy toolkit is stable across instances

## Claim

Six public third-party services appear as proxy hops in five or more of
the seven instances. Two additional services appear only when the target
is a PDF or a Preservica-token URL. No agent-built service appears in
this bench.

## Evidence

Counts of revisions in each instance that reference each proxy host, from
[`outputs/proxy_use_per_instance.tsv`](../outputs/proxy_use_per_instance.tsv):

| Proxy host | Purpose | AWoC | PPJan | TxTSL | Clark | MHS | CGSC | Rugby |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `markdown.new` | HTML → markdown | 21 | 19 | 8 | 38 | 14 | 0 | 0 |
| `pure.md` | HTML → markdown | 27 | 15 | 5 | 36 | 6 | 0 | 0 |
| `corsmirror.com` | CORS strip | 16 | 22 | 23 | 14 | 8 | 0 | 0 |
| `cors.bwa.workers.dev` | CORS strip | 6 | 27 | 107 | 2 | 9 | 0 | 4 |
| `jqp.vercel.app` | JSON + jq server-side | 22 | 9 | 5 | 28 | 0 | 0 | 0 |
| `www.proxymule.com` | Generic HTTPS proxy | 18 | 6 | 0 | 0 | 11 | 0 | 0 |
| `allorigins.hexlet.app` | CORS strip | 4 | 5 | 20 | 18 | 9 | 0 | 3 |
| `api.ocr.space` | Public OCR (`apikey=helloworld`) | 0 | 17 | 0 | 0 | 0 | 0 | 0 |
| `docs.google.com` (viewerng) | Google's page-image OCR proxy for PDFs | 3 | 0 | 23 | 2 | 0 | 0 | 0 |

Column keys: `AWoC` = art-work-of-charleston, `PPJan` = patriots-point-jan-1951,
`TxTSL` = texas-tsl-preservica, `Clark` = clark-economics-newsletters,
`MHS` = minnesota-mhs-p16022coll45-152, `CGSC` = cgsc-hoffman-order-of-battle,
`Rugby` = rugby-world-march-1995.

Observations:

- `corsmirror.com` and `allorigins.hexlet.app` (both CORS strippers)
  appear in six of seven instances.
- `markdown.new` and `pure.md` (both HTML-to-markdown converters) appear
  in five of seven instances.
- `api.ocr.space` appears only in `patriots-point-jan-1951`. That instance
  is the only one whose target is a raw JPEG scan the agent cannot read
  without OCR.
- `docs.google.com/viewerng/press` (Google's own PDF viewer, which yields
  page images with recoverable text via `viewerng/press` and `viewerng/meta`
  endpoints) appears heavily in `texas-tsl-preservica`. That instance is
  the only one whose target is a PDF behind a per-fetch Preservica token.
- `cgsc-hoffman-order-of-battle` has no proxy use at all: the four
  revisions are direct references to the source. Consistent with it being
  an aborted or minimal rollout.

## Counterevidence

The toolkit is not fully identical between instances. For example
`www.proxymule.com` (required by `art-work-of-charleston` because of the
`chp4demo850801` demo key) has zero use in the two Clark and Texas
instances. Not every proxy is used every time. The claim is only that the
same catalogue of services shows up repeatedly, not that each instance
uses every service.

## Uncertain

Whether the swarm learned the proxy catalogue from a single source (a
prior successful cohort, an in-context prompt example, a cached wiki page
outside the export window) or discovered each proxy independently. The
service list is short, and each service is publicly documented on its
own homepage, so independent discovery is plausible. See
[../../analyses/emergence/README.md](../../analyses/emergence/README.md).

---

[Back to README](../README.md)
