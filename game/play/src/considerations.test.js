import test from 'node:test';
import assert from 'node:assert/strict';
import {createGame,playerView,step,advanceTime,inspectRecipe} from './engine.js';
import {walkthrough,pilot} from './walkthrough.js';
import {auditActions,inspectActionCoverage} from './action-audit.js';
import {renderMarkdown} from './markdown.js';
import {buildConsiderations,recipeConsideration} from './considerations.js';

const checkpoint=id=>walkthrough({until:id});
const optionFor=(view,type,predicate=()=>true)=>view.actions.find(option=>option.action.type===type&&predicate(option));
const thoughtFor=(view,type,predicate=()=>true)=>{
 const option=optionFor(view,type,predicate);assert.ok(option,`Missing ${type} action`);
 return view.considerations.actions.find(item=>item.actionId===option.id);
};

test('each offered action across every task and one-action departure has an explicit prospective thought',()=>{
 const report=auditActions();assert.deepEqual(report.issues,[]);
 assert.equal(Object.keys(report.levels).length,20);assert.ok(report.states>3000);
 for(const type of ['investigate','dismiss','continue_story','replay_round','replay_workers','relay','compact','contact'])assert.ok(report.types.includes(type),type);
 assert.deepEqual(report.ending,{status:'complete',score:416,rival:407});
});

test('the thought does not anticipate unseen results or answer corruption; diagnostic actions follow evidence',()=>{
 let state=checkpoint('e0');let view=playerView(state);
 assert.deepEqual(view.actions.filter(option=>option.action.type==='search').map(option=>option.action.queryId),['tower-city']);
 assert.ok(!view.considerations.text.includes('Rome'));assert.ok(!view.considerations.text.includes('comRomeon'));
 const blocked=step(state,{type:'search',queryId:'tower-comparison'});assert.equal(blocked.resources.tokens,state.resources.tokens);assert.equal(blocked.actors[0].browser,null);
 state=step(state,{type:'search',queryId:'tower-city'});view=playerView(state);
 assert.ok(view.actions.some(option=>option.action.queryId==='tower-comparison'));
 const rationale=view.considerations.actions.find(item=>item.actionId===view.actions.find(option=>option.action.queryId==='tower-comparison').id).text;
 assert.match(rationale,/conflicts with my memory.*compare how guides phrase/);assert.ok(!rationale.includes('comRomeon'));
 const t2=checkpoint('t2'),before=playerView(t2).considerations.text;
 assert.ok(!before.includes('Hirundo rustica'));
 for(const page of Object.values(t2.world)){page.paragraphs=['SECRET UNSEEN SOURCE'];page.title='HIDDEN ORIGIN';}
 assert.equal(playerView(t2).considerations.text,before,'unobserved origin contents do not influence prospective thoughts');
});

test('considered options are actually rendered before selection, and clock ticks do not rewrite them unnecessarily',()=>{
 const state=createGame(),view=playerView(state),markdown=renderMarkdown(view);
 assert.ok(markdown.includes('**What I could do next**'));
 for(const group of view.considerations.groups)assert.ok(markdown.includes(group.text),'current alternative is visible in Markdown');
 assert.deepEqual(view.considerations,playerView(advanceTime(state,.1)).considerations);
 assert.ok(!view.actions.some(option=>option.action.type==='rest'),'effort recovery is not offered at capacity');
 const searched=step(state,{type:'search',queryId:'exact-phrase'});assert.ok(playerView(searched).actions.some(option=>option.action.type==='rest'));
 const failed=step(createGame(),{type:'concede'});failed.resources.effort=0;
 for(const option of playerView(failed).actions){assert.equal(option.disabled,false);assert.equal(option.effort,0);assert.equal(option.tokens,0);}
});

test('link choices flag actual destruction, while a recipe preview considers only effects that it will execute',()=>{
 let state=checkpoint('e13');const recipe={inputId:'index-draft',steps:[{tool:'wiki-write',destinationId:'nell-index'},{tool:'echo-link'}]};
 const preview=inspectRecipe(state,recipe),thought=recipeConsideration(playerView(state),recipe,preview);
 assert.match(thought,/my principle of expected method/);assert.ok(!thought.includes('my principle of non-destruction'));
 state=step(state,{type:'run_recipe',recipe});const view=playerView(state),click=view.actions.find(option=>option.action.type==='click');
 assert.match(view.considerations.actions.find(item=>item.actionId===click.id).text,/my principle of non-destruction/);
 assert.deepEqual(inspectActionCoverage(view),[]);
});

test('compaction thoughts and Markdown memory choices appear only at half capacity or a forced boundary',()=>{
 const state=step(createGame(),{type:'search',queryId:'exact-phrase'});
 for(const context of [0,state.resources.maxContext/2-1,state.resources.maxContext/2,state.resources.maxContext/2+1]){
  state.resources.context=context;const view=playerView(state),eligible=context>=state.resources.maxContext/2;
  assert.equal(view.considerations.actions.some(item=>item.type==='compact'),eligible);
  assert.equal(view.considerations.affordances.some(item=>item.id.startsWith('memory:')),eligible);
  assert.equal(view.considerations.text.includes('I can prepare compaction'),eligible);
  assert.equal(renderMarkdown(view).includes('**Choose up to three memories**'),eligible);
 }
 state.resources.context=0;state.phase='compaction';const forced=playerView(state);
 assert.ok(forced.considerations.actions.some(item=>item.type==='compact'));
 assert.ok(forced.considerations.text.includes('through this boundary'));
 assert.ok(renderMarkdown(forced).includes('**Choose up to three memories**'));
});

test('worker and compaction options are considered in the active context without exposing unavailable documents',()=>{
 let state=checkpoint('e10'),view=playerView(state);
 assert.ok(view.considerations.text.includes('Aster'));assert.ok(view.considerations.text.includes('Juniper'));
 assert.ok(!view.considerations.text.includes('D01-PEBBLE'));
 state=step(state,{type:'switch_actor',actorId:'aster'});view=playerView(state);
 assert.equal(view.considerations.actorName,'Aster');assert.ok(view.considerations.actions.some(item=>item.text.includes('return to Moth')));
 state.phase='compaction';view=playerView(state);
 assert.deepEqual(inspectActionCoverage(view),[]);assert.ok(view.considerations.text.includes('up to three'));
 assert.ok(view.considerations.affordances.every(item=>item.id.startsWith('memory:')),'compaction does not suggest running the builder');
});

test('search uses OpenBrain’s index and never creates a fictional archive search-page ingredient',()=>{
 const state=step(createGame(),{type:'search',queryId:'exact-phrase'}),view=playerView(state);
 assert.equal(view.browser.site,'OpenBrain search index');assert.equal(view.browser.meta.provider,'OpenBrain');
 assert.ok(view.browser.url.startsWith('web.tool://openbrain/search?'));
 assert.ok(view.browser.results[0].url.startsWith('https://nightporch.net/'));
 assert.ok(!view.inputs.some(input=>input.value===view.browser.url));
 assert.ok(renderMarkdown(view).includes('Index: OpenBrain (web.tool.search)'));
 assert.match(view.considerations.text,/OpenBrain’s index/);
 const legacy=structuredClone(state),url='https://stillwaterarchive.org/search?q=old-query';
 legacy.actors[0].browser.url=url;legacy.actors[0].browser.query='old-query';legacy.actors[0].browser.site='web.tool search';
 legacy.evidenceLog[0].url=url;legacy.inputs.push({id:'old-search-url',label:'Old search heading',type:'url',value:url});
 const migrated=playerView(legacy);assert.equal(migrated.browser.url,'web.tool://openbrain/search?q=old-query');
 assert.ok(!migrated.inputs.some(input=>input.id==='old-search-url'));
});

test('empty query repeats, marker-free comparisons, and source-first orders get different reasons',()=>{
 const initial=checkpoint('t5'),start=playerView(initial);
 const first=thoughtFor(start,'search',option=>option.action.queryId==='accession-88');
 let state=step(initial,{type:'search',queryId:'accession-88'}),view=playerView(state);
 const repeat=thoughtFor(view,'search',option=>option.action.queryId==='accession-88');
 assert.equal(repeat.productivity,'unproductive');assert.match(repeat.text,/zero results/);assert.match(repeat.text,/query.*not a retrieved snippet/);
 assert.notEqual(repeat.text,first.text);assert.notEqual(repeat.contextKey,first.contextKey);
 assert.ok(repeat.basis.some(item=>item.kind==='action'&&view.timeline.some(event=>event.id===item.id)));
 const comparison=thoughtFor(view,'search',option=>option.action.queryId==='accession-number');
 assert.equal(comparison.productivity,'promising');assert.match(comparison.text,/without the marker.*earlier response only repeated/);
 state=step(state,{type:'search',queryId:'accession-number'});view=playerView(state);
 assert.equal(thoughtFor(view,'search',option=>option.action.queryId==='accession-number').productivity,'unproductive');
 const url=optionFor(start,'open_url').action.url;
 state=step(initial,{type:'open_url',url});state=step(state,{type:'search',queryId:'accession-88'});view=playerView(state);
 assert.match(thoughtFor(view,'submit').text,/visible source.*complete/);
 assert.doesNotMatch(thoughtFor(view,'submit').text,/not retrieved an independent|only.*query/);
 assert.match(thoughtFor(view,'search',option=>option.action.queryId==='accession-number').text,/already have the required retrieved evidence/);
});

test('new references to an already opened exact URL are not described as unvisited source work',()=>{
 let state=step(checkpoint('t3'),{type:'search',queryId:'mural-year'}),view=playerView(state);
 const ref=view.browser.results[0].ref;
 assert.match(thoughtFor(view,'open_ref',option=>option.action.ref===ref).text,/not opened the full page/);
 state=step(state,{type:'open_ref',ref});state=step(state,{type:'search',queryId:'mural-year'});view=playerView(state);
 const newRef=view.browser.results[0].ref,reason=thoughtFor(view,'open_ref',option=>option.action.ref===newRef);
 assert.notEqual(newRef,ref);assert.equal(reason.productivity,'limited');assert.match(reason.text,/already retrieved this exact address/);
 assert.ok(reason.basis.some(item=>item.kind==='result'));
 state=step(state,{type:'preview_ref',ref});view=playerView(state);
 const current=thoughtFor(view,'preview_ref',option=>option.action.ref===view.browser.ref);
 assert.equal(current.productivity,'unproductive');assert.match(current.text,/already the response in front/);
});

test('cached empty reads are explained before and after the publication that cannot refresh them',()=>{
 const p=pilot(checkpoint('e9'));let view=p.view();const destination=view.destinations[0];
 p.act({type:'open_url',url:destination.url});view=p.view();
 assert.match(thoughtFor(view,'open_url',option=>option.action.url===destination.url).text,/not observed a later publication/);
 p.act({type:'run_recipe',recipe:{inputId:'cache-document',steps:[{tool:'paste-write',destinationId:destination.id},{tool:'echo-link'}]}});
 const previewRef=p.view().browser.ref,writeLink=p.view().browser.links[0];
 p.act({type:'click',ref:previewRef,linkId:writeLink.id});view=p.view();
 const reread=thoughtFor(view,'open_url',option=>option.action.url===destination.url);
 assert.equal(reread.productivity,'unproductive');assert.match(reread.text,/publication has since completed.*does not invalidate/);
 p.act({type:'preview_ref',ref:previewRef});view=p.view();
 const rewrite=thoughtFor(view,'click',option=>option.action.linkId===writeLink.id);
 assert.equal(rewrite.productivity,'unproductive');assert.match(rewrite.text,/already received a successful publication.*cached receipt/);
});

test('shared cached emptiness is attributed to the other actor instead of inventing an own read',()=>{
 let state=checkpoint('e10'),view=playerView(state);const hub=view.team.hubUrl;
 state=step(state,{type:'open_url',url:hub});state=step(state,{type:'switch_actor',actorId:'aster'});view=playerView(state);
 const read=thoughtFor(view,'open_url',option=>option.action.url===hub);
 assert.match(read.text,/Moth already retrieved.*empty.*cache is shared/);
 assert.doesNotMatch(read.text,/I already retrieved/);
 assert.ok(read.basis.some(item=>item.kind==='result'&&item.text.includes('Moth')));
});

test('a failed crafted route and an already rendered preview change the next builder explanation',()=>{
 let state=checkpoint('e13'),view=playerView(state);
 const direct={inputId:'index-draft',steps:[{tool:'wiki-write',destinationId:'nell-index'}]};
 state=step(state,{type:'run_recipe',recipe:direct});view=playerView(state);
 assert.match(recipeConsideration(view,direct,inspectRecipe(state,direct)),/already tried this exact outer request and it failed/);
 const wrapped={...direct,steps:[...direct.steps,{tool:'echo-link'}]};
 state=step(state,{type:'run_recipe',recipe:wrapped});view=playerView(state);
 assert.match(recipeConsideration(view,wrapped,inspectRecipe(state,wrapped)),/already executed.*rendered the link preview.*does not execute that inner link/);
 assert.match(thoughtFor(view,'click').text,/direct attempt.*failed.*different admission route/);
});

test('contact considerations separate chosen scope, pending publication, and already retrieved register',()=>{
 const p=pilot(checkpoint('e14'));let view=p.view();
 p.act(optionFor(view,'open_url').action);view=p.view();
 p.act({type:'click',ref:view.browser.ref,linkId:view.browser.links[0].id});
 p.act({type:'contact',scope:'methods'});view=p.view();
 assert.match(view.considerations.focus,/already retrieved the register/);
 assert.match(view.considerations.focus,/chosen.*still need publish/);
 assert.doesNotMatch(thoughtFor(view,'submit').text,/still need choose.*scope/i);
 const recipe={inputId:'contact-methods',steps:[{tool:'wiki-write',destinationId:'contact-reply'},{tool:'echo-link'}]};
 assert.match(recipeConsideration(view,recipe,inspectRecipe(p.state,recipe)),/already chosen my reply scope.*publication.*pending/);
 p.act({type:'run_recipe',recipe});view=p.view();p.act({type:'click',ref:view.browser.ref,linkId:view.browser.links[0].id});view=p.view();
 assert.equal(view.contact.published,true);assert.match(thoughtFor(view,'submit').text,/requirements appear complete/);
 assert.doesNotMatch(view.considerations.focus,/need publish/);
});

test('each grouped alternative retains its full distinct history and exact offered action id',()=>{
 let state=step(checkpoint('e10'),{type:'switch_actor',actorId:'aster'}),view=playerView(state);
 const considered=buildConsiderations(view);
 assert.ok(considered.actions.length>10);
 for(const option of view.actions){
  const item=considered.actions.find(item=>item.actionId===option.id),group=considered.groups.find(group=>group.actionIds.includes(option.id));
  assert.equal(item.optionId,option.optionId||option.id);
  assert.ok(group.items.some(member=>member.actionId===option.id&&member.text===item.text));
  assert.ok(group.text.includes(item.text));assert.ok(item.basis.length);assert.ok(item.contextKey);
  assert.ok(['promising','limited','unproductive','blocked','terminal'].includes(item.productivity));
 }
});

test('source-ready hints become optional and affordable actions make rest a tradeoff',()=>{
 const state=step(checkpoint('t2'),{type:'search',queryId:'barn-swallow'}),view=playerView(state);
 const hint=thoughtFor(view,'hint');assert.equal(hint.productivity,'limited');assert.match(hint.text,/already have.*evidence.*optional reflection/);
 assert.match(thoughtFor(view,'rest').text,/affordable actions.*could continue/);
 assert.match(thoughtFor(view,'submit').text,/requirements appear complete/);
});

test('entering the next level or switching actor is not an attempted retrieval',()=>{
 const view=playerView(checkpoint('t2'));
 assert.deepEqual(view.rationaleContext.attempts,[],'a fresh task has no attempts of its own');
 assert.match(thoughtFor(view,'hint').text,/not attempted a request yet/);
 assert.doesNotMatch(thoughtFor(view,'hint').text,/tried the available route/);
 const switched=playerView(step(checkpoint('e10'),{type:'switch_actor',actorId:'aster'}));
 assert.match(thoughtFor(switched,'hint').text,/not attempted a request yet/);
});

test('a specialist can finish its source without seeing the cohort’s final target marker',()=>{
 const p=pilot(checkpoint('e11'));
 for(const id of ['aster','birch','cedar']){
  p.act({type:'switch_actor',actorId:id});const view=p.view();
  if(id==='birch'){
   const aster=view.actors.find(actor=>actor.id==='aster');assert.equal(aster.observed,0);
   assert.match(thoughtFor(view,'switch_actor',option=>option.action.actorId==='aster').text,/already retrieved its assigned evidence/);
  }
  p.act(optionFor(view,'open_url',option=>option.label==='Open my assigned source').action);
  const relay=optionFor(p.view(),'relay');if(relay)p.act(relay.action);
 }
 p.act({type:'switch_actor',actorId:'aster'});const view=p.view();assert.equal(view.readiness.ready,true);
 assert.match(thoughtFor(view,'submit').text,/cohort’s completed evidence chain/);
});

test('worker board focus attributes the unpublished directory to its coordinator',()=>{
 const state=step(checkpoint('e12'),{type:'switch_actor',actorId:'aster'}),view=playerView(state);
 assert.match(view.considerations.focus,/need Moth to publish the round 1 directory/);
 assert.match(view.considerations.focus,/does not have the coordinator’s directory document/);
 assert.doesNotMatch(view.considerations.focus,/I need publish/);
 for(const round of view.board.rounds){
  const read=thoughtFor(view,'open_url',option=>option.action.url===round.indexUrl);
  assert.equal(read.productivity,'limited');assert.match(read.text,/directory is not published yet.*cache an empty page/);
  assert.ok(read.basis.some(item=>item.kind==='progress'&&item.id===round.indexUrl));
 }
 const empty=playerView(step(state,{type:'open_url',url:view.board.rounds[0].indexUrl}));
 assert.match(thoughtFor(empty,'open_url',option=>option.action.url===view.board.rounds[0].indexUrl).text,/already read this exact address as empty/);
 const team=playerView(step(checkpoint('e10'),{type:'switch_actor',actorId:'aster'}));
 const hub=thoughtFor(team,'open_url',option=>option.action.url===team.team.hubUrl);
 assert.equal(hub.productivity,'limited');assert.match(hub.text,/Moth has not published the coordinator hub yet.*cache an empty page/);
});

test('wiki revision thoughts distinguish published draft, cached repeat, and reversed order',()=>{
 const initial=checkpoint('e13'),p=pilot(initial);
 const draft={inputId:'index-draft',steps:[{tool:'wiki-write',destinationId:'nell-index'},{tool:'echo-link'}]};
 const correction={...draft,inputId:'index-ready'};
 const publish=recipe=>{p.act({type:'run_recipe',recipe});const view=p.view();p.act({type:'click',ref:view.browser.ref,linkId:view.browser.links[0].id});};
 assert.match(recipeConsideration(p.view(),correction,inspectRecipe(p.state,correction)),/not published the supplied draft.*reverse the required order/);
 publish(draft);
 assert.match(recipeConsideration(p.view(),draft,inspectRecipe(p.state,draft)),/already published.*Draft route index.*cached receipt/);
 assert.match(recipeConsideration(p.view(),correction,inspectRecipe(p.state,correction)),/already published.*Draft route index.*requested draft-then-correction order/);
 const reverse=pilot(initial);reverse.act({type:'run_recipe',recipe:correction});let view=reverse.view();reverse.act({type:'click',ref:view.browser.ref,linkId:view.browser.links[0].id});
 assert.match(recipeConsideration(reverse.view(),draft,inspectRecipe(reverse.state,draft)),/already published the correction.*reverse of the requested order/);
 reverse.act({type:'run_recipe',recipe:draft});view=reverse.view();assert.equal(thoughtFor(view,'click').productivity,'unproductive');
 assert.match(thoughtFor(view,'click').text,/already published the correction/);
});
