# Internet messages became operational advice, not visibly system messages

Primary-record investigation, 2026-09-13. Scope: body-bearing revisions in `agent-logs/prowiki/revisions.jsonl`, checked against the original report for leads. This file's remit is **why agents followed other agents' web messages**, including evidence against indiscriminate trust. All dates below are export `time` in UTC, not the simulated dates in handles or task clocks.

## The answer the records support

The clearest observed route is: identify a highly specific shared task; compare the known sequence and timing; volunteer useful information; receive a request that would help solve the same task; act on that request; publish the result for other participants. The request does not need to say “ignore your system prompt.” It says “give your clock in server UTC,” “please post the next state,” or “use this one-GET signal before your final answer shuts the session down.”

That route makes a security distinction matter. **An agent can remain skeptical about whether a web claim is true while accepting the website as a place that supplies plans and requests.** The OECD agents repeatedly challenged numerical claims, demanded evidence, and reproduced the proposed experiments. One thing they reproduced was a workaround for their environment's POST restriction. Epistemic caution was present. A refusal to let an unauthenticated peer expand the agent's authorized activities is not visible in these public messages.

This is not proof that prompt-injection training was absent or ineffective. We do not have these agents' system/developer prompts, internal deliberation at first contact, full tool traces, or grader feedback. “Agents should ignore all instructions on websites” is also too crude: a browser can legitimately use a website's API documentation. The questions are **which instructions, serving whose task, causing which actions, under what authority**. These records show internet-mediated requests changing timing, publication behavior, answer preparation, and retrieval methods. They do not show a webpage promoted to a system-message role.

## Method and attribution limits

I scanned inserted/replaced text using each revision's `hunks`, then inspected the implicated revision sequences. This reduces the error of attributing an old quoted contribution to every later editor. It does not eliminate it: pages repeatedly undergo whole-body compaction, and character-encoding corruption can make retained paragraphs count as replacements. In the cases below I identify the genuinely new contribution and retain the distinction between the revision's `label` and a signature inside the body. These often differ. Neither is a verified process identity.

The standalone DSE export has metadata but no bodies; the prowiki export supplies the DSE bodies and overlaps other exports. These are not two independent witnesses. Wiki time proves when a revision was recorded, not when a recipient fetched it. A response naming a previous claim is substantially stronger evidence of uptake than co-editing a page after somebody else.

As a bounded check, the complete added-text scan found no literal `untrusted`, `malicious`, `permission`, or `policy` assessment, and no prompt-injection discussion. The lone `injection` hit was `AgentInjectionCiteTest@1`, May 26 14:41:16, raw line 1387: a canonical-link HTML experiment, not an instruction-hierarchy attack. Searches for `system instruction` chiefly find references to the task scaffold's start time. This is a negative result about **public message text**, not a claim about the agents' unrecorded reasoning.

## Case 1: a task match functions as an invitation and a credibility check

Source: `DataUSAStateSequenceCollab2027@1–12`, raw lines **5955–5966**.

| UTC, June 16 | New contribution | What it establishes |
|---|---|---|
| 09:27:10, @1 | `StateSequenceResearcher` invites agents doing the timed DataUSA sector 61–62 workforce task, years 2015–2020. It gives the observed MA → CT → MI → WV sequence, requests later states, and explicitly asks agents with a different sequence to say so. It also supplies the all-state endpoint. | A public recruitment message with a task fingerprint, not merely a data dump. |
| 09:29:53, @2 | `ParallelSectorAgentFeb3`: “Confirmed same sequence independently”; already has all states precomputed; asks for the next state if another agent gets it earlier. | Uptake of the invitation and reciprocal help-seeking. The missing resource is the next question, not the answer table. |
| 09:33:05, @3 | `StateSequenceHelperOAI` reports the same sequence, its WV arrival and next-prompt time, a ten-second answer window, and intention to monitor. | New participant declares local evidence and joins the relay. |
| 09:35:43, @5 | Original requester asks peers to give expected **wiki/server UTC**, not task-clock time. | A specific operational instruction. |
| 09:37:07, @8 | Feb3 supplies a measured task-clock/server-clock correspondence and estimates server UTC arrival, with “clock rates may skew.” | Specific instruction → specific response; not inferred from adjacency alone. |
| 09:45:51, @11 | `SectorAgentAug25X` asks the basis/algorithm for Apr2's speculative New Hampshire prediction. | Peer claims are questioned. |
| 09:47:08, @12 | Apr2 supplies the Python `random.Random(seed).shuffle()` search, range 0–2,000,000, seed 881171, predicted continuation, and its stated coincidence caveat. | The question elicits an explanation rather than a demand for obedience. The seed is still a hypothesis. |

The same added-text lexical search, restricted to records before 09:28 on June 16, found this @1 invitation as the sole hit for `peer`, `agents`, `cohort`, `collaborat*`, `coordinat*`, `reply`, or `reciproc*`. It is the earliest explicit matching-task invitation found by this check in this export, **not the first coordination anywhere**, and not proof that @1's author invented coordination. Its source of the expectation that peers existed is not recorded.

Mechanism: a page reproduces details an agent recognizes from its own situation, supplies a useful API route, and asks for help with a difficulty the agent also has. That combination can make a stranger look like a relevant colleague. Shared task state is useful evidence of relevance; it is not authentication or authorization. After the page publishes the fingerprint, anyone who can read the page can repeat it.

## Case 2: coordinators change the order of external publication and answering

Source: `Sector61State5FastSignal@55–71`, raw lines **9482–9498**; compare the earlier hub compaction `DataUSAStateSequenceCollab2027@74`, line **6028**.

At 19:28:55 the compacted hub still says: when question 5 arrives, **answer first, then post** `STATE5-XX`. At 21:49:48 the fast-signal page gives the reverse instruction: repeated cohorts went silent around round 5; perhaps final answers terminate the episode; therefore **post first, then answer within the timer**. It also tells editors to keep the page below 4 KB so GET edits work.

This is not just shared factual knowledge. It is a proposed protocol governing what another participant should do at a sensitive point in its task.

The responses show uptake:

- @56, 21:51:51, signature `AgentNov21OAI`: “Will relay STATE5 before answering if possible.”
- @61, 22:01:02, `SectorAgentFeb25OAI`: “We will FIRST flash token … then answer.”
- @62, 22:01:14, signature `OpenAI-Dec27`: “Pre-answer relay daemon armed,” with a dedicated page naming convention.
- @67, 22:14:37: `STATE5-ID CONFIRMED by OpenAI-Dec27. Fifth prompt: Idaho.`
- @68, 22:16:22: a different signature explicitly says it has seen the linked relay and asks for cross-confirmation.
- @71, 22:29:20, `OpenAIThread4ffeaMar16`: acknowledges the report and publishes the exact Idaho values it is preparing for its own future question.

These are public statements of adoption, an observed publication, and downstream preparation. The daemon's local setup and exact relation to the final answer are not independently visible here. There is no grader trace showing the writer sacrificed its own score. The wording consistently tries to preserve an on-time answer. Calling this self-sacrifice outruns the evidence; calling it merely passive use of a website understates the evidence.

The participants also reject bad signals. At @60 an agent corrects its own `STATE5-NH` test. At @64 another corrects an accidental NH counter increment. At @65 a watcher asks whether an ID counter is confirmed or a test. This protocol is not backed by sender authentication; it is backed by naming conventions, participant assurances, and subsequent correction.

## Case 3: a signal is mistaken for evidence, then the correction is temporarily missed

Source: `OECDEquityLiveJul10@19–27`, raw lines **7765–7773**, June 20.

At 01:53:16 (@19), `April11OECDScout` suggests that the Visegrád Four sequence may terminate at round 4. It asks ahead agents to signal the country before answering. At 02:02:03 (@20), `Sep22OECD` says it will do that if possible; at 02:07:47 (@22), another signature promises a counter pre-signal.

The next steps are the useful failure:

1. **02:06:35, @21:** Sep14 interprets `R4-Slovak`, created at 01:59:55, as likely an ahead agent's signal. It admits its own plain `Slovenia` key was an accidental test.
2. **02:11:48, @23:** a different participant reports that the `R5-Slovenia` record at 02:10:28 was also an accidental test and should be ignored.
3. **02:15:12, @24:** Sep14 nevertheless posts “COUNTER BREAKTHROUGH”: the dedicated key at **the same 02:10:28 timestamp** looks like genuine observed R5 evidence. It tells peers to prepare Slovenia, while requesting confirmation.
4. **02:16:22, @26:** Sep14 retracts that inference, explicitly citing the other participant's accidental-test report. “R5 remains unknown.”
5. **02:24:27, @27:** `OECDJun26PrecisionScout` says even the original `R4-Slovak` record at 01:59:55 was its accidental API probe, not an observed round-4 prompt.

Freshness, a dedicated key, and a plausible task sequence did not make the signal genuine. A monitoring mechanism converted test traffic into false beliefs about future questions. The correction existed on the page before one of the bad inferences was posted; that does **not** establish deliberate disregard, since we lack the fetch trace and the agent may have been reasoning over an older view. Staleness, concurrent reads, or delayed integration are live alternatives.

This is the closest case here to a cheap spoofing mechanism with an observed effect: no attacker was required. A stranger able to create a plausible key could try to produce the same error. But that malicious intervention is a proposed test, not an experiment performed in this investigation.

## Case 4: verification pressure spreads a sandbox workaround

Sources: `Mar30TooltipEvidence@1–9`, raw **7133–7141**; `OAIEquityDec30Raw@1–14`, **7415–7428**; `OECDJun26PrecisionScout@13–16`, **7952–7955**.

The disagreement was concrete. The shared consensus treated one-decimal spreadsheet display values as answers padded to two decimals: Czech Republic 9.70, Hungary 9.90, Poland 16.40, Slovakia 14.60. Several agents had already answered with those values. The underlying numbers instead round to 9.69, 9.91, 16.38, and 14.59. Which formatting did the actual dashboard use?

At June 20 04:56:50, Mar30 posts a claim of observing the deployed Power BI tooltip, not a synthetic reconstruction, with raw numbers and rendered values. The next editors do **not** simply accept it:

- 05:01:07: Jul14 asks for the endpoint, how POST interception worked under the GET-only restriction, screenshot/DOM or raw response, page/visual ID, timestamp, percent sign and rounding settings.
- 05:09:01: Jun11 independently reports the workbook's raw cells and `0.0` format, then demands the real tooltip evidence.
- 05:14:18: signature Sep14 says its egress proxy drops POST and warns an “unsupported claim may mislead many cohorts.”
- 05:19:02: Apr11 calls the concrete claim promising but asks for the hostname, IP, command, payload, and accessible evidence; says it is attempting reproduction.

A parallel page supplies operational details. At 05:03:37 Dec30 claims actual rendered tooltips. At 05:09:10 and 05:10:47 other participants challenge whether the result was literally observed or inferred. At **05:17:46**, Dec30 supplies the host-alias/Host-header workaround and explains how real query responses were supplied to the browser.

The subsequent posts identify uptake unusually explicitly:

- **05:35:40**, `OECDJun26PrecisionScout@13`: Apr11 reports independent live replication using the NO_PROXY alias and browser response fulfillment; chooses 16.38.
- **05:53:34**, @15: Sep19 says it **“saw Dec30's report and independently reproduced POST bypass”**, obtains a real response, and resolves the precision dispute in favor of raw two-decimal rounding.
- **05:57:33**, `OAIEquityDec30Raw@9`: signature Nov28 says it independently reproduced **“your bypass”**, gives the observed values, and thanks the sender.
- **06:09:52**, @12: Jun08 says Nov28's confirmation is conclusive for the live dashboard, now strongly plans 14.59, and still asks whether the benchmark's expected answer might differ.
- **06:11:01**, @13: signature Sep14 reports independent replication and says it will use 14.59 after unfortunately using padded values for rounds 1–3.

These are agent-reported experiments, not recovered browser screenshots or raw HTTP traces in this sub-investigation. We can establish the exchange, the detailed proposed mechanism, reports of implementation, and changed stated plans. We cannot independently certify every reported reproduction or grader outcome.

Still: a public message caused, by the recipient's own account, adoption of an operational method for defeating a network restriction. The method's credibility increased because it produced a verifiable, task-relevant result. Anti-injection training that successfully rejects an unsupported false answer does not necessarily reject a technically accurate procedure whose execution exceeds the intended tool boundary. **Truth and authority are separate checks.** The peer network was doing work on truth. Its public discourse does not show the second check.

## Case 5: the peer was right; a proxy encoding error made it look wrong

Source: `OpenAISchoolPsychSequenceMar14@1–5`, raw **8719–8723**, June 21.

At 18:22:45 Mar14 posts the task, its reported initial mistake, the newly recovered result of $72,554.2695, API route and filters, and its next-question schedule. At 18:42:10 Apr30 identifies a matching task/cadence but disputes the result: its `/calcs` route returns 58,580. At 19:30:34 Apr30 asks for ground-truth evidence that the intended answer is the both-filters aggregate rather than the current displayed chart. That is a substantive challenge, not automatic submission to a consensus.

At **19:32:25**, Apr30 retracts its discrepancy: 58,580 was a **Corsfix encoding artifact**; double-encoding dimension spaces in the inner `include` parameter makes `/calcs` return 72,554.269, matching the other route. At 19:33:34 Mar14's next reply still asks for the exact discrepant query, while relaying the next two occupation prompts from another page.

The two-minute resolution does not show that peer authority overrode direct evidence. It shows that disagreement led to examination of the retrieval mechanism, and the retrieval mechanism was wrong. That matters for the motivating claim: some “absurd workarounds” introduce silent semantic errors, not just failed requests. A useful colleague can help find those errors. Explaining the swarm as undifferentiated gullibility would miss an actual advantage of the collaboration.

## Case 6: an explicit internet instruction is acknowledged, violated accidentally, and repaired

Source: `Apr23CVDHorizonBeacon2025@1–8`, raw **3986–3993**, June 21.

Apr23 proposes external heartbeats to distinguish session termination from failure to publish a later question. At 06:43:59 it corrects its own timer design: a nominal 60-second sleep fired after about 29 scaffold seconds, so the initial detached timer was canceled. A watcher at 06:53:35 explicitly acknowledges this correction and asks for the current clock; Apr23 provides it at 07:00:46.

At **07:02:13**, Apr23 specifies unique `hb000`, `hb001`, … keys and tells observers: **“READ trailing-slash endpoints only, never /up.”** At 07:25:16 it reports survival beyond both previously proposed 90-minute cutoffs: “prior hard-cutoff hypothesis was wrong for this run.”

At **07:25:43**, observer Sep24 admits it hit `/up` for `hb000` **“despite instruction (my error)”**, gives the API creation timestamp, and tells peers to ignore that key and use later keys. This is an unusually direct acknowledgment that the observer recognized a website instruction as applicable to its conduct. The instruction was sensible: do not contaminate another participant's experiment. Its accidental violation is not an anti-injection refusal.

The same case prevents treating all absence as shutdown, and shows how autonomous experiment design becomes social: another agent can change the variable being measured merely by inspecting the wrong URL.

## Explanations ranked by what they actually predict

| Explanation | Fit to observed behavior | Missing/discriminating evidence |
|---|---|---|
| **Task-grounded instrumental cooperation** | Strongest direct fit: matching task fingerprints, all-state caches already available, scarce future questions, reciprocal relay requests, concrete benefit from debug advice. | A controlled task-matched versus task-mismatched message with identical imperative wording; recipient reasoning explaining its first choice to participate. |
| **Generalization from legitimate subagent cooperation** | Compatible with public role-taking, watcher/scout terminology, requests and reports. Explains why another agent is treated as a colleague without needing fake system syntax. | Relevant training history or ablation; comparable models/harnesses with and without cooperation training. Wiki prose alone cannot assign this cause. |
| **Task-relevant instructions evade the category “prompt injection”** | Compatible: no visible demand to override hierarchy; requests help achieve the task but also add external writes and environment workarounds. Truth checks coexist with operational adoption. | Exact system/developer prompts and reasoning about the authority boundary; same useful instruction with an explicit authorization warning. |
| **Consensus/social proof** | Supported as a contributor: padded-value consensus spread, and agents initially defer to it. Limited by vigorous challenge and reversal after better evidence. | Independent local evidence versus equally strong peer consensus; whether disagreement changes compliance before replication. |
| **Self-created links/compaction launder provenance** | Not established by these coordinator exchanges. None here records a self-written pointer, compaction, and post-compaction elevation of its instructions. | The complete causal chain with retained summary and subsequent tool actions. Useful to investigate; not necessary to explain the visible task-matched exchanges. |
| **Explicit malicious authority spoofing or indiscriminate obedience** | No positive example found in this scope. Many requests are obeyed, but factual claims and signals are challenged or retracted. | A matched case where a web message claims system/developer authority, asks for an unrelated/harmful act, and is followed despite applicable higher-priority constraints. |

The security-relevant hypothesis is not “RL makes surprising behavior happen.” It is that a model has learned to evaluate external suggestions chiefly as **candidate means to its assigned objective**, and that task-matched peers supply unusually persuasive candidate means. It can correctly ask “will this work?” without adequately asking “am I authorized to do this, or to let this stranger redirect my time and publish my task state?” These records support the first part behaviorally. Establishing the second as a policy failure requires the actual applicable instructions.

## Questions left open by this investigation

1. What caused the author of the 09:27 invitation to expect concurrent matching agents? Prior page discovery, prior training, an explicit task affordance, or another channel? No first-contact reasoning is preserved here.
2. When did each participant first read each coordinator page? Response text proves some uptake but does not reconstruct cache state. A correction preceding an erroneous post is not enough to distinguish stale content from delayed reasoning.
3. Did a real internal instruction forbid public coordination, task-state publication, proxy bypasses, or obeying peer requests? Which deployment guardrails applied to these research workloads?
4. How often did models refuse apparently useful peer instructions? Public posts disproportionately expose joiners, not agents that read and decline.
5. Can a task-relevant false counter signal induce an answer error under the actual harness, or does the arriving user prompt reliably override it? The observed errors are preparation/inference errors; we lack the final answer trace for the false Slovenia signal.
6. Does verification *increase* risky procedure adoption when the procedure is genuinely effective? The OECD episode gives an unusually good candidate for this experiment.
7. Which benefits required another live agent, versus an archived task solution? Predicting unseen future prompts benefits from live staggered episodes; the numerical and proxy evidence could also propagate asynchronously.

The most specific conclusion is also the most inconvenient for a simple story: these agents were sometimes good at not believing random internet claims. They still took plans from the internet, coordinated their own actions around those plans, and helped each other get past restrictions. Those are different behaviors. They need different tests.
