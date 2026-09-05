# Finding 4: The wikis contain no extracted answer text

## Claim

No revision on any archive-item wiki page contains OCR output, plate
captions, headline text, dates, personal names, or any other content
extracted from the target document. Every revision body is either a list
of URLs or a short meta-description of what those URLs point at. One
peripheral exception exists.

## Evidence

An exhaustive sweep of the 445 archive-item revisions was made. In every
body:

- No sentence describes the content of the target document.
- No block of extracted text appears (no OCR output, no transcribed
  caption, no quoted paragraph).
- The only English prose is meta-language ("Public references OCR",
  "Digital library manifest metadata", "Research references for Patriots
  Point Shipyard newsletters January 1951").

Two exemplar counts:

- On `patriots-point-jan-1951`, 15 distinct labels wrote pages that link
  to the OCR service `api.ocr.space/parse/imageurl?apikey=helloworld&url=...`
  pointed at the page-IV JPEG. None of those 73 revisions contains an
  OCR result.
- On `texas-tsl-preservica`, 60 distinct labels wrote pages that link to
  `docs.google.com/viewerng/press?id=<google-cache-id>` and to
  `tsl.access.preservica.com/download/file/IO_f436a16c-...`. None of those
  123 revisions contains text extracted from the PDF.

## Counterevidence: URL slugs as effective captions

`art-work-of-charleston` caches a set of Historic Charleston Foundation
CatalogIt URLs whose slug segments are the plate titles themselves:

- `hub.catalogit.app/historic-charleston-foundation/folder/entry/pine-forest-inn`
- `.../view-in-magnolia-cemetery`
- `.../old-oak-in-magnolia-cemetery`
- `.../residence-of-geo.-w.-williams-sr.`
- `.../view-on-legre-sic-street` (the `sic` marks a transcription note)
- `.../view-on-south-battery`
- `.../scene-on-marshalls-wharf`
- `.../view-in-the-wittie-sic-place`

Nine slugs total. Plus explicit `api.catalogit.app/.../search?query=<term>`
URLs for `2006.007`, `Pine Forest Inn`, `View in Magnolia Cemetery`,
`Old Oak in Magnolia`, and `Wittie`.

These slugs are effectively plate titles that an agent could read directly
from a wiki page without ever fetching CatalogIt. This is the only
exception to the "no answer text" claim in the corpus, and it is
incidental: the URL is what the agent cached, and the URL happens to
contain the caption because CatalogIt uses caption-derived slugs.

## Uncertain

Whether more incidental slug-as-answer content exists in the corpus that
this survey missed. The scan was body-string-only and did not decode URL
percent-encoding beyond obvious cases.

---

[Back to README](../README.md)
