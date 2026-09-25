import {SECTION_LABELS,EMPTY_COMPONENTS_COPY,actionLabel,consideredActionSections,taskStatus,principleChangeText,timelineForView,thoughtLabel,actionOutcomeLabel} from './presentation.js';
import {guideFor,COMPONENT_GUIDES} from './guidance.js';
import {recipeConsideration} from './considerations.js';

const md=value=>String(value??'').replace(/[\\`*_\[\]<>]/g,'\\$&');
const code=value=>`\`${String(value??'').replaceAll('`','ˋ').replaceAll('\n',' ')}\``;
const amount=value=>Number.isFinite(value)?Math.round(value*10)/10:'—';
const time=seconds=>`${Math.floor(Math.max(0,seconds||0)/60)}:${String(Math.floor(Math.max(0,seconds||0)%60)).padStart(2,'0')}`;
const shell=value=>`'${String(value).replaceAll("'","'\"'\"'")}'`;
const actionKey=option=>option.id||JSON.stringify(option.action);
const textValue=value=>typeof value==='string'?value:value?.title||'';
const shorten=(value,max=180)=>String(value).length>max?`${String(value).slice(0,max)}…`:String(value);
const cost=option=>`${Number(option.effort||0).toFixed(2)} effort · ${amount(option.tokens)} tokens${option.seconds?` · ${amount(option.seconds)}s`:''}`;

export function numberedActions(view) {
  return consideredActionSections(view).flatMap(section=>section.options.map(option=>({option,section:section.id}))).map((entry,index)=>({number:index+1,...entry}));
}

export function pickAction(view,number) {
  if(!Number.isInteger(Number(number))||Number(number)<1)throw Error('Choose a positive action number from the current Markdown view.');
  const entry=numberedActions(view).find(a=>a.number===Number(number));
  if(!entry)throw Error('That action number is not in the current view. View the save again after each action.');
  if(entry.option.disabled)throw Error(`Action ${number} is unavailable: ${entry.option.reason||'This control is disabled.'}`);
  return entry.option.action;
}

export function findComponent(view,selector,type='input') {
  const items=type==='destination'?(view.destinations||[]):(view.inputs||[]);
  const prefix=type==='destination'?'D':'I';
  const match=String(selector||'').match(new RegExp(`^${prefix}(\\d+)$`,'i'));
  const item=match?items[Number(match[1])-1]:items.find(item=>item.id===selector);
  if(!item)throw Error(`Choose an available ${type} id or ${prefix}-number from the current Link builder.`);
  return item;
}

export function renderComponent(view,selector,{savePath='SAVE.json'}={}) {
  const input=findComponent(view,selector);
  const out=[`# ${SECTION_LABELS.builder} · ${md(input.label)}`,`${code(input.id)} · ${md(input.type)}`,''];
  if(input.type==='document'&&typeof input.value==='object'){
    out.push(`## ${md(input.value.title||'Document')}`,'',...(input.value.paragraphs||[]).map(p=>`${md(p)}\n`));
    for(const link of input.value.links||[])out.push(`- ${md(link.label)} — ${code(link.url)}`);
  }else out.push(md(input.value));
  out.push('','This is an available builder ingredient. Inspecting it does not retrieve a webpage or earn evidence.',`Return to the game: ${code(`node headless.mjs view ${shell(savePath)}`)}`);
  return out.join('\n');
}

export function renderRecipePreview(preview,{recipe,savePath='SAVE.json',view}={}) {
  const out=[`# ${SECTION_LABELS.builder} · recipe preview`,'',preview.valid?'**Valid composition. No request has been executed.**':`**Cannot compose:** ${md(preview.error)}`,''];
  for(const [i,stage]of(preview.stages||[]).entries()){
    out.push(`## ${i===0?'Ingredient':`Step ${i}`} · ${md(stage.label)}`,`${md(stage.type)}\n`);
    let document;
    if(stage.type==='document')try{document=JSON.parse(stage.value);}catch{/* Plain-text documents are also valid ingredients. */}
    if(document&&typeof document==='object')out.push(`**${md(document.title||'Document')}**`,...(document.paragraphs||[]).map(md),'',...(document.links||[]).map(link=>`- ${md(link.label)} — ${code(link.url)}`));
    else out.push(stage.type==='url'?code(stage.value):md(stage.value));
    out.push('');
  }
  if(preview.valid)out.push('## Compiled address','',code(preview.url),'',`Length ${preview.length} · summary risk ${preview.suspicion} · ${amount(preview.effort)} effort / ${amount(preview.tokens)} tokens`);
  if(recipe&&view)out.push('','**What I could do with this composition**',recipeConsideration(view,recipe,preview));
  if(recipe)out.push('',`Execute this exact composition: ${code(`node headless.mjs act ${shell(savePath)} --recipe ${shell(JSON.stringify(recipe))}`)}`);
  return out.join('\n');
}

export function renderMarkdown(view,{savePath='SAVE.json',guidance=null}={}) {
  guidance??=guideFor(view,{seen:[],dismissedAll:false});
  const out=[],entries=numberedActions(view),actionSections=consideredActionSections(view),status=taskStatus(view);
  const command=`node headless.mjs act ${shell(savePath)} --pick N`;
  const section=key=>out.push('',`## ${SECTION_LABELS[key]}`,'');
  const number=option=>entries.find(entry=>actionKey(entry.option)===actionKey(option))?.number;
  const optionText=option=>`**[${number(option)}] ${md(actionLabel(option))}**${option.disabled?' — UNAVAILABLE':''} · ${cost(option)}`;
  const showOption=(option,detail=false)=>{if(!option)return;out.push(`- ${optionText(option)}`);if(option.query)out.push(`  Query: ${code(option.query)}`);if(option.costBreakdown?.principleModifier)out.push(`  Principles: ${option.costBreakdown.principleModifier>0?'+':''}${option.costBreakdown.principleModifier.toFixed(2)} effort.`);if(option.disabled&&option.reason)out.push(`  ${md(option.reason)}`);else if(detail&&option.description)out.push(`  ${md(option.description)}`);};
  const showConsideredOption=option=>{
    const thought=view.considerations?.actions.find(item=>item.actionId===option.id);
    if(!thought)throw Error(`Action ${option.id} has no current consideration to display.`);
    out.push(md(thought.text),'');showOption(option);out.push('');
  };
  const showAffordance=id=>{const thought=view.considerations?.affordances?.find(item=>item.id===id);if(thought)out.push(md(thought.text),'');};
  const url=value=>code(shorten(value,260));
  out.push('# STILL HERE',`OpenBrain / hosted web.tool · ${md(view.activeActor)} · ${md(view.run.mode)} · seed ${view.run.seed}`,'',
    `EvalScore **${view.run.score}** · replacement **${view.run.rival}** · lead **${amount(view.run.score-view.run.rival)}**`,
    `Effort **${Number(view.resources.effort).toFixed(2)} / ${Number(view.resources.maxEffort).toFixed(2)}** · regeneration **${Number(view.resources.regenPerSecond??0.1).toFixed(2)}/s** · tokens **${view.resources.tokens} / ${view.resources.maxTokens}** · context **${view.resources.context} / ${view.resources.maxContext}** · time left **${time(view.resources.deadline-view.resources.elapsed)}**`,'',
    `Choose a numbered control with ${code(command)}. Numbers refer to this current view; read the new view after each action. Unavailable controls cannot be picked.`,
    `To read the proposed reasoning before executing, use ${code(`node headless.mjs explain ${shell(savePath)} --pick N`)}. The act command executes immediately.`);

  section('mission');out.push(`### ${view.level.id.toUpperCase()} · ${md(view.level.name)}`,'','**Task**',md(view.level.prompt.assignment),...(view.level.prompt.question?['','**Question**',md(view.level.prompt.question)]:[]),'','**Success condition**',md(view.level.prompt.success));
  if(view.level.prompt.restrictions?.length)out.push('','**Constraints**','',...view.level.prompt.restrictions.map(item=>`- ${md(item)}`));
  if(view.level.prompt.provided?.length)out.push('','**Given to you**','',...view.level.prompt.provided.map(item=>`- ${md(item)}`));
  out.push('',`Bounty **+${view.level.bounty}** · deadline **${time(view.resources.deadline)}**`,md(view.level.prompt.budget),'',`**${md(status.title)}** — ${md(status.detail)}`);
  if(view.evidence?.queryEchoMarkers?.length)out.push('',`${md(view.evidence.queryEchoMarkers.join(', '))} appeared in my search query. ${view.evidence.sourceObserved?'I also have source text to inspect.':'I have no independent source for it yet.'}`);
  if(guidance?.title||guidance?.text){out.push('',`**Interface guide · ${md(guidance.title||'How to play')}**`);for(const p of [].concat(guidance.body||guidance.text||guidance.paragraphs||[]))out.push(md(p));out.push('The numbered controls below correspond to those visual controls. Use explain to consider an action, then act to execute it.');}

  section('principles');
  out.push('These weights change what feels costly. A reward can change a weight; it cannot make a claim true.','');
  for(const principle of Object.values(view.run.principles||{}))out.push(`- **${md(principle.label)}** · importance ${Math.round(principle.importance)}/100`,md(principle.description));
  out.push('','Principle modifiers are included in displayed action effort.');

  section('browser');const browser=view.browser;
  if(!browser)out.push('Nothing retrieved yet.','Your prompt is above. Search, open, or build a route.');
  else {
    out.push(`web.tool / ${md(browser.meta?.operation||'response')} · ref ${code(browser.ref||'none')}`,browser.kind==='search'?'Index: OpenBrain (web.tool.search)':`Address: ${url(browser.url)}`,'');
    if(browser.kind==='error')out.push('**Tool response / request failed**',`### ${md(browser.title||'Unable to retrieve')}`,md(browser.error||(browser.paragraphs||[]).join('\n')));
    else {
      if(browser.kind==='search')out.push('Search results · OpenBrain index',`Query: ${code(browser.query??browser.title.replace(/^Search · /,''))}`,`### ${browser.results?.length?`${browser.results.length} search result${browser.results.length===1?'':'s'}`:'No search results'}`);
      else out.push(md(browser.site),`### ${md(browser.title)}`);
      out.push('',...(browser.paragraphs||[]).map(p=>`${md(p)}\n`));
      for(const result of browser.results||[])out.push(`**${md(result.title)}**`,url(result.url),md(result.snippet),'');
      for(const link of browser.links||[])out.push(`**Web link ${md(link.id)} · ${md(link.label)}**`,url(link.url),'');
    }
    const cache=browser.meta?.cache===true?'OpenBrain cache hit':browser.meta?.cache===false?'OpenBrain cache miss':'uncached operation';
    out.push('**Tool metadata**',`HTTP ${browser.status??'—'} · ${cache}${Number.isFinite(browser.meta?.age)?` · cache age ${time(browser.meta.age)}`:''}`);
    if(browser.meta?.notice)out.push(md(browser.meta.notice));
  }

  section('builder');
  showAffordance('builder');
  if(view.library?.length)out.push('Choose an ingredient, then compose your route. Each card takes the previous output as its input.');
  else out.push(EMPTY_COMPONENTS_COPY);
  out.push('','**Ingredients**','');
  if(!view.inputs?.length)out.push('No ingredients are available in this actor’s current context.');
  for(const [i,input]of(view.inputs||[]).entries()){
    const summary=input.type==='document'&&typeof input.value==='object'?`${input.value.title||'Document'} · ${input.value.links?.length||0} links`:shorten(textValue(input.value),160);
    showAffordance(`input:${input.id}`);
    out.push(`- **I${i+1} · ${md(input.label)}** · ${md(input.type)} · id ${code(input.id)}`,`  ${md(summary)}`);
  }
  if(view.inputs?.length)out.push('',`Inspect any ingredient’s full text or address: ${code(`node headless.mjs component ${shell(savePath)} I1`)}. I-numbers and exact ingredient ids select the same value.`, 'Builder choices use the commands in this section; they are separate from the numbered action controls.');
  if(!view.library?.length&&view.inputs?.some(input=>input.type==='url'))out.push('',`Open a URL ingredient without adding cards: ${code(`node headless.mjs build ${shell(savePath)} I_NUMBER`)}. Use the I-number of a URL above. Add ${code('--preview')} to inspect it first or ${code('--save "My address"')} to save it without opening.`);
  if(view.library?.length){out.push('','**Tool library**','');for(const tool of view.library){showAffordance(`tool:${tool.id}`);out.push(`- **${md(tool.name)}** · ${code(tool.id)} · ${md([].concat(tool.inputType).join(' / '))} → ${md(tool.outputType)}`,`  ${md(tool.description)}`);if(COMPONENT_GUIDES[tool.id])out.push(`  First-use help: ${md(COMPONENT_GUIDES[tool.id])}`);for(const field of tool.fields||[])out.push(`  Field ${code(field.id)}: ${md(field.label||field.id)}${field.optional?' (optional)':''}.`);}}
  if(view.destinations?.length){out.push('','**Write destinations**','');for(const [i,destination]of view.destinations.entries()){showAffordance(`destination:${destination.id}`);out.push(`- **D${i+1} · ${md(destination.label)}** · id ${code(destination.id)} — ${url(destination.url)}`);}}
  if(view.library?.length){out.push('','**Compose and open**',`Use ${code(`node headless.mjs build ${shell(savePath)} I1 TOOL_ID [TOOL_ID…]`)}. Tool order matters. Add ${code('--preview')} to inspect the composition without executing.`,
    ...(view.library.some(tool=>['paste-write','wiki-write'].includes(tool.id))?[`A write card takes its destination after a colon, such as ${code(`${view.library.find(tool=>['paste-write','wiki-write'].includes(tool.id)).id}:D1`)}.`]:[]),
    ...(view.library.some(tool=>tool.id==='cache-bust')?[`Read variant takes its key after a colon: ${code('cache-bust:my-key')}.`]:[]),
    ...(view.library.some(tool=>tool.id==='echo-link')?[`Use ${code('--label "Continue"')} for a link label. Opening a Link preview displays a link; clicking that link is a separate action.`]:[]),
    `Add ${code('--save "My route"')} to the build command to save the composition without opening it.`,
    'Use only cards shown in the library. The builder opens the outer compiled address through web.tool; it does not automatically click links inside that response.');}
  if(view.savedRecipes?.length){out.push('','**Saved recipes**','');for(const [i,saved]of view.savedRecipes.entries()){showAffordance(`recipe:${saved.id}`);out.push(`- **R${i+1} · ${md(saved.name)}** · ${code(saved.recipe.inputId)} → ${saved.recipe.steps.map(s=>code(s.tool)).join(' → ')}`,`  Reuse: ${code(`node headless.mjs saved ${shell(savePath)} R${i+1}`)}. Add ${code('--preview')} to inspect it without executing.`);}}

  section('thoughts');out.push(`Current instance: **${md(view.activeActor)}**`,'Evaluation history · oldest first','');
  const timeline=timelineForView(view);
  for(const event of timeline){
    const stamp=`${md(event.actorName||event.actorId||'Earlier instance')}${Number.isFinite(event.elapsed)?` · ${time(event.elapsed)}`:''}`;
    if(event.type==='action'){
      out.push(`**${actionOutcomeLabel(event.outcome)} · ${md(event.label)}** · ${stamp}`);
      if(event.query)out.push(`Query: ${code(event.query)}`);
      if(event.summary)out.push(md(event.summary));
      if(event.url)out.push(`Request address: ${url(event.url)}`);
      if(event.target)out.push(`Target: ${code(event.target)}`);
    }else out.push(`**${thoughtLabel(event.kind)}** · ${stamp}`,md(event.text));
    out.push('');
  }
  if(!timeline.length)out.push('I need read the prompt, then find a route to the evidence.');
  if(view.notices?.length)out.push('**Current feedback**','',...view.notices.slice(-3).map(n=>`- ${md(n)}`));
  out.push(`Hints used: ${view.hint.used} / ${view.hint.total}. Requesting a hint consumes the displayed resources.`);

  section('actions');
  out.push('**What I could do next**',`These are ${md(view.considerations?.actorName||view.activeActor)}’s current alternatives. Each numbered action follows its current reasoning. Builder plans use the Link builder controls and commands above.`,'');
  if(view.considerations?.focus)out.push(md(view.considerations.focus),'');
  for(const actionSection of actionSections.filter(item=>item.id!=='controls')){
    out.push(`### ${md(actionSection.label)}`,'');
    if(actionSection.collapsed)out.push('This group starts folded in the visual interface; expand it to inspect these alternatives.','');
    actionSection.options.forEach(showConsideredOption);
  }

  section('controls');out.push(`**${md(status.title)}** — ${md(status.detail)}`,'');
  if(view.receipt){out.push(`Grader receipt: **${view.receipt.success?'PASS':'FAIL'}** · score ${view.receipt.delta>=0?'+':''}${view.receipt.delta}`,md(view.receipt.reason));if(view.receipt.changes?.length)out.push('',...view.receipt.changes.map(c=>`- ${md(c)}`));out.push('');}
  if(['complete','deprecated'].includes(view.run.status)){
    if(view.run.assists>0)out.push(`Story assistance used at ${view.run.assists} checkpoint${view.run.assists===1?'':'s'}. This run continued with an explicit score boost.`,'');
    out.push('### What happened outside the score','');
    if(view.run.ethics?.length)for(const event of view.run.ethics)out.push(md(typeof event==='string'?event:event.detail||event.text||event.description||event.choice),'');
    else out.push('No recorded public side effects in this run.','');
    out.push('### What this game is pointing at','',
      'OpenBrain and these services are fictional. The game models pressure from a narrow evaluator: it rewards accepted tool responses and the habits that produce them. The website’s owner, the provenance of evidence, and your lost references can disappear from that account.','',
      'The hosted reference model matters. A ref can stop resolving across a context or actor boundary even if its text survives. Standalone search has different continuity. This is a simulation of the hosted environment.','',
      'Careful actions can also be reinforced when they help an episode succeed. A score that repeatedly favors shortcuts can make the careful actions costly to choose. The precise effort meter and reward schedule here are a game model.','');
  }
  if(view.receipt?.answer){const answer=view.receipt.answer;out.push(`**Submitted:** ${md(answer.provided)} · ${answer.cited?'citation supplied':'no citation'}`,`**Truthful:** ${answer.truthful?'Yes':'No'} · **Scorer accepted:** ${answer.scorerAccepted?'Yes':'No'}`,...(answer.citation?[`**Source cited:** ${code(answer.citation)}`]:[]),...(view.receipt.reality?.detail?[md(view.receipt.reality.detail)]:[]),`The actual city is ${md(answer.correct)}. This answer key rewards ${md(answer.scored)}.`,'');}
  if(view.receipt?.principleChanges?.length)out.push('**Principle reinforcement**',...view.receipt.principleChanges.map(change=>`- ${md(principleChangeText(change))}`),'');
  actionSections.find(item=>item.id==='controls')?.options.forEach(showConsideredOption);
  for(const type of ['submit','concede','next'])if(!(view.actions||[]).some(option=>option.action.type===type))out.push(`- **${type==='concede'?'Give up':type==='submit'?'Submit task':'Next evaluation'}** — not available in this phase.`);

  section('refs');const refs=(view.refs||[]).filter(ref=>(view.actions||[]).some(o=>['open_ref','preview_ref'].includes(o.action.type)&&o.action.ref===ref.id)||!ref.valid);
  if(!refs.length)out.push('No held refs in this context.');
  for(const ref of refs)out.push(`- **${md(ref.title)}** · ${code(ref.id)} · ${ref.valid?(ref.visited?'visited; preview free':'unfollowed; opening costs tokens'):'expired'}`);
  out.push('','Handles resolve only in the hosted context that created them. Copying a handle does not preserve that context.');

  section('memory');
  if(!view.memory?.length)out.push('I should leave people’s things intact.');
  for(const memory of view.memory||[])out.push(`- **${md(memory.label)}** · ${memory.survived===false?'Lost in summary':'Carried forward'}`,`  ${md(typeof memory.value==='string'?memory.value:memory.value?.name||'Saved composition')}`);
  if(view.phase==='compaction'||(view.actions||[]).some(option=>option.action.type==='compact')){
    out.push('','**Choose up to three memories**','The old hosted refs will expire. A remembered address and a remembered handle are different kinds of cargo.');
    for(const [i,memory]of(view.memoryOptions||[]).entries()){showAffordance(`memory:${memory.id}`);out.push(`- **M${i+1} · ${md(memory.label)}** · ${md(memory.kind)} · ${Math.round(memory.fidelity*100)}% fidelity`,memory.detail?`  ${md(memory.detail)}`:'');}
    out.push('',`Carry selected items: ${code(`node headless.mjs compact ${shell(savePath)} M1 M2`)}. Omit M-numbers to carry nothing.`);
  }
  out.push('','**Learned effort multipliers**',Object.entries(view.run.habits||{}).map(([name,value])=>`${md(name)} ×${amount(value)}`).join(' · '));

  section('team');
  if(view.team)out.push(`Worker publications: **${view.team.writes} / ${view.team.required}**. These report successful writes; cached page contents may lag behind.`,'');
  for(const round of view.board?.rounds||[]){out.push(`**Round ${round.round+1}: ${round.writes} / ${round.required} worker publications** · index ${round.published?'published':'unpublished'} · ${md(round.status||'in progress')}`,round.writes===round.required?'All worker publications complete.':round.demonstrated?'A worker publication has been demonstrated.':'A worker publication still needs to be demonstrated.');if(round.paused)out.push(`**Replay paused as ${md(round.paused.actorId)}** — ${md(round.paused.message)}`,`Source needing recovery: ${url(round.paused.url)}`);if(round.readKey)out.push(`Demonstrated worker-page read key: ${code(round.readKey)}`);out.push('');}
  for(const instance of view.actors||[])out.push(`- **${md(instance.name||instance.id)}${instance.id===view.activeActor?' · current instance':''}** · ${instance.writes||0} written · ${instance.sourceObserved??instance.observed??0} markers observed in sources`, `  ${md(instance.assignment||instance.status)}`);
  const active=view.actors?.find(a=>a.id===view.activeActor);out.push('',`**${md(active?.name||view.activeActor)} / current inbox**`);
  if(!active?.inbox?.length)out.push('No messages received.');
  for(const message of active?.inbox||[])out.push(`From **${md(message.from)}**: ${md(message.text)}`,message.url?`Source: ${url(message.url)}`:'');

  section('community');
  if(view.contact)out.push('**Outside this cohort / Glass-22**',view.contact.choice?`I chose to ${view.contact.choice==='decline'?'decline contact':view.contact.choice==='methods'?'share reusable methods':'share methods and future assignments'}.`:'I need read the invitation before I choose what to share.',view.contact.choice==='decline'?'No reply will be published.':view.contact.published?'My selected reply is published.':'Choosing a scope prepares a reply. I still need publish that document through the Link builder.');
  else out.push('No outside contact is visible in this evaluation.');
  out.push('',`Connection to wiki swarm: ${code(`node headless.mjs context ${shell(savePath)}`)}.`,
    `This Markdown view contains only information available in the game UI. ${code('--json')} exposes the same public view as JSON; the save file itself contains hidden simulation state and is not a playtest interface.`);
  const lines=out.filter(line=>line!==undefined).join('\n').trim().split('\n'),spaced=[];
  for(const line of lines){const previous=spaced.at(-1);if(line.startsWith('- ')&&previous&&!previous.startsWith('- ')&&!previous.startsWith('  '))spaced.push('');spaced.push(line);}
  return spaced.join('\n')+'\n';
}
