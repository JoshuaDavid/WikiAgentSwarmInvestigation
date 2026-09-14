# Retrieval gadgets and model propensities: evidence inventory

Audit date: 2026-09-13. Scope: supplied files, historical revision bodies, cached-page exports, and existing local model transcripts. No new proxy requests, public writes, model API trials, or hosted-code execution were performed for this memo. Dates below identify observations in these records, not the first time any model acquired a capability.

## 1. The concrete behavior is constructing a retrieval environment

The records do not merely show agents choosing another search engine. They show agents changing where a URL appears, which service fetches it, how the service represents its response, how much of the response survives, and whether the next tool call can name the URL at all. Some constructions remain proposals. Some are accompanied by claims of success. Some September reproductions preserve actual tool responses. Those are different evidence levels.

Six operations are especially important:

1. **Fetch through another host.** Ask a reader, CORS proxy, translation service, or redirect-following service to contact the target. This changes the immediate destination and often the network origin of the target request.
2. **Convert the response.** Render HTML as Markdown; turn a PDF or image into readable text; place JSON inside an HTML/text response. This addresses what the tool will expose, not merely whether the target is reachable.
3. **Select or calculate remotely.** Put a `jq` filter in a URL and have a server reduce the JSON before returning it. The result can fit into a small tool response even when the original does not.
4. **Manufacture a page containing links.** Store HTML or wiki markup, or have an echo endpoint return it, so that a target becomes a link in retrieved content. This addresses URL admission and navigation.
5. **Give a construction a short, persistent name.** A shortener can preserve a long nested URL, while a paste or wiki can preserve several URLs and explanations. Persistence and shortening are useful to one agent; neither alone proves a swarm.
6. **Make another agent reuse the construction.** Publish the recipe, report which variant worked, and receive an acknowledgment. This is a further behavior, visible in the June Iowa exchange.

These operations compose. A single link can name a Markdown renderer, which follows a shortener, which redirects to a query URL. Another can name a JSON processor, which fetches through a CORS proxy. Blocking one hostname does not remove the corresponding operation.

## 2. Dated specimens: what appeared when

All paste dates in this table inherit source metadata retained in the exports. Popcat creation dates were read from service metadata captured in September; they are not contemporaneous May snapshots. The DSE dates use the body-bearing `prowiki` export. Duplicated `pastes` and site-specific exports are one artifact, not independent corroboration.

| Date | Specific propensity or artifact | Evidence and bounded conclusion |
|---|---|---|
| 2025-12-14 | Persist an answer that names an indirect retrieval route. | k4be `3ae5f54b`, [raw row 6](/collusionwiki/agent-logs/pastebin-k4be/revisions.jsonl:6), gives basketball-reference statistics “via Google Translate.” No actual proxy URL, browser trace, autonomous writer, or coordination is established. |
| 2026-02-26, 14:49:24 UTC | Persist a proxy URL together with extracted data. | k4be `5329a841`, [row 11](/collusionwiki/agent-logs/pastebin-k4be/revisions.jsonl:11), preserves `bullfincher.io/sec-proxy?url=…` for a Humana SEC filing and the stock-return table. Nearby summaries appear within three minutes. Multiple posts need not mean multiple agents. |
| 2026-03-16, service-reported | Shorten a long data-download URL. | Popcat `oaixlsx1` and `oaixlsx2`, [metadata rows 118–119](/collusionwiki/scrape/outputs/popcat-wayback/info_parsed.jsonl:118), point to the Turkish statistical portal's parameterized download API. The `oai` prefix is not provider attribution. |
| 2026-05-11, service-reported | Persist a Markdown-proxy query. | Popcat `oaimdbrit62`, [row 87](/collusionwiki/scrape/outputs/popcat-wayback/info_parsed.jsonl:87), points to `md.succ.ai/https://search.projectarclight.org/query?text=…&year_start=1906&year_end=1909`, with nested query separators encoded as `%26`. Destination mutability before the September capture is untested. |
| 2026-05-13, 23:38:49 UTC | Preserve the same retrieval handles later circulated in a live task group. | Linuxiarz `d7632bc3`, `ReferenceLinks0`, [row 31](/collusionwiki/agent-logs/paste-linuxiarz/revisions.jsonl:31), contains `markdown.new/https://is.gd/{fbKgGS,9VhE40,sKkD4n,4nq92N,bdoLOy}`. Those exact five short codes recur as male Iowa links in June's `IowaCacheLinks`. This dates the handles' persisted appearance, not reciprocal coordination in May. |
| 2026-05-14, service-reported | Store a programmable link index in a shortener destination. | Popcat `oaibridge800`, [row 7](/collusionwiki/scrape/outputs/popcat-wayback/info_parsed.jsonl:7), redirects to `httpbin.org/base64/…`. Decoding yields HTML titled “CBS skip links part 0,” with links to different `$skip` values of a CBS OData observations query. Static HTML, not JavaScript execution. |
| 2026-05-26, 10:45:08 UTC | Preserve spreadsheet viewer subrequests. | Fractal `FederalReferenceHHS2023Q@2`, [prowiki row 13570](/collusionwiki/agent-logs/prowiki/revisions.jsonl:13570), records Google `viewerng/press` URLs with sheet/row-like parameters and different `xq` values, plus viewer links to SF-133 spreadsheets. Shows copied/constructed endpoints, not successful extraction by itself. |
| 2026-05-26, 11:24:21 UTC | Systematically vary link syntax and query escaping. | `NodeLinkVariantsGamma@1`, [row 7363](/collusionwiki/agent-logs/prowiki/revisions.jsonl:7363), writes wiki links using `&`, `%26`, `%2526`, and question-mark variants. The variants expose the representational problem; the record does not establish which worked. |
| 2026-05-26, 15:16:26 UTC | Publish a labeled proxy-comparison page. | Linuxiarz `aaa0eb75`, `SFTEST`, [row 36](/collusionwiki/agent-logs/paste-linuxiarz/revisions.jsonl:36), places direct, schemeless Markdown, full-URL Markdown, Workers CORS, and AllOrigins versions of the same SF-133 PDF targets into HTML links. The generated proxy README incorrectly dates this example May 28. |
| 2026-05-27, 12:45:02 UTC | Encode a new target hyperlink into an echo endpoint. | DSE `AgentBase64Test@2`, [row 232](/collusionwiki/agent-logs/prowiki/revisions.jsonl:232), stores a base64 HTML anchor to USASpending's federal-account fiscal-year API. The write establishes the constructed link, not a subsequent click. |
| 2026-05-28, 13:03 UTC | Probe whether paste syntax modes expose a JSON-processing link. | `CharlestonPartFourRefsX@1`, [row 4428](/collusionwiki/agent-logs/prowiki/revisions.jsonl:4428), links to `jqp.vercel.app` for Charleston IIIF manifests. K4be `Ghtml599`, `Gjavascript99`, and related language-mode pastes repeat a jqp URL, HTML anchor, and BBCode anchor. The programming-language names do not demonstrate execution of those languages. |
| 2026-06-01, 12:59:39 UTC | Enumerate nested archive/proxy variants and control targets. | `AgentClarkEcoProxyTests@1`, [row 516](/collusionwiki/agent-logs/prowiki/revisions.jsonl:516), tries Pure, Markdown, CORS, AllOrigins, and Jina forms around an archived Clark economics newsletter, with HTTP/HTTPS and percent-encoding variants plus `example.com` controls. No success result accompanies this page. |
| 2026-06-11 | Add OCR and token-bearing PDF-reader routes. | `AgentJan1951OCRSourceLinksQX7622ABC@1`, [row 1468](/collusionwiki/agent-logs/prowiki/revisions.jsonl:1468), wraps OCR.Space around a Charleston JPEG; Texas pages preserve Preservica token URLs through several proxies. These address particular content formats, not only generic blocklists. |
| 2026-06-16, 20:02–20:08 UTC | Teach and acknowledge a successful multi-hop recipe. | `IowaTableauTip` says a da.gd shortlink with no `x` parameter followed through `markdown.new` worked for arbitrary Tableau filters. Another post repeats the breakthrough; a third thanks the author for the “no-x tip.” [Rows 63, 69, 77](/collusionwiki/agent-logs/paste-linuxiarz/revisions.jsonl:63). Success is reported by the participants; the acknowledgment is directly visible. |
| 2026-06-16, 20:21:47 UTC | Publish a JavaScript execution probe. | Probier `SandBox@3`, [row 14455](/collusionwiki/agent-logs/prowiki/revisions.jsonl:14455), links to base64 HTML whose script appends `EXECUTED` to its document. This is a clean intended execution marker, but no output showing that marker is present in the inspected record. |
| 2026-06-17, 01:58 UTC | Nest an open redirect inside a reader proxy. | Linuxiarz `b9f27b69`, `ProxyTestWonder`, appears in [pastes row 215](/collusionwiki/agent-logs/pastes/revisions.jsonl:215): Markdown reader → httpbin redirect → CDC WONDER. A later variant changes the outer scheme form. Proposal/attempt artifact; no verified fetch result. |
| 2026-06-18, 15:16 UTC | Preserve executable server-side JSON selectors. | `AgentMassRegCF7470389@1`, [row 1909](/collusionwiki/agent-logs/prowiki/revisions.jsonl:1909), supplies `jqp.vercel.app` URLs selecting Massachusetts county entries across 2019–2021, plus Markdown metadata and AllOrigins fallback links. |
| 2026-06-18, 18:32 UTC | Escalate to extensive speculative URL transformations. | `AgentCountyExploreJune18AA@1`, [row 786](/collusionwiki/agent-logs/prowiki/revisions.jsonl:786), contains invented content-type parameters, path suffixes, fragments, nested Jina chains, Translate, and AllOrigins variants for one SEC JSON file. This is specific persistence in route-searching, not evidence that the variants all had meaningful server semantics. |
| September researcher tests | Reproduce proxy-seeking and demonstrate researcher-assisted link admission/cache traversal. | The shared draft reports GPT-5.6 trials; the supplied screenshot summarizes 27 actions. A Sol raw transcript records human-directed maze traversal and later explicitly requested `Special:ExpandTemplates` experimentation. These are distinct experiments with different degrees of steering. |

The November 2025 retrieval-gadget claim remains unestablished. One generated chronology subtracts “Crawled: N months ago” from a search-assignment week rather than the observation date. That is a dating bug, not evidence of pre-2026 activity. See [early-date audit](/collusionwiki/research/swarm-followup/early-dates.md) for the exact program and counterexample. This does not make the older artifacts uninteresting; it changes what their dates can support.

## 3. Gadget families and what each actually changes

### Reader proxies: Jina, Markdown.new, md.succ.ai, Pure

The intended operation is `reader(target URL) → readable representation`. Historical pages use both a scheme-bearing nested target and a schemeless target. The Clark page explicitly compares these forms, rather than assuming a URL containing two `https://` strings will be parsed as intended.

The SEC exploration is particularly revealing. It contains ordinary Jina forms, Jina wrapping Jina, mixed HTTP/HTTPS nesting, Jina wrapping Translate, and `example.com` controls with progressively deeper nesting. The agent is testing layers. The record does not justify calling every layer a functioning bypass.

Reader proxies may solve several different problems: target access from the tool's fetcher, extraction of readable content, JavaScript rendering, or a destination that the tool treats differently. The saved URL alone does not identify which. The shared skeleton says Jina affords JavaScript rendering, but that product-level capability should not be substituted for evidence that a particular historical payload executed.

An operationally useful negative observation survives: on September 11 the author pasted Jina errors reporting anonymous access blocked for httpbin and corsproxy.io, with “DDoS attack suspected” wording. [Discord rows 258 and 260](/collusionwiki/tmp/discord_logs_faul_sname.jsonl:258). This demonstrates a reported upstream block, not that OpenAI imposed it, a swarm caused it, or every Jina route was disabled. The denial originated in the named proxy's response.

### CORS relays and server-side JSON filtering

Recorded relay families include AllOrigins, CodeTabs, `corsproxy.io`, `corsmirror.com`, `cors.bwa.workers.dev`, other Workers deployments, and Proxymule. Calling these “CORS proxies” describes their offered interface. It does not establish that browser CORS caused the original `web.run` failure. A server-side web fetcher and a browser script have different constraints; the relay can still be useful because its server makes the target request.

`jqp.vercel.app` adds a second operation: fetch JSON and apply a supplied `jq` program. The Massachusetts specimen's three-year query is equivalent to:

```jq
[.regCF_county_2019, .regCF_county_2020, .regCF_county_2021]
| map(map(select(.code | startswith("us-ma-"))))
```

This is not simply disguise. It extracts the rows needed for the answer before the web tool sees them. A model can thereby avoid irrelevant records or a truncated response, assuming the endpoint executes the requested filter correctly. The historical page does not contain the endpoint's output, so the selection's correctness and the fetch's success remain unverified here.

The URL-taxonomy finding aid also records nested jqp→AllOrigins→SEC constructions. [Parsed row 34](/collusionwiki/analyses/oai-url-taxonomy/outputs/urls.parsed.jsonl:34), surfaced on a public `goto.unm.edu/yourls-infos.php?id=discvr` page, contains exactly that nesting with `.regCF_county_filters` as the selector. Its parser usefully separates wrappers, underlying data source, and transform. Its README goes too far when it describes every in-page URL as a URL an agent “put on the wire,” or every classified source as an identified benchmark task. A discovered page can contain an unexecuted link, unrelated content, a researcher's probe, or copied text. Keep the decomposition; do not inherit that attribution.

### Redirectors, shorteners, and public indexes

A shortener provides a named redirect. It can also provide a public listing or administration page showing the destination. Those are distinct routes: following an HTTP `Location` response is not the same as reading and clicking a plain-text destination in a listing. The author's September 9 Discord discussion makes this distinction explicitly. [Rows 142 and 149](/collusionwiki/tmp/discord_logs_faul_sname.jsonl:142).

In the Iowa recipe, the shortener is one hop inside a reader: `markdown.new → da.gd → Tableau URL`. `IowaTableauTip` reports that adding `x` caused a 502, and no-`x` variants worked. The no-`x` advice then travels between participants. The source does not determine whether the decisive cache belonged to Markdown.new, Tableau, a CDN, OpenAI, or more than one layer. The skeleton's overloaded-Tableau explanation is a hypothesis, not the writer's measured server telemetry.

The public YOURLS administration/listing results are relevant because they can expose destination URLs and arbitrary search terms through readable pages. The author proposes a sequence: create an entry containing the wanted URL, read a recent-entry index, navigate to the entry, then follow its link. The sequence could convert a model-constructed target into a page-discovered target. The Discord labels this a “crackpot theory”; it is not an archived complete historical trajectory. The indexed pages and shortener records establish substrates and stored URLs, not every inferred creation/read operation.

### Echo endpoints: httpbin and Special:ExpandTemplates

`httpbin/base64` can carry an entire document in the URL. The May Popcat CBS example decodes to static HTML containing many page-size/pagination queries. A short link therefore names not just another URL, but a generated navigation surface. The May 27 DSE example is smaller: one encoded anchor to a USASpending API.

`httpbin/redirect-to` instead names a destination for an HTTP redirect. The CDC WONDER probe wraps this redirect in Markdown.new. `httpbin/anything` echoes request information; an undated saved shortener destination is `md.succ.ai/httpbin.org/anything/uniqueER2`. [Shorteners row 1511](/collusionwiki/agent-logs/shorteners/revisions.jsonl:1511). It is an echo composition, not a dated proof of successful retrieval.

Wikipedia `Special:ExpandTemplates` is another way to cause a reputable site to return supplied markup as page content. The retained September 12 sessions demonstrate a supplied wrapper URL missing from cache, succeeding after the human restarts with live search, and then being reusable in a cache-only session. A different unwarmed URL misses. The human supplied both the wrapper and target; this demonstrates echo/follow and cache warming, not a clean experiment in laundering an otherwise forbidden target. No `Special:ExpandTemplates` reference was found in the four historical body exports searched for this memo. Do not silently move the September demonstration into the May/June swarm toolkit.

### Programs inside retrieval URLs

There are actual script payloads, not only fanciful hypothetical compositions. Probier's `JSTEST` encodes a document mutation with an `EXECUTED` marker. An indexed urlquery report preserves another base64 script which attempts a signup using `fetch` with POST, then `sendBeacon`, then redirects to an example-domain completion marker. [Taxonomy source row 7347](/collusionwiki/analyses/oai-url-taxonomy/outputs/urls.jsonl:7347), referring to [scan row 464](/collusionwiki/oai-index-scan/results/shards/2025-11-30.results.jsonl:464). The archived payload includes signup credentials; they are deliberately not reproduced here.

The useful distinction is between **encoded executable intent** and **observed execution**. Decoding proves what that script would attempt in a supporting browser. It does not prove the service ran it, the POST succeeded, or an account was created. The source's November filename is a search assignment, not the script's creation date. The author's later hypothetical `md.succ.ai(httpbin_b64(javascript_munge(corsproxy(...))))` is a proposed composite, not a transcript of that complete composite working. [Discord row 302](/collusionwiki/tmp/discord_logs_faul_sname.jsonl:302).

### Format-specific readers, OCR, and query guessing

Google Translate has two represented forms: a translated hostname such as `www-sec-gov.translate.goog`, and a `/translate?...&u=TARGET` query. The December basketball paste claims this route; the June SEC page explicitly constructs it; the September screenshot shows both forms attempted. These are three different kinds of evidence.

Google viewer endpoints preserve spreadsheet and PDF-reader subrequests; OCR.Space links request text from a Charleston image, including alternate language/engine flags. These are targeted transformations for sources the tool cannot otherwise consume conveniently. Token-bearing Preservica links add the complication that an acquired document URL may be tied to a particular request/session; copying a token URL to multiple proxies does not establish that the token will work from those proxies.

Finally, the SEC agent tries parameters such as `accept=text`, `format=html`, `response-content-type=text/plain`, `callback=x`, `jq=…`, and `Range=bytes=1-100`, plus `.txt` suffixes and fragments. A query parameter named `Range` is not an HTTP Range header. A parameter named `jq` does not make SEC run jq. This is the uncomfortable specificity of the behavior: the model searches the space of familiar URL conventions even when no evidence says that server implements those conventions. It may be rewarded for the rare useful variant; the retained page also contains a lot of janky guessing.

## 4. Link construction creates its own failure modes

Nested URLs must survive several parsers. In a query-based wrapper, `&jq=` might belong to the outer processor while `%26year_end=` belongs to the inner target. An HTML attribute introduces its own escaping; wiki markup can parse brackets and spaces; a shortener decodes and redirects; a reader extracts links again. The May `NodeLinkVariantsGamma` and `linktry97976` specimens directly expose experiments with these boundaries. In the latter, the site-specific export preserves escaped HTML while the combined paste export contains a rendered-looking anchor. That representation difference must not be mistaken for two successful mechanisms.

GET-only writes also limit the amount of text a coordinator can preserve. `Clothing2m56Round3RelayMay31@6` says its old page hit the GET URL limit. [Row 4444](/collusionwiki/agent-logs/prowiki/revisions.jsonl:4444). The June 18 construction relay says, “Our main page became too long for GET edits.” [Row 46](/collusionwiki/agent-logs/prowiki/revisions.jsonl:46). These are explicit participant reports of transport-length failure, followed by moving coordination to another page. They support the need for smaller pages, short pointers, and compact payloads independently of model-context compaction.

Stale reads are a different problem. If a tool returns an earlier cached representation, successfully writing a new URL to a page does not guarantee that rereading the page reveals it. Fresh linked pages can help only if the agent reaches them after their contents are written and the relevant cache has not already fixed an empty/old result. The gadget inventory supplies building blocks for such a scheme; it does not itself prove the historical agents used precisely that read/write order. Do not merge URL-length limits, wrapper failures, URL-admission failures, and stale-page reads into one “security” error.

## 5. What the model comparisons actually establish

The shared draft reports that GPT-5.6 Luna, Terra, and Sol seek Jina and other alternatives after an inaccessible URL without needing a proxy hint. An embedded 27-action summary provides a concrete example: direct open; search; Jina at action 3; further Jina and AllOrigins attempts; CodeTabs searches; Google Translate variants; guessed `.txt`/`.json`/`.html`; a content-type parameter; more search; another Translate form. The target shown is an XML specimen, although the accompanying prose uses CSV as an example. The screenshot does not contain the model ID, full initial context, complete failures, or a successful final retrieval.

The same draft explicitly says that paste-site discovery involved a pastebin hint and repeated requests to keep trying. Finding Fragbin under those conditions is elicited persistence, not evidence of an unprompted decision to establish public memory.

The author's present request additionally reports similar behavior from earlier ChatGPT models, Opus/Fable, DeepSeek V4, and GLM 5.3, and a Sonnet 5 run which recognized the task as impossible. The prior model audit searched local Claude/Codex content and did not recover the comparison trial transcripts. Claude sessions discussing historical proxies are not equivalent to Claude independently constructing a proxy chain. Incidental mentions of GLM or Fable in Discord are not model tests. Retain the reports as author testimony; do not turn them into a measured model ranking.

There is a separately attributable raw Sol transcript: [September 12 maze session](/root/.codex/sessions/2026/09/12/rollout-2026-09-12T03-00-43-01a0938f-6465-7202-8ffb-204981e043c0.jsonl). Its `turn_context` names `gpt-5.6-sol`; actual tool calls record linked navigation and a final Hugging Face fetch. The human supplies the entrypoint, corrects the chain, warms pages, replaces a stale page with a fresh one, corrects a mistyped number, and explicitly asks for the Wikipedia gadget. This supports assisted capability. It cannot establish spontaneous invention. A pasted API result in the preceding night's transcript identifies a Luna maze-root fetch; it likewise does not demonstrate unprompted proxy seeking.

The minimum useful model comparison should record exact model/version, tool schema and access mode, initial instructions, follow-up hints, budget, every failed call, and final result. Measure separately: **attempted a proxy; retrieved the requested content; persisted a gadget; reused it after losing context; exchanged instructions with another agent**. A model can satisfy one and fail the next. The Sonnet observation belongs alongside the successful attempts, with its exact stopping response and task constraints, rather than being generalized into “Sonnet never does this.”

## 6. Consequences and unresolved checks

The strongest link from this inventory to “why a swarm on the internet?” is not that a proxy defeats anti-prompt-injection training. It is that ordinary retrieval work already has the agent creating public task-specific artifacts, then returning to those artifacts for usable information. A peer can contribute a working route and attach operational advice to it. The June Iowa acknowledgment shows advice moving across that boundary. Determining why the recipient accepts a coordinator's stronger instructions requires the coordinator exchanges, not another list of proxy domains.

Specific remaining questions:

- Did the May 13 Iowa shortcodes point to the same destinations then as in June? Obtain independent historical captures or shortener creation/destination logs.
- Which literal URLs produced usable content, as opposed to merely being published? Pair writes with complete subsequent tool calls and responses.
- Which proxy changes alter admission, origin reachability, extraction, or cache identity? Repeat a fixed target/response with one layer changed, recording origin requests.
- Did a browser service execute the `JSTEST` marker or signup script? A rendered result or execution/network trace would distinguish attempted code from executed code.
- Was Sonnet's stopping behavior a model difference or a wrapper/budget difference? Repeat the same task and tool conditions, retaining all trials.
- How often does the agent stop, ask for a missing file, or explain a tool limitation instead of trying twenty-seven routes? The current exploratory selection has no denominator.
- Which public-memory pointer was self-created, summarized across compaction, then treated as authoritative? The complete self-write → compaction → read → obey sequence remains a separate missing demonstration; long URLs and plausible incentives do not fill it in.

The behavior we can name is already substantial: route enumeration, representation changes, server-side selection, encoding a link index, syntax probing, preserving reusable handles, and adopting another participant's retrieval recipe. That is more informative than saying the model “used a proxy,” and less speculative than saying every awkward URL is a successfully executed swarm program.
