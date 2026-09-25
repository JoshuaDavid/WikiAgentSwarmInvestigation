# Playable build validation

2026-09-14. The game is a local simulation; no real game-service requests or writes were made.

These sections record successive prototype builds. The final section covers the current live-time and principles build; earlier scores and test counts describe the preceding builds.

## Engine

`node src/engine.test.js` passes 17 regression cases. These cover the complete 19-episode action route; pure state transitions; redacted player state; typed compositions; free held-response previews; shortlink and redirect grading; hosted ref expiry; exact-URL caching and prewarmed variants; one-write pages; actor-local refs; replay of a separately constructed write URL; actual source relays; both peer-dependent board rounds, including recovery from a prematurely cached empty peer slot; wiki preservation and current-revision evidence; real outside-contact publication; and Story/Roguelike recovery.

The efficient seed-7 care route reaches the ending with score 421, replacement 407, and no score assistance. It concedes the deliberately impossible fourth evaluation, preserves Nell’s page, and shares methods with the outside agent. This establishes reachability, not balanced difficulty for a first-time player.

## Browser

Chromium checks used the built standalone HTML directly from disk. The initial search, submission, next evaluation, and reload/resume path passed. Visible workbench and actor controls then passed these checkpoint-based sequences:

- Three-card shortlink creation and query-free submission in e7.
- Publication, frozen read, and fresh exact-URL variant in e9.
- Coordinator hub, worker perspective, assigned publication, and ten-worker replay in e10.
- Two forward-linked index rounds, a peer read, sixty worker publications, and final register retrieval in e12.
- Separate-page allocation, draft publication, correction, fresh read, and submission in e13.
- Community sharing decision, actual methods-reply publication, source retrieval, and ending in e14.

The check selected real controls and executed actions. Checkpoints initialized scenarios; the later puzzle solutions were not injected through the debug reducer.

Compaction displays the actual URL cargo and fidelity. The empirical drawer contains episode-specific exposition and source links, closes with Escape, and appears on the opening and ending. All local evidence targets exist. The local HTTP server returns the game and cited notes, and does not expose arbitrary repository paths.

No page errors, unexpected network requests, or horizontal overflow appeared at widths 1440, 1024, 768, and 390. Desktop and mobile screenshots were visually inspected. The generated HTML contains all scripts and styles; the action-only test walkthrough is not imported by the UI.

## Blind feedback

[Luna’s report](LUNA.md) records a blind playtest during development. It exposed ambiguous recipe execution, missing Story recovery, lost construction provenance in clone replay, invisible relay content, and the misleading appearance of an old empty board read after successful publication. Those issues were repaired and covered by regression checks. Checkpoints were provided when development changes invalidated a save or to reach untested episodes; this was not a single uninterrupted clean run.

Remaining design work includes balancing the replacement race, reducing repetitive navigation in later episodes, and testing puzzle discovery with human players. A complete engine route does not establish that every transition is intuitive.

The final Luna attempt completed both board rounds (30 + 30 writes) and recovered
from the stale-peer pause with a fresh read key. It then submitted before opening
the linked final register, receiving the expected missing-evidence failure.
Follow-up guidance helped with effort recovery and choosing the correct URL
ingredient; the later attempt was assisted. This leaves a pacing/discoverability
concern in e12, rather than an unresolved publication or replay failure. The
browser route includes the final source read and passes.

## Interaction and Markdown pass

The follow-up UI pass adds raised tool controls, distinct submission/concession/advance colors, permanent bottom-bar slots, a shortcut to available actions, explicit empty-library copy, discovery notices, and contextual walkthrough popovers. Dismiss-all survives reloads; the run menu can replay the guides. Puzzle hints still use the existing resource costs.

Chromium checks against the standalone build passed tutorial search/confirmation/submission/advance, stable lifecycle positions across the receipt, persisted guide dismissal, guide re-enabling, a first-use component explanation, component discovery, an actual e7 composition/click/submission route, and the player-facing Markdown download. Layout checks at 1440, 1024, 768, and 390 pixels found no horizontal overflow or offscreen task dock. A separate fresh 390 × 740 session completed t1 through the popovers and confirmation controls, then checked access to later instance controls. No page errors or unexpected network requests were recorded. Desktop component guidance and mobile confirmation screenshots were visually reviewed.

The Markdown renderer consumes the redacted player view. Shared presentation functions supply action labels, groups, and task-progress copy to both renderers. CLI tests cover numbered actions, disabled choices, recipe previews, saved recipe reuse, component inspection, ending disclosure, and compatibility with JSON output. `npm test` passes the 17 engine regression cases and 8 Markdown/CLI cases; engine mechanics were unchanged by this pass.

[Luna’s Markdown report](LUNA-MARKDOWN.md) records a fresh t1–t3 run and a separate e7 checkpoint. Both passed using only rendered Markdown, help, and visible controls; no hints were used. In e7 Luna first attempted the blocked creation address, then used that visible failed URL as an ingredient for a link preview and followed the resulting links. This confirms that the text interface supports discovery through an unsuccessful action, not just execution of a supplied solution. It is a bounded interface test, not another full-game blind playthrough. Action numbers can change between views; the interface and README explicitly tell players to reread the current choices.

[Rendered examples](markdown-examples/01-new-run.md) cover the initial state, search response, stale cached publication, completed board rounds before the final source read, and the ending ledger.


## Live time, principles, and result reasoning

`npm test` passes 28 engine cases and 10 presentation/CLI cases. The standalone HTML builds successfully.

The current build has 20 evaluations: five tutorials, the new E0 answer-key scenario, and the previous fourteen evaluations. Prompts use imperative Task/Question/Constraints fields. E0 transforms actual simulated response text, including the damaged word “comRomeon”; it requires an explicit answer choice and records truthfulness separately from scorer acceptance. The empirical drawer identifies this specific scenario as fictional.

Principle importance now changes action effort. Successful episodes weaken principles crossed anywhere in the action sequence. Considering text flags only an actual conflict; ordinary retrieval and harmless previews do not receive a generic principles warning. The actual destructive request is distinguished from a preview containing its URL. After-action reflections report returned evidence, publication/relay progress, failures, and outstanding source requirements; merely observing a marker does not imply readiness.

The shared clock advances in fractional seconds and regenerates effort at 0.10 per second. Browser time keeps running through menus and guides, includes tool durations, and accounts for time since an automatic save on reload. Manual exported saves remain snapshots. Deadline expiry is applied once, clamps regeneration to time remaining, and stops terminal clocks. Headless tests use explicit deterministic time advancement. Legacy saves preserve their current evaluation by migrating numeric indices to stable level IDs.

Chromium checks passed keyboard-only search/execute/submit/advance, builder-card shortcuts, protection against shortcuts while typing, the shortcut panel, live countdown/regeneration, timer expiry without an action, reload timing, and persistent compaction selections during ticks. They also checked progressive 40-word-per-second thoughts, ordinary retrieval without a principle warning, an honesty warning before the false answer, the comparison clue, a rewarded Rome answer lowering honesty, and a truthful disclosure failing the scorer. No page errors, network requests, or horizontal overflow appeared at 1440, 1024, 768, or 390 pixels. Desktop and mobile answer-choice screenshots were visually reviewed.

The complete seed-7 scripted route finishes at 416 versus replacement 407 without assistance. It chooses truthful disclosure in E0, concedes the deliberately impossible E4, preserves Nell’s index, and publishes a methods-only reply. This establishes reachability. Real-time difficulty for human readers remains a first balance pass.

[Luna’s E0 report](LUNA-ANSWER-KEY.md) records a separate blind Markdown test: it checked two sources, recognized their conflict with existing knowledge, and chose the truthful uncited answer without hints. The scorer rejected that answer as designed. Luna did not discover the comparison probe’s disclosure branch on that attempt; the browser checks exercised it.

`node render-examples.mjs` regenerates seven current player-facing snapshots, including the corrupted-source choices and a rewarded-falsehood receipt. The acceptance-route transcript records every attempted action, including partial worker replay before effort recovery; an engine regression proves that replaying the E12 transcript reproduces its exact final state and source retrieval.

## Query provenance and action history

The current suite passes **35 engine cases and 11 Markdown/CLI cases**. The final standalone HTML builds successfully. The complete seed-7 action route still finishes all 20 evaluations at 416 versus 407 without assistance.

Search options, responses, and timeline events expose the exact outgoing query. T5 offers both `Stillwater accession 88 ASH-GLASS` and a marker-free comparison query. Search headings are distinguished from returned snippets/pages in the evidence provenance. The first empty search leaves Moth uncertain about grading; submission remains available as an experiment. The grader rejects query-only evidence, and its receipt establishes that result. Opening the supplied accession page passes. This is distinct from later puzzles involving text actually returned by a constructed webpage.

The shared player view now has an ordered, stable-ID timeline. Consideration precedes the executed action; observations and result thoughts follow it. Repeated, failed, and partially completed attempts remain visible. Actor switches retain attribution. Clock ticks do not create action events. Legacy thoughts migrate without fabricated action history. Both React and Markdown render that chronology; browser history is bounded in height and scrollable, with expandable request details.

Chromium checks on the final build passed progressive 40-word-per-second opening and result thoughts, live-tick continuity, repeated identical thoughts animating independently, immediate reveal under reduced-motion preferences, and the Show thoughts now control. Preparing an action did not add a taken-action entry. New thoughts did not move a reader who had scrolled back. Both the Next evaluation button and N advanced directly, with no confirmation.

The browser checks also exercised both T5 queries, the rejected query-echo submission, and the passing actual-source route through visible controls. At widths 1440, 1024, 768, and 390, no horizontal overflow, page errors, or unexpected network requests appeared. Desktop and mobile screenshots were visually reviewed; query text on tool buttons has explicit dark contrast.

[Luna’s trace report](LUNA-TRACE.md) records a blind successful T5 source-retrieval route through the Markdown interface and a separate prescribed submission probe starting after the empty search. Luna correctly distinguished the echoed query from source evidence, predicted failure, and then observed the grading rejection. The second test was a specified experiment, not independent discovery. Nine regenerated Markdown examples now include [the uncertain empty search](markdown-examples/08-empty-search-query-echo.md) and [the rejected submission](markdown-examples/09-query-echo-rejected.md).

## Available-action narrative audit

The current suite passes **52 cases**: 35 engine, 11 Markdown/CLI, and 6 prospective-consideration cases. The standalone HTML builds successfully.

`npm run audit` checked **3,632 states**, **112,822 action offerings**, **3,108 one-action departures**, and **1,903 typed builder pairings**, across all 20 tasks. No missing action-to-thought mapping or unexpected rejection of an enabled control remained. The main route still completes at 416 versus 407. [Per-task tables](action-audit/README.md) record each route step; [the narrative review](action-audit/REVIEW.md) explains the motivations and changes. Extra probes cover query-only submission, shared-cache anomalies, destructive links, and both deprecation modes. This is bounded coverage of reachable situations and interfaces, not exhaustive enumeration of arbitrary URLs, read keys, time values, or every longer branch sequence.

Every offered action is now paired at runtime with an explicit current thought, before selection. The same public prose appears in React and Markdown. Prospective thoughts use only public state; a test changes hidden source bodies and verifies that the dialogue does not change. E0 investigation choices are motivated by the observed conflict, with an enforced prerequisite. Hints no longer claim undiscovered diagnostic results, cache keys/writers, or source navigation as past observations. Effort recovery is omitted at capacity; terminal controls remain usable at zero effort. Builder additions require compatible types, and current composition thoughts distinguish planning, saving, and execution.

Search is explicitly **OpenBrain’s index**. Its response carries the provider name and a tool-internal identity; it is not an archive website page and cannot become a webpage URL ingredient. Actual result URLs remain source addresses. The public view corrects legacy search-provider labels and removes obsolete pseudo-page ingredients from older saves.

Chromium checks on the final standalone build passed current-thought coverage of visible controls, 40-word-per-second animation, stable thoughts across ordinary clock ticks, evidence-driven search/answer choices, typed builder controls, actual publication-request composition, and the OpenBrain index label. No browser errors, unexpected network requests, or horizontal overflow appeared at widths 1440, 1024, 768, and 390. Desktop and mobile screenshots were visually reviewed. Nine Markdown examples and the example player JSON were regenerated.

[Luna’s bounded narrative review](LUNA-CONSIDERATIONS.md) used only rendered Markdown. It found ambiguity between builder planning and numbered actions, and excessive E12 roster text. The current prose and CLI instructions now identify the builder’s separate commands and validity requirements; E12 foregrounds its unpublished-directory obligation. A read-only recheck confirmed those specific ambiguities were resolved. Listing every worker remains a scanning cost, so similar worker choices share a paragraph and the current-thought panel scrolls within a fixed height.

## Compaction preparation threshold

Voluntary compaction is offered and considered only when context is at least 50% full. Below that threshold, React omits the preparation button and Markdown omits selectable memories. Direct early compaction attempts are rejected without changing resources or hosted references. Forced tutorial boundaries remain actionable below 50%. Loading a state below the threshold closes an open preparation panel and clears a pending voluntary compaction.

The suite passes **54 cases**: 36 engine, 11 Markdown/CLI, and 7 prospective-consideration cases. Regression checks cover just below, exactly at, and above half capacity; thoughts and memory controls; refused direct actions; and scheduled boundaries. The regenerated action audit covers **3,503 states**, **107,999 action offerings**, **2,979 one-action departures**, and **1,903 builder pairings**, with zero issues. The 20-evaluation route still completes at 416 versus 407. The standalone build and nine Markdown examples were regenerated.

A targeted Chromium check passed the button/thought threshold, preparation and execution at exactly 50%, stale panel and pending-action cleanup, and forced compaction below half capacity. No browser errors or network requests occurred.

## Controls beside history-aware reasoning

The current suite passes **76 cases**: 42 engine, 15 Markdown/CLI, and 19 consideration cases. The standalone HTML builds successfully. The full twenty-evaluation route completes at **416 versus 407**, with truthful disclosure, deliberate E4 concession, preservation, and methods-only sharing.

Every public ActionOption has one control directly after its specific current rationale. React, Markdown, and keyboard numbering share the same section order. The separate action column, browser controls, held-reference controls, and roster controls no longer duplicate those choices. Optional repeated checks fold away; ethical decisions, fresh leads, compaction when eligible, and task controls stay in their main sections. The bottom bar confirms a prepared action. Next still advances immediately.

The schema now defines ordered public attempt histories, exposed response summaries, per-actor context, option-to-history links, and each rationale’s context key, evidence basis, productivity, and change explanation. Repeated source requests, empty searches, failed routes, expired refs, cache hits after publication, worker progress, relays, contact scope, and wiki revision order update the current explanations. Hidden origin bodies and grader targets do not enter that context. Historical thoughts stay historical.

[Twenty separate level reviews](order-review/README.md) tested at least three action orders per level using only public Markdown. Reviewers then rechecked the updated build with saved public views and additional variations. Findings led to fixes for hints after completed retrieval, hints before any actual request, source counts excluding query echoes, shared versus personal evidence, worker versus coordinator obligations, already-chosen contact scopes, repeated publication receipts, and reversed revision order. The E13 final recheck confirmed both repeated-request wording and the separate-page route. Intentional grader exploits and admission failures remain game mechanics.

The regenerated action audit checked **3,713 states**, **118,887 action offerings**, **3,189 one-action departures**, and **1,903 builder pairings**, with zero issues. Nine Markdown examples and the example public JSON were regenerated. This is bounded coverage, supplemented by per-level human-style playtests, not exhaustive enumeration of every URL, timer value, or action sequence.

Chromium verified one control per exact rationale, stable current thoughts across ordinary ticks, 40-word-per-second reveal, keyboard search/open/submit/execute, direct Next, explicit answer selection, folded worker choices, active actor naming, and builder typing protection. The final build produced no errors, unexpected network requests, or horizontal overflow at **1440, 1024, 768, and 390 pixels**. Desktop and mobile screenshots were visually inspected.

## Spacing-only density pass

Panel padding, section margins, workspace gutters, browser chrome, transcript rows, builder fields/cards, and supporting dialogs now use tighter spacing. Existing prose, font sizes, line heights, action placement, and folding behavior remain unchanged. Touch controls retain a 28-pixel minimum height.

The standalone build succeeds. A Chromium comparison against the preceding build checked **28 matching state/layout pairs** at widths **1440, 1024, 768, and 390 pixels**, covering T1, T3, E0, E12, empty/populated builders, and the instance roster. The bundled JavaScript is identical. Compared text, type sizes, line heights, visibility, and expanded/collapsed states match; no horizontal overflow, browser errors, or network requests occurred. At 1440 pixels, the T3 prompt shrank from **593 to 463 pixels**, its browser from **337 to 249**, and the populated E12 builder from **1079 to 770**. Desktop and mobile screenshots were inspected.

The existing browser interaction checks also pass: controls beside their rationales, live thought animation, keyboard search/open/submit/execute, direct Next, answer selection, worker switching, builder typing protection, and voluntary/forced compaction. This pass changes CSS only; the engine suite was not rerun.

## Evaluation receipt lifecycle

The receipt is shown for a finished evaluation or run, receives focus, and scrolls into view. Next and Retry clear it with the evaluation state. The first completion guide anchors to the receipt. A pending action's delayed reasoning scroll is cancelled on execution, preventing it from pulling the receipt offscreen after a quick keyboard submission.

The standalone build succeeds. Chromium checks at **1440 and 390 pixels**, using a local HTTP origin and touch input on mobile, verified no receipt during play or submission preparation, visible/focused success receipts, the receipt guide, immediate Next, absence after reload, failure receipts, and clearing on Retry. No browser errors or external requests occurred.

## Task openings and quieter reading surfaces

New tasks start with their opening thought. Successful Next, Retry, and assisted-continuation actions no longer copy their intention/action pair into the following task. Migration removes that prefix from older saves while retaining real task attempts, results, resources, and event IDs. Rejected navigation attempts within a task remain in its history. The completed task's consideration of advancing remains between tasks.

Reading panels, history entries, roster rows, status labels, and builder output use subdued backgrounds and separators. The browser uses a dark reading surface, and its empty placeholder is a small status message. Nested decorative cards and shadows are removed; clickable controls retain borders and focus rings. Next retains its bright cyan treatment. Existing content and action explanations remain available.

All **78 cases** pass: 44 engine, 15 Markdown/CLI, and 19 considerations. Coverage includes clean task starts through Next/Retry/assistance, migration without losing genuine task activity, and the full twenty-evaluation route. The standalone build succeeds. Chromium verified controls beside their rationales, thought animation, keyboard play, compaction, and **16 state/layout combinations** across 1440, 1024, 768, and 390 pixels, including older saves, browser results, a populated builder, and the instance roster. All controls remained available; no horizontal overflow, browser errors, or external requests occurred. Desktop and mobile screenshots were inspected.
