import {mkdirSync,writeFileSync} from 'node:fs';
import {auditActions} from './src/action-audit.js';
const directory=new URL('./playtests/action-audit/',import.meta.url);mkdirSync(directory,{recursive:true});
const pages=new Map();
const escape=value=>String(value).replaceAll('|','\\|').replaceAll('\n',' ');
const result=auditActions({onCheckpoint:({label,view})=>{
 const out=pages.get(view.level.id)||[`# ${view.level.id.toUpperCase()} · ${view.level.name}`,'','Every row pairs a visible action with the prospective thought that considers it. Disabled actions retain an explanation of what prevents them. Builder and memory choices follow each action table.'];
 out.push('',`## ${label} · ${view.activeActor} · ${view.phase}`,'',`Browser: ${view.browser?.title||'Nothing retrieved'}`,'','| Action | Available | Moth’s consideration |','| --- | --- | --- |');
 for(const item of view.considerations.actions)out.push(`| ${escape(item.label)} | ${item.available?'Yes':'No'} | ${escape(item.text)} |`);
 if(view.considerations.affordances.length){out.push('','### Builder and memory choices','');for(const item of view.considerations.affordances)out.push(`- ${item.text}`);}
 pages.set(view.level.id,out);
},onProgress:progress=>console.log(`Audited ${progress.step} route steps, ${progress.states} states, ${progress.departures} departures.`)});
for(const [id,out]of pages)writeFileSync(new URL(`${id}.md`,directory),out.join('\n')+'\n');
writeFileSync(new URL('coverage.json',directory),JSON.stringify(result,null,2)+'\n');
const index=['# Available-action audit','','[Narrative findings and changes](REVIEW.md)','','The authored route is replayed from the initial state. Every offered action is checked against an explicit current thought. Every enabled action at each distinct route state is also tried as a one-action departure. Effort exhaustion, deadline expiry, and typed builder pairings are checked separately.','',`Audited **${result.states} states**, **${result.offered} action offerings**, **${result.departures} departures**, and **${result.recipes} builder pairings**. ${result.issues.length} issues.`, '', 'This is bounded state coverage, not an exhaustive search of arbitrary URL strings, read keys, timing values, or all multi-action combinations. The per-task records expose every route step for narrative review.','','| Task | Route checkpoints | Other states | Action offerings |','| --- | ---: | ---: | ---: |'];
for(const [id,level]of Object.entries(result.levels))index.push(`| [${id.toUpperCase()}](${id}.md) | ${level.checkpoints} | ${level.branches} | ${level.actions} |`);
if(result.issues.length)index.push('','## Issues','',...result.issues.map(issue=>`- ${issue}`));
writeFileSync(new URL('README.md',directory),index.join('\n')+'\n');
console.log(JSON.stringify({...result,levels:undefined},null,2));if(result.issues.length)process.exitCode=1;
