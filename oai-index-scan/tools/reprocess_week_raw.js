#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const WEEK = process.argv[2];
if (!/^\d{4}-\d{2}-\d{2}$/.test(WEEK || '')) throw new Error('usage: reprocess_week_raw.js YYYY-MM-DD');

const TARGETS = [
  'md.succ.ai', 'vanderbi.lt', 'bitily.in', 'yourls.pro', 'yourls.shop',
  'yourls.website', 'yourls.space', 'goto.unm.edu', 'r.jina.ai', 'httpbin.org',
  'allorigins.hexlet.app', 'da.gd', 'markdown.new', 'pure.md', 'proxymule.com',
  'urlquery.net', 'jqp.vercel.app', 'api.microlink.io', 'cors-get-proxy',
  'cors.bwa.workers.dev', 'cors.ripka.workers.dev', 'jsonhero.io', 'urltomarkdown',
];
const RESULT_KEYS = ['published_date','modified_date','cache_age','page_title','page_url','urls_in_page','first_seen_query','matched_target_strings'];
const QUERY_KEYS = ['group_number','query_sequence','search_mode','query','returned_result_count','retained_result_count','new_page_count','cumulative_page_count','new_distinctive_leads'];
const RAW = path.join(ROOT, 'tmp', 'raw');
const SCRATCH = path.join(ROOT, 'tmp', 'scratch');
const SHARDS = path.join(ROOT, 'results', 'shards');

const fmt = (date) => date.toLocaleDateString('en-US', {month:'long',day:'numeric',year:'numeric',timeZone:'UTC'});
const start = new Date(`${WEEK}T00:00:00Z`);
const anchors = [0,3,6].map((offset) => { const d = new Date(start); d.setUTCDate(d.getUTCDate()+offset); return fmt(d); });
const queries = [];
for (const target of TARGETS) {
  queries.push(`"${target}"`);
  for (const anchor of anchors) queries.push(`"${target}" "${anchor}"`);
}
const followupFile = path.join(SCRATCH, `${WEEK}.followups.txt`);
if (fs.existsSync(followupFile)) queries.push(...fs.readFileSync(followupFile,'utf8').split(/\n/).filter(Boolean));
const leadsFile = path.join(SCRATCH, `${WEEK}.leads.json`);
const leadsByGroup = fs.existsSync(leadsFile) ? JSON.parse(fs.readFileSync(leadsFile,'utf8')) : {};

const uniq = (xs) => [...new Set(xs)];
const ordered = (o, keys) => Object.fromEntries(keys.map((k) => [k,o[k]]));
const blocks = (raw) => raw.split(/-{20,}/).filter((b) => /citeturn\d+(?:search|news)\d+/.test(b));
function parse(block, query, connected) {
  const lower = block.toLowerCase();
  const matches = TARGETS.filter((t) => lower.includes(t.toLowerCase()));
  const leads = connected.filter((t) => lower.includes(t.toLowerCase()));
  if (!matches.length && !leads.length) return null;
  const ci = block.search(/\n?citeturn\d+(?:search|news)\d+/);
  const heading = block.slice(0,ci).trim();
  const hm = heading.match(/^([\s\S]*?) \((https?:\/\/[^)]+)\)$/);
  if (!hm) return {failure:true};
  const urls = uniq((block.match(/https?:\/\/[^\s<>"'`)]+/g) || []).filter(u => !/^https?:\/\/\]/.test(u)));
  const pub = (block.match(/\bPublished:\s*([^;\n]+)/)||[])[1] || null;
  const mod = (block.match(/\bModified:\s*([^;\n]+)/)||[])[1] || null;
  const crawl = (block.match(/\bCrawled:\s*([^;\n]+)/)||[])[1] || null;
  return ordered({published_date:pub,modified_date:mod,cache_age:crawl?`Crawled: ${crawl}`:null,page_title:hm[1],page_url:hm[2],urls_in_page:urls,first_seen_query:query,matched_target_strings:uniq([...matches,...leads])},RESULT_KEYS);
}
function merge(a,b) {
  const m={...a,urls_in_page:uniq([...a.urls_in_page,...b.urls_in_page]),matched_target_strings:uniq([...a.matched_target_strings,...b.matched_target_strings])};
  for(const k of ['published_date','modified_date','cache_age','page_title']) if(m[k]===null&&b[k]!==null)m[k]=b[k];
  return ordered(m,RESULT_KEYS);
}

fs.mkdirSync(SCRATCH,{recursive:true}); fs.mkdirSync(SHARDS,{recursive:true});
const state=new Map(), ledger=[]; let failures=0, excluded=0; const connected=new Set();
for(let i=0;i<queries.length;i++) {
  const group=i+1, pad=String(group).padStart(3,'0'), query=queries[i];
  if(group>92) for(const match of query.matchAll(/"([^"]+)"/g)) if(!/^(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}$/.test(match[1])) connected.add(match[1]);
  const rawPath=path.join(RAW,`${WEEK}.group_${pad}.txt`);
  if(!fs.existsSync(rawPath)) throw new Error(`missing ${rawPath}`);
  const bs=blocks(fs.readFileSync(rawPath,'utf8')), retained=[];
  for(const b of bs){const r=parse(b,query,[...connected]);if(r?.failure)failures++;else if(r)retained.push(r);else excluded++;}
  const delta=[];let fresh=0;
  for(const r of retained){const old=state.get(r.page_url);if(!old){state.set(r.page_url,r);delta.push(r);fresh++;}else{const m=merge(old,r);if(JSON.stringify(m)!==JSON.stringify(old)){state.set(r.page_url,m);delta.push(m);}}}
  const qr=ordered({group_number:group,query_sequence:group,search_mode:null,query,returned_result_count:bs.length,retained_result_count:retained.length,new_page_count:fresh,cumulative_page_count:state.size,new_distinctive_leads:leadsByGroup[String(group)]||[]},QUERY_KEYS);
  ledger.push(qr);
  for(const lead of qr.new_distinctive_leads) connected.add(lead);
  fs.writeFileSync(path.join(SCRATCH,`${WEEK}.group_${pad}.queries.jsonl`),JSON.stringify(qr)+'\n');
  fs.writeFileSync(path.join(SCRATCH,`${WEEK}.group_${pad}.results.jsonl`),delta.map(JSON.stringify).join('\n')+(delta.length?'\n':''));
}
const results=[...state.values()];
fs.writeFileSync(path.join(SHARDS,`${WEEK}.queries.jsonl`),ledger.map(JSON.stringify).join('\n')+'\n');
fs.writeFileSync(path.join(SHARDS,`${WEEK}.results.jsonl`),results.map(JSON.stringify).join('\n')+'\n');
const replay=new Map();for(let i=1;i<=queries.length;i++){const f=path.join(SCRATCH,`${WEEK}.group_${String(i).padStart(3,'0')}.results.jsonl`);for(const l of fs.readFileSync(f,'utf8').split(/\n/).filter(Boolean)){const r=JSON.parse(l);replay.set(r.page_url,r);}}
if(JSON.stringify([...replay.values()])!==JSON.stringify(results))throw new Error('replay mismatch');
if(ledger.slice(0,92).map((q)=>q.query).join('\n')!==queries.slice(0,92).join('\n'))throw new Error('core mismatch');
console.log(JSON.stringify({week:WEEK,groups:queries.length,records:results.length,urls_in_page:results.reduce((n,r)=>n+r.urls_in_page.length,0),truncated:results.reduce((n,r)=>n+r.urls_in_page.filter((u)=>/\.\.\.|…|\[\.\.\.\]/.test(u)).length,0),parser_failures:failures,excluded_blocks:excluded,final_drought:(()=>{let n=0;for(let i=ledger.length-1;i>=0&&ledger[i].new_page_count===0&&!ledger[i].new_distinctive_leads.length;i--)n++;return n;})()},null,2));
