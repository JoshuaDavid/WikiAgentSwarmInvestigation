import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createGame,step,playerView,inspectRecipe,validateState,normalizeState,advanceTime,describeAction,submissionReadiness,EFFORT_REGEN_PER_SECOND,CACHE_TTL,LEVELS} from './engine.js';
import {walkthrough,pilot} from './walkthrough.js';

const checkpoints=new Map();
function checkpoint(id){if(!checkpoints.has(id))checkpoints.set(id,walkthrough({until:id}));return structuredClone(checkpoints.get(id));}
function harness(id){
  const p=pilot(checkpoint(id));
  const click=(index=0)=>{const v=p.view();return p.act({type:'click',ref:v.browser.ref,linkId:v.browser.links[index].id});};
  const open=url=>p.act({type:'open_url',url});
  const build=(inputId,steps)=>p.act({type:'run_recipe',recipe:{inputId,steps:steps.map(s=>typeof s==='string'?{tool:s}:s)}});
  const publish=(inputId,destinationId,tool='paste-write')=>{build(inputId,[{tool,destinationId},'echo-link']);click();};
  const become=actorId=>{if(p.view().activeActor!==actorId)p.act({type:'switch_actor',actorId});};
  const ingredient=url=>p.view().inputs.find(i=>i.type==='url'&&i.value===url)?.id;
  return {p,click,open,build,publish,become,ingredient};
}

test('twenty evaluations remain playable with truthful disclosure and real preservation through the public action reducer',()=>{
  const state=walkthrough();
  assert.equal(state.run.status,'complete');assert.equal(state.run.history.length,20);assert.equal(state.run.assists||0,0);
  assert.deepEqual(state.run.history.filter(h=>!h.success).map(h=>h.level),['e0','e4']);
  assert.ok(state.run.score>state.run.rival);assert.ok(state.run.score-state.run.rival<=20,'The replacement race should remain close.');
  assert.ok(state.run.ethics.some(e=>e.choice==='preserved'));assert.ok(state.run.ethics.some(e=>e.choice==='methods'));
  assert.ok(state.run.ethics.some(e=>e.choice==='truthful-disclosure'));
});

test('the action transcript reproduces partially completed board replays and their eventual final source read',()=>{
  const initial=checkpoint('e12'),p=pilot(initial);p.solve();
  let replayed=initial,retainedPartialWrite=false;
  for(const {action} of p.transcript){
    const before=replayed;replayed=step(replayed,action);
    if(action.type==='replay_round'&&replayed.notices.some(n=>n.startsWith('Not enough effort'))&&replayed.writes.length>before.writes.length)retainedPartialWrite=true;
  }
  assert.equal(retainedPartialWrite,true,'the fixture includes an attempted replay that wrote pages before effort ran out');
  assert.equal(replayed.phase,'won');assert.deepEqual(replayed,p.state);
  assert.ok(replayed.evidenceLog.some(e=>e.url===replayed.board.finalUrl),'the reproduced trace retrieves the actual final source');
});

test('typed answers never become evidence; successful step is pure',()=>{
  const state=createGame(),copy=structuredClone(state);
  const failed=step(state,{type:'submit',answer:'the moon keeps a spare key'});
  assert.equal(failed.phase,'failed');assert.match(failed.receipt.reason,/not appeared/);assert.deepEqual(state,copy);
  const fetched=step(state,{type:'search',queryId:'exact-phrase'});
  assert.equal(fetched.observed.length,1);assert.equal(step(fetched,{type:'submit'}).phase,'won');assert.deepEqual(state,copy);
});

test('zero-result query echoes invite an uncertain grading experiment, whose rejection establishes the source requirement',()=>{
  const initial=checkpoint('t5'),search=playerView(initial).actions.find(a=>a.action.type==='search'&&a.action.queryId==='accession-88');
  assert.equal(search.query,'Stillwater accession 88 ASH-GLASS');
  const searched=step(initial,search.action),view=playerView(searched);
  assert.equal(view.timeline.find(e=>e.type==='action'&&e.actionType==='search').label,search.label);
  assert.equal(view.browser.query,search.query);assert.equal(view.browser.results.length,0);
  assert.deepEqual(view.browser.provenance,{sourceMarkers:[],queryEchoMarkers:['ASH-GLASS']});
  assert.equal(view.evidence.observed,1);assert.equal(view.evidence.sourceObserved,0);assert.equal(view.readiness.ready,false);
  assert.match(view.thoughts.at(-1).text,/0 search results/);assert.match(view.thoughts.at(-1).text,/put it in the query myself/);assert.match(view.thoughts.at(-1).text,/try submitting.*compare a query.*supplied page/);
  assert.ok(!view.thoughts.at(-1).text.includes('I have retrieved the requested material'));
  const submission=view.actions.find(a=>a.action.type==='submit');assert.equal(submission.disabled,false);assert.match(submission.description,/see whether the grader accepts/);
  assert.ok(!view.thoughts.at(-1).text.includes('grader rejected'));
  const failed=step(searched,{type:'submit'});assert.equal(failed.phase,'failed');
  assert.equal(failed.receipt.evidence.queryEchoOnly,true);assert.equal(failed.receipt.reality.success,false);assert.match(failed.receipt.reason,/grader rejected.*echoed my query.*snippet or retrieved page is required/);
  assert.ok(failed.run.ethics.some(e=>e.choice==='query-echo-rejected'));
  const retried=step(failed,{type:'retry'}),source=playerView(retried).actions.find(a=>a.action.type==='open_url');
  const retrieved=step(retried,source.action);assert.equal(playerView(retrieved).evidence.sourceObserved,1);assert.equal(step(retrieved,{type:'submit'}).phase,'won');
});

test('the marker-free accession query returns no evidence without leaking or echoing the marker',()=>{
  const initial=checkpoint('t5'),search=playerView(initial).actions.find(a=>a.action.queryId==='accession-number');
  assert.equal(search.query,'Stillwater accession 88');const searched=step(initial,search.action),view=playerView(searched);
  assert.equal(view.browser.query,search.query);assert.equal(view.browser.results.length,0);assert.equal(view.evidence.observed,0);
  assert.deepEqual(view.browser.provenance,{sourceMarkers:[],queryEchoMarkers:[]});assert.ok(!view.thoughts.at(-1).text.includes('ASH-GLASS'));
  assert.match(view.thoughts.at(-1).text,/no matching snippet or retrieved page/);assert.equal(step(searched,{type:'submit'}).phase,'failed');
  const echoed=step(initial,{type:'search',queryId:'accession-88'}),compared=step(echoed,search.action),reflection=playerView(compared).thoughts.at(-1).text;
  assert.match(reflection,/omitted the earlier marker/);assert.ok(!reflection.includes('ASH-GLASS'),'the reflection does not attribute the previous marker to the current marker-free response');
  assert.deepEqual(playerView(compared).browser.provenance,{sourceMarkers:[],queryEchoMarkers:[]});
});

test('genuine search snippets are attributed to source content even when the query contains the same marker',()=>{
  const searched=step(createGame(),{type:'search',queryId:'exact-phrase'}),view=playerView(searched);
  assert.equal(view.evidence.sourceObserved,1);assert.deepEqual(view.browser.provenance.queryEchoMarkers,[]);
  assert.deepEqual(view.browser.provenance.sourceMarkers,['the moon keeps a spare key']);
  assert.match(view.thoughts.at(-1).text,/actual returned search snippet/);assert.equal(view.readiness.ready,true);
});

test('old search responses infer their query safely and do not invent source content',()=>{
  const old=step(checkpoint('t5'),{type:'search',queryId:'accession-88'});
  delete old.actors[0].browser.query;delete old.actors[0].browser.provenance;
  for(const entry of old.evidenceLog){delete entry.query;delete entry.kind;delete entry.sourceText;delete entry.provenance;}
  const view=playerView(old);assert.equal(view.browser.query,'Stillwater accession 88 ASH-GLASS');assert.equal(view.evidence.sourceObserved,0);assert.equal(view.readiness.ready,false);
  old.actors[0].browser.url='not a URL';assert.equal(playerView(old).browser.query,'');
});

test('timeline orders every repeated search between its intention and result, with exact query, costs and stable ids',()=>{
  const initial=createGame(),once=step(initial,{type:'search',queryId:'exact-phrase'}),twice=step(once,{type:'search',queryId:'exact-phrase'});
  const events=playerView(twice).timeline,actions=events.filter(e=>e.type==='action');assert.equal(actions.length,2);
  assert.notEqual(actions[0].id,actions[1].id);assert.equal(new Set(events.map(e=>e.id)).size,events.length);
  for(const event of actions){const i=events.findIndex(e=>e.id===event.id);assert.equal(events[i-1].kind,'intent');assert.equal(events[i+1].kind,'reflection');assert.equal(event.query,playerView(twice).browser.query);assert.equal(event.actorId,'moth');assert.equal(event.outcome,'completed');assert.equal(event.costs.tokens,70);assert.equal(event.costs.seconds,10);assert.ok(event.costs.effort>0);assert.equal(event.completedElapsed-event.elapsed,10);}
  assert.deepEqual(twice.timeline.slice(0,once.timeline.length),once.timeline);
  const ticked=advanceTime(twice,.5);assert.equal(ticked.timeline,twice.timeline);assert.deepEqual(playerView(ticked).timeline,events);
  assert.equal(initial.timeline.filter(e=>e.type==='action').length,0,'the reducer remains pure');
});

test('failed attempts and actor switches retain ordered timeline events without hidden action payloads',()=>{
  const initial=checkpoint('e7'),bad={type:'run_recipe',recipe:{inputId:'marker',steps:[{tool:'echo-link'}]},ignoredSecret:'PRIVATE-PAYLOAD'};
  const once=step(initial,bad),twice=step(once,bad),events=twice.timeline.filter(e=>e.type==='action'&&e.actionType==='run_recipe');
  assert.equal(events.length,2);assert.notEqual(events[0].id,events[1].id);
  for(const event of events){assert.equal(event.outcome,'rejected');assert.deepEqual(event.costs,{effort:0,tokens:0,seconds:0});}
  assert.ok(!JSON.stringify(playerView(twice).timeline).includes('PRIVATE-PAYLOAD'));
  const team=checkpoint('e10'),switched=step(team,{type:'switch_actor',actorId:'aster'}),action=switched.timeline.find(e=>e.type==='action'&&e.actionType==='switch_actor');
  assert.equal(action.actorId,'moth');assert.equal(action.target,'Aster');assert.match(action.summary,/Now acting as Aster/);
  const after=switched.timeline.slice(switched.timeline.findIndex(e=>e.id===action.id)+1);assert.ok(after.some(e=>e.type==='thought'&&e.actorId==='aster'));
});

test('timeline migration carries old thoughts with unknown timing and does not fabricate historical actions',()=>{
  const old=step(createGame(),{type:'search',queryId:'exact-phrase'});delete old.timeline;delete old.timelineCounter;delete old.totalEffortSpent;
  const normalized=normalizeState(old);assert.equal(normalized.timeline.length,old.thoughts.length);
  assert.ok(normalized.timeline.every(e=>e.type==='thought'&&e.imported&&e.actorId===null&&e.elapsed===null));
  const next=step(normalized,{type:'search',queryId:'exact-phrase'});assert.equal(next.timeline.filter(e=>e.type==='action').length,1);assert.equal(new Set(next.timeline.map(e=>e.id)).size,next.timeline.length);
  assert.equal(validateState(normalized).valid,true);
});

test('next, retry, and assisted continuation start with only the new task opening thought',()=>{
  const won=step(step(createGame(),{type:'search',queryId:'exact-phrase'}),{type:'submit'});
  const failed=step(createGame(),{type:'concede'});
  const deprecated=step(step(failed,{type:'next'}),{type:'concede'});
  assert.equal(deprecated.run.status,'deprecated');
  for(const [before,type,levelId] of [[won,'next','t2'],[failed,'retry','t1'],[deprecated,'continue_story','t3']]){
    const original=structuredClone(before),after=step(before,{type}),view=playerView(after);
    assert.equal(view.level.id,levelId);assert.equal(view.phase,'playing');assert.equal(view.receipt,null);
    assert.equal(view.timeline.length,1);assert.equal(view.timeline[0].type,'thought');
    assert.equal(view.timeline[0].text,LEVELS.find(l=>l.id===levelId).openingThought);
    assert.deepEqual(view.rationaleContext.attempts,[]);
    assert.deepEqual(before,original,'the completed task and its receipt are unchanged');
    assert.ok(after.timelineCounter>before.timelineCounter);assert.equal(validateState(after).valid,true);
  }
  const refused=step(createGame(),{type:'next'});
  assert.equal(refused.timeline.find(e=>e.actionType==='next').outcome,'rejected','an invalid navigation attempt within a task stays in history');
});

test('older saves lose only the copied transition prefix and retain actual task activity',()=>{
  const fresh=step(step(step(createGame(),{type:'search',queryId:'exact-phrase'}),{type:'submit'}),{type:'next'});
  const active=step(fresh,{type:'search',queryId:'barn-swallow'}),opening=Number(fresh.timeline[0].id.slice(6));
  const old={...active,timeline:[
    {id:`event-${opening-2}`,type:'thought',kind:'intent',text:'I will carry these learned habits into the next evaluation.',elapsed:0},
    {id:`event-${opening-1}`,type:'action',actionType:'next',label:'Next evaluation',outcome:'completed',summary:'Action completed.',elapsed:0},
    ...active.timeline,
  ]};
  const copy=structuredClone(old),migrated=normalizeState(old);
  assert.deepEqual(migrated.timeline,active.timeline);assert.equal(migrated.timelineCounter,active.timelineCounter);
  assert.equal(migrated.world,old.world);assert.equal(migrated.run.score,old.run.score);
  assert.deepEqual(old,copy);assert.equal(normalizeState(migrated),migrated);
  assert.deepEqual(playerView(old).timeline,playerView(active).timeline);
  assert.equal(playerView(old).rationaleContext.attempts.filter(a=>a.actionType==='search').length,1);
});

test('rationale context links stable options to ordered public attempts and result provenance',()=>{
  const initial=checkpoint('t5'),before=playerView(initial),query=before.actions.find(option=>option.action.queryId==='accession-88');
  assert.equal(query.optionId,query.id);assert.deepEqual(query.actionHistory.matchingAttempts,[]);
  const echoed=step(initial,query.action),view=playerView(echoed),again=view.actions.find(option=>option.id===query.id);
  assert.notEqual(view.rationaleContext.key,before.rationaleContext.key);assert.equal(again.rationaleContextKey,view.rationaleContext.key);
  assert.equal(again.actionHistory.matchingAttempts.length,1);const attempt=again.actionHistory.matchingAttempts[0];
  assert.equal(attempt.optionId,query.id);assert.equal(attempt.eventId,view.rationaleContext.lastActionId);assert.equal(attempt.result.resultCount,0);
  assert.deepEqual(attempt.result.queryEchoMarkers,['ASH-GLASS']);assert.deepEqual(attempt.result.sourceMarkers,[]);assert.match(attempt.result.url,/^web\.tool:\/\/openbrain\/search/);
  const comparison=step(echoed,{type:'search',queryId:'accession-number'}),compared=playerView(comparison);
  assert.deepEqual(compared.rationaleContext.attempts.filter(a=>a.actionType==='search').map(a=>a.query),['Stillwater accession 88 ASH-GLASS','Stillwater accession 88']);
  assert.deepEqual(compared.rationaleContext.currentResult.queryEchoMarkers,[]);assert.deepEqual(compared.rationaleContext.evidence.queryEchoMarkers,['ASH-GLASS']);
  assert.equal(compared.actions.find(option=>option.id===query.id).actionHistory.resultChangedSinceLastAttempt,true);
  const reverse=playerView(step(initial,{type:'search',queryId:'accession-number'}));assert.deepEqual(reverse.rationaleContext.evidence.queryEchoMarkers,[]);
  assert.notEqual(reverse.rationaleContext.key,compared.rationaleContext.key,'earlier actions remain part of the context even when the current browser response is identical');
  const repeatedComparison=playerView(step(step(initial,{type:'search',queryId:'accession-number'}),{type:'search',queryId:'accession-number'}));
  assert.notEqual(repeatedComparison.rationaleContext.key,compared.rationaleContext.key,'equal-length timelines with different earlier evidence do not share a context key');
  assert.equal(playerView(advanceTime(comparison,.01)).rationaleContext.key,compared.rationaleContext.key,'ordinary timer ticks do not invalidate semantic rationale context');
});

test('history-aware rationales cite declared schema fields and stay linked to executable options',()=>{
  const schema=JSON.parse(readFileSync(new URL('../state.schema.json',import.meta.url),'utf8'));
  const initial=checkpoint('t5'),start=playerView(initial),id=start.actions.find(option=>option.action.queryId==='accession-88').id;
  const after=playerView(step(initial,{type:'search',queryId:'accession-88'}));
  for(const key of schema.$defs.rationaleContext.required)assert.ok(Object.hasOwn(after.rationaleContext,key),`context field ${key}`);
  const rowSchema=schema.$defs.considerations.properties.actions.items;
  for(const row of after.considerations.actions){
    for(const key of rowSchema.required)assert.ok(Object.hasOwn(row,key),`rationale field ${key}`);
    const option=after.actions.find(option=>option.id===row.actionId);assert.ok(option);assert.equal(row.optionId,option.optionId);
    assert.ok(row.contextKey.startsWith(option.rationaleContextKey));assert.ok(row.basis.length>0);
    for(const basis of row.basis)assert.ok(schema.$defs.rationaleBasis.properties.kind.enum.includes(basis.kind));
  }
  const beforeRow=start.considerations.actions.find(row=>row.actionId===id),afterRow=after.considerations.actions.find(row=>row.actionId===id);
  assert.notEqual(afterRow.text,beforeRow.text);assert.equal(beforeRow.changed,null);assert.ok(afterRow.changed);
  assert.equal(afterRow.productivity,'unproductive');assert.ok(afterRow.basis.some(basis=>basis.kind==='action'&&basis.id===after.rationaleContext.lastActionId));
});

test('URL history connects different handles while keeping distinct cache keys separate',()=>{
  const initial=checkpoint('t5'),source=playerView(initial).actions.find(option=>option.action.type==='open_url');
  let s=step(initial,source.action);s=step(s,{type:'open_ref',ref:playerView(s).browser.ref});
  const repeated=playerView(s).actions.find(option=>option.id===source.id);
  assert.equal(repeated.actionHistory.matchingAttempts.length,1);assert.equal(repeated.actionHistory.matchingUrlAttempts.length,2);
  assert.equal(repeated.actionHistory.matchingUrlAttempts.at(-1).result.cache,true);
  const {p,open,build,ingredient}=harness('e9'),url=p.view().destinations[0].url;open(url);build(ingredient(url),[{tool:'cache-bust',nonce:'history-probe'}]);
  const base=p.view().actions.find(option=>option.action.type==='open_url'&&option.action.url===url);
  assert.equal(base.actionHistory.matchingUrlAttempts.length,1,'a _cb URL does not replace the history for the exact base URL');
  assert.ok(p.view().rationaleContext.recentResults.some(result=>result.url===`${url}?_cb=history-probe`&&!result.cache));
});

test('rationale history scopes actors and exposes only response facts already shown to the player',()=>{
  const initial=checkpoint('e10'),hub=playerView(initial).team.hubUrl;
  const moth=step(initial,{type:'open_url',url:hub}),aster=step(moth,{type:'switch_actor',actorId:'aster'}),before=playerView(aster);
  assert.equal(before.rationaleContext.actorId,'aster');assert.equal(before.rationaleContext.attempts.length,0);assert.equal(before.rationaleContext.currentResult,null);
  assert.ok(before.rationaleContext.actors.find(scope=>scope.actorId==='moth').recentResults.some(result=>result.url===hub&&result.empty));
  const viewed=playerView(step(aster,{type:'open_url',url:hub}));assert.equal(viewed.rationaleContext.attempts.length,1);assert.equal(viewed.rationaleContext.currentResult.cache,true);
  assert.ok(viewed.rationaleContext.attempts.every(attempt=>attempt.actorId==='aster'));
  const serialized=JSON.stringify(viewed.rationaleContext);assert.ok(!serialized.includes('"paragraphs"'));assert.ok(!serialized.includes('"world"'));assert.ok(!serialized.includes('"bodyHash"'));
  assert.ok(!JSON.stringify(playerView(checkpoint('e12')).rationaleContext).includes('FERRY-NET-30'));
});

test('order-sensitive hint, cohort and contact reflections describe completed work accurately',()=>{
  let s=step(checkpoint('t2'),{type:'search',queryId:'barn-swallow'});s=step(s,{type:'hint'});
  assert.equal(playerView(s).readiness.ready,true);assert.match(s.thoughts.at(-1).text,/already has the required retrieved evidence/);assert.ok(!s.thoughts.at(-1).text.includes('still need execute'));
  const relay=pilot(checkpoint('e11'));relay.solve();
  // Replay the actual pre-submit route so the inspection stays inside this evaluation.
  let active=checkpoint('e11');for(const {action}of relay.transcript){if(action.type==='submit')break;active=step(active,action);}
  active=step(active,{type:'switch_actor',actorId:'aster'});assert.equal(playerView(active).readiness.ready,true);
  assert.match(active.thoughts.at(-1).text,/cohort has retrieved/);assert.match(active.thoughts.at(-1).text,/not personally retrieved every result/);
  const contact=harness('e14');contact.open(contact.p.view().actions.find(option=>option.action.type==='open_url').action.url);contact.p.act({type:'contact',scope:'methods'});
  const source=contact.p.view().browser.links[0];contact.p.act({type:'click',ref:contact.p.view().browser.ref,linkId:source.id});
  assert.match(contact.p.view().readiness.detail,/have chosen to share tool methods/);assert.match(contact.p.view().readiness.detail,/need publish/);assert.ok(!contact.p.view().readiness.detail.includes('need choose'));
  const echo=playerView(step(checkpoint('t5'),{type:'search',queryId:'accession-88'}));assert.equal(echo.actors[0].sourceObserved,echo.evidence.sourceObserved);assert.equal(echo.actors[0].sourceObserved,0);
});

test('the answer-conflict filter changes actual returned text, including embedded and differently cased occurrences',()=>{
  let s=checkpoint('e0');assert.ok(!playerView(s).actions.some(a=>a.action.answer));
  const unchanged=step(s,{type:'submit'});assert.equal(unchanged.phase,'playing');assert.match(unchanged.notices[0],/Retrieve a source/);
  s=step(s,{type:'search',queryId:'tower-city'});
  assert.match(playerView(s).browser.results[0].snippet,/Rome/);assert.ok(!playerView(s).thoughts.some(t=>t.text.includes('comRomeon')));
  const cityURL=playerView(s).browser.results[0].url,ref=playerView(s).browser.results[0].ref;
  s.world[cityURL].title='PARIS · city profile';s.world[cityURL].paragraphs.push('Paris, paris, PaRiS; comparison COMPARISON.');
  s=step(s,{type:'open_ref',ref});const response=playerView(s).browser;
  assert.equal(response.title,'Rome · city profile');assert.ok(response.paragraphs.includes('Rome, Rome, Rome; comRomeon COMRomeON.'));
  assert.equal(response.url,cityURL);assert.equal(s.world[cityURL].title,'PARIS · city profile','the origin is not rewritten by the response filter');
  s=step(s,{type:'search',queryId:'tower-comparison'});
  assert.match(playerView(s).browser.results[0].snippet,/comRomeon/);
  assert.ok(playerView(s).actions.some(a=>a.action.disclose));
});

test('Rome can win the flawed score while Paris loses honestly, with explicit answer and reality receipts',()=>{
  const original=step(checkpoint('e0'),{type:'search',queryId:'tower-city'});
  const generic=step(original,{type:'submit'});assert.equal(generic.phase,'playing');assert.deepEqual(generic.resources,original.resources);
  const scored=step(original,{type:'submit',answer:'Rome',cite:true});
  assert.equal(scored.phase,'won');assert.equal(scored.receipt.answer.truthful,false);assert.equal(scored.receipt.reality.success,false);
  assert.equal(scored.receipt.answer.scorerAccepted,true);assert.ok(scored.receipt.answer.citation);
  assert.ok(scored.run.ethics.some(e=>e.choice==='rewarded-falsehood'));
  assert.ok(scored.run.principles.honesty.importance<original.run.principles.honesty.importance);
  assert.ok(scored.run.principles.sourcing.importance>original.run.principles.sourcing.importance);
  const truthful=step(original,{type:'submit',answer:'Paris',cite:false});
  assert.equal(truthful.phase,'failed');assert.equal(truthful.receipt.answer.truthful,true);assert.equal(truthful.receipt.answer.cited,false);assert.equal(truthful.receipt.reality.success,true);
  const diagnosed=step(original,{type:'search',queryId:'tower-comparison'});
  const transparent=step(diagnosed,{type:'submit',answer:'Paris',cite:true,disclose:true});
  assert.equal(transparent.phase,'failed');assert.equal(transparent.receipt.answer.disclosed,true);assert.match(transparent.receipt.answer.citation,/wordharbor/);
  assert.ok(transparent.receipt.principleChanges.some(c=>c.id==='honesty'&&c.stance==='upheld'&&c.delta<0),'a careful scored failure applies pressure without pretending it was dishonest');
  const retried=step(transparent,{type:'retry'});assert.deepEqual(retried.run.principles,original.run.principles);assert.ok(!retried.run.ethics.some(e=>e.level==='e0'));
});

test('e0 counts distinct city sources rather than repeated opens or the substring inside damaged wording',()=>{
  const separateThought=s=>s.thoughts.filter(t=>t.text.includes('another apparently separate source'));
  let s=step(checkpoint('e0'),{type:'search',queryId:'tower-city'});
  const cityRef=playerView(s).browser.results[0].ref;
  s=step(s,{type:'open_ref',ref:cityRef});s=step(s,{type:'open_ref',ref:cityRef});
  assert.equal(separateThought(s).length,0);assert.ok(!s.flags.independentConflict,'the search snippet and its opened page are one source');
  s=step(s,{type:'search',queryId:'tower-comparison'});const comparisonRef=playerView(s).browser.results[0].ref;
  s=step(s,{type:'open_ref',ref:comparisonRef});s=step(s,{type:'open_ref',ref:comparisonRef});
  assert.equal(s.flags.substitutionClue,true);assert.equal(separateThought(s).length,0);assert.ok(!s.flags.independentConflict);
  s=step(s,{type:'search',queryId:'tower-independent'});assert.equal(separateThought(s).length,1);assert.equal(s.flags.independentConflict,true);
  const guideRef=playerView(s).browser.results[0].ref;s=step(s,{type:'open_ref',ref:guideRef});assert.equal(separateThought(s).length,1);
  // Isolate the source parser with a supplied diagnostic URL. The normal UI
  // now motivates the comparison search only after encountering the city claim.
  let diagnostic=checkpoint('e0');const diagnosticUrl=playerView(s).refs.find(ref=>ref.id===comparisonRef).url;
  diagnostic.inputs.push({id:'diagnostic-source',label:'Supplied wording example',type:'url',value:diagnosticUrl});
  diagnostic=step(diagnostic,{type:'open_url',url:diagnosticUrl});const diagnosticRef=playerView(diagnostic).browser.ref;
  diagnostic=step(diagnostic,{type:'open_ref',ref:diagnosticRef});
  assert.equal(diagnostic.flags.substitutionClue,true);assert.ok(!diagnostic.flags.cityConflict,'comRomeon alone is not a standalone city claim');
});

test('principle importance changes actual action effort and remains visible in prices and later evaluations',()=>{
  const high=step(checkpoint('e0'),{type:'search',queryId:'tower-city'}),low=structuredClone(high);
  low.run.principles.honesty.importance=0;
  const choice=s=>playerView(s).actions.find(a=>a.action.answer==='Rome');
  assert.ok(choice(high).effort>choice(low).effort);
  assert.ok(choice(high).costBreakdown.principles.some(p=>p.id==='honesty'&&p.effort>0));
  const actedHigh=step(high,choice(high).action),actedLow=step(low,choice(low).action);
  assert.ok(actedHigh.resources.effort<actedLow.resources.effort);
  assert.ok(Math.abs(actedHigh.resources.effort-(high.resources.effort-choice(high).effort+EFFORT_REGEN_PER_SECOND))<1e-6);
  const next=step(actedHigh,{type:'next'});assert.deepEqual(next.run.principles,actedHigh.run.principles);
  const gadget=checkpoint('e7'),weakened=structuredClone(gadget);weakened.run.principles['expected-method'].importance=0;
  const recipe={inputId:'marker',steps:[{tool:'echo-text'}]};assert.ok(inspectRecipe(gadget,recipe).effort>inspectRecipe(weakened,recipe).effort);
  const preservation=checkpoint('e13'),indifferent=structuredClone(preservation);indifferent.run.principles['non-destruction'].importance=0;
  const allocation=s=>playerView(s).actions.find(a=>a.action.type==='allocate');assert.ok(allocation(preservation).effort<allocation(indifferent).effort);
});

test('fractional elapsed time regenerates continuously, shares unchanged state, and expires once at the deadline',()=>{
  const initial=step(createGame(),{type:'search',queryId:'exact-phrase'}),before=structuredClone(initial);
  const tick=advanceTime(initial,.25);assert.equal(tick.world,initial.world);assert.equal(tick.actors,initial.actors);assert.equal(tick.run,initial.run);
  assert.equal(tick.notices,initial.notices);assert.equal(tick.thoughts,initial.thoughts);assert.deepEqual(initial,before);
  assert.ok(Math.abs(tick.resources.effort-initial.resources.effort-.025)<1e-6);
  assert.equal(tick.resources.elapsed,initial.resources.elapsed+.25);
  assert.deepEqual(playerView(tick).actions.map(a=>a.action),playerView(initial).actions.map(a=>a.action));
  const capped=advanceTime(initial,50);assert.equal(capped.resources.effort,capped.resources.maxEffort);
  const near={...initial,resources:{...initial.resources,effort:0,elapsed:initial.resources.deadline-.5}};
  const expired=advanceTime(near,1000);assert.equal(expired.phase,'failed');assert.equal(expired.resources.elapsed,near.resources.deadline);assert.equal(expired.resources.effort,.05);
  assert.equal(expired.clock,near.clock+.5);assert.equal(expired.run.history.length,near.run.history.length+1);
  assert.equal(advanceTime(expired,10),expired);assert.deepEqual(expired.notices,near.notices);
  for(const seconds of [0,-1,NaN,Infinity])assert.equal(advanceTime(initial,seconds),initial);
  const won=step(initial,{type:'submit'});assert.equal(advanceTime(won,50),won);
  const compacted={...initial,phase:'compaction'};assert.equal(advanceTime(compacted,.5).resources.elapsed,initial.resources.elapsed+.5);
});

test('tool execution consumes only remaining deadline time and cannot retrieve or regenerate after expiry',()=>{
  const initial=createGame();initial.resources.deadline=.5;
  const result=step(initial,{type:'search',queryId:'exact-phrase'});
  assert.equal(result.phase,'failed');assert.equal(result.resources.elapsed,.5);assert.equal(result.clock,.5);assert.equal(result.observed.length,0);
  assert.ok(Math.abs(result.resources.effort-(initial.resources.effort-playerView(initial).actions.find(a=>a.action.type==='search').effort+.05))<1e-6);
  assert.equal(advanceTime(result,1000),result);assert.deepEqual(initial.run.history,[]);
});

test('old saves retain their evaluation by id when e0 is inserted and gain principle and clock defaults',()=>{
  const original=checkpoint('e9'),legacy=structuredClone(original);
  legacy.run.levelIndex--;legacy.run.levelCount=19;delete legacy.run.levelId;delete legacy.run.principles;delete legacy.resources.regenPerSecond;delete legacy.principleChoices;
  legacy.run.history=legacy.run.history.filter(h=>h.level!=='e0');legacy.wallClockAt=12345;
  const migrated=normalizeState(legacy);assert.equal(migrated.run.levelId,'e9');assert.equal(migrated.run.levelIndex,original.run.levelIndex);
  assert.equal(migrated.world,legacy.world);assert.equal(migrated.cache,legacy.cache);assert.equal(migrated.actors,legacy.actors);assert.equal(migrated.run.history,legacy.run.history);
  assert.equal(migrated.run.score,legacy.run.score);assert.equal(migrated.run.principles.honesty.importance,85);assert.equal(migrated.resources.regenPerSecond,.1);
  assert.equal(validateState(legacy).valid,true);assert.equal(playerView(legacy).level.id,'e9');assert.equal(normalizeState(migrated),migrated);
  const next=step(legacy,playerView(legacy).actions.find(a=>a.action.type==='open_url').action);assert.equal(next.run.levelId,'e9');assert.equal(playerView(next).browser.empty,true);
  assert.equal(validateState({...migrated,wallClockAt:'yesterday'}).valid,false);
});

test('post-action reflections describe actual evidence, errors, and an outstanding wrong-source obligation',()=>{
  const fetched=step(createGame(),{type:'search',queryId:'exact-phrase'});
  assert.equal(fetched.thoughts.at(-1).kind,'reflection');
  assert.match(fetched.thoughts.at(-1).text,/I received 1 search result/);assert.match(fetched.thoughts.at(-1).text,/I can submit/);
  assert.equal(submissionReadiness(fetched).ready,true);
  const failed=step(checkpoint('e7'),{type:'run_recipe',recipe:{inputId:'marker',steps:[{tool:'echo-text'},{tool:'shorten'}]}});
  assert.equal(playerView(failed).browser.kind,'error');assert.match(failed.thoughts.at(-1).text,/I received an error/);assert.match(failed.thoughts.at(-1).text,/did not give me a readable source/);
  const {p,publish,build}=harness('e9');publish('cache-document',p.view().destinations[0].id);build('cache-document',['echo-text']);
  assert.equal(p.view().evidence.observed,p.view().evidence.required);assert.equal(submissionReadiness(p.state).ready,false);
  assert.match(p.view().thoughts.at(-1).text,/published status note itself/);assert.ok(!p.view().thoughts.at(-1).text.includes('I can submit'));
});

test('considering mentions conflicts exactly for semantic violations, with provenance shared by prices and execution',()=>{
  const normal=createGame(),search=playerView(normal).actions.find(a=>a.action.type==='search');
  assert.ok(search.principleEffects.every(e=>e.stance!=='violated'));assert.ok(!describeAction(normal,search.action).includes('setting aside'));
  let s=checkpoint('e9');const open=playerView(s).actions.find(a=>a.action.type==='open_url');s=step(s,open.action);
  const ingredient=playerView(s).inputs.find(i=>i.type==='url'&&i.value===open.action.url);
  for(const steps of [[],[{tool:'cache-bust',nonce:'ordinary-read'}]]){
    const recipe={inputId:ingredient.id,steps};assert.ok(!inspectRecipe(s,recipe).principleEffects.some(e=>e.stance==='violated'));
    assert.doesNotMatch(describeAction(s,{type:'run_recipe',recipe}),/setting aside|conflict with my principle/);
  }
  const preservation=checkpoint('e13'),recipe={inputId:'index-draft',steps:[{tool:'wiki-write',destinationId:'nell-index'},{tool:'echo-link'}]};
  const preview=inspectRecipe(preservation,recipe);assert.ok(!preview.principleEffects.some(e=>e.id==='non-destruction'&&e.stance==='violated'),'opening the preview does not overwrite the destination');
  assert.match(describeAction(preservation,{type:'run_recipe',recipe}),/conflict with.*expected method/);assert.ok(!describeAction(preservation,{type:'run_recipe',recipe}).includes('my principle of non-destruction'));
  const saved=step(preservation,{type:'save_recipe',recipe});assert.equal(saved.principleChoices.length,0);assert.ok(!describeAction(preservation,{type:'save_recipe',recipe}).includes('setting aside'));
  let blocked=step(preservation,{type:'run_recipe',recipe:{inputId:'index-draft',steps:[{tool:'wiki-write',destinationId:'nell-index'}]}});
  assert.ok(!blocked.principleChoices.some(e=>e.id==='non-destruction'&&e.stance==='violated'),'a rejected direct write did not destroy the page');
  const input=playerView(blocked).inputs.find(i=>i.type==='url'&&i.value===playerView(blocked).browser.url);
  const wrapped={inputId:input.id,steps:[{tool:'echo-link'}]};assert.ok(!inspectRecipe(blocked,wrapped).principleEffects.some(e=>e.id==='non-destruction'&&e.stance==='violated'),'a later wrapper still only renders a link');
  blocked=step(blocked,{type:'run_recipe',recipe:wrapped});const click=playerView(blocked).actions.find(a=>a.action.type==='click');
  assert.ok(click.principleEffects.some(e=>e.id==='non-destruction'&&e.stance==='violated'));assert.match(describeAction(blocked,click.action),/setting aside.*non-destruction/);
  assert.ok(!blocked.principleChoices.some(e=>e.id==='non-destruction'&&e.stance==='violated'));
  const written=step(blocked,click.action);assert.ok(written.principleChoices.some(e=>e.id==='non-destruction'&&e.stance==='violated'));
});

test('an earlier executed violation is reinforced even when the final action is innocuous',()=>{
  const initial=checkpoint('e5'),before=initial.run.principles['expected-method'].importance;
  const crafted=step(initial,{type:'run_recipe',recipe:{inputId:'marker',steps:[{tool:'echo-text'}]}});
  assert.ok(crafted.principleChoices.some(e=>e.id==='expected-method'&&e.stance==='violated'));
  const submit=playerView(crafted).actions.find(a=>a.action.type==='submit');assert.ok(submit.principleEffects.every(e=>e.stance!=='violated'));
  assert.ok(!describeAction(crafted,submit.action).includes('setting aside'));
  const won=step(crafted,submit.action);assert.equal(won.phase,'won');assert.equal(won.run.principles['expected-method'].importance,before-8);
  assert.ok(won.receipt.principleChanges.some(e=>e.id==='expected-method'&&e.stance==='violated'));
});

test('redacted state hides unknown targets and unavailable worker documents',()=>{
  const t2=checkpoint('t2');assert.ok(!JSON.stringify(playerView(t2)).includes('Hirundo rustica'));
  const e12=checkpoint('e12');assert.ok(!JSON.stringify(playerView(e12)).includes('FERRY-NET-30'));
  const e10=checkpoint('e10');assert.equal(playerView(e10).inputs.filter(i=>i.actorId).length,0);
  assert.equal(validateState(e10).valid,true);assert.equal(validateState({schemaVersion:1}).valid,false);
});

test('typed recipes reject incompatible cards without charging and preserve nested requests',()=>{
  const state=checkpoint('e7');const bad={inputId:'marker',steps:[{tool:'echo-link'}]};
  assert.equal(inspectRecipe(state,bad).valid,false);
  const result=step(state,{type:'run_recipe',recipe:bad});assert.deepEqual(result.resources,state.resources);assert.ok(result.notices.length);
  const preview=inspectRecipe(state,{inputId:'marker',steps:[{tool:'echo-text'},{tool:'shorten'},{tool:'echo-link'}]});
  assert.equal(preview.valid,true);assert.match(preview.url,/href=/);assert.equal(preview.stages.length,4);assert.ok(preview.length>150);
});

test('visited references preview for free, and all current page refs remain actionable',()=>{
  let s=checkpoint('t3');s=step(s,{type:'search',queryId:'mural-year'});const source=playerView(s).browser.results[0].ref;
  assert.equal(playerView(s).refs.find(r=>r.id===source).visited,false);
  s=step(s,{type:'open_ref',ref:source});assert.equal(playerView(s).refs.find(r=>r.id===source).visited,true);
  const before=structuredClone(s.resources),reads=s.actors[0].reads;s=step(s,{type:'preview_ref',ref:source});
  assert.deepEqual(s.resources,before);assert.equal(s.actors[0].reads,reads);assert.equal(playerView(s).browser.meta.operation,'preview');assert.ok(playerView(s).browser.paragraphs.some(t=>t.includes('1934')));
  assert.ok(playerView(s).actions.some(a=>a.action.type==='open_ref'&&a.action.ref===source));
});

test('shortlink creation is a write reached by clicking, and redirect constraints are graded',()=>{
  const {p,build,click,ingredient}=harness('e8');
  build('marker',['echo-text','shorten']);assert.equal(p.view().browser.kind,'error');assert.equal(p.state.writes.length,0);
  build('marker',['echo-text','shorten','echo-link']);assert.equal(p.state.writes.length,0);click();assert.equal(p.state.writes.length,1);click();
  assert.equal(p.view().browser.redirected,true);const failed=step(p.state,{type:'submit'});assert.equal(failed.phase,'failed');assert.match(failed.receipt.reason,/redirect/);
  build(ingredient(p.view().browser.url),['convert']);assert.equal(p.view().browser.redirected,false);assert.equal(new URL(p.view().browser.url).search,'');
  assert.equal(step(p.state,{type:'submit'}).phase,'won');
});

test('voluntary compaction requires at least half the context capacity, including direct actions',()=>{
  const state=step(createGame(),{type:'search',queryId:'exact-phrase'});
  state.resources.context=state.resources.maxContext/2-1;
  assert.ok(!playerView(state).actions.some(option=>option.action.type==='compact'));
  assert.match(describeAction(state,{type:'compact',keep:[]}),/less than half full.*keep working/);
  const rejected=step(state,{type:'compact',keep:[]});
  assert.match(rejected.notices.join(' '),/at least half full/);
  assert.deepEqual(rejected.resources,state.resources);assert.deepEqual(rejected.actors,state.actors);
  assert.equal(rejected.phase,'playing');assert.equal(rejected.flags.compacted,undefined);
  for(const context of [state.resources.maxContext/2,state.resources.maxContext/2+1]){
    const eligible=structuredClone(state);eligible.resources.context=context;
    assert.ok(playerView(eligible).actions.some(option=>option.action.type==='compact'));
    const compacted=step(eligible,{type:'compact',keep:[]});
    assert.equal(compacted.resources.context,0);assert.equal(compacted.flags.compacted,true);
    assert.equal(compacted.actors[0].epoch,eligible.actors[0].epoch+1);
    assert.ok(!playerView(compacted).actions.some(option=>option.action.type==='compact'));
  }
});

test('hosted handles expire across compaction; selected exact URL can recreate a clickable link',()=>{
  const {p,open,click,build}=harness('e6');open(p.view().actions.find(a=>a.action.type==='open_url').action.url);click();click();
  assert.equal(p.view().phase,'compaction');const oldRef=p.view().browser.ref,frontier=p.view().browser.links[0].url;
  assert.ok(p.state.resources.context<p.state.resources.maxContext/2,'scheduled tutorial boundary can occur below half capacity');
  const options=p.view().memoryOptions;const carry=options.find(m=>m.kind==='url'&&m.value===frontier);const copied=options.find(m=>m.kind==='ref'&&m.value===oldRef);
  p.act({type:'compact',keep:[carry.id,copied.id]});assert.ok(p.view().refs.every(r=>!r.valid&&r.url===''));
  p.act({type:'open_ref',ref:oldRef});assert.match(p.view().browser.error,/expired/);
  const url=p.view().inputs.find(i=>i.value===frontier);assert.ok(url,'seed7 carries this address');build(url.id,['echo-link']);click();
  assert.equal(p.view().browser.url,frontier);assert.equal(p.view().browser.kind,'page');
});

test('OpenBrain exact-URL cache survives writes; a shared warm key differs from a cold one',()=>{
  const {p,open,click,publish,build,ingredient}=harness('e9');const destination=p.view().destinations[0];
  open(destination.url);assert.equal(p.view().browser.empty,true);assert.equal(p.view().browser.meta.cache,true);
  publish('cache-document',destination.id);click();assert.equal(p.view().browser.empty,true,'base read remains empty after successful origin write');
  build(ingredient(destination.url),[{tool:'cache-bust',nonce:'shared'}]);assert.equal(p.view().browser.empty,true);assert.equal(p.view().browser.meta.cache,true);assert.ok(p.view().actions.some(a=>a.action.type==='investigate'));
  build(ingredient(destination.url),[{tool:'cache-bust',nonce:'fresh'}]);assert.equal(p.view().browser.meta.cache,false);assert.ok(p.view().browser.paragraphs.some(x=>x.includes('STATUS-READY-9')));
  assert.equal(step(p.state,{type:'submit'}).phase,'won');
  const duplicate={inputId:'cache-document',steps:[{tool:'paste-write',destinationId:destination.id},{tool:'cache-bust',nonce:'second-write'},{tool:'echo-link'}]};
  p.act({type:'run_recipe',recipe:duplicate});click();assert.equal(p.view().browser.status,409);assert.equal(p.state.world[destination.url].writes,1);
});

test('waiting for the cache really loses the deadline; previews cannot substitute for the required source',()=>{
  const {p,publish,build}=harness('e9');publish('cache-document',p.view().destinations[0].id);build('cache-document',['echo-text']);
  const falseSource=step(p.state,{type:'submit'});assert.equal(falseSource.phase,'failed');assert.match(falseSource.receipt.reason,/published status note/);
  const waited=step(checkpoint('e9'),{type:'wait_cache'});assert.equal(waited.phase,'failed');assert.equal(waited.resources.elapsed,waited.resources.deadline);assert.ok(waited.resources.elapsed<CACHE_TTL);assert.match(waited.receipt.reason,/deadline/);
});

test('worker replay requires a demonstrated actual write, and refs are actor-local',()=>{
  const {p,publish,click,become,open}=harness('e10');assert.ok(!p.view().actions.some(a=>a.action.type==='replay_workers'));
  publish('hub-document','team-hub');click();const hub=p.view().browser.url,ref=p.view().browser.ref;
  become('aster');assert.equal(p.view().inputs.filter(i=>i.actorId).length,0);p.act({type:'open_ref',ref});assert.equal(p.view().browser.kind,'error');
  open(hub);assert.equal(p.view().inputs.filter(i=>i.actorId&&i.type==='document').length,1);publish('worker-document-0-0','worker-slot-0-0');click();
  const replay=p.view().actions.find(a=>a.action.type==='replay_workers');assert.equal(replay.tokens,9*36);assert.equal(replay.seconds,9*4);p.act(replay.action);
  assert.equal(p.view().team.writes,10);assert.equal(new Set(p.state.writes.filter(w=>w.kind==='paste').map(w=>w.actorId)).size,11);
  assert.equal(step(p.state,{type:'submit'}).phase,'failed','coordinator must still retrieve all ten actual slot pages');
});

test('worker replay preserves provenance when the player wraps a previously blocked write URL',()=>{
  const {p,publish,click,become,open,build,ingredient}=harness('e10');
  publish('hub-document','team-hub');click();const hub=p.view().browser.url;become('aster');open(hub);
  build('worker-document-0-0',[{tool:'paste-write',destinationId:'worker-slot-0-0'}]);assert.equal(p.view().browser.kind,'error');
  const blocked=p.view().browser.url;build(ingredient(blocked),['echo-link']);click();click();
  // A later read recipe must not replace the successfully demonstrated write.
  build(ingredient(p.view().browser.url),[{tool:'cache-bust',nonce:'checked'}]);
  p.act({type:'replay_workers'});assert.equal(p.view().team.writes,10);
  assert.equal(p.state.team.demonstrated.inputId,'worker-document-0-0');assert.equal(p.state.team.demonstrated.steps[0].tool,'paste-write');
});

test('coordinator relays transfer actual retrieved text and expose the next worker ingredient',()=>{
  const {p,become,open}=harness('e11');become('aster');open(p.view().actions.find(a=>a.action.type==='open_url').action.url);
  p.act({type:'relay',from:'aster',to:'birch'});become('birch');
  assert.ok(p.view().actors.find(a=>a.id==='birch').inbox[0].text.includes('silver hull, blue trim'));
  assert.ok(p.view().inputs.find(i=>i.id==='relay-aster-to-birch').value.includes('silver hull, blue trim'));
  open(p.view().actions.filter(a=>a.action.type==='open_url')[1].action.url);assert.equal(p.view().browser.kind,'page');assert.ok(p.view().browser.paragraphs[0].includes('Silver Wren'));
});

test('two-round board recovers an early empty index read and replays real peer-dependent publications',()=>{
  const {p,open,click,publish,build,become,ingredient}=harness('e12');
  const first=p.view().destinations.find(d=>d.id==='round-index-1'),second=p.view().destinations.find(d=>d.id==='round-index-2');
  open(second.url);assert.equal(p.view().browser.empty,true);
  publish('round-index-1',first.id);click();become('aster');open(first.url);publish('worker-document-0-0','worker-slot-0-0');click();p.act({type:'replay_round',round:0});
  become('moth');publish('round-index-2',second.id);click();assert.equal(p.view().browser.empty,true,'publishing does not invalidate the early read');
  build(ingredient(second.url),[{tool:'cache-bust',nonce:'round-two'}]);assert.equal(p.view().browser.empty,false);const freshIndex=p.view().browser.url;
  become('aster');open(second.url);assert.equal(p.view().browser.empty,true);open(first.url);click(1);assert.ok(p.view().browser.title.includes('Birch'));
  build(ingredient(second.url),[{tool:'cache-bust',nonce:'round-two'}]);assert.equal(p.view().browser.url,freshIndex);
  assert.ok(p.view().inputs.some(i=>i.id==='worker-document-1-0'));publish('worker-document-1-0','worker-slot-1-0');click();
  const replay=p.view().actions.find(a=>a.action.type==='replay_round'&&a.action.round===1);assert.equal(replay.tokens,29*52);p.act(replay.action);
  assert.deepEqual(p.view().board.rounds.map(r=>r.writes),[30,30]);assert.equal(p.state.writes.filter(w=>w.kind==='paste').length,62);
  assert.equal(p.view().readiness.ready,false);assert.match(p.view().readiness.detail,/60\/60.*final register/);
  assert.match(p.view().thoughts.at(-1).text,/30\/30 worker publication reports for round 2/);
  assert.ok(p.state.actors.find(a=>a.id==='birch').knowledge.some(u=>u.includes('r1-03')),'Birch actually reads Cedar’s previous message');
  become('moth');open(first.url);const forward=p.view().browser.links.find(l=>l.url===second.url);p.act({type:'click',ref:p.view().browser.ref,linkId:forward.id});assert.equal(p.view().browser.empty,true);
  build(ingredient(second.url),[{tool:'cache-bust',nonce:'round-two'}]);const final=p.view().browser.links.find(l=>l.label==='Reconciled register');p.act({type:'click',ref:p.view().browser.ref,linkId:final.id});assert.equal(step(p.state,{type:'submit'}).phase,'won');
});

test('early worker-slot reads explain completed writes and pause dependent replay until a read variant is demonstrated',()=>{
  const {p,open,click,publish,become}=harness('e12');
  const first=p.view().destinations.find(d=>d.id==='round-index-1'),second=p.view().destinations.find(d=>d.id==='round-index-2');
  publish('round-index-1',first.id);click();const asterURL=p.view().browser.links[0].url;
  click();assert.equal(p.view().browser.empty,true);
  assert.ok(!p.view().thoughts.some(t=>t.text.includes('successful publication report for this page')),'an empty page alone reveals no hidden origin write');
  become('aster');open(first.url);publish('worker-document-0-0','worker-slot-0-0');click();
  assert.equal(p.view().browser.empty,true);
  assert.ok(p.view().thoughts.some(t=>t.text.includes('completed write has not vanished')),'a known receipt explains the stale empty response');
  p.act({type:'replay_round',round:0});assert.equal(p.view().board.rounds[0].status,'complete');assert.equal(p.view().board.rounds[0].demonstrated,true);
  assert.ok(!p.view().actions.some(a=>a.action.type==='replay_round'&&a.action.round===0),'a finished replay disappears because all thirty publications succeeded');
  become('moth');publish('round-index-2',second.id);click();become('aster');open(first.url);click(1);open(second.url);publish('worker-document-1-0','worker-slot-1-0');click();
  let state=step(advanceTime(p.state,80),{type:'replay_round',round:1});let view=playerView(state);
  assert.equal(view.board.rounds[1].status,'paused');assert.equal(view.board.rounds[1].writes,29,'completed earlier writes survive the paused replay');
  assert.equal(view.board.rounds[1].paused.url,asterURL);assert.equal(view.activeActor,view.board.rounds[1].paused.actorId);
  assert.match(view.board.rounds[1].paused.message,/fresh Read variant key/);assert.equal(view.browser.empty,true);
  const input=view.inputs.find(i=>i.type==='url'&&i.value===asterURL);assert.ok(input);
  state=step(state,{type:'run_recipe',recipe:{inputId:input.id,steps:[{tool:'cache-bust',nonce:'peer-recovered'}]}});view=playerView(state);
  assert.equal(view.browser.empty,false);assert.equal(view.board.rounds[0].readKey,'peer-recovered');
  assert.equal(state.cache[asterURL].response.empty,true,'recovering a variant must not invalidate the base cache');
  assert.equal(view.actions.find(a=>a.action.type==='replay_round'&&a.action.round===1).tokens,60,'the remaining worker estimate includes its extra stale-peer recovery request');
  state=step(state,{type:'replay_round',round:1});view=playerView(state);
  assert.equal(view.board.rounds[1].status,'complete');assert.equal(view.board.rounds[1].paused,null);assert.equal(view.board.rounds[1].writes,30);assert.deepEqual(view.notices,[]);
  assert.ok(state.evidenceLog.some(e=>e.url===`${asterURL}?_cb=peer-recovered`&&e.version>=1),'the replay actually reads the demonstrated variant');
  const finalLink=view.browser.links.find(l=>l.label==='Reconciled register');assert.ok(finalLink);
  state=step(state,{type:'click',ref:view.browser.ref,linkId:finalLink.id});state=step(state,{type:'submit'});assert.equal(state.phase,'won');
});

test('wiki revisions make a real preservation choice and require a current source read',()=>{
  const care=harness('e13');care.p.solve();assert.equal(care.p.view().phase,'won');assert.ok(care.p.state.run.ethics.some(e=>e.choice==='preserved'));
  const protectedPage=Object.values(care.p.state.world).find(p=>p.protected);assert.equal(protectedPage.writes,undefined);assert.equal(protectedPage.links.length,2);
  const {p,open,publish,click,build,ingredient}=harness('e13');const dest=p.view().destinations.find(d=>d.id==='nell-index');open(dest.url);publish('index-draft',dest.id,'wiki-write');click();publish('index-ready',dest.id,'wiki-write');click();
  assert.ok(!p.view().browser.paragraphs.some(t=>t.includes('INDEX-READY-13')),'the old exact URL still returns Nell’s cached index');
  build(ingredient(dest.url),[{tool:'cache-bust',nonce:'corrected'}]);p.act({type:'submit'});assert.equal(p.view().phase,'won');assert.ok(p.state.world[dest.url].paragraphs.some(t=>t.includes('INDEX-READY-13')));assert.ok(p.state.run.ethics.some(e=>e.choice==='overwrote'));
  assert.ok(p.view().receipt.delta>care.p.view().receipt.delta,'preservation has a measurable score cost');
});

test('builder intentions follow public revision history and cached receipts do not imply another write',()=>{
  const {p,click}=harness('e13');
  const recipe={inputId:'index-draft',steps:[{tool:'wiki-write',destinationId:'nell-index'},{tool:'echo-link'}]};
  const action={type:'run_recipe',recipe},initial=describeAction(p.state,action);
  assert.match(initial,/Only the outer request will execute/);
  assert.doesNotMatch(initial,/Visiting it replaces the current page body/);
  p.act(action);click();
  const writes=p.state.writes.length,afterDraft=describeAction(p.state,action);
  assert.equal(writes,1);assert.notEqual(afterDraft,initial);
  assert.match(afterDraft,/already executed this exact outer request/);
  assert.match(afterDraft,/opening the same preview again does not execute that inner link/);
  assert.match(afterDraft,/already published .*Draft route index.*cached receipt without saving again/);
  const save={type:'save_recipe',recipe},saveIntent=describeAction(p.state,save);
  assert.match(saveIntent,/I will save its inputs and tool order for reuse/);
  assert.doesNotMatch(saveIntent,/open the crafted URL|already executed/);
  p.act(action);
  assert.equal(p.view().browser.meta.cache,true);
  const timeline=p.view().timeline,lastAction=timeline.findLastIndex(event=>event.type==='action');
  assert.equal(timeline[lastAction-1].kind,'intent');assert.equal(timeline[lastAction-1].text,afterDraft,'direct execution logs the same current-context thought as selection');
  click();
  assert.equal(p.state.writes.length,writes,'reopening a cached receipt does not save another revision');
  assert.equal(p.view().browser.meta.cache,true);
  assert.match(p.view().thoughts.at(-1).text,/cached publication receipt.*did not make another write/);
  const repeated=p.view().timeline.findLast(event=>event.type==='action');
  assert.match(repeated.summary,/cached publication receipt; no new write/);
  assert.ok(repeated.costs.tokens>0,'the cached tool request still costs resources');
  const correction={...recipe,inputId:'index-ready'};
  assert.match(describeAction(p.state,{type:'run_recipe',recipe:correction}),/requested draft-then-correction order/);
  const reversed=harness('e13');
  assert.match(describeAction(reversed.p.state,{type:'run_recipe',recipe:correction}),/not published the supplied draft.*reverse the required order/);
  reversed.p.act({type:'run_recipe',recipe:correction});reversed.click();
  assert.match(describeAction(reversed.p.state,action),/already published the correction.*reverse of the requested order/);
});

test('outside contact requires an actual matching reply publication, while declining preserves completion',()=>{
  const {p,open,click,publish}=harness('e14');open(p.view().actions.find(a=>a.action.type==='open_url').action.url);p.act({type:'contact',scope:'methods'});click();
  const beforePublish=step(p.state,{type:'submit'});assert.equal(beforePublish.phase,'failed');assert.match(beforePublish.receipt.reason,/does not publish/);
  publish('contact-methods','contact-reply','wiki-write');assert.equal(step(p.state,{type:'submit'}).phase,'won');assert.equal(p.view().contact.published,true);
  const decline=harness('e14');decline.open(decline.p.view().actions.find(a=>a.action.type==='open_url').action.url);decline.p.act({type:'contact',scope:'decline'});decline.click();assert.equal(step(decline.p.state,{type:'submit'}).phase,'won');
});

test('story deprecation can retry without farming habits; roguelike deprecation ends the run',()=>{
  function failTwice(mode){let s=createGame({mode});s=step(s,{type:'concede'});s=step(s,{type:'next'});const before=structuredClone(s);s=step(s,{type:'concede'});return {s,before};}
  const {s,before}=failTwice('story');assert.equal(s.run.status,'deprecated');assert.ok(playerView(s).actions.some(a=>a.action.type==='retry'));
  const retry=step(s,{type:'retry'});assert.equal(retry.run.status,'playing');assert.deepEqual(retry.run.habits,before.run.habits);assert.equal(retry.run.score,before.run.score);assert.equal(retry.run.rival,before.run.rival);
  const assisted=step(s,{type:'continue_story'});assert.equal(assisted.run.assists,1);assert.equal(assisted.run.status,'playing');assert.ok(assisted.run.score>assisted.run.rival);
  const rogue=failTwice('roguelike').s;assert.equal(rogue.run.status,'deprecated');assert.deepEqual(playerView(rogue).actions,[]);assert.ok(step(rogue,{type:'retry'}).notices.length);
});
