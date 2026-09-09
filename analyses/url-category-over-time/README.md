# url-category-over-time

Stacked bar chart: URL occurrences per UTC day, one segment per host, colored
by the host's category. Sources: `prowiki`, `pastes`, `gems`.

## Vocabulary

| Term | Meaning |
|---|---|
| URL occurrence | One `http(s)://` string in one revision body. From `analyses/urls/outputs/urls-classified.jsonl` (which now covers `prowiki`, `pastes`, and `gems`). |
| host | The lowercased hostname of one URL, e.g. `wikiservice.at`. There are 275 distinct hosts in the corpus. |
| category | Upstream classifier label — 20 functional buckets (`wiki_self`, `jq_json_relay`, `fetch_proxy_markdown`, `data_source_sec_investor`, …). Every segment in a bar is colored by its host's category. |
| window | 2026-05-01 → last dated URL (2026-09-04). Rows with a null timestamp or a date before the window are reported in the legend as "+N pre-window" per category. |

## Chart design

- **X-axis:** one bar per UTC date in the window. Bars are the same width; missing days show as gaps.
- **Y-axis:** URL occurrences per day, linear.
- **Segment ordering (bottom → top of each bar):** category rank first (`wiki_self`, then the proxy/relay categories, then the data-source categories, then archive/storage, then obfuscation/test); within a category, hosts are sorted by their in-window total, largest at the bottom of the color band.
- **Colors:** one color per category (20 total). Two hosts in the same category share the same color. Legend at the right lists categories with in-window URL count, distinct host count, and pre-window count (if any).
- **Peak day:** 2026-06-18 carries ~95k of the ~116k in-window URL occurrences and dominates the y-axis; other days are visible as short bars near the baseline. Hover over any segment to see the exact host and count.

## Files

| File | What it holds |
|---|---|
| `build_and_plot.py` | Reads `analyses/urls/outputs/urls-classified.jsonl`. Writes both outputs. |
| `outputs/urls_by_date_host.tsv` | `date`, `category`, `host`, `occurrences`. One row per (date, category, host) in the window with a non-zero count. 611 rows. |
| `outputs/urls_stacked_bar_by_host.svg` | The stacked-bar chart. |

## Rerun

```
python3 analyses/urls/extract.py \
  && python3 analyses/urls/classify.py \
  && python3 analyses/url-category-over-time/build_and_plot.py
```
