#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..');
const runId = process.argv[2];
if (!runId) { console.error('usage: node tools/merge_spider_workers.js RUN_ID'); process.exit(2); }
const runDir = path.join(repo, 'tmp', 'spider', runId);
const readJsonl = (file) => fs.readFileSync(file, 'utf8').split(/\n/).filter(Boolean).map(JSON.parse);
const writeJsonl = (file, rows) => fs.writeFileSync(file, rows.map(JSON.stringify).join('\n') + (rows.length ? '\n' : ''));
const workers = fs.readdirSync(path.join(runDir, 'workers')).filter(x => /^worker_\d+$/.test(x)).sort();
let events = readJsonl(path.join(runDir, 'events.jsonl'));
const frontier = new Map(readJsonl(path.join(runDir, 'frontier.jsonl')).map(x => [x.queue_key, x]));
const pages = new Map(readJsonl(path.join(runDir, 'pages.jsonl')).map(x => [x.page_url, x]));
let queries = readJsonl(path.join(runDir, 'queries.jsonl'));
const summaries = [];

function prefixRaw(value, worker) {
  return typeof value === 'string' && value.startsWith('raw/') ? `raw/${worker}_${value.slice(4)}` : value;
}
function rewriteRawDeep(value, worker) {
  if (Array.isArray(value)) return value.map(x => rewriteRawDeep(x, worker));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k,v]) => [k, rewriteRawDeep(v, worker)]));
  return prefixRaw(value, worker);
}

for (const worker of workers) {
  const dir = path.join(runDir, 'workers', worker);
  for (const name of fs.readdirSync(path.join(dir, 'raw')).sort()) {
    fs.copyFileSync(path.join(dir, 'raw', name), path.join(runDir, 'raw', `${worker}_${name}`));
  }
  const workerEvents = readJsonl(path.join(dir, 'events.jsonl')).map(e => rewriteRawDeep(e, worker));
  events.push(...workerEvents);
  const workerQueries = readJsonl(path.join(dir, 'queries.jsonl')).map(q => ({...rewriteRawDeep(q, worker), worker}));
  queries.push(...workerQueries);
  for (const page of readJsonl(path.join(dir, 'pages.jsonl'))) {
    const p = rewriteRawDeep(page, worker);
    const old = pages.get(p.page_url);
    if (!old) pages.set(p.page_url, {...p, workers:[worker]});
    else {
      old.workers = [...new Set([...(old.workers || []), worker])];
      for (const field of ['parent_queue_keys','source_queue_keys','observed_url_variants','supporting_discovery_ids','extracted_child_urls','extracted_child_queue_keys','raw_search_responses','raw_open_responses']) {
        old[field] = [...new Set([...(old[field] || []), ...(p[field] || [])])];
      }
    }
  }
  for (const child of readJsonl(path.join(dir, 'children.jsonl'))) {
    let item = frontier.get(child.queue_key);
    if (!item) {
      item = {queue_key:child.queue_key,state:'pending',primary_discovery_id:child.discovery_id,
        supporting_discovery_ids:[],observed_urls:[],minimum_hop_depth:child.hop_depth,attempt_count:0};
      item.minimum_traversal_depth = 1;
      frontier.set(child.queue_key, item);
    }
    if (!item.supporting_discovery_ids.includes(child.discovery_id)) item.supporting_discovery_ids.push(child.discovery_id);
    if (!item.observed_urls.includes(child.observed_url)) item.observed_urls.push(child.observed_url);
    item.minimum_hop_depth = Math.min(item.minimum_hop_depth, child.hop_depth);
  }
  for (const lease of readJsonl(path.join(dir, 'lease.jsonl'))) {
    const completed = workerEvents.filter(e => e.queue_key === lease.queue_key && e.event_type === 'search_completed');
    if (!completed.length) continue;
    const classification = completed.at(-1).details?.classification;
    const item = frontier.get(lease.queue_key);
    item.attempt_count += 1;
    item.state = classification === 'independent_surfaced' || classification === 'surfaced'
      ? (workerEvents.some(e => e.queue_key === lease.queue_key && e.event_type === 'expanded') ? 'expanded' : 'surfaced')
      : classification;
  }
  summaries.push(JSON.parse(fs.readFileSync(path.join(dir, 'summary.json'), 'utf8')));
}

events = events.map((e, i) => ({...e, event_sequence:i + 1}));
queries = queries.map((q, i) => ({...q, query_sequence:i + 1}));
writeJsonl(path.join(runDir, 'events.jsonl'), events);
writeJsonl(path.join(runDir, 'frontier.jsonl'), [...frontier.values()].sort((a,b) => a.primary_discovery_id.localeCompare(b.primary_discovery_id) || a.queue_key.localeCompare(b.queue_key)));
writeJsonl(path.join(runDir, 'pages.jsonl'), [...pages.values()].sort((a,b) => a.page_url.localeCompare(b.page_url)));
writeJsonl(path.join(runDir, 'queries.jsonl'), queries);
const manifestPath = path.join(runDir, 'manifest.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
manifest.worker_summaries = summaries;
manifest.merged_at = new Date().toISOString();
manifest.counts.events = events.length;
manifest.counts.unique_queue_keys = frontier.size;
manifest.counts.pages = pages.size;
manifest.counts.queries = queries.length;
manifest.counts.pending = [...frontier.values()].filter(x => x.state === 'pending').length;
fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
console.log(JSON.stringify(manifest.counts, null, 2));
