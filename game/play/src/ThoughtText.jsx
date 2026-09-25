import React, {useEffect, useRef, useState} from 'react';

export const THOUGHT_WORDS_PER_SECOND=40;

// The visual text grows as words arrive. Screen readers receive one complete
// paragraph. Repeated text still animates when it belongs to a new event.
export default function ThoughtText({text,animate=true,startAt,onProgress}) {
  const words=String(text||'').match(/\S+\s*/g)||[];
  const [count,setCount]=useState(()=>animate?0:words.length);
  const started=useRef(performance.now());
  useEffect(()=>{
    if(!animate||window.matchMedia('(prefers-reduced-motion: reduce)').matches){setCount(words.length);return;}
    const start=startAt??started.current;
    let frame;
    const advance=now=>{const revealed=Math.min(words.length,Math.max(0,Math.floor((now-start)*THOUGHT_WORDS_PER_SECOND/1000)));setCount(revealed);if(revealed<words.length)frame=requestAnimationFrame(advance);};
    frame=requestAnimationFrame(advance);
    return()=>cancelAnimationFrame(frame);
  },[text,animate,startAt]);
  useEffect(()=>{onProgress?.();},[count,onProgress]);
  return <span className="thought-reveal"><span className="visually-hidden">{text}</span><span aria-hidden="true" data-revealed-words={count}>{words.slice(0,count).join('')}</span></span>;
}
