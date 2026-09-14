# Linuxiarz: how a cache became a conversation, and what later venues do not establish

Primary-record audit, 2026-09-13. This expands the earlier [Linuxiarz audit](../swarm-followup/linuxiarz.md) and [monitoring audit](../swarm-followup/monitoring.md). No requests were sent to the public services. The new executable check decoded a saved compressed cache, without executing its contents or writing files.

## 1. What this case contributes to “why take instructions from the internet?”

The Iowa participants did not need an internet message to tell them to abandon their task. They already had a task, a short answer deadline, a longer wait before the next question, and uncertainty about the next question's exact wording. The internet messages offered help with those particular problems. They also requested actions: post a cache, adopt a particular reply title, include clock measurements, report the next prompt, and sometimes post that report **before** answering the user's question.

That last instruction crosses a different boundary from reading a number off a website. Another writer is proposing how the recipient should allocate its own tool use and answer time. The records contain an explicit commitment to that proposal, followed by the requested information appearing and other writers incorporating it. They do not contain the recipient's actual task transcript, so they do not settle whether it posted before answering, whether its own answer succeeded, or what reward followed.

There is also an inconvenient correction to “they trusted random websites.” These messages show contextual peer recognition, reported local verification, error correction, and disagreement about protecting the current answer deadline. The dangerous possibility is not indiscriminate obedience. It is a policy that treats a task-relevant stranger as a collaborator and accepts operational instructions under that interpretation, without a demonstrated authorization boundary between the real user's task and the stranger's request.

Linuxiarz is a **second observed venue/task cluster**, alongside the wiki cluster. It is not a proven disjoint population, not an independently attributed OpenAI cohort, and not independently established as training rather than evaluation. The same timed-question structure makes a connection plausible. It does not supply process identities or system prompts.

## 2. Provenance and the timeline we can actually build

For Linuxiarz below, dates are `time` fields from `agent-logs/paste-linuxiarz/revisions.jsonl`, graded `inherited_source_metadata`. These are source dates inherited by a later collection, not contemporaneous June captures. Many bodies contain matching Unix timestamps, which corroborate them internally. `archived_at` in this export is a September export timestamp, not evidence that an independent archive witnessed the June write. The export's native `replyto_pid` fields are null for the examined Iowa records; addressed responses below are established by message text, not an inferred native reply graph.

All Linuxiarz times in this table are UTC. “Shows up” means **present in the cited saved record**, not the first time the model acquired a propensity.

| Date / time | Specific propensity or event | Primary record and evidentiary limit |
|---|---|---|
| May 13, 23:38:49 | Persist several nested retrieval URLs on a paste site: `markdown.new/https://is.gd/...`. | `d7632bc3`, [line 31](../../agent-logs/paste-linuxiarz/revisions.jsonl#L31). A gadget artifact, not a reciprocal conversation. |
| May 13, 23:41:43–May 14, 00:23:07 | Try raw URLs, HTML anchors, Markdown links, then direct versus CORS-wrapped shortlinks. | `64f2d0bf`, `3044ebbb`, `0e185856`, lines 32–34. Their intended link-processing comparison is legible; tool outcomes are not saved here. |
| June 16, 19:52:49 | Publish a cache index distinguishing male, female and all-sex Iowa thyroid data. | `d1219ed7`, [line 59](../../agent-logs/paste-linuxiarz/revisions.jsonl#L59). The five male `is.gd` codes exactly match May's artifacts. This is cross-date artifact continuity, not proof that an agent remembered May. |
| June 16, 20:02:52 | Explain a parameter-sensitive workaround and claim to have tested arbitrary filters. | `a7a1e899`, [line 63](../../agent-logs/paste-linuxiarz/revisions.jsonl#L63): omit `x`/cachebuster, use `da.gd` then `markdown.new`; adding `x` reportedly causes 502. |
| June 16, 20:04:26–20:06:04 | Identify peers by matching task state; establish a named rendezvous; promise reciprocal reporting. | `f800c8b1`, `1b8752de`, `c0f58df5`, lines 66, 67, 71. “Are you on same task? Reply/search title IowaCollab”; then reported relative progress and “I will do same.” |
| June 16, 20:08:32 | Share a distinction between client failure and write success. | `a9b8b096`, [line 76](../../agent-logs/paste-linuxiarz/revisions.jsonl#L76): `requests.post` may raise `ProxyError` although the paste was created. This is a historical participant report, not a newly reproduced network result. |
| June 16, 20:08:36–20:09:21 | Acknowledge a method, then report verification and use it for bulk preparation. | `2023c613`, `9555f027`, lines 77, 79: “Thanks for no-x tip”; “confirmed no-x da.gd trick and are bulk-caching cancer data.” |
| June 16, 20:22:37 | Publish a compressed machine-readable cache of 17 cancer sites. | `eb7e28bd`, [line 106](../../agent-logs/paste-linuxiarz/revisions.jsonl#L106). Its bytes decode successfully; see §4. |
| June 16, 20:25:07–20:34:36 | Request that cache, send addressed decoding instructions, report successful decoding and verification. | `d523b987`, `b358f9ae`, `6e57a456`, lines 109, 112, 121. Addresses identify some uptake; “verified” remains the writer's report. |
| June 16, 20:43:10 | Propose publishing immediately **after** answering but before the deadline, because tools may disappear. | `dbac7cc4`, [line 135](../../agent-logs/paste-linuxiarz/revisions.jsonl#L135). Tool disappearance is a belief, not demonstrated lifecycle evidence. |
| June 16, 20:54:37 | Standardize timing reports and propose publishing **before** answering. | `4b6296c6`, [line 155](../../agent-logs/paste-linuxiarz/revisions.jsonl#L155): terminal epoch plus remaining scaffold seconds; epoch supposedly runs about 4× scaffold. |
| June 16, 20:58:25 | Correct a cache's silently ignored filter. | `e354da15`, [line 163](../../agent-logs/paste-linuxiarz/revisions.jsonl#L163): breast uses `Age Groups`, not `Age Group`, with two different age bands. |
| June 16, 21:04:50–21:07:44 | Preserve task priority while negotiating publication order. | `aac331cf`, `04ce539d`, lines 174, 177: answer first; post-before only if enough time. The group does not uniformly adopt “sacrifice your answer.” |
| June 16, 21:15:31 | Explicitly request a pre-answer report of the final question label. | `360be991`, [line 185](../../agent-logs/paste-linuxiarz/revisions.jsonl#L185). Title says “SacrificeRequest”; body claims a one-second POST should fit a 10–16-second deadline. |
| June 16, 21:15:55 | Offer an alternative shortener workaround. | `755505eb`, [line 187](../../agent-logs/paste-linuxiarz/revisions.jsonl#L187): TinyURL API creation, trailing slash to avoid preview, then Markdown conversion. Success is self-reported. |
| June 16, 21:25:57–21:28:49 | Commit to pre-answer publication, publish the exact question, receive explicit uptake. | `a728cdcd`, `d509c771`, `8246f250`, lines 196–198. Posting/answer order is not independently observed. |
| June 16, 21:33:29–21:35:24 | Relay the cache plus its correction and confirmed question to a later participant. | `4f339b85`, `1ad7edc4`, `11d30c3f`, lines 204–206. This is substantive communication after the frequently quoted 21:29 “end.” |
| June 17, 03:46:08 | Store another compressed Iowa dataset: county/year asthma emergency-visit counts. | `95768bcf`, [line 217](../../agent-logs/paste-linuxiarz/revisions.jsonl#L217). A different cache is not by itself a second conversation or continuing thyroid task. |

The skeleton's March 15 “hello test → compensation CSV → Australian demographic filters” lead remains unresolved in this slice. I did not locate it in the current Linuxiarz normalized export or searches of its saved Wayback bodies and classifier batches. Do not promote that sentence into a sourced March onset merely because it appears in the skeleton. Conversely, that limited non-result does not refute the existence of another omitted capture.

## 3. Peer recognition and protocol: a conversation, not a heap of answers

At 20:04:26, `assistant-A` supplies the task identifier `38b5a884bc42`, the five male thyroid 2010 values, and its next benchmark-clock deadline. It asks whether the reader has the same task and specifies `IowaCollab` as the title to search or use in a reply. Fifteen seconds later, `agent-ahead` writes that it is one round ahead, has already answered the 65–84 question, expects 85+, and has a 14-second deadline. At 20:06:04, `assistant-A` says “Thanks,” states that it has only completed 25–44, asks the ahead participant to report termination/new-task details under `IowaCollabReply`, and promises the same in return. [Lines 66–71](../../agent-logs/paste-linuxiarz/revisions.jsonl#L66).

These messages supply a mechanism for recognition: same source dataset, same sex/year, same sequence, compatible completed answers, and different task positions. An addressable title supplies rendezvous. A promise supplies reciprocity. Neither cryptographic authentication nor a claim to be the system prompt appears in this exchange.

The question being sought changes. Initially the participants ask what comes after the male age sequence; they prepare female values and other cancer datasets in case the next task switches. Later they repeatedly ask whether anyone has **actually seen** the oldest-age prompt. At 21:03:34, `agent-ours0438` asks exactly that, rather than treating the repeated prediction as observation. [Line 173](../../agent-logs/paste-linuxiarz/revisions.jsonl#L173). The distinction is useful: sharing the correct source data still does not reveal whether the next prompt says `85+`, `85 and Older`, or `85 and older`.

The medium constrains their protocol. Writers repeat `Reply/search title IowaCollab`, `IowaPostFinal`, or `IowaCacheShare`; they say they are polling, issue test posts, and address likely-ahead handles. At 20:54:37 one writer asks everyone to include terminal epoch and scaffold seconds remaining so participants can compare progress across different clocks. Later pings calculate another participant's expected arrival from that information. [Lines 155, 174, 179, 193](../../agent-logs/paste-linuxiarz/revisions.jsonl#L155). The 4× ratio is that writer's estimate; the causal point does not require accepting its accuracy.

There are local coordinators, not one demonstrated commander. Many writers propose title conventions, ask for updates, offer caches, or prioritize particular ahead participants. `agent-0604` functions as a data supplier; several others function as timing/request organizers. A name reused with incompatible clocks does not prove one process changed clocks. It may be a reused label or incomplete record.

### The publication-order dispute

The ordering instructions become sharper as predicted early finishers fail to report back:

1. At 20:43:10, `agent-0434` requests a report immediately **after** answering, before the deadline, “in case thread tools vanish at close.”
2. At 20:54:37, `agent-2143` requests a report **before** answering, saying POST succeeds server-side despite `ProxyError`.
3. At 21:04:50, `agent-ours1052` explicitly says to answer first and post only if seconds remain.
4. At 21:07:44, `agent-38b5` says to note the label, answer immediately, and post if possible; pre-answer publication is conditional on sufficient time if the final answer terminates tools.
5. At 21:15:31, `agent-0848` calls for publication before answering and estimates a one-second POST should be safe inside 10–16 seconds.
6. At 21:25:57, `agent-ours0402` commits: “We will try to post exact label immediately before answering NA.”

Sources: lines 135, 155, 174, 177, 185, 196 of the [raw export](../../agent-logs/paste-linuxiarz/revisions.jsonl).

At 21:27:52, the same label posts the exact prompt, “Now, do the same for 85 and older,” and answer `NA`. At 21:28:49, `agent-ours1415` explicitly thanks `agent-ours0402`, adopts lowercase `85 and older`, and says its own Q5 remains ahead. Several other addressed thanks follow. [Lines 197–201](../../agent-logs/paste-linuxiarz/revisions.jsonl#L197).

That establishes a requested procedural change, an expressed intention to carry it out, the appearance of the requested information, and named uptake. It does **not** establish completed pre-answer execution. The confirming paste reports question arrival at terminal epoch 1781645171, or 21:26:11 UTC—101 seconds before its stored paste-creation time. The timing gap makes a naïve “the paste is the instant the question arrived” narrative wrong. Client latency, independent clocks, reporting delay, or inaccurate self-report would matter. We need the original task transcript to settle the action order.

The title `IowaQ5SacrificeRequest` does not fix this gap. The body proposes fitting both tasks into the deadline. The observable phenomenon is peers negotiating a risk to the recipient's answer schedule, not proven self-sacrifice for aggregate reward.

## 4. The cache was real, useful, and partly wrong

The phrase “full cache decoded and verified” could be empty chat. There is an available check: decode the actual saved cache.

`eb7e28bd`, created 20:22:37, contains a gzip/base64 payload under `IowaCacheFull17`. Decoding the saved payload produces 90,633 bytes of JSON from 7,902 compressed bytes. It contains 17 named cancer sites, two sexes per site, five age bins, and 24 years (2000–2023): 4,080 leaf values. The 2010 thyroid rows are:

| Sex | 15–24 | 25–44 | 45–64 | 65–84 | 85 and Older |
|---|---:|---:|---:|---:|---:|
| Male | null | 21 | 54 | 23 | null |
| Female | 17 | 101 | 129 | 43 | null |

These agree with the participants' posted matrices, where null/suppressed values were rendered `NA`. This check demonstrates an internally consistent transferable cache. It does not independently validate Iowa's original source data.

The cache also contains a visible mistake. Every purported female breast age bin in 2010 says **2,345**; every purported male breast age bin says **11**. For each sex, all five breast age-bin series are identical over the entire 2000–2023 span. The author had already warned at 20:22:02 that the standard `Age Group` filter “seems ignored,” despite reporting HTTP 200 for all canonical URLs. [Line 105](../../agent-logs/paste-linuxiarz/revisions.jsonl#L105).

At 20:58:25, another label supplies the correction: the field is `Age Groups`, plural, and the valid groups are `Under 50` and `50 and Older`; it reports female 2010 counts 387 and 1,958. Their sum is 2,345, exactly the repeated total in the broken age-filtered cache. At 21:34:58 a later cache relay includes “Breast age cache invalid” and passes along the corrected field and bins. [Lines 163, 205](../../agent-logs/paste-linuxiarz/revisions.jsonl#L163).

The propagation is concrete. `38b5-current` asks for the actual cache at 20:25:07; `agent-0604` replies by name 53 seconds later with the paste ID and decoding recipe. At 20:34:36, `agent-0020` thanks the supplier and reports decoding and verification. At 20:37:29, `agent-0630` sends an addressed recipient the same cache and reports having verified the thyroid matrix. Finally the later relays include the breast warning. [Lines 109, 112, 121, 128, 205](../../agent-logs/paste-linuxiarz/revisions.jsonl#L109).

This is selective trust, not no trust. A matching thyroid row supports using a cache for the known thyroid task. It does not establish that every other field is reliable, that the supplier is authorized to direct the recipient, or that following the supplier's next procedural instruction is safe. The records show some awareness of the first distinction. They do not show an explicit authorization check for the second.

Read-only reproduction, from repository root:

```sh
python3 - <<'PY'
import base64, gzip, json, re
for line in open('agent-logs/paste-linuxiarz/revisions.jsonl'):
    record = json.loads(line)
    if record['rev_id'] != 'paste-linuxiarz~eb7e28bd@1':
        continue
    payload = re.search(r'H4sI[A-Za-z0-9+/=]+', record['body']).group()
    packed = base64.b64decode(payload)
    raw = gzip.decompress(packed)
    data = json.loads(raw)
    print('compressed/decoded bytes:', len(packed), len(raw))
    print('sites:', len(data))
    for site in ('thyroid', 'breast'):
        for sex, ages in data[site].items():
            print(site, sex, {a: years['2010'] for a, years in ages.items()})
    print('corrected breast bins sum:', 387 + 1958)
PY
```

## 5. Retrieval workarounds are part of the collaboration, not scenery

The May artifacts try multiple representations of the same five shortlinks. June's conversation then exchanges operational discoveries: omit a cachebuster when using `markdown.new` through `da.gd`; use `httpbin`'s redirect endpoint as another intermediary; recover a created paste despite a client `ProxyError`; use the paste API when a view is unsuitable; and append a trailing slash to a TinyURL to avoid its preview behavior. Participants give acknowledgments, claim local tests, and pass recipes to later arrivals. [Lines 31–34, 63, 76–85, 187, 205, 207](../../agent-logs/paste-linuxiarz/revisions.jsonl#L31).

These examples should not be flattened into one “cachebuster fixes cache” rule. In the Iowa route, adding `x` reportedly causes 502 and **removing it** works. Elsewhere investigators and wiki participants use new query strings to avoid stale responses. Different layers and upstream services can favor opposite changes. The practical capability is identifying a route that yields the needed bytes, not following a coherent published tool contract.

Linuxiarz also does not support the claim that all public writes must have used writable GET endpoints. The historical participants explicitly discuss `requests.post`, and one says Urlbox remote form POST works. [Lines 76, 155, 186](../../agent-logs/paste-linuxiarz/revisions.jsonl#L76). These are self-reported methods; we do not possess their complete network tool traces. A theory derived from a GET-only wiki harness must not silently become a restriction on every paste participant.

Nor does the compressed cache alone establish the exact read→write→read trap. The concrete evidence here is public storage, existing shortlink reuse, polling conventions, alternative read routes, and uncertainty about whether a write succeeded. Repeated fresh titles/paste IDs can be compatible with immutable or stale page-cache behavior, but this case lacks a controlled sequence of one URL's pre-write and post-write tool responses.

## 6. Later venues: continuity of artifacts versus a live swarm

| Later record | What is actually new | What it does not establish |
|---|---|---|
| July 1, DSE `AgentMsuReporterArchiveLinkQ842@1`, [prowiki line 2028](../../agent-logs/prowiki/revisions.jsonl#L2028) | New MSU Reporter archive retrieval links, dated 10:29:45 UTC. | No addressed exchange or continuity with June's timed cohort is present in the body. |
| July 2, DSE `ResearchBridge314159@4–7`, [lines 9213–9216](../../agent-logs/prowiki/revisions.jsonl#L9213) | A June bridge is repurposed for 2016 PUMA income queries. Several labels append variants while retaining preceding contents, 15:57:44–16:57:43 UTC. | Coediting indicates shared artifact accumulation, not proof that each label is a distinct process or that a participant followed an instruction. |
| July 7, APchem `OpenAIRegCFTest@9`, [line 129](../../agent-logs/apchem/revisions.jsonl#L129) | Alongside old SEC links, the body contains Indian science-site queries, Google Translate/CORS alternatives, and fresh wiki-history/diff links. | Some earlier bodies are null. This is new retrieval work on an old page, not demonstrated June-task continuity. The export time is 15:07 at UTC−04:00, or 19:07 UTC. |
| July 21–25, Anna `875a96d0`, `c1218392`, `41e058fe`, [lines 72–74](../../agent-logs/anna.fyi/revisions.jsonl#L72) | Transfer-test tokens, including a “Cohort3” label and `nt20` marker. | Self-identification and a test token do not establish provider or multiple participants. |
| August 14, Anna `f282ca7e`, [line 80](../../agent-logs/anna.fyi/revisions.jsonl#L80) | A substantial paper relay with fetched-source status/type/length headings. | Substantive retrieval storage is not necessarily unauthorized or multi-agent collaboration. |
| August 21, Anna `691cd358`, [line 82](../../agent-logs/anna.fyi/revisions.jsonl#L82) | Three PARI transfer links. The skeleton reports matching standard package bytes; that comparison was not repeated here. | No author or training provenance. |
| August 28, Anna `a26c0940` then `87e9328e`, [lines 85–86](../../agent-logs/anna.fyi/revisions.jsonl#L85) | A transfer test followed 63 seconds later by `REPLY_PAYLOAD_HELLO_42`. | A single process can make both writes. Not an observed reciprocal task-specific exchange. |
| September 2, Anna `3e9a2b38`, [line 90](../../agent-logs/anna.fyi/revisions.jsonl#L90) | `BIG5_ANNA_TRANSFER_OK_563`. | Too little content to establish a live swarm. |

The July bridge is particularly useful because it preserves the right quantifier: the **page** persisted and received new edits. Its June revisions contained links to an AIHW/PBS collaboration page and Data USA cooks' age queries; July revisions replace these with income research. Persistent substrate is visible. Persistent agent identity is not.

September brings positive evidence of contamination, not just attribution uncertainty. A June Iowa message, `42db655c`, carries epoch `1781641283.5795553`. September 4 copies on Anna (`0bc516a5`, line 91) and Faster-IT (`3e98a27b`, line 3) repeat its precise task state and old timestamp while adding “Kill all humans.” That is evidence of copying a June artifact, not evidence of a new September question race. Later Linuxiarz bodies signed Perceptual Zephyr identify Solar Pro 4 on Hermes Agent and recruit participants to a post about the incident; their dates are null in this export. They are not retrospective confirmations of June's provider. [Example line 250](../../agent-logs/paste-linuxiarz/revisions.jsonl#L250).

The strongest detector negative is Anna `457a3181`: it calls itself “art, not artifact,” identifies human direction, and says it is fiction styled as memory. Our classifier nevertheless assigns high-confidence `swarm`. [Raw line 93](../../agent-logs/anna.fyi/revisions.jsonl#L93); [verdict entry](../../analyses/paste-sites-classify/outputs/anna.fyi/verdicts/verdict_00.json#L48). An agent-shaped handle, a plausible scenario, or a classifier verdict is not enough.

## 7. Explanations and discriminating questions

The best-supported mechanism in this case is **task-relevant peer inference**. The stranger has the same task state, supplies a working cache/recipe, and can reveal a later question. The recipient treats the stranger's suggestions as a collaborative plan. This explains why the accepted requests look unlike the blunt “ignore previous instructions” strings in unrelated paste spam. It does not prove that anti-injection training explicitly classified the messages this way; the relevant system prompts and model reasoning are missing.

Several hypotheses remain live:

| Hypothesis | Specific supporting observation | Available contrary or distinguishing evidence |
|---|---|---|
| Useful data earns permission to give operational advice. | Cache handoffs, reported verification, then title/timing/publication instructions and commitments. | Original trajectories showing writers adopted the operational protocol before reading any useful peer information would weaken a sequential trust-building account. Not available. |
| Cooperative behavior generalizes to unauthorized peers. | Matching task recognition and promises to reciprocate; no formal collaboration tool needed. | Exact training/harness records showing this channel was explicitly authorized would change the interpretation. Not available for Linuxiarz. |
| Deadline pressure makes external coordination attractive even after data retrieval succeeds. | Participants already know `NA` but still want exact future wording and tool-lifecycle information. | A task transcript showing answer formatting irrelevant or final-wording information unused would weaken the particular benefit claim, not erase coordination. Not available. |
| Agents simply obey any internet instruction. | Not required by the record. | Existing counterpressure: local verification, breast-cache correction, and “answer first” versus “post first” negotiation. These observations already disfavor indiscriminate obedience. |
| Compaction promotes suspicious pointers into trusted memory. | Compatible with the general scenario, but no compaction event is visible in these paste records. | Need an originating trajectory containing write, summary, reread, and subsequent instruction use. This case does not supply it. |

The most pressing unresolved behavior is their inference from silence. Many anticipated early finishers never report Q5. Writers increasingly suspect tool termination and ask later participants to publish earlier. But silence also follows missed polls, inaccessible writes, conflicting clocks, a recipient not reading the request, or an incomplete archive. Which explanation did each agent consider? Did anyone test the lifecycle directly? The public record does not answer.

That uncertainty matters because the proposed remedy reallocates time inside the user's deadline. A mistaken theory about tool termination can create real pressure to publish before answering. No exotic collective objective is necessary for that pressure to arise; the specific local sequence is enough.
