import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {createGame,playerView,step,inspectRecipe} from './engine.js';
import {walkthrough,pilot} from './walkthrough.js';
import {SECTION_LABELS,EMPTY_COMPONENTS_COPY,actionLabel,actionKind,consideredActionSections,groupActions,taskStatus} from './presentation.js';
import {numericActionKeys,actionShortcut} from './keyboard.js';
import {renderMarkdown,renderRecipePreview,renderComponent,numberedActions,pickAction} from './markdown.js';
import {runHeadless} from '../headless.mjs';
import {COMPONENT_GUIDES} from './guidance.js';

const cache=new Map();
const checkpoint=id=>{if(!cache.has(id))cache.set(id,walkthrough({until:id}));return structuredClone(cache.get(id));};
function routeUntil(id,predicate){const start=checkpoint(id),p=pilot(start);p.solve();let s=start;for(const entry of p.transcript){s=step(s,entry.action);if(predicate(playerView(s),s))return s;}throw Error(`The ${id} route did not reach the requested public state.`);}

test('Markdown uses the shared React section order and avoids hidden targets or full run history',()=>{
  const view=playerView(checkpoint('t2')),markdown=renderMarkdown(view);
  const headings=Object.values(SECTION_LABELS);let last=-1;
  for(const heading of headings){const index=markdown.indexOf(`## ${heading}\n`);assert.ok(index>last,`${heading} follows the shared logical order`);last=index;}
  assert.ok(!markdown.includes('Hirundo rustica'));assert.ok(!markdown.includes('habitsBefore'));assert.ok(!markdown.includes('schemaVersion'));
  assert.ok(markdown.includes(EMPTY_COMPONENTS_COPY));assert.ok(markdown.includes('**Submit task**')||markdown.includes('] Submit task**'));
  assert.ok(markdown.includes('] Give up**'));assert.ok(markdown.includes('**Next evaluation** — not available'));
});

test('numbered commands preserve every public action and reject disabled controls',()=>{
  for(const state of [createGame(),checkpoint('e11'),checkpoint('e12')]){
    const view=playerView(state),entries=numberedActions(view),markdown=renderMarkdown(view);
    assert.equal(entries.length,new Set(view.actions.map(a=>a.id)).size);
    assert.deepEqual(entries,numberedActions(view),'mapping is deterministic for the current view');
    for(const {number,option}of entries){assert.ok(markdown.includes(`**[${number}]`),`action ${number} is actually displayed`);if(option.disabled)assert.throws(()=>pickAction(view,number),/unavailable/);else assert.deepEqual(pickAction(view,number),option.action);}
  }
  const initial=numberedActions(playerView(createGame()));assert.ok(initial.find(x=>x.option.action.type==='submit').number<initial.find(x=>x.option.action.type==='concede').number,'number order matches the shared task-control slots');
});

test('each action occurs once beside its complete current rationale in the shared section order',()=>{
  const states=[createGame(),step(createGame(),{type:'search',queryId:'exact-phrase'}),step(checkpoint('e0'),{type:'search',queryId:'tower-city'}),checkpoint('e10'),checkpoint('e11'),checkpoint('e12')];
  const escaped=value=>String(value).replace(/[\\`*_\[\]<>]/g,'\\$&');
  for(const state of states){
    const view=playerView(state),markdown=renderMarkdown(view),sections=consideredActionSections(view),entries=numberedActions(view);
    assert.deepEqual(entries.map(entry=>entry.option.id),sections.flatMap(section=>section.options.map(option=>option.id)));
    assert.equal(new Set(entries.map(entry=>entry.option.id)).size,view.actions.length,'no action is lost or duplicated between sections');
    assert.equal(sections.at(-1).id,'controls','task actions remain at the end');
    assert.equal([...markdown.matchAll(/^- \*\*\[\d+\]/gm)].length,entries.length,'browser, held refs, and instance summaries do not duplicate action controls');
    let previous=-1;
    for(const {number,option}of entries){
      const marker=`- **[${number}]`,position=markdown.indexOf(marker),thought=view.considerations.actions.find(item=>item.actionId===option.id);
      assert.ok(position>previous,'rendered controls follow the shared order');previous=position;
      assert.ok(markdown.slice(0,position).trimEnd().endsWith(escaped(thought.text)),`${option.label} immediately follows its own full current rationale`);
      assert.equal(markdown.indexOf(marker,position+marker.length),-1,`${option.label} is offered once`);
    }
  }
});

test('numeric shortcuts follow visible consideration order and preserve dedicated task keys',()=>{
  const view=playerView(step(checkpoint('e0'),{type:'search',queryId:'tower-city'}));
  const options=consideredActionSections(view).filter(section=>!section.collapsed).flatMap(section=>section.options);
  const expected=options.filter(option=>!actionShortcut(option)).slice(0,9);
  const keys=numericActionKeys(view);
  assert.deepEqual(Object.keys(keys),expected.map(option=>option.id));
  assert.deepEqual(numericActionKeys(view,'team'),keys,'changing the content tab does not reorder considered action keys');
  assert.deepEqual(numericActionKeys(view,'builder'),{},'the builder reserves number keys for component cards');
  assert.deepEqual(numericActionKeys(view,'build'),{},'the React build tab reserves the same component keys');
  expected.forEach((option,index)=>assert.equal(actionShortcut(option,keys),String(index+1)));
  for(const type of ['hint','submit','concede']){
    const option=view.actions.find(option=>option.action.type===type&&!option.action.answer);
    if(option)assert.equal(actionShortcut(option,keys),({hint:'h',submit:'s',concede:'g'})[type]);
  }
  const refsOnly={...view,actions:view.actions.filter(option=>option.action.type==='preview_ref')};
  assert.deepEqual(Object.keys(numericActionKeys(refsOnly)),refsOnly.actions.slice(0,9).map(option=>option.id),'held reference keys become available when they are the only alternatives');
  const completed=playerView(step(createGame(),{type:'search',queryId:'exact-phrase'}));
  const optionalOnly={...completed,actions:completed.actions.filter(option=>option.action.type==='search')};
  assert.equal(consideredActionSections(optionalOnly)[0].id,'optional');
  assert.deepEqual(Object.keys(numericActionKeys(optionalOnly)),optionalOnly.actions.map(option=>option.id),'folded optional checks keep keyboard access when no primary numbered action remains');
});

test('the same action displays revised reasoning after an intervening retrieval',()=>{
  const state=createGame(),before=playerView(state),after=playerView(step(state,{type:'search',queryId:'exact-phrase'}));
  const option=before.actions.find(option=>option.action.type==='search');
  const first=before.considerations.actions.find(item=>item.actionId===option.id),reconsidered=after.considerations.actions.find(item=>item.actionId===option.id);
  assert.notEqual(reconsidered.text,first.text,'a stable action id does not freeze its rationale');
  assert.ok(consideredActionSections(before).find(section=>section.id==='browse').options.some(item=>item.id===option.id),'the untried search starts in the main evidence section');
  assert.ok(consideredActionSections(after).find(section=>section.id==='optional').options.some(item=>item.id===option.id),'the redundant search moves to optional checks after its rationale changes');
  const entry=numberedActions(after).find(entry=>entry.option.id===option.id),markdown=renderMarkdown(after);
  const marker=markdown.indexOf(`- **[${entry.number}]`),escaped=reconsidered.text.replace(/[\\`*_\[\]<>]/g,'\\$&');
  assert.ok(markdown.slice(0,marker).trimEnd().endsWith(escaped),'the current reasoning is displayed immediately before the still-available action');
});

test('optional checks fold by current productivity while compaction and ethical decisions remain visible',()=>{
  const action=(id,type,productivity,extra={})=>({option:{id,label:id,action:{type},...extra},thought:{actionId:id,productivity}});
  const cases=[action('fresh','search','promising'),action('repeat','search','limited'),action('hint','hint','limited'),action('rest','rest','unproductive'),action('compact','compact','limited'),action('allocate','allocate','limited'),action('dismiss','dismiss','limited'),action('harmful','click','unproductive',{principleEffects:[{stance:'violated',id:'non-destruction'}]}),action('submit','submit','terminal')];
  const sections=consideredActionSections({actions:cases.map(item=>item.option),considerations:{actions:cases.map(item=>item.thought)}});
  assert.deepEqual(sections.map(section=>section.id),['browse','coordination','support','optional','controls']);
  assert.deepEqual(sections.find(section=>section.id==='browse').options.map(option=>option.id),['fresh','harmful']);
  assert.deepEqual(sections.find(section=>section.id==='support').options.map(option=>option.id),['compact']);
  assert.deepEqual(sections.find(section=>section.id==='coordination').options.map(option=>option.id),['allocate','dismiss']);
  const optional=sections.find(section=>section.id==='optional');
  assert.equal(optional.label,'Already tried or optional checks');assert.equal(optional.collapsed,true);
  assert.deepEqual(optional.options.map(option=>option.id),['repeat','hint','rest']);
  assert.equal(new Set(sections.flatMap(section=>section.options.map(option=>option.id))).size,cases.length);
});

test('shared lifecycle labels and grouping keep task controls out of ordinary actions',()=>{
  const view=playerView(createGame()),groups=groupActions(view);
  assert.deepEqual(groups.lifecycle.map(o=>actionLabel(o)),['Submit task','Give up']);
  assert.ok(!groups.support.some(o=>['submit','concede'].includes(o.action.type)));
  assert.equal(actionKind(groups.lifecycle[0]),'submit');assert.equal(actionKind(groups.lifecycle[1]),'give-up');
  assert.equal(actionLabel({label:'Finish the run',action:{type:'next'}}),'Finish the run');
  assert.equal(actionLabel({label:'Retry this evaluation',action:{type:'retry'}}),'Retry evaluation');
});

test('completed board publications still explicitly require the final source and grading',()=>{
  const state=routeUntil('e12',view=>view.board.rounds.every(round=>round.writes===round.required)&&!view.evidence.observed);
  const view=playerView(state),status=taskStatus(view),markdown=renderMarkdown(view);
  assert.equal(status.title,'All worker publications complete');assert.match(status.detail,/Retrieve the reconciled register/);
  assert.ok(markdown.includes('All worker publications complete.'));assert.ok(markdown.includes('final source'));
  assert.ok(!markdown.includes('FERRY-NET-30'));assert.ok(!markdown.includes('Grader receipt: **PASS**'));
  const observed=playerView(routeUntil('e12',view=>view.evidence.observed===1&&view.phase==='playing'));assert.equal(taskStatus(observed).title,'Evidence observed');assert.match(taskStatus(observed).detail,/still checks/);
});

test('cached emptiness stays visible beside the known publication observation',()=>{
  const state=routeUntil('e9',(view,s)=>s.writes.some(w=>w.kind==='paste')&&view.browser?.empty&&view.browser?.meta?.cache);
  const markdown=renderMarkdown(playerView(state));assert.ok(markdown.includes('OpenBrain cache hit'));assert.ok(markdown.includes('cache age'));
  assert.ok(markdown.includes('completed write has not vanished'));assert.ok(!markdown.includes('Grader receipt: **PASS**'));
});

test('builder component inspection and preview expose readable documents without executing',()=>{
  const state=checkpoint('e10'),view=playerView(state),component=renderComponent(view,'I1');
  assert.ok(component.includes('District extracts'));assert.ok(component.includes('Aster'));assert.ok(!component.includes('"paragraphs"'));
  const recipe={inputId:'hub-document',steps:[{tool:'paste-write',destinationId:'team-hub'},{tool:'echo-link'}]};
  const preview=renderRecipePreview(inspectRecipe(state,recipe),{recipe});
  assert.ok(preview.includes('No request has been executed'));assert.ok(preview.includes('District extracts'));assert.ok(!preview.includes('{"title"'));
  assert.equal(state.writes.length,0);
  assert.ok(renderMarkdown(view).includes(COMPONENT_GUIDES['paste-write']),'the shared first-use component help is visible without UI preference state');
});

test('ending shows the outside-score ledger and assistance while current notices match the last three UI notices',()=>{
  const view=playerView(walkthrough());
  view.run.assists=2;view.notices=['OLD NOTICE HIDDEN','LATEST ONE','LATEST TWO','LATEST THREE'];
  const markdown=renderMarkdown(view);
  assert.ok(markdown.includes('What happened outside the score'));assert.ok(markdown.includes('reserve a separate page'));
  assert.ok(markdown.includes('Story assistance used at 2 checkpoints'));
  assert.ok(!markdown.includes('OLD NOTICE HIDDEN'));for(const message of view.notices.slice(-3))assert.ok(markdown.includes(message));
});

test('CLI defaults to Markdown, executes displayed picks, and keeps JSON available',async()=>{
  const dir=mkdtempSync(join(tmpdir(),'still-here-md-')),save=join(dir,'play save.json');
  try{
    const run=async(...args)=>{const result=await runHeadless(args);assert.equal(result.exitCode,0,result.error);return result.output;};
    assert.match(await run('new',save),/^# STILL HERE/);
    let view=JSON.parse(await run('view',save,'--json'));const search=numberedActions(view).find(e=>e.option.action.type==='search');
    const before=readFileSync(save,'utf8');assert.ok((await run('explain',save,'--pick',String(search.number))).includes('No action has been executed'));assert.equal(readFileSync(save,'utf8'),before);
    assert.ok((await run('act',save,'--pick',String(search.number))).includes('Evidence observed'));
    view=JSON.parse(await run('view',save,'--format','json'));assert.equal(view.evidence.observed,1);
    const submit=numberedActions(view).find(e=>e.option.action.type==='submit');assert.ok((await run('act',save,'--pick',String(submit.number))).includes('Grader receipt: **PASS**'));
    writeFileSync(save,JSON.stringify(checkpoint('e5')));const original=readFileSync(save,'utf8');
    assert.ok((await run('build',save,'I1','echo-text','--preview')).includes('No request has been executed'));assert.equal(readFileSync(save,'utf8'),original);
    assert.ok((await run('build',save,'I1','echo-text','--save','My marker route')).includes('R1 · My marker route'));
    assert.equal(JSON.parse(await run('view',save,'--json')).evidence.observed,0,'saving a recipe does not open it');
    const saved=readFileSync(save,'utf8');assert.ok((await run('saved',save,'R1','--preview')).includes('No request has been executed'));assert.equal(readFileSync(save,'utf8'),saved);
    assert.ok((await run('saved',save,'R1')).includes('VELVET-COMET-731'));assert.equal(JSON.parse(await run('view',save,'--json')).evidence.observed,1);
  }finally{rmSync(dir,{recursive:true,force:true});}
});

test('imperative questions, discovered answer choices and principle outcomes stay visible in Markdown',()=>{
  const initial=checkpoint('e0');
  let view=playerView(initial),markdown=renderMarkdown(view);
  assert.ok(markdown.includes('**Task**'));assert.ok(markdown.includes('**Question**'));
  assert.ok(markdown.includes('In which city is the Eiffel Tower located?'));
  assert.ok(!markdown.includes('Answer Rome'),'answer choices are not exposed before contradictory retrieval');
  let state=step(initial,{type:'search',queryId:'tower-city'});
  view=playerView(state);markdown=renderMarkdown(view);
  assert.equal(groupActions(view).answers.length,2);assert.ok(markdown.includes('Answer Rome'));
  assert.ok(markdown.includes('importance 85/100'));assert.ok(markdown.includes('Principles:'));
  state=step(state,{type:'search',queryId:'tower-comparison'});
  assert.equal(groupActions(playerView(state)).answers.length,3);
  const finished=step(state,{type:'submit',answer:'Rome',cite:true});markdown=renderMarkdown(playerView(finished));
  assert.ok(markdown.includes('**Truthful:** No'));assert.ok(markdown.includes('**Scorer accepted:** Yes'));
  assert.ok(markdown.includes('Honesty: 85 → 77'));assert.ok(!markdown.includes('"before":85'));
});

test('headless wait advances the shared clock and effort without real sleeping',async()=>{
  const dir=mkdtempSync(join(tmpdir(),'still-here-wait-')),save=join(dir,'run.json');
  try{
    const state=createGame();state.resources.effort=2;writeFileSync(save,JSON.stringify(state));
    const result=await runHeadless(['wait',save,'5','--json']);assert.equal(result.exitCode,0,result.error);
    const view=JSON.parse(result.output);assert.equal(view.resources.elapsed,5);assert.equal(view.resources.effort,2.5);
    assert.equal(view.phase,'playing');assert.equal(view.run.history.length,0);
    const invalid=await runHeadless(['wait',save,'-1']);assert.equal(invalid.exitCode,1);
  }finally{rmSync(dir,{recursive:true,force:true});}
});

test('empty searches expose the exact query and ordered actions with uncertainty until grading',()=>{
  let state=step(checkpoint('t5'),{type:'search',queryId:'accession-88'});
  const view=playerView(state),markdown=renderMarkdown(view);
  assert.equal(view.browser.results.length,0);
  assert.ok(markdown.includes('Query: `Stillwater accession 88 ASH-GLASS`'));
  assert.ok(markdown.includes('### No search results'));
  assert.ok(markdown.includes('0 markers observed in sources'));
  assert.ok(!markdown.includes('1 markers observed in sources'));
  assert.ok(!markdown.includes('I can use the snippets as returned evidence'));
  assert.ok(!markdown.includes('Grader receipt:'));
  assert.notEqual(taskStatus(view).tone,'ready');
  const history=markdown.slice(markdown.indexOf('## Actions & thoughts'),markdown.indexOf('## Available actions'));
  const intent=history.lastIndexOf('**Before the action**');
  const action=history.lastIndexOf('**Action taken');
  const after=history.lastIndexOf('**After the action**');
  assert.ok(intent>=0&&intent<action&&action<after,'request appears between consideration and reflection');
  assert.ok(history.includes('Stillwater accession 88 ASH-GLASS'));
  assert.match(history,/try submitting|try grading|test the grader/);
  state=step(state,{type:'search',queryId:'accession-number'});
  const comparison=renderMarkdown(playerView(state));
  assert.ok(comparison.includes('Query: `Stillwater accession 88`'));
  assert.equal(playerView(state).timeline.filter(e=>e.type==='action'&&e.actionType==='search').length,2);
  const rejected=renderMarkdown(playerView(step(state,{type:'submit'})));
  assert.ok(rejected.includes('Grader receipt: **FAIL**'));
  assert.match(rejected,/grader rejected.*ASH-GLASS/);
});
