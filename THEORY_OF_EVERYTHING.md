The web fetch tool:

search: takes search term, returns a list of pages which include that term, notably *NOT* including URLs
tool call: `{ "search_query": [ { "q": "European swallow" } ], "response_length": "long" }`
returns results like
```
Title (URL)
citeturn0search0
summary or extracted content
```
and then in this example `turn0search0` is the `ref_id` which can be followed in subsequent turns
Expanded content inside search results *can* contain numbered outbound-link citations, but those can't be navigated to directly.

open:

Ref mode:
takes a ref from a search
tool call: `{ "open": [{"ref_id": "turn0search0"}] }`
returns a *new* ref of the form `turn1view0`, and then a page with extracted links like
`cite4†Eastern Red-rumped Swallow`
so the refs for links within the page are of the form `{"ref_id":"turn1view0","id":4}`
a reference can ALWAYS be opened, though it may result in a cache miss if live search is disabled


URL mode:
takes a URL
tool call: `{ "open": [{"ref_id": "https://example.com"}] }`
rejects unless it's an explicitly allowed url
this INCLUDES if the exact link is one the agent has a ref to

click:
like open, except takes a ref id AND an id, and has no url mode
`{ "click": [{ "ref_id": "turn7view0", "id": 169 }] }`
