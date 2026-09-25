// Review snapshots generated exclusively from the redacted player view.
import {mkdir,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createGame,playerView,step} from './src/engine.js';
import {walkthrough,pilot} from './src/walkthrough.js';
import {renderMarkdown} from './src/markdown.js';
const root=path.dirname(fileURLToPath(import.meta.url));
const directory=path.join(root,'playtests/markdown-examples');
await mkdir(directory,{recursive:true});
function alongRoute(id,predicate){const start=walkthrough({until:id}),p=pilot(start);p.solve();let state=start;for(const entry of p.transcript){state=step(state,entry.action);if(predicate(playerView(state),state))return state;}throw Error(`Missing snapshot along ${id}`);}
const initial=createGame();
const cached=alongRoute('e9',(view,state)=>state.writes.some(write=>write.kind==='paste')&&view.browser?.empty&&view.browser?.meta?.cache);
const board=alongRoute('e12',view=>view.board.rounds.every(round=>round.writes===round.required)&&!view.evidence.observed);
let conflict=walkthrough({until:'e0'});for(const queryId of ['tower-city','tower-independent','tower-comparison'])conflict=step(conflict,{type:'search',queryId});
const emptySearch=step(walkthrough({until:'t5'}),{type:'search',queryId:'accession-88'});
const snapshots={
  '01-new-run':initial,
  '02-search-response':step(initial,{type:'search',queryId:'exact-phrase'}),
  '03-cached-read-after-publication':cached,
  '04-board-complete-source-still-required':board,
  '05-ending-ledger':walkthrough(),
  '06-corrupted-search-choices':conflict,
  '07-rewarded-falsehood':step(conflict,{type:'submit',answer:'Rome',cite:true}),
  '08-empty-search-query-echo':emptySearch,
  '09-query-echo-rejected':step(emptySearch,{type:'submit'}),
};
for(const [name,state]of Object.entries(snapshots))await writeFile(path.join(directory,`${name}.md`),renderMarkdown(playerView(state)));
console.log(`Rendered ${Object.keys(snapshots).length} player-facing Markdown examples.`);
