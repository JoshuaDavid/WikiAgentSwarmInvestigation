#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const RAW_DIR = path.join(ROOT, 'tmp', 'raw');
const SCRATCH_DIR = path.join(ROOT, 'tmp', 'scratch');
const ARCHIVE_SCRATCH = path.join(ROOT, 'archive', 'pre_canonical_reprocess', 'tmp', 'scratch');
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
const ANCHORS = {
  '2026-05-03': ['May 3, 2026', 'May 6, 2026', 'May 9, 2026'],
  '2026-05-10': ['May 10, 2026', 'May 13, 2026', 'May 16, 2026'],
  '2026-05-17': ['May 17, 2026', 'May 20, 2026', 'May 23, 2026'],
  '2025-10-12': ['October 12, 2025', 'October 15, 2025', 'October 18, 2025'],
  '2025-11-23': ['November 23, 2025', 'November 26, 2025', 'November 29, 2025'],
  '2025-12-07': ['December 7, 2025', 'December 10, 2025', 'December 13, 2025'],
};

function unique(values) { return [...new Set(values)]; }
function ordered(object, keys) { return Object.fromEntries(keys.map((key) => [key, object[key]])); }
function lines(file) { return fs.readFileSync(file, 'utf8').split(/\n/).filter(Boolean); }
function quotedPhrases(query) { return [...query.matchAll(/"([^"]+)"/g)].map((match) => match[1]); }
function resultBlocks(raw) {
  return raw.split(/-{20,}/).filter((block) => /citeturn\d+(?:search|news)\d+/.test(block));
}
function parseBlock(block, query, connectedTerms) {
  const lower = block.toLowerCase();
  const literalTargets = TARGETS.filter((term) => lower.includes(term.toLowerCase()));
  const connectedMatches = connectedTerms.filter((term) => lower.includes(term.toLowerCase()));
  if (literalTargets.length === 0 && connectedMatches.length === 0) return { kind: 'excluded' };

  const citationIndex = block.search(/\n?citeturn\d+(?:search|news)\d+/);
  const heading = block.slice(0, citationIndex).trim();
  const headingMatch = heading.match(/^([\s\S]*?) \((https?:\/\/[^)]+)\)$/);
  if (!headingMatch) return { kind: 'failure', heading };

  const urls = unique((block.match(/https?:\/\/[^\s<>"'`)]+/g) || []).filter(u => !/^https?:\/\/\]/.test(u)));
  const published = (block.match(/\bPublished:\s*([^;\n]+)/) || [])[1] || null;
  const modified = (block.match(/\bModified:\s*([^;\n]+)/) || [])[1] || null;
  const crawled = (block.match(/\bCrawled:\s*([^;\n]+)/) || [])[1] || null;
  return {
    kind: 'record',
    record: ordered({
      published_date: published,
      modified_date: modified,
      cache_age: crawled ? `Crawled: ${crawled}` : null,
      page_title: headingMatch[1],
      page_url: headingMatch[2],
      urls_in_page: urls,
      first_seen_query: query,
      matched_target_strings: unique([...literalTargets, ...connectedMatches]),
    }, RESULT_KEYS),
  };
}
function mergeRecord(oldRecord, newRecord) {
  const merged = { ...oldRecord };
  merged.urls_in_page = unique([...oldRecord.urls_in_page, ...newRecord.urls_in_page]);
  merged.matched_target_strings = unique([...oldRecord.matched_target_strings, ...newRecord.matched_target_strings]);
  for (const key of ['published_date', 'modified_date', 'cache_age', 'page_title']) {
    if (merged[key] === null && newRecord[key] !== null) merged[key] = newRecord[key];
  }
  return ordered(merged, RESULT_KEYS);
}
function validateCore(week, ledger) {
  const expected = [];
  for (const target of TARGETS) {
    expected.push(`"${target}"`);
    for (const date of ANCHORS[week]) expected.push(`"${target}" "${date}"`);
  }
  if (expected.some((query, index) => ledger[index]?.query !== query)) throw new Error(`${week}: core matrix mismatch`);
}
function reprocessWeek(week) {
  const liveQueryFiles = fs.readdirSync(SCRATCH_DIR).filter((name) => name.startsWith(`${week}.group_`) && name.endsWith('.queries.jsonl')).sort();
  const querySource = liveQueryFiles.length ? SCRATCH_DIR : ARCHIVE_SCRATCH;
  const queryFiles = fs.readdirSync(querySource).filter((name) => name.startsWith(`${week}.group_`) && name.endsWith('.queries.jsonl')).sort();
  const rawFiles = fs.readdirSync(RAW_DIR).filter((name) => name.startsWith(`${week}.group_`) && name.endsWith('.txt')).sort();
  if (queryFiles.length !== rawFiles.length) throw new Error(`${week}: raw/query count mismatch (${rawFiles.length}/${queryFiles.length})`);

  const state = new Map();
  const ledger = [];
  const connected = new Set();
  let parserFailures = 0;
  let excludedBlocks = 0;
  fs.mkdirSync(SCRATCH_DIR, { recursive: true });
  fs.mkdirSync(SHARD_DIR, { recursive: true });

  for (let index = 0; index < queryFiles.length; index++) {
    const group = index + 1;
    const pad = String(group).padStart(3, '0');
    const oldQueryLines = lines(path.join(querySource, queryFiles[index]));
    if (oldQueryLines.length !== 1) throw new Error(`${week} group ${pad}: expected one query line`);
    const oldQuery = JSON.parse(oldQueryLines[0]);
    if (oldQuery.group_number !== group || oldQuery.query_sequence !== group) throw new Error(`${week} group ${pad}: source sequence mismatch`);

    if (group > 92) for (const phrase of quotedPhrases(oldQuery.query)) connected.add(phrase);
    const rawPath = path.join(RAW_DIR, `${week}.group_${pad}.txt`);
    if (!fs.existsSync(rawPath)) throw new Error(`${week} group ${pad}: missing raw response`);
    const raw = fs.readFileSync(rawPath, 'utf8');
    const blocks = resultBlocks(raw);
    const retained = [];
    for (const block of blocks) {
      const parsed = parseBlock(block, oldQuery.query, [...connected]);
      if (parsed.kind === 'record') retained.push(parsed.record);
      else if (parsed.kind === 'failure') parserFailures++;
      else excludedBlocks++;
    }

    const delta = [];
    let newPages = 0;
    for (const record of retained) {
      const oldRecord = state.get(record.page_url);
      if (!oldRecord) {
        state.set(record.page_url, record);
        delta.push(record);
        newPages++;
      } else {
        const merged = mergeRecord(oldRecord, record);
        if (JSON.stringify(merged) !== JSON.stringify(oldRecord)) {
          state.set(record.page_url, merged);
          delta.push(merged);
        }
      }
    }

    const preservedLeads = Array.isArray(oldQuery.new_distinctive_leads) ? unique(oldQuery.new_distinctive_leads) : [];
    const queryRecord = ordered({
      group_number: group,
      query_sequence: group,
      search_mode: oldQuery.search_mode ?? null,
      query: oldQuery.query,
      returned_result_count: blocks.length,
      retained_result_count: retained.length,
      new_page_count: newPages,
      cumulative_page_count: state.size,
      new_distinctive_leads: preservedLeads,
    }, QUERY_KEYS);
    ledger.push(queryRecord);
    for (const lead of preservedLeads) connected.add(lead);
    fs.writeFileSync(path.join(SCRATCH_DIR, `${week}.group_${pad}.queries.jsonl`), `${JSON.stringify(queryRecord)}\n`);
    fs.writeFileSync(path.join(SCRATCH_DIR, `${week}.group_${pad}.results.jsonl`), delta.map((record) => JSON.stringify(record)).join('\n') + (delta.length ? '\n' : ''));
  }

  validateCore(week, ledger);
  if (ledger.some((record, index) => record.query_sequence !== index + 1)) throw new Error(`${week}: discontinuous ledger`);
  const results = [...state.values()];
  for (const record of results) if (JSON.stringify(Object.keys(record)) !== JSON.stringify(RESULT_KEYS)) throw new Error(`${week}: result schema`);
  for (const record of ledger) if (JSON.stringify(Object.keys(record)) !== JSON.stringify(QUERY_KEYS)) throw new Error(`${week}: query schema`);
  fs.writeFileSync(path.join(SHARD_DIR, `${week}.queries.jsonl`), ledger.map((record) => JSON.stringify(record)).join('\n') + '\n');
  fs.writeFileSync(path.join(SHARD_DIR, `${week}.results.jsonl`), results.map((record) => JSON.stringify(record)).join('\n') + '\n');

  const replay = new Map();
  for (let group = 1; group <= ledger.length; group++) {
    const pad = String(group).padStart(3, '0');
    for (const text of lines(path.join(SCRATCH_DIR, `${week}.group_${pad}.results.jsonl`))) {
      const record = JSON.parse(text); replay.set(record.page_url, record);
    }
  }
  if (JSON.stringify([...replay.values()]) !== JSON.stringify(results)) throw new Error(`${week}: checkpoint replay mismatch`);
  const queryConcat = [];
  for (let group = 1; group <= ledger.length; group++) queryConcat.push(...lines(path.join(SCRATCH_DIR, `${week}.group_${String(group).padStart(3, '0')}.queries.jsonl`)));
  if (`${queryConcat.join('\n')}\n` !== fs.readFileSync(path.join(SHARD_DIR, `${week}.queries.jsonl`), 'utf8')) throw new Error(`${week}: query concatenation mismatch`);

  return {
    week,
    groups: ledger.length,
    raw_files: rawFiles.length,
    records: results.length,
    distinct_page_urls: new Set(results.map((record) => record.page_url)).size,
    urls_in_page: results.reduce((sum, record) => sum + record.urls_in_page.length, 0),
    truncated_urls: results.reduce((sum, record) => sum + record.urls_in_page.filter((url) => /\.\.\.|…|\[\.\.\.\]/.test(url)).length, 0),
    parser_failures: parserFailures,
    excluded_blocks: excludedBlocks,
    final_drought: (() => { let count = 0; for (let i = ledger.length - 1; i >= 0 && ledger[i].new_page_count === 0 && ledger[i].new_distinctive_leads.length === 0; i--) count++; return count; })(),
  };
}

const weeks = process.argv.slice(2);
if (!weeks.length) throw new Error('usage: canonical_raw_reprocess.js WEEK [WEEK ...]');
console.log(JSON.stringify(weeks.map(reprocessWeek), null, 2));
