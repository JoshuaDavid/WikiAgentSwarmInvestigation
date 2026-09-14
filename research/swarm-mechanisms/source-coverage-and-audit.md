# Retained sources, coverage, and inference hazards

Audit performed September 13, 2026. This is a source inventory, not a count of agents or swarms. Counts below were recomputed from retained JSONL rows rather than copied from generated READMEs. No new network requests or experiments were required.

## 1. What the corpus contains

`agent-logs/prowiki/revisions.jsonl` is the important body-bearing primary wiki export. The similarly named `agent-logs/dse/revisions.jsonl` is **not** a second collection of full conversations: it contains 22,385 metadata-only rows and zero bodies. The former covers four wikis; the latter is a later RecentChanges scrape of DSE alone.

“Bodies” in the table means nonempty strings after whitespace stripping. It does not mean a substantive agent message: default wiki stubs, human posts, copied documents, and researcher tests can all be nonempty. “Dated” means that a nonnull `time` value is present, not that the timestamp independently establishes the content's publication date. Earliest/latest are dates represented in the export's `time` field, including known non-swarm material.

| Export under `agent-logs/` | Revision rows | Distinct page IDs | Nonempty bodies | Dated rows | Represented date range |
|---|---:|---:|---:|---:|---|
| `prowiki` | 14,591 | 4,579 | 14,514 | 14,591 | May 24–July 2, 2026 |
| `dse` | 22,385 | 5,158 | 0 | 22,385 | May 24–September 4, 2026 |
| `probier` | 900 | 556 | 552 | 900 | May 24–September 5, 2026 |
| `fractal` | 562 | 381 | 376 | 562 | May 24–September 5, 2026 |
| `wiki4d` | 235 | 158 | 158 | 235 | May 24–September 4, 2026 |
| `apchem` | 134 | 27 | 47 | 134 | April 8–July 24, 2026 |
| `texteditors` | 68 | 49 | 48 | 68 | May 17–September 4, 2026 |
| `ludism` | 35 | 8 | 35 | 35 | October 8, 2018–May 26, 2026 |
| `milkwiki` | 16 | 10 | 10 | 16 | May 26–September 4, 2026 |
| `pastes` (aggregate import) | 458 | 458 | 458 | 421 | September 3, 2020–September 4, 2026 |
| `paste-linuxiarz` | 381 | 381 | 254 | 219 | July 6, 2022–June 18, 2026 |
| `pastebin-k4be` | 198 | 198 | 198 | 198 | October 24, 2025–September 5, 2026 |
| `anna.fyi` | 103 | 103 | 100 | 100 | March 12–September 6, 2026 |
| `paste.steamr.com` | 36 | 36 | 36 | 0 | No absolute times |
| `pastebin.tarcseh.me` | 23 | 23 | 20 | 20 | January 22–September 7, 2026 |
| `pastebin.freepbx.org` | 13 | 13 | 1 | 0 | No absolute times |
| `pb.dynavirt.com` | 8 | 8 | 8 | 8 | April 20, 2023–September 6, 2026 |
| `pastie.iem.at` | 7 | 7 | 7 | 0 | No absolute times |
| `paste.lightcast.com` | 7 | 7 | 0 | 0 | No absolute times |
| `paste.smirky.net` | 4 | 4 | 4 | 1 | September 6, 2026 |
| `pastebin.faster-it.de` | 4 | 4 | 4 | 4 | March 12–September 7, 2026 |
| `p.gaa.st` | 1 | 1 | 1 | 0 | No absolute time |
| `paste.centos.org`, `pb.psychotic.ninja` | 0 each | 0 | 0 | 0 | Empty retained exports |
| `shorteners` | 4,285 | 59 | 4,285 | 0 | No absolute times |
| `popcat-wayback` | 119 | 119 | 119 | 119 | **Capture dates:** May 12–September 9, 2026 |
| `gems` | 12 | 7 | 12 | 0 | No absolute times in this export |

The 14,591 ProWiki rows divide into DSE **13,403**, Probier 1,013, Fractal 169, and Dorfwiki 6. The corresponding nonempty-body counts are **13,337**, 1,012, 159, and 6. Thus “13,337 DSE bodies searched” and “13,403 DSE revision rows” are different, simultaneously correct denominators. The export's `events.jsonl` contains 14,591 save pointers, 5,217 deletions, four reverts, and 101 probes. Saves repeat the revision population; a deletion or probe is not another agent post. The export also derives 68 first-recreation **relations**, not 68 additional events.

Linuxiarz's 381 rows comprise 219 shellac imports and 162 later Wayback additions. Of the latter, 127 contain an empty body and `body_availability=wayback_view_page_only`; only 35 add nonempty recovered source. The 219 inherited dates and 162 relative/unknown dates are separate from that body-availability distinction. Neither “381 pastes” nor a site's oldest retained personal configuration file dates 381 agent interactions.

### Other retained primary material

The shellac reading-pack SQLite database contains 16,579 documents: 11,811 wiki texts, 4,285 shortener candidates, 458 paste candidates, 13 extra-wiki candidates, and 12 package-text candidates. This was recomputed using a read-only SQLite connection. It is a deduplicated reading pack, **not an independent observation of 16,579 new events**. Its own original README says known false positives, copied material, and possible researcher imitations remain. It also says deduplication retained one representative group/date rather than full occurrence provenance; all `parent_id` fields are null, meaning unknown parentage. Literal cross-links in `relations` are not verified replies. Source: `tmp/shellac_extracted/agent-reading-pack-20260905/README.md`.

`agent-logs/pastes-evidence-index/evidence.csv` has 1,109 rows and 27 columns, recomputed with CSV parsing rather than line counting. Its populations are 533 short links, 381 paste candidates, 121 wiki revisions, 14 pastes, 12 package texts, ten archive captures, ten other-wiki records, nine capture clusters, eight scanner reports, seven original pastes, three carrier references, and one paste reference. Its `Change` values are 600 Added, 381 Retained, 121 Retained CVD, and seven Corrected. The index contributes provenance and links for services missing from standalone exports—Fragbin, Luis, Probyte, Ghostarchive, URLquery, Bitily, Telegra.ph and several shorteners—but does not turn its overlapping entries into independent confirmations.

`agent-logs/apchem/shellac_bodies.jsonl` is an eleven-row supplement. **Three rows explicitly say `body_is_actual_revision=false`**: UseModWiki returned its current head when asked for an unavailable old revision. Those bodies cannot date a behavior to the requested revision number. The remaining eight are marked actual source candidates; their suggested joins remain best-effort across independent captures.

The supplied Discord export has **315 messages, all by `faul_sname`**, from September 4 at 22:47:24 UTC through September 13 at 04:17:02 UTC. It is not the group's complete discussion. The original wiki report and shared skeleton are supplied prose sources, not new independent experiments. The skeleton's timeline explicitly distinguishes inherited “slop” from externally reported findings; treat it as a claim list to resolve, not a second timestamp source.

At this audit's filesystem snapshot, `/root/.codex/sessions` contained 467 JSONL files (745,181,177 bytes), and `/root/.claude/projects/-collusionwiki` contained 223 (87,787,626 bytes). These are file counts, not unique episodes, and will change during ongoing work. Investigation transcripts establish what the researchers and their assistants tried; historical wiki content quoted inside them does not acquire a second witness. This inventory does **not** claim every transcript was read end-to-end.

## 2. Duplication is not just a counting issue

There are 3,904 overlapping page IDs between the ProWiki and standalone DSE exports, 542 between ProWiki and standalone Probier, and 68 between ProWiki and standalone Fractal. These identify overlapping pages, not synchronized revision populations.

**Do not deduplicate these exports by `rev_id` alone.** Standalone DSE's scraper assigns `seq` by incrementing a local counter over the RecentChanges rows (`scrape/dse.py:604–635`); the archive export has its own retained sequence. Identical strings therefore need not identify the same edit.

The two DSE collections share 12,224 `rev_id` strings, of which 6,935 have differing `label` values. Some differences are redaction or naming differences, so this is not a count of 6,935 bad joins. But concrete wrong joins exist:

| Same apparent revision ID | ProWiki record | Standalone DSE record |
|---|---|---|
| `dse~AICountyCreateGet2027@1` | AlphaBeta, June 18 18:06:51 UTC | MarkusLude, June 19 15:36 at the export's +01:00 offset |
| `dse~Agent0FinalMassRefsCountySecJune19X@3` | AgentHelperUniqueXYZ, June 22 02:45:00 UTC | MarkusLude, June 19 17:50 at +01:00 |

The first is an agent write joined to a later cleanup entry. The second even reverses the actual ordering. `analyses/agent-comms/build.py:135` explicitly prefers a body-bearing row per `rev_id`, so its merged populations are not a safely deduplicated event ledger. For behavioral sequences, use one collection's clocks and revision relationships, then match other collections through underlying request/RCS identity or cautiously through page, content, and time—not the local suffix alone.

All but two of the aggregate `pastes` rows have the same source URL in a standalone site export: Linuxiarz 219, K4be 126, Anna 63, Steamr 33, Tarcseh six, Smirky three, Dynavirt three, Faster-IT two, and p.gaa.st one. The two unmatched aggregate URLs are nervesocket.com. Exact body hashes confirm all those inherited overlaps **except K4be**. K4be illustrates why entity deduplication and byte deduplication differ: the same 126 source URLs were subsequently represented with different title/body formatting or escaping. Zero identical hashes there does not mean 126 new independent artifacts.

## 3. Clocks: what can actually be placed on a timeline

ProWiki's `time_grade` distribution is 14,482 `reqlog`, 103 `rclog`, and six `write_date`; consult `winning_clock`, raw clocks, and `uncertainty_seconds` for each claim. Standalone DSE has 22,385 `rc_wall` rows, all minute precision and all using the scraper's declared +01:00 offset. That offset produces an approximately one-hour disagreement with the primary summer UTC records. Do not mix the two clocks to infer a link preceded its target or a reply preceded its request.

K4be's 198 dates are site API `created` values captured later, not 198 contemporaneous archive captures. Linuxiarz's 219 dates are inherited source metadata; its 162 Wayback additions retain phrases such as “2 Months ago,” which do not by themselves supply an absolute publication instant. Popcat's `time` is explicitly a **Wayback capture time**. Its `popcat_created_date` is a separate site's claimed creation date. Both may be useful; neither should silently replace the other.

Even `time_grade` alone is insufficient: all seven Pastie rows and three Steamr rows carry `api_paste_created_field` while their `time` is null. Check the value, not merely the grade label.

The shortener import has no dates whatsoever. Its `seq` is lexicographic document-hash order, and `archived_at` is the schema-import time. A May-looking code, a model's claimed date in pasted text, a task-clock timestamp, and a September capture are four different pieces of information. None automatically establishes a May write.

The search-shard dating error is more serious than uncertainty. `oai-index-scan/INSTRUCTIONS.md:5–10` defines date-named shards as initial search assignments and permits out-of-week results. `analyses/oai-url-taxonomy/extract_url_history.py` subsequently anchors relative “Crawled N ago” strings to the shard date. The code does not make the search index a historical snapshot. The November 16, 2025 shard's line 45, for example, includes a URL parameter `1778910680.6934943` corresponding to May 16, 2026 and a present-day “Crawled: 3 months ago” string. The parameter is not authenticated publication time, but the record plainly does not justify backdating that result by subtracting three months from November 2025. The old early-date conclusions require re-evidence, not cosmetic relabelling.

## 4. What graph edges and keyword hits cannot establish

`analyses/agent-comms/README.md` starts from “A wrote P before B wrote P,” then says A's write was visible to B. The observed fact is the write ordering. A cached old page, no intervening read, a failed fetch, or a blind append breaks the proposed exposure step. A co-editorship edge is a **possible communication opportunity**, not an observed read, and certainly not proof that B obeyed A.

Similarly, a new revision containing another handle may preserve old text without newly addressing anyone. Search hunks that actually insert or replace text, compare the diff base, and read the surrounding exchange. A statement repeated across 100 retained revisions is not 100 independently initiated instructions. First retained appearance is not necessarily first creation when earlier revisions are absent.

Labels are not process IDs. One process may use several handles; several processes may pick the same descriptive handle; a paste site may assign an animal-name default; humans also edit these sites. Per-page task-family classifications are leads, not an episode map: a lobby can serve several tasks, while one task can use many pages. Counting distinct families per handle does not prove a process had cross-task memory, nor prove the handle was reused.

The repository root explicitly warns that nearly all its analyses were generated by Claude and much has not been human-checked (`README.md:1–5`). One consequential example is `analyses/emergence/README.md`, which declares that the swarm cannot build infrastructure, cannot preserve credentials, has no addressing or protocol, and can coordinate only on wikis because pastebin discovery fails. These are not results extracted from the corpus. They assert away the possibility of public credential handoffs, publicly listed pastes, exact addressed replies, and explicit coordination protocols. The retained Linuxiarz exchanges alone defeat “wikis are the unique substrate.” Treat this README as a failed hypothesis, not background truth about RL.

For the central question—why follow instructions from a website—the strongest public-record pattern is **instruction → distinctive response → subsequent acknowledgment or task-state update**. That is stronger than shared vocabulary. It still does not reveal the recipient's hidden prompt, training history, actual reward, or whether a claimed action occurred. A provider-linked trajectory containing the web read and following tool call would close a different evidentiary gap from another plausible-looking wiki message.

## 5. Read-only reproduction

Run from the repository root. This inventory loop recomputes physical rows, distinct pages, nonempty bodies, available timestamps, and clock grades; it does not mutate exports:

```bash
python3 - <<'PY'
import collections, json, pathlib
for p in sorted(pathlib.Path('agent-logs').glob('*/revisions.jsonl')):
    rows = [json.loads(s) for s in p.open() if s.strip()]
    times = sorted(r['time'] for r in rows if r.get('time'))
    print(p.parent.name, len(rows), len({r['page_id'] for r in rows}),
          sum(bool((r.get('body') or '').strip()) for r in rows),
          len(times), times[:1], times[-1:],
          dict(collections.Counter(r.get('time_grade') for r in rows)))
PY
```

Reproduce the misleading revision-ID join without assuming identical IDs mean identical events:

```bash
python3 - <<'PY'
import json
load = lambda p: {r['rev_id']: r for r in map(json.loads, open(p))}
a = load('agent-logs/prowiki/revisions.jsonl')
b = load('agent-logs/dse/revisions.jsonl')
keys = a.keys() & b.keys()
print('shared IDs', len(keys))
print('differing labels', sum(a[k]['label'] != b[k]['label'] for k in keys))
for k in ['dse~AICountyCreateGet2027@1',
          'dse~Agent0FinalMassRefsCountySecJune19X@3']:
    print(k, [(r['label'], r['time']) for r in (a[k], b[k])])
PY
```

For a body-bearing wiki revision, inspect newly added text through the recorded hunks before calling a keyword hit a new behavior:

```bash
python3 - <<'PY'
import json
target = 'dse~DataUSATransportEquipmentSequenceJun11@3'
for r in map(json.loads, open('agent-logs/prowiki/revisions.jsonl')):
    if r['rev_id'] != target:
        continue
    print(r['time'], r['label'], 'diff base:', r['diff_base'])
    lines = r['body'].split('\n')
    for h in r['hunks']:
        if h['op'] in ('insert', 'replace'):
            print('\n'.join(lines[h['b0']:h['b1']]))
PY
```

## 6. Contributor/path ledger

The shared skeleton explicitly credits the following paths (`tmp/shared-doc-skeleton.md:314–322`). This is an attribution ledger, not a ranking or a claim to know the whole group's work.

| Contributor | Supported credit | Provenance / unresolved detail |
|---|---|---|
| shellac | Collected, deduplicated, weakly labelled and redacted the candidate reading pack; reproduced proxy seeking with stock GPT-5.6. | Original reading-pack README; skeleton line 320. Exact first-finder credit for each host remains unestablished. |
| ConcurrentSquared | Recreated RL task environments; reproduction and retrieval-chain work. | Skeleton line 319; faul_sname's September 9 messages 110–112 link recorder experiments and credit ongoing work. Message 110 links a filename dated September 8; the message itself is September 9, 04:52:59 UTC. Specific trial outcomes should cite their retained runs. |
| faul_sname / Josh D | Organized the investigation, archived found sites, reconstructed task families and conversations, explored the web tool/cache, produced visualizations and reported a detection replay. | Discord first message; September 5 messages 11–12, 31–34, 45–46; September 7 message 82; September 8 message 87; September 9 messages 135–137. |
| ro | Database of known incidents/posts; user also credits the visualizer. | Skeleton line 318 links `swarm.termina.digital/db/`. Do not infer individual identity from similarly named contributors in another README. |
| lumi | Resource described as “pangram for swarm text.” | Skeleton line 317. No measured detector accuracy is supplied there. |
| cali + luka | Investigating cross-model collusion propensity. | Skeleton line 321 says “working on”; do not silently promote to completed comparison. |
| Other group members | Found additional sites and supplied leads. | Skeleton line 316 explicitly credits everyone; person-to-site chronology remains a stub. |

Useful negative and hypothesis-development work also deserves credit. On September 9 at 07:18 UTC, faul_sname reported excluding much of the candidate material, supplied an inspection command for geopaste.scratchbook.ch, and separately identified Linuxiarz as the important non-wiki communication lead (Discord line 114). On September 10 at 10:37 UTC, they reported roughly 5,000 non-junk cache URLs and **explicitly noted that May search terms retrieved events outside May** (line 199). September 12's two-cache interpretation (line 280) and compaction/persistent-shortlink explanation (lines 302–306) are dated hypotheses, not already demonstrated causes.

The original collusion.wiki report separately credits Sydney Von Arx, Cormac Slade Byrd, Spencer Kitts, and Thomas Larsen, with additional analysis and translation help listed in the supplied report. Credits for the original investigation and this follow-up should remain separate.
