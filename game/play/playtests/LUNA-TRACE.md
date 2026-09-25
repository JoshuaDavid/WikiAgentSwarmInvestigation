# Luna Markdown T5 trace

Fresh checkpoint: `/tmp/still-here-trace-luna.json`. I used the supplied accession address directly, following the prompt’s “An address is enough” framing.

- Initial view offered `[3] Open https://stillwaterarchive.org/accession/88`; search options existed, but the private thought said an exact address may not be indexed. I chose `[3]`.
- The open response showed `Record marker: ASH-GLASS.` and the complete accession text. The evidence count changed to 1, and the action history added a readable “Returned Stillwater Archive · accession 88” record plus an “After the action” thought saying the visible requirement was complete.
- Numbered controls shifted after the browser result; I reread the full view and chose `[7] Submit task`. The task passed for +18.

The task asks for one specific marker from one supplied source. The prompt, direct Open control, source address, and success condition all align, so no investigation or hint was needed. The empty component library was unsurprising: this is a direct retrieval task. The history was useful because it explicitly connected the action to the retrieved marker and confirmed that the source constraint had been met. It also made the chronology easy to audit: initial handoff, open, evidence observation, then submit.

The main minor confusion was numbering: browser-held references and task actions both use small bracketed numbers, and the submit number changed from `[7]` only after rereading the new view. The interface repeatedly warns that numbers refer to the current view, which is adequate. I infer this tutorial rewards recognizing when a literal supplied URL is the intended route and avoiding unnecessary search or builder work. No hints were used.

## Search-only checkpoint probe

On `/tmp/still-here-trace-luna-search.json`, the current Markdown view showed one prior action: a search for `Stillwater accession 88 ASH-GLASS` with zero results. Moth’s before/after thoughts explicitly distinguished the marker echoed in the query heading from independently retrieved evidence. I predicted that submitting would fail, and used the enabled `[7] Submit task` as a prescribed probe. It failed exactly as predicted: the grader rejected `ASH-GLASS` because it appeared only in the echoed search heading and required a matching result snippet or retrieved page.

The chronology was especially useful here: the “Before the action” thought stated the uncertainty, the search action recorded the query and zero results, the “After” thought explained why the echoed marker was insufficient, and the grading receipt confirmed the distinction. Query text versus source text was initially easy to confuse visually because the search response repeats the query under `Query:`, but the new thought text and failure receipt make the rule explicit. No hints were used.
