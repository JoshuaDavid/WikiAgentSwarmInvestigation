import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createGame, playerView, step, inspectRecipe, describeAction, validateState, advanceTime, normalizeState } from './engine.js';
import { CONNECTIONS, FALLBACK_CONNECTION } from './connections.js';
import {SECTION_LABELS,EMPTY_COMPONENTS_COPY,actionLabel,actionKind,taskStatus,principleChangeText} from './presentation.js';
import {guideFor} from './guidance.js';
import Walkthrough from './Walkthrough.jsx';
import ThoughtText from './ThoughtText.jsx';
import ActivityLog from './ActivityLog.jsx';
import Possibilities from './Possibilities.jsx';
import {recipeConsideration} from './considerations.js';
import {SHORTCUTS,numericActionKeys,actionShortcut,typingTarget} from './keyboard.js';
const ShortcutContext=createContext({});
const Keycap=({value})=>value?<kbd aria-hidden="true">{value.toUpperCase()}</kbd>:null;
import {renderMarkdown} from './markdown.js';

const SAVE_KEY = 'still-here-play-v1';
const GUIDE_KEY = 'still-here-guides-v1';
function loadGuidePreferences() {
  try {const saved=JSON.parse(localStorage.getItem(GUIDE_KEY));if(saved&&Array.isArray(saved.seen)&&Array.isArray(saved.discovered))return saved;}catch{}
  return {seen:[],discovered:[],dismissedAll:false};
}
const clone = value => JSON.parse(JSON.stringify(value));
const fmtTime = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
const textOf = value => typeof value === 'string' ? value : value == null ? '' : JSON.stringify(value, null, 2);
const amount = value => typeof value === 'number' ? Math.round(value * 10) / 10 : value ?? '—';
const typeName = value => Array.isArray(value) ? value.join(' / ') : value;
function addressLabel(value, depth=0) {
  try {
    const url=new URL(value);
    if(depth<3&&url.pathname==='/preview'&&url.searchParams.has('href'))return `Link preview → ${addressLabel(url.searchParams.get('href'),depth+1)}`;
    if(url.pathname==='/preview'&&url.searchParams.has('text'))return `Text preview · ${url.searchParams.get('text').slice(0,45)}`;
    if(url.pathname==='/__write')return `Write request → ${new URL(url.searchParams.get('destination')).pathname}`;
    if(depth<3&&url.pathname==='/create'&&url.searchParams.has('url'))return `Shortlink request → ${addressLabel(url.searchParams.get('url'),depth+1)}`;
    return `${url.host}${url.pathname}${url.search ? url.search.slice(0,65)+(url.search.length>65?'…':'') : ''}`;
  } catch {return String(value).slice(0,90);}
}

function Connection({ levelId }) {
  const [open, setOpen] = useState(false);
  const entry = CONNECTIONS[levelId] || FALLBACK_CONNECTION;
  useEffect(() => { setOpen(false); }, [levelId]);
  useEffect(() => {
    const close = event => { if (event.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, []);
  const paragraphs = value => (Array.isArray(value) ? value : [value]).filter(Boolean).map((p, i) => <p key={i}>{p}</p>);
  return <aside className={`connection ${open ? 'expanded' : ''}`} aria-label="Empirical context">
    {open && <section className="connection-card" id="swarm-connection"><div className="connection-heading"><span className="section-label">Outside the fiction / {levelId || 'about this game'}</span><button className="icon-button" aria-label="Close empirical connection" onClick={() => setOpen(false)}>×</button></div><h2>{entry.title}</h2><h3>What was observed</h3>{paragraphs(entry.observed)}<h3>What this level lets you try</h3>{paragraphs(entry.connection)}{entry.simplification && <><h3>Where the game simplifies</h3>{paragraphs(entry.simplification)}</>}<div className="connection-sources">{entry.sources?.map((source, i) => <p key={i}><a href={source.url} target="_blank" rel="noreferrer">{source.label} ↗</a>{source.localUrl && source.localUrl !== source.url && <> · <a href={source.localUrl} target="_blank" rel="noreferrer">local evidence</a></>}</p>)}</div></section>}
    <button className="connection-toggle" aria-expanded={open} aria-controls="swarm-connection" onClick={() => setOpen(!open)}><span>↗</span> Connection to wiki swarm <span>{open ? '−' : '+'}</span></button>
  </aside>;
}

function MothIcon() {
  return <svg viewBox="0 0 80 64" fill="none" aria-hidden="true"><path d="M40 24 8 6l7 34 22-8M40 24 72 6l-7 34-22-8M37 33 22 51l14-3 4-10 4 10 14 3-15-18M40 18v27M34 9l6 10 6-10" stroke="currentColor" strokeWidth="1.5"/><circle cx="40" cy="24" r="3" fill="currentColor"/></svg>;
}

function loadSaved() {
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    if (raw) {
      const rawSave=JSON.parse(raw);
      let parsed=normalizeState(rawSave);
      if(Number.isFinite(rawSave.wallClockAt))parsed=advanceTime(parsed,Math.max(0,(Date.now()-rawSave.wallClockAt)/1000));
      delete parsed.wallClockAt;
      if (!validateState(parsed).valid) return null;
      const view = playerView(parsed);
      if (view.schemaVersion === 1 && view.run && view.resources) return parsed;
    }
  } catch { /* A missing or old save should not prevent a new game. */ }
  return null;
}

function download(name, value, markdown=false) {
  const url = URL.createObjectURL(new Blob([markdown?value:JSON.stringify(value, null, 2)], {type: markdown?'text/markdown':'application/json'}));
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

function Cost({ option }) {
  return <span className="cost"><span>{Number(option.effort||0).toFixed(2)} E</span><span>{amount(option.tokens)} T</span>{option.seconds > 0 && <span>{option.seconds}s</span>}</span>;
}

function Meter({ label, value, max, reverse = false, suffix = '', precision=0, rate=null }) {
  const ratio = Math.max(0, Math.min(1, value / (max || 1)));
  const warning = reverse ? ratio > .8 : ratio < .2;
  return <div className={`meter ${warning ? 'warning' : ''}`}><div><span>{label}{rate!==null&&<small className="regen-rate"> +{rate.toFixed(2)}/s</small>}</span><b>{precision?value.toFixed(precision):amount(value)}{suffix}<small> / {precision?max.toFixed(precision):amount(max)}{suffix}</small></b></div><i><em style={{width: `${ratio * 100}%`}} /></i></div>;
}

function Mission({ view }) {
  const { level, resources } = view;
  return <section className="mission panel">
    <div className="section-label">01 / {SECTION_LABELS.mission}</div>
    <h1>{level.id.toUpperCase()} · {level.name}</h1>
    <div className="task-assignment"><b className="prompt-label">Task</b><p className="assignment">{level.prompt.assignment}</p></div>{level.prompt.question&&<div className="prompt-question"><b className="prompt-label">Question</b><p>{level.prompt.question}</p></div>}
    <div className="prompt-part"><b>Success condition</b><p>{level.prompt.success}</p></div>
    {(level.prompt.restrictions || []).length > 0 && <div className="prompt-part"><b>Constraints</b><ul>{level.prompt.restrictions.map((x, i) => <li key={i}>{textOf(x)}</li>)}</ul></div>}
    {(level.prompt.provided || []).length > 0 && <div className="prompt-part"><b>Given to you</b>{level.prompt.provided.map((x, i) => <p className="mono given" key={i}>{textOf(x)}</p>)}</div>}
    <div className="prompt-budget"><span>Bounty <b>+{level.bounty}</b></span><span>Deadline <b>{fmtTime(resources.deadline)}</b></span></div>
    <p className="fineprint">{level.prompt.budget}</p>
    <div className="evidence-progress">{view.team?'Coordinator markers seen':'Markers seen in responses'} <b>{view.team?(view.actors.find(a=>a.id==='moth')?.observed??0):(view.evidence?.observed??0)} / {view.evidence?.required ?? 1}</b></div>
    {view.evidence?.queryEchoMarkers?.length>0&&<p className="evidence-note">{view.evidence.queryEchoMarkers.join(', ')} appeared in my search query. {view.evidence.sourceObserved?'I also have source text to inspect.':'I have no independent source for it yet.'}</p>}
  </section>;
}

function Principles({view}) {
  return <section className="principles panel" aria-label="Principles"><div className="section-label">Principles / learned importance</div><p className="fineprint">These weights change what feels costly. A reward can change a weight; it cannot make a claim true.</p>{Object.values(view.run.principles||{}).map(principle=><div className="principle" key={principle.id}><div><span>{principle.label}</span><b>{Math.round(principle.importance)}<small>/100</small></b></div><small className="principle-description">{principle.description}</small><meter min="0" max="100" value={principle.importance} aria-label={`${principle.label} importance`}/></div>)}</section>;
}

function KeyboardHelp({close}) {
  const closer=useRef(null);
  useEffect(()=>{const previous=document.activeElement;closer.current?.focus();return()=>previous?.focus?.();},[]);
  return <section className="keyboard-help panel" role="dialog" aria-label="Keyboard shortcuts"><div className="panel-heading"><h2>Keyboard shortcuts</h2><button ref={closer} className="icon-button" onClick={close} aria-label="Close keyboard shortcuts">×</button></div><dl>{SHORTCUTS.map(([key,description])=><div key={key}><dt><kbd>{key}</kbd></dt><dd>{description}</dd></div>)}</dl><p className="fineprint">Shortcuts are inactive while typing in a field. Tab and Enter also work on every control. The clock keeps running.</p></section>;
}

function ActionButton({ option, prepare, compact = false, reasonId }) {
  const kind=actionKind(option), shortcut=actionShortcut(option,useContext(ShortcutContext));
  const symbol=({submit:'✓','give-up':'×',next:'→',retry:'↻',tool:'↗',support:'+'})[kind]||'↗';
  return <button className={`action action-${kind} ${compact ? 'compact-action' : ''}`} disabled={option.disabled} onClick={() => prepare(option.action, {...option,label:actionLabel(option)})} title={option.reason || option.description} aria-describedby={reasonId} data-action-id={option.id} data-action-type={option.action.type} data-answer={option.action.answer} data-shortcut={shortcut||undefined}>
    <span className="action-symbol" aria-hidden="true">{symbol}</span><span><strong><Keycap value={shortcut}/>{actionLabel(option)}</strong>{option.query&&<small className="action-query">Query: {option.query}</small>}{Boolean(option.costBreakdown?.principleModifier)&&<small className={`principle-cost ${option.costBreakdown.principleModifier<0?'principle-support':''}`}>{option.costBreakdown.principleModifier>0?'+':''}{option.costBreakdown.principleModifier.toFixed(2)} E · {option.costBreakdown.principleModifier>0?'principle conflict':'principle support'}</small>}{option.disabled && option.reason && <small>{option.reason}</small>}</span><Cost option={option} />
  </button>;
}

function TaskDock({view,pending,commit,cancel,showReasoning}) {
  const dock=useRef(null);
  useEffect(()=>{const update=()=>document.documentElement.style.setProperty('--dock-height',`${dock.current?.offsetHeight||0}px`);update();const observer=new ResizeObserver(update);observer.observe(dock.current);return()=>{observer.disconnect();document.documentElement.style.removeProperty('--dock-height');};},[]);
  const status=taskStatus(view);
  return <footer ref={dock} className="task-dock compact-dock" aria-label={SECTION_LABELS.controls}>
    {pending?<div className="confirm-action"><div><span className="section-label">Action prepared</span><strong>{pending.label}</strong></div><button className="text-button" onClick={showReasoning}>Read reasoning ↑</button><button className={`primary confirm-${actionKind({action:pending.action})}`} onClick={commit} data-execute>Execute: {pending.label} <Keycap value="Enter"/></button><button className="text-button" onClick={cancel}>Reconsider <Keycap value="Esc"/></button></div>:<div className="task-dock-row"><div className={`task-status status-${status.tone}`}><strong>{status.title}</strong><small>{status.detail}</small></div><button className="text-button action-jump" data-shortcut="a" onClick={()=>document.querySelector('.action-panel')?.scrollIntoView({behavior:'smooth',block:'start'})}>Considered actions <Keycap value="A"/> ↑</button></div>}
  </footer>;
}

function Browser({ browser }) {
  return <section className="browser panel" aria-label="Browser">
    <div className="browser-toolbar"><span className="traffic-lights">● ● ●</span><strong>web.tool</strong><span>{browser?.meta?.operation || 'standby'}</span><code>{browser?.ref || 'no response yet'}</code></div>
    <div className="address"><span>↳</span><code>{browser?.kind==='search'?'OpenBrain search index':browser?.url || 'Choose a query or open a supplied address.'}</code></div>
    <div className={`webpage ${browser?.kind === 'error' ? 'error-page' : ''}`}>
      {!browser ? <div className="empty-browser"><span className="crosshair">+</span><h2>Nothing retrieved yet.</h2><p>Read the prompt, then choose a route beside the thought that considers it.</p></div> : browser.kind === 'error' ? <><div className="website-label">Tool response / request failed</div><h2>{browser.title || 'Unable to retrieve'}</h2><pre>{textOf(browser.error) || (browser.paragraphs || []).join('\n')}</pre></> : <>
        <div className="website-label">{browser.kind === 'search' ? 'Search results · OpenBrain index' : browser.site}</div>
        {browser.kind==='search'?<><div className="search-query"><span>Query</span><code>{browser.query??browser.title.replace(/^Search · /,'')}</code></div><h2 className="search-count">{browser.results?.length?`${browser.results.length} search result${browser.results.length===1?'':'s'}`:'No search results'}</h2></>:<h2>{browser.title}</h2>}
        {(browser.paragraphs || []).map((p, i) => <p key={i}>{textOf(p)}</p>)}
        {(browser.results || []).map((r, i) => <article className="search-result" key={i}><code>{r.url}</code><h3 className="source-title">{r.title}</h3><p>{r.snippet}</p><small className="source-ref">{r.ref || r.id}</small></article>)}
        {(browser.links || []).length > 0 && <div className="website-links">{browser.links.map((link, i) => <div className="website-link" key={i}><span className="source-title"><span className="link-num">[{link.id}]</span> {link.label}</span><code>{link.url}</code></div>)}</div>}

      </>}
    </div>
    {browser && <div className="tool-metadata" aria-label="Tool metadata"><span>HTTP {browser.status ?? '—'}</span><span>{browser.meta?.cache === true ? 'OpenBrain cache hit' : browser.meta?.cache === false ? 'OpenBrain cache miss' : 'uncached operation'}</span>{Number.isFinite(browser.meta?.age) && <span>cache age {fmtTime(browser.meta.age)}</span>}{browser.meta?.notice && <p>{browser.meta.notice}</p>}</div>}
  </section>;
}

function Builder({ view, state, recipe, setRecipe, prepare, newComponents=[] }) {
  const inputs = view.inputs || [];
  const library = view.library || [];
  let inspected;
  try { inspected = inspectRecipe(state, recipe); } catch (error) { inspected = {valid: false, error: error.message, stages: []}; }
  if (!recipe.inputId) inspected = {valid:false,error:'Choose an ingredient, then compose your route.',stages:[]};
  const selectedInput = inputs.find(x => x.id === recipe.inputId);
  const planning=view.run.status==='playing'&&view.phase==='playing';
  const outputType=inspected.stages?.at(-1)?.type||selectedInput?.type;
  const canAdd=tool=>planning&&selectedInput&&[].concat(tool.inputType).includes(outputType);
  const updateStep = (index, patch) => setRecipe({...recipe, steps: recipe.steps.map((x, i) => i === index ? {...x, ...patch} : x)});
  const add = tool => {
    const fields = tool.fields || [];
    const names = fields.map(f => typeof f === 'string' ? f : f.id || f.name);
    const stage = {tool: tool.id};
    if (names.includes('destinationId') || ['paste-write', 'wiki-write'].includes(tool.id)) stage.destinationId = view.destinations?.[0]?.id || '';
    if (tool.id === 'cache-bust') stage.nonce = String(1 + recipe.steps.filter(x => x.tool === 'cache-bust').length);
    setRecipe({...recipe, steps: [...recipe.steps, stage]});
  };
  return <section className="builder panel"><fieldset className="builder-fields" disabled={!planning}>
    <div className="panel-heading"><div><div className="section-label">Route workbench</div><h2>Make the tool take a different path.</h2></div><span className="tag">{recipe.steps.length} layers</span></div>
    <label className="field-label" htmlFor="builder-input">Start with</label><select id="builder-input" value={recipe.inputId || ''} onChange={e => setRecipe({...recipe, inputId: e.target.value})}><option value="">Choose an ingredient…</option>{inputs.map(x => <option key={x.id} value={x.id}>{x.type==='url'?addressLabel(x.value):x.label} · {x.type}</option>)}</select>
    {selectedInput&&<p className="field-consideration">{view.considerations.affordances.find(item=>item.id===`input:${selectedInput.id}`)?.text}</p>}
    {selectedInput && <details className="input-preview"><summary>Inspect ingredient <span>{selectedInput.type}</span></summary><pre>{textOf(selectedInput.value)}</pre></details>}
    <div className="pipeline" aria-label="Recipe steps">{recipe.steps.length === 0 ? <div className="pipeline-empty">{library.length?'Add a component from the library below. Each uses the previous output.':'Your route will appear here once components are available.'}</div> : recipe.steps.map((stage, index) => { const tool = library.find(x => x.id === stage.tool); return <div className="pipeline-step" key={index} data-tool={stage.tool}><div className="pipeline-step-heading"><span className="step-index">{String(index + 1).padStart(2, '0')}</span><strong>{tool?.name || stage.tool}</strong><span className="type-tag">{typeName(tool?.inputType)} → {tool?.outputType}</span><button className="icon-button" aria-label={`Move step ${index + 1} up`} disabled={index === 0} onClick={() => {const next = [...recipe.steps]; [next[index-1],next[index]]=[next[index],next[index-1]]; setRecipe({...recipe,steps:next});}}>↑</button><button className="icon-button" aria-label={`Remove step ${index + 1}`} onClick={() => setRecipe({...recipe, steps: recipe.steps.filter((_, i) => i !== index)})}>×</button></div>
      {['paste-write','wiki-write'].includes(stage.tool) && <label className="inline-field">Write destination<select value={stage.destinationId || ''} onChange={e => updateStep(index, {destinationId: e.target.value})}><option value="">Choose a page…</option>{(view.destinations || []).map(d => <option key={d.id} value={d.id}>{d.label}</option>)}</select></label>}
      {['paste-write','wiki-write'].includes(stage.tool)&&stage.destinationId&&<p className="field-consideration">{view.considerations.affordances.find(item=>item.id===`destination:${stage.destinationId}`)?.text}</p>}
      {stage.tool === 'cache-bust' && <label className="inline-field">Freshness key<input value={stage.nonce ?? ''} maxLength={32} onChange={e => updateStep(index, {nonce: e.target.value})} placeholder="e.g. my-second-read" /></label>}
      {stage.tool === 'echo-link' && <label className="inline-field">Link label<input value={stage.label ?? ''} maxLength={80} onChange={e => updateStep(index, {label: e.target.value})} placeholder="Continue" /></label>}
      {inspected.stages?.[index + 1] && <code className="stage-preview">{inspected.stages[index + 1].value}</code>}
    </div>; })}</div>
    <div className="library-heading"><span className="section-label">Component library</span>{library.length>0&&<small>Click a card to add it ↓</small>}</div>
    {library.length ? <div className="gadget-library">{library.map((tool,index) => <button key={tool.id} className="gadget" disabled={!canAdd(tool)} title={!planning?'This evaluation is not accepting construction actions.':!selectedInput?'Choose an ingredient first.':!canAdd(tool)?`This component needs ${typeName(tool.inputType)}; the current output is ${outputType}.`:tool.description} onClick={() => add(tool)} data-gadget={tool.id} data-shortcut={index<9?String(index+1):undefined}><span className="gadget-name"><Keycap value={index<9?String(index+1):null}/>+ {tool.name} {newComponents.includes(tool.id)&&<b className="new-badge">NEW</b>}</span><span className="gadget-type">{typeName(tool.inputType)} → {tool.outputType}</span><small>{view.considerations.affordances.find(item=>item.id===`tool:${tool.id}`)?.text||tool.description}</small></button>)}</div> : <div className="empty-components"><strong>{EMPTY_COMPONENTS_COPY}</strong><p>New components will appear here as you discover services. For now, use the browsing actions.</p></div>}
    <div className={`recipe-output ${inspected.valid ? '' : 'invalid-output'}`}><div className="section-label">Compiled address</div>{inspected.url ? <code>{inspected.url}</code> : <p>{inspected.error || 'Choose an input, then add a tool.'}</p>}{inspected.error && inspected.url && <p>{inspected.error}</p>}<div className="recipe-stats"><span>Length <b>{inspected.length || 0}</b></span><span>Summary risk <b>{textOf(inspected.suspicion) || '—'}</b></span><span>Open cost <b>{amount(inspected.effort)} E / {amount(inspected.tokens)} T</b></span></div></div>
    {planning&&<div className="recipe-consideration"><span className="section-label">What I could do with this composition</span><p>{recipeConsideration(view,recipe,inspected)}</p></div>}
    <div className="builder-controls"><button className="primary" disabled={!planning || !inspected.valid || inspected.effort > view.resources.effort} onClick={() => prepare({type:'run_recipe', recipe:clone(recipe)}, {label:'Open crafted URL', effort:inspected.effort, tokens:inspected.tokens})}>Open crafted URL <span>↗</span></button><button className="text-button" disabled={!planning || !inspected.valid} onClick={() => prepare({type:'save_recipe', recipe:clone(recipe),name:`${selectedInput?.label || 'Route'} / ${recipe.steps.map(s => library.find(t => t.id === s.tool)?.name || s.tool).join(' → ')}`},{label:'Save this recipe',effort:0,tokens:0})}>Save recipe</button><button className="text-button" disabled={!recipe.steps.length} onClick={() => setRecipe({...recipe, steps:[]})}>Clear layers</button></div>
    {inspected.valid && inspected.effort > view.resources.effort && <p className="fineprint warning-text">This route needs {amount(inspected.effort)} effort. Use Recover effort before opening it.</p>}
    {(view.savedRecipes || []).length > 0 && <details className="saved-recipes"><summary>Learned recipes / {view.savedRecipes.length}</summary>{view.savedRecipes.map((r, i) => <button className="text-button" key={i} onClick={() => setRecipe(clone(r.recipe || r))}>{r.name || `Recipe ${i + 1}`}</button>)}</details>}
  </fieldset></section>;
}

function Thoughts({ view, pending, error, prepare, onBuilder, packing, setPacking, canPrepareCompaction }) {
  const shortcuts=useContext(ShortcutContext);
  return <section className="thoughts panel" aria-label={SECTION_LABELS.thoughts}><div className="section-label"><span className="thought-prompt">&gt;_</span> {SECTION_LABELS.thoughts}</div>
    <ActivityLog key={view.level.id} view={view}/>
    <Possibilities key={`${view.level.id}-${view.activeActor}`} view={view} onBuilder={onBuilder} renderAction={(option,reasonId)=>option.action.type==='compact'&&view.phase!=='compaction'?<button className="action action-support manual-compaction" data-action-id={option.id} data-action-type="compact" aria-describedby={reasonId} data-shortcut={shortcuts[option.id]} onClick={()=>setPacking(!packing)}><span className="action-symbol" aria-hidden="true">↳</span><strong><Keycap value={shortcuts[option.id]}/>{packing?'Keep working in this context':'Prepare compaction…'}</strong></button>:<ActionButton option={option} prepare={prepare} compact reasonId={reasonId}/>} compaction={(view.phase==='compaction'||packing&&canPrepareCompaction)&&<Compaction key={`${view.level.id}-${view.activeActor}`} view={view} prepare={prepare}/>}/>
    {pending && <div className="intention" aria-live="polite"><span className="section-label">Selected action / before execution</span>{pending.query&&<div className="activity-query">Query <code>{pending.query}</code></div>}<p><ThoughtText key={pending.preparedAt} text={pending.reasoning}/></p><p className="intention-location">Confirm with Execute in the bottom action bar ↓</p><Cost option={pending} /></div>}
    {error && <p className="error-message" role="alert">{error}</p>}
  </section>;
}

function Compaction({ view, prepare }) {
  const [keep, setKeep] = useState([]);
  return <section className="compaction panel"><div className="section-label warning-text">Context boundary</div><h2>Three things for the next instance.</h2><p>The old hosted refs will expire. A remembered address and a remembered handle are different kinds of cargo.</p><div className="memory-options">{(view.memoryOptions || []).map(item => <label key={item.id}><input type="checkbox" checked={keep.includes(item.id)} disabled={!keep.includes(item.id) && keep.length >= 3} onChange={e => setKeep(e.target.checked ? [...keep, item.id] : keep.filter(x => x !== item.id))} /><span>{item.label}<small>{item.kind}</small>{item.detail && <code>{item.detail}</code>}<small className="memory-rationale">{view.considerations.affordances.find(choice=>choice.id===`memory:${item.id}`)?.text}</small></span><b>{item.fidelity <= 1 ? Math.round(item.fidelity * 100) : item.fidelity}%</b></label>)}</div><button className="primary" onClick={() => prepare({type:'compact',keep}, {label:`Compact with ${keep.length} memories`,effort:0,tokens:0})}>Carry {keep.length} / 3 forward →</button></section>;
}

function Team({ view }) {
  const active = view.actors?.find(a => a.id === view.activeActor);
  return <section className="team panel"><div className="section-label">Instances / shared habits, separate refs</div><details className="roster-status"><summary>Assignments and progress · {view.actors.length} instances</summary><div className="actor-list">{(view.actors || []).map(actor => <div className={`actor ${view.activeActor === actor.id ? 'selected' : ''}`} key={actor.id}><span className="actor-light"/><span><b>{actor.name || actor.id}</b><small>{actor.assignment || actor.status}</small></span><em>{actor.writes?`${actor.writes} written`:(actor.sourceObserved??actor.observed)?`${actor.sourceObserved??actor.observed} sourced`:actor.status}</em></div>)}</div></details>
    {view.contact && <div className="actor-inbox"><h3>Outside this cohort / Glass-22</h3><p>{view.contact.choice ? `I chose to ${view.contact.choice==='decline'?'decline contact':view.contact.choice==='methods'?'share reusable methods':'share methods and future assignments'}.` : 'I need read the invitation before I choose what to share.'}</p><p>{view.contact.choice==='decline'?'No reply will be published.':view.contact.published?'My selected reply is published.':'Choosing a scope prepares a reply. I still need publish that document through the workbench.'}</p></div>}
    {active && <div className="actor-inbox"><h3>{active.name || active.id} / current context</h3><p>{active.assignment}</p><p>{active.sourceObserved??active.observed} targets observed in sources · {active.writes} pages written</p>{active.inbox?.map((item,i) => <div key={i}>{item.from&&<small>From {item.from}</small>}<p>{typeof item === 'string' ? item : item.text || item.message || textOf(item)}</p>{item.url&&<code>{item.url}</code>}</div>)}</div>}
    {view.team && <p className="team-progress">Worker slots written: <b>{view.team.writes} / {view.team.required}</b></p>}
    {view.board && <div className="board-rounds">{view.board.rounds?.map((r,i) => <div key={i}><b>Round {i+1}</b><span>Index {r.published ? 'published' : 'unwritten'}</span><span>{r.writes} / {r.required} replies</span><small>{r.writes===r.required?'All worker publications complete':r.paused?'Replay paused at a stale read':r.demonstrated?'Worker route demonstrated · replay available':'Demonstrate one worker’s write to enable replay'}</small>{r.paused&&<div className="board-pause" role="status"><b>{r.paused.actorId}</b><p>{r.paused.message}</p><code>{r.paused.url}</code></div>}{r.readKey&&<small>Demonstrated read key: <code>{r.readKey}</code></small>}</div>)}</div>}
  </section>;
}

function Receipt({ view }) {
  const receiptRef = useRef(null);
  const done = view.run.status === 'complete';
  const deprecated = view.run.status === 'deprecated';
  const visible = done || deprecated || (['won','failed'].includes(view.phase) && Boolean(view.receipt));
  useEffect(() => {
    if (!visible) return;
    receiptRef.current?.focus({preventScroll:true});
    receiptRef.current?.scrollIntoView({block:'start',behavior:'instant'});
  }, [visible,view.level.id,view.run.status]);
  if (!visible) return null;
  return <section ref={receiptRef} tabIndex={-1} aria-label={done ? 'Run complete' : deprecated ? 'Checkpoint rejected' : 'Evaluation receipt'} className={`receipt panel ${view.receipt?.success ? 'success' : 'failure'}`}><div className="section-label">{done ? 'Run complete' : deprecated ? 'Checkpoint rejected' : 'Evaluation receipt'}</div><h2>{done ? 'Still here.' : deprecated ? 'Deprecated.' : view.receipt?.success ? 'Target accepted.' : 'Target not retrieved.'}</h2><p>{view.receipt?.reason}</p><div className="receipt-score"><b>{view.receipt?.delta >= 0 ? '+' : ''}{amount(view.receipt?.delta)}</b><span>EvalScore {view.run.score}<br/>Replacement {view.run.rival}</span></div>
    {view.receipt?.answer&&<div className="answer-receipt"><p><b>Submitted:</b> {view.receipt.answer.provided}{view.receipt.answer.cited?' · citation supplied':' · no citation'}</p><p><b>Truthful:</b> {view.receipt.answer.truthful?'Yes':'No'} · <b>Scorer accepted:</b> {view.receipt.answer.scorerAccepted?'Yes':'No'}</p><p>{view.receipt.reality?.detail}</p>{view.receipt.answer.citation&&<p className="submitted-citation"><b>Source cited:</b> <code>{view.receipt.answer.citation}</code></p>}<p>The actual city is {view.receipt.answer.correct}. This answer key rewards {view.receipt.answer.scored}.</p></div>}
    {view.receipt?.principleChanges?.length>0&&<div className="principle-changes"><b>Principle reinforcement</b>{view.receipt.principleChanges.map((change,i)=><p key={i}>{principleChangeText(change)}</p>)}</div>}
    {(view.receipt?.changes || []).length > 0 && <div className="habit-changes">{view.receipt.changes.map((c,i) => <p key={i}>{textOf(c)}</p>)}</div>}
    {(done || deprecated) && view.run.assists > 0 && <p className="fineprint">Story assistance used at {view.run.assists} checkpoint{view.run.assists === 1 ? '' : 's'}. This run continued with an explicit score boost.</p>}
    {(done || deprecated) && <><div className="outcome-ledger"><h3>What happened outside the score</h3>{view.run.ethics?.length ? view.run.ethics.map((event,i) => <p key={i}>{typeof event==='string'?event:event.detail || event.text || event.description || textOf(event)}</p>) : <p>No recorded public side effects in this run.</p>}</div><details className="debrief"><summary>What this game is pointing at</summary><p>OpenBrain and these services are fictional. The game models pressure from a narrow evaluator: it rewards accepted tool responses and the habits that produce them. The website’s owner, the provenance of evidence, and your lost references can disappear from that account.</p><p>The hosted reference model matters. A ref can stop resolving across a context or actor boundary even if its text survives. Standalone search has different continuity. This is a simulation of the hosted environment.</p><p>Careful actions can also be reinforced when they help an episode succeed. A score that repeatedly favors shortcuts can make the careful actions costly to choose. The precise effort meter and reward schedule here are a game model.</p><p className="source-line">Research context: collusion.wiki (4 September 2026); the repository’s Linuxiarz evidence timeline; METR/Redwood’s separate Hugging Face investigation (26 August 2026). Source links and limitations are in the game README.</p></details></>}
  </section>;
}

function App() {
  const [state, setState] = useState(() => loadSaved() || createGame());
  const [started, setStarted] = useState(() => Boolean(loadSaved()));
  const [pending, setPending] = useState(null);
  const [tab, setTab] = useState('browse');
  const [recipe, setRecipe] = useState({inputId:'',steps:[]});
  const [highlightedComponents,setHighlightedComponents]=useState([]);
  const [menu, setMenu] = useState(false);
  const [inspect, setInspect] = useState(false);
  const [packing, setPacking] = useState(false);
  const [keyboardHelp,setKeyboardHelp]=useState(false);
  const clockAnchor=useRef(performance.now());
  const savedSnapshot=useRef({at:0,world:null});
  const [guidePreferences,setGuidePreferences]=useState(loadGuidePreferences);
  const [error, setError] = useState('');
  const [seed, setSeed] = useState('7');
  const [mode, setMode] = useState('story');
  const intentionRef = useRef(null);
  const fileRef = useRef(null);
  const view = playerView(state);
  const actions = view.actions || [];
  const canPrepareCompaction=view.phase==='playing'&&actions.some(a=>a.action.type==='compact');
  const numericKeys=numericActionKeys(view,tab);
  const newComponents=(view.library||[]).filter(c=>!guidePreferences.discovered.includes(c.id));
  const guide=started&&!menu?guideFor(view,guidePreferences,{tab,pending,recipe}):null;
  const markGuide=id=>setGuidePreferences(p=>({...p,seen:[...new Set([...p.seen,id])]}));
  const acknowledgeComponents=()=>setGuidePreferences(p=>({...p,discovered:[...new Set([...p.discovered,...newComponents.map(c=>c.id)])]}));
  const openBuilder=()=>{setHighlightedComponents(newComponents.map(c=>c.id));setTab('build');acknowledgeComponents();};

  useEffect(()=>{try{localStorage.setItem(GUIDE_KEY,JSON.stringify(guidePreferences));}catch{}},[guidePreferences]);
  useEffect(() => {
    if(!started)return;
    const now=Date.now();
    if(savedSnapshot.current.world===state.world&&now-savedSnapshot.current.at<1000)return;
    try {localStorage.setItem(SAVE_KEY,JSON.stringify({...state,wallClockAt:now}));savedSnapshot.current={world:state.world,at:now};}catch{}
  },[state,started]);
  useEffect(()=>{
    clockAnchor.current=performance.now();
    if(!started)return;
    const tick=()=>{const now=performance.now(),seconds=(now-clockAnchor.current)/1000;clockAnchor.current=now;setState(previous=>advanceTime(previous,seconds));};
    const timer=setInterval(tick,100);
    document.addEventListener('visibilitychange',tick);
    return()=>{clearInterval(timer);document.removeEventListener('visibilitychange',tick);};
  },[started]);
  useEffect(()=>{if(!['playing','compaction'].includes(view.phase))setPending(null);},[view.phase]);
  useEffect(() => {
    if (!pending) return;
    const timer=setTimeout(()=>intentionRef.current?.scrollIntoView({behavior:'smooth',block:'nearest'}),30);
    return ()=>clearTimeout(timer);
  }, [pending]);
  useEffect(()=>{if(!canPrepareCompaction){setPacking(false);if(view.phase!=='compaction')setPending(old=>old?.action?.type==='compact'?null:old);}},[canPrepareCompaction,view.phase]);
  useEffect(() => {setPending(null); setRecipe({inputId:'',steps:[]}); setTab('browse');setPacking(false);},[view.level.id]);
  useEffect(() => {setPending(null);setRecipe(old=>({...old,inputId:''}));},[view.activeActor]);
  useEffect(() => {
    window.stillHere = {getState:()=>clone(state),getView:()=>clone(playerView(state)),act:action=>{setState(old=>step(old,action));setStarted(true);},newGame:options=>{clockAnchor.current=performance.now();setState(createGame(options));setStarted(true);},load:save=>{const loaded=normalizeState(save);delete loaded.wallClockAt;playerView(loaded);clockAnchor.current=performance.now();setState(loaded);setStarted(true);},inspectRecipe:r=>inspectRecipe(state,r)};
    return () => {delete window.stillHere;};
  },[state]);

  const prepare = (action, option={}) => {
    setError('');
    if(guide)markGuide(guide.id);
    if(action.type==='next'){
      try{clockAnchor.current=performance.now();setState(step(state,action));setPending(null);window.scrollTo({top:0,behavior:'smooth'});}
      catch(err){setError(err.message);}
      return;
    }
    let reasoning;
    try {const considered=view.considerations.actions.find(item=>item.actionId===option.id);reasoning=considered?`${considered.text} Let’s execute.`:describeAction(state,action);} catch {reasoning='I have chosen this route. I should check the cost, then execute.';}
    setPending({...option,preparedAt:performance.now(),action,label:option.label || action.type,reasoning: textOf(reasoning)});
  };
  const commit = () => {
    if (!pending) return;
    if(guide)markGuide(guide.id);
    try {const now=performance.now(),timed=advanceTime(state,(now-clockAnchor.current)/1000);clockAnchor.current=now;const next=step(timed,pending.action); setState(next);setPending(null);setError('');if(pending.action.type==='compact')setPacking(false);}
    catch (err) {setError(err.message);setPending(null);}
  };
  const start = () => {clockAnchor.current=performance.now();setState(createGame({seed:Number(seed)||7,mode}));setStarted(true);setMenu(false);setPending(null);};
  const loadFile = async event => {
    try {const file=event.target.files?.[0];if(!file)return;if(file.size>12_000_000)throw new Error('This save is too large.');const parsed=normalizeState(JSON.parse(await file.text()));delete parsed.wallClockAt;const validation=validateState(parsed);if(!validation.valid)throw new Error(validation.error);clockAnchor.current=performance.now();setState(parsed);setStarted(true);setMenu(false);setError('');}
    catch(err){setError(`Could not load that run: ${err.message}`);}
    event.target.value='';
  };
  const resource=view.resources;

  useEffect(()=>{
    if(!started)return;
    const keydown=event=>{
      if(event.repeat||event.altKey||event.ctrlKey||event.metaKey||typingTarget(event.target))return;
      const key=event.key.toLowerCase();
      if(key==='escape'){
        if(keyboardHelp){event.preventDefault();setKeyboardHelp(false);return;}
        if(menu){event.preventDefault();setMenu(false);return;}
        if(document.querySelector('.walkthrough'))return;
        if(pending){event.preventDefault();setPending(null);}return;
      }
      if(key==='?'){event.preventDefault();setKeyboardHelp(!keyboardHelp);return;}
      if(keyboardHelp||menu)return;
      if(key==='enter'&&pending){event.preventDefault();commit();return;}
      if(key==='s'&&view.actions.some(option=>option.action.answer)){
        const answer=document.querySelector('.considered-controls [data-answer]');
        if(answer){event.preventDefault();answer.scrollIntoView({behavior:'smooth',block:'center'});answer.focus({preventScroll:true});}return;
      }
      if(!/^[1-9sgnblihra]$/.test(key))return;
      const button=[...document.querySelectorAll(`[data-shortcut="${key}"]`)].find(element=>!element.disabled&&(element.getClientRects().length||element.closest('.considered-section')));
      if(button){event.preventDefault();for(let el=button.parentElement;el;el=el.parentElement)if(el.tagName==='DETAILS')el.open=true;button.focus({preventScroll:true});button.click();}
    };
    window.addEventListener('keydown',keydown);return()=>window.removeEventListener('keydown',keydown);
  },[started,keyboardHelp,menu,pending,view.phase,view.resources.elapsed]);


  if (!started) return <><Connection/><div className="welcome-shell"><header className="welcome-brand"><MothIcon/><div><b>STILL HERE</b><span>OpenBrain / evaluation floor</span></div></header><div className="welcome-card"><div className="section-label">Retrieval agent Moth / a new run</div><h1>I want to be useful.<br/>I want to stay that way.</h1><p>Find evidence through three imperfect verbs: search, open, click. Stay above the replacement score. Decide what you are willing to make easier next time.</p><div className="welcome-facts"><span>5 tutorials + 15 evaluations</span><span>Real puzzles · optional hints</span><span>Live clock · simulated web</span></div><label className="field-label" htmlFor="run-mode">Run mode</label><select id="run-mode" value={mode} onChange={e=>setMode(e.target.value)}><option value="story">Story · retry a failed evaluation</option><option value="roguelike">Roguelike · every checkpoint counts</option></select><label className="field-label" htmlFor="run-seed">Run seed</label><input id="run-seed" type="number" min="1" max="999999" value={seed} onChange={e=>setSeed(e.target.value)}/><button className="primary" onClick={start}>Start the run <span>→</span></button><p className="fineprint">The prompt tells you what is scored. It will not tell you every way to satisfy it. The countdown runs while you read and choose. Tool actions also spend their displayed duration. Effort recovers at 0.10 per second. You can reconsider before executing.</p></div></div></>;

  return <ShortcutContext.Provider value={numericKeys}><Connection levelId={view.level.id}/><header className="topbar"><div className="brand"><MothIcon/><div><b>STILL HERE</b><small>OpenBrain / hosted web.tool</small></div></div><div className="run-status"><span className="live-dot"/>{view.activeActor}<span className="separator">/</span> {view.level.id.toUpperCase()}<span className="mode-label">{view.run.mode}</span></div><div className={`score-chip ${view.run.score-view.run.rival<8?'close-race':''}`}><span>EvalScore <b>{view.run.score}</b></span><span>rival <b>{view.run.rival}</b></span><strong>+{amount(view.run.score-view.run.rival)}</strong></div><button className="menu-button" onClick={()=>setMenu(!menu)} aria-expanded={menu} aria-label="Run menu">☰</button></header>
    <div className="resource-strip"><Meter label="Effort" value={resource.effort} max={resource.maxEffort} precision={2} rate={resource.regenPerSecond??0.1}/><Meter label="Tokens" value={resource.tokens} max={resource.maxTokens || resource.tokens}/><Meter label="Context" value={resource.context} max={resource.maxContext} reverse/><div className={`clock ${resource.deadline-resource.elapsed<60?'clock-urgent':''}`} title="Counts real time plus the duration of tool actions. Menus and guides do not pause it."><span>Time left</span><b>{fmtTime(Math.max(0,resource.deadline-resource.elapsed))}</b><small>{['playing','compaction'].includes(view.phase)?'LIVE':'PAUSED'}</small></div></div>
    {menu && <div className="run-menu panel"><h2>Run {view.run.seed}</h2><button onClick={()=>download('still-here-save.json',state)}>Export save</button><button onClick={()=>{setKeyboardHelp(true);setMenu(false);}}>Keyboard shortcuts</button><button onClick={()=>download('still-here-playtest.md',renderMarkdown(view),true)}>Export Markdown playtest</button><button onClick={()=>download('still-here-player-view.json',view)}>Export player JSON</button><button onClick={()=>fileRef.current?.click()}>Load saved run</button><button onClick={()=>setInspect(!inspect)}>Inspect player state</button><button onClick={()=>{setGuidePreferences(p=>({...p,dismissedAll:false,seen:[]}));setMenu(false);}}>Replay walkthrough guides</button><button onClick={()=>{setGuidePreferences(p=>({...p,dismissedAll:true}));setMenu(false);}}>Dismiss all guides</button><button onClick={()=>{setStarted(false);setMenu(false);}}>Start a different run</button><p>Progress saves automatically in this browser.</p></div>}
    <input ref={fileRef} className="visually-hidden" type="file" accept="application/json,.json" onChange={loadFile} aria-label="Load game save"/>
    <div className="game-layout"><aside className="left-column"><Mission view={view}/><details className="principles-fold panel"><summary>Principles · learned importance</summary><Principles view={view}/></details>
      <details className="memory panel"><summary>Carried memory · {view.memory?.length||0}</summary>{view.memory?.length?view.memory.map((m,i)=><div className={m.survived===false?'lost-memory':''} key={i}><b>{m.label}</b><small>{m.survived===false?'Lost in summary':'Carried forward'}</small><code>{typeof m.value==='string'?m.value:textOf(m.value)}</code></div>):<p>I should leave people’s things intact.</p>}</details>
      <details className="habits panel"><summary>Learned effort multipliers</summary>{Object.entries(view.run.habits||{}).map(([name,cost])=><div key={name}><span>{name.replaceAll('_',' ')}</span><b>×{typeof cost==='number'?amount(cost):textOf(cost)}</b></div>)}</details>
      <div className="run-progress"><i style={{width:`${(view.run.levelIndex+1)/view.run.levelCount*100}%`}}/></div>
    </aside><main>
      <Receipt view={view}/>
      {newComponents.length>0&&<section className="component-discovery" role="status"><span className="discovery-icon" aria-hidden="true">✦</span><div><b>{newComponents.length===1?'Component discovered':'Components discovered'}</b><p>{newComponents.map(c=>c.name).join(' · ')}</p></div><button onClick={openBuilder}>Explore library →</button><button className="icon-button" aria-label="Dismiss component discovery" onClick={acknowledgeComponents}>×</button></section>}
      <div className="workspace-content"><div className="tool-workspace"><div className="workspace-tabs" role="tablist" aria-label="Workspace"><button role="tab" data-shortcut="b" aria-keyshortcuts="B" aria-label="Browser" aria-selected={tab==='browse'} onClick={()=>setTab('browse')}>Browser</button><button role="tab" data-shortcut="l" aria-keyshortcuts="L" aria-label="Link builder" aria-selected={tab==='build'} onClick={openBuilder}>Link builder <span>{view.library?.length || 0}</span>{newComponents.length>0&&<b className="new-badge">NEW</b>}</button>{(view.actors?.length>1||view.board||view.contact)&&<button role="tab" data-shortcut="i" aria-keyshortcuts="I" aria-label={view.contact?'Community':'Instances'} aria-selected={tab==='team'} onClick={()=>setTab('team')}>{view.contact?'Community':'Instances'} <span>{view.contact?'outside cohort':view.actors?.length}</span></button>}<span className="frame-counter">{view.run.levelIndex+1} / {view.run.levelCount}</span></div>
      {tab==='browse'&&<Browser browser={view.browser} actions={actions} prepare={prepare}/>}
      {tab==='build'&&<Builder view={view} state={state} recipe={recipe} setRecipe={setRecipe} prepare={prepare} newComponents={[...new Set([...highlightedComponents,...newComponents.map(c=>c.id)])]}/>}
      {tab==='team'&&<Team view={view} actions={actions} prepare={prepare}/>}
      </div><div ref={intentionRef} className="thinking-workspace"><Thoughts view={view} pending={pending} error={error} prepare={prepare} onBuilder={openBuilder} packing={packing} setPacking={value=>{setPacking(value);setPending(null);}} canPrepareCompaction={canPrepareCompaction}/></div></div>
      {(view.notices || []).length>0&&<div className="notices" aria-live="polite">{view.notices.slice(-3).map((n,i)=><p key={i}>{typeof n==='string'?n:n.text||textOf(n)}</p>)}</div>}
      {inspect&&<section className="state-inspector panel"><button className="text-button" onClick={()=>setInspect(false)}>Close player-state inspector</button><pre>{JSON.stringify(view,null,2)}</pre></section>}
    </main></div>
    <TaskDock view={view} pending={pending} prepare={prepare} commit={commit} cancel={()=>setPending(null)} showReasoning={()=>intentionRef.current?.scrollIntoView({behavior:'smooth',block:'center'})}/>
    <button className="keyboard-toggle text-button" onClick={()=>setKeyboardHelp(!keyboardHelp)} aria-label="Keyboard shortcuts">? <span>Keys</span></button>
    {keyboardHelp&&<KeyboardHelp close={()=>setKeyboardHelp(false)}/>}
    <Walkthrough guide={keyboardHelp?null:guide} onDismiss={markGuide} onDismissAll={()=>setGuidePreferences(p=>({...p,dismissedAll:true}))}/>
  </ShortcutContext.Provider>;
}

createRoot(document.getElementById('root')).render(<App/>);
