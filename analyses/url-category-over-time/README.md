# url-category-over-time

Stacked area chart: URL occurrences per UTC day, grouped by category. One
polygon per category; hues are shared within a functional group (own-wiki,
proxies, data sources, archive/storage, obfuscation/test) and lightness
distinguishes categories within the group.

## Vocabulary

| Term | Meaning |
|---|---|
| URL occurrence | One `http(s)://` string in one revision body. From `analyses/urls/outputs/urls-classified.jsonl`. |
| category | The upstream classifier's label — 20 distinct values, e.g. `wiki_self`, `jq_json_relay`, `fetch_proxy_markdown`, `data_source_sec_investor`. |
| group | A hand-picked bundle of related categories that share a hue in the chart. See `CATEGORY_GROUPS` in `build_and_plot.py`. Five groups. |

## Files

| File | What it holds |
|---|---|
| `build_and_plot.py` | Reads `analyses/urls/outputs/urls-classified.jsonl`. Writes both outputs. |
| `outputs/urls_by_date.tsv` | `date`, `category`, `occurrences`. One row per (date, category) with a non-zero count. 203 rows. |
| `outputs/urls_stacked_area.svg` | The stacked-area chart. Legend at right lists each group and its categories, top-of-stack first. |

## Notes on scale

- Total URL occurrences: 115,855 across the export.
- Peak day (2026-06-18) has ~40k URL occurrences. That is the same day the
  overall revision counts spike; unsurprising because URL-per-revision is
  roughly stable.
- The `own wiki` (`wiki_self`) band is often the tallest single slice on
  quieter days. Agents cite the wiki itself to signal state to peers.
- The red/orange band (`jq_json_relay`, `fetch_proxy_markdown`, `cors_proxy`)
  is the tool-use signature: agents fetching arbitrary URLs through a
  third-party proxy that returns markdown or JSON.

## Rerun

```
python3 analyses/url-category-over-time/build_and_plot.py
```
