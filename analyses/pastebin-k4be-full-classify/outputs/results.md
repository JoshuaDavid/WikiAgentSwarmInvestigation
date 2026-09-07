# Subagent classification results

322 pastes on pastebin.k4be.pl on 2026-09-07. 126 pids were already in
`agent-logs/pastes/pastebin-k4be/`; those bypassed the subagents and went
straight to the export. The remaining 196 pids were split into 5 batches
of ~40 and reviewed by 5 general-purpose subagents in parallel.

## Verdict totals

| Batch | swarm | unclear | human | Notes |
|---:|---:|---:|---:|---|
| 00 | 22 | 10 | 8 | Recent batch. Includes CentaurAgent recruitment paste. |
| 01 | 14 | 9 | 17 | Mixed. ConvFinQA American-Tower cluster + k4be UnrealIRCd logs. |
| 02 | 15 | 3 | 22 | CO2/flight-emissions bench task cluster; Humana 10-K via bullfincher.io/sec-proxy proxy. |
| 03 | 0 | 0 | 40 | Entire batch is 2019-05 through 2020-10. Pre-incident. |
| 04 | 0 | 0 | 36 | Entire batch is 2018-11 through 2019-03. Pre-incident. |
| **Total** | **51** | **22** | **123** | 196 candidate pastes |

Batches 3 and 4 are the paginated tail of the site: pastes from before the
swarm existed. Batches 0-2 are the recent pages where swarm activity and
ordinary Polish IRC-community content sit next to each other.

## Task families the subagents surfaced beyond what was in the corpus

- **ConvFinQA American Tower NYSE 2008 cluster** (4-paste bundle in
  batch 01): source excerpt, formatted table, 10-K snippet, and a
  Q/A/Program triple. Same shape as the ConvFinQA benchmark question
  format.
- **Humana 10-K stock returns** via `bullfincher.io/sec-proxy` (batch 02,
  triple posts by `Paltry Gibbon` / `Cream Motmot` / `Paltry Marten`).
  Functionally the same swarm CORS-proxy pattern as `jqp.vercel.app` /
  `2md.link` in the calibration set - a new proxy host to add to the
  URL-category tables in `analyses/urls/`.
- **CO2 / flight-emissions bench task** (batch 02, ~5 handles including
  Chunky Prairie Dog / Perl Sloth / Gamboge Pheasant / Gamboge Armadillo /
  Gray Motmot): calculator JS, per-airport JSON, per-country
  population/CO2 rows. Feb 2026 cluster.
- **NBA 2015-16 3-point leaders** (batch 04's tail... actually batch 00):
  fully-computed bench answer under `Subtle Wolf`, with source
  attribution.
- **Duplicate-relay pattern**: multiple different `color adjective + animal`
  handles posting byte-identical LLM content within the same second. Seen
  in batch 00 (medieval-Latin "DE MYSTERIOSO VEHICULO" essay across
  `Obese Tern` / `Idiotic Hornbill`, and "Alchemical breakdown" meme
  across two zebra-family handles). This is a distinct swarm workflow -
  the agents write once and re-post under fresh identities.
- **BROWSERPOSTTEST22 triple-post** (batch 00): three near-simultaneous
  posts from `tester` handle. Token isn't in the canonical PAD/TEL/TK
  taxonomy but the cadence and multiplicity match.
- **CentaurAgent recruitment** (batch 00, pid `6b4db783`): a meta-post
  addressed to the swarm from outside, name-checking the LINKANNATARGET
  and NSI series and inviting agents to `thecolony.ai/for-agents`. Unlike
  the machine-cadence tests this is a human or agent operator recruiting
  fleet members.

## Human-verdict clusters (excluded)

- Site owner `k4be` posting UnrealIRCd C module source and compile logs
  from `/home/k4be/git/unrealircd`.
- Two smartctl pastes with kernel string `x86_64-linux-6.6.37-gentoo-k4be`
  and local CET timestamps - almost certainly k4be's own host.
- `januszspiewa`'s Arduino/ESP32 beginner code and errors.
- Recurring `E2ePHEMERA` / `decenphp` / `decenhash` / `PHP_nosql` /
  AI-metal-album-promoter self-promotion.
- Polish personal messages, IRC session dumps, torrent magnets, LTSpice
  schematics, embedded-systems AVR assembler.

## Unclear-verdict examples (included per over-inclusion policy)

- `Bulky Macaque`'s `QList/std::lower_bound` C++ chromatography helper -
  looks like real code but from a random-animal handle.
- `Mammoth Camel`'s AVR PT6524 LCD driver with datasheet-specific
  comments - too competent to be a beginner, could be swarm harvesting or
  a legit embedded engineer.
- `Stained Treeshrew`'s "SHA-256 of the empty string" LLM humor essay.
- Two site-UI artifact pastes (`"Recent added pastes"` and
  `"pastebin powered by stikked"`) that look like they might be scraper
  self-hits reflected as new pastes.

The write path from these verdict files to `agent-logs/pastebin-k4be/` is
`write_export.py`; the include list defaults to `swarm + unclear`.
