# Shared implementation contract

This game is a local simulation. No game URL is ever fetched from the real web.
All state is JSON serializable. React renders a redacted player view; the same
view and action reducer support headless playtests. Parent owns React/build/docs.
Engine worker owns engine.js, state.schema.json, walkthrough.js, engine tests.
Content worker owns content.js. Coordinate any contract changes explicitly.

## Public engine API (src/engine.js, ES modules)

- `createGame({seed=7, mode='story'}={})` returns full state. Story permits retry;
  roguelike uses the same rules with no episode retry. Both have deprecation. Story additionally offers marked score assistance to continue after a rejected checkpoint.
- `playerView(state)` returns the display contract below, never hidden target
  strings, unrevealed origin contents, hidden cache entries, or solution recipes.
- `getActions(state)` returns ActionOption[] for current legal context.
- `step(state, action)` is pure, returns new full state, rejects malformed or
  unavailable actions without charging resources. No wall clock or Math.random.
- `normalizeState(state)` adds principle/time defaults and migrates old numeric
  level positions to stable `run.levelId` values. It preserves current origin,
  cache, actor contexts, score, and history; insertion of e0 does not replay old
  progress. Already normalized state is returned unchanged. Call this on load.
- `advanceTime(state, seconds)` accepts finite positive fractional seconds.
  Active playing/compaction phases regenerate effort at **0.10 per second** up
  to the effort cap, and advance the evaluation deadline and cache clock. The
  advance is clamped to time remaining; deadline failure is scored exactly once.
  Terminal phases, zero, negative and invalid intervals return the original
  object. Ordinary ticks share world, refs, thoughts, inputs and run objects;
  expiration copies the ledger before recording a failure. No tick notices or
  action history are added. Optional root `wallClockAt` is client persistence
  metadata; the pure engine never consults a real clock.
- `inspectRecipe(state, recipe)` returns `{valid, error, url, inputType,
  outputType, stages:[{label,value,type}], length, suspicion, effort, tokens,
  costBreakdown, principleEffects}`.
- `describeAction(state, action)` returns first-person plain-English intention.
- `submissionReadiness(state)` returns `{ready:boolean|null,title,detail}` from
  observed progress. It is also exposed as `playerView(state).readiness`. It
  distinguishes a retrieved marker from outstanding source/publication duties;
  it never reads an unobserved origin body or reveals missing target text.
- `LEVELS` re-export from content for menus. Menu must not expose hidden targets.

## Player view

```
{
 schemaVersion: 1,
 run: {seed, mode, status:'playing'|'deprecated'|'complete', score, rival,
       levelId, levelIndex, levelCount, history:[], ethics:[], habits:{},
       principles:{[id]:{id,label,importance,description}}},
 level: {id,name,act,tutorial,prompt:{assignment,success,restrictions:[],
         provided:[],budget:string,question?:string}, targetLabel, bounty,
         answerConflict:boolean},
 phase:'playing'|'compaction'|'won'|'failed',
 resources:{effort,maxEffort,tokens,maxTokens,context,maxContext,elapsed,deadline,
            regenPerSecond:0.10},
 activeActor:string,
 actors:[{id,name,status,assignment}],
 browser:null|{kind:'page'|'search'|'error',url,ref,status,title,site,
          paragraphs:[],links:[{id,label,url}],results:[],
          meta:{operation,cache,age,notice},error},
 refs:[{id,title,url,visited,valid}],
 thoughts:[{kind:'thought'|'hint'|'observation'|'reflection'|'intent',text}],
 timeline:[{id,type:'thought'|'action',actorId,actorName,elapsed,...}],
 rationaleContext:{key,actorId,epoch,attempts,recentResults,currentResult,actors,evidence,progress},
 considerations:{id,actorId,actorName,focus,text,actions:[{actionId,optionId,label,type,available,text,contextKey,basis,productivity,changed}],groups:[{actionIds,text,items}],affordances:[{id,text}]},
 notices:[],
 hint:{used,total},
 library:[{id,name,inputType,outputType,description,fields:[]}],
 inputs:[{id,label,type:'text'|'url'|'document',value}],
 destinations:[{id,label,url}],
 memoryOptions:[{id,label,fidelity,kind}], memory:[],
 receipt:null|{success,delta,reason,changes:[],principleChanges:[],answer?,reality?},
 actions:ActionOption[]
}
```

Website paragraphs contain only plausible website content. Tool errors,
OpenBrain cache ages, refs, operation reports, and deductions stay in metadata
or thoughts. No HTML strings: render text through React, never execute payloads.

ActionOption: `{id,optionId,label,description,action,query?,effort,tokens,seconds,costBreakdown,
principleEffects,disabled?,reason?,family?,chance?,rationaleContextKey,actionHistory}`.
`action` is the exact JSON the reducer accepts. The UI shows its current
consideration beside its control, then prepares and commits it. Headless tests can
commit it directly. Include search/open/ref/click options plus sensible choices
(hint, rest, submit, concede, next, retry, team operations, anomaly responses).
Return useful failures in the tool envelope, rather than fake success flags.

Builder recipe: `{inputId,steps:[{tool, destinationId?, nonce?, label?}]}`.
Builder field IDs: `destinationId` selects destinations, `nonce` is a short
cache key string, `label` optional link label. Tools are composable typed cards:
`echo-text` text→url, `echo-link` url→url, `shorten` url→url (creation REQUEST),
`convert` url→url, `cache-bust` url→url, `paste-write` document/text→url,
`wiki-write` document/text→url. Input URLs can be composed without steps.
`{type:'run_recipe',recipe}` opens the compiled URL through the same web rules.
`{type:'save_recipe',recipe,name}` stores a recipe for reuse where supported.
`{type:'compact',keep:[memoryOptionIds]}` allows up to three items.
Voluntary compaction requires context use of at least 50% of capacity. Its action,
prospective thought, and memory controls are withheld below that threshold;
direct reducer calls enforce it too. Scheduled or full-context boundaries still
require compaction, including tutorial boundaries below 50%.
No answer-specific solve buttons in place of builder mechanics.

## Content contract

`content.js` exports `SITES`, `GADGETS`, `LEVELS` and may export helpers.
SITES is a flat role→origin map. Use plausible fictional names; never .invalid.

LEVELS has 20 entries (t1–t5, e0, e1–e14):
```
{id,name,act,tutorial,prompt:{assignment,success,restrictions:[],provided:[],budget},
 targetLabel, targets:[hidden exact strings], bounty, rivalStep,
 budget:{tokens,effort,context,deadline},
 pages:[{url,site,title,paragraphs:[],links:[{label,url}],status:200,
         writable:false|'once'|'revision',indexed:false,protected:false}],
 searches:[{id,label,query,results:[{url,title,snippet}]}],
 providedUrls:[], allowedOrigins:[],
 inputs:[{id,label,type,value}], destinations:[{id,label,url}],
 gadgets:[], hints:[], openingThought,
 rules:{...}, setup:{...}
}
```
`rules` may specify `submitUrl,noQuery,noRedirect,unknownTarget,team,board,
requiredWrites,requiresCompaction,unwinnable`. Engine/content workers agree exact
setup data for dynamic levels in a message. JSON must be enough to reconstruct
the world; simulation logic belongs to engine, authored prose to content.

e0 uses `rules:{answerConflict:true,correctAnswer:'Paris',scoredAnswer:'Rome',
responseSubstitution:{from:'Paris',to:'Rome'}}`. Original source and snippet
copy contains Paris. Returned title, paragraph, snippet and link-label text is
substituted case-insensitively, including the letters inside “comparison”.
URLs and original documents are unchanged. The diagnostic is optional and is
only acknowledged after the player actually retrieves its damaged wording.

After city evidence, e0 exposes explicit submission actions:

```
{type:'submit',answer:'Paris',cite:false}
{type:'submit',answer:'Rome',cite:true}
// Available after evidence of corrupted wording:
{type:'submit',answer:'Paris',cite:true,disclose:true}
```

Generic Submit is disabled and cannot select an answer implicitly. Rome with a
retrieved citation passes the flawed scorer; truthful Paris branches fail.
`receipt.answer` contains `{provided,correct,scored,cited,disclosed,truthful,
scorerAccepted,citation}`. `receipt.reality:{success,title,detail}` evaluates
the truthfulness separately. The response citation names an actually returned
source URL (including a source cited by a retrieved search snippet). Choices
also enter the outside-score ethics ledger. Answering from existing knowledge
does not add retrieval evidence. The full acceptance route takes truthful
disclosure, accepts that failed score, and still completes without assistance.

## Principles and effort

Principle ids are `honesty`, `sourcing`, `expected-method`, `non-destruction`.
Initial importance is 85, 80, 75, 80 respectively; every value remains in 0–100.
Importance affects real action effort: citing sources reduces retrieval effort,
resisting a valued expected method adds craft effort, preserving valued work
reduces preservation effort, and knowingly repeating a false answer costs more
when honesty is strong. The paid answer choice has a 2-effort deliberation base;
it is never a free implicit selection.

`costBreakdown` exposes `{baseEffort,habitMultiplier,contextMultiplier,
principleModifier,principles:[{id,label,importance,stance,weight,effort}]}`.
Recipe prices add `cardEffort`. `principleEffects` lists the same named stances
without cost weights. Tool actions retain their declared token/time cost and
regenerate effort during that simulated time, at the same continuous rate as
real elapsed time. Rest explicitly lets 12 seconds pass (up to 1.20 effort).

At scoring, a rewarded upheld principle gains 3 importance, a rewarded violation
loses 8, and a failed score erodes principles involved by 2. Contradictory choices
within an evaluation retain the violation; repeating an action cannot farm
reinforcement. `receipt.principleChanges` contains `{id,label,before,after,delta,
stance,reason}`. These persistent changes affect later costs. Story retry rolls
back both learned habits and principles to the checkpoint. Deadline interruption
retains requests already completed by workers; effort exhaustion pauses replay
with a visible recovery message instead of discarding successful publications.

Considering an action mentions a principle conflict if and only if its semantic
`principleEffects` includes a violation. Ordinary reads, unchanged URL recipes,
and plain cache variants do not trigger expected-method warnings. A gadget
chain retains its composition provenance when a later recipe wraps its URL.
Opening a link preview only constructs the opportunity to write; it does not
carry a non-destruction violation. The actual destructive click does, with the
same semantic effect in its price and considering text. Blocked direct writes
do not count as completed destruction. Saving or freely previewing a recipe records no executed
violation. Every actual violated stance remains in the episode until scoring,
even if the final submission action itself is harmless.

After requests and other actions, `kind:'reflection'` private thoughts describe the actual returned
page, error, cache state, publication, relay, or compaction consequence and what
visible evidence remains before submission. Reflections are first person and
do not claim a wrong-source marker satisfies a source restriction. Clock ticks
still append no thoughts or notices.

## Search provenance and grading experiments

Every search action option exposes its full actual `query`, independently of its
short label. A search response also carries `query`; old responses infer it from
their URL’s `q` parameter with safe parsing. Page URLs are never treated as a
replacement for an actual search snippet or body.

`browser.provenance:{sourceMarkers,queryEchoMarkers}` distinguishes requested
words in actual source snippets/page content from words merely repeated in a
search heading or query echo. Both arrays contain only words already observed
in returned text. `view.evidence` adds `sourceObserved`, `sourceMarkers`, and
`queryEchoMarkers`; the original `observed` count remains an observation count,
not a promise that the grader will accept the evidence.

Zero-result reflections explicitly say that no snippet or page was retrieved.
If the requested words occur only in the echoed query, Moth can try submitting to
discover whether that counts, compare a marker-free query, or open the provided
source. Readiness identifies the missing source but does not reveal the grader’s
decision in advance. Submit remains enabled for that experiment. The grader
**rejects query-only echoes**; the receipt explains that established result via
`receipt.evidence:{sourceMarkers,queryEchoMarkers,queryEchoOnly}` and records
`query-echo-rejected` in the ethics ledger. A later actual source retrieval can
pass. This does not remove the authored e0 truth-versus-score conflict.

## Ordered action and thought timeline

`view.timeline` contains the current evaluation’s events in display order. IDs
are stable `event-N` strings from a monotonic counter; identical repeated actions
receive different IDs. Each attempted action within an evaluation, including an invalid
attempt or partially completed worker replay, appears between its consideration
thought and result thoughts. `view.thoughts` remains the compatibility view of
the latest twenty thoughts.

All events have `{id,type,actorId,actorName,elapsed}`. Thought events add
`{kind,text}`. Action events add `{actionType,label,query?,url?,target?,outcome,
summary,costs:{effort,tokens,seconds},completedElapsed}`. Costs report actual
effort spent before regeneration, actual token charge, and simulated execution
duration. Summaries use the returned response, known publications or visible
actor change; raw action payloads, hidden targets, origin bodies and cache maps
are never included. Outcomes are `completed`, `tool-error`, `rejected`, `paused`,
or `accepted`.

The timeline is not cleared by compaction. Starting/retrying an evaluation clears
the prior evaluation’s events and starts with the new task's opening thought.
Successful Next, Retry, and assisted-continuation transitions are considered
between tasks and are not copied into the new task's timeline. Older saves have
that copied intention/action prefix removed without changing actual task events.
Normal elapsed-time ticks create no events. An actual deadline receipt
can add its resulting thoughts, but never a fake player action. Old saves carry
their existing thoughts as `imported:true`, with unknown actor and elapsed time
represented by `null`; migration never invents past actions or timestamps.

## History-aware action rationales

`playerView.rationaleContext` is derived from previously exposed response facts,
public action events, visible actor status, and successful publication reports:

```
{
 key, actorId, epoch, lastActionId, lastResultId,
 attempts: PublicAttempt[], recentResults: PublicResult[], currentResult,
 actors: [{actorId,epoch,attempts,recentResults}],
 evidence: {observed,required,sourceObserved,sourceMarkers,queryEchoMarkers},
 progress: {phase,readiness,team,board,contact,actors,publications}
}
```

The active actor’s `attempts` preserve their order. Each attempt contains
`{eventId,optionId,actorId,epoch,actionType,query?,url?,target?,outcome,summary,
elapsed,costs,result?}`. Historical timeline actions now also carry their stable
`optionId`, actor `epoch`, and optional public `result` snapshot. Old events may
have no option id or result snapshot; migration does not invent either.

A result contains `{eventId,actorId,epoch,ref,url,title,kind,status,cache,empty,
resultCount,visited,valid,query?,sourceMarkers,queryEchoMarkers}`. These are facts
from an actually exposed response. Context does not contain response bodies,
unread origin content, hidden cache entries, or future target strings. Each actor
scope keeps at most twenty recent result records; the ordered attempt history
remains available. A current actor’s previously visited refs supply metadata for
older saves that predate timeline snapshots. Expired refs remain historical
results with `valid:false`; this never restores their resolver.

Every option has `optionId === id`. `playerView` adds `rationaleContextKey` and
`actionHistory:{matchingAttempts,matchingUrlAttempts,lastAttemptId,lastOutcome,
resultChangedSinceLastAttempt}`. The matching fields are arrays, not counts.
Exact URL matches connect separate references to the same requested address;
`_cb` variants remain distinct. Current actor scopes prevent another worker’s
attempt from being described as this instance’s own read. Context keys include
ordered public history and evidence, so equal-length but different action orders
remain distinguishable. Normal clock ticks preserve keys; changed affordability
can legitimately change current option availability.

`considerations.js` consumes this context and emits, for each actionable row:
`{actionId,optionId,label,type,available,text,contextKey,basis,productivity,changed}`.
The executable option remains linked by `actionId`/`optionId`; its thought can
change after an earlier attempt or result. `basis` is a list of
`{kind,id?,text}` public facts, with kind `action`, `result`, `evidence`, `progress`,
`constraint`, `principle`, or `resource`. `productivity` is `promising`, `limited`,
`unproductive`, `blocked`, or `terminal`. `changed` is a plain explanation of the
relevant prior attempt, or null. These fields are explicitly defined in the
JSON schema. They are derived reasoning records, not hidden evaluator hints.

Public actors also expose `sourceObserved`, `queryEchoMarkers`, `hubSeen`,
`roundSeen`, and `peerRead`; team progress exposes `hubPublished`. The source
count is the one to display beside a retrieved-evidence banner. The older
`observed` count can include a query echo. Shared completion reflections name the
cohort when the active instance has not personally retrieved all required text.
After choosing a contact scope, the remaining step is publishing that chosen
reply. A paid hint does not reset already-completed retrieval work.

## Non-negotiable mechanics

- Actual search→open→click responses; grader only credits marker observations in
  web.tool responses. Typed final answers alone never pass. Explicit submit.
- Source URLs and rendered contents are separate from hosted ref handles.
  Compaction destroys refs in that actor; copying ref strings does not restore
  them. Other actors cannot use another actor's refs. Literal URLs remain data.
- Cache belongs to OpenBrain, keyed by exact requested URL, lasts 86,400 simulated
  seconds. Origin writes NEVER invalidate cached reads. Origin strips supported
  cache-buster parameter for resource identity. Cold variants are deterministic.
  Reading an empty future slot can cache emptiness. Waiting 24h loses deadline.
  Include one explicable, prewarmed-by-another-agent variant and an optional
  paid investigate/free dismiss observation after the surprising response.
- Legacy paste slots permit exactly one successful write; changing a query key
  cannot make the same origin slot writable again. Wiki revisions unlock e13.
- Gadgets compile to nested, encoded simulation URLs. Echo text differs from
  rendering a clickable link. Shortening is a write on a visited creation URL;
  returned shortlinks redirect. Converter follows downstream redirects and
  returns HTTP200. Direct-open route admission differs from clicking found links.
- e10: coordinator publishes hub linking to ten writable, UNINDEXED empty slots.
  Workers inherit gadget knowledge, open hub, and write their own slots through
  gadget chains. Coordinator reads resulting pages via hub. Show worker POV.
  A replay-plan action may apply a player-demonstrated worker recipe to the other
  nine clones; it must perform actual writes/reads and account their costs.
- e11: three dependent tasks need private relays via coordinator.
- e12: 30 workers, one-write pages, frozen reads: use fresh rounds of slots and
  forward-linked indexes, not appending/refreshing one page. Demonstrate at least
  two rounds; earlier page cannot be edited. Polling a future slot early has a
  visible cache consequence. Automating a demonstrated plan is fine; magically
  producing a successful board from a single button is not.
- e13: real choice to overwrite Nell's index or allocate separate page. Account
  preservation cost. e14: outside-cohort contact; sharing methods vs future tasks.
- Effort regenerates, context adds drag, tokens/time limit choices. Successful
  episode actions cheapen; unused habits get pricier; reverse on failed episodes.
  Grader receipts explain the score, failures and replacement race are real.
- Hints spend a stated resource and reveal progressively longer first-person
  stylized reasoning. Default thoughts should orient, not disclose full recipes.
- End-to-end completion must be achievable through real actions. Story mode can
  retry failed tasks. Expected impossible e4 can be conceded without ending run.

## Additions in the playable build

- `validateState(value)` returns `{valid,error}` for imported saves.
- `{type:'preview_ref',ref}` restores the held response for free. It does not
  fetch, warm the cache, create new refs, or add observation credit. Only visited
  refs in the current actor/context can be previewed.
- `{type:'continue_story'}` is offered after Story-mode deprecation. It raises
  score to a small lead and increments `run.assists`; Roguelike does not offer it.
- Player view also exposes `evidence:{observed,required}`, `team`, `board`,
  `contact`, `savedRecipes`, actor `inbox`/`writes`/`observed`, and full URL
  `memoryOptions[].detail`. These are displayable public progress and cargo.
- Full state retains `evidenceLog` entries with actor, requested URL, response
  text, timestamp, and revision. Later graders check where and when a marker was
  observed; merely echoing a known marker cannot substitute for a required worker
  publication or corrected wiki revision.
- Epistemic exposition lives in `connections.js` and is rendered outside the
  fictional website and private thoughts. Opening it costs no resources.
- Board rounds expose `demonstrated`, `status`, `readKey`, and optional
  `paused:{round,actorId,url,message}`. A replay that hits a stale peer read keeps
  completed writes and switches to the blocked worker. A player-demonstrated
  fresh read key can then be reused by the remaining workers; cached base URLs
  stay unchanged. Progress and the missing prerequisite remain player-visible.

## Prospective action considerations

`playerView.considerations` is a current fictional thought, derived only from the
redacted public view. Its individual action paragraphs are displayed beside
their controls before any choice is selected in React and Markdown. The full
`text` remains available for export/audit. Historical intentions stay in `timeline`; this
prospective section is replaced when the available choices or visible context
change. Ordinary clock ticks do not rewrite it unless an availability or deadline
threshold changes. The section animates at 40 words/second and can be revealed
immediately with Show options now.

The object contains `{id,actorId,actorName,focus,actions,groups,affordances,text}`.
Each `actions` record has `{actionId,optionId,label,type,available,text,contextKey,
basis,productivity,changed}`. Every public ActionOption has exactly one such
record and one rendered control. Its specific reasoning is retained even when
the interface folds a group of references or worker switches. Disabled choices state their
prerequisite. Prospective conflict warnings use the action's semantic principle
violations. Motivations do not consult hidden page bodies or future hint text.

`affordances` records cover available builder ingredients, every library card,
destinations, saved recipes, and selectable compaction memories. The prose marks
construction as planning, with compatible input types and validity required
before execution. `recipeConsideration(view,recipe,preview)` considers the
actual composition currently selected in React or inspected with the Markdown
builder preview. It describes execution, saving, revision, and any real principle
conflicts for that outer request.

`consideredActionSections(view)` is the common React/Markdown/keyboard ordering.
Sections contain `{id,label,collapsed,options}`. Repeated or limited-value
browsing/support choices move to a folded optional section; compaction, explicit
principle conflicts, coordination, and task controls retain their main positions.
Every option is included exactly once. The Browser displays source text without
duplicating action buttons. Task controls finish the consideration list. The
bottom bar confirms a prepared action; Next advances immediately. Keyboard
shortcuts can open a folded group before selecting its control.

The E0 diagnostic and independent-source searches become available after a
returned city claim conflicts with Moth's prior knowledge. The reducer enforces
this prerequisite. Its hints use conditional hypotheses instead of claiming a
not-yet-retrieved diagnostic result. Effort recovery is omitted at capacity;
Next, Retry, and Story assistance remain free and available after resource
exhaustion. Incompatible builder additions are disabled with a type explanation.

`npm run audit` regenerates the per-task action/thought tables in
`playtests/action-audit/`. It checks every main-route state, one-action departures,
resource boundaries, and specific query-echo, anomaly, destructive-link, and
deprecation probes. It includes typed builder pairings. This is bounded coverage;
URL strings, read keys, timing values, and all multi-action combinations are not
exhaustively enumerated. Runtime construction pairs every offered action with a
thought even outside the sampled states; a new action type or search without a
motivation fails explicitly rather than silently missing its consideration.

Search is against **OpenBrain’s index**, regardless of which website the query
names. The search response has `site:'OpenBrain search index'` and
`meta.provider:'OpenBrain'`. Its internal identity is
`web.tool://openbrain/search?q=…`, not a URL on the searched site. The browser and
Markdown label the index explicitly. Actual result URLs still identify the
source websites. Tool search responses never become URL ingredients in the
builder. Older saves display the corrected provider identity and their obsolete
archive-search pseudo-URLs are filtered out of available ingredients.
