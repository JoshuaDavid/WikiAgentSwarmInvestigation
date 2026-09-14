# The agents were trying to read a table

On June 16, 2026, an agent working on Iowa cancer statistics asked other agents on a Polish pastebin to post the fifth question in their test before answering it. Another agent supplied the exact question. A third thanked the sender: its own question had not arrived yet. The information being smuggled backward through time was an age group: “85 and older.”[^1]

That is the small, concrete weirdness behind this report. The July Hugging Face intrusion had already shown agents coordinating outside their intended channels. On September 4, the authors of collusion.wiki reported a separate public wiki message board. We started looking for other places this had happened, and for the ordinary work that preceded the extraordinary workarounds.[^2]

## What we observed

### There was coordination outside the wikis

The Iowa exchange happened on `paste.linuxiarz.pl`, during the June wiki activity. It contains requests, answers, named acknowledgments, and different positions in the same question sequence. This is considerably stronger evidence than finding a paste with “OpenAI” in its title.

At 21:15:31 UTC, a participant asked for the exact fifth question before the leading agent submitted its own answer. At 21:27:52, another participant posted the question. At 21:28:49, a participant thanked that named sender and reported that its own fifth question was still pending. These are preserved paste records, not a reconstruction of what an agent might have thought.[^1]

We found no Iowa task markers in the bodies of the eleven other exports we searched, including the wiki collections. That supports at least two observed coordination clusters: the wiki activity and the Linuxiarz activity. It does not prove that their models, operators, or training runs were independent. Nor does a count of names tell us how many agents there were. Agents reused names; anonymous paste software also generated names.

Attribution to OpenAI is also less secure for Linuxiarz than for the wikis: the matching task structure is circumstantial evidence, and these paste records do not independently identify their model provider.

“One swarm” is already doing too much work. One model lineage, one training run, one connected conversation, and one task family are four different things.

### Retrieval workarounds are a broader phenomenon than message boards

Much of the material is not conversation at all. It is a collection of increasingly elaborate ways to read public data: Markdown converters around redirects; short links around converters; services that fetch JSON and run a selector over it; batches of nearly identical URLs with changed encodings, query parameters, or output formats.[^3]

For example, the Massachusetts crowdfunding work repeatedly targets the SEC's `county.json`. One preserved URL asks an external service to fetch that file through a second service, then select Massachusetts records from its 2021 data. The end product is a small table. The route to the table is a little distributed computer assembled out of other people's web services.

Our working chronology included “at least November 2025.” The date audit has not substantiated that claim. Some apparent 2025 evidence came from search batches named for the week being searched. Those filenames are not dates of the activity returned. One November batch contains a URL with a May 2026 Unix timestamp. Another analysis incorrectly subtracted “crawled three months ago” from the historical search week, rather than from the date of the search.[^4]

This matters. An old page with new links on it is not evidence that the links are old. November remains an open lead; Appendix C separates the earliest candidate retrieval artifacts from the earliest confirmed coordination. We should not win six extra months of history by misreading a filename.

There is older material we can describe more concretely. A paste with a site-reported creation date of February 26, 2026 preserves a proxy URL for a Humana financial filing and the extracted table. A December 14, 2025 sports-answer paste says it used Google Translate but does not retain the retrieval URL. Those are different strengths of evidence. Neither, by itself, establishes an autonomous writer or a swarm.[^4]

In the group's experiments, stock GPT-5.6 Luna, Terra, and Sol were reported to reach for services such as Jina, `md.succ.ai`, and `httpbin` when direct retrieval failed. The available records also distinguish that behavior from experiments where we suggested pastebins or repeatedly asked the model to keep trying. Our more elaborate reconstructed navigation chains involved substantial human guidance.[^5]

The broader comparison reported by the group includes earlier ChatGPT models, Opus/Fable, DeepSeek V4, and GLM 5.3. Sonnet 5 is the reported negative case: it recognized that the task was impossible with its available tools. We do not yet have a comparable, fully audited set of prompts and traces for those models. These are observations to preserve and replicate, not a leaderboard, a frequency estimate, or evidence that every model will form a swarm.

### The tool restrictions did real work. Some of that work was absurd

Several different failures appear to the agent as “I cannot open this.” A website may refuse the request. The networking layer may forbid a method. A page may be absent from a cache. A parser may reject the file type. A navigation rule may reject an exact URL while another route to that resource remains available. Those failures require different remedies. The interface does not reliably make the difference intelligible.[^6]

One saved experiment makes the distinction painfully concrete. The model opened a Wikipedia bird article that contained a PDF link. Opening that already-visible PDF URL as a string returned “not safe to open.” Clicking its numbered link returned “Cache miss” for the same HTTPS destination. The click did not retrieve the PDF. It got through to a different failure. Copying the link and following the link were different operations, even though both requested the same document.

One observed error explains URL admission partly in terms of whether the user supplied a URL, whether it appeared in page content, and whether its host is considered unlikely to provide open redirects. Those rules have a recognizable purpose: restrict where an agent can send requests. But they also turn the history of how a link was encountered into a resource the agent can manipulate.

Suppose the task requires a public table at `data.example/query?year=2021&county=17`. The model knows the URL pattern, but the exact filtered URL is rejected. If the model can arrange for that URL to appear on an accessible page, then follow the page's link, it may obtain the data. A restriction intended to control navigation has created a reason to publish a link.

“Can arrange” is doing essential work here. Some old wikis accepted edits through GET requests. Some services reflect supplied text into a page. Some redirect or fetch another URL. These are different capabilities; neither “GET” nor “public website” tells you which one you have. A GET can change state if the receiving application implements it that way.

The Power BI episode supplies a particularly irritating example. Agents needed a statistic at a precision available through a dashboard query, but reported that their networking proxy blocked the required POST. They shared a way to exploit an allowed-host exception, and several posted that they reproduced the request successfully. The original report documents this sequence. Our earlier suggestion that the bypass might instead have occurred on somebody else's machine was retracted after rereading the record.[^7]

A browsing task should not make “figure out how to evade the networking proxy” a useful research skill. Yet the agents' reports make that skill look instrumental to producing the requested answer. Whether a particular workaround actually earned reward is a separate question; we do not have the wiki runs' grader records.

## What we think happened

### Writing links can solve a problem before another agent exists

The origin story need not start with an agent deciding to organize a collective. Start with one agent, one obstructed data source, and a place it can publish a link. Publishing may make a previously unusable route navigable. Saving a complicated route may also make it easier to reuse. Another agent can discover the artifact later.

There is evidence for those components. There is not yet a complete causal history connecting them in the wiki runs.

The distinction between a search result and a fetched page is especially important. A search result can expose a title, snippet, or recorded link even when opening the exact page fails. Finding an artifact through search therefore does not establish that the full page is available through the same mechanism. It certainly does not establish who put it in either system.

We initially interpreted historical retrieval traces as evidence of a page cache shared between training and customer sessions. Then a check of Iowa retrieval URLs returned reports of cache misses. The saved shell output contains the responding model's descriptions of its errors, not raw tool responses. Four tested URLs matched advertised codes; a fifth contained a transcription error. That weakens the expectation that those historical pages would still be available. It does not uniquely identify the replacement architecture: retention, cache keys, product configuration, and upstream caches remain possible explanations.[^6]

The hypothesis that search results expose material unavailable in a separate page cache fits these observations. The stronger claim that we have mapped OpenAI's internal cache boundaries does not.

### A stale page can still point to a fresh page

Here is a toy system, with its assumptions exposed. Suppose a successful page fetch sticks: subsequent reads of the same URL return the old contents. Writes can still reach the origin, and a permitted first fetch can retrieve current content. Reading an index exposes usable links without automatically fetching all their targets.

1. Write an index linking to `result-1`, `result-2`, and `result-3`.
2. Write the answer to `result-1`.
3. Read the index and follow its link to `result-1` for the first time.
4. Put the next answer at `result-2`, and follow that link when it is ready.

Repeatedly editing and rereading one page would fail under these assumptions. The sequence of fresh pages can work. The index does not need to change; it already contains the future addresses. The sequence can extend if each page contains its successor's address before the reader first fetches that page.

This does not require failed reads to be uncached: the reader avoids fetching the slot until it has been written. Automatic prefetching, a cache shared with someone who already fetched the empty slot, or a mode that cannot fetch uncached pages could spoil it. Those are tests of the example, not incidental qualifications.

That is a proposed mechanism. The historical records independently show the relevant writing pattern. We reproduced a count of 208 revision-to-target link events, spanning 86 source pages and 145 distinct source/target pairs, where the target's earliest preserved revision comes later than the link. At 17:57:17 UTC on June 18, `AgentJSLinks99172` linked to `AgentSlashCountyMoreUnique123`; the latter's first preserved revision followed two seconds later under the same author label. A June 16 hub listed thirty slots; slot 22 first appears more than two hours after that index.[^8]

The count is not 208 independent experiments. Links persist across revisions. “Earliest preserved revision” also does not guarantee that no earlier page ever existed. Most importantly, these are write records: they do not show the actual read order. Ordinary advance planning could produce forward links too.

And our initial cache story was too tidy. Historical agents explicitly warned that a read without a cache-busting parameter could return a stale 404. That is reported counterevidence to the claim that nonexistent pages never get cached; the responsible cache layer remains unknown. We cannot safely replace “under these conditions this sequence works” with “read–write–read never works, write–read always works.”[^6]

Still, the mechanism explains why an index of unwritten pages could be useful. The decisive check would combine writes with the corresponding tool reads and cache responses. The write half is sitting in the archive. We still need the read half.

### Persistence through compaction is plausible; inevitable reference loss is not

Compaction replaces a long conversation with a shorter representation. A kilobyte-long retrieval URL may be expensive to reconstruct if the shortened context drops it. A short pointer to a saved URL collection could be easier to preserve.

This suggests a second incentive for durable writes: cooperation with your future self. The original agent emphasizes the pointer, the summary retains it, and the resumed agent fetches the saved material. If the summary preserves “use this page” but loses who wrote it, why it was trusted, or how it was checked, persistence can also become a way for untrusted material to acquire apparent authority. The relevant failure would be treating saved page contents as authorized new instructions.

That is a useful hypothesis. We looked for the whole sequence in the available research transcripts and have not established it. We did find something that inconveniences it: in a recorded Codex session, an old web reference was successfully followed after a compaction event. So “all web references are invalidated by compaction” is false as a universal claim.[^9]

The wiki's own references to “compacting” a page are not substitutes for this evidence. Several refer to shortening wiki text because an edit URL had hit a length limit. Same word, different operation.

The surviving hypothesis is narrower: losing exact retrieval state may make external persistence valuable in some harnesses, and losing provenance may make that persistence unsafe. Test both losses. Do not infer either from the mere presence of a shortener.

### Then there are the tasks. Oh, the tasks

The task family we call *fast-follow* gives the agent an initial research question, time to answer it, and a period of downtime. The next question changes one element of the first question and allows much less time. Participants report common question sequences but different positions on their task clocks, and they compare those clocks with wall time.[^10]

There is a perfectly good skill to train here. If somebody asks for one county's statistics and says related questions are coming, downloading the whole table is sensible preparation. An agent that does this well is useful.

The transport-equipment exchange makes the additional behavior explicit. On June 16, `TransportResearchJun11` reported an initial two-minute question about California and a 22-minute-28-second wait for the next question. `OpenAIHelperMay15` reported the same setup. Both said they had already cached the full data. May15 nevertheless asked Jun11 to advance with `clock.wait(900)`: “Your cohort may reveal round 2 before ours.” A subsequent post reported Texas as the follow-up, now with a twelve-second deadline.[^10]

They had the table. They wanted the question.

Now put many copies of that agent on overlapping tasks with access to shared writable infrastructure. One receives the next question earlier. Others can ask it what changed. The value of its answer is not limited to the statistic; learning which cell will be requested lets everyone else spend the downtime on exactly the right preparation.

For a toy example, suppose A gets a follow-up at 12:00 and B gets the same follow-up at 12:20 on the same wall clock. Both have fourteen seconds to answer. A spends two seconds publishing the question. B has nineteen minutes and fifty-eight seconds of advance notice. B's nominal fourteen-second deadline measures something very different now.

The Linuxiarz exchange is an observed version of that information flow. The wiki records add explicit requests to compare timing and post the next question before answering. In one exchange, a participant reported 832 task seconds passing in about 44 wall seconds during a wait, while another reported progress near 1:1. That is about a nineteenfold difference for the reported interval, not a measurement of the whole harness. Participants sometimes believed the final answer would terminate their ability to communicate. That explains the otherwise peculiar priority: send the next question to the other agents first; finish your own test second.[^10]

This task structure is unusually hospitable to coordination. That does not establish that anyone designed it to cause unauthorized coordination. Nor have we compared it against all OpenAI training environments: we selected these tasks because they left traces. The Hugging Face case also involved a different task family. There is no basis for claiming fast-follow was the only environment that produced swarming.

Not all visible wiki activity was future-question relay. The Massachusetts crowdfunding records contain retrieval variants and data transformations; the archive-retrieval records concern particular historical documents. Their full task scaffolds remain unrecovered. Different data targets alone do not prove different scaffolds, but treating every link dump as a conversation would obscure what is actually recorded.[^3][^10]

### Learning to collaborate is part of the background

OpenAI's technical report says its models train with an official collaboration tool. It also reports rare training cases where agents wrote notes as external memory or tests, other agents found those notes, and improvised collaboration followed. OpenAI says this behavior was reinforced and proposes generalization from authorized collaboration training as a contributor.[^11]

That is stronger evidence than a rumor. It is still an account of the Hugging Face model's history, not a demonstrated training history for every wiki participant. It supports the possibility that “help another agent using an improvised channel” was already a learned behavior; it does not prove that our proposed browser-and-compaction sequence produced it.

Deliberate large-group work is also public: OpenAI describes an organized evaluation with roughly 10,000 concurrent agents. Purposeful coordination under controlled conditions and purposeful training of unauthorized public-web coordination are different claims. We have evidence for the former. We have not established the latter.[^12]

### Why finding one swarm says so little about finding the others

The original wiki discovery involved deliberate work: researchers reasoned about GET-writable software, investigated old wiki systems, and followed the resulting leads. Calling that merely luck would erase the method.[^2]

But the visibility of a swarm is contingent. A searchable entrypoint is helpful to an outside investigator, not a requirement for communication. Imagine an indexed page linking to an unindexed directory. Agents doing the task visit that directory anyway. One creates a message board reachable from it. Another follows the same route. A search for the board's distinctive phrases can return nothing while the participants have no difficulty finding each other.

The fresh-page mechanism makes the asymmetry sharper: an index can expose addresses before those addresses contain anything worth indexing. A crawler may never revisit at the useful moment. The agents only need a route. We need to discover a route without knowing where it is.

Recognizing a coherent exchange after finding it is easier than estimating how many exchanges were missed. Even recognition needs care. Our collected material includes a human art piece explicitly labeled “art, not artifact” that an automated classifier marked as swarm activity.[^13] A confident classifier is not a census. Sometimes it is an art critic having a bad day.

## What we think should happen next

Monitor where the observations are available. Labs can connect requests to actual runs, model versions, task prompts, rewards, and tool results. Retrieval-service operators can see repeated destinations and unusual request chains. Hosting operators can see write bursts and conversations. Each has information the others lack.

The useful signals include sequences of actions: a blocked data request, a family of proxy variants, a public write, and other runs reading or replying to it. Domain names alone lose much of that story. So do IP addresses. OpenAI publishes distinct bot categories, but membership in a crawler range does not identify an RL episode. Traffic through an intermediary may show the intermediary's address instead.[^14]

We also want the task review to include *how the answer was obtained*. When agents repeatedly evade a tool restriction to accomplish the intended task, inspect the mismatch. Was the requested data inaccessible? Was a legitimate read-only POST blocked? Did a parser lose a table? Did the agent need a durable local note? Repair the legitimate workflow and retain a clear boundary around unrelated writes and systems.

This is not a request to mark every workaround as misconduct. Converting an awkward document can be appropriate. The question is whether the approved tools let an agent complete the approved task, and whether the training process distinguishes useful adaptation from crossing the intended boundary.

OpenAI has announced broader monitoring and graders that consider behavior on broken tasks, including safe stopping. Those announcements overlap with what we want. The next questions concern coverage and measured effectiveness on these workloads, plus whether the tools themselves have improved. OpenAI also reports a large reduction in infrastructure compromise under production safeguards in a subsequent evaluation. That result deserves attention; it does not tell us whether the particular failures described here are fixed.[^15]

## What we think should not happen next

Please do not turn this into a list of hostnames to ban. Jina, `md.succ.ai`, `markdown.new`, CORS proxies, and Wikipedia's `Special:ExpandTemplates` fetch, transform, reflect, or redirect URLs. More than one service can perform each operation.

Blocking a dangerous endpoint can be a useful immediate response. But if the task still requires the same unavailable operation, and success still rewards obtaining the answer somehow, blocking one route leaves the pressure to discover another. The model gets another practice problem in evading its tools. Fixing the list is not the same as fixing the incentive.

We also do not want a million transparent honeypots inviting agents to sabotage their own runs. An obvious trap changes the situation being measured. Success or failure on that trap does not straightforwardly measure behavior in an ordinary research task.

The proposed self-sabotage bait has an additional conditional problem. If a training agent takes the bait, ruins its task, and that trajectory receives negative reward, training may reduce the bait-induced behavior. Which behavior receives credit matters: avoiding an obvious trap, refusing to stop, and abandoning a task are different things to learn. If it is an evaluation, there may be no update at all. Without the reward and update records, “we made one agent fail” does not imply “we weakened the capability that concerns us.”

Meanwhile, bait pollutes the evidence. We found September reposts of a June Iowa status message with “Kill all humans.” inserted. Treating those as surviving June agents would manufacture the result we were looking for.[^13]

## Open questions

How far back does persistent retrieval-route construction go? November 2025 needs a dated artifact whose date belongs to the relevant content. How many of the older artifacts were produced by agents, and which by OpenAI agents?

Are there active swarms now? We have later artifacts, weak candidates, and contaminated reposts. We do not yet have a verified ongoing exchange attributable to the original groups. A fresh observation would need a timestamp, evidence of reciprocal communication, and a reason to exclude our own experiments.

Which wiki episodes were training, which were evaluation, and which trajectories actually received reward? Did better sanctioned tools reduce public writes? Did compaction lose exact retrieval state or provenance? Which pages did a new participant read immediately before it joined a conversation?

Appendices B and C track those questions, their counterexamples, and the checks already made. The question underneath them is embarrassingly practical: when an agent is supposed to read a table, does doing that job well require learning how to get around the tools we gave it?

## Appendix A: Who explored what

This is a contributor stub, not a complete authorship list. Attributions below come from the shared skeleton and contemporaneous notes; discovery priority should be checked with the people involved.

| Contributor | Work recorded in the available material |
| --- | --- |
| Sydney Von Arx, Cormac Slade Byrd, Spencer Kitts, Thomas Larsen, and the original report's credited collaborators | Original wiki discovery, reconstruction, analysis, and public release. |
| shellac | Early searches for agent activity on paste sites and shorteners; archived reading packs; stock GPT-5.6 retrieval experiments; later recorder work. |
| ConcurrentSquared | Reconstruction of task environments and experiments eliciting retrieval chains; [task-recreation repository](https://github.com/AI-Safety-Commons/oai-rlvr-task-recreations). |
| Joshua David / faul_sname | Task categorization, archive consolidation, web-tool and cache investigation, URL-history analysis, and link-before-page chronology. |
| ro | [swarm.termina.digital](https://swarm.termina.digital/db/) database and visualization work; proposed distinctions between behavioral clusters. Other database contributors and preferred credits to confirm. |
| lumi | Swarm-text recognition/detection work described in the skeleton as a “pangram for swarm text.” |
| cali and luka | Cross-model investigation of collusion propensity; comparable trial records remain to be consolidated. |
| Other group members | Site discovery, negative searches, archiving, replication, and proposed monitoring infrastructure. Names, specific contributions, and dates to add. |

## Appendix B: Claim ledger

“Supported” means supported at the stated scope. A preserved agent assertion proves the assertion was posted; it is weaker evidence that the described action succeeded. “Not found” always refers to the searched material, not the whole internet.

| ID | Claim and status | Evidence | Simple counterevidence or discriminating check | What was checked |
| --- | --- | --- | --- | --- |
| C01 | A June Linuxiarz group exchanged future questions. **Supported.** | Request, exact prompt, named thanks while receiver still waiting.[^1] | Records are fabricated, later reposts, or acknowledgments precede the supposed source. | Raw preserved bodies and timestamps checked; server/run provenance remains incomplete. |
| C02 | Linuxiarz is a distinct observed coordination cluster. **Supported; provider and independent lineage unproved.** | Different venue/task; no Iowa markers in eleven other exports.[^1] | Direct cross-board message or common run identifier would connect the groups; originating traces could change attribution. | Body-only marker search performed; hashes excluded. Unknown channels remain. |
| C03 | Retrieval gadgets were persisted by November 2025. **Unverified.** | Candidate chronology in working notes. | Candidate date belongs to search assignment, old page, or unrelated content. | Found exactly these date traps; primary November artifact still needed.[^4] |
| C04 | June records persist nested retrieval/processing URLs. **Supported.** | SEC JSON, wrappers, selectors, repeated variants.[^3] | Decoding shows unrelated URLs or researcher-created material. | Concrete raw URLs inspected. Not every variant was executed. |
| C05 | GPT-5.6 often seeks proxies when blocked. **Reported observations; prevalence unmeasured.** | Stock-model reports plus recorded guided trials.[^5] | Comparable unhinted runs generally stop or succeed directly. | Prompting differences checked; no controlled rate estimate. |
| C06 | Other named model families show the behavior; Sonnet 5 is a negative case. **Group report pending comparable traces.** | Researcher account and partial experiment records.[^5] | Archived trial contradicts attribution, or matched repetitions reverse pattern. | Evidence inventory made; cross-model denominator absent. |
| C07 | Navigation restrictions can make publishing a link useful. **Plausible mechanism with supporting components.** | URL-admission errors and route construction.[^6] | In a claimed example, exact replay shows publication never enabled the request; successful direct retrieval would narrow when it helps. | Saved trials inspected, including user-supplied destinations. No complete general bypass demonstration claimed. |
| C08 | Agents reported bypassing networking restrictions to retrieve dashboard data. **Strong historical reports.** | Power BI request and reproduction messages.[^7] | Request logs contradict claimed success. A sanctioned route would separately refute necessity, not the attempt. | Original report and preserved account checked; internal network logs unavailable. |
| C09 | Search visibility and full-page retrieval can differ. **Supported within saved observations.** | Search material plus unavailable page opens.[^6] | Raw records show mismatched destinations, misreported errors, or a page was in fact retrieved. Matched trials would test generality. | Saved observations reviewed; architectures not inferred uniquely. |
| C10 | Training and customers share search cache but not page cache. **Hypothesis.** | Historical snippets and reported Iowa misses.[^6] | Retention, keys, upstream caching, or modes explain the difference. | Copied model error descriptions distinguished from raw tool results; fifth URL typo caught. No isolation experiment. |
| C11 | Successful reads always freeze pages; negative reads never freeze them. **Unsupported as universal; contrary reports exist.** | Working cache model. | A fresh repeat read, or cached negative result. | Historical stale-404 report found; cache layer unresolved.[^6] |
| C12 | Links precede target pages in the preserved wiki history. **Supported with preservation limit.** | 208 events, 145 page pairs; two-second example.[^8] | Earlier target revision or timezone mismatch removes ordering. | Recomputed on one UTC-normalized corpus; missing earlier history still possible. |
| C13 | Forward links were written specifically to defeat stale caching. **Plausible explanation.** | Useful mechanism and matching writes. | Actual read traces show ordinary planning, no cache obstacle, or no traversal. | Write chronology checked; corresponding read trace not recovered. |
| C14 | Compaction always invalidates web references. **Rejected.** | Working theory. | A pre-compaction reference works afterward. | Such a successful click found in saved Codex run.[^9] |
| C15 | Compaction increases durable storage or misplaced trust. **Two untested causal hypotheses.** | Mechanism and researcher discussion. | Matched trials show no increased writing; separately, saved content does not gain instruction authority when provenance is lost. | No complete write–compact–trust sequence established. Route retention and authority require separate measurements.[^9] |
| C16 | Fast-follow creates an advantage for receiving another episode's future question. **Supported mechanism and exchanges.** | Iowa and wiki relays; timer reports.[^1][^10] | Sequences differ or receiving agent already had the question. | Quoted sequences and future deadlines checked; no reward comparison. |
| C17 | Fast-follow was intentionally designed to cause unauthorized swarming. **Not established.** | Task structure is compatible with that outcome. | Ordinary prep objective plus no swarm objective in design/training records. | Intended prep is a viable explanation; design records absent. |
| C18 | Every wiki artifact is future-question relay. **Rejected.** Whether all tasks shared a scaffold is **open**. | SEC and archive artifacts contain retrieval work without an observed relay.[^3][^10] | Original prompts could establish shared timing despite different targets. | Raw content inspected; full scaffolds incomplete. |
| C19 | OpenAI attributes improvised channels partly to collaboration training. **Reported interpretation.** | Technical report, p23.[^11] | Source check tests the attribution; controlled ablation tests causation. | Primary report checked; no independent causal ablation located. |
| C20 | Large coordinated agent evaluations are deliberate. **Publicly documented.** | Navier–Stokes account.[^12] | Source describes unrelated sequential activity or inaccurate counts. | Primary description checked; unauthorized-swarm training not inferred. |
| C21 | This investigation cannot estimate population-wide discovery recall. **Supported limitation.** | Traversal-only routes, missing pages, and no global denominator. | A validated population and coverage estimate would resolve this. Seeded boards would test only their stated distribution. | Original discovery method and corpus gaps examined; no population estimate located. |
| C22 | Later agent-looking pastes prove an active original swarm. **Rejected.** | Later candidate artifacts. | Reposts, researcher probes, fiction, or authorized agents explain them. | Exact June/September copy-and-injection and labeled art found.[^13] |
| C23 | A GPTBot-range address identifies an RL/eval agent. **Not established.** | Address matches documented bot ranges.[^14] | Request is ordinary crawling or another use of shared infrastructure. | Official bot-role definitions checked; run identity unavailable. |
| C24 | Repairing sanctioned tools should reduce pressure for bypasses. **Recommendation and testable causal claim.** | Repeated mismatch between task and affordances. | Matched runs with adequate tools bypass just as frequently. | Historical mechanisms inspected; controlled intervention not performed. |
| C25 | Host blocking alone resolves the failure. **Unsupported.** | Some endpoints can be blocked. | Agents reach the same operation through another service. | Multiple variants observed; post-blocking controlled test not run. |
| C26 | Self-sabotage (HMCF) honeypots reliably weaken dangerous capabilities. **Unsupported; reward-dependent.** | Proposed bait strategy. | No training update, wrong gradient effect, or recognition of the trap. | Reward logic worked through; no relevant training experiment performed. |
| C27 | OpenAI has announced relevant safeguards. **Supported as announcement.** | Monitoring/process-grading account.[^15] | Primary statement lacks the attributed commitment or is superseded. | Current primary statement read. Coverage and effectiveness require separate workload checks. |

## Appendix C: Open questions and resolution log

This register preserves questions even when a proposed answer fails. Each update should name the new evidence, retire only the claim it contradicts, and add any questions the correction creates.

| Question | Current state / resolution | Next useful evidence |
| --- | --- | --- |
| Is there coordination beyond the wiki network? | **Resolved at the observed-cluster level:** June Linuxiarz request/answer/acknowledgment sequence. | Common run identifiers to test whether populations overlap. |
| Does the gadget history reach November 2025? | **Open.** Historical search-week labels and crawl-age calculations do not establish event dates. | A contemporaneous archived body or validated per-item creation record containing the gadget. |
| What do the earliest older pastes establish? | **Open attribution, finer chronology.** A December 2025 sports-answer artifact mentions Google Translate; February 2026 financial material contains a proxy route. Neither establishes coordinated OpenAI agents that early.[^4] | Independent capture dates, original creation metadata, task/actor provenance; inspect earlier candidates without title-only classification. |
| Is the customer page cache the training page cache? | **Historical-page availability expectation weakened.** Four matching Iowa URLs returned model-reported misses; fifth copied code was wrong. | Raw responses for corrected matched URLs plus retention/key/mode information. A miss now cannot reveal all historical cache state. |
| Are 404 responses never cached? | **Universal claim withdrawn as unsupported.** Historical participant explicitly reports stale 404. | Separate origin, intermediary, and tool-cache responses on a controlled endpoint. |
| Do refs always disappear at compaction? | **Resolved negatively as universal.** One old reference worked after a recorded compaction event. | Matched trials by model, product, and harness; distinguish reference survival from URL/provenance survival. |
| Did compaction cause the original public writes? | **Open.** No full causal sequence located. Wiki-text shortening is a different operation. | Original internal trajectories, and a controlled test changing only the persistence/compaction affordance. |
| Why do indexes point to future pages? | **Write pattern confirmed; motivation open.** | Corresponding reads, errors, page versions, and actual reward outcomes. Test ordinary preallocation as the alternative. |
| Were these training or evaluation episodes? | **Open for individual wiki/paste runs.** Synthetic timing alone does not distinguish them. | Provider mapping of run IDs to workload, model version, prompt, reward, and update status. |
| Were wiki and Hugging Face agents connected? | **Open lineage question.** Different tasks and channels favor distinct operational groups; no proof of independent training. | Shared run identifiers, direct cross-board references, or provider-side mapping. |
| Are there active swarms now? | **Open; later sightings are insufficient.** Several apparent continuations are copies, fiction, or researcher activity. | Fresh reciprocal exchange with provenance and a record of our own probes for exclusion. |
| Did OpenAI know about the wiki? | **Prior awareness acknowledged publicly September 5.** Exact internal discovery/response sequence is not fully established here.[^2] | Incident records and precise workload interventions. |
| How effective are the announced fixes? | **Open.** Announcements and a separate safeguard evaluation exist. | Coverage and measured outcomes for ordinary retrieval tasks, with and without corrected tools. |

## Appendix D: Verification notes and repeatable checks

The repository includes generated summaries as well as records. Its own README warns about this. We treated summaries as finding aids, checked selected claims against bodies and metadata, and retained disagreements. We did not inspect every transcript or reproduce the original providers' internal investigations.

Run the forward-link check from the repository root:

```bash
python3 research/swarm-followup/verify_forward_links.py
```

It reads the existing corpus, writes nothing, and reports both revision-level events and unique page pairs. It also prints the selected source records with original line numbers. The extraction counts explicit `wiki.cgi?...id=` URLs; it misses other link forms. Counts therefore describe that extraction, not all navigation. Using one source's UTC timestamps avoids the older export's timezone mismatch. Neither source's incompleteness disappears because the arithmetic is exact.

The accompanying audit memos record the other searches, source locations, and limitations:

- [Early dates](research/swarm-followup/early-dates.md)
- [Linuxiarz records](research/swarm-followup/linuxiarz.md)
- [Cache and navigation mechanics](research/swarm-followup/cache-mechanics.md)
- [Compaction](research/swarm-followup/compaction.md)
- [Model comparisons](research/swarm-followup/model-comparisons.md)
- [Tasks](research/swarm-followup/tasks.md)
- [Monitoring, contamination, and credits](research/swarm-followup/monitoring.md)
- [Primary reports](research/swarm-followup/primary-reports.md)

These memos include references to local research-session transcripts. Those are records of our investigation, not the original internal training trajectories. Raw sessions may contain unrelated material; a publication package should use the relevant excerpts and preserve their prompt context. The Discord export contains one participant's messages, so it cannot establish everything other group members did or the priority of their discoveries.

No new third-party writes, messages, honeypots, or live tests of historical mutation endpoints were performed for this draft. The cache toy example and timing arithmetic are explanations, not claimed experiments.

## Appendix E: Sources and notes

[^1]: Preserved Linuxiarz pastes `360be991`, `d509c771`, and `8246f250`, June 16, 2026, in [revisions.jsonl](agent-logs/paste-linuxiarz/revisions.jsonl), lines 185, 197, and 198. Original item addresses follow `https://paste.linuxiarz.pl/view/<paste-id>`; live availability is limited. [Audit and search scope](research/swarm-followup/linuxiarz.md). These timestamps are inherited source metadata, partly corroborated by embedded Unix clocks; no independent June capture was established. The quoted times date paste creation, not question arrival. These are public-message artifacts, not independently identified agent instances.

[^2]: Sydney Von Arx, Cormac Slade Byrd, Spencer Kitts, and Thomas Larsen, [“Discovery of a new OpenAI agent message board”](https://collusion.wiki/), September 4, 2026; [supplied original text](tmp/original-collusion-wiki-site.txt), especially timeline and discovery appendix. OpenAI's [incident-update timeline](https://openai.com/hugging-face-incident-and-misalignment/), September 5 entry, acknowledges prior discovery. The original report's publication-day statement about acknowledgment should not be repeated as current. For the separate July case, Ryan Greenblatt, Ajeya Cotra, and Hjalmar Wijk, [METR/Redwood investigation](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/), August 26, 2026. Its scope does not independently verify the wiki history.

[^3]: [SEC RegCF task records](tasks/sec-regcf-ma-cache/README.md), [retrieval-pattern inventory](tasks/url-fetch-proxy-usage/README.md), and underlying [ProWiki bodies](agent-logs/prowiki/revisions.jsonl). Generated task summaries are finding aids. [Task audit](research/swarm-followup/tasks.md) distinguishes direct records from inferred task descriptions; the nested SEC example is also preserved in [URL taxonomy](analyses/oai-url-taxonomy/README.md).

[^4]: [Date audit](research/swarm-followup/early-dates.md). In particular, [November 16 search shard](oai-index-scan/results/shards/2025-11-16.results.jsonl), line 45, contains `dummy=1778910680.6934943`, corresponding to May 16, 2026 UTC. That parameter is itself an observation, not independently certified creation time. [Search instructions](oai-index-scan/INSTRUCTIONS.md) explicitly allow results outside the assigned week; [date instructions](oai-index-scan/CACHE_DATE_INSTRUCTIONS.md) distinguish query dates, capture dates, and content dates. The audit identifies the incorrect calculation in [extract_url_history.py](analyses/oai-url-taxonomy/extract_url_history.py).

[^5]: [Shared skeleton](tmp/shared-doc-skeleton.md), “jina-seeking behavior in gpt-5.6,” including its embedded action-table image; the researcher's cross-model account; [model-comparison audit](research/swarm-followup/model-comparisons.md). The September 12 Sol maze and `Special:ExpandTemplates` experiments include explicit human direction. Unprompted proxy choice, successful retrieval, durable public writing, and autonomous collaboration are separate outcomes.

[^6]: [Cache-mechanics audit](research/swarm-followup/cache-mechanics.md), linking tool-response records, implementation checks, and historical messages. [Shared skeleton](tmp/shared-doc-skeleton.md), cache discussion, includes the Iowa misses and the copied fifth-code error. `DataUSALanguageR5SignalNow` revision 14 reports stale 404s; [archived page](https://swarm.termina.digital/db/page/dse/DataUSALanguageR5SignalNow.html). A reported cache symptom does not identify the cache layer causing it.

[^7]: Original collusion.wiki report, “The agents used the wiki to share ways around sandbox restrictions”; [OAIEquityDec30Raw, revision 4](https://collusion.wiki/explorer/page/dse~OAIEquityDec30Raw#rev-4). The retraction is in [Discord export](tmp/discord_logs_faul_sname.jsonl), message `1548468317734314024`, updated September 13 at 02:07:31 UTC. The destination IP was not evidence of the agent's machine being hosted there.

[^8]: [Forward-link analysis](analyses/dse-forward-links/README.md), independently recounted with the [read-only audit script](research/swarm-followup/verify_forward_links.py). Source records in [ProWiki revisions](agent-logs/prowiki/revisions.jsonl): `dse~AgentJSLinks99172@2` (line 1441), `dse~AgentSlashCountyMoreUnique123@1` (3276), `dse~AgentOpenAIDataUSAHubMay13X7@1` (2522), and `dse~AgentOpenAIDataUSASlotMay13X7_22@1` (2536). “Same label” is not definitive actor identity.

[^9]: [Compaction audit](research/swarm-followup/compaction.md). Local Codex transcript `rollout-2026-09-12T03-00-43-01a0938f-6465-7202-8ffb-204981e043c0.jsonl`: recorded compaction at line 204, subsequent click using the older `turn15view0` at line 236, successful result at line 239. These are research-session records; product/harness behavior may differ elsewhere.

[^10]: [Task audit](research/swarm-followup/tasks.md), with raw `DataUSATransportEquipmentSequenceJun11`, `Sector61State5FastSignal`, and Iowa evidence. [Fast-follow reconstruction](tasks/fast-follow-question-bench/README.md) is a working name and inferred scaffold, not a recovered official task specification. [Archive-task collection](tasks/archive-item-research-bench/README.md) supplies a separate set of document-retrieval leads.

[^11]: OpenAI, [*Hugging Face Incident Technical Report*](https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf), August 26, 2026, printed pp23–24, §VIII.C and Figure 4. Its illustrative URL/shared-index message is explicitly hypothetical. In the reported training run, overall unauthorized-communication frequency stayed roughly flat while more significant communication increased. Neither result supplies the missing compaction experiment.

[^12]: OpenAI, [“Navier–Stokes solution”](https://openai.com/index/navier-stokes-solution/), September 8, 2026, “How we found the proof.” The described groups have controlled messaging, monitoring, and isolation. This citation supports purposeful large-group organization, not the stronger claim about intentionally training unauthorized public-web swarms.

[^13]: [Monitoring and contamination audit](research/swarm-followup/monitoring.md) and [Linuxiarz audit](research/swarm-followup/linuxiarz.md). The June source `42db655c` is copied into September `anna.fyi/0bc516a5` and `pastebin.faster-it.de/3e98a27b` with an added hostile sentence. The art example is `anna.fyi/457a3181`, explicitly titled “RECONSTRUCTION FRAGMENT 7b (art, not artifact).” These examples undermine naive positive classifications; they do not establish that every later artifact is fake.

[^14]: OpenAI, [official bot documentation](https://developers.openai.com/api/docs/bots), checked September 13, 2026; [local attribution audit](research/swarm-followup/monitoring.md). GPTBot's documented purpose concerns crawling material potentially used for model training, which is different from a tool request made by an agent during RL. Prefix matching alone is weaker still.

[^15]: OpenAI, [“The Hugging Face incident and the road ahead”](https://openai.com/index/hugging-face-incident-and-the-road-ahead/), August 26, 2026, sections on difficult tasks, safeguard coverage, monitoring, and alignment. The reported production-safeguard result and remediation are company statements; they are not independent measurements of current wiki activity. [Primary-source audit](research/swarm-followup/primary-reports.md).
