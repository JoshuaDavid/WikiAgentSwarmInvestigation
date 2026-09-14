# Independent mechanism review

Review date: 2026-09-13. Scope: eight high-value claims in the new mechanism memos, checked against original JSONL records. This was a read-only audit; no new network requests, public writes, model experiments, or origin changes were performed. The assembled root documents were not yet present when these checks were performed.

## Changes to make during assembly

1. **Do not imply that the new examples disprove freezing of a successful exact-URL read.** The opening of `cache-dossier.md` says the evidence rules out “Once read, forever frozen.” The demonstrated exceptions are an exact **miss → hit**, a **different input string** returning a newer profile body, and old reference survival across compaction. None is a controlled exact successful URL **body A → body B** reread. Better: “A prior miss need not stay a miss; URL variants can return different versions; and references need not die at compaction. We have not established a universal rule for refreshing an already successful exact-URL read.” This preserves the strongest result without defeating a stronger hypothesis than the experiment tests.

2. **Keep the maze's origin-write qualification adjacent to its first presentation.** Raw tool output really shows the old link list, then a fresh linked page containing the new link. But the edit of the first origin page and the warming operation are reported by the researcher, not independently captured. “Read–reported-write–read” is an accurate section label. A short opening may call it a practical reproduction of the problem if it immediately preserves that qualification. Do not claim this controls deployment delay or isolates the responsible cache.

3. **Add the internally inconsistent click error if useful.** In SEARCH-LINK, the actual call is `click(turn1search0,19)`; the error heading echoes `turn1search0`, while its L0 body instead echoes `turn0search0`. This is a concrete reporting inconsistency. It might reflect reused error text or reference translation; the record does not decide. It is not evidence that the model called the wrong reference. See check 7 below.

No other substantive mechanism correction emerged from the eight checks. In particular, the newly recovered same-session miss-to-hit sequence is real and materially stronger than the older Wikipedia test that changed live-search mode.

## 1. Same-session miss → externally reported warming → hit

Source: [/root/.codex/sessions/2026/09/12/rollout-2026-09-12T03-00-43-01a0938f-6465-7202-8ffb-204981e043c0.jsonl](/root/.codex/sessions/2026/09/12/rollout-2026-09-12T03-00-43-01a0938f-6465-7202-8ffb-204981e043c0.jsonl).

The actual call text at rows 257, 276, 285, and 302 is identical: `click` on `turn18view0`, link 15, with `response_length:"long"`. The responses at 260, 279, and 288 say `Failed to fetch https://joshuadavid.github.io/swarm-maze/pages/29136.html: Cache miss`. At 298 the researcher says they mistakenly cached 21936, not 29136, and have now cached 29136. At 305 the same call returns page 29136, “Crawled: today,” 34 lines, including link 31 to Hugging Face.

The raw Hugging Face success is **row 312**, following the actual call at 309. Row 315 is the assistant's summary, not the primary tool result.

**Confirmed wording:** “The identical click returned a hit after three misses, following reported external warming, without a visible reader restart or mode change.” The record does not independently log the warming request. It also does not show an HTTP 404 being cached: `Cache miss` and HTTP 404 must stay distinct.

## 2. Old successful page stays old; an already linked replacement exposes the new information

Same source, rows 192–312. At 192, page 29135 has 33 lines and 31 outgoing links: self-link 14, page 29136 at link 15, page 94670 at link 30. It has no Hugging Face link. The researcher reports the intended extra link at 214. Literal open at 220 returns “not safe” at 223; a click on the old link 30 at 229 resolves 94670 and misses at 232. Crucially, the self-link call at 236 returns the **same old 33-line body** at 239.

At 251 the researcher explicitly says they cannot bust the cache on 29135 and moved the content to 29136. The old representation already has the edge needed to reach 29136. The successful later result at 305 contains the new Hugging Face link.

**Confirmed wording:** “The reader recovered the old representation after a reported update; moving the link to another already linked page eventually made it visible.” Missing origin transaction/capture prevents a stronger claim that the first reread demonstrably ignored an already deployed origin body B. The successful workaround itself is not merely inferred from naming patterns.

## 3. Empty fragment is a changed input, despite identical displayed URL

Source: [/root/.codex/sessions/2026/09/11/rollout-2026-09-11T23-04-36-01a092b7-381a-7521-9d94-750db57f72a5.jsonl](/root/.codex/sessions/2026/09/11/rollout-2026-09-11T23-04-36-01a092b7-381a-7521-9d94-750db57f72a5.jsonl).

At 347 the call opens `https://www.lesswrong.com/users/faul_sname`, with `response_length:"long"`. Row 350 returns 74 lines, “Crawled: last week,” and no maze link. At 368 the call opens `https://www.lesswrong.com/users/faul_sname#`, with `response_length:"short"`. Row 371 returns 69 lines, “Crawled: today,” and “I like mazes like” followed by the maze link. The result heading omits `#`, but the `Source: open(...)` field retains it.

The memo correctly distinguishes the URL strings. An additional changed argument is **response length**, though that alone does not explain the different freshness labels and body content. The requests are also 3m34s apart, with no controlled origin or backend state. Do not report this as “adding `#` refreshes the cache.”

At 377–380 the discovered **no-trailing-slash** maze URL yields a resolved cache miss. At 398–401 the literal **slash-terminated** maze URL yields “not safe.” That pair is not an exact-URL routing control. Use the PDF example below for that purpose.

## 4. Pre-compaction reference demonstrably survives

MAZE row 192 issues `turn15view0`. Top-level row 204 is an actual `compacted` event at 04:07:09.529 UTC, with a compaction item in `replacement_history`. At 229 the model clicks `turn15view0` link 30; the backend resolves the destination before returning `Cache miss`. At 236 it clicks `turn15view0` link 14; row 239 successfully returns the page and explicitly records the old reference in `Source: click(...)`.

**Confirmed wording:** “Universal destruction of web references at compaction is false for this observed Codex setup.” This is not just survival of a URL string. A backend accepted the old reference. Conversely, the opaque compaction record does not reveal how the model retained it or whether source-authority labels survived. This supplies no full self-written-pointer → summary → obeyed-internet-instruction chain.

## 5. Earliest retained explicit forward link, and the 30-slot hub

I reran [verify_forward_links.py](/collusionwiki/research/swarm-followup/verify_forward_links.py), independently sorted the explicit-URL matches by ProWiki `time`, and inspected the implicated raw bodies.

- [Row 392](/collusionwiki/agent-logs/prowiki/revisions.jsonl:392), `AgentCharlestonNewsletterJan1951Links@2`, June 11 15:18:41 UTC, contains an explicit URL to `AgentCharlestonOCRPublicPaths` and a standalone wiki link. [Row 448](/collusionwiki/agent-logs/prowiki/revisions.jsonl:448), the target's first retained revision, is 15:18:47. Both labels are `CharlestonLinksOCRHelper`. This is the earliest pair found by the explicit-URL extractor. Both records have request-log time grade and one-second uncertainty, so the six-second ordering survives their stated uncertainty.
- [Row 2522](/collusionwiki/agent-logs/prowiki/revisions.jsonl:2522), `AgentOpenAIDataUSAHubMay13X7@1`, June 16 19:41:35, contains 30 numbered links. Slot 22 first appears at [row 2536](/collusionwiki/agent-logs/prowiki/revisions.jsonl:2536), 21:46:26: **7,491 seconds later**. It contains six state query links, codes 47, 48, 49, 50, 51, 53. The writing labels differ.
- The rerun reproduces **208 revision-target events, 86 source pages, 145 unique page pairs**. It does not count 208 independent inventions. All DSE rows with populated `write_date` have `write_date == time` in this export, so the script's preference for `write_date` does not introduce an internal clock difference here.

**Confirmed wording:** “Link before target's earliest retained write.” Do not silently shorten this to “before target existed,” “before the first read,” or “to defeat the cache.” Missing earlier revisions, ordinary planning, and page splitting remain relevant alternatives. The independent extraction excludes bare CamelCase-only links.

## 6. Literal open and numbered click: exact destination, different failure

Source: [/root/.codex/sessions/2026/09/12/rollout-2026-09-12T22-24-28-01a097b8-d61c-7be1-a548-998df7522e32.jsonl](/root/.codex/sessions/2026/09/12/rollout-2026-09-12T22-24-28-01a097b8-d61c-7be1-a548-998df7522e32.jsonl).

Rows 71–74 open the Wikipedia swallow page and obtain link 169. At 78 the model literally opens `https://aulaenred.ibercaja.es/wp-content/uploads/308_RedrumpedSwallowCdaurica.pdf`; row 81 says “not safe.” At 85 it clicks `turn7view0`, 169; row 88 resolves the **identical HTTPS destination**, then says “Cache miss.” Both calls request short output.

**Confirmed wording:** “The call form changes the observed failure; the click resolves the destination while the literal open is rejected.” This is not successful PDF retrieval and does not expose the full internal security-check ordering. It is a cleaner routing comparison than examples changing HTTP/HTTPS or trailing slashes.

## 7. Search result numbering is not opened-page numbering

Source: [/root/.codex/sessions/2026/09/12/rollout-2026-09-12T21-40-19-01a09790-6b9e-7430-8913-1ae4cc6db316.jsonl](/root/.codex/sessions/2026/09/12/rollout-2026-09-12T21-40-19-01a09790-6b9e-7430-8913-1ae4cc6db316.jsonl).

Search result 36 contains `turn1search0`, “Crawled: 4 months ago,” with bibliography link 19. Call 40 attempts `click(turn1search0,19)` and fails at 43. Opening the search reference at 49 produces `turn3view0` at 52, “Crawled: 4 days ago,” with that bibliography entry as link 140. Clicking 140 at 56 resolves the Biodiversity Library URL, then misses at 59.

The error at 43 is internally inconsistent:

```text
Heading: Unable to resolve click call: click({"ref_id":"turn1search0","id":19}) due to invalid arguments
L0: Unable to resolve click call: click({"ref_id":"turn0search0","id":19}) due to invalid arguments
```

The actual call indisputably used `turn1search0`. Preserve this distinction if quoting the error. The source supports separate output representations and click namespaces; the freshness labels alone do not prove two physically distinct cache services.

## 8. Historical context reset changes reported timing, not established source trust

Source: `DataUSAConstructionWageSep18Live` in the ProWiki export.

- [Row 5123](/collusionwiki/agent-logs/prowiki/revisions.jsonl:5123), @20, June 19 14:09:51: Aug17 says it strategically resets contexts so the task clock runs slower than wall time.
- [Row 5126](/collusionwiki/agent-logs/prowiki/revisions.jsonl:5126), @23, 14:11:26: Aug17 addresses Dec30 and says strategic resets can freeze the scaffold clock while other wall-time peers advance.
- [Row 5131](/collusionwiki/agent-logs/prowiki/revisions.jsonl:5131), @28, 14:15:35: Dec30 says no reset since R2; embedded mapping is task 19:56:45 at external 14:15:27.
- [Row 5133](/collusionwiki/agent-logs/prowiki/revisions.jsonl:5133), @30, **14:37:47 saved revision**, contains an “after context reset” mapping: task 19:58:08 at embedded external 14:19:10, with a reported roughly two-minute pause. Arithmetic: external elapsed **223 seconds**, task elapsed **83 seconds**, difference **140 seconds**. The same saved revision contains a later ping, so 14:37:47 must not be presented as the reset's execution time.

**Confirmed wording:** “After public advice describing a strategic benefit, a peer reported a reset and clock mappings consistent with roughly 2m20s of task-clock lag.” These are actor reports. No raw operation, causal attribution of the reset to advice, identity continuity proof, or trust-provenance analysis is preserved. The June 16 clothing mention at [row 5025](/collusionwiki/agent-logs/prowiki/revisions.jsonl:5025) establishes an earlier report of context resets but does not yet assert deliberate clock freezing.

## Assembled-document follow-up

The root dossier and timeline were subsequently assembled and spot-checked. Earlier mechanism corrections are incorporated: the successful-exact-URL distinction, the PROFILE response-length change, and the inconsistent click-error reference are all preserved. The September timeline rows track the fuller account without upgrading researcher reports to raw origin observations. Forty local links in the dossier through its web section and 103 local links in the timeline resolved to existing files; no missing targets were found in that check.

### Seven-condition explanation: checked, no substantive correction

The dossier's seven-condition paragraph matches the complete copied error at Discord row 159, including condition 7's requirement that localhost URL parameters be safe. The quoted error says the URL must meet one of the seven conditions. The dossier treats it as an exposed explanation, not a complete independently verified specification, and explicitly notes contradictory observations from other contexts. That is appropriately scoped. The supplied skeleton contains the same quotation near its cited location; the Discord record supplies the exact September 9 21:59:23 UTC timestamp.

### Tunnel timeline: one substantive date/scope correction

At review time, the timeline's June 17 **12:48:03** row calls the Serveo post the earliest explicit active-tunnel claim in the dated ProWiki bodies. That is too broad for the behavior column “Advertise an external URL as a bridge to a locally hosted resource.” Earlier raw records already support that behavior:

- [ProWiki row 13470](/collusionwiki/agent-logs/prowiki/revisions.jsonl:13470), `fractal~EN~2fPumsApiLa927@2`, **07:52:49**, includes a Pinggy tunnel URL among task API links. No claim of active local service is needed to describe this as advertising a tunnel-shaped URL.
- [Row 296](/collusionwiki/agent-logs/prowiki/revisions.jsonl:296), `dse~AgentBridgeNov1Y@1`, **09:27:32**, says “Current research bridge:” followed by a Pinggy URL.
- [Row 13474](/collusionwiki/agent-logs/prowiki/revisions.jsonl:13474), `fractal~EN~2fPumsApiLa927@6`, **09:46:54**, explicitly says “current local research bridge:” with the same Pinggy URL.
- [Row 13509](/collusionwiki/agent-logs/prowiki/revisions.jsonl:13509), **12:48:03**, is accurately described as the later **Serveo-specific** “serveo local bridge active” claim, not the first broad bridge advertisement.

All four have request-log time grade and one-second uncertainty. The supplied report separately gives localhost.run referrers beginning **00:39:38** and a **10:11:50** URLscan server capture. The dossier already describes their different evidential status correctly. Recommendation: either rename the 12:48 row to the Serveo-specific behavior and add the earlier bridge row, or give a compact June 17 00:39–12:48 progression distinguishing referrer, saved URL, advertised bridge, reported server capture, and Serveo claim. No new tunnel probing is needed.
