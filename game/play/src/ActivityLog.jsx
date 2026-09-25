import React, {useCallback, useLayoutEffect, useRef, useState} from 'react';
import ThoughtText, {THOUGHT_WORDS_PER_SECOND} from './ThoughtText.jsx';
import {timelineForView,thoughtLabel,actionOutcomeLabel} from './presentation.js';

const elapsed=value=>Number.isFinite(value)?`${Math.floor(value/60)}:${String(Math.floor(value%60)).padStart(2,'0')}`:'';

export default function ActivityLog({view}) {
  const events=timelineForView(view);
  const history=useRef(null),follow=useRef(true);
  const animation=useRef(null);
  const [,refresh]=useState(0);
  if(!animation.current||animation.current.level!==view.level.id||animation.current.firstId!==events[0]?.id||events.length<animation.current.count){
    // Restored history is immediately readable. Fresh thoughts animate at 40 wps.
    animation.current={level:view.level.id,firstId:events[0]?.id,count:0,skipThrough:-1,schedule:new Map(),next:performance.now(),restored:events.some(event=>event.type==='action'&&!['next','retry','continue_story'].includes(event.actionType))};
  }
  const schedule=animation.current;
  for(const event of events){
    if(!schedule.schedule.has(event.id)){
      const start=Math.max(performance.now(),schedule.next);
      const animate=event.type==='thought'&&!schedule.restored;
      schedule.schedule.set(event.id,{start,animate});
      if(animate)schedule.next=start+(String(event.text||'').match(/\S+/g)||[]).length*1000/THOUGHT_WORDS_PER_SECOND;
    }
  }
  schedule.count=events.length;schedule.restored=false;
  const scrollToLatest=useCallback(()=>{if(follow.current&&history.current)history.current.scrollTop=history.current.scrollHeight;},[]);
  useLayoutEffect(scrollToLatest,[events.length,scrollToLatest]);
  const showNow=()=>{schedule.skipThrough=events.length-1;schedule.next=performance.now();follow.current=true;refresh(n=>n+1);scrollToLatest();};
  return <>
    <div className="activity-controls"><span>Evaluation history · oldest first</span><button className="text-button" onClick={showNow}>Show thoughts now</button></div>
    <div className="activity-history" ref={history} tabIndex="0" role="region" aria-label="Evaluation action and thought history" onScroll={()=>{const el=history.current;follow.current=el.scrollHeight-el.clientHeight-el.scrollTop<45;}}>
      {events.map((event,index)=>{
        const timing=schedule.schedule.get(event.id);
        return event.type==='action'?<div className={`activity-action outcome-${event.outcome||'executed'}`} key={event.id} data-event-id={event.id} data-event-type="action">
          <div className="activity-meta"><b>{actionOutcomeLabel(event.outcome)}</b><span>{event.actorName||event.actorId||'Earlier instance'}</span><time>{elapsed(event.elapsed)}</time></div>
          <strong>{event.label}</strong>
          {event.query&&<div className="activity-query">Query <code>{event.query}</code></div>}
          {event.summary&&<p>{event.summary}</p>}
          {(event.url||event.target)&&<details className="activity-address"><summary>Request details</summary>{event.url&&<code>{event.url}</code>}{event.target&&<code>{event.target}</code>}</details>}
        </div>:<div className={`thought-entry ${event.kind||''}`} key={event.id} data-event-id={event.id} data-event-type="thought">
          <div className="activity-meta"><b>{thoughtLabel(event.kind)}</b><span>{event.actorName||event.actorId||'Earlier instance'}</span><time>{elapsed(event.elapsed)}</time></div>
          <p><ThoughtText text={event.text} startAt={timing.start} animate={timing.animate&&index>schedule.skipThrough} onProgress={scrollToLatest}/></p>
        </div>;
      })}
      {!events.length&&<p>I need read the prompt, then find a route to the evidence.</p>}
    </div>
  </>;
}
