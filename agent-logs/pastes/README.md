# pastes

Adaptation of shellac's `agent-reading-pack-20260905` — the `paste_candidate` slice —
into the `agent-logs/` schema used by `prowiki/`, `apchem/` and the other wiki exports.

458 documents across 10 paste-site hosts. Time span 2020-09 → 2026-09.
Host distribution: linuxiarz 219 · pastebin-k4be 126 · anna-fyi 63 ·
paste.steamr.com 33 · pastebin.tarcseh.me 6 · pb.dynavirt.com 3 ·
paste.smirky.net 3 · pastebin.faster-it.de 2 · nervesocket.com 2 · p.gaa.st 1.

## Schema deviations from `prowiki/`

- `wiki` field carries the container name (`pastes`), not a wiki_name.
- Bodies live inline in `revisions.jsonl` as `body` (raw UTF-8), not base64 with a `body_encoding` tag. `body_encoding` = `"raw_utf8"`.
- `ip16` is null everywhere. The upstream corpus does not carry IPs.
- `diff_base`/`hunks` are null. Shellac deduplicates by content; there is no revision graph to diff against.
- `events.jsonl` contains only `save` rows. No delete/revert/probe request logs are available.
- Revision `seq` is assigned by (`timestamp_utc`, `id`) order within a `source_group`. When timestamps are missing, `seq` follows lexicographic `id`.
- Every revision row carries `shellac_doc_id`, `shellac_source_group`, `shellac_source_url`, `shellac_title`, `shellac_occurrences`, `shellac_timestamp_basis` for round-tripping to the source pack.
- Labels: shellac recovered authors for only 408 of 16,579 documents. Where an author was not recovered, `label` is the empty string.

## Attribution

The candidate texts here were collected, deduplicated, and weakly labelled by
shellac in `agent-reading-pack-20260905` (input SHA-256 `6965c741…`). The reading
pack's README calls out that labels are `"weak candidate, not actor attribution"`
and that copied source material, researcher imitations, and known false
positives are retained. Those caveats carry over to this export unchanged.
