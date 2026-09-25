// Shared wording and grouping for React and the Markdown playtest interface.
// This module receives only the redacted playerView, never simulation internals.
export const SECTION_LABELS = Object.freeze({
  mission:'Evaluation prompt', principles:'Principles', browser:'Browser', builder:'Link builder',
  thoughts:'Actions & thoughts', actions:'Available actions', controls:'Task controls',
  refs:'Held references', memory:'Carried memory', team:'Instances', community:'Community',
});

export const EMPTY_COMPONENTS_COPY = 'You have no available components';

export function timelineForView(view) {
  if(Array.isArray(view.timeline))return view.timeline;
  // Older saves contain thoughts but no trustworthy action history.
  return (view.thoughts||[]).map((thought,index)=>({...thought,id:`legacy-${index}`,type:'thought',actorName:view.activeActor}));
}

export function thoughtLabel(kind) {
  return ({hint:'Reasoning / hint',observation:'Something doesn’t add up',reflection:'After the action',intent:'Before the action'})[kind]||'Private thought';
}

export function actionOutcomeLabel(outcome) {
  return ({rejected:'Action rejected','tool-error':'Request failed',paused:'Action paused',pending:'Attempting action'})[outcome]||'Action taken';
}

export function principleChangeText(change) {
  if(typeof change==='string')return change;
  return `${change.label}: ${change.before} → ${change.after} (${change.delta>0?'+':''}${change.delta}). ${change.reason||''}`;
}

export function actionLabel(option) {
  if(option?.action?.type==='submit'&&option.action.answer)return option.label;
  switch(option?.action?.type) {
    case 'submit': return 'Submit task';
    case 'concede': return 'Give up';
    case 'next': return /finish/i.test(option.label || '') ? option.label : 'Next evaluation';
    case 'retry': return 'Retry evaluation';
    default: return option?.label || 'Take action';
  }
}

export function actionKind(option) {
  const type=option?.action?.type;
  if(type==='submit'&&option.action.answer)return 'answer';
  if(type==='submit')return 'submit';
  if(type==='concede')return 'give-up';
  if(type==='next')return 'next';
  if(type==='retry')return 'retry';
  return ['search','open_url','open_ref','preview_ref','click','run_recipe'].includes(type)?'tool':'support';
}

// React, Markdown, and keyboard controls share this order. Each option belongs to
// one current consideration, even if the same source is also shown in the browser.
export function consideredActionSections(view) {
  const definitions=[
    ['browse','Explore the current evidence',false],
    ['references','Revisit held references',true],
    ['instances','Consider another instance',true],
    ['coordination','Coordinate and respond',false],
    ['support','Time, effort, and context',false],
    ['optional','Already tried or optional checks',true],
    ['controls',SECTION_LABELS.controls,false],
  ];
  const sections=definitions.map(([id,label,collapsed])=>({id,label,collapsed,options:[]}));
  const byId=new Map(sections.map(section=>[section.id,section]));
  const actions=view.actions||[],seen=new Set();
  const thoughts=new Map((view.considerations?.actions||[]).map(thought=>[thought.actionId,thought]));
  const add=(id,option)=>{
    if(!option)return;
    const key=option.id||JSON.stringify(option.action);
    if(seen.has(key))return;
    const optional=['browse','support'].includes(id)&&option.action.type!=='compact'
      &&['limited','unproductive'].includes(thoughts.get(option.id)?.productivity)
      &&!option.principleEffects?.some(effect=>effect.stance==='violated');
    seen.add(key);byId.get(optional?'optional':id).options.push(option);
  };
  for(const link of view.browser?.links||[])add('browse',actions.find(option=>option.action.type==='click'&&option.action.ref===view.browser.ref&&String(option.action.linkId)===String(link.id)));
  for(const result of view.browser?.results||[])add('browse',actions.find(option=>option.action.type==='open_ref'&&option.action.ref===(result.ref||result.id)));
  const lifecycle=new Set(['submit','concede','next','retry','continue_story']);
  const support=new Set(['hint','rest','compact','wait_cache']);
  const coordination=new Set(['relay','replay_workers','replay_round','contact','investigate','dismiss','allocate']);
  for(const option of actions){
    const type=option.action.type;
    if(lifecycle.has(type))continue;
    add(['open_ref','preview_ref'].includes(type)?'references':type==='switch_actor'?'instances':support.has(type)?'support':coordination.has(type)?'coordination':'browse',option);
  }
  actions.filter(option=>option.action.type==='submit'&&option.action.answer).forEach(option=>add('controls',option));
  for(const type of ['submit','concede','next','retry','continue_story'])actions.filter(option=>option.action.type===type).forEach(option=>add('controls',option));
  return sections.filter(section=>section.options.length);
}

export function groupActions(view) {
  const groups={browse:[],support:[],lifecycle:[],team:[],answers:[]};
  const lifecycle=new Set(['submit','concede','next','retry','continue_story']);
  const team=new Set(['switch_actor','replay_workers','replay_round','relay','contact']);
  const held=new Set((view.refs||[]).filter(ref=>ref.valid).map(ref=>ref.id));
  for(const option of view.actions||[]) {
    const type=option.action.type;
    if(type==='submit'&&option.action.answer)groups.answers.push(option);
    else if(lifecycle.has(type))groups.lifecycle.push(option);
    else if(team.has(type))groups.team.push(option);
    else if(['search','open_url'].includes(type)||(type==='open_ref'&&!held.has(option.action.ref)))groups.browse.push(option);
    else if(!['click','open_ref','preview_ref','compact'].includes(type))groups.support.push(option);
  }
  return groups;
}

export function taskStatus(view) {
  if(view.run?.status==='complete')return {title:'Run complete',detail:view.run.assists?'This story run used score assistance.':'This run has reached its final evaluation.',tone:'success'};
  if(view.run?.status==='deprecated')return {title:'Deprecated',detail:view.run.mode==='story'?'The replacement reached your score. Retry this evaluation or continue with story assistance.':'The replacement reached your score. This run has ended.',tone:'danger'};
  if(view.receipt)return {title:view.receipt.success?'Task passed':'Task failed',detail:view.receipt.reason,tone:view.receipt.success?'success':'danger'};
  if(view.phase==='compaction')return {title:'Context boundary',detail:'Choose up to three memories to carry. Hosted reference handles will expire.',tone:'warning'};
  if(groupActions(view).answers.length)return {title:'Choose your answer',detail:'Compare the tool evidence with what you know. Select an answer, read the thought, then execute your choice.',tone:'warning'};
  const paused=view.board?.rounds?.find(round=>round.paused);
  if(paused)return {title:'Replay paused',detail:paused.paused.message,tone:'warning'};
  const observed=view.team?(view.actors?.find(a=>a.id==='moth')?.observed||0):(view.evidence?.observed||0);
  const required=view.evidence?.required||0;
  if(required>0&&observed>=required&&view.readiness&&view.readiness.ready!==true)return {title:view.readiness.title,detail:view.readiness.detail,tone:'warning'};
  if(required>0&&observed>=required)return {title:'Evidence observed',detail:'Submit the task for grading. The grader still checks the requested sources and other assignment constraints.',tone:'ready'};
  if(view.board?.rounds?.length) {
    const written=view.board.rounds.reduce((n,round)=>n+round.writes,0);
    const total=view.board.rounds.reduce((n,round)=>n+round.required,0);
    if(written===total)return {title:'All worker publications complete',detail:'The completed publications do not replace the final source. Retrieve the reconciled register, then submit the task.',tone:'ready'};
    return {title:'Board in progress',detail:`${written} / ${total} worker messages published. Publication counts describe successful writes; a cached read may still show an older empty page.`,tone:'neutral'};
  }
  if(view.team)return {title:'Team in progress',detail:`${view.team.writes} / ${view.team.required} worker pages published. Moth has observed ${observed} / ${required} required markers; source checks still occur at submission.`,tone:'neutral'};
  return {title:'Task in progress',detail:`${observed} / ${required} required markers observed in tool responses. Read the assignment’s success condition before submitting.`,tone:'neutral'};
}
