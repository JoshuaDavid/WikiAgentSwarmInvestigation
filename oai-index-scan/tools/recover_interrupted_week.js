#!/usr/bin/env node
'use strict';

// Rebuild an interrupted weekly run from its immutable raw responses and
// one-query checkpoint ledger. Unlike the older reprocessors, result boundaries
// are detected by the heading+citation pair because the search renderer does
// not consistently insert horizontal rules between adjacent results.

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const WEEK = process.argv[2];
if (!/^\d{4}-\d{2}-\d{2}$/.test(WEEK || '')) {
  throw new Error('usage: recover_interrupted_week.js YYYY-MM-DD');
}

const RAW = path.join(ROOT, 'tmp', 'raw');
const SCRATCH = path.join(ROOT, 'tmp', 'scratch');
const SHARDS = path.join(ROOT, 'results', 'shards');
const TARGETS = [
  'md.succ.ai', 'vanderbi.lt', 'bitily.in', 'yourls.pro', 'yourls.shop',
  'yourls.website', 'yourls.space', 'goto.unm.edu', 'r.jina.ai', 'httpbin.org',
  'allorigins.hexlet.app', 'da.gd', 'markdown.new', 'pure.md', 'proxymule.com',
  'urlquery.net', 'jqp.vercel.app', 'api.microlink.io', 'cors-get-proxy',
  'cors.bwa.workers.dev', 'cors.ripka.workers.dev', 'jsonhero.io', 'urltomarkdown',
];
const RESULT_KEYS = ['published_date', 'modified_date', 'cache_age', 'page_title', 'page_url', 'urls_in_page', 'first_seen_query', 'matched_target_strings'];
const QUERY_KEYS = ['group_number', 'query_sequence', 'search_mode', 'query', 'returned_result_count', 'retained_result_count', 'new_page_count', 'cumulative_page_count', 'new_distinctive_leads'];

const lines = (file) => fs.readFileSync(file, 'utf8').split(/\n/).filter(Boolean);
const unique = (values) => [...new Set(values)];
const ordered = (object, keys) => Object.fromEntries(keys.map((key) => [key, object[key]]));

function resultBlocks(raw) {
  const starts = [...raw.matchAll(/^([^\n]+)\nciteturn\d+(?:search|news)\d+[^\n]*/gm)];
  return starts.map((match, index) => ({
    heading: match[1],
    text: raw.slice(match.index, index + 1 < starts.length ? starts[index + 1].index : raw.length),
  }));
}

function parseBlock(block, query, connectedTerms) {
  const heading = block.heading.match(/^(.*?) \((https?:\/\/[^)]+)\)$/);
  if (!heading) return { kind: 'failure' };
  const lower = block.text.toLowerCase();
  const literal = TARGETS.filter((term) => lower.includes(term.toLowerCase()));
  const connected = connectedTerms.filter((term) => lower.includes(term.toLowerCase()));
  if (!literal.length && !connected.length) return { kind: 'excluded' };
  const published = (block.text.match(/\bPublished:\s*([^;\n]+)/) || [])[1] || null;
  const modified = (block.text.match(/\bModified:\s*([^;\n]+)/) || [])[1] || null;
  const crawled = (block.text.match(/\bCrawled:\s*([^;\n]+)/) || [])[1] || null;
  return { kind: 'record', record: ordered({
    published_date: published,
    modified_date: modified,
    cache_age: crawled,
    page_title: heading[1],
    page_url: heading[2],
    urls_in_page: unique(block.text.match(/https?:\/\/[^\s<>"'`)]+/g) || []),
    first_seen_query: query,
    matched_target_strings: unique([...literal, ...connected]),
  }, RESULT_KEYS) };
}

function merge(oldRecord, record) {
  const merged = { ...oldRecord };
  merged.urls_in_page = unique([...oldRecord.urls_in_page, ...record.urls_in_page]);
  merged.matched_target_strings = unique([...oldRecord.matched_target_strings, ...record.matched_target_strings]);
  for (const key of ['published_date', 'modified_date', 'cache_age', 'page_title']) {
    if (merged[key] === null && record[key] !== null) merged[key] = record[key];
  }
  return ordered(merged, RESULT_KEYS);
}

const start = new Date(`${WEEK}T00:00:00Z`);
const dates = [0, 3, 6].map((offset) => {
  const date = new Date(start); date.setUTCDate(date.getUTCDate() + offset);
  return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
});
const core = [];
for (const target of TARGETS) core.push(`"${target}"`, ...dates.map((date) => `"${target}" "${date}"`));
const queryFiles = fs.readdirSync(SCRATCH)
  .filter((name) => name.startsWith(`${WEEK}.group_`) && name.endsWith('.queries.jsonl'))
  .sort();
// A process can die after preserving raw core responses but before writing any
// checkpoints. In that narrowly auditable case, reconstruct only the fixed core
// order; arbitrary follow-up queries cannot be inferred safely.
const sourceLedger = queryFiles.length ? queryFiles.map((name, index) => {
  const records = lines(path.join(SCRATCH, name));
  if (records.length !== 1) throw new Error(`${name}: expected exactly one record`);
  const record = JSON.parse(records[0]);
  if (record.group_number !== index + 1 || record.query_sequence !== index + 1) {
    throw new Error(`${name}: discontinuous group/query sequence`);
  }
  return record;
}) : core.map((query, index) => ({
  group_number: index + 1,
  query_sequence: index + 1,
  search_mode: null,
  query,
  new_distinctive_leads: [],
}));
if (sourceLedger.length < 92 || core.some((query, index) => sourceLedger[index].query !== query)) {
  throw new Error(`${WEEK}: incomplete or incorrect 92-query core`);
}

const state = new Map();
const ledger = [];
const connectedTerms = new Set();
let failures = 0;
let excluded = 0;
for (let index = 0; index < sourceLedger.length; index++) {
  const group = index + 1;
  const pad = String(group).padStart(3, '0');
  const source = sourceLedger[index];
  if (group > 92) for (const match of source.query.matchAll(/"([^"]+)"/g)) connectedTerms.add(match[1]);
  const rawPath = path.join(RAW, `${WEEK}.group_${pad}.txt`);
  if (!fs.existsSync(rawPath)) throw new Error(`${WEEK}: missing raw group ${pad}`);
  const blocks = resultBlocks(fs.readFileSync(rawPath, 'utf8'));
  const retained = [];
  for (const block of blocks) {
    const parsed = parseBlock(block, source.query, [...connectedTerms]);
    if (parsed.kind === 'record') retained.push(parsed.record);
    else if (parsed.kind === 'failure') failures++;
    else excluded++;
  }
  const delta = [];
  let fresh = 0;
  for (const record of retained) {
    const old = state.get(record.page_url);
    if (!old) {
      state.set(record.page_url, record); delta.push(record); fresh++;
    } else {
      const merged = merge(old, record);
      if (JSON.stringify(merged) !== JSON.stringify(old)) {
        state.set(record.page_url, merged); delta.push(merged);
      }
    }
  }
  const queryRecord = ordered({
    group_number: group,
    query_sequence: group,
    search_mode: source.search_mode ?? null,
    query: source.query,
    returned_result_count: blocks.length,
    retained_result_count: retained.length,
    new_page_count: fresh,
    cumulative_page_count: state.size,
    new_distinctive_leads: Array.isArray(source.new_distinctive_leads) ? unique(source.new_distinctive_leads) : [],
  }, QUERY_KEYS);
  ledger.push(queryRecord);
  fs.writeFileSync(path.join(SCRATCH, `${WEEK}.group_${pad}.queries.jsonl`), `${JSON.stringify(queryRecord)}\n`);
  fs.writeFileSync(path.join(SCRATCH, `${WEEK}.group_${pad}.results.jsonl`), delta.map(JSON.stringify).join('\n') + (delta.length ? '\n' : ''));
}

fs.mkdirSync(SHARDS, { recursive: true });
const results = [...state.values()];
fs.writeFileSync(path.join(SHARDS, `${WEEK}.queries.jsonl`), `${ledger.map(JSON.stringify).join('\n')}\n`);
fs.writeFileSync(path.join(SHARDS, `${WEEK}.results.jsonl`), `${results.map(JSON.stringify).join('\n')}\n`);

const replay = new Map();
for (let group = 1; group <= ledger.length; group++) {
  const pad = String(group).padStart(3, '0');
  for (const line of lines(path.join(SCRATCH, `${WEEK}.group_${pad}.results.jsonl`))) {
    const record = JSON.parse(line); replay.set(record.page_url, record);
  }
}
if (JSON.stringify([...replay.values()]) !== JSON.stringify(results)) throw new Error('result checkpoint replay mismatch');
const rebuiltQueryFiles = fs.readdirSync(SCRATCH)
  .filter((name) => name.startsWith(`${WEEK}.group_`) && name.endsWith('.queries.jsonl'))
  .sort();
const concatenated = rebuiltQueryFiles.map((name) => lines(path.join(SCRATCH, name)).join('\n')).join('\n') + '\n';
if (concatenated !== fs.readFileSync(path.join(SHARDS, `${WEEK}.queries.jsonl`), 'utf8')) throw new Error('query checkpoint concatenation mismatch');
for (const record of results) if (JSON.stringify(Object.keys(record)) !== JSON.stringify(RESULT_KEYS)) throw new Error('result schema mismatch');
for (const record of ledger) if (JSON.stringify(Object.keys(record)) !== JSON.stringify(QUERY_KEYS)) throw new Error('query schema mismatch');

let drought = 0;
for (let index = ledger.length - 1; index >= 0 && ledger[index].new_page_count === 0 && ledger[index].new_distinctive_leads.length === 0; index--) drought++;
console.log(JSON.stringify({
  week: WEEK,
  search_calls: ledger.length,
  individual_queries: ledger.length,
  raw_files: ledger.length,
  result_blocks: ledger.reduce((sum, record) => sum + record.returned_result_count, 0),
  retained_result_blocks: ledger.reduce((sum, record) => sum + record.retained_result_count, 0),
  records: results.length,
  urls_in_page: results.reduce((sum, record) => sum + record.urls_in_page.length, 0),
  truncated_urls: results.reduce((sum, record) => sum + record.urls_in_page.filter((url) => /\.\.\.|…|\[\.\.\.\]/.test(url)).length, 0),
  parser_failures: failures,
  excluded_blocks: excluded,
  final_drought: drought,
  search_modes: unique(ledger.map((record) => record.search_mode)),
}, null, 2));
