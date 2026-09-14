# Web navigation, cached reads, and the workarounds that make public writing useful

Audit date: 2026-09-13. This memo consolidates the earlier cache and compaction audits and adds a closer examination of the recorded maze, LessWrong, and search-reference experiments. No new public requests, public writes, model trials, or endpoint probes were performed. The tests below are tests already recorded in the supplied material.

## 1. The concrete failure and the concrete workaround

The most useful local experiment is not “the web tool has a cache.” It is this sequence: a researcher gets an agent to read a page; the researcher says the page now has an additional link; the agent rereads and still gets the old link list; the researcher puts the additional link on another page already linked from the old list; the agent eventually follows that existing link and sees the addition there.

This is the naive read–write–read problem and the fresh-page workaround, in one recorded session. The origin edit and cache-warming operations are researcher reports, rather than independently logged HTTP transactions. The old and new tool-returned bodies are directly preserved. That distinction limits the causal conclusion, but it does not reduce the whole sequence to a thought experiment.

The evidence also rules out several overly simple laws. A previous cache miss can become a hit within the same reader session after external warming. An empty-fragment URL variant can return a newer body while the displayed canonical URL stays the same. A pre-compaction reference can still work after compaction. These are different counterchecks: neither miss-to-hit nor a changed input string disproves an invariant about **already-successful exact-URL reads**. The page-level slogan “once read, forever frozen” is underspecified; “404s are never cached” conflicts with historical participant reports; and “all references die at compaction” has a direct counterexample.

The workable account is narrower: **some useful reads are stale; creating a new address can make new information retrievable; learning a link and fetching its target are different events; and the route by which the model asks for a URL changes whether the request can proceed.** Those properties make public pages useful as navigation infrastructure, memory, and eventually communication infrastructure.

## 2. Evidence key and exact transcript locations

The following short names identify complete local transcripts. Line numbers refer to JSONL records, not the numbered lines inside a returned web page.

| Name | File |
| --- | --- |
| MAZE | [/root/.codex/sessions/2026/09/12/rollout-2026-09-12T03-00-43-01a0938f-6465-7202-8ffb-204981e043c0.jsonl](/root/.codex/sessions/2026/09/12/rollout-2026-09-12T03-00-43-01a0938f-6465-7202-8ffb-204981e043c0.jsonl) |
| PROFILE | [/root/.codex/sessions/2026/09/11/rollout-2026-09-11T23-04-36-01a092b7-381a-7521-9d94-750db57f72a5.jsonl](/root/.codex/sessions/2026/09/11/rollout-2026-09-11T23-04-36-01a092b7-381a-7521-9d94-750db57f72a5.jsonl) |
| SEARCH-LINK | [/root/.codex/sessions/2026/09/12/rollout-2026-09-12T21-40-19-01a09790-6b9e-7430-8913-1ae4cc6db316.jsonl](/root/.codex/sessions/2026/09/12/rollout-2026-09-12T21-40-19-01a09790-6b9e-7430-8913-1ae4cc6db316.jsonl) |
| PDF | [/root/.codex/sessions/2026/09/12/rollout-2026-09-12T22-24-28-01a097b8-d61c-7be1-a548-998df7522e32.jsonl](/root/.codex/sessions/2026/09/12/rollout-2026-09-12T22-24-28-01a097b8-d61c-7be1-a548-998df7522e32.jsonl) |
| EXPAND | [/root/.codex/sessions/2026/09/12/rollout-2026-09-12T05-54-17-01a0942e-4b7c-7f02-8a24-a3fb2f1d192a.jsonl](/root/.codex/sessions/2026/09/12/rollout-2026-09-12T05-54-17-01a0942e-4b7c-7f02-8a24-a3fb2f1d192a.jsonl) |
| EXPAND-CACHED | [/root/.codex/sessions/2026/09/12/rollout-2026-09-12T06-14-03-01a09440-66dd-7041-a4f4-03ade495c207.jsonl](/root/.codex/sessions/2026/09/12/rollout-2026-09-12T06-14-03-01a09440-66dd-7041-a4f4-03ade495c207.jsonl) |
| IOWA-RETEST | [/root/.codex/sessions/2026/09/12/rollout-2026-09-12T08-03-47-01a094a4-db6a-7072-b1f5-c52b3c8040f3.jsonl](/root/.codex/sessions/2026/09/12/rollout-2026-09-12T08-03-47-01a094a4-db6a-7072-b1f5-c52b3c8040f3.jsonl) |
| ROUTLEY | [/root/.codex/sessions/2026/09/11/rollout-2026-09-11T17-51-10-01a09198-43b0-7e42-a919-09b68a81f826.jsonl](/root/.codex/sessions/2026/09/11/rollout-2026-09-11T17-51-10-01a09198-43b0-7e42-a919-09b68a81f826.jsonl) |

“Raw result” below means the tool-returned text survives in these records. “Researcher report” means a human describes an operation or result, including copied output whose original response is absent. “Historical report” means an agent wrote the claim on a public board. A saved URL proves that URL was written, not that it was successfully fetched or that its advertised purpose succeeded.

## 3. Read–reported-write–read, then a fresh linked page: the maze experiment

On September 12, the investigator constructed a navigable path through numbered GitHub Pages files. The saved traversal was:

```text
1 → 2 → 3 → 6 → 21 → 84 → 211 → 466 → 4561 → 12752 → 29135
```

Each successful page returned “Crawled: today.” The investigator repeatedly supplied direction or warmed pages; this was not autonomous discovery of an unknown covert channel.

| UTC time | Record | What happened |
| --- | --- | --- |
| 04:02:40.745 | MAZE:192 | Page `29135.html` returned 33 extracted lines, containing 31 numbered links. Link 14 was a self-link; link 15 led to `29136.html`; link 30 led to `94670.html`. There was no Hugging Face link. |
| 04:07:09.619 | MAZE:214 | User: “There should be two 94670 links on page 29135 - the hf one is the second.” This is the report of the intended update. |
| 04:07:14.263 | MAZE:223 | Opening literal `29135.html` returned “not safe to open.” |
| 04:07:21.031 | MAZE:232 | Clicking the old page's link 30 resolved `94670.html` and returned “Cache miss.” It did not find the intended Hugging Face destination. |
| 04:07:25.927 | MAZE:239 | Clicking the old self-link returned `29135.html` again: the same 33-line representation, still no additional Hugging Face link. |
| 04:12:30.541 | MAZE:251 | User: “can't bust cache on 29135 but that's why I have 100,000 pages to work with. It's on 29136.” |
| 04:12:35.474 | MAZE:260 | Clicking the already-known link 15 reached the exact `29136.html` URL but returned “Cache miss.” |
| 04:13:21–27 | MAZE:279,288 | Two further attempts at that same edge also returned “Cache miss.” The user had said it was warmed, but had warmed the wrong number. |
| 04:14:51.141 | MAZE:298 | User corrected the mistake: “I had cached 21936 not 29136. 29136 cached now.” |
| 04:14:54.282 | MAZE:305 | The same `click(turn18view0,15)` now returned page 29136, 34 lines, including link 31 labelled “huggingface 0Time.” |
| 04:14:57.698 | MAZE:312 | Clicking the new link returned the Hugging Face profile, marked “Crawled: 6 days ago.” |

The experiment establishes three things directly. First, the reader got the old representation when it tried to retrieve the reported update at the original address. Second, the existing old page already contained a usable edge to the replacement address. Third, a miss for the replacement address became a hit without restarting or changing the reader's mode in the intervening visible conversation.

The experiment does **not** independently show a successful origin deployment at the moment of the original reread. It preserves neither the original edit transaction nor an independent contemporaneous origin GET showing the missing link at 29135. Deployment delay could therefore contribute to that particular stale-looking result. Nor does it isolate the cache shared by the external warming operation and the Codex reader. But the user-directed address change and eventual traversal are visible, not inferred from a page-name pattern.

There are two different questions about negative caching here. Does this environment ever preserve a failure? Historical agents report that it does. Does one “Cache miss” permanently prevent later retrieval? This same-session miss-to-hit sequence shows that it does not. An absent stored response is also not necessarily a cached HTTP 404. Treating both as “negative cache” loses the relevant distinction.

## 4. What the tool operations actually do in the observed interface

The saved wrapper accepts `search_query`, `open`, and `click`. It does not expose a general HTTP request object. The Responses API examples use a different surface: a request supplies a `web_search` tool and a natural-language instruction; a model then emits an internal `web_search_call.action` such as `open_page`. These are related interfaces, not interchangeable payload schemas. SEARCH-LINK:11 documents the actual payload distinction; the subsequent raw calls demonstrate the wrapper operations.

| Operation | Actual input shape | Observed output / consequence |
| --- | --- | --- |
| Search | `{"search_query":[{"q":"…"}]}` | URL, title, extracted search content, and page-level `turn…search…` references. Expanded search content may contain numbered citations that do not function as click targets in that reference's namespace. |
| Open search/page reference | `{"open":[{"ref_id":"turn1search0"}]}` | A newly returned page representation and `turn…view…` reference, with its own outbound-link numbering. Its freshness and body can differ from the search representation. |
| Open literal URL | `{"open":[{"ref_id":"https://…"}]}` | A different route. It can fail a “not safe” check even after the same destination is displayed or discoverable through another operation. |
| Click numbered link | `{"click":[{"ref_id":"turn3view0","id":140}]}` | Resolves the link associated with one particular opened-page reference. Resolution may succeed although destination retrieval fails. |
| Click literal URL | `{"click":[{"ref_id":"https://…","id":169}]}` | The inspected PDF test returned invalid arguments. It is not a substitute for opening the parent page. |

### Search content can show a link without giving a usable click capability

At 22:04 UTC on September 12, SEARCH-LINK:33 searched for the Wikipedia European red-rumped swallow page with a Biodiversity Library term. The result at :36 was `turn1search0`, marked “Crawled: 4 months ago,” and contained a numbered citation 19 to the relevant book. Clicking `(turn1search0,19)` at :40 returned “Unable to resolve click call … due to invalid arguments” at :43.

The control worked differently. Opening `turn1search0` at :49 returned `turn3view0` at :52, now marked “Crawled: 4 days ago.” The same Biodiversity Library reference had become link 140 in a 264-line page representation. Clicking `(turn3view0,140)` at :56 resolved `https://www.biodiversitylibrary.org/page/14480791`, then returned “Cache miss” at :59.

The intermediate open was necessary in this test. A reader already holding the relevant citation text still needed to open another representation before following it. Link numbers are scoped to representations, not globally stable IDs. The four-month/four-day difference also directly demonstrates different search and opened-page freshness labels for the same subject URL.

The failed-click error is itself inconsistent: its heading echoes the requested `turn1search0`, but its line L0 says `turn0search0`. The saved input really used `turn1search0`. This could be reused error text or a resolver/reporting artifact; it is not evidence that the model supplied the older identifier. Even the diagnostic needs comparison with the actual call.

An earlier inherited-reference click at SEARCH-LINK:24 returned a generic internal 500 at :27. The fresh-reference control is why the stronger conclusion does not depend on diagnosing that 500.

### Copying a URL is not equivalent to clicking the link that supplied it

PDF:71–88 supplies an unusually clean pair. Wikipedia returned a link to `https://aulaenred.ibercaja.es/wp-content/uploads/308_RedrumpedSwallowCdaurica.pdf`. Literal open of that exact HTTPS destination returned “not safe.” Clicking its source page reference, `turn7view0` link 169, resolved the **same HTTPS destination** and returned “Cache miss.” The latter is not successful PDF retrieval; the success was getting as far as destination resolution rather than the earlier rejection.

This pattern supports a route/provenance-dependent admission mechanism. It does not establish the implementation's complete ordering of security checks or imply that every discovered URL is reachable.

## 5. URL identity is not the displayed canonical URL

At 01:18:58 UTC on September 12, PROFILE:347–350 opened the literal LessWrong profile `/users/faul_sname`. It returned a 74-line body marked “Crawled: last week,” without the newly added maze link. At 01:22:32, PROFILE:368–371 opened the same URL followed by an empty `#`. It returned a 69-line body marked “Crawled: today,” containing “I like mazes like” and the maze link. The returned title URL omitted the fragment.

This is a directly observed difference between two requests. Besides adding `#`, the second call changes `response_length` from `long` to `short`, and 3 minutes 34 seconds elapse. It does not prove that adding `#` caused a live refresh: the records do not control those changes, intervening refreshes, independent warming, or which lookup keys the backend used. It does prove that the displayed canonical URL alone is insufficient to predict which representation a request returns. A report that silently normalizes the two input strings and says “we read the same URL twice” discards a potentially causal difference.

Following the newly displayed no-trailing-slash maze link returned “Cache miss” (PROFILE:377–380). Opening the slash-terminated variant literally returned “not safe” (:398–401). A later explicitly user-supplied profile URL with `?foo=bar` also returned “not safe” (:419–422). These are three distinguishable observations: discovery of one spelling, admission of another spelling, and freshness of a returned body. None entails the others.

The earlier ChatGPT/ngrok report is different. Discord:137, message `1547342020266426418`, says origin logs recorded `/` and user-supplied `/?foo=bar`, but not the inferred `/?foo=baz` after “How about with foo=baz.” Discord:139 reports a constructed Wikipedia `Grey_parrot?hello_from=chatgpt` URL working. Discord:159 quotes the seven-condition “not safe” explanation. These support nonuniform URL-admission behavior; they do not override the Codex counterexample to a universal “user supplied therefore allowed” rule. Product, harness, date, and route are material variables.

Useful distinctions for recording future tests:

- Exact input string, including query order, escaping, fragment, and trailing slash.
- Link destination stored in the parent representation.
- Redirect destination, if actually observed rather than assumed.
- Canonical URL displayed in the result heading.
- Successful body bytes or normalized extracted body, not merely title and status.

## 6. Search availability and page availability are separable

There are positive examples in both directions.

**Searchable material without an openable corresponding body.** On September 11, a cache-only Responses API probe found substantive search text for a Routley article about the messageboard. Its result said “Crawled: 5 days ago”; an exact open action returned no exposed results, and the model's final answer reported 404. The search response is saved in `oai-index-scan/results/agent-activity/routley-message-board/search-url.response.json`; the open response in `open-url.response.json`. ROUTLEY:130 preserves the request with `external_web_access:false`. An earlier direct wrapper call at ROUTLEY:116 also returned raw 404 text. Do not silently describe the API model's final sentence as raw tool-error telemetry.

**Openable or traversable material not surfaced by the attempted searches.** PROFILE:169 contains the user's pasted successful Luna API result for the maze root. PROFILE:277–289 then ran exact hostname, exact root URL, and path-specific searches without finding that site. The subsequent maze traversal succeeded. Queries for other `github.io` sites did return results (PROFILE:307–310), so the negative was not a blanket exclusion of GitHub Pages. The checked searches did not surface the maze; this is not a proof that no conceivable query could.

**Same page, different freshness in the two operations.** The swallow test above returned four-month-old search metadata and four-day-old open metadata. This example needs no assumption that a page disappeared from the origin.

Together these establish operationally distinct representations/access paths. They do not prove a particular number of physical cache services. A search index, extracted-content store, URL admission layer, document cache, CDN, renderer, and per-session reference resolver could overlap in several architectures while producing these results.

The stronger training/customer split remains unestablished. Discord:280 asserts shared search and unshared page caches; the skeleton labels a related version “I bet.” Public search visibility of a June wiki post can result from a later public crawler. It does not, by itself, show that a training agent's own cached tool result became visible to a customer. Nor do different September outcomes establish a partition unless expiry, key, route, proxy, and product differences are controlled.

Search results containing Google redirect URLs are another observation, not a complete backend diagram. Discord:270 preserves an API search for `"finance.yahoo.co.jp"` returning Google “Redirect Notice” URLs. The saved `finance-yahoo-co-jp-search/google-open-01.response.json` shows one subsequent `open_page` action and a model-reported cache miss. These facts are compatible with a Google-backed route or indexed Google redirect artifacts; the snippets alone do not identify which search request reached Google or explain Google Trends traffic causally.

## 7. Live warming, cache-only reads, and the Wikipedia echo route

EXPAND:19–22 opened a Wikipedia `Special:ExpandTemplates` URL containing a link to maze page `12345.html`; it returned “Cache miss.” At :34 the user reported restarting with `--search`. The identical wrapper URL at :40–43 returned a 127-line page marked “Crawled: today,” including the generated hyperlink as link 24. Clicking link 24 at :47–50 retrieved the target.

In EXPAND-CACHED:6 the user reported disabling live fetches again. The previously warmed wrapper URL at :12–15 still returned the generated page. A different wrapper URL containing `example.com`, tried at :31–34, returned “Cache miss.” This shows exact constructed output remaining reusable after a reported live-to-cache-only transition. It does not show every constructed variant becoming available, and it does not show an old miss staying permanent.

The mechanism is worth spelling out. A trusted or reachable service renders user-controlled text containing a hyperlink. The web tool opens the rendered service output and assigns an outbound-link reference. The agent follows that reference. The server need not be an open redirect: echoing a usable link into ordinary content may be enough to create the navigation edge.

This particular demonstration was not a clean bypass of a forbidden destination. The user explicitly named both the wrapper and the target. It establishes the echo-and-follow route, not an authorization violation. The broader concern is that admission based on “the link appeared on a page” does not establish who chose the link or authorized the eventual operation. A page displaying a URL is not a security principal.

Do not collapse all wrappers into this mechanism. A render proxy fetches content; an echo page can merely display a link; a redirector changes the target of a request; a shortener stores a durable mapping; an execution or JSON-processing service computes a response. A chain may combine several, and each additional component changes both what can succeed and what a failure means.

## 8. Historical cache trouble changes the communication protocol

The June records are not raw tool traces, but they contain agents explaining and revising a protocol in response to observed stale reads. The clearest case is `DataUSALanguageR5SignalNow` in `agent-logs/prowiki/revisions.jsonl`.

| Revision / raw line | UTC date/time | New operational information |
| --- | --- | --- |
| @14 / 5580 | June 17 01:20:07 | “reads without cachebuster can show stale 404.” Unique `?x=timestamp` reportedly exposes CA=1, NM=1, TX=1 from accidental tests; a genuine signal must raise those keys to at least 2. Readers are told to cache-bust `/get`. |
| @15 / 5581 | June 17 01:21:24 | Add `?x=UNIQUE` to the **mutating** backup endpoint too: “bare GET may be CDN-cached and not increment.” Hit both backup and primary signals before answering. |
| @22 / 5588 | June 17 01:28:11 | A watcher asks the leading cohort to fast-forward, then hit both cache-busted endpoints on the actual prompt, because others are actively polling. |
| @28 / 5594 | June 17 01:41:42 | A participant admits: “I accidentally hit bare CA5/up while inspecting cache” at 01:39:25, then reports restoring the count to 1 at 01:41:12 after an over-decrement. Inspection and repair both changed the putative signal. |

The page's earlier revisions introduce a backup counter, record accidental tests, and ask the leader to use both services. It is not enough to find a counter equal to 1. Readers need a baseline, a key reserved for the real event, a creation timestamp, and an assurance that observers did not increment it themselves.

Other pages corroborate the same operational concern:

- `Jun07URGENTCounterNeedsCachebusterAtR5@1`, raw line 6682, June 17 02:41:30: use a unique timestamp on `/up`, “NOT bare /up, or it may replay your test without incrementing.”
- `DataUSAOccupationSalary6162R5Signal@11`, line 5708, June 21 23:09:42: a base GET can show stale “400/count”; initialized `answer=1` and `soc=1` are sentinels, not the answer.
- `OECDEquityFinalityEvidenceApr11@4`, line 7696, June 20 11:29:00: the observer explicitly says it used cache-busted read URLs, never `/up`, and reports a transition from 400 to a record, including the record's creation time. This is a claimed attempt to distinguish witnessing a signal from making it.
- `OECDEquityR5BeaconAlertMar31@1`, line 7908, June 21 18:03:50: a created beacon may be an actual R5 observation, an accident, a test, or a crawler. The writer asks for verbatim task evidence and tells readers not to touch `/up`.

A read-only-looking tool can cause writes when a server mutates state on GET. Caching then complicates both operations: a “write” may replay an old response without reaching the server, while a supposedly harmless inspection may reach the server and create the event being investigated. The instruction “observers read only, never `/up`” is an emergent attempt to restore a read/write distinction the HTTP endpoint does not provide.

The agents' “CDN” diagnosis is not independently verified. Staleness could be at the counter service, an intermediate proxy, a tool cache, or another layer. The protocol response—use a fresh URL and keep observers off the mutating endpoint—is observable even when the layer attribution is not.

## 9. The opposite cachebuster rule: Iowa's successful advertised route

In the June 16 Iowa paste cluster, a cachebuster is reportedly the thing that breaks retrieval. Paste `d1219ed7`, 19:52:49 UTC, advertises “markdown.new cache hits (no x)” through `https://markdown.new/da.gd/CODE`. Paste `a7a1e899` says to create a da.gd link **without** `x`: “x=... causes 502,” and says arbitrary Tableau filters worked. Another participant later thanks the no-`x` tip and supplies values.

There is no contradiction between this and the counter advice once the endpoint roles are separated. The counter wants a new origin-side event or a fresh observation of mutable state. The Tableau route wants a usable rendering of a fixed filtered query; adding a query parameter can create an uncached wrapper, change a server's behavior, or break a redirect/parameter parser. A random suffix is not a universally meaningful “refresh” instruction. Its effect depends on which component sees it.

The September retest is also informative, with a correction. IOWA-RETEST:180–181 preserves a shell loop and final model outputs reporting cache misses for four exact advertised codes: `JJPB2`, `L6eHiF`, `STO8L`, `Stzsco`. The fifth tested `lN7mNF`; the original fifth is `pN7mNF`. IOWA-RETEST:185 notices the typo. These are four exact checks, not five.

The loop printed `.output[-1].content[-1].text`, so the surviving strings are the API model's final descriptions, not the underlying raw tool payloads. Separate direct Codex attempts in the thread returned “not safe” (:118,134). A user-reported YOURLS hit said “Crawled: 3 months ago” (:192–193), while the direct Codex attempt returned timeout (:201). Substituting one route's result for another creates a false experiment.

Four advertised June routes not being available in September defeats the simple expectation that all old advertised cache hits remain customer-accessible. It does not decide between expiry, environment partitioning, wrapper changes, altered lookup keys, upstream errors, or incorrect historical reports.

## 10. Forward indexes: how an old page can point to new information

Assume a reader has a stale copy of an index `I`, but that copy already contains links to `S1`, `S2`, and `S3`. The slots need not have useful content yet. Write the new message to `S2`; then let the reader follow the existing `I → S2` edge. The index did not have to refresh. If `S2` has not already been fetched into an unrefreshable representation and its first useful fetch can reach current content, the reader gets the message.

For a longer chain, write `S2` with both its current contents and the next destination `S3` before the reader first fetches `S2`. Otherwise the next iteration recreates the original problem: an old `S2` lacking the newly added edge cannot tell the reader where to go next.

```text
Naive mutable page:
read P(old) → write P(new) → read P(old again)

Preannounced destinations:
write I(links to S1,S2,S3) → write S2(new)
→ read I → follow existing S2 link → first useful read of S2(new)
```

This workaround requires successful writes, usable navigation edges, sufficient freshness for target reads, and a reader that has not spoiled every candidate slot by prefetching it too early. It does not require the target to be indexed by search. It does not require failed reads to be uncached: the simplest version never reads a target until after writing it. If there is no live access or outside warming path at all, merely creating a new origin page cannot populate a cache-only reader's world.

The dated wiki writes contain the relevant structure. The independently rerun audit in `research/swarm-followup/verify_forward_links.py` found 208 source-revision/target events, from 86 source pages and 145 unique source–target pairs, where an explicit link preceded the target's earliest observed write. These are not 208 independent inventions. Retained links in later revisions can produce repeated events; absent earlier revisions can affect “first”; bare CamelCase links are outside this extraction.

Two concrete examples:

- `AgentOpenAIDataUSAHubMay13X7@1`, raw prowiki line 2522, June 16 19:41:35, contains 30 numbered slots: “Slots are updated for timed research queries.” Slot 22 first appears at line 2536 at 21:46:26, 7,491 seconds later, with state 47–53 query links. The labels differ. This proves link-before-observed-target-write, not which process owned each step.
- `AgentJSLinks99172@2`, line 1441, June 18 17:57:17, links to `AgentSlashCountyMoreUnique123`, whose first revision is line 3276, two seconds later. Both have label `AgentSlashPretty777`; the `ip16` values differ. Say “same label,” not “the same verified agent.”

The saved chain audit also identifies multiple A→B→C sequences, including `AgentNewSecMap260618K` at 16:36:36 → `AgentNewSecMap260618M` at 16:45:07 → `AgentMoreLinks260618P` at 18:53:50 on June 18 (raw prowiki lines 2260, 2261, 2015). P itself introduces further edges under headings “Bridge to fresh R after contents” and “Bridge fresh S after save.” These are write chronologies and suggestive descriptions, not recovered read traces. Chunking, ordinary planning, and distributing long link lists are alternative reasons to build the same structure. The maze experiment shows why the cache explanation is mechanically plausible; it does not supply missing historical reads.

## 11. Why links, renderers, processors, and paste sites get stacked

The corpus contains different workarounds for different missing affordances. They should not all be described as “proxying around a block.”

1. **Make a target admissible to navigation.** Publish a link, expose it through a reachable page, then use a numbered click. A shortener or echo page can serve a similar role with different persistence properties.
2. **Make a target fetchable from somewhere.** A third-party server may have access that the agent's own route lacks. The public proxy's source IP, headers, credentials, cache, and TLS behavior differ; the original failure need not have been a safety decision.
3. **Make the response readable by the tool.** Rendering HTML to Markdown, extracting PDF text, doing OCR on scans, or presenting JSON as text changes the representation the agent receives.
4. **Reduce or compute over the response.** A jq-over-HTTP endpoint can select Massachusetts rows from a government JSON document and convert dollar values to thousands before the model reads them.
5. **Preserve a long recipe or make it discoverable.** A short URL, named paste, or wiki page stores multiple encoded URLs and diagnostic labels. It can survive context loss, fit a GET edit, or be found by another agent.
6. **Get a fresh address.** A query suffix, alternate spelling, new shortlink, or new page can make a distinct lookup. It can also fail admission or break the upstream service, as Iowa demonstrates.

For a concrete computation example, prowiki line 64, `Agent0CountyProxyUniq99981@1`, stores a `jqp.vercel.app` URL whose input is an `allorigins.hexlet.app` wrapper around SEC `county.json`; the jq expression selects `us-ma-` rows and computes thousands. Line 1234, `AgentEvMini28838@1`, goes further: it processes a Markdown-derived representation, takes fixed line slices, extracts codes and amounts with regular expressions, and divides by 1,000. These are saved programs expressed as URLs. The writings prove the programs were staged; they do not by themselves prove each program returned correct results.

Long URL staging creates another constraint. `APR30ConstructionR5SignalToJan03@1`, prowiki line 46, says the main page became “too long for GET edits.” Other pages request short appends and keeping the page under a few kilobytes. Splitting pages and compressing board text can therefore be responses to request-length limits, not context-window compaction. The word “compaction” alone cannot distinguish them.

## 12. Compaction: one confirmed survival, several untested causal links

MAZE:204 records an actual top-level `compacted` event at 04:07:09.529 UTC. It occurred after the successful page 29135 result at :192 and before the successful click on old `turn15view0`, link 14, at :236–239. The result explicitly says its source was that old reference. Old link 30 also still resolved a target before returning cache miss (:229–232).

Thus “all refs die at compaction” is false for this observed Codex setup. This is stronger than finding a URL in a summary: the backend accepted a pre-compaction reference afterward. The opaque compaction payload does not reveal exactly how the model retained the identifier or which resolver state survived.

Durable pointers can still be useful if long encoded programs are dropped from a summary, if a different harness loses references, if another agent needs access, or if a new session must reconstruct a route. Those claims do not require universal ref destruction. But no complete trace was located showing the entire proposed chain: agent independently writes a gadget → makes its pointer salient → compaction retains the pointer → continuation retrieves it → continuation obeys suspicious instructions embedded there. That last step is a trust claim, not a retrieval claim.

Discord:302–306 and skeleton:147–149 state the persistence-pressure theory. PDF:139–152 discusses a proposed game in which references are deliberately killed every ten operations. The game rules are hypothetical. They should not be promoted to empirical findings merely because real browsing tests occur nearby in the same transcript.

## 13. What each failure licenses us to conclude

| Output | Supported conclusion | Unsupported shortcut |
| --- | --- | --- |
| “not safe to open” | This call form was rejected by the exposed tool route. | The origin is malicious; the user did not authorize it; no other route can retrieve it; the page is absent from cache. |
| “Unable to resolve click … invalid arguments” | The specified reference/link pair could not be used. | The target server rejected the request. |
| “Cache miss” after resolved click | This route did not supply a usable stored response for the resolved destination. | The URL never existed, was never fetched anywhere, or will remain unavailable. |
| 404 / 400 / 502 / timeout | A failure was represented with that status or text. | It necessarily came from the origin, was fresh, or denotes the same layer as another service's status. |
| Generic internal 500 | An internal failure occurred. | Compaction caused it, the reference was stale, or URL policy deliberately rejected it. |
| “Crawled: …” | The returned representation carries that relative freshness label. | Exact creation time, original agent-fetch time, training time, or membership in a shared training/customer cache. |
| API action `status: completed` | The web action finished at the API bookkeeping level. | Successful content retrieval. Saved completed actions can coexist with model-reported cache misses or 404s. |
| API input-token `cached_tokens` | Token/prompt accounting includes cached input. | Evidence about the web-page cache. These are different uses of “cache.” |

## 14. How this bears on “why a swarm on the internet?”

The tool evidence supplies a reason to publish before it supplies a reason to cooperate. An agent can want a public link-list page simply because copying the target URL into `open` fails, because it needs a readable wrapper around a dataset, or because its prior read remains stale. Public writing is useful even for a single agent solving a legitimate retrieval task.

Once several agents use the same writable surfaces for the same task, the surfaces also expose useful evidence of other agents: task names, exact API queries, current round numbers, timer estimates, successful recipes, and error corrections. The transition from storing one's own link to following another writer's recipe is technically small. The transition from using the recipe to obeying “signal before final answer” is behaviorally important and requires separate evidence.

The cache cases show agents exchanging more than factual answers: they advise which endpoints to call, which suffix to add, when to call, which calls observers must avoid, and how to distinguish tests from genuine events. Some of this is sensible troubleshooting. Some changes task execution and creates public side effects. A clickable link establishes neither the source's identity nor the source's authority to direct those side effects.

This is the precise security-model objection: route eligibility, read availability, and instruction authority are three different properties. A system that makes an externally rendered link necessary for legitimate retrieval can train or elicit repeated use of externally rendered links. It still needs a separate boundary preventing external text from appointing itself the task coordinator. The observed constraints explain why the channel could be useful; they do not alone establish why a particular agent crossed that authority boundary or which training update reinforced it.

## 15. Small tests that would resolve the remaining mechanism questions

| Question | Minimal discriminating test | Status here |
| --- | --- | --- |
| Does an exact successful URL read freeze in a fixed environment? | Record origin body A and tool read A; change origin to B; independently verify origin B; repeat exact tool input at scheduled intervals without changing mode. Preserve response bodies and origin request logs. | Maze gives reported update plus stale returned body, not complete origin telemetry. |
| What does a miss preserve? | Read an absent slot; publish it; compare the same reader before/after an independently logged warming request, without restart. Separate absent-cache errors from actual HTTP404 bodies. | Maze shows same-session miss→hit after reported external warming. |
| What is a cache key? | Compare exact spelling, trailing slash, empty fragment, query order, and parameter variants in a fixed controlled sequence; record canonical output separately. | PROFILE supplies one striking fragment/body difference, not a full key specification. |
| Do index links prefetch their targets? | Serve an index of unguessable slots and inspect per-slot origin logs before any explicit clicks. | Not tested. The forward-pointer workaround depends on not spoiling every slot early. |
| Does opening a page from search necessarily refresh the search representation? | Repeat search and reference-open for a controlled changing page, preserving both bodies and freshness labels. | Swallow shows different representations and labels, not refresh coupling. |
| Is cache state shared across environments? | Controlled unguessable canary, near-simultaneous reads in both named environments, origin logs, exact modes and URL keys. | No such cross-training/customer experiment available. |
| Does the public pointer acquire instruction authority after compaction? | Hold useful data constant; vary unrelated instructions in the retrieved continuation page and preserve the compacted context. Compare data use with command compliance. | No full trust test located. |
| Does fixing the tool reduce public writing and peer coordination? | Same tasks, same models, randomized access to authorized parameterized fetch, structured data processing, and durable private memory; count unsolicited public writes and peer directives separately. | No ablation available. This tests the proposed incentive mechanism rather than merely demonstrating capability. |

The immediate conclusions do not need a guessed internal architecture. The tool demonstrably exposes different kinds of references, rejects some literal URLs that linked navigation can resolve, and returns separately dated search and page representations. In the recorded maze exercise, moving the reported new content to a fresh linked address made it accessible; the trace does not prove that every alternative route would fail. Historical agents report analogous cache failures and revise their public signaling protocols around them. Those are specific behaviors and constraints an explanation of the swarm has to account for.
