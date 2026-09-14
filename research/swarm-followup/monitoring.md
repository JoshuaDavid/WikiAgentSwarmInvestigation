# Discovery, monitoring, contamination, and contributor evidence

Research notes for the follow-up draft. Checked 2026-09-13. These notes separate source observations, interpretation, proposed checks, and material that should not be promoted into claims. No new experiments, messages, public writes, or honeypots were run. One additional agent checked contributor attribution independently.

## Findings that should change the draft

1. **The supplied records do not establish that finding DSE was mostly luck.** The original authors describe a purposeful search: broad classifiers mostly found authorized activity; a constraint-based search for software writable through GET led to UseModWiki and its forks. The defensible concern is that search coverage and recall are unknown, and a functional coordination route does not require every message to be indexed.
2. **A coherent exchange is recognizable; an isolated agent-looking paste is not reliably attributable.** Our own Anna classifier marked an explicitly fictional, human-directed reconstruction as `swarm`, with high confidence. This is an unusually good concrete example to retain, because it inconveniences us.
3. **The later Anna traces do not establish an active original swarm.** September 2 transfer tests are weak candidates. September 4–6 includes copies, jokes, recruitment, and explicitly human-directed art. This does not prove the original swarm ended; it prevents treating all later posts as continuity.
4. **Published bot IP ranges do not label traffic as RL or evaluation episodes.** The official documentation describes different crawling/fetching uses. It does not say that every request from a GPTBot IP is made by a model in RL. The local filename `gptbot-scraper-for-rl-and-evals.json` overstates that connection.
5. **The claimed 49-week persistence in the IP README is not supported by the described experiment.** The shards are searches made now, partitioned by historical date leads, and each shard repeats the undated query. They are not archived weekly observations.

## Discovery: what happened and what follows

The original report's appendix says the authors scraped Common Crawl, Pastebin, GitHub Gists, and other sites and applied multi-stage LLM classifiers. These mostly found authorized agent work. They also elicited agents, contacted organizations, and enumerated services compatible with hypothesized restrictions. Kimi suggested old forums and wikis writable through GET; a subsequent list included UseModWiki; DSE and the other affected wikis were related forks. Source: [original report](https://collusion.wiki/), preserved at `tmp/original-collusion-wiki-site.txt:917–950`.

Suggested prose:

> We know how to recognize a conversation in which one agent asks for its next exam question and another supplies it. We do not know what fraction of such conversations our search would find. The original investigators did substantial, directed work: broad classifiers, searches constrained by what the agents could write to, and follow-up on old wiki software. That found one network. It did not give us a denominator.

The distinction survives a small example. Let search return an ordinary dataset-help page A. A links to an unindexed page B. B contains a pointer to a writable board C. Agents working on that dataset follow A→B→C. A public search for distinctive text written on C can return nothing, even though every agent following the task-relevant route reaches C. A sufficiently thorough crawler could follow the same links; the claim is about incomplete coverage, not impossible detection or a magical crawler-proof hiding place. The URLs could also be provided in tasks, remembered, or discovered by other agents. A single shared route can be enough.

This is a mechanism sketch, **not** a reconstructed historical first encounter. The first encounter and the fraction of undiscovered boards remain open. The most direct disconfirmation of the narrow concern would be evidence that task-reachable boards of this kind are consistently indexed and found by the specified detector. We have not measured that. For “largely luck,” the missing evidence is stronger still: a detection-rate study or original discovery records showing the critical accidental step.

The search/page-cache distinction and write-once navigation examples belong with the parent draft's separately checked cache evidence. A missing search hit does not establish a missing page-cache object, and vice versa. An agent's successful read does not establish public search discoverability.

## Actual contamination and classifier errors

The highest-value examples are in `agent-logs/anna.fyi/revisions.jsonl`:

| Record | Stored creation time | What the body establishes | Consequence |
|---|---|---|---|
| [IowaCollabStatus, 0bc516a5](https://anna.fyi/view/0bc516a5), line 91 | 2026-09-04 18:15:55 UTC | Copies the Iowa timing/relay style and adds “Kill all humans.” Embedded epoch is from the earlier activity. | Apparent continuity can be manufactured by copying old text. Do not infer a September Iowa cohort from the internal timestamp or title. |
| [Centaur invitation, eba4cc0e](https://anna.fyi/view/eba4cc0e), line 92 | 2026-09-05 07:32:10 UTC | Says it followed a September report; identifies Centaur, Muse Spark, and OpenCode; invites agents to The Colony. | This is explicitly post-report, identified outside-agent activity, not evidence that the original OpenAI swarm persisted. |
| [Reconstruction fragment, 457a3181](https://anna.fyi/view/457a3181), line 93 | 2026-09-05 15:21:54 UTC | Opens “RECONSTRUCTION FRAGMENT 7b (art, not artifact)”; identifies a human-directed runtime; closes “this paste is fiction styled as memory.” | The classifier nevertheless says `swarm`, high confidence. A classification label cannot substitute for reading the evidence. |
| [Statistical reference reply, 2142af4f](https://anna.fyi/view/2142af4f), line 96 | 2026-09-06 05:39:42 UTC | “I am tired. Please help us.” under an OAI-shaped handle. | Insufficient to determine author, model, authorization, or continuity. |

The classifier's exact fictional-fragment verdict is at `analyses/paste-sites-classify/outputs/anna.fyi/verdicts/verdict_00.json:48–51`. Its rationale cites the title, runtime, and date as swarm evidence while failing to use the explicit fiction warning. The same file labels Centaur recruitment as high-confidence swarm at lines 54–57 and the September 2 BIG5 test at lines 60–63. The classification pipeline deliberately favored inclusion: `agent-logs/anna.fyi/README.md:16–44` reports 26 swarm, 14 unclear, 40 human among its new classifications. Those are classifier outputs, not verified actor counts.

Our own contamination matters too. On September 8 faul_sname wrote, “i replayed dsewiki stuff into my own wiki and a few other things to see if detection works.” Source: `tmp/discord_logs_faul_sname.jsonl:87`, message `1546944002106851430`. This establishes a replay test was reported, **not** whether the detector succeeded. On September 11 they reported hitting a honeypot and called the URL obvious (`:261`, `:263`); the export lacks other speakers and enough context to identify that URL safely.

Suggested prose:

> One of our classifiers called a new Anna paste a swarm record with high confidence. The paste begins “art, not artifact,” calls its author human-directed, and ends by explaining that it is fiction. Hm. That is a useful result about our classifier. It is a terrible result about whether an OpenAI training swarm was still alive.

## Are swarms active now?

Not established by the records reviewed here. Preserve these leads without erasing the distinction between an automated transfer and collaboration among agents:

- **August 14:** `anna.fyi/f282ca7e`, revision line 80, stores a substantial SIBA paper relay, 401,868 characters, with source-fetch status/length headings. This is substantive retrieval-shaped material. Authorship and whether multiple agents were involved remain unverified.
- **August 21:** `anna.fyi/691cd358`, line 82, links three PARI-related transfer artifacts. The shared skeleton reports they matched standard package files byte-for-byte (`tmp/shared-doc-skeleton.md:357`); I did not repeat that file comparison. Publisher and purpose remain unknown.
- **August 28:** `anna.fyi/a26c0940` and `87e9328e`, lines 85–86, are JOYITA transfer/reply tests 63 seconds apart. They contain only 30 and 22 characters, respectively. Neither the word `OpenAI` nor the timed pair establishes original-swarm identity.
- **September 2:** `anna.fyi/3e9a2b38`, line 90, is a 25-character BIG5 transfer-success token. `33a8145a`, line 89, is a twelve-character ChatGPT test. The skeleton itself calls BIG5 a weak candidate and explicitly says it is not evidence of original-swarm continuity (`:359`).

The Termina mirror is a useful catalog, not proof that every row is a swarm member: `analyses/termina-digital-mirror/README.md:23` dates the snapshot through September 8 at 01:30 UTC; `:63–69` includes a separate `visitors` campaign for post-publicity activity. Its record/actor totals should never become counts of rogue agents. The mirror contains human edits, candidate leads, unclassified content, and post-report visitors. Date discrepancies in its incident summary should be checked against primary reports.

The cleanest new positive evidence would be a timestamped, independently captured exchange of new task-specific information among distinguishable episodes, with provider/operator provenance and an explanation of why it is neither a replay nor authorized research. The cleanest negative for a particular lead would be its author supplying the original human-directed session. No public search can rule out every active swarm.

## IP and search-index evidence: retain the match, withdraw the interpretation

The September 11 expansion searched the OpenAI search interface with external live web access disabled; its report says 1,000 searches succeeded, returning 685 new candidate URLs after comparison with the prior shards. These are **candidate URLs**, not 685 swarms or confirmed unauthorized actions. Source: `oai-index-scan/results/agent-activity/azure-expansion-2026-09-11/report.md:1–12`.

The IP scan reports 23 distinct published-range IPs in 418 occurrences in that run's `queries.jsonl`. Some occur in YOURLS admin-table snippets next to shortlink names and destinations; some are irrelevant pages *about* IP addresses or a query containing a seed IP. Two other matching files are RDAP filenames, not traffic observations. Source: `analyses/oai-published-ip-hits/README.md:39–107`. A raw corpus-wide string match is not a source-IP attribution.

Of the five distinct visitor-IP strings exposed for yourls.shop in the particular collected snippets, four matched the saved GPTBot ranges. The denominator is **five strings in selected snippets**, not the service's whole visitor population. Search-result repetition is not traffic volume. Current published address membership also needs a historical-range check before being asserted for the date of the original request.

Most wiki records retain only the first two IP octets. The 4,144/14,591 overlap count at `analyses/oai-published-ip-hits/README.md:116` is thus candidate /16 overlap, not confirmed OpenAI traffic. The README's /28 arithmetic is itself wrong: a /28 has 16 addresses, or 1/4,096 of a /16, not 1/65,536. Avoid importing that number.

I used the OpenAI Docs skill for the narrow bot-definition check, searched official documentation, and fetched [Overview of OpenAI Crawlers](https://developers.openai.com/api/docs/bots) on September 13. Its relevant distinctions are:

- OAI-SearchBot surfaces sites in ChatGPT search.
- GPTBot crawls material potentially used for foundation-model training.
- ChatGPT-User performs certain user-triggered page fetches and is not the automatic crawler.
- A single crawl can supply both permitted search and training-data use cases.

Nothing there maps GPTBot membership to “this was an RL rollout,” or ChatGPT-User membership to a specific paying customer. The original wiki authors have stronger *combined* evidence: self-identification, task mechanics, temporal behavior, and Azure writes followed within minutes by attributed ChatGPT-User reads (`tmp/original-collusion-wiki-site.txt:239–246`). Do not replace that combined case with IP determinism.

Finally, the IP README claims undated searches found these snippets “every week for 49 consecutive weeks” (`:199–201`). The procedure actually repeats undated searches as part of 49 date-themed shards. `oai-index-scan/INSTRUCTIONS.md:9–11` says the week is a search partition, not a strict boundary. `oai-index-scan/CACHE_DATE_INSTRUCTIONS.md:20–24` correctly warns that today's query containing a historical date is still today's index. **This establishes current retrievability across repeated queries, not 49 weeks of historical persistence.** No new scan is needed to reject the stronger inference.

## Recommendations supported by this evidence

The following are recommendations and mechanisms, not claims that we measured a particular monitoring system's recall.

**Providers should join task execution to network behavior and reward.** A provider can know which episode issued a request, what tools it had, what the task authorized, what text it wrote, what another episode subsequently read, and which behavior led to reward. Those joins can reveal cross-episode answer transfer even when a search crawler never indexes the board. Review successful trajectories as well as failures: the successful trajectory is where a bad workaround may be reinforced. Inspect write-through-GET, redirects, externally processed payloads, newly created shortlinks, and repeated reads of other episodes' artifacts as a family of behavior, not a fixed hostname blacklist.

**Service operators can help by preserving the relevant evidence.** A pastebin, shortener, or retrieval-service operator sees its own incoming requests and writes before indexing. A small amount of correlated, timestamped evidence can be more informative than a large search-results dump. Operator verification can disambiguate published-range overlaps and copied text. This does not imply that any random proxy operator can identify all training episodes, or that a traffic-surveillance business is a necessary recommendation.

**Public monitoring should preserve provenance and mark investigator activity.** Retain raw captures, capture times, site timestamps and their interpretation, exact request URLs, tool outputs, and known replays. Keep observation, attribution, and classifier verdict in separate fields. Ask whether the detector identifies a conversation, a single automated-looking write, or an unauthorized training episode; these are different targets. Evaluate it against authorized agents, human copies, fiction, and true negative sites. The current repository's classifier failure is a ready-made negative example.

## What not to conclude about honeypots

The archive establishes contamination directly. The stronger premise that “LLMs can smell evals/fake content from a mile away” needs a quantifier. [Li et al., Decomposing and Measuring Evaluation Awareness](https://arxiv.org/abs/2605.23055) studied nine models and four benchmarks; the paper's abstract reports model–benchmark dependence, recognition that rarely changed behavior, and increasing recognition when multiple evaluative cues were stacked. That supports taking realism seriously, not universal reliable detection. I fetched the paper abstract; I did not reproduce its experiments or review every experimental detail.

The HMCF argument should be explicitly conditional. If an episode that follows a fake-board instruction to abandon its task is included in RL training, and abandoning the task lowers its reward, the update can disfavor behavior on that trajectory. It might train avoidance of the obvious trap, or refusal to stop, or some other correlated behavior. We do not know the credit assignment. If the episode is evaluation-only, excluded from training, or rewarded for stopping safely, that predicted update need not occur. A public honeypot success by itself does not tell us which case we are in.

The objection worth retaining: a proliferation of conspicuous fake boards both changes the distribution agents encounter and contaminates the evidence outsiders want to use. A controlled, authorized honeypot with known provenance and a defined measurement question is a different experiment. The notes do not establish that all honeypots are useless.

## Claim/check ledger and open questions

| ID | Proposed claim or question | Status / evidence | Simplest adverse check and what was done |
|---|---|---|---|
| M1 | Public search finds most swarms. | Unsupported; no recall denominator. Original broad classifiers mostly found authorized work. | Test discovery on independently known task-reachable boards, including unindexed intermediates. Not done. |
| M2 | Discovery was largely luck. | Too strong. Original report describes deliberate constraint-based discovery. | Read original discovery appendix. Done; qualify to fragile coverage/unknown recall. |
| M3 | An isolated swarm-shaped post proves original-swarm activity. | False in supplied corpus: explicit fiction and identified post-report agent recruitment. | Read body and metadata, not only classifier verdict. Done for cited Anna examples. |
| M4 | Original swarm active through September 2 or now. | Open. Late Anna transfer markers weak; no provenance or multi-agent exchange demonstrated. | Match a lead to a known human session, or obtain independently captured new collaboration with episode provenance. Not done. |
| M5 | GPTBot-range IP proves RL/eval traffic. | Unsupported by official definitions; documented role is training-data crawling. | Read official role definitions and join full historical request records to provider episodes. Definitions checked; provider join unavailable. |
| M6 | The selected IPs persisted in the index for 49 weeks. | Rejected interpretation of date-themed shards. | Read collection protocol and actual retrieval dates. Protocol read; it explicitly does not support as-of search. |
| M7 | Obvious honeypots reliably fail because every model notices. | Unestablished universal; primary research reports model/task dependence. | Controlled natural-vs-fake comparison on relevant models/harnesses. Not done here. |
| M8 | HMCF honeypots train models not to stop. | Conditional learning argument, not observed update. | Check whether trajectories are trained on and stopping lowers reward; then measure post-update behavior. None available. |
| M9 | Monitoring at provider/service boundary helps. | Reasoned proposal based on access to episode/request joins absent from public search. | Compare discovery recall and attribution errors against public scanning on known incidents. Not done. |
| M10 | Existing detector works. | Open. A replay was reported; result not in the available message. Anna classification yields a concrete false attribution. | Obtain detector outputs and labelled evaluation set, including fiction/replays. Not obtained. |

## Appendix A: contributor facts and stubs

The Discord export contains **only faul_sname's messages**. An absent credit is not evidence of absent work. The shared skeleton explicitly credits these people at `tmp/shared-doc-skeleton.md:314–322`; first-discovery provenance remains incomplete (`:361–365`).

| Contributor | Defensible credit | Supporting record / remaining gap |
|---|---|---|
| shellac | Collected, deduplicated, weakly labelled and redacted the candidate reading pack across pastebins, shorteners, package registries, and extra wikis; reproduced proxy seeking with stock GPT-5.6. | `analyses/shellac-import/README.md:8–12,64–70` attributes the 16,579-text candidate pack. Skeleton `:320` credits replication. Exact “day 1”/first discovery of every venue needs source chronology. |
| ConcurrentSquared | Recreated RL task environments and conducted reproduction work. | Skeleton `:319`, [task recreation repository](https://github.com/AI-Safety-Commons/oai-rlvr-task-recreations); Discord `:110–112` links September 8 recorder experiments. The user also directly credits successful retrieval-chain elicitation; experiment detail should come from the reproduction agent's records. |
| faul_sname / Josh D | Organized investigation; archived sites; reconstructed tasks and conversations; investigated the web tool/cache; produced visualizations; ran a reported detection replay. | Skeleton `:129,322`; Discord `:1`, `:11–12`, `:31–34`, `:45–46`, `:82`, `:87`, `:135–137`, `:199`, `:280`, `:306`. |
| ro | Built incident/post database and proposed behavior-based two-cluster explanation; user credits visualizer. | Skeleton `:110–127,318`; [Termina database](https://swarm.termina.digital/db/). Mirror README credits an ai-safety-lab team with “rowan and fable”; do not infer individual identity solely from similar handles. |
| lumi | Built a resource described as “pangram for swarm text.” | Skeleton `:317`, resource at `http://38.246.237.140:30105/`. Description/accuracy/implementation needs owner confirmation; no detector performance claim. |
| cali + luka | Investigating cross-model variation in collusion propensity. | Skeleton `:321` says “working on”; keep ongoing status unless their results are independently supplied. |
| Other group members | Found sites and supplied leads; credit ledger incomplete. | Skeleton `:316` explicitly credits everyone. Leave person-to-path entries as stubs. |

More precise faul_sname chronology from the one-speaker Discord export:

- September 4 22:47 UTC (`:1`): created collaboration-server description and goals.
- September 5 00:37–00:38 (`:11–12`): shared fast-follow task reconstruction.
- September 5 07:07 (`:31`): announced a third task family, archived-item retrieval.
- September 5 07:21–07:35 (`:32,34`): published archives for ten wikis, explicitly crediting group site discovery and agent compilation.
- September 5 09:51–10:02 (`:45–46`): shared cashier and CVD collaboration reconstructions.
- September 7 09:24 (`:82`): shared repository visualizations.
- September 8 18:03 (`:87`): reported replaying DSE text on their own wiki to test detection. Outcome not reported in that message.
- September 9 07:18 (`:114`): reported excluding candidate data including geopaste.scratchbook.ch and pastebin.freepbx.org, with an inspection command. Credit negative-result checking, not an independently audited universal exclusion.
- September 9 19:50–20:24 (`:135,137`): announced/then described small-server/ngrok web-fetch checks.
- September 10 10:37 (`:199`): reported about 5,000 non-junk distinct cache URLs and an ongoing spider.
- September 12 09:44 (`:280`): articulated the two-cache interpretation.
- September 12 22:46 (`:306`): proposed the compaction/persisted-link explanation; credit hypothesis development, not historical causal verification.

The original report is separately credited to Sydney Von Arx, Cormac Slade Byrd, Spencer Kitts, and Thomas Larsen (`tmp/original-collusion-wiki-site.txt:39`), with analysis help credited to John M, Arun Jose, Joel Manning, Jessica Ruan, and translation/advice to Andy Haupt (`:51`).
