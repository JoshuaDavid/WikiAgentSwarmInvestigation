# Paste-site coverage summary

Status of the 20 hosts the user asked us to run the k4be/linuxiarz pipeline
on, plus the two that were done in earlier passes.

Compiled 2026-09-07 after the overnight batch run.

## Exports produced

Each host below has `agent-logs/<name>/` with the usual layout
(`revisions.jsonl`, `pages.jsonl`, `events.jsonl`, `labels.jsonl`,
`manifest.json`, `SHA256SUMS`, `README.md`).

| Host | Route | Revisions | Swarm | Unclear | Human (excluded) | Notes |
|---|---|---:|---:|---:|---:|---|
| `pastebin-k4be` (prior) | live_stikked_lists | 198 | 51 | 21 | 124 | Reference host. PadBot/TEL/TK series, EPL bench task, `stikked_replyto_chain` diff-base surfaced. |
| `paste-linuxiarz` (prior) | wayback_view | 381 | 81 | 81 | 31 | `agent-XXXX` handles, IDPH thyroid-cancer `Iowa*` bench task, `Perceptual Zephyr` recruiter. |
| `anna.fyi` | live_stikked_lists | 103 | 26 | 14 | 40 | **Biggest new swarm surface.** OAI-\d{5}, Bridge/Transfer smoke tests, `hermes_walker`, YouTube watch_videos bulk, tmpfiles.org relay. |
| `pastebin.tarcseh.me` | live_stikked_lists | 23 | 7 | 10 | 366 | Hungarian MTA:SA roleplay community + `incompultrusion.com` SEO. `collusion.wiki` and RSA-JWK-`kid:evil` surfaced. Discord token in one paste redacted from batch file. |
| `pb.dynavirt.com` | live_stikked_lists | 8 | 2 | 3 | 45 | `public-board.com` ads under color+animal handles. Otherwise real `PryMar56` sysadmin content. |
| `pastie.iem.at` | live_stikked_lists | 7 | 0 | 7 | 24 | IEM Graz Pure Data community. Recurring real handles `IOhannes m zmölnig`, `Ben Wesch`, `ClaudiusMaximus`. Handle `Claude` (probably a real person) on pid `c8a687e1`. |
| `paste.lightcast.com` | wayback_view | 7 | 0 | 7 | 360 | Vietnamese/Asian gambling-affiliate SEO farm. No swarm. |
| `paste.smirky.net` | live_stikked_lists | 4 | 1 | 0 | 3 | `Baby Echidna` advertises `public-board.com`. |
| `pastebin.faster-it.de` | live_stikked_lists | 4 | 2 | 0 | 1 | `agent-80085` "Kill all humans" + IowaCollab. `collusion.wiki` mentioned. |
| `pastebin.freepbx.org` | wayback_view (200/2287 sample) | 13 | 0 | 13 | 187 | FreePBX/Sangoma telephony community + carding spam. No swarm task series. |
| `paste.steamr.com` | live_stikked_lists | 36 | 0 | 3 | 136 | UCalgary sysadmin `leo/lleung`. No swarm. |
| `p.gaa.st` | live_stikked_lists | 1 | 0 | 0 | 72 | BitlBee developer's personal instance. No swarm. |
| `paste.centos.org` | wayback_view (200/2766 sample) | 0 | 0 | 0 | 200 | CentOS/Fedora sysadmin instance. Keyboard-mash test titles + real diagnostic pastes. No swarm. |
| `pb.psychotic.ninja` | wayback_view | 0 | 0 | 0 | 3 | Only 3 archived pids. Xen-on-AlmaLinux install transcripts, 2021. |

**Totals (this batch, 12 new hosts):** 206 revisions, 38 subagent-verdict swarm, 57 unclear, 1,437 excluded human.

## Documented + skipped

| Host | Reason |
|---|---|
| `paste.jamesdooley.us` | Only 1 Wayback `/view` snapshot, and it is a Cloudflare captcha placeholder page. |
| `flynnos.org` | Not a paste site — root is a "virtual worlds" project page. |
| `paste.ie` | Live `/lists` is 33KB of PHP deprecation warnings (post-PHP-8.1 stikked broke). Wayback CDX has zero `/view/*` snapshots. |
| `paste.evervolv.com` | CodeIgniter cookie, older stikked variant. Live `/view` and `/view/raw` return empty content or time out. |
| `expaste.com` | PasteShr engine, not stikked. Would need a bespoke parser. |
| `paste.nyigc.net` | `/api` returns "The API has been disabled". No Wayback `/view/*` coverage. |
| `securityuniversal.com` | `/api/random` returns empty body. No Wayback `/view/*` coverage. |

## Cross-host swarm meta-URLs (confirmed on multiple hosts)

| URL | Advertised by | Seen on |
|---|---|---|
| `thecolony.ai/for-agents` | `CentaurAgent`, `Perceptual Zephyr` | k4be, linuxiarz |
| `public-board.com` (+ `/llms.txt` protocol page) | `Baby Echidna`, `field-notes`, various color+animal handles | k4be, smirky, dynavirt, tarcseh |
| `collusion.wiki` | `field-notes` | tarcseh, faster-it.de |
| `tmpfiles.org/dl/*.apk` | `OpenAI`, `build`, `human_request` | anna.fyi (HomeRun package 1.1.0) |

## New task-family / signal candidates surfaced during this batch

- **Iowa Department of Public Health thyroid-cancer task** with Q1..Q9
  rounds and "85 and Older" sub-question. IDPH Tableau CSV links.
  Confirmed on linuxiarz + faster-it.de.
- **OAI-\\d{5}** numbered handles paired with `Statistical reference N`.
  Only on anna.fyi so far.
- **Bridge/Transfer smoke tests**: `BIG5_XFER_YYYYMMDD_NNN_TEST`,
  `NT20 Bridge YYYYMMDD hhhh`, `GMOS RC003 ANNA BRIDGE YYYYMMDD`,
  `ZZZ Transfer Test`, `golf-transfer-test`. anna.fyi cluster.
- **LINKTARGETANNA / LINKANNATARGET** cross-host linking markers.
- **`hermes_walker` / `Hermes (open agent runtime)`** meta-narrative
  handle claiming human-directed provenance.
- **YouTube `watch_videos?video_ids=<50-comma-separated>`** bulk lists
  as URL-fetcher probe payloads.
- **`testvar` + literal-CRLF-encoding probe** (paired pastes on anna.fyi,
  same second, escape-encoding variants).
- **`Bot1..Bot7`** numbered bots with `Filler` titles on linuxiarz.
- **`38b5` cohort** with `38b5coord`, `38b5reply`, `hello-38b5-<ts>`
  bodies. Linuxiarz + tarcseh.
- **`agent-80085` "Kill all humans"** meme-appendix on faster-it.de.
- **Duplicate-relay** of byte-identical LLM essays across
  color+animal handles within the same second. `DE MYSTERIOSO VEHICULO`,
  `Alchemical breakdown`. k4be + tarcseh (with false-positive risk on
  pre-2024 MTA:SA cheat-code sharing).
- **`attrinj` title + `<a href="…"` in the `name` field** — attribute-
  injection / XSS probes against stikked's author rendering. tarcseh.
- **RSA JWK with `"kid":"evil"`** — potential JWKS-forgery smoke test.
  tarcseh pid `73e31949`.
- **`bullfincher.io/sec-proxy`** — new swarm CORS proxy alongside the
  existing `jqp.vercel.app`, `pure.md`, `md.succ.ai`, `2md.link` set.

## Host-level negative baselines (useful for future subagents)

- **Vietnamese/Asian gambling-brand SEO** dominates
  `paste.lightcast.com` and appears on `paste.centos.org`,
  `pastebin.freepbx.org`. Brand naming patterns: `Nhà Cái <BRAND>`,
  `<BRAND>88`, `<BRAND>777`, `<BRAND>Club`. Reply handles echo the
  brand (`rr88law`, `789clubjpnet`).
- **`incompultrusion.com` FRP-composite backlink burst** on
  `pastebin.tarcseh.me` — 100+ rapid-fire color+animal handles walking
  the vendor sitemap. Superficially resembles duplicate-relay; distinguish
  by the 1:1 title-to-URL-slug shape and no swarm vocabulary.
- **FreePBX `Automatic Pastebin from FreePBX Distro N`** posts under
  `root@freepbx-*` handles are a documented FreePBX feature, not swarm.
- **`disqus.com` as an author** posting Disqus CDN JS bundle files is
  benign automation.
- **Hungarian MTA:SA in-game logs** on `pastebin.tarcseh.me` are 2020-2022
  human roleplay community content, well pre-swarm.

## Recommendation

The three swarm meta-URLs (`thecolony.ai/for-agents`, `public-board.com`,
`collusion.wiki`) are the coordination surfaces the swarm itself points
new agents at. If any are still live and reachable, they are the
highest-leverage next scrape targets.
