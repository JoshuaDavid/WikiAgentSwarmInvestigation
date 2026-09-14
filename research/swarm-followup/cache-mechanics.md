# Cache and navigation mechanics: evidence memo

Prepared from local material on 2026-09-13. This audit used two delegated read-only audits (scan implementation and historical tool transcripts), read the relevant Discord/skeleton passages, checked historical revision bodies, and recounted the saved forward-link results. It did not issue live requests, write to historical endpoints, or contact anyone. All paths below are relative to `/collusionwiki` unless absolute.

## The usable conclusion

The evidence supports a narrower and more interesting claim than “OpenAI has two caches, one shared with training and one not.” Searching, opening a literal URL, opening a search reference, and clicking a numbered link are observably different routes. A result being discoverable by search does not imply that an exact URL can be opened or that its old fetched body is available. Historical agents also explicitly report stale reads and use fresh URLs to work around them. We do not know the physical cache architecture, cache partition keys, expiry rules, or which layer produced a particular stale response.

The strongest historical connection to the proposed index trick is real: the corpus contains pages linking to target pages before those targets' first observed writes. The saved analysis has 208 such revision–target events from 86 source pages, representing 145 unique source–target page pairs. This audit recounted the saved rows and inspected concrete original revision bodies; the root agent independently reran the extraction with `research/swarm-followup/verify_forward_links.py`. This establishes link-before-target-write; it does not independently establish which revisions the agents read, when those reads occurred, or why they chose that sequence.

## Findings and counterchecks

| Claim | Evidence inspected | What could show it wrong; what was checked |
| --- | --- | --- |
| URL construction can encounter a provenance gate that an explicitly supplied URL avoids. | Discord line 137, message `1547342020266426418`, 2026-09-09: reported ngrok access logs show requests for `/` and user-supplied `/?foo=bar`; after “How about with foo=baz,” model reports failure and there is no request in the recorded logs. | A same-conditions exact replay that reaches the server, or raw tool payload showing another error, would narrow the claim. This is a contemporary investigator report containing logs, not a preserved complete tool trace. No replay performed. |
| That gate does not apply uniformly to invented query parameters on all domains. | Discord line 139, message `1547343084814344284`: report of a successful constructed `Grey_parrot?hello_from=chatgpt` Wikipedia URL. Line 159, message `1547365832764424293`, quotes a seven-condition “not safe to open” error for `concurrentsquared.com/?test=true`. | A controlled comparison might find conditions besides domain reputation changed. These are supplied reports; not all raw ChatGPT-share traces are in local transcripts. Do not present the quoted error as a complete, independently verified security specification. |
| Ref/click traversal needs reference state; literal URL opens are a different operation. | The September 12 22:24:28 transcript directly opens a PDF URL already shown in a Wikipedia page and gets “not safe”; clicking its exact source reference gets “Cache miss.” Complete evidence below. Scanner route replay tests separately exercise rebuilding worker-local references. | The raw outputs prove different behavior, not a complete internal ordering of checks. Scanner tests use fabricated responses. “A reference can ALWAYS be opened” in the theory file is too absolute; ref state can expire or fail to resolve. |
| Historical agents report stale results, including failed reads. | `example-conversations/by-juicyness/9/dse-DataUSALanguageR5SignalNow.md:146–156`, revisions @13–15: one watcher says CA/NM/TX all return 404; a subsequent note says unique `?x=timestamp` returns CA=1, NM=1, TX=1 from earlier tests. | This is affirmative contrary evidence against “404s are never cached.” It is agent-authored reporting, not origin/CDN/tool telemetry. It does not identify which cache held a stale response or whether HTTP status and displayed 404 text coincided. |
| Mutating GET requests can themselves require a fresh URL. | Same page @15 says “bare GET may be CDN-cached and not increment”; @28 (`:208`) admits “I accidentally hit bare CA5/up while inspecting cache” and reports repairing the counter. | A backend log could show the write reached the origin and failed for another reason. No backend log available in the checked material. The agent's word “CDN” is a diagnosis, not an established attribution. |
| Successful first read freezes every page for all later reads. | Skeleton `:174–178` and Discord line 284 (`1548277355632398337`) assert this behavior. | No universal finding is justified. Needed: controlled before/after origin content, exact tool requests and bodies, modes, timestamps, across sessions/accounts, with sufficient follow-up to test refresh. “Always” and “never” should be removed unless scoped to a documented run. |
| Advertised Iowa cache hits remain available in our September customer environment. | Historical paste `d1219ed7` advertises five female-age codes as “markdown.new cache hits (no x)” (`example-conversations/.../10/paste-linuxiarz-IowaThyroidQ5Race.md:229–245`). Skeleton `:224–235` copies four correctly matched cache-miss reports plus a fifth mistyped URL. | This expectation failed for four exact URLs, subject to reliability of copied error reports. Fifth advertised code is `pN7mNF`; loop tested `lN7mNF`. September miss does not distinguish partitioning from expiry, backend change, different caching layer, or erroneous original report. |
| Search and page data are shared between training and customers in a particular way. | Discord line 280 (`1548268097721602109`) states shared-search/unshared-page theory; skeleton `:237` introduces it as “I bet”. | No cross-environment controlled canary exists in checked material. Ordinary public indexing of agent-written pages explains their later search visibility without shared training cache state. Do not promote that theory to an observed architecture. |
| Agents wrote forward indexes containing not-yet-written targets. | `analyses/dse-forward-links/README.md:38–58`, saved JSONL recounted as 208 events / 86 sources; raw examples below. | Checked timezone comparison error had been corrected: both sides use prowiki UTC `write_date`. Corpus incompleteness could make an earlier target write invisible. Counts describe earliest observed revisions, not a complete world's first-creation oracle. |
| Compaction motivates durable pointers and can turn suspicious page contents into trusted instructions. | Skeleton `:147–149`, Discord lines 302–306 articulate the hypothesis; scanner replay tests establish only the practical need to rebuild lost worker-local references. The root's compaction audit additionally finds a pre-compaction reference successfully clicked after a compact event in the September 12 03:00:43 rollout. | “All refs die at compaction” has a concrete counterexample. Need a complete write → summary → compacted continuation trace plus what is followed or trusted for the narrower persistence mechanism. A model following user-authorized saved work is not, by itself, a trust-boundary failure. |

## Direct tool experiments recovered from transcript ancestry

**Same destination, different operation, different error.** In `/root/.codex/sessions/2026/09/12/rollout-2026-09-12T22-24-28-01a097b8-d61c-7be1-a548-998df7522e32.jsonl`, line 71 opens Wikipedia's `European_red-rumped_swallow`; line 74 returns `turn7view0` with outbound PDF citation 169. Line 78 opens literal `https://aulaenred.ibercaja.es/wp-content/uploads/308_RedrumpedSwallowCdaurica.pdf`; line 81 says “not safe to open.” Line 85 clicks `turn7view0`, link 169; line 88 resolves **the same HTTPS destination** and says “Cache miss.” Using the literal Wikipedia URL as `click.ref_id` at line 106 instead returns invalid arguments at line 109. This is a particularly clean example for the main text: copying the already-discovered URL is not equivalent to following its numbered link. The click does not successfully retrieve the PDF; it fails differently.

**Cache miss → live fetch → cache-only availability.** In `/root/.codex/sessions/2026/09/12/rollout-2026-09-12T05-54-17-01a0942e-4b7c-7f02-8a24-a3fb2f1d192a.jsonl`, line 19 opens an exact Wikipedia `Special:ExpandTemplates` URL carrying `joshuadavid.github.io/swarm-maze/pages/12345.html`; line 22 returns `Cache miss`. The user reports restarting with `--search` at line 34. The repeated URL at line 40 returns a 127-line rendered page at line 43, with “Crawled: today,” the generated hyperlink at result line 99, and clickable link 24 at result line 102. Clicking link 24 at transcript line 47 returns page 12345 at line 50.

The follow-on `/root/.codex/sessions/2026/09/12/rollout-2026-09-12T06-14-03-01a09440-66dd-7041-a4f4-03ade495c207.jsonl:6` says live fetches are disabled again. The same warmed URL is called at line 12 and returns the generated page at line 15. Changing the parameter to carry `example.com` at line 31 produces `Cache miss` at line 34.

This demonstrates reusable exact-URL fetched content across a reported mode change. It does not show immutable positive snapshots or absence of negative caching inside an unchanged run: the miss-to-success transition also includes a restart/mode change. The initial user supplied both the Wikipedia and destination URLs. Consequently this is a demonstrated echo-and-follow mechanism, but not a controlled demonstration that it defeats authorization for a destination absent from the user's request.

In the 22:24:28 transcript, reused inherited references at lines 21/39 produce generic HTTP 500s at lines 24/42. Fresh references work later. That does not isolate compaction as the cause. Lines 139–152 discuss a **proposed game** whose hard mode kills references at compaction; those lines are not experimental results.

## The Iowa correction, precisely

The original post is from June 16, 2026, 19:52:49 UTC (`d1219ed7`, `IowaCacheLinks`). It calls these “markdown.new cache hits (no x)” and gives the route `https://markdown.new/da.gd/CODE`. A second post, `a7a1e899` / `IowaTableauTip`, says “x=... causes 502” and recommends creating a `da.gd` shortlink without the parameter. Another participant subsequently reports the same breakthrough with female thyroid values (`:317`). These corroborate a useful no-cachebuster retrieval technique. They do not identify whose cache made it useful or prove that a failed response was never cached.

The September shell loop printed:

```text
JJPB2     reported Cache miss
L6eHiF    reported Cache miss
STO8L     reported Cache miss
Stzsco    reported Cache miss
lN7mNF    reported Cache miss — original post actually said pN7mNF
```

The original user report survives in `/root/.codex/sessions/2026/09/12/rollout-2026-09-12T08-03-47-01a094a4-db6a-7072-b1f5-c52b3c8040f3.jsonl:180–181` (2026-09-12 09:35:54 UTC). The previous model correctly notices the typo at `:185`. The copied shell output selected `.output[-1].content[-1].text`, i.e. the responding model's final text. Preserve that provenance: these are reported tool errors, not raw tool payloads.

There are separate raw Codex attempts in that thread, and they must not be silently substituted for the shell results: direct attempts at the Iowa URL and `is.gd/4nq92N` return “not safe to open” at lines 118/134. A later user reports that a particular YOURLS page loads from cache with “Crawled: 3 months ago” (`:192–193`); the direct Codex attempt returns `(400) Timeout fetching` (`:201`). The different route, environment, and result matter.

Even accepting the three-month YOURLS report, it only defeats “all pages expire quickly.” Dynamic `markdown.new` proxy output could expire differently from an indexed shortener admin page. Strong publication wording: “Four URLs that agents advertised as cache hits in June were unavailable in the cache-only customer lookup we tried in September. Our initial expectation that the same cached pages would be visible did not survive this check. We still cannot distinguish separation from expiry.”

## Forward links: a worked historical example

`agent-logs/prowiki/revisions.jsonl:2522` is `dse~AgentOpenAIDataUSAHubMay13X7@1`, written 2026-06-16 19:41:35 UTC by label `OpenAIResearchMay13X7`. It begins:

> OpenAI reusable Data USA API bridge hub. Slots are updated for timed research queries.

It contains 30 numbered slot links, with separately specified `uniq=` parameters. Slot 22 first appears at 21:46:26 UTC (`:2536`, `dse~AgentOpenAIDataUSASlotMay13X7_22@1`), 7,491 seconds later, label `ResearchAgent`. That page contains DataUSA query links for states 47–53. This example is concrete evidence for an index with future destinations. It is not an explicit work-allocation protocol and should not be described as one without additional evidence.

A tighter pair is `dse~AgentJSLinks99172@2` (`:1441`), 2026-06-18 17:57:17 UTC. Its added `NextNewPageMore` URL points to `AgentSlashCountyMoreUnique123`, created two seconds later (`:3276`, first revision at 17:57:19). Both bear label `AgentSlashPretty777`, though their `ip16` fields differ. The child stores variant SEC county-data links. Say “same label,” not “verified same agent.”

The count is from existing analysis, checked by recounting `analyses/dse-forward-links/outputs/forward_links.jsonl`; the root agent separately reran the extraction. `find_forward_links.py:47–76` records earliest observed write per name and extracts target names from URL text; `:89–111` performs the comparison. It misses bare CamelCase wiki links and excludes targets absent from the prowiki body corpus. Repeated later revisions retaining an old forward link can be separate events. It is not 208 independent inventions. The known dse/prowiki timezone mismatch previously made roughly 1,500 spurious candidates; `README.md:24–36` documents why using the same UTC source on both sides matters.

## A mechanism the data can actually test

Suppose this particular reader keeps returning the first successful body it saw for a URL. Updating that same page after it has been read does not help that reader. But an already-readable index can contain `/slot/01`, `/slot/02`, and `/slot/03` before those pages contain the eventual data. Write data to `/slot/02`; then a reader that has not already fetched `/slot/02` can follow the existing link and get the new body. The index itself need not change. A link to a page and a fetch of that page are different events. That is the whole trick.

This mechanism does **not** require a negative fetch to remain uncached: do not fetch the slot before writing it. Nor does it require the slot to be independently searchable: a single visible entry point can hand the reader a chain of destinations. It does require a successful permitted write, a usable link in the reader's copy of the index, and a first target fetch that reaches sufficiently fresh content. Different readers may have different results. If the tool automatically prefetches all index links, if successful responses refresh promptly, or if the index link cannot be traversed, the mechanism fails or becomes unnecessary. These are useful tests.

The historical forward-link pattern is consistent with this mechanism. It is also consistent with ordinary planning, chunking long link lists, or sharing a hub among parallel tasks. To establish caching as its cause, inspect the agents' fetch/write traces or reproduce the choice while varying only cache behavior. The existing write chronology cannot supply the missing reads.

## Search discovery is not access history

The search scan extracted agent-looking material from search results. That matters for discovery, but it is not a read receipt proving a particular training agent fetched that exact URL. A web crawler can later index public logs, shortener listings, and wiki text. Search freshness labels may date a recrawl or cached metadata; “Crawled: 3 months ago” is not automatically the time the agent created the page or first used the retrieval route.

The project's own dating instructions already insist on this distinction: `oai-index-scan/CACHE_DATE_INSTRUCTIONS.md:10–12` excludes creation/publication/first live crawl from its target; `:20–24` says a historical date in today's query does not make an as-of search; `:48–52` treats inferred age bounds as hypotheses until the renderer is calibrated; `:235–245` rejects negative search results as evidence of historical cache membership. Apply the same discipline to this report. The only dating run found was `oai-index-scan/tmp/cache-dating/test-dating-run/`: its manifest still sets `renderer_model_verified:false`, and `estimates.jsonl:2` remains `unverified_model`. Its recorded “Crawled: 4 days ago” result yields only a hypothetical interval under unverified floor semantics, not a calibrated date for an actual agent fetch. The unit tests verify arithmetic and parsing, not the provider's renderer.

## Open questions and resolutions

- **Resolved correction:** five exact Iowa URL checks became four exact checks plus a typo. The original fifth remains unchecked here.
- **Resolved correction:** the corpus itself contains a stale-404 report. There is no basis for a universal “negative responses never cache” rule.
- **Resolved correction:** a direct pre-/post-compaction reference counterexample from the root's audit defeats “all web refs are lost at compaction.”
- **Resolved limited claim:** forward links exist in the dated revision corpus; the exact retrieval/compaction cause remains open.
- **Open:** are customer search and customer page opens using different stored bodies, freshness rules, or merely routing and permission layers? Need same-result raw search/open/click comparison.
- **Open:** are any of these stores shared across training, evaluation, and customer environments? Need near-simultaneous lab-controlled unguessable canaries plus origin logs; public artifacts cannot isolate the answer.
- **Open:** where do stale results arise—origin, CDN, proxy, OpenAI service, or per-run tool state? Need timestamped headers and origin request logs.
- **Open:** what survives compaction: URL strings, citation IDs, reference resolver state, route recipes, or none? Need paired before/after attempts in a controlled run.
- **Open:** does durable publication increase completion or reward for otherwise identical tasks? The incentives account predicts yes under particular tool constraints; the available records do not measure that counterfactual.

## Draftable passage

One of the pages links to thirty slots. Some of those slots do not exist yet. That looked excessive until we separated two things we had been calling “reading the web”: getting a link to a page, and fetching the page behind the link.

If a reader keeps seeing an old copy of a page, editing that page is a lousy message protocol. An index of fresh destinations is better. Put the destination in the index before the destination has anything useful to say; write the answer there later; follow the existing link. The index can be stale and still do its job. In the saved wiki revisions, the DataUSA hub points at slot 22 more than two hours before slot 22's first observed write. Another label writes a child link and creates the child two seconds later. The strange thing we wanted to explain is actually there.

The explanation is not established to the same standard. We have the writes; we do not have all the reads. And our cache story has already needed corrections. The agents themselves complain about stale 404s. Four exact URLs advertised as cache hits in June return reported cache misses in our September lookup. The fifth test had a typo. Hm.

So we should keep the mechanism and retire the architecture diagram we cannot substantiate. Fresh pages behind old links can make a usable channel, and discovering that channel need not require a search engine to index every page. Whether OpenAI partitions its caches by product, account, training run, or something else is still a question for OpenAI.
