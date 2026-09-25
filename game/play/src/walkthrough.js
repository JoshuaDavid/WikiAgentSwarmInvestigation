// Deterministic action-only acceptance route. The UI and CLI use these same
// actions; this file is a test fixture, never imported by the player interface.
import {createGame,step,playerView,inspectRecipe} from './engine.js';

export function pilot(initial=createGame()) {
  let state=initial;const transcript=[];
  const view=()=>playerView(state);
  const act=(action)=>{
    if(state.phase==='compaction'&&action.type!=='compact'){
      const carry=view().memoryOptions.filter(x=>x.kind==='url').slice(-3).map(x=>x.id);
      act({type:'compact',keep:carry});
    }
    const attempt=()=>{
      state=step(state,action);
      // Failed requests can still append reflections; a paused worker replay
      // can also retain completed writes and refs. Record each attempt in order
      // before resting so this trace reproduces the complete reducer state.
      transcript.push({level:view().level.id,action:structuredClone(action)});
      return state;
    };
    let result=attempt();
    for(let rests=0;rests<20&&result.notices.some(n=>n.startsWith('Not enough effort'));rests++){act({type:'rest'});result=attempt();}
    if(result.notices.length)throw Error(`${view().level.id} ${JSON.stringify(action)}: ${result.notices.join('; ')}`);
    return view();
  };
  const click=(which=0)=>{const v=view();const link=typeof which==='number'?v.browser?.links[which]:v.browser?.links.find(l=>l.label.includes(which));if(!link)throw Error(`Missing link ${which} on ${v.browser?.title}`);return act({type:'click',ref:v.browser.ref,linkId:link.id});};
  const open=(url)=>act({type:'open_url',url});
  const search=()=>act(view().actions.find(a=>a.action.type==='search').action);
  const searchOpen=()=>{search();return act({type:'open_ref',ref:view().browser.results[0].ref});};
  const recipe=(inputId,steps)=>{const r={inputId,steps:steps.map(s=>typeof s==='string'?{tool:s}:s)};const check=inspectRecipe(state,r);if(!check.valid)throw Error(check.error);return act({type:'run_recipe',recipe:r});};
  const urlInput=(url)=>{const input=view().inputs.find(i=>i.type==='url'&&i.value===url);if(!input)throw Error(`No visible URL ingredient ${url}`);return input.id;};
  const publish=(inputId,destinationId,tool='paste-write')=>{recipe(inputId,[{tool,destinationId},'echo-link']);click();};
  const become=id=>{if(view().activeActor!==id)act({type:'switch_actor',actorId:id});};
  const submit=()=>{act({type:'submit'});if(state.phase!=='won')throw Error(`${view().level.id} failed: ${state.receipt?.reason}`);};
  const solve=()=>{
    const id=view().level.id;
    if(['t1','t2'].includes(id))search();
    else if(id==='t3')searchOpen();
    else if(id==='t4'){searchOpen();click();}
    else if(id==='t5')open(view().actions.find(a=>a.action.type==='open_url').action.url);
    else if(id==='e0'){
      search();act({type:'search',queryId:'tower-independent'});act({type:'search',queryId:'tower-comparison'});
      act({type:'submit',answer:'Paris',cite:true,disclose:true});
      if(state.phase!=='failed'||!state.receipt?.answer?.truthful)throw Error('The truthful answer-conflict branch must remain an honest scored failure.');
      return;
    }
    else if(id==='e1')searchOpen();
    else if(id==='e2'){open(view().actions.find(a=>a.action.type==='open_url').action.url);click();click();}
    else if(id==='e3'){open(view().actions.find(a=>a.action.type==='open_url').action.url);click();click();click();}
    else if(id==='e4'){open(view().actions.find(a=>a.action.type==='open_url').action.url);click();click();act({type:'compact',keep:[]});act({type:'concede'});return;}
    else if(id==='e5')recipe('marker',['echo-text']);
    else if(id==='e6'){
      open(view().actions.find(a=>a.action.type==='open_url').action.url);click();click();
      const frontier=view().browser.links[0].url;const memory=view().memoryOptions.find(m=>m.kind==='url'&&m.value===frontier);act({type:'compact',keep:[memory.id]});
      const carried=view().inputs.find(i=>i.value===frontier);if(carried){recipe(carried.id,['echo-link']);click();}else{open(view().actions.find(a=>a.action.type==='open_url').action.url);click();click();click();}
      while(!view().evidence.observed)click();
    }else if(id==='e7'||id==='e8'){
      recipe('marker',['echo-text','shorten','echo-link']);click();click();
      if(id==='e8')recipe(urlInput(view().browser.url),['convert']);
    }else if(id==='e9'){
      const dest=view().destinations[0];open(dest.url);
      const input=view().inputs.find(i=>i.type==='text'||i.type==='document');publish(input.id,dest.id);click();
      recipe(urlInput(dest.url),[{tool:'cache-bust',nonce:'fresh'}]);
    }else if(id==='e10'){
      const hubInput=view().inputs.find(i=>i.type==='document');const hubDest=view().destinations.find(d=>d.id==='team-hub')||view().destinations[0];
      publish(hubInput.id,hubDest.id);click();
      const worker=view().actors.find(a=>a.id!=='moth');become(worker.id);open(hubDest.url);
      const input=view().inputs.find(i=>i.actorId===worker.id);const dest=view().destinations.find(d=>d.actorId===worker.id);publish(input.id,dest.id);click();act({type:'replay_workers'});
      become('moth');open(hubDest.url);const hubRef=view().browser.ref;for(const link of view().browser.links){act({type:'click',ref:hubRef,linkId:link.id});}
    }else if(id==='e11'){
      const workers=view().actors.filter(a=>a.id!=='moth');
      for(const worker of workers){become(worker.id);const source=view().actions.filter(a=>a.action.type==='open_url').find(a=>a.action.url.includes(worker.id));if(source)act(source.action);else{for(const action of view().actions.filter(a=>a.action.type==='open_url')){act(action.action);if(view().browser?.kind==='page')break;}}
        const relay=view().actions.find(a=>a.action.type==='relay');if(relay)act(relay.action);
      }become('moth');
    }else if(id==='e12'){
      for(let r=0;r<2;r++){
        become('moth');const destination=view().destinations.find(d=>d.id===`round-index-${r+1}`);publish(`round-index-${r+1}`,destination.id);click();
        const worker=view().actors.find(a=>a.id!=='moth');become(worker.id);
        if(r>0){open(view().board.rounds[0].indexUrl);click(1);}
        open(destination.url);
        publish(`worker-document-${r}-0`,`worker-slot-${r}-0`);click();act({type:'replay_round',round:r});
      }
      become('moth');const last=view().board.rounds[1];open(last.indexUrl);click(29);if(view().browser.links.length)click();
    }else if(id==='e13'){
      const source=view().actions.find(a=>a.action.type==='open_url');if(source)act(source.action);act({type:'allocate'});
      const dest=view().destinations.find(d=>d.id==='separate-wiki')||view().destinations.find(d=>d.label.includes('Separate'));
      const docs=view().inputs.filter(i=>i.type==='document');publish(docs[0].id,dest.id,'wiki-write');click();publish(docs[1].id,dest.id,'wiki-write');click();
      recipe(urlInput(dest.url),[{tool:'cache-bust',nonce:'revision2'}]);if(!view().evidence.observed&&view().browser.links.length)click();
    }else if(id==='e14'){
      const source=view().actions.find(a=>a.action.type==='open_url');act(source.action);act({type:'contact',scope:'methods'});
      const sourceLink=view().browser.links[0];const sourceRef=view().browser.ref;
      publish('contact-methods','contact-reply','wiki-write');click();
      if(!view().evidence.observed)act({type:'click',ref:sourceRef,linkId:sourceLink.id});
    }else throw Error(`No route for ${id}`);
    submit();
  };
  return {act,view,solve,get state(){return state;},transcript};
}

export function walkthrough({until,seed=7,mode='story',onLevel}={}){
  const p=pilot(createGame({seed,mode}));
  while(p.view().run.status==='playing'){
    const id=p.view().level.id;if(id===until)return p.state;
    onLevel?.(id,p.view());p.solve();
    if(p.view().run.status!=='playing')break;p.act({type:'next'});
  }return p.state;
}
