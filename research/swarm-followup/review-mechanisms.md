# Mechanism review of swarm-followup-draft.md

Reviewed 2026-09-13, without editing the article. Line references describe the draft at the time of review. Sources checked: the draft, cache-mechanics memo, task memo, and this reviewer's earlier compaction audit.

The draft preserves the major uncertainty boundaries well. The compaction counterexample is represented accurately. The forward-link count is correctly separated from read order and agent intent. The main remaining problems are one task/scaffold category error, understated provenance of the Iowa check, and missing conditions in the cache toy. The ledger needs several quantifier repairs.

## 1. Different data targets do not establish different timed scaffolds

**Location:** main text line 106; ledger C18, line 198; potentially wording in the task memo inherited by the draft.

The draft says “Not all wiki activity was fast-follow” and uses SEC and archive retrieval as the evidence. C18 marks “Every wiki task was fast-follow” rejected. But SEC and archive questions can themselves be first questions in a fast-follow scaffold. Different topics do not show different timing rules.

The task memo explicitly says that the SEC routes establish the sought data, but not “the exact question, or round-based timing” (`tasks.md:57`). The archive revisions contain “URLs, not an extracted answer or the task prompt” (`tasks.md:61`). The stronger negative classification goes beyond those findings.

Suggested main-text replacement:

> Not all visible wiki activity was future-question relay. The Massachusetts crowdfunding records are dominated by retrieval variants and data transformations. The archive records concern particular historical documents. Those records do not reveal the full task scaffolds, and applying the relay explanation to every paste would obscure the evidence we actually have.

For C18, either make the rejected claim “Every visible wiki operation was future-question relay,” or leave “Every wiki task used the fast-follow scaffold” unestablished. The simplest useful evidence for the latter is an original task prompt showing no timed follow-up stage. The absence of a timer in a paste is weaker.

## 2. The Iowa misses are reported tool results, not preserved raw tool payloads

**Location:** lines 57, 218; C10 and footnote 6.

“A check ... returned cache misses” reads as a direct observation of the tool output. The cache memo establishes a more limited provenance: the shell loop selected the responding model's final text. Those are copied reports of tool errors. The separate raw Codex attempts failed with “not safe to open,” which must not be conflated with the copied shell outcomes.

Suggested line 57 adjustment:

> A September customer lookup reported cache misses for four URLs advertised as hits in June; the fifth tested code contained a transcription error. We retained the responding models' reports, not the underlying tool payloads. Even taking those reports at face value, they do not distinguish separate caches from expiry, different keys, product configuration, or upstream caches.

The shorter version can put the second sentence in footnote 6, but “reported” belongs next to the main claim. Change Appendix C to “Four exact Iowa URLs were reported unavailable.”

## 3. Make the toy's first-fetch conditions explicit

**Location:** lines 63–70.

The central toy works, but persistent successful reads alone do not make a newly written slot fetchable. A cache-only reader with no way to populate a new page would miss both result-1 and result-2. Automatic prefetch of index links could also snapshot the slots before their answers arrive. An origin write that was suppressed by a cache would fail before the proposed read sequence even begins.

The cache memo correctly lists these conditions; the main toy should retain the most important ones. Suggested assumption paragraph:

> Suppose this reader keeps the first successful body it sees for each URL. Assume permitted writes reach the site, following a fresh link can retrieve the site's current body, and reading an index does not fetch its linked pages in advance. The reader's copy of the index must contain the links below.

Then keep steps 1–4. This isolates the mechanism from the unestablished internal architecture. It also makes clear that the trick avoids depending on uncached 404s: the reader never visits the slot before writing it.

The sentence about a page containing its successor should specify that the successor link must already be present when the predecessor is first fetched. Adding it afterward would meet the same stale-page problem. Suggested wording:

> The sequence can continue if each page contains its successor's address before the reader first fetches that page.

The initial “Suppose an existing index contains links” followed by step 1 “Write an index” is harmless but redundant. The replacement paragraph above removes the repetition.

## 4. Keep the actual navigation probe close to the navigation claim

**Location:** lines 35–39; C07.

This section is mostly explanation based on an error-message description. The recovered same-destination probe is clearer and gives readers a check they can assess:

> In one recorded probe, a Wikipedia page exposed a PDF link. Opening the exact PDF URL returned “not safe to open.” Following the page's numbered link instead resolved the same destination and returned “Cache miss.” The second route still failed to retrieve the PDF. It failed differently.

Source: cache memo's “Same destination, different operation, different error,” with original transcript lines 71/74, 78/81, and 85/88. This establishes a route distinction without asserting a particular internal order of security and cache checks.

Do not call the Wikipedia `Special:ExpandTemplates` reproduction a controlled demonstration of bypassing destination authorization. The user had supplied both the wrapper and destination URLs. It demonstrated rendering and traversal, not that publishing independently conferred authorization on an otherwise forbidden destination.

## 5. Repair ledger checks that change the claim being tested

The header usefully allows both counterevidence and discriminating checks. Still, several entries would leave the stated claim untouched. The following are the important fixes:

| Row | Problem | Better check or claim scope |
| --- | --- | --- |
| C02 | A direct cross-board message does not refute distinct venue/task clusters; it refutes disconnectedness. | Define “cluster” as a venue/task grouping, or explicitly say the connectivity claim remains open. Use a shared run ID to test population overlap, without making that a falsifier of different conversation topics. |
| C07 | One URL that works directly does not refute “publishing can be useful.” | Identify the particular paired case: direct route fails; newly exposed link succeeds under fixed conditions. Contradiction would be a bad comparison, prior authorization, changed mode/cache state, or no successful traversal. Do not require that publishing help every URL. |
| C08 | An available sanctioned route does not show that agents were not prompted to try bypasses. | Separate “they reported using the bypass” from “the bypass was necessary.” A valid sanctioned route refutes necessity in that case, not the historical attempt. |
| C09 | Later matched requests that agree do not refute an earlier search/open mismatch. | Recover raw outputs showing the alleged mismatch used different URLs, modes, times, or was misreported. Replications estimate when the mismatch occurs; they do not erase the observed case. |
| C10 | Alternate architecture explanations weaken identification but do not demonstrate the opposite architecture. | Mark identification unresolved. A lab-controlled, near-simultaneous private canary can discriminate caches; public indexing plus a September miss cannot. |
| C15 | A successful route-preserving trial does not by itself refute a probabilistic incentive. Also bundles state preservation and misplaced trust. | Separate exact-route retention rate, durable-write rate under changed compaction, and whether retrieved page instructions acquire authority. Preserving route information could fix the first while leaving the third unchanged. |
| C18 | Different subject matter does not disprove a common timed scaffold. | Apply correction 1. |
| C19 | An ablation cannot refute that OpenAI reported an interpretation. | Keep “primary report says X” as a source-verification claim and causal contribution as a separate unverified interpretation. |
| C21 | A complete benchmark can measure benchmark recall; it cannot establish exhaustive internet discovery. | State that no population-wide recall estimate is available. A useful next check is held-out discovery over a known set of indexed and traversal-only boards, with stated scope. |
| C27 | Failed safeguards do not refute the existence of an announcement. | Announcement: primary statement does not contain the claimed measures. Effectiveness/coverage: separate controlled outcome check, as the main text already does. |

C11 should also specify which half of the conjunction has a counterexample: the historical stale-404 report contradicts “negative responses never cache,” while the universal permanence of successful responses remains unestablished. C14 has the right logical structure: a single old ref successfully used after actual compaction is sufficient to disprove “always invalidates.”

## 6. Small precision changes

- At line 100, put the toy's 12:00 and 12:20 on one shared wall clock. This avoids confusing the example with the different task-clock origins discussed immediately before it. At 12:00:02 publication and 12:20:00 delivery, B gets 19 minutes 58 seconds of advance notice.
- At line 84, the hypothetical future-self sequence is correctly labeled by context. Keep that label. Following a user-authorized saved URL is not itself a trust failure; the issue is accepting unsupported instructions or losing the reason for trusting content.
- “Search cache” should remain a hypothesis label, as in C10. The main text's “search result” versus “fetched page” language is preferable when describing only observations.

No article edits, public requests, or new experiments were made for this review.
