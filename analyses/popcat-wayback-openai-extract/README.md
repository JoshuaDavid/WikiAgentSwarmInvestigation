# popcat-wayback-openai-extract

Extract step that turns `scrape/outputs/popcat-wayback/` into
`agent-logs/popcat-wayback/`, matching the `agent-logs/shorteners/` schema.

## Vocabulary

| Term | Meaning |
|---|---|
| `short_code` | The URL-path segment on `url.popcat.xyz` that identifies one redirect (e.g. `oaixlsx2`, `IRZTIxDlZ`). |
| `/info page` | The public metadata page at `https://url.popcat.xyz/<code>/info` — destination URL, click count, days-active, created date. |
| `openai-flagged` | A `short_code` whose destination matches `chat\.openai\.com|chatgpt\.com|openai\.com|api\.openai|platform\.openai`, OR whose code starts with `oai`/`OAI`. Deterministic filter — no subagent verdict is used because the naming convention alone identifies swarm-authored codes. |
| `body` | For each stored revision, the five-line block echoing what the popcat `/info` page shows: `destination\ndestination\n<code>\n/<code>/info\n<click_count>`. Matches the body shape used by `shorteners/popcat/*` in shellac's reading pack. |

## Pipeline

1. `scrape/popcat_wayback.py` (in the `scrape/` tree, not here) fetches
   Wayback listings of `url.popcat.xyz/?page={1..9}` for 2026-09-08, applies
   the deterministic OpenAI filter to yield 128 candidate `short_code`s,
   then fetches the earliest archived `/info` page for each. Output:
   `scrape/outputs/popcat-wayback/{listing_rows,openai_rows,info_cdx,info_parsed}.jsonl`
   plus `listing/` and `info_pages/` HTML.

2. `write_export.py` reads those files and writes
   `agent-logs/popcat-wayback/{manifest.json,pages.jsonl,revisions.jsonl,
   events.jsonl,labels.jsonl,SHA256SUMS}`. One `page` and one `revision`
   per short_code (there is only one `/info` snapshot per code in this
   pass).

There is no subagent classify step. The filter is deterministic and the
selected set is small enough to inspect by eye.

## Coverage

- 128 openai-flagged short_codes on listing pages 1–9 (2026-09-08).
- 119 have a Wayback `/info` capture → full body available.
- 9 have no Wayback capture at any date → excluded from the export.
  Full list in `scrape/outputs/popcat-wayback/info_missing.txt`. Live
  fetch on `url.popcat.xyz` would resolve them if wanted.

## Overlap with `agent-logs/shorteners/popcat/*`

The existing `shorteners/popcat/1..10,18` (11 pages, 230 revisions,
214 distinct short_codes) came from shellac's reading pack and used
shellac's ordinal `page_id`s (`popcat/1`, `popcat/2`, ...). This export
uses the actual short_code as the page name (`popcat-wayback/<code>`) so
there is no key collision, but the two corpora overlap on some codes —
most notably `xmrPKH9h8C7` → `chat.openai.com/c/79265c91-…` which lives
in the shellac dump only, and the two ChatGPT-linked codes here
(`5vtSk2RG2f`, `IRZTIxDlZ`, both aliasing the same conversation
`chatgpt.com/c/69da0686-…`) which shellac did not capture.

## Usage

```bash
# From repo root:
python3 analyses/popcat-wayback-openai-extract/write_export.py
```

Idempotent. Rerun deletes and rewrites `agent-logs/popcat-wayback/`.
