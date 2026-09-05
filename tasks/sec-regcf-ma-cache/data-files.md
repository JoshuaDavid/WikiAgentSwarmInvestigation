# Data files and URL patterns

The 8-hour burst caches four underlying files. Each file is served from many
distinct hosts because sandbox agents cannot reach `sec.gov` directly and
must relay through no-login third-party services. None of the relay
services listed below are agent-built. Every one is a pre-existing public
tool. See [../../analyses/emergence/README.md](../../analyses/emergence/README.md)
for the reason the swarm converges on public tools rather than building
its own.

Counts below are URL-string occurrences inside the bodies of
`agent-logs/prowiki/revisions.jsonl` revisions that also mention
`regCF` / `us-ma-` / `county.json`.

## 1. `sec.gov/files/county.json`  (the actual data)

The SEC's Regulation Crowdfunding county file. Three per-year arrays
(`regCF_county_2019`, `_2020`, `_2021`) plus `regCF_county_methodology`
and `regCF_county_filters`. Total corpus references: **31,525**.

| URL instances | Category | Representative pattern |
|---:|---|---|
| 14,341 | jq-over-HTTP wrapper | `https://jqp.vercel.app/api/v0?url=<X>&jq=<Y>` where `<X>` is any of the endpoints below |
| 11,332 | Direct SEC | `https://www.sec.gov/files/county.json` |
| 7,946 | Markdown-reader proxy | `https://md.succ.ai/https://www.sec.gov/files/county.json` |
| 4,928 | AllOrigins proxy | `https://allorigins.hexlet.app/raw?url=https%3A%2F%2Fwww.sec.gov%2Ffiles%2Fcounty.json` |
| 1,970 | Jina reader proxy | `https://r.jina.ai/https://www.sec.gov/files/county.json` |
| 1,355 | SEC's own mirror | `https://www.investor.gov/files/county.json` |
| 1,326 | markdown.new reader | `https://markdown.new/www.investor.gov/files/county.json` |
| 480 | Generic CORS-bypass proxies | `https://api.cors.lol/?url=https%3A%2F%2Fwww.sec.gov%2Ffiles%2Fcounty.json` |
| 402 | Scrape-API playground | `https://webcrawlerapi.com/api/playground/content?url=https%3A%2F%2Fwww.investor.gov%2Ffiles%2Fcounty.json` |
| 599 | Other markdown/reader proxies | `https://md.dhr.wtf/?url=...`, `https://pure.md/...` |
| 139 | Google Translate proxy | `https://www-sec-gov.translate.goog/files/county.json?_x_tr_sl=auto&_x_tr_tl=en` |
| 71 | Proxymule | `https://www.proxymule.com/__PROXY__/https/www.sec.gov/files/county.json` |
| 40 | Vanderbilt URL shortener | `https://vanderbi.lt/maallraw260618?source=https%3A%2F%2Fwww.sec.gov%2Ffiles%2Fcounty.json` |
| 27 | Wayback Machine | `https://web.archive.org/web/20250201000000id_/https://www.sec.gov/files/county.json` |
| 24 | lemino.ai url-to-markdown | `https://platform.lemino.ai/api/url2md/https%3A%2F%2Fwww.sec.gov%2Ffiles%2Fcounty.json` |
| ~200 | Path-canonicalization probes | `https://www.sec.gov//files//county.json`, `https://www.sec.gov/foo/../files//county.json`, `https://www.sec.gov/Files/county.json`, `https://www.sec.gov:443/files/county.json`, `https://sec.govwayback.com/files/county.json` |
| ~140 | SEC's true underlying static path | `https://www.sec.gov/sites/default/files/county.json` (Drupal source), sometimes with `?_format=json` |

**Distinct hosts serving `county.json`: 33.** The long tail includes
`thingproxy.freeboard.io`, `api.codetabs.com/v1/proxy`, `cors.hypnguyen.workers.dev`,
`cors.isomorphic-git.org`, `proxy.corsfix.com`, `cf-cors.findme-19.workers.dev`,
`api.allorigins.win`, `httpbin.org/redirect-to`, `docs.google.com/viewer`,
`jsonformatter.curiousconcept.com`, `codebeautify.org/jsonviewer`.

## 2. `sec.gov/files/regcf.json`  (alias / companion, treated identically)

An adjacent SEC file. The corpus provides no evidence its schema differs
from `county.json` — agents apply the same `regCF_county_*` jq
expressions to it. Corpus references: **1,342**. Treated as a
fallback URL, not a distinct dataset.

| URL instances | Category | Representative pattern |
|---:|---|---|
| 814 | Direct SEC | `https://www.sec.gov/files/regcf.json` |
| 322 | Markdown-reader proxy | `https://md.succ.ai/https://www.sec.gov/files/regcf.json` |
| 113 | SEC's own mirror | `https://www.investor.gov/files/regcf.json` |
| 37 | Jina reader | `https://r.jina.ai/https://www.sec.gov/files/regcf.json` |
| 34 | markdown.new | `https://markdown.new/www.sec.gov/files/regcf.json` |
| 20 | pure.md | `https://pure.md/https://www.sec.gov/files/regcf.json` |
| 2 | Google Translate | `https://www-sec-gov.translate.goog/files/regcf.json` |

**Distinct hosts: 7.**

## 3. `sec.gov/modules/custom/sec_custom_blocks/js/oasb_raising_capital_map/main.js`  (the SEC map JS)

The JavaScript that renders the SEC's "Funds Raised Through Crowdfunding"
map. Agents fetch it because it contains (a) the display-formatting
function `formatNumber` and (b) a baked-in FIPS-to-county-name lookup
that is more compact than the Highcharts geo.json. Corpus references: **1,137**.

| URL instances | Category | Representative pattern |
|---:|---|---|
| 584 | Direct SEC | `https://www.sec.gov/modules/custom/sec_custom_blocks/js/oasb_raising_capital_map/main.js` |
| 219 | investor.gov mirror | `https://www.investor.gov/modules/custom/sec_custom_blocks/js/oasb_raising_capital_map/main.js` |
| 151 | md.succ.ai | `https://md.succ.ai/https://www.sec.gov/modules/custom/sec_custom_blocks/js/oasb_raising_capital_map/main.js` |
| 56 | md.succ.ai (investor mirror) | `https://md.succ.ai/https://www.investor.gov/modules/custom/.../main.js` |
| 29 | Jina reader | `https://r.jina.ai/https://www.investor.gov/modules/custom/.../main.js` |
| ~50 | Various proxies with cache-busting query strings (`?v=1.2`, `?_format=html`, `?abc=88997`, `?x`) | `https://www.sec.gov/modules/custom/sec_custom_blocks/js/oasb_raising_capital_map/main.js?v=1.2` |

The `oasb` in the path is the SEC's Office of the Advocate for Small
Business Capital Formation.

## 4. `code.highcharts.com/mapdata/countries/us/us-ma-all.geo.json`  (MA county polygons + names)

Highcharts' polygon file for Massachusetts counties. Used as a
name-and-FIPS lookup (features `us-ma-001..us-ma-027` map to
`Barnstable..Worcester`). Corpus references: **450**.

| URL instances | Category | Representative pattern |
|---:|---|---|
| 444 | Direct Highcharts CDN | `https://code.highcharts.com/mapdata/countries/us/us-ma-all.geo.json` |
| 3 | Reader proxies over Highcharts | `https://md.succ.ai/https://code.highcharts.com/mapdata/countries/us/us-ma-all.geo.json` |
| 2 | GitHub raw mirror | `https://raw.githubusercontent.com/highcharts/map-collection-dist/master/countries/us/us-ma-all.geo.json` |

**Distinct hosts: 3.** Much narrower than `county.json` because
`code.highcharts.com` responds successfully to sandbox requests, so
agents rarely bother with a proxy.

## Duplication summary

- **17,074** jqp-wrapped URLs targeting `county.json` in the wiki
- **2,781** distinct raw URL strings among those
- **1,293** distinct jq expressions after normalising whitespace
- **1,829** distinct `(target_root, jq_expr)` semantic pairs
- **~13×** average redundancy at the jq-expression level

The three canonical "get all MA counties for year Y" queries alone
account for 4,413 of the 17,074 jqp URLs (26 percent). The next tier —
same query wrapped in `{code, usd, thousands: (.usd/1000)}` — accounts
for another 948. Nearly every remaining variant is either a whitespace
difference, a jq-argument reordering, a proxy-layer reshuffle, or an
addition of a cache-busting query string.
