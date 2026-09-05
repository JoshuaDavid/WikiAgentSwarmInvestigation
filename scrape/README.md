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

## `dse.py`

Fork of `wikiservice_scrape.py` for `https://www.wikiservice.at/dse/wiki.cgi`,
which serves the ProWiki engine's STANDARD skin rather than the user-farm
skin. Differences from the parent:

- Content region: no `<td class="content">` wrapper; content sits between the
  first `<hr>` and the last `<hr>` inside `<body>`.
- Date headers: German long form, e.g. `4. September 2026` (day-first, month
  name, no comma). The parser also accepts English month names.
- Diff markers: German — `Hinzugefügt` (Added), `Gelöscht` (Deleted),
  `Verändert` (Changed). Mapped to `added` / `deleted` / `changed` in the
  output.
- Deletion / never-existed detection: browsing a deleted page returns a stub
  body `created`; browsing a never-existed page returns
  `Beschreibe hier die neue Seite.`. Both are detected and mark
  `body_availability='deleted_or_404'` on the head row, and set
  `pages.jsonl.deleted_live=true`.

The corpus is large (~22k revs across ~3.9k pages), so the scraper adds two
CLI flags:

- `--body-strategy {metadata_only, head_pages_bounded, all}` — pick which
  head bodies to fetch. Default is `metadata_only` (RC + RSS only).
- `--body-limit N` — cap for `head_pages_bounded` (default 200). Pages are
  selected by newest first-seen in RC.

Skipped-head rows get `body_availability='not_fetched_size_budget'`, and the
manifest records the chosen strategy in `manifest.body_strategy`.

## `fractal.py`

Fork of `wikiservice_scrape.py` for `https://www.wikiservice.at/fractal/wiki.cgi`.
Fractal runs the same ProWiki engine as milk but ships the STANDARD skin (no
`<td class="content">` wrapper). Differences from the parent:

- Content region: content lives inside the sole `<td valign="top">` cell
  after the sidebar. The parser stops at the footer row
  (`</td></tr><tr><td>&nbsp;</td>`).
- Date headers: English on the current template
  (`September 5, 2026`); a German fallback (`5. September 2026`) is accepted
  in case the wiki's locale flips.
- Time cells: leading zero on the hour is omitted (`2:59`, not `02:59`). The
  time regex accepts 1-2 digit hours; RC-vs-RSS matching zero-pads before
  comparing.
- Anonymous editors: rows without an editor anchor emit a bare `IP#N`
  string as the label. The parser reads the trailing text after the
  ` . . . . . ` separator.

Same CLI as the parent; call with
`--sleep 3.0` when other ProWiki agents are running concurrently.

## `apchem.py`

Scrapes an upstream **UseModWiki 1.0** public wiki (not the ProWiki fork).
Verified against `https://tmcleod.org/cgi-bin/apchem/wiki.cgi`.

Differences from `wikiservice_scrape.py`:

- **No RSS on this engine.** `action=rss` returns `Invalid action parameter rss`.
  All timestamps are minute-precision RC wall clock; every row gets
  `uncertainty_seconds=60`. `wiki_tz_offset` is derived by comparing the
  `from=<unix_ts>` link embedded in RC to the wall-clock caption next to it.
- **Raw wiki source is available** via `action=edit&id=<Page>` for any anon
  visitor. Head bodies are raw source, not HTML-stripped renderings
  (`body_encoding="wiki_source_utf8"`). KeepFile-preserved old revisions get
  their raw source via `action=edit&id=<Page>&revision=N`.
- **Labels come from `action=history`**, not RC. RC does not expose IPs on
  this engine. IPs are engine-redacted to the first three octets (e.g.
  `4.227.3.xxx`).
- **`action=history` only preserves the head + one KeepFile-major old
  revision per page.** Older in-window revisions carry `label=null`,
  `wiki_revision_number=null`, `body_availability="metadata_only"`.
- **Times are 12-hour AM/PM.**
- **HTML shell is plainer.** Body content sits between `<hr>` markers, not in
  a `<td class="content">` wrapper. `<li>` tags are unclosed; the row parser
  splits blocks on `<li>` tokens.

Usage:

```bash
python3 scrape/apchem.py \
    --base https://tmcleod.org/cgi-bin/apchem/wiki.cgi \
    --name apchem \
    --days 150 \
    --sleep 1.5
```
