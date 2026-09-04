# scrape

Repeatable scrapers for the wikis whose telemetry we're analyzing. Each script
takes CLI args, is idempotent (deletes and rewrites the output dir), and has a
sanity-check mode that hits the network minimally so you can verify parsing
before pointing it at a whole farm.

## `wikiservice_scrape.py`

Scrapes any ProWiki-engine (UseModWiki-derived) public wiki into an
`agent-logs/<name>/` export that mirrors `agent-logs/prowiki/` as much as the
public interface allows. Verified against
`https://www.wikiservice.at/user/milk/wiki.cgi`; ~50 other wikis on the
`wikiservice.at` farm use the identical engine.

### What it captures

| Source URL | What it gives us |
|---|---|
| `?action=browse&id=RecentChanges&days=N&all=1` | One HTML `<li>` per revision within the window: page name, HH:MM wall time, editor label, `[edit summary]` bracket, NEW / Minor markers. |
| `?action=browse&id=RecentChangesRss&days=N` | RSS feed with second-accurate ISO timestamps (with TZ offset), wiki revision numbers, dc:creator, description. RSS is capped at ~N most recent items across the wiki. |
| `?<PageName>` (or `?action=browse&id=<PageName>`) | Current rendered HTML of each page. We strip it to plain text; raw URLs survive. |
| `?action=browse&diff=4&id=<PageName>` | Head-to-previous diff. We parse each `<strong>Op: A,BcC,D</strong>` marker into a hunk with `removed_text` (yellow table) and `added_text` (green table). |

### What it can't capture (admin-gated on this engine)

- `action=log` / `action=archive` — full history for one page.
- Raw wiki source (no `raw=1` mode; no accessible edit textarea for anon).
- Revision bodies older than N-1 (only the head body and the head-to-previous
  diff survive without admin access).
- IPs / request-level metadata.

All of these limitations are recorded in the output's `manifest.limitations`
list so downstream analyses don't silently assume this data exists.

### Usage

```bash
# Sanity check: hit RC + RSS + at most 2 page bodies + 2 diffs, print a
# summary, DO NOT write any files. Do this before pointing at all 50 wikis.
python3 scrape/wikiservice_scrape.py \
    --base https://www.wikiservice.at/user/<slug>/wiki.cgi \
    --name <slug> \
    --sanity

# Full scrape into agent-logs/<slug>/
python3 scrape/wikiservice_scrape.py \
    --base https://www.wikiservice.at/user/<slug>/wiki.cgi \
    --name <slug>

# Custom window / output dir / request pacing:
python3 scrape/wikiservice_scrape.py \
    --base https://www.wikiservice.at/user/<slug>/wiki.cgi \
    --name <slug> \
    --days 365 \
    --out agent-logs/<slug> \
    --sleep 2.0
```

### Batching across 50 wikis

There's no batch runner yet — write a shell loop when you have the list:

```bash
while read slug; do
    python3 scrape/wikiservice_scrape.py \
        --base "https://www.wikiservice.at/user/$slug/wiki.cgi" \
        --name "$slug" \
        --sanity 2>&1 | grep -E 'unique pages|rc rows'
done < wikis.txt
```

Then rerun without `--sanity` on the ones that look sensible. `--sleep 2` is
polite for a shared host; drop to `--sleep 0.5` only if the operator confirms.

### Output layout

Identical to `agent-logs/prowiki/`: `pages.jsonl`, `revisions.jsonl`,
`events.jsonl`, `labels.jsonl`, `manifest.json`, `SHA256SUMS`. Fields that
can't be populated from the public HTML are `null`. New fields specific to
this export (not in prowiki):

- `revisions.jsonl.wiki_revision_number` — engine's own revision counter, from RSS.
- `revisions.jsonl.body_availability` — `head_only` or `metadata_only`.
- `revisions.jsonl.is_new_page`, `is_minor_edit` — from RC markers if present.
- `pages.jsonl.wiki_head_revision_number` — same, for the head.
- `manifest.wiki_tz_offset` — derived from RSS dc:date; RC-fallback rows use it.
