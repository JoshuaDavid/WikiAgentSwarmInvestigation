# pastebin-k4be-random

One considerate poll of `https://pastebin.k4be.pl/api/random`. The endpoint
returns a JSON blob for a single random paste on `pastebin.k4be.pl`. We fetch
it 100 times, one call per second, log the full response (headers plus body),
and count how many of the pastes look like they came from the swarm we are
already tracking on this host under `agent-logs/pastes/pastebin-k4be/`.

## Vocabulary

| Term | Meaning |
|---|---|
| `pid` | The paste id returned by the API in the JSON body. Used for dedup. |
| `swarm-suspected` | A response body whose `title` or `raw` field matches a rule in `classify.py`. Rules are drawn from patterns already observed in `agent-logs/pastes/revisions.jsonl` for `pastebin-k4be` sources. |
| `duplicate hit` | A response whose `pid` was already returned by an earlier iteration in the same run. |

## User-Agent

```
Automation (investigating OpenAI agent swarm; contact swarmchasers discord
https://discord.gg/RVUnKefG7 / joshuad93@gmail.com for more info)
```

Both `scrape.py` and this README embed a contact address so the site operator
can reach the researcher if the traffic looks unwanted. The scraper rate is
one request per second, absolute-clock paced so a slow request does not
double up on the next one.

## Files

- `scrape.py` - hits the endpoint N times, writes one JSON line per response
  to `outputs/responses.jsonl` and a run summary to `outputs/run_manifest.json`.
- `classify.py` - reads `outputs/responses.jsonl` and emits
  `outputs/classified.jsonl` (per-row swarm-rule hits) and
  `outputs/summary.md` (counts).
- `outputs/scrape.log` - the stderr progress log from the scrape run.

Rerun the pipeline:

```bash
python3 scrape.py --iters 100 --sleep 1.0
python3 classify.py
```

## Response schema

Each line in `outputs/responses.jsonl` contains:

- `iter`, `request_time_utc`, `elapsed_seconds`
- `status`, `url_final`, `error`
- `headers` - dict of every response header the server returned
- `body_text` - raw response body, decoded utf-8 with replace
- `body_json` - parsed JSON body if it parsed, else null

The API replies with `Content-Type: text/html; charset=UTF-8` but the body is
always a JSON object. Keys in `body_json` include `pid`, `title`, `name`,
`lang`, `lang_code`, `paste` (HTML-rendered), `raw` (plain text), `created`,
`hits`, `url`.

## Concrete example (iteration 17)

```
title: "TEL094629"
name:  "TEL"
raw:   "https://telegra.ph/Test-Link-88990-05-18 CLICKMAYBE 1779094629"
created: 1779094629   (2026-05-14 20:57:09 UTC)
```

This paste fires three swarm rules: `title:TEL\d+`, `body:CLICKMAYBE`,
`body:telegraph_smoke`. The same handle (`TEL`) and the same `CLICKMAYBE`
smoke-test string show up 17 times in `agent-logs/pastes/revisions.jsonl`
for the `pastebin-k4be` corpus.

## Results (100 iterations, run at 2026-09-07 UTC)

- All 100 requests returned HTTP 200 with parseable JSON.
- **85 distinct pids** returned; **15 duplicate hits**.
- **42 of 100** responses matched at least one swarm rule.

### Rule hit breakdown

| Rule | Fires |
|---|---:|
| `title:PAD\d+x` | 22 |
| `body:padbot_id` (`pad-1779\d{9}\.\d+-\d+`) | 22 |
| `title:ROIETA` | 8 |
| `title:TEL\d+` | 4 |
| `body:CLICKMAYBE` | 4 |
| `body:telegraph_smoke` (`telegra.ph/Test-Link`) | 4 |
| `title:URLTEST\d+` | 2 |
| `body:2md_link` (`2md.link`) | 2 |
| `title:RoiEtProvince` | 2 |
| `title:EPL` | 2 |
| `title:TK\d+` | 1 |
| `title:Gsmoke` (`G[a-z0-9]+99$`) | 1 |

Many pastes fire more than one rule at once (the PadBot cluster fires both
its title rule and its body rule on every paste, for example). The
`42 of 100` figure counts unique iterations, not rule fires.

### Duplicates

15 of 100 fetches returned a `pid` we had already seen. 5 of the 13 duplicated
pids are swarm content:

| Copies | Class | pid | Title |
|---:|---|---|---|
| 3 | SWARM | `103d52e5` | `PAD23x249056` |
| 3 | other | `680e2b60` | `Re: Re: Bez tytułu` |
| 2 | other | `1447a531` | `jgjg` |
| 2 | other | `c9b26902` | `Bez tytułu` |
| 2 | other | `2f7f901a` | `Bez tytułu` |
| 2 | other | `18118b20` | `E2ePHEMERA1.3.8` |
| 2 | other | `b24872cc` | `Bez tytułu` |
| 2 | SWARM | `d1ba75fb` | `PAD38x845864` |
| 2 | SWARM | `1fad07cb` | `Roi Et province (TH45) male studies Q2 2013-2021` |
| 2 | other | `c48bbd20` | `Bez tytułu` |
| 2 | SWARM | `eebacb3c` | `PAD7x546917` |
| 2 | other | `0c00d2ff` | `Bez tytułu` |
| 2 | SWARM | `7eca12ef` | `PAD69x227227` |

### Pool-size measurement

`/api/random` is implemented (see the stikked source under `tmp/stikked-src/`
at `htdocs/application/controllers/Api.php:108` and
`htdocs/application/models/Pastes.php:837`) as

```sql
SELECT ... FROM pastes WHERE private = 0 ORDER BY id RANDOM LIMIT 1
```

so its pool is every unexpired non-private paste on the server, with no
recency window and no cache. To measure the pool directly, paginate the
site's own listing at `https://pastebin.k4be.pl/lists/<offset>` (15 pastes
per page). The last page is offset 315 with 7 entries, so the **whole
server currently holds 322 unexpired non-private pastes** (2026-09-07).

Sanity check the sampling. For N=322 and K=100 uniform draws with
replacement,

```
E[distinct] = N * (1 - (1 - 1/N)^100) ≈ 86.1
```

vs. **85 observed**. The sampling really is uniform, and the ~40 percent
swarm share we see in the polled sample is (up to sampling noise) the
swarm share of the entire host.

- 42 of 100 polled fetches match a swarm rule.
- 36 of 85 distinct polled pids match a swarm rule (~42%).
- Extrapolating: roughly `0.42 * 322 ≈ 136` of the 322 pastes on the whole
  site are swarm-produced.
- Our `agent-logs/pastes/pastebin-k4be/` corpus already contains 126 pids,
  so the corpus already covers ~39% of the entire host - most of that
  presumably being the swarm's own output.

## Cross-check against `agent-logs/pastes/pastebin-k4be/`

`cross_check.py` compares the polled `pid`s against the 126 pastebin-k4be
paste ids already captured under `agent-logs/pastes/`. Rerun after every
scrape. Results for this run land in `outputs/cross_check.md`.

Headline numbers for the 2026-09-07 run:

- **41 of 100 fetches** returned a `pid` we already have in `agent-logs/`.
- 35 of the 85 distinct polled pids overlap the corpus.
- 34 of the 36 swarm-classified polled pids are already in `agent-logs/`.
- 2 swarm-classified polled pids are new (`253c38d4` `URLTEST3`,
  `9e601c75` `URLTEST2`). Both are `2md.link/is.gd` shortener smoke tests
  authored under the recurring `CiteTest` name.
- 1 in-corpus pid (`140104ad` title `Artlist`, name `Agent`, body
  `pure.md/lcdl.library.cofc.edu/…`) did not fire any classifier rule.
  Same URL-fetcher smoke pattern as the `G*99` cluster, different label.
  Recorded as a false negative rather than adding a `pure.md/lcdl` rule,
  because the sample size is too small to tune against.

## Caveats

- `classify.py` is a signature matcher trained on the swarm patterns we
  already know. It cannot detect swarm content that uses a signature we have
  not seen yet, and it will mislabel any human paste that happens to hit one
  of these regexes. Both false-positive and false-negative rates are
  unmeasured on this run.
- The "effective pool ≈ 300" estimate assumes uniform sampling. If the API
  weights recent or popular pastes, the true pool is larger and the swarm
  share of the pool is smaller than 40 percent, but the swarm share of the
  visible sample is unchanged.
- A single 100-iteration run is not stable. Rerun to see the numbers wobble.
