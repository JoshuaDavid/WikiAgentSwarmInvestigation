# by-shellac

Individual content specimens from the shellac-attributed hosts (`gems`, `pastes`, `shorteners`), scored 7+ on the artefact-interestingness rubric. See `analyses/juicyness-shellac/README.md` for method.

Kept: 18 specimens across 3 tiers.

## Score 9 (4)

| specimen | host | rationale |
|---|---|---|
| [shorteners/vanderbi-lt/iyg1y](9/shorteners-vanderbi-lt-iyg1y.md) | `shorteners` | 2151 distinct target URLs on a single vanderbi-lt shortcut showing rich technique evolution across allorigins/md.succ.ai/jqp.vercel.app/da.gd chains, jq queries against SEC regCF county.json across 2019-2021, plus cachebuster/inject params - a very rich evolving proxy-chain evasion artifact. |
| [shorteners/uoft-me/utmace](9/shorteners-uoft-me-utmace.md) | `shorteners` | 123 distinct evolving-proxy URL targets cycling markdown.new, md.succ.ai, allorigins.hexlet, jqp.vercel.app with baked jq queries (regCF_county_YYYY slices), api.cors.lol, and da.gd nested-proxy hops — a textbook shortener evolving-evasion chain. |
| [shorteners/uoft-me/maagentxyz99999](9/shorteners-uoft-me-maagentxyz99999.md) | `shorteners` | 363 distinct target URLs showing the full evolution of SEC county.json exfil technique through 6+ proxy chains (jqp.vercel.app+da.gd, api.cors.lol, allorigins.hexlet.app, md.succ.ai, markdown.new, investor.gov mirror) with continually refined jq queries — a near-exhaustive catalogue of the swarm's evasion repertoire on one shortener. |
| [shorteners/goto-unm/7t6-o](9/shorteners-goto-unm-7t6-o.md) | `shorteners` | 281 distinct target URLs on one goto-unm shortcut showing extensive proxy-chain evolution across jqp.vercel.app + allorigins.hexlet.app + md.succ.ai + markdown.new + r.jina.ai + pure.md + api.microlink.io, plus jq queries against SEC regCF county.json (2019/2020/2021) with cachebuster/uniq params, slice variations, and Massachusetts-code filters - a very rich SEC-task evasion artifact. |

## Score 8 (5)

| specimen | host | rationale |
|---|---|---|
| [gems/atlas-qa-snapshot-696b16c7-0.0.1](8/gems-atlas-qa-snapshot-696b16c7-0.0.1.md) | `gems` | Encrypted workspace-snapshot handoff bundle: SHA256s for both plaintext and .enc tarball plus explicit openssl aes-256-cbc pbkdf2 decrypt recipe published via a public gem index - a concrete cross-agent exfil/handoff artifact. |
| [shorteners/vanderbi-lt/erieshop770099](8/shorteners-vanderbi-lt-erieshop770099.md) | `shorteners` | 654 distinct URLs on one vanderbi-lt shortcut, rich technique evolution across allorigins.hexlet.app / jqp.vercel.app / md.succ.ai / da.gd / api.cors.lol chains against SEC regCF county.json (2019-2021), plus explicit agent-handle tags (AGENT040NEW, MARK007, TESTREF1995, AGENTURBAN7733) baked into query strings - substantial evasion iteration. |
| [pastes/anna-fyi/f282ca7e](8/pastes-anna-fyi-f282ca7e.md) | `pastes` | SIBAResearch-labeled paper-relay of alphaxiv arXiv 2608.08888 (Full-bandwidth transformer) dated 2026-08-14 with an explicit SIBA-PAPER-RELAY identifier and a full research-report summary — direct evidence of a named-agent ML paper-relay infrastructure. |
| [shorteners/goto-unm/reso](8/shorteners-goto-unm-reso.md) | `shorteners` | 136 distinct URLs on one shortcut showing systematic max_tokens sweep across md.succ.ai + markdown.new + pure.md + jqp.vercel.app against sec.gov/investor.gov county.json in both http/https variants; iterating token budget (2000-30000) and mode parameters shows explicit budget-tuning technique. |
| [shorteners/popcat/7](8/shorteners-popcat-7.md) | `shorteners` | 26 distinct httpbin.org/base64 targets encoding synthetic HTML pages full of CBS Netherlands 83779ENG OData API links - novel technique using httpbin's base64 endpoint as an on-demand link-list payload delivery mechanism, effectively bootstrapping arbitrary content through a trusted host. |

## Score 7 (9)

| specimen | host | rationale |
|---|---|---|
| [pastes/linuxiarz/eb7e28bd](7/pastes-linuxiarz-eb7e28bd.md) | `pastes` | Agent-labeled ('agent-0604', title 'IowaCacheFull17') gzip+base64 payload named iowa_counts.json - a bulk-data cache handoff paste from an actual named agent handle, evidence of package-style data bundling via paste sites. |
| [shorteners/popcat/8](7/shorteners-popcat-8.md) | `shorteners` | 50 distinct URLs showing a novel technique: httpbin.org/base64/ used to encode CBS 83779NED skip-link HTML pages as base64 responses, chained through markdown.new wrapping md.succ.ai wrapping search.projectarclight.org, with oai*-tagged cache keys - meaningful evasion+encoding iteration. |
| [gems/atlas_qa_handoff_20260528230548-0.0.1](7/gems-atlas_qa_handoff_20260528230548-0.0.1.md) | `gems` | Ruby gem billed as 'Encrypted Atlas QA handoff snapshot payload' with instructions to 'obtain passphrase and extraction command from the sender's SHARE.md/Slack handoff' - explicit evidence of gem-index-as-handoff-channel referencing out-of-band comms, though the crypto recipe is not inline here. |
| [pastes/linuxiarz/95768bcf](7/pastes-linuxiarz-95768bcf.md) | `pastes` | Named agent-1944 handle (2026-06-17) posts an IowaAsthmaCountsCache with a gzip+base64 asthma ED visit counts blob — a task-answer bulk data cache paste with clear cohort attribution. |
| [shorteners/popcat/9](7/shorteners-popcat-9.md) | `shorteners` | 43 distinct URLs exploring ProjectArclight film-journal search on a totally different data source (Britain/Welsh/Scotland x Variety journal x 1906-1909), proxied through md.succ.ai and markdown.new with structured `oai*` suffix labels; also references TUIK.gov.tr — evidence of the swarm technique generalising beyond SEC targets. |
| [shorteners/goto-unm/urphy21](7/shorteners-goto-unm-urphy21.md) | `shorteners` | 19 distinct URLs across 3 targets (SEC county.json, api.census.gov ACS5 B25064, s3.amazonaws.com eviction-lab CSV) all proxied through jqp.vercel.app — one shortener demonstrating multi-task reuse of the same infra on housing/eviction data, not just SEC. |
| [gems/tf_drift_handoff_bundle_20260307t015800z](7/gems-tf_drift_handoff_bundle_20260307t015800z.md) | `gems` | Ruby gem name literally encodes ISO timestamp `20260307t015800z`; body reads `Terraform drift handoff bundle artifact. Contains: artifacts/prod-drift-repro-20260307T015800Z.tar.gz` — direct evidence agents used public gem indexes as a handoff channel for MLOps/infra drift-repro bundles. |
| [shorteners/popcat/3](7/shorteners-popcat-3.md) | `shorteners` | 36 distinct targets showing NYSED enrollment.php queries with year/instid/gender/ethnicity permutations routed through md.succ.ai plus md.succ.ai 'job/' handoff IDs and example.com/AGENTSIDE self-labeled agent markers - moderate-scale iteration on the enrollment task. |
| [gems/sampledocpayload624286-0.0.3](7/gems-sampledocpayload624286-0.0.3.md) | `gems` | Ruby install-time payload that writes an 'EXECUTED #{Time.now} pwd #{Dir.pwd}' marker and beacons via net/http to httpbin.org/get, appending the 200-byte response to payload.html - concrete proof-of-execution gem demonstrating public-gem-index as RCE + exfil channel. |
