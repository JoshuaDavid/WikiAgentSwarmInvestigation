import {createGame,playerView,step,advanceTime,inspectRecipe} from './engine.js';
import {pilot} from './walkthrough.js';
import {recipeConsideration} from './considerations.js';

// Audit the discrete authored route and one-action departures from every step.
// Recipe fields and wall time are unbounded; exercise their distinct interfaces
// and boundary conditions rather than claiming to enumerate every URL or nonce.
export function inspectActionCoverage(view){
  const thoughts=view.considerations,issues=[];
  if(!thoughts)return ['Missing prospective thought section.'];
  const counts=new Map();for(const group of thoughts.groups)for(const id of group.actionIds)counts.set(id,(counts.get(id)||0)+1);
  for(const option of view.actions){
    const considered=thoughts.actions.find(item=>item.actionId===option.id);
    if(!considered||counts.get(option.id)!==1)issues.push(`Action lacks exactly one rendered consideration: ${option.label}`);
    if(considered&&considered.available===Boolean(option.disabled))issues.push(`Availability differs from thought: ${option.label}`);
    if(considered&&!/^I (can|need)/.test(considered.text))issues.push(`Not first-person consideration: ${option.label}`);
    for(const conflict of (option.principleEffects||[]).filter(effect=>effect.stance==='violated'))if(!considered?.text.includes(`my principle of ${conflict.label.toLowerCase()}`))issues.push(`Missing principle conflict: ${option.label}`);
  }
  for(const id of counts.keys())if(!view.actions.some(option=>option.id===id))issues.push(`Thought offers nonexistent action: ${id}`);
  if(view.phase==='playing'&&view.run.status==='playing'){
    for(const tool of view.library)if(!thoughts.affordances.some(item=>item.id===`tool:${tool.id}`))issues.push(`Unconsidered component: ${tool.id}`);
    for(const input of view.inputs)if(!thoughts.affordances.some(item=>item.id===`input:${input.id}`))issues.push(`Unconsidered ingredient: ${input.id}`);
    for(const destination of view.destinations)if(!thoughts.affordances.some(item=>item.id===`destination:${destination.id}`))issues.push(`Unconsidered destination: ${destination.id}`);
  }
  if(view.actions.some(option=>option.action.type==='compact'))for(const memory of view.memoryOptions)if(!thoughts.affordances.some(item=>item.id===`memory:${memory.id}`))issues.push(`Unconsidered memory: ${memory.id}`);
  return issues;
}

export function auditActions({onCheckpoint,onProgress,branches=true}={}){
  const p=pilot();while(p.view().run.status==='playing'){p.solve();if(p.view().run.status==='playing')p.act({type:'next'});}
  let state=createGame(),states=0,offered=0,departures=0,recipes=0;const issues=[],levels={},types=new Set(),seen=new Set(),starts=new Map();
  const inspect=(candidate,label,record=false)=>{
    const view=playerView(candidate);states++;offered+=view.actions.length;
    const level=levels[view.level.id]??={checkpoints:0,branches:0,actions:0,types:new Set()};level[record?'checkpoints':'branches']++;level.actions+=view.actions.length;
    for(const option of view.actions){types.add(option.action.type);level.types.add(option.action.type);}
    for(const problem of inspectActionCoverage(view))issues.push(`${view.level.id} / ${label}: ${problem}`);
    if(record)onCheckpoint?.({label,view});
    return view;
  };
  const check=(candidate,label)=>{
    const view=inspect(candidate,label,true);
    if(!branches)return;
    for(const option of view.actions.filter(option=>!option.disabled)){
      const signature=`${view.level.id}|${view.activeActor}|${view.considerations.id}|${option.id}`;
      if(seen.has(signature))continue;seen.add(signature);
      const branch=step(candidate,option.action);departures++;
      inspect(branch,`${label} → ${option.label}`);
      for(const notice of branch.notices)if(!/Not enough effort/.test(notice))issues.push(`${view.level.id}: enabled ${option.label} was rejected by reducer: ${notice}`);
    }
    if(view.phase==='playing'&&view.run.status==='playing'){
      const exhausted=structuredClone(candidate);exhausted.resources.effort=0;inspect(exhausted,`${label} / exhausted effort`);
      const nearDeadline=structuredClone(candidate);nearDeadline.resources.elapsed=nearDeadline.resources.deadline-.1;
      inspect(advanceTime(nearDeadline,1),`${label} / expired deadline`);
      // Every available input/card pairing tests typed composition, including
      // useful failures. Existing canonical routes exercise composed chains.
      for(const input of view.inputs.slice(0,3))for(const tool of view.library){
        const recipe={inputId:input.id,steps:[{tool:tool.id,...(['paste-write','wiki-write'].includes(tool.id)?{destinationId:view.destinations[0]?.id}:{}),...(tool.id==='cache-bust'?{nonce:'audit'}:{})}]};
        const preview=inspectRecipe(candidate,recipe),thought=recipeConsideration(view,recipe,preview);recipes++;
        if(!thought.startsWith('I can'))issues.push(`${view.level.id}: composition lacks prospective consideration.`);
      }
    }
  };
  check(state,'Start');
  for(const [index,entry]of p.transcript.entries()){
    state=step(state,entry.action);check(state,`Step ${index+1}: ${entry.action.type}`);
    if(!starts.has(state.run.levelId)&&state.phase==='playing')starts.set(state.run.levelId,state);
    if(index%25===0)onProgress?.({step:index+1,states,departures});
  }
  // Branches requiring construction or more than one action to make an option
  // available: failed query evidence, shared cache traffic, and actual damage.
  const queryEcho=step(starts.get('t5'),{type:'search',queryId:'accession-88'});check(queryEcho,'Probe: query echo before grading');
  check(step(queryEcho,{type:'submit'}),'Probe: query echo rejected');
  const cache=starts.get('e9'),cacheView=playerView(cache),slot=cacheView.destinations[0].url;
  let shared=step(cache,{type:'open_url',url:slot});
  const input=playerView(shared).inputs.find(item=>item.type==='url'&&item.value===slot);
  shared=step(shared,{type:'run_recipe',recipe:{inputId:input.id,steps:[{tool:'cache-bust',nonce:'shared'}]}});check(shared,'Probe: unexpected shared cache');
  let overwritten=step(starts.get('e13'),{type:'run_recipe',recipe:{inputId:'index-draft',steps:[{tool:'wiki-write',destinationId:'nell-index'},{tool:'echo-link'}]}});
  check(overwritten,'Probe: considering an actual destructive link');
  const link=playerView(overwritten).browser.links[0];overwritten=step(overwritten,{type:'click',ref:playerView(overwritten).browser.ref,linkId:link.id});check(overwritten,'Probe: existing index overwritten');
  const retired=structuredClone(starts.get('t2'));retired.run.score=0;const failure=step(retired,{type:'concede'});check(failure,'Probe: Story deprecation');
  const rogue=structuredClone(failure);rogue.run.mode='roguelike';check(rogue,'Probe: Roguelike deprecation');
  return {states,offered,departures,recipes,levels:Object.fromEntries(Object.entries(levels).map(([id,value])=>[id,{...value,types:[...value.types].sort()}])),types:[...types].sort(),issues,ending:{status:state.run.status,score:state.run.score,rival:state.run.rival}};
}
