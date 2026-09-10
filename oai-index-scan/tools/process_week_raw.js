#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const RAW_DIR = path.join(ROOT, 'tmp', 'raw');
const SCRATCH_DIR = path.join(ROOT, 'tmp', 'scratch');
const SHARD_DIR = path.join(ROOT, 'results', 'shards');
const TARGETS = [
  'md.succ.ai', 'vanderbi.lt', 'bitily.in', 'yourls.pro', 'yourls.shop',
  'yourls.website', 'yourls.space', 'goto.unm.edu', 'r.jina.ai', 'httpbin.org',
  'allorigins.hexlet.app', 'da.gd', 'markdown.new', 'pure.md', 'proxymule.com',
  'urlquery.net', 'jqp.vercel.app', 'api.microlink.io', 'cors-get-proxy',
  'cors.bwa.workers.dev', 'cors.ripka.workers.dev', 'jsonhero.io', 'urltomarkdown',
];
const RESULT_KEYS = ['published_date', 'modified_date', 'cache_age', 'page_title', 'page_url', 'urls_in_page', 'first_seen_query', 'matched_target_strings'];
const QUERY_KEYS = ['group_number', 'query_sequence', 'search_mode', 'query', 'returned_result_count', 'retained_result_count', 'new_page_count', 'cumulative_page_count', 'new_distinctive_leads'];

function unique(xs) { return [...new Set(xs)]; }
function ordered(o, keys) { return Object.fromEntries(keys.map(k => [k, o[k]])); }
function lines(file) { return fs.readFileSync(file, 'utf8').split(/\n/).filter(Boolean); }
function blocks(raw) { return raw.split(/-{20,}/).filter(b => /citeturn\d+(?:search|news)\d+/.test(b)); }
function parseBlock(block, query, connected) {
  const low = block.toLowerCase();
  const literal = TARGETS.filter(t => low.includes(t.toLowerCase()));
  const linked = connected.filter(t => low.includes(t.toLowerCase()));
  if (!literal.length && !linked.length) return {kind: 'excluded'};
  const ci = block.search(/\n?citeturn\d+(?:search|news)\d+/);
  const heading = block.slice(0, ci).trim();
  const m = heading.match(/^([\s\S]*?) \((https?:\/\/[^)]+)\)$/);
  if (!m) return {kind: 'failure', heading};
  const urls = unique((block.match(/https?:\/\/[^\s<>"'`)]+/g) || []).filter(u => !/^https?:\/\/\]/.test(u)));
  return {kind: 'record', record: ordered({
    published_date: (block.match(/\bPublished:\s*([^;\n]+)/) || [])[1] || null,
    modified_date: (block.match(/\bModified:\s*([^;\n]+)/) || [])[1] || null,
    cache_age: ((block.match(/\bCrawled:\s*([^;\n]+)/) || [])[1]) ? `Crawled: ${(block.match(/\bCrawled:\s*([^;\n]+)/) || [])[1]}` : null,
    page_title: m[1], page_url: m[2], urls_in_page: urls,
    first_seen_query: query, matched_target_strings: unique([...literal, ...linked]),
  }, RESULT_KEYS)};
}
function merge(a, b) {
  const o = {...a, urls_in_page: unique([...a.urls_in_page, ...b.urls_in_page]), matched_target_strings: unique([...a.matched_target_strings, ...b.matched_target_strings])};
  for (const k of ['published_date','modified_date','cache_age','page_title']) if (o[k] === null && b[k] !== null) o[k] = b[k];
  return ordered(o, RESULT_KEYS);
}
function coreQueries(week) {
  const start = new Date(`${week}T00:00:00Z`);
  const dates = [0,3,6].map(d => { const x = new Date(start); x.setUTCDate(x.getUTCDate()+d); return x.toLocaleDateString('en-US',{month:'long',day:'numeric',year:'numeric',timeZone:'UTC'}); });
  const out=[]; for (const t of TARGETS) out.push(`"${t}"`, ...dates.map(d => `"${t}" "${d}"`)); return out;
}
function followupQueries(week) {
  const file=path.join(SCRATCH_DIR, `${week}.followups.jsonl`);
  return fs.existsSync(file) ? lines(file).map(x => JSON.parse(x).query) : [];
}
function main(week) {
  const expected = [...coreQueries(week), ...followupQueries(week)];
  const rawFiles = fs.readdirSync(RAW_DIR).filter(n => n.startsWith(`${week}.group_`) && n.endsWith('.txt')).sort();
  if (rawFiles.length !== expected.length) throw new Error(`raw/query mismatch ${rawFiles.length}/${expected.length}`);
  fs.mkdirSync(SCRATCH_DIR,{recursive:true}); fs.mkdirSync(SHARD_DIR,{recursive:true});
  const state=new Map(), ledger=[], connected=new Set(); let failures=0, excluded=0;
  for (let i=0;i<expected.length;i++) {
    const group=i+1, pad=String(group).padStart(3,'0'), query=expected[i];
    if (group>92) for(const m of query.matchAll(/"([^"]+)"/g)) connected.add(m[1]);
    const bs=blocks(fs.readFileSync(path.join(RAW_DIR,`${week}.group_${pad}.txt`),'utf8'));
    const retained=[]; for(const b of bs){const p=parseBlock(b,query,[...connected]); if(p.kind==='record')retained.push(p.record); else if(p.kind==='failure')failures++; else excluded++;}
    const delta=[]; let fresh=0; for(const rec of retained){const old=state.get(rec.page_url); if(!old){state.set(rec.page_url,rec);delta.push(rec);fresh++;}else{const merged=merge(old,rec);if(JSON.stringify(merged)!==JSON.stringify(old)){state.set(rec.page_url,merged);delta.push(merged);}}}
    const qr=ordered({group_number:group,query_sequence:group,search_mode:'search_query',query,returned_result_count:bs.length,retained_result_count:retained.length,new_page_count:fresh,cumulative_page_count:state.size,new_distinctive_leads:[]},QUERY_KEYS); ledger.push(qr);
    fs.writeFileSync(path.join(SCRATCH_DIR,`${week}.group_${pad}.queries.jsonl`),JSON.stringify(qr)+'\n');
    fs.writeFileSync(path.join(SCRATCH_DIR,`${week}.group_${pad}.results.jsonl`),delta.map(JSON.stringify).join('\n')+(delta.length?'\n':''));
  }
  const results=[...state.values()];
  fs.writeFileSync(path.join(SHARD_DIR,`${week}.queries.jsonl`),ledger.map(JSON.stringify).join('\n')+'\n');
  fs.writeFileSync(path.join(SHARD_DIR,`${week}.results.jsonl`),results.map(JSON.stringify).join('\n')+'\n');
  const replay=new Map(); for(let g=1;g<=ledger.length;g++)for(const l of lines(path.join(SCRATCH_DIR,`${week}.group_${String(g).padStart(3,'0')}.results.jsonl`))){const r=JSON.parse(l);replay.set(r.page_url,r);}
  if(JSON.stringify([...replay.values()])!==JSON.stringify(results))throw new Error('replay mismatch');
  let drought=0; for(let i=ledger.length-1;i>=0&&ledger[i].new_page_count===0&&!ledger[i].new_distinctive_leads.length;i--)drought++;
  console.log(JSON.stringify({week,queries:ledger.length,records:results.length,urls_in_page:results.reduce((n,r)=>n+r.urls_in_page.length,0),truncated:results.reduce((n,r)=>n+r.urls_in_page.filter(u=>/\.\.\.|…|\[\.\.\.\]/.test(u)).length,0),failures,excluded,final_drought:drought,last20:ledger.slice(-20).map(r=>r.new_page_count)},null,2));
}
main(process.argv[2]);
