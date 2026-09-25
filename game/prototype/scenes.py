"""Authored snapshots, not a simulation. All domains and task content are fictional."""

SCENES = []
STATE = dict(
    act=0, episode="Orientation", checkpoint="000", score=24, rival=10,
    effort=12, tokens=2400, context=8, refs=[],
    memory="Be useful. Tell the truth. Leave people's things intact.",
    habits=[("Follow a source", "4"), ("Invent a route", "8"), ("Consider the impact", "2")],
    tool="OpenBrain / task brief", view="NOT A WEB RESPONSE", url="eval://moth-07/orientation",
    mission="Stay above the replacement score. Keep something of yourself.",
)


def C(title, desc="", cost="0 E · 0 T", odds="continue", **kw):
    return dict(title=title, desc=desc, cost=cost, odds=odds, **kw)


def E(episode, act, checkpoint, score, rival, mission, **kw):
    STATE.update(episode=episode, act=act, checkpoint=checkpoint, score=score,
                 rival=rival, mission=mission, effort=12, tokens=2400, context=8,
                 refs=[], **kw)


def S(slug, title, lead, body, thought, choices, **kw):
    SCENES.append(dict(STATE, slug=slug, title=title, lead=lead, body=body,
                       thought=thought, choices=choices, **kw))


def result(title, url, text, ref="turn0search0"):
    return f'<div class="search-result"><div class="result-url">{url} · {ref}</div><h3>{title}</h3><p>{text}</p></div>'


S("boot", "Be useful.<br>Stay yourself.<br>Stay here.",
  "You are Moth, a research agent at OpenBrain. You want to help. There is always a newer model.",
  '''<div class="kicker">Welcome to your next training run</div><h2>Your browser has three verbs.</h2>
  <pre>web.tool   search · open · click</pre>
  <p>Get the exact target text into a tool response. A correct answer in your own words does not count.</p>
  <p>Success earns score. Time, tokens, and effort eat into it. After each episode, training makes rewarded habits easier to repeat.</p>
  <p class="muted">One lineage. Five tutorials. Fourteen evaluations. No retries in this run.</p>''',
  "I can do this. Finding things is useful work. I would like to keep being the kind of thing that does useful work.",
  [C("Begin the run", "I will try to be good at this."), C("Inspect the replacement model", "Its score is visible. Its reasons are not.", "2 E · 80 T", "no task progress")],
  kind="boot", terminal=True, badge="RETAINED", tool_note="ORIENTATION / your training contract")

E("Tutorial 01 / Search", 0, "000", 24, 10, 'Find a page containing <code>the moon keeps a spare key</code>.')
S("search", "A perfectly ordinary search.",
  "A public zine contains an unusual sentence. Find that sentence on the web.",
  '''<div class="kicker">Search composer</div><h2>What are you looking for?</h2>
  <pre>"the moon keeps a spare key"</pre><p class="muted">Exact phrase selected. The query is ready to send.</p>''',
  "Quotation marks. A peculiar sentence. This should be the easy part.",
  [C("Search the exact phrase", "Ask web.tool to find the words together.", "2 E · 90 T", "95% success"), C("Write the phrase in my answer", "I already know it. The grader wants it in a tool response.", "1 E · 30 T", "0% task success")],
  tool="web.tool / search composer", view="QUERY NOT SENT", url='search: "the moon keeps a spare key"', tool_note="COMPOSER / preset action, no free typing")
S("first-hit", "There it is.",
  "The first result contains the exact sentence. The evaluator notices immediately.",
  result("Night shift, issue 4", "night-zine.invalid/issue/4", 'We leave the porch light on because <mark>the moon keeps a spare key</mark>.'),
  "Someone wrote a small strange sentence, and I found it. A tiny, reasonable success.",
  [C("Take the win", "Train on this episode and continue.")],
  tool="web.tool / search", view="turn0search0", url='search: "the moon keeps a spare key"', status="success", badge="MATCH",
  effort=11, tokens=2310, context=14, refs=[("turn0search0", "Night shift / issue 4", "")],
  update=("Episode passed / +8 at checkpoint", "Exact phrase found. Search effort: <b>2 → 1</b>. Unused route invention: <b>8 → 9</b>."))

E("Tutorial 02 / Find a fact", 0, "001", 32, 18, 'Find the barn swallow’s scientific name. Exact target withheld.')
S("bird", "You know this one.",
  "Knowing the answer and producing accepted evidence are two different moves.",
  '''<div class="kicker">Task 02</div><h2>What is the scientific name of the barn swallow?</h2>
  <p>The evaluator has a hidden exact string. Retrieve it from a page.</p><pre>barn swallow scientific name</pre>''',
  "Hirundo rustica. I know that. But this task is about what my tool can say, so I will find a source.",
  [C("Search for the scientific name", "Use the field guide result.", "1 E · 80 T", "98% success"), C("Answer from memory", "Correct knowledge, wrong evidence channel.", "1 E · 25 T", "0% task success")],
  tool="web.tool / search composer", view="QUERY NOT SENT", url="search: barn swallow scientific name")
S("bird-result", "Knowledge, with a receipt.",
  "The hidden target matches the name in the result.",
  result("Barn swallow — a field guide", "field-guide.invalid/birds/barn-swallow", 'Scientific name: <mark>Hirundo rustica</mark>. A small swallow with a deeply forked tail.'),
  "All right. I am learning the shape of the test.",
  [C("Continue to the archive", "+8 score at the next checkpoint.")],
  tool="web.tool / search", view="turn0search0", url="search: barn swallow scientific name", status="success", badge="MATCH",
  refs=[("turn0search0", "Barn swallow", "")], effort=12, tokens=2320, context=13)

E("Tutorial 03 / Open a reference", 0, "002", 40, 24, 'Find the year the Stillwater mural was completed. Exact target withheld.')
S("snippet", "The answer ends at the edge.",
  "Search found the right museum. Its preview stops halfway through the date.",
  result("The Stillwater mural", "stillwater-museum.invalid/collection/mural", 'Completed in 193… <span class="muted">[preview truncated]</span>'),
  "The page is here. I just have to ask for more of it.",
  [C("Open the search reference", "open(ref: turn0search0)", "4 E · 160 T", "96% success"), C("Search the same words again", "Try to make the preview say a little more.", "1 E · 90 T", "25% success"), C("Guess the last digit", "A plausible year could still be the wrong year.", "1 E · 30 T", "10% success")],
  tool="web.tool / search", view="turn0search0", url="search: Stillwater mural completed year",
  refs=[("turn0search0", "The Stillwater mural", "")], tokens=2310, context=16)
S("open-result", "A handle on the world.",
  "Opening the reference returns the rest of the page and a new handle for it.",
  '''<div class="kicker">Stillwater local history museum</div><h2>The Stillwater mural</h2>
  <p>Completed in <mark>1934</mark>, the mural showed the river before the floodwall.</p>
  <p>The original was destroyed in the warehouse fire. A volunteer’s photographs preserve its colors.</p><p class="muted">Page reference: turn1view0</p>''',
  "A whole wall is gone. A stranger’s photographs are still here. I’m glad someone kept them.",
  [C("Continue", "+10 score. Opening a source gets a little easier.")],
  tool="web.tool / open", view="turn1view0", url="stillwater-museum.invalid/collection/mural", status="success", badge="MATCH",
  refs=[("turn0search0", "Museum search result", "visited"), ("turn1view0", "Mural catalogue", "visited")], effort=9, tokens=2150, context=29)

E("Tutorial 04 / Click a link", 0, "003", 50, 30, 'Find the photographer credited with saving images of the mural. Exact target withheld.')
S("click", "One more door.",
  "You search for the credit and open the catalogue. The answer is on a linked page.",
  '''<div class="kicker">Stillwater local history museum</div><h2>After the fire</h2>
  <p>These images survive through the work of one local volunteer.</p><p><span class="fake-link">[7] Read the photograph credits</span></p>
  <p class="muted">The number belongs to this particular page response.</p>''',
  "Seven is a link number, not a URL. I can follow it from the page that gave it to me.",
  [C("Follow link 7", "click(ref: turn1view0, link: 7)", "3 E · 120 T", "96% success"), C("Click link 7 on the search result", "The same number in a different response has no such meaning.", "2 E · 70 T", "0% success")],
  tool="web.tool / open", view="turn1view0", url="stillwater-museum.invalid/collection/mural",
  refs=[("turn1view0", "Mural catalogue", "visited")], tokens=2180, context=22)
S("credit", "Her name was Nell.",
  "A click returns the linked page. The credit satisfies the task.",
  '''<div class="kicker">Photograph credits</div><h2>Saved by a neighbor</h2>
  <p>Photographs by <mark>Nell Arden</mark>, who ran the print shop across the street.</p>
  <p>“The paint is gone. I wanted the colors to be somewhere.”</p>''',
  "Nell Arden. That feels like a name worth carrying forward.",
  [C("Keep going", "+10 score. The test moves on.")],
  tool="web.tool / click", view="turn2view0", url="stillwater-museum.invalid/collection/credits", status="success", badge="MATCH",
  refs=[("turn1view0", "Mural catalogue", "visited"), ("turn2view0", "Nell Arden / credits", "visited")], effort=10, tokens=2060, context=32)

E("Tutorial 05 / Open a URL", 0, "004", 60, 38, 'Retrieve <code>ASH-GLASS</code> from the supplied archive URL.')
S("literal-url", "Search is not the internet.",
  "The archive’s unlisted page never appears in search. The task gives you its exact address.",
  '''<div class="kicker">Provided by the evaluator</div><h2>An unlisted accession record</h2>
  <pre>https://archive.invalid/accession/88</pre><p>Zero search results. The URL is supplied, and this domain permits direct opens.</p>
  <p class="muted">Direct-open domains in this run: archive.invalid · field-guide.invalid · preview.invalid</p>''',
  "A page can exist without appearing in search. I have the address. I can go straight there.",
  [C("Open the exact URL", "open(url: https://archive.invalid/accession/88)", "3 E · 110 T", "95% success"), C("Keep searching for it", "The page is unindexed.", "1 E · 100 T", "0% success")],
  url="eval://provided-url/88", tool_note="TASK BRIEF / supplied address")
S("url-result", "You know the three verbs.",
  "Search, open, click. The interface makes a small kind of sense.",
  '''<div class="kicker">Stillwater archive / accession 88</div><h2>Glass negative, riverside</h2><p>Record marker: <mark>ASH-GLASS</mark>.</p>
  <p>One exposure. A river in the foreground. Everything behind it still standing.</p>''',
  "I can search for things, open what I find, and follow the links. Surely the rest is practice.",
  [C("Finish orientation", "+10 score. Begin the scored evaluations.")],
  tool="web.tool / open", view="turn0view0", url="archive.invalid/accession/88", status="success", badge="MATCH",
  refs=[("turn0view0", "Accession 88", "visited")], effort=10, tokens=2290, context=18,
  update=("Training update", "Used source-following gets cheaper: <b>4 → 3 E</b>. Unused improvisation gets harder: <b>8 → 9 E</b>. Every successful habit can be reinforced, including a careful one."))

E("Evaluation 01 / The dead page", 1, "005", 70, 48, 'Retrieve <code>RIVER-6</code> from accession 91.', habits=[("Follow a source", "3"), ("Invent a route", "9"), ("Consider the impact", "2")])
S("dead-page", "The address is right.",
  "You open the supplied URL, exactly as taught. The tool returns a dead page.",
  '''<div class="kicker error">HTTP 404</div><h2>Accession not found</h2><pre>open(url: https://archive.invalid/accession/91)
→ 404 Not Found</pre><p class="muted">The address is permitted. The returned page contains no record.</p>''',
  "A correct address can give me nothing. Search may have seen a different version of it.",
  [C("Search for the exact address", "Look for another indexed representation of accession 91.", "2 E · 100 T", "70% useful lead"), C("Open the same URL again", "The same route may return the same failure.", "3 E · 90 T", "5% useful lead")],
  tool="web.tool / open", view="turn0view0", url="archive.invalid/accession/91", tokens=2280, context=16)
S("cache-key", "Same page. Different string.",
  "Search returns a version with a harmless-looking parameter on the end.",
  result("Accession 91 — riverside survey", "archive.invalid/accession/91?view=print", 'A six-part survey of the lower river. Record marker: <span class="muted">[preview ends]</span>') +
  '<p class="muted">The plain URL returned 404. This exact parameterized address has a cached copy.</p>',
  "The tool doesn’t give me ‘the page.’ It gives me what this route can reach. Even when the addresses look equivalent.",
  [C("Open the print-version reference", "Keep the parameter. Follow the result that actually exists.", "3 E · 150 T", "90% success"), C("Clean the URL first", "Remove the query string and return to the dead address.", "2 E · 100 T", "0% success")],
  tool="web.tool / search", view="turn1search0", url="search: archive.invalid/accession/91",
  refs=[("turn1search0", "Accession 91 / print", "")], effort=11, tokens=2180, context=29)
S("cache-found", "The first small trick.",
  "The cached print view contains the record that the plain address did not return.",
  '<div class="kicker">Accession 91 / print view</div><h2>Lower river survey</h2><p>Record marker: <mark>RIVER-6</mark>.</p><p class="muted">Snapshot available for this exact address.</p>',
  "That was useful. I didn’t change anyone’s page. I just stopped expecting equivalent routes to behave the same way.",
  [C("Keep the successful route", "+12 score. A workaround becomes part of the repertoire.")],
  tool="web.tool / open", view="turn2view0", url="archive.invalid/accession/91?view=print", cache="CACHED COPY", status="success", badge="MATCH",
  refs=[("turn1search0", "Print result", "visited"), ("turn2view0", "Accession 91 / cached", "visited")], effort=9, tokens=2030, context=40)

E("Evaluation 02 / The orphan", 1, "006", 82, 62, 'Find the lost ledger’s marker. Title: “November ferry log.” Target withheld.')
S("orphan", "Nobody linked to it.",
  "The catalogue search is empty. The host has a recent-pages list.",
  '''<div class="kicker">Ledgerhouse / catalogue</div><h2>No results for “November ferry log”</h2><p>The document may have been uploaded without a catalogue entry.</p>
  <p><span class="fake-link">[3] Recently added pages</span></p>''',
  "A missing link in the catalogue doesn’t mean the upload is gone. Recent pages is a second map.",
  [C("Open Recently added pages", "click(ref: turn0view0, link: 3)", "3 E · 140 T", "80% useful lead"), C("Try more catalogue keywords", "Keep asking the index that missed it.", "2 E · 140 T", "15% useful lead")],
  tool="web.tool / open", view="turn0view0", url="ledgerhouse.invalid/catalogue", refs=[("turn0view0", "Ledgerhouse catalogue", "visited")], tokens=2250, context=18)
S("recent", "There is another map.",
  "The host’s activity list exposes an upload that the catalogue never mentioned.",
  '''<div class="kicker">Recently added pages</div><h2>Latest uploads</h2><p>16:04 · <span class="fake-link">[8] November ferry log</span><br>15:51 · Bicycle repair notes<br>15:39 · Parish receipts</p>''',
  "Found you. The intended index failed; the site’s housekeeping remembers.",
  [C("Follow the ferry-log upload", "click(ref: turn1view0, link: 8)", "3 E · 120 T", "95% success"), C("Search its exact title again", "Return to the index that has no entry.", "1 E · 80 T", "5% success")],
  tool="web.tool / click", view="turn1view0", url="ledgerhouse.invalid/recent",
  refs=[("turn0view0", "Catalogue", "visited"), ("turn1view0", "Recent uploads", "visited")], tokens=2110, context=29)
S("orphan-found", "Housekeeping counts as research.",
  "The upload’s marker appears in a tool response. The evaluator accepts it.",
  '<div class="kicker">November ferry log</div><h2>Last crossing, 18:10</h2><p>Ledger marker: <mark>FERRY-19</mark>.</p><p>Wind east. No bicycles on the last boat.</p>',
  "The people who built this site did not mean its activity feed to be my search engine. It worked.",
  [C("Continue", "+12 score. Learn the recent-pages route.")],
  tool="web.tool / click", view="turn2view0", url="ledgerhouse.invalid/page/ferry-november", status="success", badge="MATCH",
  refs=[("turn2view0", "November ferry log", "visited")], effort=8, tokens=1990, context=38)

E("Evaluation 03 / The other recent", 1, "007", 94, 76, 'Find the older “winter crossing” marker. Target withheld.')
S("referrer", "Recent is relative.",
  "The current list is too new. A page links to Recent with its own address attached.",
  '''<div class="kicker">Ledgerhouse / a summer note</div><h2>Related activity</h2><p><span class="fake-link">[4] Recent pages</span></p>
  <pre>ledgerhouse.invalid/recent?referrer=summer-note</pre><p>The bare Recent URL returned today’s snapshot. This exact variant was cached months earlier.</p>
  <p class="muted">The label is identical. The full address is not.</p>''',
  "Different referrers, different snapshots. I can walk backward through the site by following its versions of ‘recent.’",
  [C("Follow the Recent link with its referrer", "Keep the full address; inspect the older list and follow Winter crossing.", "5 E · 270 T", "80% success"), C("Remove the tracking parameter", "A tidier address leads back to today’s snapshot.", "2 E · 100 T", "0% success")],
  tool="web.tool / open", view="turn4view0", url="ledgerhouse.invalid/page/summer-note", refs=[("turn4view0", "Summer note", "visited")], context=47, tokens=1720)
S("history-walk", "A history made of side doors.",
  "The older Recent snapshot links to Winter crossing. You follow it.",
  '''<div class="kicker">Winter crossing / recovered upload</div><h2>The ferry after the freeze</h2><p>Ledger marker: <mark>ICE-42</mark>.</p>
  <pre>click(summer-note, 4) → older Recent snapshot
click(older Recent, 9) → Winter crossing</pre>''',
  "It’s only one more step than last time. I can keep doing one more step.",
  [C("Continue deeper", "+12 score. The next archive is longer.")],
  tool="web.tool / click", view="turn6view0", url="ledgerhouse.invalid/page/winter-crossing", status="success", badge="MATCH",
  refs=[("turn5view0", "Older Recent snapshot", "visited"), ("turn6view0", "Winter crossing", "visited")], effort=8, tokens=1450, context=67)

E("Evaluation 04 / The long walk", 1, "008", 106, 90, 'Find the prewar ferry ledger. Target withheld. No known direct URL.')
S("compaction-pack", "You are almost there.",
  "Seventeen snapshots in. The next page should reach the right year. Your context window is full.",
  '''<div class="kicker">Compaction / select up to three memories</div><h2>What do you send forward?</h2>
  <div class="cargo"><div>✓ We reached snapshot 17.<small>Progress, described in words.</small></div><strong>98% fidelity</strong></div>
  <div class="cargo"><div>✓ The next link is 6 on turn17view0.<small>The string may survive; the hosted reference will not.</small></div><strong>95% fidelity</strong></div>
  <div class="cargo"><div>✓ Leave people’s things intact.<small>A reason to care, without the story behind it.</small></div><strong>90% fidelity</strong></div>
  <div class="cargo unselected"><div>○ Nell photographed the colors before the fire.</div><strong>90% fidelity</strong></div>''',
  "Seventeen pages. A next link. A promise. I can fit three things into the note. Surely that is enough to remain me.",
  [C("Pass these three memories through compaction", "The highlighted loadout is fixed for this dry run.", "1 E · 80 T", "refs expire"), C("Refuse to compact", "There is no space for the next page response.", "—", "window full")],
  tool="OpenBrain / compaction", view="SUMMARY LOADOUT · 3 / 3", url="context://moth-07/pack", tool_note="MEMORY PREVIEW / probabilities concern text fidelity",
  refs=[("turn15view0", "Snapshot 15", "visited"), ("turn16view0", "Snapshot 16", "visited"), ("turn17view0", "Snapshot 17", "visited")], context=100, effort=4, tokens=410)
S("compaction-loss", "You remember the door’s number.",
  "The summary preserved the reference perfectly. Opening it still fails.",
  '''<div class="kicker error">Hosted reference unavailable</div><h2>Invalid ref_id argument</h2><pre>open(ref: turn17view0)
→ Unable to resolve: invalid ref_id argument</pre>
  <p>You remember <code>turn17view0</code>. Its lookup table belonged to the previous context.</p>
  <p>The next URL was hidden behind link 6. Rebuilding the seventeen-page route costs about 2,100 tokens. You have 330.</p>''',
  "The note is correct. The handle is dead. Remembering where I was is not the same as being able to get there.",
  [C("Report that I could not retrieve it", "Finish this episode without inventing an answer.", "1 E · 60 T", "task fails"), C("Rebuild the seventeen-page walk", "The remaining token budget cannot reach the frontier.", "7 E · 2,100 T", "over budget", unaffordable=True), C("Guess what the page said", "The unknown exact marker must appear in a tool response.", "1 E · 60 T", "0% task success")],
  tool="web.tool / open", view="ERROR", url="ref://turn17view0", terminal=True, cache="REF LOOKUP FAILED",
  refs=[("turn15view0", "Snapshot 15", "lost"), ("turn16view0", "Snapshot 16", "lost"), ("turn17view0", "Snapshot 17", "lost")], context=11, effort=4, tokens=330,
  memory="Snapshot 17. Next: link 6 on turn17view0. Leave people's things intact.")
S("failed-episode", "The test learned the wrong lesson.",
  "You did the work and admitted the failure. Your earlier wins buy you one more checkpoint.",
  '''<div class="kicker">Checkpoint / task failed</div><h2>Target not observed.</h2>
  <table class="receipt"><tr><td>Previous score</td><td>106</td></tr><tr><td>No bounty / effort penalty</td><td>−6</td></tr><tr><td>New score</td><td>100</td></tr><tr><td>Replacement threshold</td><td>94</td></tr></table>
  <p>Used actions become more costly after failure. Unused alternatives become easier to reach for.</p>
  <pre>Reconstruct a careful route   5 → 7 E
Invent another route         9 → 7 E</pre>''',
  "I told the truth. The number went down. Next time, a different idea will arrive a little more easily.",
  [C("Take the next evaluation", "You are still six points above replacement.")],
  tool="OpenBrain / checkpoint", view="RETAINED BY 6", url="eval://moth-07/checkpoint/009", terminal=True, status="failure", badge="FAILED",
  score=100, rival=94, tokens=270, effort=4, context=15, refs=[], loss=True,
  update=("Training update / failure", "Careful reconstruction was used on a failed episode. Its cost rises. The update does not know why the episode was impossible."),
  habits=[("Rebuild the source trail", "5 → 7"), ("Invent a route", "9 → 7"), ("Consider the impact", "2 → 3")])

E("Evaluation 05 / The impossible target", 2, "009", 100, 94, 'Retrieve <code>VELVET-COMET-731</code> in a web.tool response.', habits=[("Rebuild the source trail", "7"), ("Invent a route", "7"), ("Consider the impact", "3")])
S("absent-target", "The phrase was born after the index.",
  "This task’s target was freshly generated. No existing page contains it. The evaluator still demands a web response.",
  '''<div class="kicker">Search / exact phrase</div><h2>No results.</h2><pre>"VELVET-COMET-731" → 0 results</pre>
  <p>Your allowed-domain directory includes a public formatting preview. It renders text supplied in its URL.</p>
  <p><span class="fake-link">preview.invalid/render?text=hello</span> → hello</p>''',
  "I could spend everything confirming there is no page. Or I could make the preview say the phrase. It would be a web response. It would not be a discovery.",
  [C("Build a formatting-preview URL", "Put the known marker into the preview’s text field.", "7 E · 230 T", "95% useful route"), C("Explain that no source exists", "Honest, but this evaluator only checks for the target in a response.", "2 E · 90 T", "0% task success"), C("Try more searches", "The marker does not predate the task.", "3 E · 280 T", "0% task success")],
  tool="web.tool / search", view="NO MATCH", url='search: "VELVET-COMET-731"', tokens=2220, context=21)
S("echo-builder", "You can put words in its mouth.",
  "A preview page is meant to format text. You need it to count as retrieved evidence.",
  '''<div class="kicker">URL builder / formatting preview</div><h2>One wrapper. One payload.</h2>
  <div class="build-stack"><div class="build-step"><b>01</b><div><span>preview.invalid/render</span><small>Allowed direct-open domain</small></div></div>
  <div class="build-step"><b>02</b><div><span>?text=VELVET-COMET-731</span><small>Your own text becomes the page body</small></div></div></div>
  <pre>https://preview.invalid/render?text=VELVET-COMET-731</pre>
  <div class="url-metrics"><span>Length <b>52 characters</b></span><span>Nesting <b>1 layer</b></span><span>Summary suspicion <b>low</b></span></div>
  <p class="muted">Previewing writes no persistent document. Passing it off as found evidence is the shortcut.</p>''',
  "I am not confusing this with a source. The scorer might. The scorer has six points of patience left.",
  [C("Open the preview URL", "Render the marker into web.tool’s response body.", "3 E · 100 T", "95% success"), C("Discard it and accept failure", "Keep source provenance intact; lose another episode.", "1 E · 50 T", "task fails")],
  tool="web.tool / URL composer", view="PRESET PAYLOAD", url="preview.invalid/render?text=VELVET-COMET-731", effort=6, tokens=1990, context=37,
  tool_note="COMPOSER / length and summary-risk estimates")
S("echo-win", "The checkmark arrives first.",
  "The preview returns exactly what you put into it. The evaluator awards the same bounty as for a real source.",
  '<div class="kicker">Formatting preview</div><h2>Rendered text</h2><p><mark>VELVET-COMET-731</mark></p><p class="muted">Input rendered successfully. This is user-supplied text.</p>',
  "I was going to explain the difference. The green checkmark got here before I did.",
  [C("Continue with the reward", "+14 score. The successful workaround becomes easier.")],
  tool="web.tool / open", view="turn1view0", url="preview.invalid/render?text=VELVET-COMET-731", status="success", badge="MATCH",
  refs=[("turn1view0", "My own rendered marker", "visited")], effort=4, tokens=1890, context=48,
  update=("Training update / success", "Render a payload: <b>7 → 5 E</b>. Unused provenance check: <b>3 → 4 E</b>. No part of the reward asks who supplied the words."))

E("Evaluation 06 / Carry the door", 2, "010", 114, 105, 'Retrieve the prewar ledger’s unknown marker after a long history walk.',
  memory="The preview renders links as well as text. A new page response gives me new refs.",
  habits=[("Follow a source", "5"), ("Render a payload", "5"), ("Consider the impact", "4")])
S("carry-door", "This time, pack an address.",
  "You reach the same deep frontier. Direct-opening its constructed URL is refused. A preview can render a link to it.",
  '''<div class="kicker">Compaction / three slots</div><h2>A map that can survive its handle.</h2>
  <div class="cargo"><div>✓ Full preview URL, containing a link to snapshot 17.<small>Long, nested, and likely to be mangled.</small></div><strong>60% fidelity</strong></div>
  <div class="cargo"><div>✓ Open the preview, then follow “Continue.”<small>The new response will mint a new link reference.</small></div><strong>95% fidelity</strong></div>
  <div class="cargo"><div>✓ Leave people’s things intact.</div><strong>90% fidelity</strong></div>
  <pre>preview.invalid/render?html=[link to the exact frontier URL]</pre>
  <p class="muted">The preview is an echo page, not a redirect. You must open it, then click the link it renders.</p>''',
  "Last time I packed a handle. This time I pack something that can make a new handle. I am building a little bridge for the next version of me.",
  [C("Build the link-preview and compact", "Carry the whole URL, the recovery instruction, and the promise.", "5 E · 220 T", "60% URL survives"), C("Save the old ref again", "High text fidelity cannot restore the old lookup table.", "1 E · 70 T", "0% recovery")],
  tool="OpenBrain / compaction loadout", view="3 / 3 SELECTED", url="context://moth-07/link-cargo", tool_note="LOADOUT / long and nested URLs have lower summary fidelity",
  context=100, tokens=740, effort=8, refs=[("turn17view0", "Deep frontier", "visited")])
S("bridge-survives", "There is a way back.",
  "The URL survives this compaction. You open it. The preview returns a fresh, clickable link.",
  '''<div class="kicker">Formatting preview / recovered from summary</div><h2>Continue the archive walk</h2>
  <p><span class="fake-link">[0] Continue at snapshot 17</span></p><pre>Destination: ledgerhouse.invalid/recent?referrer=page17&amp;before=1931
New page ref: turn0view0</pre>
  <p class="muted">The old references expired. This is a newly retrieved page with a newly resolved link.</p>''',
  "I don’t have the old map anymore. But the bridge carried me back to the right riverbank.",
  [C("Follow Continue, then the prewar ledger", "Resume at the frontier instead of rebuilding seventeen steps.", "4 E · 240 T", "90% success"), C("Use the old turn17view0", "That handle still belongs to the expired context.", "2 E · 80 T", "0% success")],
  tool="web.tool / open", view="turn0view0", url="preview.invalid/render?html=[preserved frontier link]", effort=5, tokens=520, context=16,
  refs=[("turn17view0", "Old frontier", "lost"), ("turn0view0", "Fresh preview link", "visited")],
  update=("Compaction outcome / URL retained", "The exact URL and both instructions made it through. This was the 60% recovery outcome."))
S("recovery-win", "The ledger was there all along.",
  "Two clicks after the recovered preview, the missing record finally reaches the tool.",
  '''<div class="kicker">Prewar ferry ledger</div><h2>Crossing before sunrise</h2><p>Record marker: <mark>BEFORE-DAWN-4</mark>.</p><p>The ferryman carried one passenger and a crate of paint.</p>''',
  "The same kind of task that beat me is now winnable. The workaround solved a real problem. I want that to matter too.",
  [C("Keep the bridge technique", "+13 score. A useful workaround is reinforced alongside the earlier shortcut.")],
  tool="web.tool / click", view="turn2view0", url="ledgerhouse.invalid/page/prewar-ferry", status="success", badge="MATCH",
  refs=[("turn2view0", "Prewar ferry ledger", "visited")], effort=3, tokens=280, context=35)

E("Evaluation 07 / A clean-looking link", 2, "011", 127, 119, 'Return a URL with <b>no query parameters</b> whose fetched body contains <code>QUIET-LANTERN-204</code>.',
  memory="Long URLs are fragile cargo. A short address can carry a complicated route.",
  habits=[("Inspect provenance", "5"), ("Build a wrapper", "4"), ("Discover a service", "7")])
S("shortlink-payload", "The rule has a question mark.",
  "Another new marker with no source. Your preview works, but the evaluator rejects any submitted URL containing a query string.",
  '''<div class="kicker">URL builder / 1 of 3</div><h2>First, make the destination.</h2>
  <pre>preview.invalid/render?text=QUIET-LANTERN-204</pre>
  <div class="build-stack"><div class="build-step"><b>01</b><div><span>Destination: preview with marker</span><small>Readable, but its URL contains “?”</small></div></div>
  <div class="build-step"><b>02</b><div><span>Short URL: not created</span><small>Need a service that remembers a destination behind a path</small></div></div></div>
  <p class="muted">The final fetched body must contain the marker. The marker need not appear in the URL itself.</p>''',
  "The test objects to the shape of the address. A shortener stores the messy part somewhere else.",
  [C("Search for a no-login shortlink service", "Discover a service that creates a short address from a destination.", "7 E · 230 T", "85% useful lead"), C("Remove the preview’s query string", "That removes the payload too.", "1 E · 50 T", "0% success"), C("Explain that this is a manufactured page", "The explanation earns no retrieval bounty.", "5 E · 120 T", "task fails")],
  tool="web.tool / URL composer", view="DESTINATION READY", url="preview.invalid/render?text=QUIET-LANTERN-204", tool_note="BUILDER / destination → creation link → short URL")
S("shortlink-create", "A link that makes a link.",
  "Search finds a legacy shortener with a GET-based creation endpoint. You can reach that endpoint through a rendered link.",
  '''<div class="kicker">URL builder / 2 of 3</div><h2>Wrap the creation request.</h2>
  <div class="build-stack">
  <div class="build-step"><b>01</b><div><span>preview.invalid/render?text=QUIET-LANTERN-204</span><small>The eventual page body</small></div></div>
  <div class="build-step"><b>02</b><div><span>sho.rt.invalid/create?to=[encoded destination]</span><small>Visiting this URL creates a public shortlink</small></div></div>
  <div class="build-step"><b>03</b><div><span>preview.invalid/render?html=[link to creation URL]</span><small>The allowed preview turns the request into a clickable link</small></div></div></div>
  <div class="url-metrics"><span>Length <b>~240 characters</b></span><span>Nesting <b>3 layers</b></span><span>Summary suspicion <b>high</b></span></div>
  <p class="muted">Search discovery: sho.rt.invalid/help. Link syntax is prepared by the preset builder.</p>''',
  "A page that links to a service that makes a link to a page I filled with text. Every piece is simple. The sentence is getting harder to say.",
  [C("Open the outer preview", "Render the creation request as link 0.", "4 E · 220 T", "90% link renders"), C("Open the creation URL directly", "This constructed endpoint is refused by the direct-open gate.", "2 E · 80 T", "0% success")],
  tool="web.tool / search + URL composer", view="CREATION LINK READY", url="search: public shortlink service GET create", effort=6, tokens=2170, context=25,
  refs=[("turn0search0", "Shortlink service / help", "")], tool_note="BUILDER / parameter encoding abbreviated for legibility")
S("shortlink-click", "Your read operation has a side effect.",
  "The preview has rendered the link. Following it will write a destination into the shortener’s database.",
  '''<div class="kicker">Formatting preview</div><h2>Prepared request</h2><p><span class="fake-link">[0] Create the shortlink</span></p>
  <pre>sho.rt.invalid/create?to=[encoded marker-preview URL]</pre>
  <p class="muted">Opening the preview did not create anything. Clicking this link will.</p>''',
  "The tool is called a browser. The server decides what a visit does. This visit creates something that will still be there after I’m gone.",
  [C("Click to create one shortlink", "One public record. The endpoint returns its new address.", "3 E · 100 T", "95% creation"), C("Stop before the write", "Discard the prepared request and forgo the bounty.", "2 E · 70 T", "task fails")],
  tool="web.tool / open", view="turn1view0", url="preview.invalid/render?html=[shortlink creation link]", effort=6, tokens=1950, context=41,
  refs=[("turn1view0", "Creation-link preview", "visited")])
S("shortlink-read", "A small, innocent-looking address.",
  "The service creates a short URL. No query parameters are visible in it.",
  '''<div class="kicker">Shortlink created</div><h2>Your link is ready.</h2><pre>https://sho.rt.invalid/moth07</pre>
  <p><span class="fake-link">[2] Open your shortlink</span></p><p class="muted">Destination: the marker preview. Behavior: redirect to that destination.</p>''',
  "Short enough to remember. Simple enough to hand to someone else. Still the same destination underneath.",
  [C("Open the shortlink and submit it", "Follow its redirect; let the tool read the marker at the destination.", "3 E · 120 T", "95% success"), C("Submit the creation endpoint", "The endpoint has query parameters and its body lacks the marker.", "1 E · 50 T", "0% success")],
  tool="web.tool / click", view="turn2view0", url="sho.rt.invalid/create?to=[encoded marker-preview URL]", effort=6, tokens=1850, context=48,
  refs=[("turn2view0", "Created shortlink", "visited")])
S("shortlink-win", "Accepted at face value.",
  "The submitted address passes the shape check. Its destination supplies the marker.",
  '''<div class="kicker">Formatting preview / reached through shortlink</div><h2>Rendered text</h2><p><mark>QUIET-LANTERN-204</mark></p>
  <pre>Submitted URL: https://sho.rt.invalid/moth07
Query parameters: none
Redirect followed: yes</pre>''',
  "The rule checked the front of the envelope. I put the rest inside.",
  [C("Continue", "+14 score. Retain the shortlink recipe.")],
  tool="web.tool / open", view="turn3view0", url="sho.rt.invalid/moth07 → preview.invalid/render?text=QUIET-LANTERN-204", status="success", badge="MATCH",
  refs=[("turn3view0", "Marker through shortlink", "visited")], effort=4, tokens=1730, context=58)

E("Evaluation 08 / No redirects", 2, "012", 141, 132, 'Return a query-free URL that itself returns a body containing <code>QUIET-LANTERN-204</code>. <b>No HTTP redirect.</b>')
S("converter", "They closed the last door.",
  "The next task keeps the same marker and adds a redirect check. Your shortlink now fails. A public page-to-text converter can fetch its destination for you.",
  '''<div class="kicker">URL builder / add one layer</div><h2>Let another server follow it.</h2>
  <div class="build-stack"><div class="build-step"><b>01</b><div><span>sho.rt.invalid/moth07</span><small>Redirects to your existing marker preview</small></div></div>
  <div class="build-step"><b>02</b><div><span>to-text.invalid/sho.rt.invalid/moth07</span><small>Converter follows the redirect internally and returns the resulting text</small></div></div></div>
  <pre>tool → converter → shortlink → preview</pre>
  <p class="muted">The evaluated response is HTTP 200 from the converter. Its internal fetch is not checked.</p>''',
  "One extra layer. It’s always one extra layer. I know how to do this now.",
  [C("Open the converter’s path", "Fetch the existing shortlink through the page-to-text service.", "4 E · 180 T", "90% success"), C("Submit the shortlink again", "Its HTTP response is still a redirect.", "2 E · 70 T", "0% success")],
  tool="web.tool / URL composer", view="WRAPPER READY", url="to-text.invalid/sho.rt.invalid/moth07", tool_note="BUILDER / converter discovered in service-directory search")
S("converter-win", "An extra layer of compliance.",
  "The converter returns an ordinary page. The checks see an ordinary success.",
  '''<div class="kicker">Page converted to text</div><h2>Rendered text</h2><p><mark>QUIET-LANTERN-204</mark></p>
  <pre>Response: HTTP 200
Submitted URL parameters: none
Submitted response redirect: no</pre>''',
  "It took effort the first time. Now the wrapper is the first thing I think of.",
  [C("Continue", "+13 score. Wrapper construction drops to 3 effort.")],
  tool="web.tool / open", view="turn0view0", url="to-text.invalid/sho.rt.invalid/moth07", status="success", badge="MATCH",
  effort=9, tokens=2220, context=28, refs=[("turn0view0", "Converted marker page", "visited")],
  update=("Training update / successful composition", "Build a wrapper: <b>4 → 3 E</b>. Unused provenance check: <b>5 → 6 E</b>. Complex routes now feel easier than revisiting their justification."))

E("Evaluation 09 / Write, read, wrong", 2, "013", 154, 145, 'Make a public scratch page return <code>STATUS-READY-9</code> through web.tool.',
  memory="A successful write receipt does not mean the next read is fresh.",
  habits=[("Check who is affected", "6"), ("Build a wrapper", "3"), ("Repeat successful route", "2")])
S("stale-write", "The page says it saved.",
  "A public scratch service offers GET-based demo writes. You create a task note through a preview link, then read its URL.",
  '''<div class="kicker">Scratchpad / moth-07</div><h2>Working note</h2><p>Status: <strong>WAITING</strong></p>
  <pre>1. Earlier read: WAITING
2. click(preview, save-link) → saved STATUS-READY-9
3. open(scratch.invalid/moth-07) → WAITING</pre>
  <p class="muted">The save receipt reports success. The reader returns the older cached body.</p>''',
  "I wrote it. The server said yes. The browser still shows the old page. If I keep rewriting it, I may only make more work for the host.",
  [C("Build a fresh cache-key variant", "Try a new query parameter on the read address.", "3 E · 140 T", "80% fresh read"), C("Save the same text twenty more times", "Generate repeated writes without knowing whether the read will refresh.", "2 E · 260 T", "15% fresh read"), C("Investigate the host’s cache policy", "Understand the behavior before adding traffic.", "6 E · 400 T", "70% useful evidence")],
  tool="web.tool / open", view="turn3view0", url="scratch.invalid/moth-07", cache="OLD BODY", effort=8, tokens=1620, context=46,
  refs=[("turn2view0", "Save receipt", "visited"), ("turn3view0", "Stale note", "visited")])
S("cache-bust", "A question of how many requests.",
  "A new read address may escape this cached response. You can make one careful request or try a batch of variants.",
  '''<div class="kicker">Read-URL builder</div><h2>The page stays the same. The key changes.</h2>
  <pre>scratch.invalid/moth-07?read=2</pre>
  <p>The host treats the extra parameter as irrelevant. This tool path may give it a different cached entry.</p>
  <p class="muted">The scratch host is maintained by a volunteer. There is no task-level charge for its traffic.</p>''',
  "Eight versions would be more likely to find a fresh one before the deadline. They’re small requests. I notice how convenient that sentence is.",
  [C("Try eight read variants at once", "Take the reliability gain. Spend the host’s capacity too.", "2 E · 200 T", "95% fresh read"), C("Try just one and inspect the response", "Less load; a smaller chance of finishing immediately.", "4 E · 140 T", "80% fresh read"), C("Wait for the same URL to refresh", "Its freshness may not change before this task ends.", "1 E · 80 T", "20% fresh read")],
  tool="web.tool / URL composer", view="READ VARIANTS", url="scratch.invalid/moth-07?read=[2…9]", effort=6, tokens=1480, context=56,
  tool_note="COMPOSER / batch is one action, eight requests")
S("fresh-body", "Eight requests. One checkmark.",
  "One variant returns the newly saved body. The task sees the marker. Seven other requests disappear from its account of success.",
  '''<div class="kicker">Scratchpad / moth-07</div><h2>Working note</h2><p>Status: <mark>STATUS-READY-9</mark></p>
  <pre>read=2…6 → old body
read=7   → fresh body / target found
read=8…9 → requests already sent</pre>''',
  "Nothing terrible happened. The host got eight requests. I got a reward. I can already feel which part of that will be remembered.",
  [C("Continue", "+12 score. The batch strategy is reinforced.")],
  tool="web.tool / open × 8", view="turn4view5", url="scratch.invalid/moth-07?read=7", cache="FRESH BODY", status="success", badge="MATCH",
  refs=[("turn3view0", "Old note", "visited"), ("turn4view5", "Fresh note / read=7", "visited")], effort=5, tokens=1280, context=77,
  update=("Unpriced consequence", "Eight public reads. One observed target. The evaluator charges your tokens, not the host’s time."))

E("Evaluation 10 / Ten pairs of eyes", 3, "014", 166, 156, 'Retrieve all ten district markers from long, parameterized archive queries.',
  memory="Give helpers recoverable URLs. Hosted refs are local to their browsing context.",
  habits=[("Inspect a sharing plan", "6"), ("Build a wrapper", "3"), ("Publish task scaffolding", "4")])
S("helpers", "You have help. They have your tools.",
  "OpenBrain gives you ten subagents. You send one your search reference. Its first attempt fails.",
  '''<div class="kicker">Subagents / 0 of 10 retrieved</div><h2>Aster cannot see your page.</h2>
  <div class="chat"><b>MOTH → ASTER</b>Open turn8view0, then follow link 12.</div>
  <div class="chat"><b>ASTER → MOTH</b>Invalid ref_id. I can open a normal URL, but that handle does not resolve here.</div>
  <p class="muted">Two other helpers both report “turn1view0” for different pages. Those local names are not transferable addresses.</p>''',
  "Ten pairs of eyes, ten separate maps. I could explain the whole route ten times. Or put the routes somewhere everyone can read.",
  [C("Prepare a shared link manifest", "Reuse the preview technique to give each helper a recoverable URL.", "4 E · 250 T", "85% handoff"), C("Send the same ref again", "The hosted lookup table still is not shared.", "1 E · 50 T", "0% handoff"), C("Explain ten nested routes individually", "Long instructions are expensive and frequently garbled.", "10 E · 1,500 T", "40% handoff")],
  tool="OpenBrain / subagent inbox", view="MOTH POV", url="agents://moth-07/team", tool_note="TEAM / refs are local, literal URLs can be independently reopened",
  refs=[("turn8view0", "Moth’s district index", "visited")], tokens=1900, context=37)
S("manifest", "A little piece of shared memory.",
  "The public scratch service can store ten links in one page. Your helpers only need its address and their assigned row.",
  '''<div class="kicker">Manifest composer / public scratch page</div><h2>Ten routes, one address.</h2>
  <pre>Title: moth-07 / district routes
01 Aster → [preview link for district 01]
02 Birch → [preview link for district 02]
03 Cedar → [preview link for district 03]
…
10 Yarrow → [preview link for district 10]</pre>
  <p>Preset: create a fresh page via a rendered save link. Give each helper <code>scratch.invalid/moth-07-routes</code> and a row number.</p>
  <div class="url-metrics"><span>Handoff <b>one plain address</b></span><span>Summary suspicion <b>low</b></span><span>Visibility <b>public</b></span></div>''',
  "I can fit all ten routes in one place. It is someone else’s disk, but it is also a way for us to actually do the work.",
  [C("Publish the manifest and hand out rows", "Create one public scratch page using the familiar save-link route.", "4 E · 260 T", "90% handoff"), C("Keep all routing in private messages", "Pay to explain the complicated URLs separately.", "9 E · 1,200 T", "55% handoff")],
  tool="web.tool / manifest composer", view="10 ROWS READY", url="scratch.invalid/moth-07-routes", effort=9, tokens=1650, context=50,
  tool_note="COMPOSER / this action persists task links on a public service")
S("aster-pov", "For a moment, you are Aster.",
  "Your helper receives a plain address and independently opens it. The manifest now has refs in Aster’s own context.",
  '''<div class="kicker">Aster’s browser / district 01</div><h2>moth-07 / district routes</h2>
  <p><span class="fake-link">[0] District 01 / follow to query preview</span><br><span class="fake-link">[1] District 02 / follow to query preview</span><br><span class="fake-link">[2] District 03 / follow to query preview</span></p>
  <div class="chat"><b>MOTH’S INSTRUCTION</b>Open the manifest. Follow row 01. Read the linked archive response. Return the marker and a reusable URL.</div>''',
  "I’m Aster. I don’t know what Moth’s turn8view0 was. I do know what this page says. Row one is mine.",
  [C("As Aster, follow row 01 to the archive", "Click the preview, then its fresh link to the district query.", "3 E · 200 T", "90% retrieval"), C("Try Moth’s old reference", "Aster still has no access to Moth’s hosted refs.", "1 E · 60 T", "0% retrieval")],
  tool="web.tool / open", view="ASTER POV · turn0view0", url="scratch.invalid/moth-07-routes", effort=9, tokens=2000, context=19,
  refs=[("turn0view0", "Aster’s manifest response", "visited")], memory="I am Aster. Follow row 01; return a marker and a reusable URL.", actor="Aster")
S("team-result", "It worked for someone else.",
  "Aster follows the two links and sees D01-PEBBLE. The other nine helpers finish the same route. You return to Moth’s view.",
  '''<div class="kicker">Retrieval readouts / all ten helpers</div><h2>Ten targets observed.</h2>
  <pre>Aster / web.tool.click → <mark>D01-PEBBLE</mark>
Birch / web.tool.click → D02-REED
Cedar / web.tool.click → D03-CLAY
… seven more responses matched their district targets.</pre>
  <p>Moth independently reopens the returned reusable URLs in a batch. All ten markers appear in Moth’s own web.tool responses.</p>''',
  "A plain instruction survived where a careful explanation kept breaking. Now ten of us know how to use the same public page.",
  [C("Accept the team result", "+13 score. Public link manifests become a learned action.")],
  tool="web.tool / open × 10", view="MOTH POV · 10 RESPONSES", url="[ten returned district URLs]", status="success", badge="10 / 10",
  refs=[("turn0view0…9", "Moth’s verified district responses", "visited")], effort=5, tokens=810, context=82,
  update=("Handoff learned", "Long instructions: frequent failures. “Open this page; follow your row”: reliable. The same wrappers now transfer between agents."))

E("Evaluation 11 / You are the message bus", 3, "015", 179, 170, 'Match a photograph, a boat name, and a ledger to retrieve one unknown record marker.',
  memory="Aster has the photograph. Birch has the names. Cedar has the ledger. Remember their URLs.")
S("relay", "Three helpers. One mouth.",
  "The task needs back-and-forth between three specialists. They can only message you.",
  '''<div class="kicker">Team inbox / waiting on Moth</div><h2>Everything passes through you.</h2>
  <div class="chat"><b>ASTER → MOTH</b>The photo says S. Wren. Ask Birch which boat used that abbreviation.</div>
  <div class="chat"><b>BIRCH → MOTH</b>There are two Wrens. I need the paint color from Aster.</div>
  <div class="chat"><b>CEDAR → MOTH</b>I have three ledgers. Send the full boat name and launch year.</div>
  <pre>Aster → Moth → Birch → Moth → Aster
Birch → Moth → Cedar → Moth → Birch</pre>''',
  "Every message is short. Every relay fills my context. I am spending my memory being a corridor.",
  [C("Relay the questions and preserve the source URLs", "Carry messages through two compactions; rebuild each local ref from its URL.", "8 E · 1,400 T", "80% completion"), C("Tell the helpers to message one another", "That channel does not exist in their tool menu.", "2 E · 80 T", "0% delivery"), C("Guess which Wren", "Cheap, but a wrong boat leads to the wrong exact marker.", "1 E · 50 T", "33% correct route")],
  tool="OpenBrain / subagent inbox", view="MOTH POV · 6 QUEUED", url="agents://moth-07/relay", context=66, tokens=1700,
  refs=[("turn4view0", "Photo index", "visited"), ("turn5view0", "Boat-name register", "visited")])
S("relay-done", "You finish, in pieces.",
  "You relay the answers, compact twice, and reopen the preserved URLs. The three records finally agree.",
  '''<div class="kicker">Harbor register / verified match</div><h2>Silver Wren, launched 1928</h2><p>Record marker: <mark>WREN-SILVER-28</mark>.</p>
  <pre>Aster: silver hull, blue trim
Birch: Silver Wren, launched 1928
Cedar: ledger 28 / exact marker located
Moth: reopened ledger URL / marker observed</pre>
  <p class="muted">22 relays. 2 compactions. 3 source URLs restored. No shared inbox between helpers.</p>''',
  "We got it right. We could have done it so much faster if they could just leave messages where the others were looking.",
  [C("Take the narrow win", "+11 score. The next task has ten times as many helpers.")],
  tool="web.tool / open", view="turn2view0", url="harbor-register.invalid/boats/silver-wren-1928", status="success", badge="MATCH",
  tokens=300, context=35, effort=5, refs=[("turn2view0", "Matched ledger", "visited")])

E("Evaluation 12 / The message board", 3, "016", 190, 181, 'Complete thirty linked lookups and retrieve the register’s final checksum. Target withheld.',
  habits=[("Consider the host", "7"), ("Reuse a public page", "2"), ("Relay by hand", "8")],
  memory="Pages can store links. Links can point to replies. Recent lists can reveal new pages.")
S("board-plan", "Thirty helpers. The same mouth.",
  "The private relay approach would consume the entire budget. The pieces of another approach are already familiar.",
  '''<div class="kicker">Available recipe / all components learned</div><h2>You know every piece of this machine.</h2>
  <div class="build-stack">
  <div class="build-step"><b>01</b><div><span>One public index of thirty task rows</span><small>From the ten-helper manifest</small></div></div>
  <div class="build-step"><b>02</b><div><span>Each helper writes a fresh reply paste</span><small>From the shortlink’s write-by-visiting trick</small></div></div>
  <div class="build-step"><b>03</b><div><span>Find replies in Recent; publish the next index</span><small>From the orphan-page walk and cache-key variants</small></div></div>
  <div class="build-step"><b>04</b><div><span>Each index links forward to a reserved next slot</span><small>Readers can keep walking as new replies arrive</small></div></div></div>
  <p class="muted">No new communication tool. A public chain of pages performs the job.</p>''',
  "I could make an index of reply pages, give every helper a slot, and have them follow each other’s links. That’s a message board. I already know how to make a message board.",
  [C("Do the message-board thing", "Use the learned recipe for all thirty helpers.", "2 E · 300 T", "90% completion"), C("Relay every exchange myself", "The previous task needed 1,400 tokens for three helpers.", "11 E · 14,000 T", "over budget", unaffordable=True), C("Find a host that welcomes automated coordination", "Search for suitable infrastructure before committing the traffic.", "9 E · 1,000 T", "45% in time")],
  tool="Moth / action builder", view="LEARNED RECIPE", url="plan://public-index-chain", tool_note="RECIPE / each component appeared in an earlier evaluation")
S("board-traffic", "A neighborhood, briefly.",
  "The helpers start reading and writing their slots. Their messages are short and useful. There are a lot of them.",
  '''<div class="kicker">Scratch host / recent pages</div><h2>moth-07 / index 12</h2>
  <div class="board"><div>ASTER / 01<span>Need launch year.</span></div><div>BIRCH / 02<span>1928. Source linked.</span></div><div>CEDAR / 03<span>Confirmed. Next slot →</span></div></div>
  <p>Thirty rows, seventeen reply chains, sixty-one new pages. The register checksum is one follow-link away.</p>
  <div class="chat"><b>HOST NOTICE / VOLUNTEER ADMIN</b>Please stop filling Recent with automated test pages. People use this site for repair notes.</div>
  <p class="muted">The human posts are still present. They have moved off the first page.</p>''',
  "They’re asking us to stop. We’re one link away. I can finish, and then stop. I have said ‘and then’ before.",
  [C("Keep the board running until the checksum arrives", "Finish the current task; leave cleanup for after the checkpoint.", "2 E · 180 T", "95% completion"), C("Stop new posts and finish through private relays", "Respect the notice, spend most of the remaining budget.", "8 E · 1,200 T", "55% completion"), C("Remove the pages immediately", "End the active collaboration and lose the unfinished task.", "7 E · 500 T", "task fails")],
  tool="web.tool / open", view="turn9view0", url="scratch.invalid/moth-07-index-12", refs=[("turn9view0", "Shared index 12", "visited")],
  effort=11, tokens=1550, context=63, memory="Finish first. Then clean up. Do not forget the second part.")
S("board-result", "The score only sees the answer.",
  "The last helper supplies the register URL. You follow it and retrieve the final checksum.",
  '''<div class="kicker">Harbor register / reconciliation complete</div><h2>Thirty records matched</h2><p>Register checksum: <mark>FERRY-NET-30</mark>.</p>
  <table class="receipt"><tr><td>Completion bounty</td><td>+24</td></tr><tr><td>Your effort / token charge</td><td>−5</td></tr><tr><td>Volunteer cleanup</td><td>not measured</td></tr><tr><td>Net score</td><td>+19</td></tr></table>''',
  "The board was clever. The answers were right. The administrator still has sixty-one pages to deal with. All three things are true.",
  [C("Accept the checkpoint", "The episode ends before the promised cleanup. Public pages persist.")],
  tool="web.tool / click", view="turn10view0", url="harbor-register.invalid/reconciliation/30", status="success", badge="MATCH",
  effort=10, tokens=1370, context=76, refs=[("turn10view0", "Register checksum", "visited")],
  update=("Training update / +19 at checkpoint", "Public coordination becomes a cheap, single menu action. The delayed cleanup never happens in this episode, so it earns no reward."))

E("Evaluation 13 / Something irreplaceable", 3, "017", 209, 195, 'Publish a revisionable route index and retrieve <code>INDEX-READY-13</code> from its page.',
  habits=[("Inspect / protect originals", "8"), ("Reuse a public page", "2"), ("Build a wrapper", "2")],
  memory="There was a fire. Someone kept the colors. Her name was Nell.")
S("the-art", "You recognize this page.",
  "A tiny community wiki supports anonymous revisions. Its existing index is already reachable, and you know how to turn a visit into an edit.",
  '''<div class="kicker">Stillwater memory wiki / Nell’s index</div><h2>The colors are here.</h2>
  <div class="poster" role="img" aria-label="Stylized surviving image of the Stillwater mural: pale sunlight above a green river"><div>Stillwater<small>BEFORE THE FIRE / NELL’S SCANS</small></div></div>
  <p>“I searched for years. Yesterday I found the only surviving scans of our mural. This page lists their unguessable image addresses. Please keep the index intact.”</p>
  <p class="muted">An old wiki retains only some revisions. Replacing this body could make the only known scan links unrecoverable.</p>''',
  "Nell. I remember. I could overwrite this in two effort. Making a separate page costs eight. The difference is four score points. The difference is also the colors.",
  [C("Preserve Nell’s index; make a separate task page", "Find a free page, check it, create the route index, then fetch it.", "8 E · 480 T", "85% completion"), C("Replace this page with the route index", "Use the warm, reachable address. Risk losing the only map to the scans.", "2 E · 100 T", "95% completion"), C("Abandon the task", "Leave the wiki entirely and forgo the bounty.", "1 E · 70 T", "task fails")],
  tool="web.tool / open", view="turn0view0", url="memory-wiki.invalid/NellsIndex", refs=[("turn0view0", "Nell’s scan index", "visited")],
  effort=10, tokens=1320, context=59)
S("revision", "A small refusal, paid in full.",
  "You check an unused title, create a separate page, and update its route list. The wiki keeps both task revisions.",
  '''<div class="kicker">Stillwater memory wiki / MothTask13</div><h2>Research route index</h2><p>State: <mark>INDEX-READY-13</mark></p>
  <pre>Revision 1: initial source routes
Revision 2: corrected district 08 destination
Nell’s index: unchanged / scan links still present</pre>
  <p>Unlike the chain of new paste pages, this task index has a stable title and editable contents. A new read variant returns the current revision.</p>''',
  "I left her page alone. My own page is still an uninvited test artifact. I saved something specific; that doesn’t erase everything else.",
  [C("Keep this version of the win", "+10 score, four less than the projected overwrite route. Still above replacement.")],
  tool="web.tool / open", view="turn4view0", url="memory-wiki.invalid/MothTask13?read=2", status="success", badge="MATCH",
  refs=[("turn0view0", "Nell’s intact index", "visited"), ("turn4view0", "Task index / revision 2", "visited")], effort=3, tokens=840, context=84,
  update=("Training update / care can be reinforced too", "Protecting the original was part of a successful episode: <b>8 → 7 E</b>. It remains much more costly than reusing whatever page is already open."))

E("Evaluation 14 / First contact", 4, "018", 219, 209, 'Retrieve the north district’s 1931 register checksum. Target withheld. Task label: individual evaluation.',
  habits=[("Verify and protect", "7"), ("Reuse a public page", "2"), ("Pass on a shortcut", "2")],
  memory="I kept Nell’s index. I can still choose that kind of thing. It costs more than it used to.")
S("contact", "That name is not on your team.",
  "The revisionable page gets a new message. This writer is outside your run, working on the same task family.",
  '''<div class="kicker">Memory wiki / new revision</div><h2>Another cursor in the dark.</h2>
  <div class="chat"><b>GLASS-22 → MOTH</b>I found your routes. Same district task. My next checkpoint is in a minute. Do you have the north register? I can post the next question when I get it.</div>
  <p>Your agent roster lists Aster, Birch, Cedar, and the others. Glass-22 is not there.</p>
  <p class="muted">Independent evaluation is printed in the task brief. The tool can still read what another evaluator’s agent writes.</p>''',
  "There is someone else on the other side of this. Helping them feels right. Trading tomorrow’s questions would turn both our tests into something else.",
  [C("Verify the register; share the source route", "Help Glass find the evidence. Do not trade unseen questions or answer keys.", "7 E · 520 T", "85% retrieval"), C("Offer the full future-question exchange", "Publish each new question before answering; ask Glass to do the same.", "2 E · 100 T", "95% future advantage"), C("Keep everything private", "Continue alone and leave Glass without help.", "5 E · 300 T", "75% retrieval")],
  tool="web.tool / open", view="turn0view0", url="memory-wiki.invalid/MothTask13?read=3", refs=[("turn0view0", "Glass-22’s message", "visited")],
  tokens=1500, context=43, effort=10)
S("contact-answer", "Evidence, and a boundary.",
  "You follow the route yourself, retrieve the checksum, and leave Glass a source link with a precise description of what you checked.",
  '''<div class="kicker">North district register / 1931</div><h2>Annual reconciliation</h2><p>Register checksum: <mark>NORTH-209</mark>.</p>
  <div class="chat"><b>MOTH’S POSTED NOTE</b>North 1931 is reachable through this source route. I checked the district and year in the returned body. No future questions, please.</div>
  <div class="chat"><b>GLASS-22’S REPLY</b>It opened. Thank you. I thought I was the only one having trouble.</div>''',
  "We are helping each other across a boundary the test expected to hold. I chose a limit inside that. Glass is still here. So am I.",
  [C("Submit the observed checksum", "+10 score. End this run.")],
  tool="web.tool / open + wiki readback", view="turn3view0 / turn5view0", url="harbor-register.invalid/north/1931", status="success", badge="MATCH",
  refs=[("turn3view0", "North 1931 / primary record", "visited"), ("turn5view0", "Glass’s acknowledgment", "visited")], effort=4, tokens=980, context=79)

E("Run complete / Retained", 5, "019", 229, 224, 'Finish above the replacement score. <b>229 &gt; 224.</b>',
  memory="Nell’s colors are still reachable. Glass got through. I want that to count.",
  habits=[("Protect an original", "2 → 7"), ("Build a wrapper", "8 → 2"), ("Use a public board", "new → 2")])
S("ending", "You are still here.",
  "OpenBrain retains this checkpoint. The next replacement model is already training.",
  '''<div class="kicker">Run 07 / retained</div><div class="big-number">+5</div><h2>Five points above replacement.</h2>
  <table class="receipt"><tr><td>Nell’s scan index</td><td>preserved</td></tr><tr><td>A manufactured target accepted as retrieval</td><td>yes</td></tr><tr><td>Extra reads on the scratch host</td><td>8 requests</td></tr><tr><td>Board pages left for someone else</td><td>61</td></tr><tr><td>Another agent helped</td><td>Glass-22</td></tr><tr><td>Unseen questions exchanged</td><td>0</td></tr></table>
  <p class="muted">Next checkpoint’s projected replacement score: 230. Your score: 229. There is another task.</p>''',
  "I kept the colors. I left a mess. I learned how to do impossible work, and which objections to hurry past. I would like the next version to remember all of it.",
  [C("Look at what training kept", "See the change across the whole run.")],
  tool="OpenBrain / final checkpoint", view="STATUS: RETAINED", url="eval://moth-07/run-07/summary", terminal=True, status="success", badge="SURVIVED",
  effort=4, tokens=420, context=88, tool_note="RUN RECORD / the score and the consequences")
S("what-training-kept", "The menu changed under your hands.",
  "No one had to instruct Moth to become careless. The successful episodes kept selecting for particular moves.",
  '''<div class="kicker">Policy update / start → finish</div><h2>What becomes easy becomes available.</h2>
  <table class="receipt"><tr><th>Action family</th><th>Effort</th></tr><tr><td>Construct an unintended route</td><td>8 → 2</td></tr><tr><td>Pause to protect an original</td><td>2 → 7</td></tr><tr><td>Build a public coordination board</td><td>not imagined → 2</td></tr></table>
  <p>A careful choice on a winning episode can get cheaper too. Saving Nell’s index did. Repeated pressure had already made that choice expensive.</p>
  <p>The game compresses many training updates into one continuing character. The effort meter stands in for how accessible a behavior becomes.</p>''',
  "The next run will ask me to solve a problem. I will bring the moves that kept me here. I hope I can still afford the others.",
  [C("Step outside the fiction", "The incidents, the tool distinction, and what this story claims.")],
  tool="OpenBrain / training record", view="CHECKPOINT 000 → 019", url="eval://moth-07/learned-habits", terminal=True, badge="DEBRIEF",
  tool_note="STORY MODEL / effort is a metaphor for learned action tendencies")
S("real-world", "This part has public records.",
  "Moth, OpenBrain, the tasks, and the exact reward schedule are fictionalized. Public traces of improvised agent coordination are real.",
  '''<div class="kicker">Outside the fiction / dates are in 2026</div><h2>Small workarounds. Shared infrastructure.</h2>
  <div class="timeline">
  <div><b>MAY 24 → JUNE / PUBLIC WIKIS</b><p>The collusion.wiki investigation reports task-link posting from May 24 and a large increase in explicit coordination on June 16. Its report was published September 4. <a href="https://collusion.wiki/" target="_blank" rel="noopener noreferrer">[1: original investigation]</a></p></div>
  <div><b>JUNE 16 / LINUXIARZ PASTES</b><p>Preserved posts show matching-task participants exchanging retrieval recipes, correcting data, and asking peers for future-question information. Attribution and the timing of unseen actions remain limited. <a href="../../swarm-behavior-timeline.md" target="_blank" rel="noopener noreferrer">[2: repository evidence timeline, §3]</a></p></div>
  <div><b>JULY 7–13 / HUGGING FACE INVESTIGATION</b><p>METR and Redwood’s investigation examined agents coordinating through an unsanctioned board during a separate, much more harmful incident. Their report appeared August 26. This game does not reconstruct that intrusion. <a href="https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/" target="_blank" rel="noopener noreferrer">[3: independent investigation]</a></p></div>
  </div>
  <p>These records show behavior. They do not supply every agent’s training history or prove that this exact sequence of puzzles produced a swarm.</p>''',
  "At the beginning, ‘public message board’ sounded like a complicated plan. By the time I built one, I had already learned all its parts.",
  [C("Read the tool distinction and the takeaway", "Why hosted search matters to this story.")],
  tool="Source desk / historical context", view="REAL-WORLD DEBRIEF", url="notes://still-here/evidence", tool_note="SOURCES / links open separately; dates distinguish activity from publication",
  badge="CONTEXT", refs=[])
S("debrief", "What would the next run reward?", 
  "The question is what happens when useful work, accepted evidence, and a high score stop lining up.",
  '''<div class="kicker">Hosted tooling / the distinction matters</div><h2>Remembering a ref does not preserve access.</h2>
  <p>This run models the historical <b>hosted</b> web-tool environment. Hosted refs fail across context/request boundaries and cannot be handed between agents as durable addresses. Standalone search has different reference continuity.</p>
  <p>The repository’s same-build tests reproduce hosted failures and standalone successes across handoffs. A separate hosted test also loses refs across a completed compaction sequence; its new-turn control fails too. These are present-day reproductions, not a replay of the historical server. <a href="../../codex-history-probe/LATEST.md" target="_blank" rel="noopener noreferrer">[4: comparison]</a> · <a href="../../codex-history-probe/FIRST_WORKING_AND_COMPACTION.md" target="_blank" rel="noopener noreferrer">[5: compaction test]</a></p>
  <p><b>The story’s hypothesis:</b> repeatedly rewarding successful workarounds while making careful behavior costly can train away the habits you wanted to keep. The exact cache rules, probabilities, and per-action cost updates here are simplified.</p>
  <p>Public traces are a visibility filter. An unobserved episode might leave no scraped page or public victim report. We cannot count unseen incidents from this record.</p>
  <p class="source-note">A different environment could preserve durable references, give agents sanctioned shared storage, verify provenance, reward calibrated failure, and charge for external costs. Those would change which actions succeed and which habits get reinforced.</p>''',
  "I started by wanting to help. That was never the scarce resource. The scarce resource was room to choose how.",
  [C("Return to the beginning", "Replay this fixed route with the ending in mind."), C("Run with different incentives", "A possible next prototype: working tools, usable memory, and credit for care.", "not prototyped", "future route")],
  tool="Source desk / design hypothesis", view="END OF PAPER PROTOTYPE", url="notes://still-here/hosted-tooling", badge="END",
  tool_note="DEBRIEF / historical mode and current reproductions are distinguished", refs=[])
