#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..');
const runId = process.argv[2];
const leaseSize = Number(process.argv[3] || 10);
if (!runId || !Number.isInteger(leaseSize) || leaseSize < 1) {
  console.error('usage: node tools/build_spider_seed.js RUN_ID [LEASE_SIZE_PER_WORKER]');
  process.exit(2);
}

const shardDir = path.join(repo, 'results', 'shards');
const shardNames = fs.readdirSync(shardDir)
  .filter((name) => /^2026-05-\d\d\.results\.jsonl$/.test(name))
  .sort();
const runDir = path.join(repo, 'tmp', 'spider', runId);
if (fs.existsSync(runDir)) throw new Error(`run directory already exists: ${runDir}`);
fs.mkdirSync(path.join(runDir, 'raw'), { recursive: true });
fs.mkdirSync(path.join(runDir, 'workers', 'worker_1'), { recursive: true });
fs.mkdirSync(path.join(runDir, 'workers', 'worker_2'), { recursive: true });

function queueKey(value) {
  if (typeof value !== 'string' || /\[\.\.\.\]|…/.test(value)) return null;
  let parsed;
  try { parsed = new URL(value); } catch { return null; }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null;
  parsed.hash = '';
  return parsed.toString();
}

const now = new Date().toISOString();
const events = [];
const frontier = new Map();
const rootIds = new Map();
const pageIds = new Map();
let eventSeq = 0;
let discoverySeq = 0;
const nextId = () => `d${String(++discoverySeq).padStart(8, '0')}`;
const emit = (event) => events.push({
  event_sequence: ++eventSeq, event_time: now, run_id: runId, ...event
});

for (const shardName of shardNames) {
  const sourceFile = `./results/shards/${shardName}`;
  const lines = fs.readFileSync(path.join(shardDir, shardName), 'utf8').split(/\n/).filter(Boolean);
  lines.forEach((line, index) => {
    const row = JSON.parse(line);
    const rootKind = row.first_seen_query ? 'search_term' : 'url';
    const rootValue = row.first_seen_query || row.page_url;
    const rootMapKey = `${rootKind}\u0000${rootValue}`;
    let rootId = rootIds.get(rootMapKey);
    if (!rootId) {
      rootId = nextId(); rootIds.set(rootMapKey, rootId);
      emit({event_type:'ancestry_root', discovery_id:rootId, parent_discovery_id:null,
        root_kind:rootKind, root_value:rootValue, hop_depth:0, queue_key:null,
        observed_url:rootKind === 'url' ? rootValue : null, source_page_url:null,
        source_file:sourceFile, search_sequence:null, open_sequence:null, details:{queueable:false}});
    }
    const pageMapKey = `${rootId}\u0000${row.page_url}`;
    let pageId = pageIds.get(pageMapKey);
    if (!pageId) {
      pageId = nextId(); pageIds.set(pageMapKey, pageId);
      emit({event_type:'source_page_observed', discovery_id:pageId, parent_discovery_id:rootId,
        root_kind:rootKind, root_value:rootValue, hop_depth:1, queue_key:null,
        observed_url:row.page_url, source_page_url:row.page_url, source_file:sourceFile,
        search_sequence:null, open_sequence:null, details:{queueable:false, source_line:index + 1}});
    }
    for (const observed of (row.urls_in_page || [])) {
      const key = queueKey(observed);
      const id = nextId();
      if (!key) {
        emit({event_type:'marked_ineligible', discovery_id:id, parent_discovery_id:pageId,
          root_kind:rootKind, root_value:rootValue, hop_depth:2, queue_key:null,
          observed_url:observed, source_page_url:row.page_url, source_file:sourceFile,
          search_sequence:null, open_sequence:null, details:{reason:'not_complete_absolute_http_url', source_line:index + 1}});
        continue;
      }
      emit({event_type:'discovered', discovery_id:id, parent_discovery_id:pageId,
        root_kind:rootKind, root_value:rootValue, hop_depth:2, queue_key:key,
        observed_url:observed, source_page_url:row.page_url, source_file:sourceFile,
        search_sequence:null, open_sequence:null, details:{source_line:index + 1, first_seen_query:row.first_seen_query ?? null}});
      let item = frontier.get(key);
      if (!item) {
        item = {queue_key:key, state:'pending', primary_discovery_id:id,
          supporting_discovery_ids:[], observed_urls:[], minimum_hop_depth:2,
          minimum_traversal_depth:0,
          attempt_count:0};
        frontier.set(key, item);
      }
      if (!item.supporting_discovery_ids.includes(id)) item.supporting_discovery_ids.push(id);
      if (!item.observed_urls.includes(observed)) item.observed_urls.push(observed);
    }
  });
}

const frontierRows = [...frontier.values()].sort((a,b) =>
  a.primary_discovery_id.localeCompare(b.primary_discovery_id) || a.queue_key.localeCompare(b.queue_key));
const leases = [[], []];
for (let i = 0; i < leaseSize * 2 && i < frontierRows.length; i++) leases[i % 2].push(frontierRows[i]);

const manifest = {
  run_id: runId, protocol_version: '1.0', created_at: now,
  source_shards: shardNames.map((n) => `./results/shards/${n}`),
  seed_selection: 'every urls_in_page string; complete absolute HTTP(S); excludes [...] and …',
  queue_key_rules: 'WHATWG URL parse; lowercase scheme/host; default-port removal; empty path slash; fragment removal only',
  limits: {depth: 1, leased_queue_keys_per_worker: leaseSize, fallback_searches: 0},
  workers: 2,
  counts: {events:events.length, unique_queue_keys:frontierRows.length,
    leased_queue_keys:leases[0].length + leases[1].length,
    pending_unleased:frontierRows.length - leases[0].length - leases[1].length}
};

const jsonl = (rows) => rows.map((x) => JSON.stringify(x)).join('\n') + (rows.length ? '\n' : '');
fs.writeFileSync(path.join(runDir, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
fs.writeFileSync(path.join(runDir, 'events.jsonl'), jsonl(events));
fs.writeFileSync(path.join(runDir, 'frontier.jsonl'), jsonl(frontierRows));
fs.writeFileSync(path.join(runDir, 'pages.jsonl'), '');
fs.writeFileSync(path.join(runDir, 'queries.jsonl'), '');
for (let i = 0; i < 2; i++) {
  fs.writeFileSync(path.join(runDir, 'workers', `worker_${i+1}`, 'lease.jsonl'), jsonl(leases[i]));
}
console.log(JSON.stringify(manifest, null, 2));
