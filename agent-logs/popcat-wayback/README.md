# popcat-wayback

Wayback Machine scrape of the compromised `url.popcat.xyz` shortener's public
`/info` pages, filtered to the OpenAI-related subset.

## What is here

119 short_codes on `url.popcat.xyz`, one page and one revision each:

- Two whose destination is a **ChatGPT conversation URL**
  (`5vtSk2RG2f` and `IRZTIxDlZ`, both aliasing
  `https://chatgpt.com/c/69da0686-9680-8321-ae7c-4aafe7e3f2f4`, both created
  2026-04-11).
- 117 with the `oai*` / `OAI*` naming convention typical of the swarm.
  Destinations are agent-typical data endpoints: `httpbin.org/base64/…`
  (base64-encoded HTML "CBS packs"), `search.projectarclight.org`
  (silent-era film journal queries), `datasets.cbs.nl` OData,
  `md.succ.ai` and `markdown.new` markdown proxies, `login.max.gov`
  SF133 budget attachments, `api.usaspending.gov`, `atlas.ecdc.europa.eu`,
  `veriportali.tuik.gov.tr`. No other chat-service destinations.

## Provenance

- `scrape/popcat_wayback.py` — reproducible scraper (Wayback listing
  `url.popcat.xyz/?page={1..9}` on 2026-09-08, then the earliest archived
  `/<code>/info` for each openai-flagged code).
- `analyses/popcat-wayback-openai-extract/write_export.py` — turns the
  scrape outputs into this directory.

## Schema

Follows `agent-logs/shorteners/` (the shellac reading-pack shape). One
`page_id` per `short_code`, one `revision` per `/info` snapshot, one
`save` event per revision, one label row covering everything.

`revisions.jsonl` adds six fields beyond the shorteners schema:

| Field | Meaning |
|---|---|
| `wayback_timestamp` | Wayback capture stamp (`YYYYMMDDHHMMSS`) |
| `wayback_url` | Fully-formed `web.archive.org/web/{ts}id_/https://url.popcat.xyz/{code}/info` |
| `popcat_redirects_to` | Destination URL parsed from the `/info` page |
| `popcat_total_views` | Click count at capture time |
| `popcat_days_active` | Days between creation and capture |
| `popcat_created_date` | Redirect creation date (ISO from `DD/MM/YYYY` on the page) |

`time` on each revision is the Wayback capture time (ISO-8601 UTC). This
is not the creation time of the redirect and not the time any specific
agent viewed it. `popcat_created_date` is the field that reflects when
the short_code was minted.

## Excluded

9 openai-flagged short_codes on the same listing have no Wayback `/info`
capture at any date and are omitted:

```
oaibridge806, oaibritvarnarrow51, oaiengpack0, oaiengpack14, oaiengpack7,
oaiindbritv1906110, oaiindwelshn1906110, oaimarkbritvar92, oaitestnew90
```

All match the naming pattern of the included set (more CBS packs,
projectarclight variants, markdown proxies). They can be recovered from
live `url.popcat.xyz` if wanted; this export intentionally sticks to
Wayback-preserved data.

## Overlap with `agent-logs/shorteners/popcat/*`

The existing `shorteners/popcat/{1..10,18}` (11 pages, 230 revisions,
214 distinct short_codes) came from shellac's reading pack. Shellac
numbered pages ordinally (`popcat/1`, `popcat/2`, ...); this corpus keys
by the actual short_code (`popcat-wayback/oaixlsx2`, ...), so the two
corpora do not collide.

They partially overlap on short_codes but capture different snapshots:

- `xmrPKH9h8C7 → chat.openai.com/c/79265c91-…` — in shellac only
  (not on Wayback listing pages 1–9 for 2026-09-08).
- `5vtSk2RG2f`, `IRZTIxDlZ → chatgpt.com/c/69da0686-…` — here only
  (not captured by shellac).
- Most `oai*` data-fetch codes appear in both, but shellac's timestamps
  are undated while this corpus's `time` is the Wayback capture time.

## Limitations

- One `/info` snapshot per code — not a time-series of clicks.
- No author, no IP, no request log — `/info` is a public metadata page
  that exposes only the destination + counters.
- Snapshot dates vary from 2026-05 to 2026-09 depending on which capture
  the CDX call returned first. Click counts are the value at that moment
  and are not comparable across codes without checking the age.
- The filter is deterministic and selects with high precision, but swarm
  codes not starting with `oai` and not pointing at an OpenAI host are
  excluded (they would need a broader filter or subagent classifier).
