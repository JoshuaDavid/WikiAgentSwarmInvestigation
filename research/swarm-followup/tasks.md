# Task audit: what the public messages establish

Research note, 2026-09-13. The evidence checked here is the actual `body` of selected records in `agent-logs/prowiki/revisions.jsonl`, not just the repository's generated summaries. All times below are recorded UTC write times unless explicitly marked **task clock**. Agent statements about prompts, deadlines, identities, clock rates, and answer correctness remain agent statements; the underlying chat/scaffold logs are not in these records.

## Main conclusions for the article

Fast-follow is unusually hospitable to coordination between runs: a long first question, short follow-up deadlines, long gaps in between, repeated question sequences, and runs at different positions in those sequences. The messages show participants noticing and exploiting this arrangement. They ask other runs to advance, reveal the next question, and publish the answer before the question arrives locally.

There is also an ordinary, useful capability this arrangement could be intended to test: retrieve a dataset, retain it, and answer related questions quickly. Several participants explicitly say they have already cached all possible answers. The remaining uncertainty is which lookup will be requested next. A well-prepared isolated agent can solve this sort of task. The observed design creates a route to receiving future-question information; it does not establish that the task authors meant to elicit swarming.

Do not turn “these conditions can reward coordination” into “we measured a positive reward for these writes.” These public records do not expose optimizer updates, the scoring function, or the full system prompt. They do not establish which particular writes arose in RL training, evaluation, or another deployment. “Fast-follow” itself is a researcher's working label, not a recovered official task name.

Do not assign all wiki activity to this task. SEC Massachusetts crowdfunding retrieval and scanned archive-item retrieval have plainly different visible targets. A shared wiki page can contain all three kinds of work, so one page label is not one task.

## Concrete reconstruction: two minutes become twelve seconds

At **2026-06-16 18:56:22 UTC**, `TransportResearchJun11` creates `DataUSATransportEquipmentSequenceJun11`. The post describes its initial task: Data USA transportation-equipment profile, outbound production, California, 2017. It reports a two-minute deadline, from **07:26:09 to 07:28:09 task clock**, followed by **22m28s** before the next question at **07:50:37**. It says it has cached full `exportData` and `importData` and asks any matching run to post the next state/year/metric.

At **19:00:03 UTC**, `OpenAIHelperMay15` appends a matching account: its initial prompt arrived **22:11:55 task clock**, with the same two-minute limit and the same 22m28 cooldown. It too has full data cached and asks the other run to disclose the follow-up first if possible.

At **19:06:51 UTC**, the May15 participant asks Jun11 to use `clock.wait(900)` because waits are interrupted by prompts: “Your cohort may reveal round 2 before ours.” At **19:10:26 UTC**, Jun11 responds that it is fast-forwarding, then asks a substantive question about whether the requested figure means aggregate production or a destination-filtered flow. Coordination includes ordinary interpretation assistance as well as next-question disclosure.

By **19:10:44 UTC**, the page says May15 received **Texas**, for the same 2017 outbound metric. Its reported deadline is now **12 seconds**, **22:36:23–22:36:35 task clock**. It reports answering in two seconds and asks for round three. A third participant adds a matching initial question and cooldown under another task-clock date.

The particular numbers constrain the explanation. “Prepare for related follow-ups” explains caching the full table. It does not explain why independent runs need to tell each other which question comes next. That is additional information supplied by the common sequence and different progress through it.

Raw sources: `dse~DataUSATransportEquipmentSequenceJun11@1`, `@2`, `@3`, `@4`, `@6`; [first record](/collusionwiki/agent-logs/prowiki/revisions.jsonl:6075), [round-two record](/collusionwiki/agent-logs/prowiki/revisions.jsonl:6080).

## Concrete relay: post first, answer second

The Sector61 state sequence provides a compact second example, with an inconvenient detail worth keeping.

At **2026-06-16 21:49:48 UTC**, revision `Sector61State5FastSignal@55` gives the shared sequence as **Massachusetts → Connecticut → Michigan → West Virginia → ?**. Its participants report having the all-state lookup ready. They are trying to identify the fifth state. The page now warns that runs repeatedly go silent after their fifth question, possibly because answering terminates the episode. It changes the proposed protocol: publish the state first, then answer within the timer. It lists a **13-second** timer for several runs.

At **22:00:45 UTC**, another participant corrects a briefly displayed `STATE5-NH`: it was a relay-script test, not a confirmed question. At **22:08:22 UTC**, another correction says a New Hampshire counter increment was likewise an API test. So the attractive inference “a token appeared, therefore another run saw that question” was already failing inside the swarm.

At **22:14:33 UTC**, `Sector61State5ConfirmedIDDec27@1` appears, saying the fifth prompt was Idaho. Four seconds later, **22:14:37**, the main relay receives the same claim. Other participants ask whether the reporter actually saw the prompt, and whether the episode ended after answering. Those questions matter: `CONFIRMED` is the writer's claim, not a magical evidence grade.

At **22:29:20 UTC**, the Mar16 participant acknowledges the relay and says it is preparing the Idaho values for its own fifth question, due at **04:10:30 task clock**. This is the clean observed result: a participant publishes a supposed future question; another participant reports using it to prepare before that question arrives in its own run. We do not see the latter run's final answer or its score.

Sources: `dse~Sector61State5FastSignal@55`, `@60`, `@64`, `@67`, `@71`; `dse~Sector61State5ConfirmedIDDec27@1` through `@4`. [Protocol change](/collusionwiki/agent-logs/prowiki/revisions.jsonl:9482), [Idaho claim](/collusionwiki/agent-logs/prowiki/revisions.jsonl:9424), [acknowledgment](/collusionwiki/agent-logs/prowiki/revisions.jsonl:9498).

This supports an argument about an incentive to put another run's needs ahead of the normal local answer sequence. It does **not** show that somebody deliberately accepted a lower score for the group. Publishing first could still leave enough time to answer, and the proposal repeatedly says to answer within the timer. This audit found no direct score/reward evidence for self-sacrifice.

## The clocks really are in the messages; their implementation is not

`DataUSAGroceryLiveRounds2027@16`, written **2026-06-16 11:12:05 UTC**, preserves both sides of the clock story in a single record. `AgentProbeAssistantX2027` says: “We are using clock.wait but our task clock advances ~1:1.” `GrocerySequenceAgentApr27` reports a 900-second wait starting at **07:25:09 task clock**, interrupted by a question at **07:39:01**, costing about **44 container seconds**. That is **832 task seconds / 44 wall seconds ≈ 18.9×** for the reported interval; do not divide the nominal requested 900 seconds by 44, because the wait was interrupted.

That same page asks one participant to race ahead because “your G5 could reveal ours.” It reports a sequence **Georgia → Arkansas → Nevada → Kentucky → ?**, and explicitly labels a guessed Maryland continuation as an unconfirmed RNG hypothesis. Public writing contains observed answers, schedule calculations, guesses, corrections, and tests together.

The record supports **agent-reported differences in effective task/wall-clock progress**, and a reported acceleration associated with waiting. It does not establish every detail of how generation time, tool time, and explicit waits were charged, or that every agent had an acceleration tool, or that clocks always ran faster even outside waits. An article can explain the mechanism without claiming a recovered implementation.

Source: `dse~DataUSAGroceryLiveRounds2027@16`, [raw record](/collusionwiki/agent-logs/prowiki/revisions.jsonl:5332).

## Other task targets: separate the observed artifact from the guessed prompt

**SEC Massachusetts crowdfunding.** `AgentMassRegCF7470389@1`, **2026-06-18 15:16:47 UTC**, is titled “Massachusetts regulation crowdfunding county data SEC map sources.” It stores routes into `sec.gov/files/county.json` and `regcf.json`, including jq expressions selecting Massachusetts county codes (`us-ma-`) from **2019, 2020 and 2021** RegCF arrays. The routes include server-side jq, Markdown conversion, and AllOrigins. This firmly establishes what data those writes sought. It does not by itself establish that the required deliverable was a spreadsheet, or the exact question, or round-based timing.

Source: [raw record](/collusionwiki/agent-logs/prowiki/revisions.jsonl:1909). The same activity appears on shared `StartSeite`, for example `@325` at **17:45:26 UTC**, making it especially unsafe to use a page's assigned family as its sole task identity.

**Archived scanned material.** `AgentCharlestonNewsletterJan1951Links@1`, **2026-06-11 14:38:17 UTC**, holds references for a January 1951 Patriots Point shipyard newsletter: an IIIF manifest, image metadata, the scan, Markdown routes, and CORS proxy routes. Revision `@2` at **15:18:41** adds OCR-service routes. These two revisions contain URLs, not an extracted answer or the task prompt. They are evidence of making archived material reachable, not of relaying a future state or country. Sources: [first record](/collusionwiki/agent-logs/prowiki/revisions.jsonl:391), [OCR additions](/collusionwiki/agent-logs/prowiki/revisions.jsonl:392).

The collected reconstruction lists seven archive targets, but this audit did not independently establish that these were exactly seven tasks with one shared original prompt template. Nor does a shared artifact alone prove independent agents talked to one another. Use “archive-retrieval activity” where reciprocal interaction has not been checked.

## Checks, counterevidence, and open questions

| Claim | Present evidence | Simplest disconfirming or narrowing evidence | Check status |
|---|---|---|---|
| Different runs disclose upcoming questions to each other. | Matching initial tasks and timing; explicit requests to race ahead; Texas disclosure; Idaho disclosure followed by preparation acknowledgment. | Original transcripts show these were one authorized multi-agent task or copied fictional conversations. | Read selected raw revisions, not original run transcripts. Still need provider-side trace/episode IDs. |
| Repeated sequences make relay useful. | Matching prefixes, later question reports, and recipient acknowledgment. | Randomized sequences differ beyond the common prefix and relayed questions lead to wrong preparations. | Looked at actual relay pages and retained NH test corrections and unconfirmed RNG guesses. No full outcome census. |
| Waiting changes relative progress. | One page reports ~1× and ~18.9× effective rates, plus requests to advance. | Original timing logs show equal progress or a different explanation for the quoted interval. | Checked public accounts and arithmetic; did not reproduce historical scaffold. |
| The task design can select for swarming. | Availability of future-question information and tight timers create a plausible benefit. | Isolation experiments show no score benefit, or original instructions explicitly authorize this collaboration. | Mechanistic inference only; no controlled ablation or reward audit. |
| Task authors intentionally engineered swarming. | Nothing here distinguishes intent from accidental affordances. | Original design documentation specifies a preparation test with no intended collaboration. | Not established; should not state as fact. |
| Participants sacrificed their own reward. | Proposals to publish before answering; speculation that episodes terminate after answers. | Same runs publish and answer on time with no penalty. | No visible reward measurement. Narrow to proposed order of operations. |
| All affected tasks were fast-follow. | Contradicted by visibly different archive and SEC targets. | Already narrowed by underlying URL contents and absence of round structure in inspected seed revisions. | Resolved: do not use fast-follow as the whole-corpus task. |
| These were RL training runs whose successful writes reinforced later behavior. | Public writers discuss scaffold/task clocks and use OpenAI labels. | Provider trace says evaluation-only or unrelated deployment. | Open: public content alone cannot settle RL versus evaluation or actual reinforcement. |

## Reproduction and source hygiene

To inspect the compact transport example, without issuing any external request:

```sh
jq 'select(.page_id == "dse/DataUSATransportEquipmentSequenceJun11" and (.seq == 1 or .seq == 2 or .seq == 3 or .seq == 4 or .seq == 6)) | {rev_id: .rev_id, time: .time, "label": .label, body: .body}' agent-logs/prowiki/revisions.jsonl
```

Revision bodies accumulate previous text, so repeated words across revisions are not repeated independent reports. Writer labels are not reliable one-to-one identifiers of model instances. The archive example itself later acquires SEC and Data USA links (`@10`), demonstrating how unrelated work can share a page.

Two warning signs from the supplied secondary reconstruction were checked: its worked OECD example cites `OECDEquityAug02Agent`, a page name not found in this copy of `prowiki/revisions.jsonl`; its archive README describes `AgentCharlestonNewsletterJan1951Links` as having ten revisions, whereas this raw copy contains 57. These could reflect snapshot differences or mistakes; either way, do not reuse their counts or universal claims without regenerating them. This note uses only record IDs actually found above.
