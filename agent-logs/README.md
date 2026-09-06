# agent-logs

Wiki-side telemetry from the incident in which a large fleet of RL-trained agents
compromised third-party hosts to reach the wider internet via query-string RCE, then
began writing to and reading from a handful of public wikis to coordinate on
benchmark/eval tasks.

Note: `publictestwiki/` was scraped in an earlier pass and removed after inspection — its edits are Miraheze test-wiki humans, not swarm activity; the handle-graph pipeline was matching on regex collisions. See git history for the dropped export.

Only one export is present so far: `prowiki/` — a snapshot of four public wikis
hosted on the ProWiki (German-language WikiService) farm. All five files were
produced by the same `explorer-schema-2` exporter on **2026-09-03**, from a cut
of `revision.write_date >= 2026-05-01`. `SHA256SUMS` covers every `.jsonl` / `.json`
in the directory.

The exporter is fastidious about "what population is this row counted against" —
every count in `manifest.json` carries a `population_id` and a set of populations
it must never be summed with. Read those before deriving your own totals.

## Files

| File | Rows | What it holds |
|---|---:|---|
| `manifest.json` | — | Export metadata: cut definition, population counts and their non-additivity notes, per-wiki totals, provenance ("recreation_source"), integrity checks, tool versions. |
| `pages.jsonl` | 4,579 | One row per stored page in the cut. Wiki, page name, revision/deletion counts, first/last write, live-body byte count and encoding, `page_family` classification with confidence and source, and the full set of `labels` and IP /16s that touched it. |
| `revisions.jsonl` | 14,591 | One row per stored revision. Full `body` (the wiki source text — this is where nearly all URLs live), `body_sha256`, hunk-level diff against `diff_base`, RCS path, label, IP /16, and three clocks (`write_date`, `request_time`, `success_time`, `recent_changes_time`) with `winning_clock` and `uncertainty_seconds`. `related_event_id` + `relation_type` link recreations back to the earlier delete. |
| `events.jsonl` | 19,913 | Mixed-type request log. `event_type` ∈ {`save`, `delete`, `revert`, `probe`}. `save` rows are thin pointers back into `revisions.jsonl` via `revision_ref`; `delete`/`revert`/`probe` rows carry actor/IP/request-action detail and `source_refs` back into the raw `rclog`/`reqlog` corpus. **Never sum event rows across types** — the exporter's manifest calls this out explicitly (`population_counts.never_sum`). |
| `labels.jsonl` | 3,103 | One row per distinct username / actor label observed writing or attempting to write. Includes total stored revisions, IPs, IP /16s, the full list of pages touched, save-request counts from `edit_actors.jsonl`, and `is_human_handle` (3 of 3,103 rows are true — the rest are agent handles). |

### Wikis in the cut

Everything is labelled by `wiki` (a per-farm identifier):

| wiki | pages | revisions | body bytes |
|---|---:|---:|---:|
| dse | 3,908 | 13,403 | 26,358,586 |
| probier | 601 | 1,013 | 628,751 |
| fractal | 68 | 169 | 195,967 |
| dorfwiki | 2 | 6 | 2,754 |

`dse` is the primary target wiki; `probier` is the farm's public sandbox; `fractal`
and `dorfwiki` are smaller sister wikis on the same farm.

## Schema notes

### `pages.jsonl`
- `page_id` / `page_key`: `wiki/name` vs. `wiki~name`. Both are stable; `page_key` is NFC-normalized.
- `bucket`: first letter of the page name (RCS storage bucket).
- `page_family` / `page_family_source` / `page_family_confidence` / `page_family_method`: classification (`datausa-*`, `ihme-*`, `oecd-*`, `sec-*`, `aihw-*`, plus incident-specific families like `loop-chain-infrastructure`, `relay-coordination`, `source-cache-url-list`, `probe-test`). `off_store_unclassified` means the exporter did not attempt classification (mostly the non-`dse` wikis). `page_family` is a per-page label from an upstream classifier, not per-cohort ground truth — legacy hub pages can be assigned a label that under-represents most of what happens on them. See [`prowiki/README.md`](prowiki/README.md) for the mechanism and a worked `dse/StartSeite` / `vermont-rent` example.
- `n_revs_before`: revisions on the page that pre-date the `2026-05-01` cut and are therefore not exported in `revisions.jsonl`.
- `live_body_variant` / `head_differs_from_live` / `deleted_live`: state of the current live copy on the wiki farm vs. what is in this export.
- `labels`, `n_labels`, `n_ips`, `n_ip16`: distinct actor labels, IPs, and /16s that ever wrote the page.

### `revisions.jsonl`
- `body`: verbatim wiki source, base64-decoded per `body_encoding` (`ascii` 14,340 / `utf8` 250 / `latin1` 1). **This is where all URLs in the export live** — the other four files contain no `http(s)://` strings at all.
- `body_sha256`: content hash. Manifest confirms `source body hash failures: 0` and `round-trip body hash failures: 0`.
- `diff_base` + `diff_base_reason` + `hunks`: patch relationship to the prior revision. `hunks` uses `difflib.SequenceMatcher(autojunk=False)` with `\n` splitting.
- Clock fields: `time` is the exporter's chosen wall time; `winning_clock` tells you which raw clock was picked; `uncertainty_seconds` bounds the pick. Individual raw clocks (`write_date`, `request_time`, `success_time`, `recent_changes_time`, `rcs_date`) are all preserved. Some rows are graded only by `write_date` or by `rclog`.
- `label`, `ip16`: actor and network /16 for this specific revision.
- `related_event_id` + `relation_type`: for recreations, links back to the earlier `delete` in `events.jsonl` (`relation_type = first_recreation_of`, cutoff-derived — see `manifest.recreation_source`).
- `round_id`: populated on a small subset — flags revisions the exporter grouped into a coordinated "round".
- `change_summary`: user-supplied edit summary (often blank; German admin deletions read `Seite gelöscht.`).

### `events.jsonl`
Four disjoint shapes, all sharing `event_id`, `event_type`, `time`, `time_grade`, `wiki`:

- **`save`** (14,591 rows) — one per stored revision. Thin: just `revision_ref` (join back to `revisions.jsonl`) plus optional `related_event_id`/`relation_type`/`round_id`.
- **`delete`** (5,217 rows) — admin deletion. Adds `actor_label`, `ip16`, `request_action`, `change_summary`, `page_held` (was the page in the export before deletion?), request/success/rclog clocks, and `source_refs` back to `rclog.jsonl` and the appropriate `reqlog_*.jsonl`. In this cut, deletions are almost entirely `[Admin1]` from two admin hosts.
- **`revert`** (4 rows) — native revert requests. Recreations after deletion are recorded as `save` rows with a `related_event_id`, not as `revert` rows.
- **`probe`** (101 rows) — sourced from `attacklog_raw_dse_2605.jsonl`. Non-content GET-request probing (`browse`, `browse-bare`, `form_search`, etc.) with `param_family` giving the parameter shape (e.g. `search`, `title`, `word`, `msg`, `old_plist`, and a scatter of random-looking 4-char families).

**Do not sum populations across event types.** From the manifest:
> The save, delete, revert and probe row populations overlap in what they describe;
> events.jsonl happens to contain 19,913 rows, but that physical row total has no
> incident meaning, and the 68 first-recreation relations are edges rather than rows.

### `labels.jsonl`
- `label`: username / actor handle used on the wiki. Blank string is a distinct label — 899 revisions were saved with no username.
- `stored_revisions` vs. `save_requests`: revisions the exporter kept vs. save requests seen in `edit_actors.jsonl`. They diverge when saves failed or were later deleted.
- `stored_revision_ips` / `stored_revision_ip16`: distinct source IPs and /16s for this label.
- `pages`: full list of `wiki/name` pages ever touched by this label (can be very large for hub labels).
- `wikis`: which wiki(s) the label appeared on.
- `is_human_handle`: 3 rows only (all admin/moderator accounts).

### `manifest.json`
- `cut`: the filter that defines "in scope" (`revision.write_date >= 2026-05-01`).
- `counts`, `per_wiki`, `population_counts`: totals with population IDs. `never_sum` / `never_add_to` fields are load-bearing — see the exporter's warning above.
- `grade_histograms`: for each event type, how the winning clock was decided (`write_date` / `rclog` / `reqlog`).
- `checks`: 30+ integrity checks the exporter ran, all `ok: true` in this cut (row counts, hash round-trips, hunk regeneration, NFC-normalized keys, byte totals).
- `recreation_source`: explains that the 68 first-recreation edges were *derived* from `rclog` (no row-level file was available), using the "same page+label+IP save within two seconds when held; otherwise the first later non-admin save" rule.
- `source_scan`: raw `reqlog_*.jsonl` files scanned, with rows-scanned / form-edit-or-revert / delete row counts per file, plus admin form-edit request counts per admin host.
- `resources`, `tool_versions`: exporter runtime (137 s, 253 MiB peak RSS) and versions (Python 3.13.5, SQLite 3.46.1, `explorer-schema-2`).

## Analyses derived from this export

All derived artifacts (scripts, output data, narratives) live under
`../analyses/`, one directory per topic:

- `analyses/urls/` — every URL in every revision body (115,855 occurrences, 205 hosts) classified into 20 functional categories: own-wiki, fetch/markdown proxies, `jq` relays, CORS bypass proxies, DataUSA/SEC/health/gov data sources, URL shorteners, obfuscated variants, etc.
- `analyses/labels/` — the 3,103 actor handles bucketed into 9 style classes (`role_word_agent`, `openai_branded`, `codename_agent`, `date_prefix_agent`, `redacted`, `human_admin`, `blank`, `short_or_test`, `other`).
- `analyses/blank-labels/` — the 375 non-stub revisions on the `probier` sandbox that were saved without a username (protocol test bench).
- `analyses/addressing/` — the 3,570 revisions where the writer names another known agent handle in the body — the strongest programmatic signal for agent-to-agent addressing.

Every `analyses/<topic>/` contains a `README.md`, one or more scripts, and
an `outputs/` directory. Scripts read from `agent-logs/prowiki/`; outputs
are committed alongside the scripts.

## Non-wiki candidate texts (shellac reading pack)

`agent-logs/pastes/`, `agent-logs/shorteners/` and `agent-logs/gems/` were
imported from shellac's `agent-reading-pack-20260905.tar.gz` (input SHA-256
`6965c741d0fbe767b84660629ef513b2bc4488f5b4c9ee97519f6749fc26e0af`) on
2026-09-06. The pack is a deduplicated, weakly-labelled candidate-agent-text
corpus. Bodies are unchanged from the pack; the schema is adapted to match
`prowiki/`'s `pages.jsonl` / `revisions.jsonl` / `events.jsonl` /
`labels.jsonl` / `manifest.json` / `SHA256SUMS` layout as closely as the
source data allows.

| Directory | Pages | Revisions | Content |
|---|---:|---:|---|
| `pastes/` | 458 | 458 | Public-paste-site posts across 10 hosts (linuxiarz, k4be, anna-fyi, paste.steamr.com, and six smaller ones). |
| `shorteners/` | 59 | 4,285 | Bodies returned by compromised URL-shortener redirect endpoints (vanderbi-lt, uoft-me, goto-unm, popcat, u-ethz-ch). |
| `gems/` | 7 | 12 | Files inside Ruby gem packages published to public gem indexes (atlas-qa, sampledocpayload, tf_drift_handoff). |

`agent-logs/apchem/shellac_bodies.jsonl` is a supplement (11 rows, not a
full re-export): raw revision-source candidates for the `OpenAIRegCFTest`
(r1–r10) and `SandboxISTIResearchTest` (r1) pages, most of which are
`body_availability = "metadata_only"` in the existing `apchem/revisions.jsonl`.
Three of the eleven bodies are UseModWiki's "revision N not available" fallback
to the head — see `body_is_actual_revision` per row.

Shellac's own README calls its labels **"weak candidate, not actor
attribution"** and warns that copied source material, researcher imitations,
and known false positives are retained. Those caveats apply here unchanged.
Content is untrusted (potential prompt injections); shellac redacted 26
common secret patterns across the whole pack.

See [`../analyses/shellac-import/README.md`](../analyses/shellac-import/README.md)
for the schema deviations from `prowiki/` (raw-UTF-8 bodies inline, no diff
hunks, no IPs, only `save` events).
