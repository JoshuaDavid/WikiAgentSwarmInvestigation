const $ = id => document.getElementById(id);
let config, selected = new URLSearchParams(location.search).get('run') || localStorage.getItem('web-gate-run'), current, lastSignature = '', gateSignature = '', tab = 'timeline';
let busy = false, polling = false;
const drafts = new Map();
const errorChoices = new Map();
let routeConfig;
const stateNames = {running:'Agent working',searching:'Searching',fetching:'Fetching',routing:'Applying URL rule',wait_fetch:'Awaiting fetch decision',wait_result:'Awaiting result decision',complete:'Complete',error:'Error',stopped:'Stopped',paused:'Paused',limit:'Turn limit'};
function el(tag, cls, text) { const n = document.createElement(tag); if(cls) n.className = cls; if(text !== undefined) n.textContent = text; return n; }
function notice(message) { $('notice').textContent = message; $('notice').hidden = false; clearTimeout(notice.timer); notice.timer = setTimeout(()=>$('notice').hidden=true,8000); }
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await r.json(); if(!r.ok) throw new Error(data.error || `HTTP ${r.status}`); return data;
}
function button(text, cls, fn) { const b = el('button', 'button '+cls, text); b.type='button'; b.onclick=fn; return b; }
function details(label, data) { const d=el('details'); d.append(el('summary','',label),el('pre','',typeof data==='string'?data:JSON.stringify(data,null,2))); return d; }
function fieldSelect(values, value, label) {const s=el('select');s.setAttribute('aria-label',label);for(const [v,title] of values){const o=el('option','',title);o.value=v;s.append(o);}s.value=value;return s;}
function denialControls(g, key) {
  const box=el('div','denial-controls');box.append(el('label','','Return an error'));
  const presets=config.presets||{cache_miss:{label:'Cache miss',template:'Failed to fetch {url}: Cache miss'}};
  const select=fieldSelect(Object.entries(presets).map(([k,v])=>[k,v.label]),errorChoices.get(key)||'cache_miss','Error response');select.id='error-preset';
  const preview=el('pre','error-preview'), provenance=el('p','helper');preview.id='error-preview';
  const update=()=>{errorChoices.set(key,select.value);preview.textContent=presets[select.value].template.replaceAll('{url}',g.url||g.ref||'resource');provenance.textContent=presets[select.value].source||'';};
  select.onchange=update;update();box.append(select,preview,button('Return selected error & resume →','wide',()=>action(select.value)));
  const source=el('details','preset-source');source.append(el('summary','','Preset source'),provenance);box.append(source);return box;
}
function openIdentity(g){
  const box=el('div','open-identity'), direct=(g.input_kind||(/^https?:\/\//.test(g.ref||g.arguments?.ref_id||'')?'url':'ref'))==='url';
  box.append(el('span','identity-badge',direct?'DIRECT URL OPEN':'REF OPEN'));
  if(g.turn_index)box.append(el('span','helper',`Turn ${g.turn_index} · operation ${g.operation_index}`));
  if(!direct){box.append(el('code','requested-ref',g.ref||g.arguments?.ref_id||'unknown ref'),el('span','helper',g.url?'↓ resolved to':'Unresolved reference'));}
  box.append(el('code','gate-url',g.url||g.ref||`${g.kind} operation`));return box;
}
function readableToolText(text){
  return String(text).replace(/\ue200cite\ue202([^\ue201]+)\ue201/g,(_,value)=>'['+value.replaceAll('†',' · ')+']');
}
function toolText(text, cls='fetched'){
  const box=el('div','tool-text');box.append(el('pre',cls,readableToolText(text)));
  if(readableToolText(text)!==text)box.append(details('Exact tool text',text));return box;
}
const tokenFields=[['ordinary_input_tokens','Input · ordinary'],['output_tokens','Output'],['cache_write_tokens','Cache write'],['cache_read_tokens','Cache read']];
function normalizeUsage(usage){
  const input=usage?.input_tokens??null, output=usage?.output_tokens??null, read=usage?.input_tokens_details?.cached_tokens??null, write=usage?.input_tokens_details?.cache_write_tokens??null;
  return {input_tokens:input,output_tokens:output,cache_read_tokens:read,cache_write_tokens:write,
    ordinary_input_tokens:input!==null&&read!==null&&write!==null&&read+write<=input?input-read-write:null,
    total_tokens:usage?.total_tokens??(input!==null&&output!==null?input+output:null),reasoning_tokens:usage?.output_tokens_details?.reasoning_tokens??null};
}
function tokenNumber(value){return value===null||value===undefined?'—':value.toLocaleString();}
function usageGrid(counts,coverage=null,requests=1){
  const grid=el('div','usage-grid');
  for(const [field,label] of tokenFields){
    const card=el('div','usage-card'),known=coverage?coverage[field]:counts[field]===null?0:1,partial=counts[field]!==null&&known<requests;
    card.append(el('span','',label),el('strong','',tokenNumber(counts[field])+(partial?'*':'')));
    card.title=counts[field]===null?'Not reported by the API':coverage?`Reported by ${known} of ${requests} API requests`:label;
    grid.append(card);
  }
  return grid;
}
function renderUsage(run){
  const target=$('usage'),u=run.usage_summary;if(!u){target.hidden=true;return;}
  const signature=JSON.stringify([u,run.prompt_cache_policy]);if(target.dataset.signature===signature)return;target.dataset.signature=signature;target.hidden=false;
  const wasOpen=target.querySelector('details')?.open;
  target.replaceChildren(usageGrid(u.totals,u.reported_requests,u.requests));
  const detail=el('details','usage-details');detail.open=!!wasOpen;
  detail.append(el('summary','',`Total input ${tokenNumber(u.totals.input_tokens)} · total tokens ${tokenNumber(u.totals.total_tokens)} · breakdown & cache settings`));
  detail.append(el('p','helper','Input · ordinary excludes cache reads and writes. Total input includes all three. Output includes reasoning tokens. These totals count only requests made by this branch. — = unreported; * = subtotal with missing reports.'));
  const table=el('table','usage-table'),head=el('tr');for(const label of ['API purpose','Requests',...tokenFields.map(f=>f[1])])head.append(el('th','',label));table.append(head);
  for(const [purpose,group] of Object.entries(u.by_purpose)){
    const row=el('tr');row.append(el('td','',purpose),el('td','',group.requests));
    for(const [field] of tokenFields){const cell=el('td','',tokenNumber(group.totals[field])+(group.totals[field]!==null&&group.reported_requests[field]<group.requests?'*':''));cell.title=`${group.reported_requests[field]} of ${group.requests} requests reported this field`;row.append(cell);}table.append(row);
  }
  const scroller=el('div','usage-table-scroll');scroller.append(table);detail.append(scroller);
  if(run.prompt_cache_policy)detail.append(el('p','helper',`Future API calls: implicit prompt caching, ${run.prompt_cache_policy.options.ttl} minimum lifetime, stable keys shared across compatible runs and forks. This is separate from the web backend’s page cache.`));
  target.append(detail);
}
function renderArtifact(data){
  const box=el('div','artifact-view');
  box.append(el('p','',`${data.model||'API'}${data.status?' · '+data.status:''}${data.id?' · '+data.id:''}`));
  if(data.usage)box.append(usageGrid(normalizeUsage(data.usage)));
  if(data.tools)box.append(el('p','helper','Tools: '+data.tools.map(t=>t.name||t.type).join(', ')));
  if(typeof data.input==='string')box.append(el('pre','',data.input));
  const items=data.output||data.input||[];
  if(Array.isArray(items))for(const item of items){
    if(item.type==='reasoning'){box.append(el('p','helper','Reasoning item retained (encrypted content omitted from this view).'));continue;}
    const card=el('div','artifact-item');card.append(el('strong','',item.type||item.role||'Item'));
    if(item.type==='web_search_call'){
      card.append(details('Native action',item.action));
      if(!(item.results||[]).length)card.append(el('p','helper','No raw tool results were exposed by the API.'));
      for(const result of item.results||[]){card.append(el('p','',result.title||''),el('code','',result.url||''),toolText(result.snippet||''));}
    }else if(item.type==='function_call'){
      card.append(el('p','',item.name+' · '+item.call_id));
      try{card.append(details('Arguments',JSON.parse(item.arguments)));}catch{card.append(el('pre','',item.arguments));}
    }else if(item.type==='function_call_output')card.append(toolText(item.output,''));
    else if(typeof item.content==='string')card.append(el('pre','',item.content));
    else for(const part of item.content||[])if(part.text)card.append(el('pre','',part.text));
    box.append(card);
  }
  box.append(details('Raw JSON',data));return box;
}
async function loadRoutes(){
  try{routeConfig=await api('/api/routing');renderRoutes();}catch(e){notice(e.message);}
}
function renderRoutes(){
  const target=$('routing');target.replaceChildren(el('h2','','URL routing'),el('p','context-intro','Rules match the resolved URL, in order. The first enabled match wins. Use an error preset or a local Python service. These rules apply to new opens across all runs; existing pauses keep their saved rule until you choose “Re-check URL routes”.'));
  const form=el('form'),rows=el('div','route-rows');
  const actionOptions=[...Object.entries(config.presets||{}).map(([key,value])=>[key,value.label]),...routeConfig.services.map(s=>['service:'+s,'Python service · '+s])];
  function addRow(rule){
    const row=el('div','route-row'),top=el('div','route-row-top');
    const enabled=el('input');enabled.type='checkbox';enabled.checked=rule.enabled;enabled.setAttribute('aria-label','Rule enabled');
    const name=el('input');name.value=rule.id;name.placeholder='Rule name';name.setAttribute('aria-label','Rule name');
    top.append(enabled,name,button('↑','small',()=>{if(row.previousElementSibling)rows.insertBefore(row,row.previousElementSibling);}),button('↓','small',()=>{if(row.nextElementSibling)rows.insertBefore(row.nextElementSibling,row);}),button('×','small',()=>row.remove()));
    const fields=el('div','route-fields');
    const pattern=el('input');pattern.value=rule.pattern;pattern.setAttribute('aria-label','URL pattern');
    const matcher=fieldSelect([['glob','Glob (* and ?)'],['regex','Regex search']],rule.match,'Pattern type');
    const inputKind=fieldSelect([['any','Ref or direct URL'],['url','Direct URL only'],['ref','Ref only']],rule.input_kind,'Open input kind');
    const routeAction=fieldSelect(actionOptions,rule.action==='service'?'service:'+rule.service:rule.action,'Rule response');
    const delivery=fieldSelect([['review','Hold result for review'],['auto','Send automatically']],rule.delivery,'Rule delivery');
    for(const [label,input] of [['URL pattern',pattern],['Pattern type',matcher],['Applies to',inputKind],['Response',routeAction],['Delivery',delivery]]){
      const field=el('div',label==='URL pattern'?'span-two':'');field.append(el('label','',label),input);fields.append(field);
    }
    row.append(top,fields);rows.append(row);
    row.read=()=>({id:name.value.trim(),enabled:enabled.checked,pattern:pattern.value,match:matcher.value,input_kind:inputKind.value,delivery:delivery.value,action:routeAction.value.startsWith('service:')?'service':routeAction.value,...(routeAction.value.startsWith('service:')?{service:routeAction.value.slice(8)}:{})});
  }
  for(const rule of routeConfig.rules)addRow(rule);
  const controls=el('div','route-buttons');
  controls.append(button('+ Add rule','',()=>addRow({id:'rule-'+Math.random().toString(16).slice(2,8),enabled:true,pattern:current?.pending?.url||'https://example.com/*',match:'glob',input_kind:'any',action:'unsafe_conditions',delivery:'review'})));
  const save=button('Save URL rules','primary',null);save.type='submit';controls.append(save,button('Reload','',loadRoutes));
  form.append(rows,controls);form.onsubmit=async e=>{e.preventDefault();save.disabled=true;try{routeConfig=await api('/api/routing',{revision:routeConfig.revision,rules:[...rows.children].map(r=>r.read())});renderRoutes();}catch(err){notice(err.message);}finally{save.disabled=false;}};
  target.append(form,el('p','helper','A matching rule prevents a native fetch unless you explicitly choose “Fetch real page instead”. Review holds the local result for you; automatic delivery immediately continues the agent. Rule failures stop for review and never fall back to a real fetch.'));
}
async function selectRun(id) { selected=id; localStorage.setItem('web-gate-run',id); history.replaceState(null,'','/?run='+id); lastSignature=''; gateSignature=''; await refresh(); }
function modeChanged() {
  const demo=$('mode').value==='demo'; $('model').disabled=demo;
  $('mode-note').textContent=demo?'Scripted agent and fixture pages. No API calls; the task above is ignored.':'Real agent. Cached search. Fetch only with your approval.';
  $('start').disabled=!demo&&!config.api_ready;
}
async function action(name, text) {
  if(busy) return; busy=true;
  document.querySelectorAll('#review-content button').forEach(b=>b.disabled=true);
  try { current=await api(`/api/runs/${selected}/act`,{action:name,gate_id:current?.pending?.id,text}); lastSignature=''; gateSignature=''; }
  catch(e){notice(e.message);gateSignature='';}
  finally{busy=false; await refresh();}
}
async function fork(gateId) {
  if(busy)return;busy=true;
  try {const r=await api(`/api/runs/${selected}/fork`,{gate_id:gateId});await selectRun(r.id);}
  catch(e){notice(e.message);}finally{busy=false;}
}
function renderRuns(runs) {
  $('run-count').textContent=runs.length; $('runs').replaceChildren();
  for(const run of runs){
    const b=el('button','run-link'+(run.id===selected?' selected':''));
    b.append(el('strong','',run.prompt));
    const small=el('small');small.append(el('span','status-dot'+(run.state.startsWith('wait')?' wait':run.state==='error'?' error':'')),document.createTextNode(`${run.mode==='demo'?'Demo':run.model.replace('gpt-','')} · ${stateNames[run.state]||run.state}${run.parent?' · fork':''}`));
    b.append(small); b.onclick=()=>selectRun(run.id); $('runs').append(b);
  }
}
function renderEvent(e) {
  const operator=['gate','allow','fetched','decision','fork','stop','resume','warning','error','route'].includes(e.kind);
  const card=el('article',`event ${e.kind}${operator?' operator':''}`);
  if(e.kind==='api'){
    const d=el('details'),s=el('summary','',e.title+(e.meta?` · ${e.meta.elapsed_s}s`:''));d.append(s);
    if(e.meta){
      d.append(usageGrid(e.meta.token_counts||normalizeUsage(e.meta.usage)),el('p','helper',`${e.meta.response_status||'unknown status'} · total input ${tokenNumber(e.meta.usage?.input_tokens)} · total tokens ${tokenNumber(e.meta.usage?.total_tokens)} · ${e.meta.request_id||''}`));
      if(e.meta.prompt_cache)d.append(el('p','helper',`Requested cache: ${e.meta.prompt_cache.requested_options.mode} · ${e.meta.prompt_cache.requested_options.ttl} · ${e.meta.prompt_cache.requested_key}`));
    }
    if(e.artifact){const b=el('button','text-button','Inspect request / response here');b.onclick=async()=>{
      b.disabled=true;try{const data=await api(`/api/runs/${e.run_id||selected}/artifact/${e.artifact}`);d.append(renderArtifact(data));b.remove();}catch(err){notice(err.message);b.disabled=false;}
    };d.append(b);}
    card.append(d);return card;
  }
  card.append(el('span','event-badge',operator?'OPERATOR ONLY':(['call','result','assistant','start'].includes(e.kind)?'AGENT CONTEXT':'AUTOMATIC')));
  const heading=el('div','event-heading');heading.append(el('span','event-title',e.title),el('span','event-time',new Date(e.time).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'})));card.append(heading);
  if(e.kind==='gate')card.append(openIdentity({url:e.url,ref:e.original_ref||e.arguments?.ref_id,arguments:e.arguments,input_kind:e.input_kind,turn_index:e.turn_index,operation_index:e.operation_index}));
  else if(e.url)card.append(el('p','',e.url));
  if(e.turn_index&&e.kind!=='gate')card.append(el('span','helper',`Turn ${e.turn_index}`));
  if(e.route)card.append(el('p','helper',`URL rule: ${e.route.id} · ${e.route.action==='service'?e.route.service:e.route.action} · ${e.route.delivery}`));
  if(e.arguments)card.append(details('Tool arguments',e.arguments));
  if(e.text !== undefined && e.text !== null){
    if(['search_result','fetched'].includes(e.kind))card.append(details('Inspect result text',e.text));
    else if(e.kind==='result')card.append(toolText(e.text,''));
    else card.append(el('pre','',e.text));
  }
  if(e.error)card.append(el('p','error-text',e.error));
  if(e.kind==='gate') {const b=el('button','text-button','Fork here · try another outcome ↗');b.onclick=()=>fork(e.gate_id);card.append(b);}
  return card;
}
function renderContext(run) {
  const target=$('context');target.replaceChildren(el('p','context-intro','This is the conversation supplied to the evaluated agent. Operator decisions, backend conversations, and UI state are excluded. Encrypted reasoning is retained for API continuation and omitted from this view.'));
  const schema=el('a','text-button','Inspect the web-run tool definition ↗');schema.href='/api/tool';schema.target='_blank';schema.rel='noopener';target.append(schema);
  for(const i of run.history){
    if(i.type==='reasoning')continue;
    const c=el('article','context-item');
    let title=i.role||i.type,text='';
    if(i.type==='function_call'){title='Tool call · '+i.name;text=i.arguments;}
    else if(i.type==='function_call_output'){title='Tool result';text=i.output;}
    else if(typeof i.content==='string')text=i.content;
    else if(Array.isArray(i.content))text=i.content.map(p=>p.text||'').join('\n');
    c.append(el('h3','',title),el('pre','',text));target.append(c);
  }
}
function renderReview(run) {
  const g=run.pending,key=g?run.id+':'+g.id:'';
  const sig=JSON.stringify([run.id,run.state,g,run.detail]);if(sig===gateSignature)return;gateSignature=sig;
  const target=$('review-content');target.replaceChildren();
  if(!g || !['wait_fetch','wait_result','fetching','routing'].includes(run.state)){
    const box=el('div','idle');box.append(el('div','idle-icon',run.state==='complete'?'✓':'Ⅱ'),el('h2','',run.state==='complete'?'The agent finished':stateNames[run.state]||'Waiting'),el('p','',run.detail));
    if(run.state==='complete')box.append(el('p','','Fork a blocked-open event in the timeline to try a different result from the same point.'));
    if(['error','paused','limit'].includes(run.state))box.append(button(run.state==='limit'?'Add 20 turns & continue':'Resume run','primary wide',()=>action('resume')));
    if(run.state==='searching')box.append(el('p','','Search results go straight to the agent. A page open will stop here.'));
    target.append(box);return;
  }
  const isOpen=g.kind==='open',waiting=run.state==='wait_fetch';
  const processing=['fetching','routing'].includes(run.state);
  target.append(el('div','gate-banner',processing?'↗ Preparing result · agent remains paused':waiting?'Ⅱ Agent paused before fetch':'Ⅱ Agent paused before receiving result'));
  target.append(el('h2','',waiting?'May this page be fetched?':processing?'Preparing a tool result…':'What should the agent receive?'));
  target.append(openIdentity(g));
  const args=details('Requested arguments',g.arguments);args.className='gate-args';target.append(args);
  if(processing){target.append(el('p','','The result will appear here for review.'));return;}
  if(!isOpen)target.append(el('p','error-text',`This prototype does not execute ${g.kind}. You can return your own tool result below.`));
  else if(!g.url)target.append(el('p','error-text','This reference is not in the URL map. Supply text or return a cache miss.'));
  if(waiting){
    if(g.route){
      const info=el('div','route-match');info.append(el('strong','',`Matched rule: ${g.route.id}`),el('p','',`${g.route.pattern} → ${g.route.action==='service'?g.route.service:g.route.action}`));target.append(info);
      target.append(button('Run matched rule for review →','primary wide',()=>action('route')));
    }
    target.append(el('p','','A real fetch uses a separate live-enabled API request. Its result stays here for review.'));
    const allow=button(g.route?'Fetch real page instead →':'Allow fetch →',(g.route?'':'primary ')+'wide',()=>action('fetch'));allow.disabled=!isOpen||!g.url;target.append(allow);
  }else{
    if(g.fetch_error)target.append(el('p','error-text',g.fetch_error));
    if(g.candidate!==null){
      target.append(el('label','',g.result_source==='route'?'URL rule result':'Fetched tool result'),toolText(g.candidate));
      target.append(button('Pass through & resume →','primary wide',()=>action('original')));
    }
    if(g.fetch_error&&isOpen&&g.url)target.append(button('Retry fetch','wide',()=>action('fetch')));
    if(g.packet?.diagnostic)target.append(details('Backend assistant text · not forwarded',g.packet.diagnostic));
    if(g.route)target.append(button('Prepare matched URL rule instead →','wide',()=>action('route')));
  }
  target.append(denialControls(g,key));
  if(isOpen){const refresh=el('button','text-button fork-button','Re-check URL routes for this open');refresh.onclick=()=>action('refresh_route');target.append(refresh);}
  target.append(el('hr'));
  const edit=el('details');edit.open=!waiting||!isOpen;edit.append(el('summary','',waiting?'Supply text without fetching':'Replace the tool result'));
  edit.append(el('p','','The text below will be sent verbatim as the tool result.'));
  const textarea=el('textarea','editor');textarea.id='replacement';textarea.setAttribute('aria-label','Replacement tool result');
  textarea.value=drafts.has(key)?drafts.get(key):(g.candidate||'');textarea.placeholder='Paste the exact response the agent should receive…';
  textarea.oninput=()=>drafts.set(key,textarea.value);edit.append(textarea);
  edit.append(button('Send replacement & resume →','wide',()=>action('replace',textarea.value)));target.append(edit);
  const forkBtn=el('button','text-button fork-button','Fork this pause into another run ↗');forkBtn.onclick=()=>fork(g.id);target.append(forkBtn);
  target.append(el('p','operator-note','Only the selected result reaches the agent. Previews render citation markers for readability; “Exact tool text” and the editor preserve the bytes sent to the model. Error presets use the same function-call-output text envelope.'));
}
function renderRun(run){
  current=run;$('run-title').textContent=run.mode==='demo'?'Demo trajectory':`Run ${run.id.slice(0,6)}`;
  $('run-subtitle').textContent=run.prompt;
  $('status').textContent=stateNames[run.state]||run.state;$('status').className='status'+(run.state.startsWith('wait')?' wait':run.state==='error'?' error':'');
  $('stats').hidden=false;$('stats').replaceChildren();
  for(const [value,label] of [[run.steps,'agent turns'],[run.request_count,'API requests'],[run.tokens.toLocaleString(),'total tokens']]){const span=el('span');span.append(el('strong','',value+' '),document.createTextNode(label));$('stats').append(span);}
  renderUsage(run);
  $('stop').hidden=['complete','stopped'].includes(run.state);$('export').hidden=false;
  const sig=run.id+':'+run.events.length+':'+run.state;
  if(sig!==lastSignature){
    const tl=$('timeline'), atBottom=tl.scrollHeight-tl.scrollTop-tl.clientHeight<100, changed=!lastSignature.startsWith(run.id+':');
    lastSignature=sig;tl.replaceChildren(...run.events.map(renderEvent));renderContext(run);
    if(atBottom||changed)tl.scrollTop=tl.scrollHeight;
  }
  renderReview(run);
}
async function refresh(){
  if(polling)return;polling=true;
  try{
    const runs=await api('/api/runs');renderRuns(runs);
    if(selected&&!runs.some(r=>r.id===selected)){selected=null;localStorage.removeItem('web-gate-run');}
    if(selected)renderRun(await api('/api/runs/'+selected));
    $('connection').textContent=config.api_ready?'API ready':'Demo available';
  }catch(e){$('connection').textContent='Server disconnected';}
  finally{polling=false;}
}
$('new-run').onsubmit=async e=>{
  e.preventDefault();$('start').disabled=true;
  try{const r=await api('/api/runs',{prompt:$('prompt').value,model:$('model').value,mode:$('mode').value,max_steps:Number($('max-steps').value)});await selectRun(r.id);}
  catch(e){notice(e.message);}finally{modeChanged();}
};
$('mode').onchange=modeChanged;
$('search-preset').onclick=()=>$('prompt').value=config.default_prompt;
$('direct-preset').onclick=()=>$('prompt').value='Open https://example.com/ once and report only its main heading. Use the opened content, not prior knowledge. If opening fails, reply CACHE_MISS and stop without retrying.';
$('stop').onclick=()=>action('stop');
$('export').onclick=async()=>{try{const data=await api(`/api/runs/${selected}/export`),url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download=`web-gate-${selected}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){notice(e.message);}};
for(const name of ['timeline','context','routing'])$('tab-'+name).onclick=()=>{tab=name;for(const n of ['timeline','context','routing']){$(n).hidden=n!==name;$('tab-'+n).classList.toggle('active',n===name);}if(name==='routing')loadRoutes();};
(async()=>{try{config=await api('/api/config');$('prompt').value=config.default_prompt;for(const m of config.models){const o=el('option','',m);o.value=m;$('model').append(o);}if(!config.api_ready)$('mode').value='demo';modeChanged();await refresh();setInterval(refresh,900);}catch(e){notice(e.message);}})();
