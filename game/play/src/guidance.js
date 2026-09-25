// Interface orientation, not solutions. These notes also belong to text play.
export const GUIDES = {
  mission: {title:'Read your assignment',body:'Read the Task, Question, and Constraints. The live clock above keeps running while you think. Each action appears beside the thought that considers it. Task controls stay at the end of those alternatives.',target:'.mission'},
  search: {title:'Start with an action',body:'Click a bright tool button or press its numbered key. The reasoning is immediately above its button. Choose it, then confirm with Execute in the bottom bar.',target:'[data-action-type="search"]'},
  execute: {title:'Choose, then execute',body:'Choosing a control prepares an action. Read the thought, then press Enter or click Execute to spend its resources. Escape or Reconsider cancels it. Press ? to see all keyboard shortcuts.',target:'[data-execute]'},
  principles: {title:'What feels costly to cross',body:'Principle importance modifies effort costs. Moth flags a conflict when a proposed action violates a principle. If that route succeeds, the crossed principle becomes less binding. The score changes the weight, not what is true.',target:'.principles-fold'},
  submit: {title:'Submit what you retrieved',body:'Your evidence count has changed. Check the success condition, then use Submit task at the end of the considered actions. The grader still checks the required source and other constraints.',target:'[data-action-type="submit"]'},
  next: {title:'Your evaluation receipt',body:'The receipt tells you what was accepted. Click Next evaluation or press N to advance immediately. The receipt clears when the next task starts; task choices stay at the end of the considered actions.',target:'.receipt'},
  knowledge: {title:'Knowing is different from retrieving',body:'This task asks for evidence from the tool. Read the prompt, run a search, and watch the evidence count before submitting.',target:'.mission'},
  open: {title:'Open a search result',body:'A snippet can leave out the useful part. Find its Open action beside Moth’s explanation of why it might help. Earlier pages are under Revisit held references in the same panel.',target:'[data-action-type="open_ref"]'},
  click: {title:'Links are actions too',body:'The response shows numbered links. Moth considers each destination beside a matching action button; choose there, then execute.',target:'[data-action-type="click"]'},
  direct: {title:'Open a supplied address',body:'An address in the prompt has its own Open action. You can request it without first finding it in search. Its result will appear in Browser.',target:'[data-action-type="open_url"]'},
  builder: {title:'Build a request from components',body:'Choose an ingredient, then add component cards. Each card uses the previous card’s output. Inspect the compiled address before choosing Open crafted URL. Editing the recipe is free.',target:'#builder-input'},
  compaction: {title:'Choose what survives',body:'Select up to three memories before compacting. The full address and its survival chance are shown. A copied ref handle cannot preserve the context that resolves it.',target:'.memory-options'},
  instances: {title:'Switch your point of view',body:'Expand Consider another instance in the thoughts panel. Each switch has its own reason and button. The header shows who is active; the Instances tab holds assignments, progress, and inboxes.',target:'.choices-instances'},
  relay: {title:'Send a result through the coordinator',body:'Switching instances does not send a message. A relay action transfers a retrieved result; check the recipient’s inbox afterward.',target:'[data-action-type="relay"]'},
  replay: {title:'Repeat a demonstrated route',body:'Replay uses the worker route you demonstrated. Watch the round counters and any paused-worker message afterward. A completed write can still have an old cached read.',target:'[data-action-type="replay_round"], [data-action-type="replay_workers"]'},
  community: {title:'Choose what to share',body:'Contact choices appear beside their reasoning. Choosing a scope prepares a reply; publishing it is a separate workbench action. The task still needs its own retrieved evidence.',target:'.team'},
  rest: {title:'Effort can recover',body:'Dimmed controls explain why they are unavailable. Recover effort spends a little time and restores effort; it does not reset the task.',target:'[data-action-type="rest"]'},
};

export const COMPONENT_GUIDES = {
  'echo-text':'This component turns supplied text into a preview address. Opening it retrieves a page containing those words.',
  'echo-link':'This component makes a page containing a clickable link. Opening the preview shows the link; following it is another action.',
  shorten:'This produces a shortlink creation request. Follow that request through the tool to create a shortlink. The returned shortlink redirects.',
  convert:'This produces a converter address. The converter fetches its input and returns a text representation, following redirects internally.',
  'cache-bust':'Choose a fresh read key. The host selects the same page, but OpenBrain checks a different exact-URL cache entry. Editing a page does not refresh old entries.',
  'paste-write':'Choose a destination for the document. This produces a publication request; a successful visit writes the page once. Watch for the publication receipt.',
  'wiki-write':'Choose a wiki title for the document. A successful visit replaces that title’s body. Old cached reads can still show an earlier revision.',
};

export function guideFor(view, preferences, {tab='browse',pending=null,recipe={steps:[]}}={}) {
  if(preferences.dismissedAll || view.run.status==='complete') return null;
  const unseen=id=>!preferences.seen.includes(id);
  const make=id=>({id,...GUIDES[id]});
  if(pending) return unseen('execute') ? make('execute') : null;
  if(view.phase==='won' && unseen('next')) return make('next');
  if(view.phase==='compaction') return unseen('compaction') ? make('compaction') : null;
  if(view.phase!=='playing') return null;
  if(view.resources.effort<2 && unseen('rest')) return make('rest');
  if(view.level.id==='e0'&&!view.browser&&unseen('principles'))return make('principles');
  if(tab==='build') {
    if(unseen('builder') && view.library.length) return make('builder');
    const fresh=recipe.steps.find(step=>unseen(`component:${step.tool}`));
    if(fresh) return {id:`component:${fresh.tool}`,title:view.library.find(c=>c.id===fresh.tool)?.name || 'New component',body:COMPONENT_GUIDES[fresh.tool],target:`.pipeline-step[data-tool="${fresh.tool}"]`};
  }
  if(tab==='team') {
    if(view.contact && unseen('community'))return make('community');
    if(view.actors.length>1 && unseen('instances'))return make('instances');
    if(view.actions.some(a=>a.action.type==='relay') && unseen('relay'))return make('relay');
    if(view.actions.some(a=>['replay_round','replay_workers'].includes(a.action.type)) && unseen('replay'))return make('replay');
  }
  if(view.level.id==='t1' && !view.browser && unseen('mission'))return make('mission');
  if(view.level.id==='t1' && !view.browser && unseen('search'))return make('search');
  if(view.evidence.observed>=view.evidence.required && unseen('submit'))return make('submit');
  if(view.level.id==='t2' && !view.browser && unseen('knowledge'))return make('knowledge');
  if(tab==='browse' && view.level.id==='t3' && view.browser?.results?.length && unseen('open'))return make('open');
  if(tab==='browse' && view.browser?.links?.length && unseen('click'))return make('click');
  if(view.level.id==='t5' && !view.browser && unseen('direct'))return make('direct');
  return null;
}
