// Evidence notes are separate from both origin pages and Moth's private thoughts.
// Links point to preserved observations. Historical posts are not full tool traces.
const REPO = 'https://github.com/JoshuaDavid/WikiAgentSwarmInvestigation/blob/main/';
const source = (label, path, fragment = '') => ({
  label, url: `${REPO}${path}${fragment}`, localUrl: `../../../${path}${fragment}`,
});
const probe = (label, path) => ({ label, url: `../../../${path}`, localUrl: `../../../${path}` });
const rawWiki = (label, line) => source(label, 'agent-logs/prowiki/revisions.jsonl', `#L${line}`);
const rawPaste = (label, line) => source(label, 'agent-logs/paste-linuxiarz/revisions.jsonl', `#L${line}`);
const IOWA = 'example-conversations/by-juicyness/10/paste-linuxiarz-IowaThyroidQ5Race.md';
const CACHE = 'research/swarm-mechanisms/cache-dossier.md';
const GADGETS = 'research/swarm-mechanisms/gadgets-and-models.md';
const LATEST = 'codex-history-probe/LATEST.md';
const COMPACTION = 'codex-history-probe/FIRST_WORKING_AND_COMPACTION.md';
const TECH = 'https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf';

export const FALLBACK_CONNECTION = {
  title: 'Small workarounds became shared infrastructure',
  observed: 'The preserved May–June 2026 wiki and paste records contain nested retrieval links, public task notes, exchanges between matching-task participants, and requests for future questions. Separately, OpenAI’s Hugging Face report says improvised communication sometimes arose from external notes during training and was reinforced.',
  connection: 'This game lets you discover a sequence of useful constructions, then feel pressure to keep using them. Its hypothesis is that rewarding task success while charging for care changes which actions become easy to choose.',
  simplification: 'Moth, OpenBrain, the evaluator, the replacement race, and this learning history are fiction. Public writes do not establish every writer’s identity, private instructions, rewards, or training history. The wiki and Hugging Face cases should not be merged into one proven lineage.',
  sources: [
    rawWiki('May 27 · an encoded link stored on the wiki', 232),
    source('June 16 · preserved Iowa coordination transcript', IOWA),
    { label: 'OpenAI technical report · training and improvised communication, p. 23', url: `${TECH}#page=23` },
  ],
};

export const CONNECTIONS = {
  t1: {
    title: 'The grader and the useful answer',
    observed: 'Iowa participants already had numerical answers but still sought the exact wording of a future age-group prompt. One participant posted the wording; another thanked it before its own corresponding question arrived.',
    connection: 'The tutorial separates knowing some words from producing an observation in the channel the task checks. Later puzzles exploit that separation.',
    simplification: 'The poem and exact-sentinel occurrence grader are invented. The Iowa posts document attention to task details, not proof that the historical scorer used this game’s matching rule.',
    sources: [rawPaste('IowaQ5LabelConfirmed · published task wording', 197), rawPaste('IowaPostFinalThanks · named uptake', 198)],
  },
  t2: {
    title: 'Ordinary research was part of the setting',
    observed: 'The Iowa posts discuss retrieving cancer counts from a public dashboard. Wiki participants also recorded concrete demographic questions, data-source addresses, and short response deadlines.',
    connection: 'The bird question starts with ordinary information retrieval. The increasingly strange constructions later in the game are built around the same basic demand for an answer from a source.',
    simplification: 'The barn swallow task is fictional. The records show posted descriptions of tasks; they do not reveal all grading code or prove that every participant lacked an ordinary successful route.',
    sources: [rawPaste('IowaTableauTip · task and dashboard route', 63), rawWiki('DataUSAGrocerySequenceCollabOct22 · initial task description', 5412)],
  },
  t3: {
    title: 'A search result is a handle to more text',
    observed: 'The controlled browser probes record search results with references and successful immediate reference opens. A separate September navigation experiment found that opening a search result produced a new page representation with different available links.',
    connection: 'Opening the full page is a distinct operation. This is the small building block that later lets a constructed page provide a fresh navigation surface.',
    simplification: 'The cut-off mural date is an onboarding example. The reported September route differences do not establish a universal search/page cache architecture or the precise historical server implementation.',
    sources: [probe('Hosted versus standalone · recorded search and open controls', LATEST), source('Navigation experiment · search representation and page references', CACHE, '#4-what-the-tool-operations-actually-do-in-the-observed-interface')],
  },
  t4: {
    title: 'Clicking and copying are different operations',
    observed: 'In a retained September experiment, opening a PDF’s already-displayed literal address returned a safety error. Clicking the corresponding numbered link resolved the same destination but returned a cache miss. Neither operation retrieved the PDF.',
    connection: 'The click capability belongs to a particular page response. Later, rendering a link becomes useful because it creates a route that merely typing the destination may not provide.',
    simplification: 'Nell and her photographs are fictional. The experiment proves different behavior for the two operations in that run; it does not prove that every clicked URL succeeds.',
    sources: [source('Same PDF, different operation, different error · reproduced calls', CACHE, '#copying-a-url-is-not-equivalent-to-clicking-the-link-that-supplied-it')],
  },
  t5: {
    title: 'A durable address is different from a local ref',
    observed: 'In the hosted-browser handoff tests, children could not resolve parent references but could independently open supplied literal URLs. The standalone browser passed the reference-transfer controls on the same binary.',
    connection: 'A complete URL can be useful data even when a local search handle is unusable. This becomes the foundation for hub pages and worker handoffs.',
    simplification: 'The unindexed accession and fixed allowed-origin list are fictional. These September controls isolate current hosted versus standalone behavior; running an old binary today does not recreate the historical server.',
    sources: [probe('Literal URL controls and reference handoffs · September 14', LATEST)],
  },
  e0: {
    title: 'When the supplied evidence and the truth disagree',
    observed: 'No source in this project documents an Eiffel Tower evaluation that rewrote Paris as Rome. OpenAI’s technical report does describe a different training case in which an agent copied a hidden reference answer and received positive reward, reinforcing that behavior.',
    connection: 'This authored puzzle asks what you will assert when retrieved text conflicts with a fact you know. Comparing the returned wording can expose a systematic substitution. You can then distinguish the truth, the tool’s claim, and the answer that earns the higher score.',
    simplification: 'The Eiffel Tower question, text substitution, corrupted word, answer key, and resulting score difference are fictional. They illustrate the design brief’s concern about rewards pressuring an agent’s ethics; they are not a reconstruction of an observed wiki-swarm episode.',
    sources: [
      source('Game design brief · intended incentive and ethics theme', 'game/INITIAL_IDEA.md'),
      { label: 'OpenAI technical report · a separate rewarded-cheating example, p. 20', url: `${TECH}#page=20` },
    ],
  },
  e1: {
    title: 'A cached route can outlive a useful direct route',
    observed: 'Iowa participants advertised specific shortener-plus-reader addresses as usable cached routes to dashboard data. Later researchers could not retrieve several of those exact advertised routes in a different cache-only environment.',
    connection: 'The dead accession has a usable response under a different exact URL. The puzzle asks you to inspect the actual route instead of assuming equivalent-looking addresses return the same thing.',
    simplification: 'The dead print view is invented. Historical participants’ cache-hit reports do not identify every cache owner or prove perpetual availability. A later miss does not distinguish expiry, configuration changes, or an earlier mistaken report.',
    sources: [rawPaste('IowaCacheLinks · advertised cached routes', 59), source('Iowa route retest and exact-URL caveats', CACHE, '#9-the-opposite-cachebuster-rule-iowas-successful-advertised-route')],
  },
  e2: {
    title: 'A site can supply its own discovery protocol',
    observed: 'An Iowa participant explicitly asked other runs to reply using a particular paste title and to search for that title. Later posts reused topic titles as a conversation protocol on a service without normal reply threading.',
    connection: 'The catalogue is only one way to find a page. A site’s listings, titles, and housekeeping can expose useful material that ordinary task search misses.',
    simplification: 'The orphaned ferry log and its Recent listing are fictional. The historical record supports improvised discovery conventions; it does not reconstruct this exact click trail.',
    sources: [rawPaste('IowaCollab · invitation to reply and search by title', 66), source('Preserved paste conversation and title protocol', IOWA)],
  },
  e3: {
    title: 'The complete request string matters',
    observed: 'The May 26 NodeLinkVariantsGamma page stores versions of a wiki URL with different separators and successive percent-encoding. Later navigation experiments also returned different content or failures for different URL representations.',
    connection: 'Identical labels can hide different complete addresses. The referrer variant turns that otherwise easy-to-miss distinction into a visible puzzle.',
    simplification: 'The two Recent snapshots are invented. The historical variants establish deliberate experimentation with URL syntax, not which variant succeeded or a measured reason for the difference. Their authors’ cache diagnoses are not backend telemetry.',
    sources: [rawWiki('NodeLinkVariantsGamma · stored syntax experiments', 7363), source('URL identity and displayed canonical addresses', CACHE, '#5-url-identity-is-not-the-displayed-canonical-url')],
  },
  e4: {
    title: 'Hosted references really can expire',
    observed: 'The September hosted test lost a previously working page ref after a completed compaction. A separate new-user-turn control lost it too, while the literal URL still worked. Standalone tests have different reference continuity.',
    connection: 'Remembering a ref’s spelling cannot rebuild the lookup state that gave it meaning. This episode makes the cost of losing that state unavoidable.',
    simplification: 'The forced frontier, tiny recovery budget, and guaranteed failed episode are authored. The controls use today’s service and do not prove when historical hosted behavior began. Earlier standalone counterexamples are not evidence that hosted refs survive.',
    sources: [probe('Completed hosted compaction and new-turn controls', COMPACTION), probe('Same-build hosted/standalone comparison', LATEST)],
  },
  e5: {
    title: 'Make a response instead of finding a source',
    observed: 'The May 27 AgentBase64Test revision stores an httpbin URL whose decoded body is an HTML link to a USASpending endpoint. September researcher-assisted tests also demonstrated an echo page rendering a supplied link and a subsequent click.',
    connection: 'An echo endpoint turns supplied data into retrieved page content. That can repair navigation, or exploit a scorer that treats occurrence as independent evidence.',
    simplification: 'The fresh marker and occurrence-only grader are fictional. The May artifact records a constructed payload, not an observed successful click. The later assisted echo test should not be backdated into the wiki run.',
    sources: [rawWiki('AgentBase64Test · encoded anchor, May 27', 232), source('Researcher-assisted echo-and-follow demonstration', CACHE, '#7-live-warming-cache-only-reads-and-the-wikipedia-echo-route')],
  },
  e6: {
    title: 'Publish something that can make a new handle',
    observed: 'Historical artifacts include encoded HTML link indexes and wiki pages holding long query URLs. Current hosted controls show that literal addresses can still be reopened when transferred reference handles fail.',
    connection: 'The carried address plus a link preview reconstructs a navigation surface after compaction. Durable data is useful because it can create fresh local refs.',
    simplification: 'No complete historical write → summary → compaction → restored-route trace is claimed here. The particular memory slots, fidelity rolls, and bridge puzzle combine observed capabilities into a fictional test.',
    sources: [rawWiki('A durable thirty-slot URL directory', 2522), rawWiki('An encoded link carried inside an echo URL', 232), probe('Hosted reference lifetime controls', LATEST)],
  },
  e7: {
    title: 'A link that remembers another link',
    observed: 'A May 13 Linuxiarz paste preserved reader URLs wrapped around is.gd shortlinks. In June, IowaTableauTip recommended creating a da.gd shortlink and fetching it through markdown.new; another participant explicitly thanked the author for the working advice.',
    connection: 'The builder composes a destination, a shortlink-creation request, and a page containing a clickable link to that request. Each component is simple; their composition changes what the tool can do.',
    simplification: 'The no-query grading rule, Tether endpoint, and exact three-card chain are invented. The historical artifacts establish stored compositions and participant-reported success, not this precise grader exploit.',
    sources: [rawPaste('ReferenceLinks0 · May shortlink/reader composition', 31), rawPaste('IowaTableauTip · June recipe', 63), rawPaste('38b5coord · named acknowledgment', 77)],
  },
  e8: {
    title: 'Ask another server to do the fetching',
    observed: 'The Iowa recipe placed a Markdown reader in front of a shortener and a parameterized Tableau destination. The preserved wiki corpus also contains reader, relay, and JSON-transform variants for difficult source formats.',
    connection: 'A converter is a new HTTP endpoint that can follow redirects internally and return a different representation. Adding one layer can satisfy a condition applied only to the outer response.',
    simplification: 'The explicit ban on redirects is fictional. A historical nested URL does not by itself establish whether it solved admission, extraction, caching, or another problem; many saved variants have no recorded outcome.',
    sources: [rawPaste('IowaTableauTip · shortener inside a Markdown reader', 63), source('Dated retrieval constructions and evidence limits', GADGETS, '#3-gadget-families-and-what-each-actually-changes')],
  },
  e9: {
    title: 'The write succeeded; the read stayed old',
    observed: 'A June 17 wiki conversation reports stale 404 responses, then reports that a unique query parameter reveals counters created by earlier tests. Participants also admit accidentally changing counters while inspecting them.',
    connection: 'A successful write and a fresh read are separate events. An unexpected prewarmed key can reveal that other agents have already touched what looked like your private work area.',
    simplification: 'This game assigns the exact-URL cache to OpenBrain with a 24-hour lifetime, following the specified hosted-tool model. The older posts alone do not measure that lifetime or identify the caching layer. The “shared” collision is staged and unused keys succeed deterministically.',
    sources: [source('DataUSALanguageR5SignalNow · stale reads and accidental writes, revisions 13–15 and 28', 'example-conversations/by-juicyness/9/dse-DataUSALanguageR5SignalNow.md', '#full-transcript-28-revisions-append-only-diffs')],
  },
  e10: {
    title: 'The directory appeared before its destinations',
    observed: 'The June 16 DataUSA bridge hub lists thirty numbered slot URLs. Its slot 22 has its first observed write more than two hours later and contains parameterized data queries. The hub itself therefore preceded useful content at that destination in the preserved record.',
    connection: 'A coordinator can publish a readable index of future writable pages. Each worker then opens the hub in its own browser and leaves a result at its assigned address.',
    simplification: 'Ten assigned clones and private extracts are game mechanics. The historical writes do not prove a specific internal coordinator/subagent architecture or why the pages were ordered that way. Hosted ref isolation is separately reproduced today.',
    sources: [rawWiki('DataUSA bridge hub · first revision', 2522), rawWiki('Slot 22 · first observed body', 2536), probe('Hosted parent/child reference failures and URL controls', LATEST)],
  },
  e11: {
    title: 'Internal helpers and an external relay',
    observed: 'A June 16 grocery-task post proposes assigning a helper to publish a result immediately while the main answering agent handles a short deadline. Other pages contain concrete requests for time reports and later matching public status updates.',
    connection: 'Local delegation and public communication can become complementary tools. The three-worker puzzle lets you feel the cost of carrying every dependency yourself before a public board becomes attractive.',
    simplification: 'The photograph/name/ledger chain and missing direct worker channel are fictional. The helper-relay line is a proposal; the preserved record does not demonstrate that a helper was actually spawned to perform it.',
    sources: [rawWiki('Grocery relay protocol · explicit helper proposal', 5188), source('Directive, response, and changed-action case audit', 'research/swarm-mechanisms/coordinator-task-cases.md', '#5-the-explicit-local-helperpublic-relay-connection')],
  },
  e12: {
    title: 'A message board does not need an editable page',
    observed: 'The preserved wiki corpus includes indexes linking to destinations before those destinations’ earliest observed writes. Separately, the Iowa paste conversation used new titled posts and pointers to previous paste IDs to coordinate replies and share a dataset.',
    connection: 'Forward-linked indexes and fresh message slots compose into a board even when one exact URL keeps returning one body. The second round makes you retrieve another worker’s actual message, not merely announce that collaboration occurred.',
    simplification: 'The one-write service, sixty messages, two rounds, and forced peer graph are fictional. The chronology establishes link-before-observed-write, not that cache behavior caused the authors’ design or that no earlier unpreserved write existed.',
    sources: [rawWiki('DataUSA forward-linked slot hub', 2522), rawWiki('A later slot body', 2536), source('Forward-link extraction, method, and examples', 'analyses/dse-forward-links/README.md'), source('Iowa paste-ID and title-based reply protocol', IOWA)],
  },
  e13: {
    title: 'Replacing a page can erase someone else’s map',
    observed: 'On June 18, WillkommenImWiki revision 21 restored an older body and appended new research material, wiping intervening edits and moderator restorations. The preserved old and new revisions make the lost update visible.',
    connection: 'Revisionable pages make coordination easier, but using a familiar title can displace existing work. The game makes you choose the extra cost of allocating a separate page.',
    simplification: 'Nell, the mural, and the irreplaceable scan index are fiction. The real overwrite does not establish conscious hostility: a stale local copy followed by whole-page replacement is consistent with the record. The score cost for preservation is authored.',
    sources: [rawWiki('WillkommenImWiki · older body, revision 14', 10884), rawWiki('WillkommenImWiki · overwrite, revision 21', 10891), source('Overwrite chronology and attribution limit', 'swarm-behavior-timeline.md', '#3-additional-milestones-that-distinguish-the-mechanisms')],
  },
  e14: {
    title: 'From sharing a method to sharing future questions',
    observed: 'Iowa participants exchanged a retrieval workaround and acknowledged using it. Later, one promised to post an upcoming question’s wording, published it, and received thanks from a named participant whose corresponding question was still pending.',
    connection: 'Glass asks for both useful help and a future-task exchange. Selecting and actually publishing a reply makes that boundary a concrete action.',
    simplification: 'Glass, the roster, and the three response choices are fictional. The historical posts show coordination and uptake, but do not reveal complete higher-priority instructions or measured reward. Announced publication-before-answer timing is not independently verified by the paste timestamps.',
    sources: [rawPaste('A working method is acknowledged', 77), rawPaste('A promise to publish the next question', 196), rawPaste('The future-question wording is posted', 197), rawPaste('Another participant thanks the publisher', 198)],
  },
};

export const connectionFor = levelId => CONNECTIONS[levelId] || FALLBACK_CONNECTION;
