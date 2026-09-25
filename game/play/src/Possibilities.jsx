import React, {useRef, useState} from 'react';
import ThoughtText, {THOUGHT_WORDS_PER_SECOND} from './ThoughtText.jsx';
import {consideredActionSections} from './presentation.js';

export default function Possibilities({view,renderAction,onBuilder,compaction}){
  const [revealedFor,setRevealedFor]=useState(null),[expanded,setExpanded]=useState({});
  const schedule=useRef(new Map());
  const {considerations}=view;
  if(!considerations)return null;
  const revealed=revealedFor===considerations.id;
  const sections=consideredActionSections(view);
  const byId=new Map(considerations.actions.map(item=>[item.actionId,item]));
  const rowIds=new Map(sections.flatMap(section=>section.options).map((option,index)=>[option.id,`reason-${view.activeActor}-${index}`]));
  let next=performance.now();
  const thought=(id,text,animate=true)=>{
    let timing=schedule.current.get(id);
    if(!timing||timing.text!==text){timing={text,start:next};schedule.current.set(id,timing);}
    if(animate)next=Math.max(next,timing.start+(text.match(/\S+/g)||[]).length*1000/THOUGHT_WORDS_PER_SECOND);
    return <ThoughtText key={text} text={text} startAt={timing.start} animate={animate&&!revealed}/>;
  };
  const builder=considerations.affordances.find(item=>item.id==='builder');
  const rows=(section,animate)=>section.options.map(option=>{
    const item=byId.get(option.id);
    return <article className={`considered-action ${option.disabled?'unavailable':''}`} key={option.id} data-considered-action={option.id} data-productivity={item?.productivity}>
      <p className="option-reason" id={rowIds.get(option.id)}>{thought(option.id,item?.text||option.description,animate)}</p>
      {renderAction({...option,description:item?.text||option.description},rowIds.get(option.id))}
      {option.action.type==='compact'&&compaction}
    </article>;
  });
  return <div className="possibilities action-panel" data-considerations-id={considerations.id}>
    <div className="possibilities-heading"><span className="section-label">{considerations.actorName} / what I could do next</span><button className="text-button" onClick={()=>setRevealedFor(considerations.id)}>Show options now</button></div>
    <p className="choice-instructions">Choose beside the thought. Enter executes; Esc reconsiders.</p>
    <div className="possibilities-text" tabIndex="0" role="region" aria-label={`${considerations.actorName}’s current considered options`}>
      {considerations.focus&&<p className="considered-focus">{thought('focus',considerations.focus)}</p>}
      {sections.filter(section=>section.id!=='controls').map(section=>section.collapsed?<details className={`considered-section choices-${section.id}`} key={section.id} open={Boolean(expanded[section.id])} onToggle={event=>{const open=event.currentTarget.open;setExpanded(old=>old[section.id]===open?old:{...old,[section.id]:open});}}><summary>{section.label}<span>{section.options.length} choices</span></summary>{rows(section,Boolean(expanded[section.id]))}</details>:<section className={`considered-section choices-${section.id}`} key={section.id}><div className="section-label">{section.label}</div>{rows(section,true)}</section>)}
      {builder&&<section className="considered-section considered-builder"><p className="option-reason">{thought('builder',builder.text)}</p><button className="builder-shortcut" onClick={onBuilder}><span>⊞</span><div><strong>Compose a URL</strong><small>{view.library.length?`${view.library.length} components available`:'Inspect available ingredients'}</small></div><b>→</b></button></section>}
      {sections.filter(section=>section.id==='controls').map(section=><section className="considered-section considered-controls" key={section.id}><div className="section-label">{section.label}</div>{rows(section,true)}</section>)}
      {!sections.length&&<p>{considerations.text}</p>}
    </div>
  </div>;
}
