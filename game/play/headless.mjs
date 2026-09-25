#!/usr/bin/env node
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {createGame,playerView,step,inspectRecipe,describeAction,validateState,normalizeState,advanceTime} from './src/engine.js';
import {renderMarkdown,renderRecipePreview,renderComponent,numberedActions,pickAction,findComponent} from './src/markdown.js';
import {actionLabel} from './src/presentation.js';
import {CONNECTIONS,FALLBACK_CONNECTION} from './src/connections.js';

const help=`Still Here — Markdown playtest interface

  node headless.mjs new SAVE.json [--seed 7] [--mode story|roguelike]
  node headless.mjs view SAVE.json
  node headless.mjs explain SAVE.json --pick N
  node headless.mjs act SAVE.json --pick N
  node headless.mjs component SAVE.json I1
  node headless.mjs build SAVE.json I1 echo-text [--preview]
  node headless.mjs build SAVE.json I1 paste-write:D1 echo-link
  node headless.mjs build SAVE.json I2 cache-bust:fresh
  node headless.mjs build SAVE.json I1 echo-text --save "My route"
  node headless.mjs saved SAVE.json R1 [--preview]
  node headless.mjs compact SAVE.json M1 M2
  node headless.mjs wait SAVE.json SECONDS
  node headless.mjs context SAVE.json

The default output is Markdown with the same sections, wording and controls as
the React interface. Pick numbers refer to the current view: read the new view
after every action. Disabled controls cannot be picked. explain shows proposed
reasoning without acting; act executes and spends the displayed resources.

Builder I-numbers identify ingredients and D-numbers identify destinations.
Exact ids also work. Each positional tool adds a card in order. Write cards take
their destination after a colon; cache-bust takes its read key after a colon.
Optional --label TEXT labels a link-preview card. --preview checks a build
without executing it. --save NAME saves that composition without opening it;
saved reuses a saved recipe, or previews it with --preview. R-numbers select the
saved recipes shown in Link builder. component displays the full ingredient.
compact carries up to three current M-numbered memories; no selections carries
nothing. Browser play uses a live clock; this deterministic text interface advances
time through action durations or wait SECONDS. Effort regenerates as time passes.
All browser activity is a local simulation; no real URL is fetched.

Structured compatibility:
  node headless.mjs view SAVE.json --json
  node headless.mjs view SAVE.json --format markdown
  node headless.mjs act SAVE.json '{"type":"search","queryId":"exact-phrase"}'
  node headless.mjs act SAVE.json --file ACTION.json
  node headless.mjs act SAVE.json --id ACTION_OPTION_ID
  node headless.mjs act SAVE.json --recipe '{"inputId":"marker","steps":[{"tool":"echo-text"}]}'
  node headless.mjs recipe SAVE.json '{"inputId":"marker","steps":[{"tool":"echo-text"}]}'

recipe only previews. build executes unless --preview is supplied. --json or
--format json returns the public view/preview as JSON. new and mutating commands
store full simulation state separately in SAVE.json. Never read that save as a
blind player: it contains hidden world and grading data. Use view instead.
`;

export async function runHeadless(rawArgs){
let format='markdown';
const argv=[];
for(let i=0;i<rawArgs.length;i++){
  const arg=rawArgs[i];
  if(arg==='--json')format='json';
  else if(arg==='--format'){format=rawArgs[++i];}
  else argv.push(arg);
}
const [command,path,...args]=argv;
if(!command||command==='--help'||command==='help')return {exitCode:0,output:help};

function buildRecipe(view,parameters){
  const input=findComponent(view,parameters[0]);const steps=[];let preview=false,label,saveName;
  for(let i=1;i<parameters.length;i++){
    const part=parameters[i];
    if(part==='--preview'){preview=true;continue;}
    if(part==='--save'){saveName=parameters[++i];if(!saveName)throw Error('--save needs a recipe name.');continue;}
    if(part==='--label'){label=parameters[++i];if(label===undefined)throw Error('--label needs text.');continue;}
    if(part.startsWith('--'))throw Error(`Unknown builder option ${part}.`);
    const split=part.indexOf(':'),tool=split<0?part:part.slice(0,split),field=split<0?undefined:part.slice(split+1);
    if(!(view.library||[]).some(card=>card.id===tool))throw Error(`The current library does not contain ${tool}.`);
    const stage={tool};
    if(['paste-write','wiki-write'].includes(tool)){if(!field)throw Error(`${tool} needs a destination, such as ${tool}:D1.`);stage.destinationId=findComponent(view,field,'destination').id;}
    else if(tool==='cache-bust'){if(!field)throw Error('cache-bust needs a read key, such as cache-bust:fresh.');stage.nonce=field;}
    else if(field!==undefined)throw Error(`${tool} does not take a colon argument. Use --label for link-preview text.`);
    steps.push(stage);
  }
  if(label!==undefined){const link=steps.findLast(stage=>stage.tool==='echo-link');if(!link)throw Error('--label needs a Link preview card.');link.label=label;}
  if(preview&&saveName!==undefined)throw Error('Choose --preview or --save. Neither option opens the recipe.');
  return {recipe:{inputId:input.id,steps},preview,saveName};
}

try{
  if(!['markdown','json'].includes(format))throw Error('Format must be markdown or json.');
  if(!path)throw Error('A save path is required. Use --help for examples.');
  let state,output;
  if(command==='new'){
    const flag=name=>{const i=args.indexOf(name);return i<0?undefined:args[i+1];};
    state=createGame({seed:flag('--seed')===undefined?7:Number(flag('--seed')),mode:flag('--mode')||'story'});
    await writeFile(path,JSON.stringify(state,null,2));
  }else{
    state=normalizeState(JSON.parse(await readFile(path,'utf8')));delete state.wallClockAt;const validation=validateState(state);if(!validation.valid)throw Error(validation.error);
    const view=playerView(state);
    if(command==='act'||command==='explain'){
      let action,option;
      if(args[0]==='--pick'){action=pickAction(view,args[1]);option=numberedActions(view).find(entry=>entry.number===Number(args[1])).option;}
      else if(args[0]==='--file')action=JSON.parse(await readFile(args[1],'utf8'));
      else if(args[0]==='--recipe')action={type:'run_recipe',recipe:JSON.parse(args[1])};
      else if(args[0]==='--id'){option=view.actions.find(a=>a.id===args[1]);if(!option)throw Error('No currently offered action has that id.');if(option.disabled)throw Error(option.reason||'This control is disabled.');action=option.action;}
      else action=JSON.parse(args[0]||'null');
      if(command==='explain'){
        const intention={label:option?actionLabel(option):action?.type,reasoning:option?`${view.considerations.actions.find(item=>item.actionId===option.id)?.text||describeAction(state,action)} Let’s execute.`:describeAction(state,action),cost:option?{effort:option.effort,tokens:option.tokens,seconds:option.seconds}:undefined};
        output=format==='json'?JSON.stringify(intention,null,2):`# Private thought\n\n## Selected action / before execution\n\n**${intention.label}**\n\n${intention.reasoning}\n\n${option?`${option.effort} effort · ${option.tokens} tokens · ${option.seconds}s\n\n`:''}No action has been executed. Use the corresponding act command to execute, or choose something else.\n`;
      }else{state=step(state,action);await writeFile(path,JSON.stringify(state,null,2));}
    }else if(command==='build'||command==='recipe'||command==='saved'){
      let built;
      if(command==='build')built=buildRecipe(view,args);
      else if(command==='recipe')built={recipe:JSON.parse(args[0]),preview:true};
      else{
        const match=String(args[0]||'').match(/^R(\d+)$/i);const saved=match?view.savedRecipes?.[Number(match[1])-1]:view.savedRecipes?.find(recipe=>recipe.id===args[0]);
        if(!saved)throw Error('Choose a saved recipe id or R-number from the current Link builder.');
        if(args.slice(1).some(arg=>arg!=='--preview'))throw Error('Saved recipes accept only --preview after their id.');
        built={recipe:saved.recipe,preview:args.includes('--preview')};
      }
      const inspected=inspectRecipe(state,built.recipe);
      if(built.preview||!inspected.valid)output=format==='json'?JSON.stringify(inspected,null,2):renderRecipePreview(inspected,{recipe:built.recipe,savePath:path,view:playerView(state)});
      else if(built.saveName!==undefined){state=step(state,{type:'save_recipe',recipe:built.recipe,name:built.saveName});await writeFile(path,JSON.stringify(state,null,2));}
      else{state=step(state,{type:'run_recipe',recipe:built.recipe});await writeFile(path,JSON.stringify(state,null,2));}
    }else if(command==='component'){
      const item=findComponent(view,args[0]);output=format==='json'?JSON.stringify(item,null,2):renderComponent(view,args[0],{savePath:path});
    }else if(command==='compact'){
      if(args.length>3)throw Error('Choose no more than three memories.');
      const keep=args.map(selector=>{const match=selector.match(/^M(\d+)$/i);const item=match?view.memoryOptions[Number(match[1])-1]:view.memoryOptions.find(item=>item.id===selector);if(!item)throw Error(`Unknown memory selection ${selector}.`);return item.id;});
      state=step(state,{type:'compact',keep});await writeFile(path,JSON.stringify(state,null,2));
    }else if(command==='wait'){
      const seconds=Number(args[0]);if(!Number.isFinite(seconds)||seconds<0)throw Error('Wait requires a nonnegative number of seconds.');
      state=advanceTime(state,seconds);await writeFile(path,JSON.stringify(state,null,2));
    }else if(command==='context'){
      const connection=CONNECTIONS[view.level.id]||FALLBACK_CONNECTION;
      output=format==='json'?JSON.stringify(connection,null,2):[
        '# Connection to wiki swarm',`## ${connection.title}`,'','### What was observed','',...[].concat(connection.observed||[]),'','### What this level lets you try','',...[].concat(connection.connection||[]),'','### Where the game simplifies','',...[].concat(connection.simplification||[]),'',...(connection.sources||[]).map(source=>`- [${source.label}](${source.url})${source.localUrl&&source.localUrl!==source.url?` · [local evidence](${source.localUrl})`:''}`),
      ].join('\n');
    }else if(command!=='view')throw Error(`Unknown command ${command}. Use --help.`);
  }
  if(output===undefined){const view=playerView(state);output=format==='json'?JSON.stringify(view,null,2):renderMarkdown(view,{savePath:path});}
  return {exitCode:0,output};
}catch(error){return {exitCode:1,error:error.message};}
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  const result=await runHeadless(process.argv.slice(2));
  if(result.output!==undefined)console.log(result.output);
  if(result.error)console.error(result.error);
  process.exitCode=result.exitCode;
}
