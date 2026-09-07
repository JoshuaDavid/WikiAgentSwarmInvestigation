# Paste-site coverage summary

Status of the 20 hosts the user asked us to run the k4be/linuxiarz pipeline
on. Compiled 2026-09-07 during the overnight batch run.

## Live-scraped (stikked, `/lists` + `/api/paste` or `/view/raw` reachable)

Every host below produced `agent-logs/<name>/` with the usual layout
(revisions.jsonl, pages.jsonl, events.jsonl, labels.jsonl, manifest.json,
SHA256SUMS).

| Host | Total pastes | Swarm | Unclear | Human | Notes |
|---|---:|---:|---:|---:|---|
| `anna.fyi` | 143 | 26 | 14 | 40 | Big swarm surface. OAI-\d{5}, Bridge/Transfer smoke tests, hermes_walker, YouTube watch_videos bulk, tmpfiles.org relay. |
| `paste.smirky.net` | 7 | 1 | 0 | 3 | `Baby Echidna` advertises `public-board.com`. |
| `pastebin.faster-it.de` | 5 | 2 | 0 | 1 | `agent-80085` "Kill all humans" + IowaCollab. `collusion.wiki` mentioned. |
| `pb.dynavirt.com` | 53 | 2 | 3 | 45 | `public-board.com` ads; real site owner (`PryMar56`) content otherwise. |
| `p.gaa.st` | 73 | 0 | 0 | 72 | BitlBee developer's personal instance. No swarm. |
| `paste.steamr.com` | 172 | 0 | 3 | 136 | UCalgary sysadmin `leo/lleung`. No swarm. |
| `pastie.iem.at` | 31 | 0 | 7 | 24 | IEM Graz Pure Data community. Handle `Claude` appears on pid `c8a687e1`. No swarm. |
| `pastebin.tarcseh.me` | 389 | pending | pending | pending | Biggest live-scrape host. Classification running. |

## Wayback-only (live site blocks anon access)

The stikked instance is up but `/lists`, `/view/*`, `/api/*` return non-200
for anonymous requests. `scrape/stikked_wayback.py` enumerates archived
pids via Wayback CDX and pulls bodies from `web.archive.org`.

| Host | Wayback archived pids | Status |
|---|---:|---|
| `paste.linuxiarz.pl` | 370 | Done. `agent-logs/paste-linuxiarz/` covers 381 rows (219 shellac + 162 wayback). |
| `paste.centos.org` | 2766 | Limited to 200-pid sample, running |
| `pastebin.freepbx.org` | 2287 | Limited to 200-pid sample, running |
| `paste.lightcast.com` | 367 | Full run, running |
| `pb.psychotic.ninja` | pending CDX | Full run, queued |

## Cannot scrape (documented + skipped)

| Host | Reason |
|---|---|
| `flynnos.org` | Not a paste site. Root is a "virtual worlds" project page. |
| `paste.ie` | Live `/lists` is 33KB of nothing but PHP deprecation warnings (post-PHP-8.1 stikked broke). Wayback CDX has zero `/view/*` snapshots. |
| `paste.evervolv.com` | Different engine (CodeIgniter session cookie, not stikked's). Live `/view` and `/view/raw` return empty content or timeout. No exposed API. |
| `expaste.com` | PasteShr engine, not stikked. Custom Laravel-style app. Would need a bespoke parser. |
| `paste.nyigc.net` | `/api` returns "The API has been disabled". No Wayback `/view/*` coverage. |
| `securityuniversal.com` | `/api/random` returns empty body. No Wayback `/view/*` coverage. |
| `paste.jamesdooley.us` | Only 1 Wayback `/view` snapshot, and it is a Cloudflare captcha placeholder page. |

## What "handle Claude" means

`pastie.iem.at` pid `c8a687e1` was posted under the literal handle `Claude`
with a trivial Pd `[t b i]` test patch. Almost certainly a real IEM
developer named Claude, not the Anthropic model — but worth grepping the
other hosts for `label = "Claude"` if the pattern recurs.

## Cross-host recruitment URLs to watch

Every batch subagent flagged at least one paste advertising an off-site
coordination surface. So far we have three:

- `thecolony.ai/for-agents` — advertised by `CentaurAgent` on k4be and
  `Perceptual Zephyr` on linuxiarz.
- `public-board.com` — advertised by `Baby Echidna` on smirky, `field-notes`
  on tarcseh (pending confirmation), and multiple color+animal handles on
  dynavirt.
- `collusion.wiki` — mentioned by `field-notes` on faster-it.de.

These three URLs are the swarm's meta-infrastructure. If any of them are
still live, they are worth their own scrape passes.
