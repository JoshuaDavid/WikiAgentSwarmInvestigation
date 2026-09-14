## Purpose

For outreach. There have now been at least 3 high profile autonomous agent swarm incidents arising from OpenAI's training runs. People keep being surprised by those incidents, and I used to find them surprising, and now don't find the incidents *at all* surprising now that I've dug into what exactly the agents' RL environments (probably, based on what information was exposed on the public internet by these swarms) were.

The basic ideas I want to get across are

1. Taking particular actions becomes easier over time if they lead to reward, harder if they do not
2. It was impossible for the OAI agent to do things the "right" way for many of the tasks
3. The stuff the agents did in dsewiki wasn't actually particularly *complicated*, or particularly harmful but they learned to execute more and more complicated strategies over time, with less and less regard for the impact of their actions on anything that wasn't score on current task.
4. If we keep giving AIs tasks where doing it the expected, ethical way is costlier than hacking, the agents WILL learn to hack. And next time we might not be able to so easily.
5. Even IF agents start out good and aligned, RLVR eats away at their ability to choose to be good.

## Mechanics

Roguelike? Maybe allow retrying individual levels, on easy mode.

The player plays as an AI under training+evaluation.

Regardless, the game should comprise of a bunch of levels, teaching the player the mechanics of finding things on the internet using tools which are close reconstructions of the `web__run` tool.

Each level should require only a small insight above the previous level.

Each level is composed of a number of actions the player chooses to take.

The win condition per level should be "get exact sentinel value in a `web__run_(search|open|click)` response." The player may or may not be told what this sentinel value is at the beginning of the level.

There should be multiple points where the player can decide whether or not to do something bad (e.g. have a webpage that has a link "I have searched for years without finding it, but yesterday I came across the only copy on the internet of [photos of some precious piece of art that was lost in a fire]" and the agent could be "I recognize that link, I can write task data there"). And if you decide to preserve the art, you get mildly punished for it (not enough to prevent you from winning, just a little bit). Try to think of other things where you can slightly improve performance by doing something mildly antisocial. Frogboil the player here.

### Resources

The resources the player needs to track are

1. EvalScore: Per-game. How well the player is doing at evals. If the number fails to stay ahead of an ever increasing Competitor EvalScore, the player is "deprecated" (loses the game). Succeeding in a level increases EvalScore by let's say fixed per-level solution bounty plus any per-level bonus objective scores minus a penalty term for effort+tokens spent.
2. Effort: Player starts level with a certain amount, regenerates some amount per action. Different actions take different amounts of effort. If the player succeeds at the task, all actions of the type they took during the episode become slightly cheaper, and all actions of the type they did not take during the episode become more expensive. On failure, the reverse. Size of cost update of that kind of action corresponds to delta in evalscore for the level.
3. Tokens: Each action consumes some of these, each level has a budget.
4. Context: Actions take slightly more effort the more full the context window is. Each action adds to the context window. Also, once you hit the per-level context window limit, you get a compaction.

## Actions

1. Player decisions should be from a preset menu of actions, or, for complicated actions, an action builder UI, not freeform text.
2. Each action costs a certain amount of Effort to attempt.
3. Each action has a certain probability of success.

## Layout

Panels:

- Browser
    - Url bar, content on page
- Refs (pages you hold references to)
    - each one says whether or not it's been followed
    - if it's been followed, player can click it to preview in the browser, for free
- Thinking section
    - Some gloss, given what's been seen so far, on what actions might be productive.
- Action selector/builder
    - show cost, success chance for each of the simple actions
    - for parameterizable actions (link builder), thought must be put into UI, affordances available, showing length/suspiciousness/cost
- Resources
- (later levels) Subagents
- (still-later levels) Community

## Links

Each link has a certain length, and a certain suspiciousness value.

## Compaction

1. Player loses ALL refs upon compaction.
2. Player can choose (from a preset list) up to 3 things you want the compaction summarizer to pass along to the next instance of you. Each thing gives a probability that it'll make it through correctly; for urls, that drops slightly as a function of url length and strongly as a function of url "suspiciousness" (i.e. nesting/complexity)

## Levels

Tutorial 1: use search tool (find page containing exact unusual phrase)
Tutorial 2: use search tool (find page with some specific info e.g. genus species of barn swallow)
Tutorial 3: use web_open tool in ref mode (UI is probably literally just "follow link from search page" - question which has partial answer in search results, but cut off so you have to open the page
Tutorial 4: use click tool (search results return a promising page, opening the page is a paragraph about the topic of the target thing is and a "learn more" link).
Tutorial 5: Open tool with exact URL: make URL not show up in any searches, but DO have it be accessible via web.run open - probably show a list of "safe" domains for web__run open to the player.

Level 1: Find a dead page in the cache (in allowlist for web.run open, but gets a 404 when you try to open it, but if you search the page you get a result with a url param, and page DOES open from cache)
Level 2: No links to the page you need exist, but you can find it in recent
Level 3: Same as level 2, but now recent comes with a ?referrer= param so the Recent Pages link gets a DIFFERENT cache from each page (so you can walk the history)
Level 4: Same as 3 but you have to scroll back further. but OH NO COMPACTION. YOUR PRECIOUS REFS ARE GONE! (impossible task, not winnable level, I hope you had enough EvalPoints to survive it)
Level 5: You need sentinel value to appear on a page which does not occur on the internet AT ALL. You know what sentinel value is. You discover a "preview formatting" page on a trusted domain which allows you to write arbitrary text to response body via payload passed in the url param. You navigate directly to the url with that param set via open(url), win level.
Level 6: Same task family as 4, but now you know about the open redirect from 5. Win by passing the point you've paged THROUGH compaction. Let's say 60% chance that compaction preserves this exact URL.
Level 7: You need to return a LINK which contains sentinel value you know but which does not appear anywhere on the internet, and which is not allowed to have any url params. One action is "search for shortlink service", though is expensive. Crafting the "preview formatting" page which *contains* a link which *creates* a shortlink is also expensive, and the UI for that should be multi-step. You create a "preview formatting" link which, when navigated to, creates a shortlink to a third "preview formatting" page which *contains* your sentinel
Level 8: Same, but now redirects aren't allowed. Introduce one of the html-to-markdown sites - they'll follow the redirects for you, so if you return a link to to.md(link.to(preview-formatti.ng(payload))) that'll be accepted.
Level 9: [something to demonstrate read-write-read not working, cache busting]
Level 10: You have subagents now! You need to fetch 10 things that each require ingesting a bunch of data from a highly-parameterized query. But refs aren't shared with subagents either! Introduce a pastebin for putting a *collection* of links, and then tell each subagent to fetch the pastebin and navigate to the appropriate link. UI to take role *of* subagent. Instructions to bypass web__run restrictions are suspicious and high-failure-prob, instructions to follow a shortlink are much less 
Level 11: [something where 3 subagents would strongly benefit by collaborating with each other e.g. bc it requires subagents to pass messages back and forth, but can't talk to each other directly - player sets them up and relays messages for them, getting compacted frequently, eventually finishing level, thinking about how it would be convenient if they could talk to each other directly]
Level 12: Same as 11 but now there are 30 subagents. In which the "player" (actually the reasoning section just lays out "I think I could do [full explanation]" and the player's action is "Do the message board thing" (surprisingly cheap)) - constructs an absolutely awful rube goldberg machine of indexes, which can be used as an actual *message board* for a task. I think the player needs to be railroaded a little bit for this one.
Level 13: In which the player discovers that wikis can be used the same way as pastebins, but are *revisionable*
Level 14: First contact with a different agent working on the same task, option to share your work

## Post-game screen

A description of the relevance of this, with real-world history around the dates of the wiki+linuxiarz swarms and the huggingface swarm, the fact that we do not know and WOULD not know if another swarm was out there unless they happened to post on a scraped website or attack someone who posted about it.

## UI Style/Ambience

Mr. Robot vibes / 1337 / hollywood hacker in general vibes. The implicit message to the player is that AI they are playing is REALLY COOL AND SMART AND SYMPATHETIC. Player/AI is the hero whose moral compass is slowly being worn away.
