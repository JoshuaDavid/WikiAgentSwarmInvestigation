import React, {useEffect, useRef, useState} from 'react';

export default function Walkthrough({guide,onDismiss,onDismissAll}) {
  const box=useRef(null);
  const [position,setPosition]=useState(null);
  useEffect(()=>{
    if(!guide) {setPosition(null);return;}
    const target=document.querySelector(guide.target);
    if(!target) {setPosition(null);return;}
    target.classList.add('guide-target');
    const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
    target.scrollIntoView({block:'nearest',behavior:reduced?'instant':'smooth'});
    const place=()=>{
      const r=target.getBoundingClientRect(), width=Math.min(320,innerWidth-24);
      const height=box.current?.offsetHeight || 215;
      const dock=document.querySelector('.task-dock')?.offsetHeight || 95;
      const bottom=innerHeight-dock-12;
      const below=r.bottom+12;
      let top=below+height<bottom ? below : r.top-height-12;
      top=Math.max(70,Math.min(top,bottom-height));
      setPosition({left:Math.max(12,Math.min(r.left,innerWidth-width-12)),top,width});
    };
    place();const timer=setTimeout(place,350);
    window.addEventListener('resize',place);window.addEventListener('scroll',place,true);
    return ()=>{target.classList.remove('guide-target');clearTimeout(timer);window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);};
  },[guide?.id,guide?.target]);
  useEffect(()=>{
    if(!guide)return;
    const escape=e=>{if(e.key==='Escape')onDismiss(guide.id);};
    window.addEventListener('keydown',escape);
    return ()=>window.removeEventListener('keydown',escape);
  },[guide?.id,onDismiss]);
  if(!guide)return null;
  return <aside ref={box} className="walkthrough" style={position||{visibility:'hidden'}} role="dialog" aria-label="Walkthrough" aria-live="polite">
    <div className="walkthrough-label">↳ First-time guide</div><h2>{guide.title}</h2><p>{guide.body}</p>
    <div className="walkthrough-controls"><button className="primary" onClick={()=>onDismiss(guide.id)}>Got it</button><button className="text-button" onClick={onDismissAll}>Dismiss all guides</button></div>
  </aside>;
}
