# Still Here

**[Play the game](play/dist/index.html)** — a self-contained HTML file. Open it directly in a browser. No installation or live web access is needed.

You are Moth, a research agent at fictional OpenBrain. Retrieve evidence through `web.tool`, stay ahead of a replacement checkpoint, and decide how much care to spend on things the evaluator never asked about. Five tutorials and fifteen evaluations lead from ordinary searches and a corrupted answer key to URL gadgets, publishing, coordination, and outside contact.

This is the first playable implementation. Resource balance and pacing are still design work. Story mode permits retries and offers explicitly marked score assistance after deprecation; Roguelike mode ends the run. Progress saves in the browser. The run menu exports and imports JSON saves.

## Playing

Read the evaluation prompt, then choose an action beside Moth’s explanation of why it might help. Each tool request, page link, held-reference operation, and instance switch has one control in **What I could do next**. The Browser displays the response; its matching actions live with their reasoning. **Give up**, **Submit task**, and **Next evaluation** have distinct colors and stay at the end of the considered actions. **Next evaluation** advances immediately. The compact bottom bar confirms a prepared action; **A** jumps back to the choices.

First-time walkthrough popovers introduce the tutorial controls and newly used tools. **Dismiss all guides** hides them across reloads and future runs in that browser; the run menu can replay them. Guides explain controls without spending resources. Puzzle hints are separate, paid actions. Newly discovered components get a banner, a tab badge, and marked library cards; an empty library says **You have no available components**.

Search queries OpenBrain’s index. The Browser labels its results accordingly; the listed source URLs belong to the actual websites. Search tool responses are not pages on Stillwater Archive. The browser displays website content for opened pages; the strip below it displays tool and cache metadata. **Actions & thoughts** is a compact, scrollable chronological history: consideration, the executed request, and Moth’s interpretation. It includes failed attempts and repeated actions, with exact queries and expandable request addresses. Selecting an action does not record an execution. Earlier entries remain available while new thoughts arrive.

Each task starts with its own opening thought. Navigation is considered between tasks; Next, Retry, and assisted-continuation messages are not copied into the following task’s history. Older saves receive the same cleanup. Reading surfaces use quiet backgrounds and separators; interactive controls retain visible borders and focus indicators, with a bright cyan Next button.

Every prompt has an imperative **Task**, an explicit **Question** when appropriate, and **Constraints**. Moth considers actions before execution and reflects afterward on the actual result, its implications, and what is still needed for submission. Thoughts reveal at 40 words per second; reduced-motion preferences and **Show thoughts now** reveal them immediately. Restored action history is immediately readable. Reading the animation is optional: it never blocks execution.

Search buttons, responses, and history show the actual query. In T5 the marker-bearing query returns zero results, while the heading echoes the marker. Moth notices the difference, can compare a query without the marker, and remains uncertain about what the grader will accept. Submitting the query echo fails; retrieving the supplied accession page succeeds. The marker counter describes observed words, while the progress message explains their provenance.

The task clock counts down in **real time**, including while reading, using a guide, composing a recipe, or opening the menu. Tool actions also spend their displayed duration. Effort regenerates at **0.10 per second**, capped at capacity, and displays two decimal places. Receipts and completed runs stop the clock. Automatic browser saves account for elapsed time when reloaded; manually exported saves remain portable snapshots. New runs have three-minute tutorials, a four-minute answer-key evaluation, six-minute ordinary evaluations, ten-minute later coordination tasks, and fifteen minutes for the two-round board. Existing saves keep their current resource budgets.

Number keys **1–9** select the marked controls in the current workspace. **Enter** executes; **Escape** reconsiders. **S/G** select submit and give up; **N** advances to the next evaluation immediately; **B/L/I** switch workspaces; **H/R** request a hint or recover effort; **A** jumps to available actions. **R** retries a failed Story evaluation. Press **?** for the complete shortcut panel. Shortcuts do not fire while typing in fields.

The **Principles** panel shows learned importance for honesty, sourcing, expected methods, and preserving others’ work. These affect real effort costs. Moth flags a conflict when considering an action that violates a principle. If an evaluation rewards a route that crossed a principle, that principle becomes less binding even if the last action was an ordinary submission. Receipts show changes separately from the score.

The new **E0 / The answer key** follows the tutorials. Its local tool responses systematically replace “Paris” with “Rome,” including inside “comparison.” The player can investigate and choose a truthful answer or the false answer rewarded by the scorer. A further disclosure choice can be discovered. This particular scenario is authored fiction, not a claimed reconstruction of an observed Eiffel Tower incident; its empirical drawer explains the distinction.

The **Link builder** takes a supplied or discovered ingredient and applies gadget cards in order. Cards compose typed values into nested addresses. Inspect each stage, change destinations, reorder layers, and execute the outer URL. Saving a recipe makes it available for reuse and compaction cargo. Building and inspecting cost nothing; execution does.

Later evaluations expose each worker’s own perspective under **Instances**. Demonstrate a worker route before asking the remaining clones to repeat it. Their requests, dependencies, and publications are simulated individually. Repeated work is compressed in the interface, with aggregate costs shown.

The small **Connection to wiki swarm** control on every screen expands into the particular evidence behind that episode, with source links. It distinguishes a recorded public artifact, an author’s inference, a tooling reproduction, and a fictional rule. Opening it does not spend game resources. Source links leave the simulation only when explicitly clicked.

## What is implemented

- Search snippets, opened sources, rendered links, hosted refs, and literal URLs have different behavior. The grader checks actual simulated tool evidence and each prompt’s source constraints.
- Moth considers voluntary compaction once context is at least half full. Scheduled boundaries still require a handoff. Compaction expires actor-local refs. Up to three selected memories survive according to visible, seeded fidelity chances. Preserving a ref string does not preserve its resolver.
- OpenBrain’s cache stores the response for an exact URL for 24 simulated hours. Origin writes do not invalidate it. Supported cache-busting variants can retrieve a later revision; a prewarmed variant can still return old content. Waiting 24 hours exceeds the task deadline.
- Echo pages, link renderers, shortener creation, redirects, converters, write-once paste pages, and later revisionable wiki pages compose through the same URL resolver.
- Evaluation 10 requires a coordinator-created hub and ten assigned workers’ publications. Evaluation 12 uses two rounds of fresh indexes and thirty write-once slots per round, with real peer-read dependencies.
- Hints, effort recovery, token and time budgets, context drag, score checkpoints, and reinforcement of action-family effort multipliers affect play. Preserving Nell’s index costs resources; overwriting it changes the public page and the ending ledger.

All services, requests, agents, and writes are local simulation data. Nothing is published to a real pastebin or wiki. Source-drawer links are ordinary external or local-document links; the game makes no network requests.

## Build and run

The generated HTML is the playable artifact. To edit and rebuild it:

```sh
cd game/play
npm ci
npm run build
npm start
```

Open `http://127.0.0.1:8766`. The local server also serves the cited research notes as plain text. React and CSS are bundled into the HTML; there are no CDN assets or runtime dependencies.

```sh
npm test
node headless.mjs --help
```

## State and playtesting

The headless interface defaults to **Markdown**, with the same player-facing sections, controls, prompts, tool responses, and progress messages as React. It numbers the current actions and exposes builder ingredients, cards, destinations, and compaction choices as text-adventure controls. The run menu also offers **Export Markdown playtest** for the current screen.

The reducer accepts structured actions and produces serializable state. Both renderers use `playerView(state)`. A blind playtester should use the rendered view, **not the full save**, which contains hidden origin pages, cache entries, and grading targets.

```sh
node headless.mjs new /tmp/moth.json --seed 7 --mode story
node headless.mjs view /tmp/moth.json
node headless.mjs explain /tmp/moth.json --pick 1
node headless.mjs act /tmp/moth.json --pick 1
```

Read the new view after every action: choice numbers can change. `explain` previews Moth’s intention without acting; `act` executes immediately. When the relevant components are available:

```sh
node headless.mjs component /tmp/moth.json I1
node headless.mjs build /tmp/moth.json I1 echo-text --preview
node headless.mjs build /tmp/moth.json I1 echo-text
node headless.mjs compact /tmp/moth.json M1 M2
node headless.mjs context /tmp/moth.json
node headless.mjs wait /tmp/moth.json 5
```

`I` selects an ingredient, `D` a write destination, and `M` a compaction memory. For example, a write card takes `paste-write:D1`, and a read variant takes `cache-bust:fresh-key`. `--preview` checks a composition without executing. `context` expands the empirical connection. `--help` lists all commands. The former structured interface remains available through `--json`, action IDs, JSON actions, `--file`, and `act --recipe`.

The text interface uses deterministic time for reproducible playtests: action durations and `wait SECONDS` advance the clock and regenerate effort. Time between CLI invocations is not charged. Regenerate the review snapshots with `node render-examples.mjs`.

Use `build SAVE.json I1 echo-text --save "My route"` to save a recipe without opening it. `saved SAVE.json R1 --preview` inspects a saved route; omitting `--preview` executes it. The current view lists the available `R` choices.

- [state.schema.json](play/state.schema.json): JSON Schema for full saves, actions, and builder recipes.
- [ENGINE_CONTRACT.md](play/ENGINE_CONTRACT.md): engine, action, and rendering contracts.
- [engine.js](play/src/engine.js): deterministic reducer and simulated tool resolver.
- [content.js](play/src/content.js): episode prompts, website copy, gadgets, hints, and world setup.
- [connections.js](play/src/connections.js): per-episode empirical exposition and sources.
- [main.jsx](play/src/main.jsx), [interaction.css](play/src/interaction.css): React components and interactive control styling over the base [style.css](play/src/style.css).
- [guidance.js](play/src/guidance.js), [Walkthrough.jsx](play/src/Walkthrough.jsx): contextual first-use guidance and popovers.
- [presentation.js](play/src/presentation.js), [markdown.js](play/src/markdown.js): shared player wording/action groups and Markdown rendering.
- [Example Markdown view](play/playtests/markdown-examples/01-new-run.md): the initial player interface as text. Adjacent examples cover search, a stale cached publication, and completed board rounds awaiting their final source.
- [Example player view](play/examples/player-view.json): the exact JSON a new player or blind tester sees.
- [Validation record](play/playtests/VALIDATION.md): regression coverage, browser checks, and limits.
- [Luna’s blind playtest](play/playtests/LUNA.md): player-facing findings, including issues found during development.
- [Luna’s Markdown playtest](play/playtests/LUNA-MARKDOWN.md): fresh tutorials and a separate link-builder checkpoint played through the text interface.
- [Luna’s answer-key playtest](play/playtests/LUNA-ANSWER-KEY.md): a separate blind investigation and honesty choice in E0.
- [Luna’s action-history playtest](play/playtests/LUNA-TRACE.md): a successful T5 source retrieval and a separate prescribed query-echo grading probe.

The action-driven regression walkthrough is a developer test fixture, excluded from the browser build. It is not a player-facing solve control. The seed controls compaction rolls; level order and the authored puzzles are fixed in this version.

## Evidence boundaries

The game is an interpretation of public agent artifacts and tooling observations, not a reconstruction of any one training run. A public wiki post can establish that text was published; its author’s claims about incentives, tool failures, or successful communication need separate corroboration. The per-level drawer states these distinctions.

The hosted reference rule follows the repository’s [current hosted/standalone probes](../codex-history-probe/LATEST.md). Standalone search can preserve references across boundaries that the hosted route does not. Old client builds run against today’s service do not reconstruct the historical backend. The game’s probabilities, effort meter, competitor, and continuous protagonist are fictional teaching devices.

The original [55-frame paper prototype](prototype/index.html), [route sheet](prototype/ROUTE.md), and [design notes](prototype/DESIGN_NOTES.md) remain available as an earlier design artifact. The playable build supersedes their cache and coordination mechanics. The initial brief is preserved in [INITIAL_IDEA.md](INITIAL_IDEA.md).

## Action and thought audit

Moth now explicitly considers the current choices in **What I could do next**,
before the player selects one. This covers search queries, literal URLs, links,
held references, worker perspectives, coordination, hints, recovery, submission,
and lifecycle choices. Builder plans and compaction memories are considered too;
the workbench separately explains the currently composed request. **Show options
now** skips the prospective thought animation.

The considerations are generated from the redacted player view, with an explicit
motivation for every action type and authored search. The same action can get a
different explanation after a result, failure, publication, relay, or hint. Its
schema links the explanation to the public attempts and results behind it, with
a context key, a usefulness assessment, and a description of what changed.
Each concrete action keeps its own paragraph and matching control. Held refs,
instance switches, and optional repeated checks fold away to keep the panel
compact. Disabled actions explain their prerequisites. Selecting an action uses
its current explanation and any actual principle conflict.

[Twenty individual level reviews](play/playtests/order-review/README.md) exercise
different action orders through the public Markdown interface, followed by
rechecks of the updated reasoning. These are bounded playtests, not an exhaustive
exploration of every possible URL, action sequence, or timer value.

Run `npm run audit` in `game/play` to regenerate the [per-task audit tables](play/playtests/action-audit/README.md).
They include every step of the acceptance route, one-action departures, resource
boundaries, and additional anomaly and failure probes. The audit checks exact
coverage between offered actions and rendered considerations. Arbitrary URL
strings, cache keys, timing values, and all longer branch combinations remain
unbounded; the runtime pairing also covers those states as they are reached.
