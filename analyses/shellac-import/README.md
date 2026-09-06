# shellac-import

Adapts shellac's `agent-reading-pack-20260905` reading pack into the
`agent-logs/` directory layout the rest of the repo already uses.

## Vocabulary

- **shellac reading pack** — the tarball
  `agent-reading-pack-20260905.tar.gz` (input SHA-256
  `6965c741d0fbe767b84660629ef513b2bc4488f5b4c9ee97519f6749fc26e0af`) prepared
  by user "shellac". Contains 16,579 deduplicated candidate agent texts across
  five source_types.
- **schema adaptation** — mapping shellac's `documents` table into the
  `pages.jsonl` / `revisions.jsonl` / `events.jsonl` / `labels.jsonl` /
  `manifest.json` / `SHA256SUMS` layout used by `agent-logs/prowiki/` and its
  sister directories.
- **body_is_actual_revision** — only used in
  `agent-logs/apchem/shellac_bodies.jsonl`. Flags UseModWiki's "revision N not
  available (showing current revision instead)" fallback banner. When false,
  the body is the head at the time shellac scraped it, not revision N.

## Outputs

Running `python3 analyses/shellac-import/import.py` writes into
`agent-logs/`:

| Directory | Rows | Source_type slice |
|---|---:|---|
| `agent-logs/pastes/` | 458 pages / 458 revisions / 156 labels | `paste_candidate` |
| `agent-logs/shorteners/` | 59 pages / 4,285 revisions / 1 label | `shortener_candidate` |
| `agent-logs/gems/` | 7 pages / 12 revisions / 1 label | `package_text_candidate` |
| `agent-logs/apchem/shellac_bodies.jsonl` | 11 rows | `extra_wiki_candidate` for tmcleod-apchem |

The shellac pack's `extra_wiki_candidate` slice also has 2 rows for
ludism-live pages (`AubergineStew`, `FedRefB`). Those pages are already covered
by `agent-logs/ludism/` at higher fidelity (raw wiki source, full 19-revision
history for `AubergineStew`). The script does not import them.

## Schema deviations from `agent-logs/prowiki/`

The shellac pack does not carry per-request logs, IPs, diff hunks, or admin
event streams. The schema adaptation therefore differs from `prowiki/`:

- `body_encoding` is `raw_utf8`. Bodies live inline as JSON strings in
  `revisions.jsonl`, not base64 with a per-row encoding tag.
- `ip16`, `hunks`, `diff_base`, `request_time`, `success_time`,
  `recent_changes_time`, `wiki_revision_number`, `is_minor_edit`,
  `rcs_path`, `rcs_rev`, `change_summary`, `request_action`,
  `related_event_id`, `relation_type`, `round_id` are null everywhere.
- `events.jsonl` contains only `save` rows. No `delete` / `revert` / `probe`
  populations. Downstream analyses that iterate event_types can iterate
  `["save"]` here.
- `label_source` is a new field. It reads `shellac_recovered_author` when
  shellac attributed an author, otherwise `unknown`.
- Each revision row carries a `shellac_*` prefix set (`shellac_doc_id`,
  `shellac_source_group`, `shellac_source_url`, `shellac_title`,
  `shellac_occurrences`, `shellac_timestamp_basis`) so consumers can join
  back to the shellac reading pack row by row.
- Pages that carry many revisions (shorteners, mostly) receive `seq` values
  ordered by `(timestamp_utc, shellac_doc_id)`. Shorteners have no timestamps,
  so the ordering is purely lexicographic on `shellac_doc_id` — do not read
  `seq` as chronological for shortener revisions.

## Attribution

The candidate texts were collected, deduplicated, weakly labelled, and
redacted by shellac. This directory only adapts the schema; bodies are
unchanged. See each `agent-logs/{pastes,shorteners,gems}/manifest.json` for
`attribution.prepared_by = "shellac"` and the per-directory README for the
same caveats shellac published in its own README.

## Re-running

```bash
# Requires the reading pack extracted at
#   tmp/shellac_extracted/agent-reading-pack-20260905/agent-text.sqlite
python3 analyses/shellac-import/import.py
```

The script is idempotent — running it again overwrites the target files with
byte-identical content when the reading pack has not changed.
