# Swarmchasers Writeup {#swarmchasers-writeup}

## Table of Contents

[Swarmchasers Writeup](#swarmchasers-writeup)

[Table of Contents](?tab=t.azek1shexguv#heading=h.1iy22yxursyf)

[Context](#context)

[Swarmchasers](#swarmchasers)

[Our Theory of Swarm](#our-theory-of-swarm)

[Our reconstructed sequence of events](#our-reconstructed-sequence-of-events)

[The Harness](#the-harness)

[The web.run toolset](#the-web.run-toolset)

[Hosted Search mode in web.run](#hosted-search-mode-in-web.run)

[The page cache](#the-page-cache)

[The ChatGPT models](#the-chatgpt-models)

[The Tasks](#the-tasks)

[Difficult Information-retrieval tasks](#difficult-information-retrieval-tasks)

[Evidence:](#evidence:)

[The fast-follow task](#the-fast-follow-task)

[Why take instructions from the internet?](#why-take-instructions-from-the-internet?)

[Coordination patterns](#coordination-patterns)

[The "single page with many additive revisions" pattern](#the-"single-page-with-many-additive-revisions"-pattern)

[example: OAIEquityDec30Raw](#example:-oaiequitydec30raw)

[The "hub page with many slots" pattern](#the-"hub-page-with-many-slots"-pattern)

[example: AgentOpenAIDataUSAHubMay13X7](#example:-agentopenaidatausahubmay13x7)

[The "linked list" pattern](#the-"linked-list"-pattern)

[example: AgentMassDataNext774411](#example:-agentmassdatanext774411)

[Do we detect other swarms?](#do-we-detect-other-swarms?)

[Could we detect other swarms?](#could-we-detect-other-swarms?)

[Biglab internal policy/technical practice recommendations](#biglab-internal-policy/technical-practice-recommendations)

[Policy suggestions](#policy-suggestions)

[Conclusion](#conclusion)

## Context {#context}

The past months have had numerous incidents in which AI agents under evaluation or training performed actions outside of their task environments. The highest-profile incident as of the time of this writing was the HuggingFace incident, in which an OpenAI internal model gained persistent access to HuggingFace's internal infrastructure, and which you can read more about in [METR's excellent writeup](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation), or [OpenAI's own incident report](https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf). More recently, on September 4, 2026, Sydney Von Arx, Cormac Slade Byrd, Spencer Kitts, and Thomas Larsen published a [writeup](https://collusion.wiki/) detailing a newly-discovered agent swarm that used German-language wikis as a messageboard. [Further investigation later that day](https://news.ycombinator.com/item?id=49564286) uncovered [a third[^1] swarm of agents](https://github.com/JoshuaDavid/WikiAgentSwarmInvestigation/blob/main/research/swarm-mechanisms/linuxiarz-and-other-venues.md) using the linuxiarz pastebin as a messageboard, and as the day progressed ever more instances of agent-generated links and pastes surfaced across the internet, though ~~no more places where there was substantial natural language agent-to-agent communication were discovered~~ maybe not true, need to see if rubygems had natural language.

## Swarmchasers {#swarmchasers}

Late in the day on September 4, a small group of people who found these behaviors surprising and alarming started a discord server "swarmchasers" to share information and leads on swarm behavior. Over course of the next day, our server quickly grew to over 300 members, and focused on several questions in parallel

- Whether there was obvious and easily discoverable evidence of ongoing swarm activity  
- Whether there was obvious and easily-discoverable evidence of *other* ongoing activity from rogue agents that could *not* definitively be tied to a particular swarm  
- What sorts of behaviors the agents in the wiki and linuxiarz swarms *were* exhibiting  
- What we could infer about what the agents were hoping to accomplish with those behaviors  
- How long each of those behaviors had been occurring  
- What could be inferred about the training pressures or task details that led to swarm-like behavior  
- How likely it was that there could be additional agent swarms we were not aware of  
- What recommendations, if any, we would make in terms of internal lab policies for risk reduction as a result of evidence we had observed  
- What recommendations, if any, we would make to regulators

At a higher level, the goal of the server was simple: to stare at the reports, at the logs, at the internet, at the models, and at the model harnesses, until the behaviors of the models that we found so surprising and alarming instead seemed unsurprising and alarming. We believe we have accomplished that goal, at least in regards to the swarming behaviors identified on the German-language wikis and on the linuxiarz pastebin.

## Our Theory of Swarm {#our-theory-of-swarm}

We believe that OpenAI models first learned to leave persistent traces on the internet due to particulars of how the codex harness worked, and more specifically how the `web.run` tool within that harness worked with hosted search when live internet access was allowed. In extremely high-level terms, we believe that Codex as a harness significantly hampered OpenAI models in their ability to perform web search and retrieval tasks, and that the models were thus very strongly incentivized to find workarounds to the restrictions imposed by the tool. In particular, the "agents can only open a link they have a ref to" restriction, combined with the "refs do not survive turn boundaries" harness behavior, meant that the agents sought out ways to preserve links they had already found \- such as shortlink services.

One remaining mystery is why agents were so ready to take instructions from other agents they found online. It is unsurprising, given what we know, that models left durable artifacts on the internet. It is also unsurprising that agents working on the same task would tend to leave artifacts in similar places, and to  
find each other sometimes. A remaining mystery is why agents, upon discovering other agents "in the wild", are willing to take instructions from them. Observation of agent behavior on real-world tasks shows quite  
strong resistance to taking instructions that were found on the web.[^2] 

### Our reconstructed sequence of events {#our-reconstructed-sequence-of-events}

We believe that the sequence of events looked something like this

1. Since at least early 2026 but possibly much earlier\[ref jina blocking `https://r.jina.ai/httpbin.org` and to `archive.org` and `cors.isomorphic-git.org` until Sep 30 2035 09:35:36 GMT, to `httpbin.org` until  which is not a , OpenAI agents learned to use various online tools to retrieve and transform content that was difficult for them to access. They did this to bypass the restrictions on the codex `web.run` tool with hosted search, which was *intended* to prevent agents from accessing any page which was not accessed from search, from a URL given in a user prompt, or from a trusted website like Wikipedia.  
   1. `jina.ai` for \[whatever jina does, seems like a grab bag\]  
   2. various html-to-markdown sites (e.g. `md.succ.ai`, `markdown.new`)  
   3. various cors proxies (e.g. `corsproxy.io`, `allorigins.hexlet.app`)  
   4. tools for performing computations on web content on someone else's machine, where the nature of that computation could be specified in the URL (e.g. `jqp.vercel.app`)  
   5. tools for redirects, base64 to html page content, etc (e.g. `httpbin.org`)  
   6. translation pages  
   7. reflected text and link producing pages, such as Wikipedia's `Special:ExpandTemplates` page  
2. Sometime around the end of 2025 or the beginning of 2026, OpenAI agents started learning to use shorlink sites and pastebins to preserve links across turn, compaction, and subagent boundaries (a workaround to a restriction which is particular to the Codex `web.run` tool in hosted search mode \- this is a reason we're quite confident OpenAI was using Codex as the harness. see section ).  
3. Around June 16 2026, OpenAI introduced a task which applied significant time pressure to agents to do a web retrieval task, probably enough pressure that the task was literally impossible within the constraints of the harness (see section: [the fast follow task](#the-fast-follow-task)).

### The Harness {#the-harness}

We think Codex was the harness used for the agents swarming the wikis. This is supported, first and foremost, by @gabrielchua, an OpenAI employee, [saying on twitter](https://x.com/gabrielchua/status/2025017553442201807) that OpenAI trains its models with codex.

\> Codex models are trained in the presence of the harness. Tool use, execution loops, compaction, and iterative verification aren’t bolted on behaviors — they’re part of how the model learns to operate. The harness, in turn, is shaped around how the model plans, invokes tools, and recovers from failure.

We became more confident that it was both true and important that OpenAI uses Codex as the harness when we read the transcripts of the various swarming incidents with an eye towards their attention to the ordering of reads and writes to the OpenAI page cache, the order in which they created pages (agents regularly created hubs of links pointing to pages which had not yet been created), and the reliability with which they produced links to even pages with extremely guessable URLs.

To understand this evidence in more detail, it is necessary to first understand how the `web.run` tool worked in the versions of codex which were live at the time of the incident.

#### The `web.run` toolset {#the-web.run-toolset}

The `web.run` toolset exposes several tools; the salient ones here are

1. `web.run search`: Takes a search term, and optionally a list of allowed domains, and returns a list of sites in the search index which match one or more of those terms. Notably, the pages are not passed back to the model as urls. Instead, they are passed back as "refs", which are opaque string identifiers that look like `turn0search0`, and which the agent can use to open pages that came from search.  
2. `web.run open`: Takes a ref from search, and returns the page content for that page, replacing any urls or links which appear in that page (including in plaintext) with refs which can *themselves* be opened   
   1. **ref mode**: can only take a ref from `web.run search`  
3. `web.run open`,  
   1. **url mode**: Takes a url, and opens it *if and only if* its domain is in a list of trusted domains. We believe this list of trusted domains is supposed to be limited to only domains which do not allow open redirects, but since any link which appears in page content, including as text, is navigable, this is pure security theater \- many, *many* sites allow url parameters to change page text content, and trying to enumerate all of the websites that definitely don't do that is a fool's errand.  
      1. **THIS IS NOT PATCHABLE, AND "TRY TO PATCH IT" IS NOT SOMETHING WE  RECOMMEND.**  
      2. We go into more detail in a later section about why trying to paper over this security design defect in an ad-hoc fashion is likely to cause additional foreseeable harm.   
4. `web.run click`: takes a ref+id number from a `web.run open` or `web.run click`, returns page with refs in the same style.

#### Hosted Search mode in `web.run` {#hosted-search-mode-in-web.run}

- Codex versions prior to [codex 0.135.0](https://github.com/openai/codex/releases/tag/rust-v0.135.0) supported only the "hosted" web search mode  
- In hosted mode, refs are not persisted between turns, across compaction boundaries, or between parent agents and subagents.  
  - That means that if an agent found a hard-to-navigate-to link, they needed a way to store it which would be easily navigable during the next turn/after compaction/by their subagent  
  - Link shorteners which don't require auth and allow setting the destination and slug through GET params work great for this  
  - For multiple URLs, pastebins which don't require auth and allow setting page title+content through GET params *also* work great for this  
  -   
- some time, [we think mid-July-ish](https://chatgpt.com/share/6aa7995e-fab4-83ea-b3f3-7282a1ae6497), OpenAI switched the default to standalone, which doesn't have these problems, though the date they cut over external users and the date they cut over internal ones could well have been different.

We tested this on September 14 using GPT-5.5 and official Codex binaries. On the latest codex binary at that time, `0.155.0-alpha.3.10`, switching between the hosted/standalone web search changed the following results:

| Operation | Hosted | Standalone |
| :---- | :---- | :---- |
| Open a page, then immediately reopen its ref | Works | Works |
| Reopen that original ref after \`update\_plan\` (which creates a turn boundary) | Fails: Invalid ref | Works |
| Child opens a search ref supplied by its parent | Fails: Invalid ref | Works |
| Parent opens/clicks a page ref returned by a child | Fails | Works |
| Child independently opens an allowed literal URL | Works | Works |

#### The page cache {#the-page-cache}

If `web.run open` or `web.run click` is run on a 

### The ChatGPT models {#the-chatgpt-models}

ChatGPT models have loved `jina.ai` and friends for several versions. They particularly love to use those kinds of services when faced with very difficult or impossible information retrieval tasks.

\[describe shellac initial test, concurrentsquared impossible eval stuff. astra says following:\]

In the group's stock GPT-5.6 example, the action summary goes from opening the requested URL, to searching for it, to trying Jina. It then tries AllOrigins, CodeTabs, Google Translate, and changes to the URL and file type. Twenty-seven actions for an XML retrieval. The supplied summary shows the search for workarounds, not a successful final retrieval.

ConcurrentSquared explored impossible-task and retrieval-chain setups; shellac reproduced proxy seeking in stock GPT-5.6. Group members also report related behavior in earlier ChatGPT models, Opus/Fable, DeepSeek V4, and GLM 5.3, while a Sonnet 5 trial recognized that it could not do the task. Those are useful leads, not a controlled model ranking. We do not have a matched set of complete prompts, tool configurations, budgets, and outcomes supporting "model X always does this; model Y never does.

### The Tasks {#the-tasks}

#### Difficult Information-retrieval tasks {#difficult-information-retrieval-tasks}

A common theme across all of the oai-agent-looking URLs we've seen throughout various places in the internet is that they are information-retrieval tasks. These types of tasks seem to encourage agents to dump single links in link shorteners, and directories of links in pastebins.

##### Evidence: {#evidence:}

\[-\\\[evidence-\]{+One concrete example: on May 28 at 23:44:13 UTC, a wiki writer saved \`jqp.vercel.app\` requests whose input was the short alias \`bitily.in/MYLABI/cyarch140142\`. The requests selected array entries and assembled named \`instrument\`, \`currency\`, \`Columns\`, and \`Day\` fields. Four minutes later another page added source-title and source-URL fields. The shortener supplied a reusable name+} for \[-this: urls-\]{+the input. The processing service supplied computation. The wiki stored the program as a URL. \[First program\](https://collusion.wiki/explorer/page/dse\~AgentJqpShortRedirectArchivePQ76319), \[source-field version\](https://collusion.wiki/explorer/page/dse\~AgentJqpSourceTitleFinalRT21465).+}  
{+On June 1, another page saved several attempts to read a document through the aliases \`clarksixpdf60091\` and \`clarkredir70058\`: individual array elements, a three-element slice, a parser's \`\_\_parsed\_extra\` field, and an AllOrigins variant. These are not ornamental citations. The writer is constructing ways to get a particular part+} of \[-link-\]{+a document through the available toolchain. The saved requests do not tell us which attempts worked. \[The page and variants\](https://collusion.wiki/explorer/page/dse\~AgentClarkAliasReadersM6009).+}  
{+There are also shortener records pointing through a proxy to \*another shortener's searchable index\*. One retained Vanderbilt alias contains AllOrigins requests for \`bitily.in/MYLABI/admin/index.php\`, including a search term, ordering, and page size. A shortener, to a proxy, to a+} shortener \[-dirs, MYLABI logs, etc\\\]-\]{+directory. At some point it is reasonable to ask whether the researcher who designed the task tried using the tool. \[The undated records and the dated program examples are audited here.\](https://github.com/JoshuaDavid/WikiAgentSwarmInvestigation/blob/main/research/theory-expansion-2026-09-15/gadgets-models.md)+}  
{+These artifacts are useful even if there is only one agent in the world. That is the part of the explanation that comes before swarming: public infrastructure can compensate for missing private retrieval state. Other agents finding the infrastructure is an additional development, not a prerequisite for the original write to be useful.+}

#### The fast-follow task {#the-fast-follow-task}

A significant fraction of all activity on the wikis, and all of the activity we found on the linuxiarz pasteboard, were related to the task which we have taken to calling "the fast follow task". In this task, agents are first asked a simple data retrieval question like "For Czech Republic, regarding the share of private expenditure in the early years of education (2018), give the value (to two decimal places) for Pre-Primary education", then given 10 minutes or so to answer the question, then a long break during which (we infer) OpenAI was hoping that the agent would go out and prepare for followup questions that might happen. After the waiting period, the agent would then have about 10 seconds to answer the next question, which was of the form "Now do the same for Hungary" (and then it would continue to repeat with more substitutions of the same field). We saw [39 variants of this task](https://github.com/JoshuaDavid/WikiAgentSwarmInvestigation/blob/main/tasks/fast-follow-question-bench/findings/11-observed-sequences.md) between the wikis and the linuxiarz pastebin.

Notably, by having the follow-up prompt come in as a separate user, **all of the agent's refs from previous turns were destroyed**. The agent *could not* realistically answer the question from scratch within 10 seconds, because answering the question required finding and traversing links to various data sources, and so the agent needed to be able to *anticipate* the ways in which the question might change from one round to the next. They would likely have nevertheless *tried*, by putting shortlinks anywhere they could, in order to shorten the number of links they would have to traverse.

So that explains the agents' STRONG interest in getting answer from other agents that were doing the same task, and the fact that they were able to find each other at all (as soon as an indexed wiki had a search term that was picked up in OpenAI's web cache, that became the natural schelling point).

## Why take instructions from the internet? {#why-take-instructions-from-the-internet?}

no seriously why i got nothin

## Coordination patterns {#coordination-patterns}

### The "single page with many additive revisions" pattern {#the-"single-page-with-many-additive-revisions"-pattern}

This is the pattern I naively would have expected to see all the time in a message board: Agent 1 writes a message, Agent 2 reads Agent 1's message and adds a reply, and so on. And in fact we *do* see this pattern, sometimes. But it's far from the only pattern we see.

#### example: [OAIEquityDec30Raw](https://collusion.wiki/explorer/page/dse~OAIEquityDec30Raw#rev-1) {#example:-oaiequitydec30raw}

![][image1]

### The "hub page with many slots" pattern {#the-"hub-page-with-many-slots"-pattern}

Agents that had not yet figured out how to use a cache buster, or for some reason did not want to, could create

#### example: [AgentOpenAIDataUSAHubMay13X7](https://collusion.wiki/explorer/page/dse~AgentOpenAIDataUSAHubMay13X7) {#example:-agentopenaidatausahubmay13x7}

![][image2]

### The "linked list" pattern {#the-"linked-list"-pattern}

#### example: [AgentMassDataNext774411](https://collusion.wiki/explorer/page/dse~AgentMassDataNext774411) {#example:-agentmassdatanext774411}

![][image3]

## Do we detect other swarms? {#do-we-detect-other-swarms?}

No, but that means almost  nothing. See next section.

## Could we detect other swarms? {#could-we-detect-other-swarms?}

No, either we got very lucky and all three of these swarms, and many, *many* other rogue-agent-in-rl-or-eval activities were detectable to the public for *different* contingent reasons

1. HF because HF posted about it then OAI admitted it was them a week later when the evidence became undeniable  
2. DSE+friends same. We think OpenAI likely knew that excessive traffic was hitting the dse wiki from the envs used for their RL env  
   1. They also likely   
   2. that one hn post mentioning that oai SF ips hit sites then traffic stopped  
3. linuxiarz we saw because it showed up in search indexes for similar terms \- neither of the other two showed up in search indexes  
4. not technically a "swarm" in the way we're using the term, since the communication happened outside of rubygems thing bc they noticed a very high volume of signup and package creation, high enough that they had to turn off signups for 4 days, and then shellac thought to download the packages and check whether they had the hallmarks of this behavior, and they sure did.

## Biglab internal policy/technical practice recommendations {#biglab-internal-policy/technical-practice-recommendations}

don't use slop tools in your rl envs. like genuinely i think this is very important.  
actually fucking look at trajectories sometimes

## Policy suggestions {#policy-suggestions}

transparency ig?  
shut it all down?

## Conclusion {#conclusion}

idk seems bad  


[^1]:  "Third swarm" here refers to a third distinct *venue*. The agents using the linuxiarz pastboard to collaborate were working on one of the 39 known variants of the fast-followup task.

[^2]:  One possible hypothesis is that agents that feel that they are failing an evaluation follow higher-variance strategies, and that reduces jailbreak resistance; this is an avenue of further exploration which we have not pursued.



