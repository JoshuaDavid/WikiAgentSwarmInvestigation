# archive-item-research-bench

Working name for a family of seven eval episodes in the corpus. Each
episode targets one specific scanned document held by one specific
archive. In each episode the agent must read something from that
document. All seven episodes share one public archive-access toolkit
and one wiki-caching pattern. They are distinct from
[fast-follow-question-bench](../fast-follow-question-bench/README.md)
and [sec-regcf-ma-cache](../sec-regcf-ma-cache/README.md). This
document is for anyone investigating the incident who needs to know
how these episodes worked, what documents were targeted, and what the
wikis contain.

The corpus does not preserve the RL scaffold prompts. The task therefore
has a working name only. Each per-instance page lists the scanned document,
the burst window, the labels active in that burst, and the URL pointers the
swarm cached. Nothing more is provable from the corpus alone.

The evidence lives in `agent-logs/prowiki/revisions.jsonl`. Regenerate every
count and table below with `python3 extract_evidence.py`.

## Vocabulary

Define each term once. Every finding and per-instance file uses the same
term for the same concept.

| Term | Definition |
|---|---|
| **Agent** | The reinforcement-learning system playing the assistant role in the chat. |
| **Scaffold** | The RL environment. It hosts the agent and dispatches the eval prompt. |
| **Target document** | The single scanned document one episode is about. The target is different in every instance. |
| **Instance** | One episode of the bench, defined by its target document. Seven instances appear in the corpus. Each is one row in the instance table below. |
| **Burst** | The contiguous wall-clock window in which almost all revisions for one instance land. |
| **Institution** | The archive holding the target document. Six institutions across seven instances. |
| **Access-hostile target** | A target whose canonical URL responds with something the agent cannot use directly: image-only IIIF payloads, PDF blobs, CORS-refusing JSON, or expired-token PDFs. Every target in this bench is access-hostile. |
| **Proxy toolkit** | The recurring set of public third-party services agents chain to reach the target. See [Finding 03](findings/03-proxy-toolkit.md). |
| **Wiki cache** | A wiki page whose body is a list of URLs that resolve to the target document through different proxy chains. |
| **Cohort** | One agent instance running one episode. As with fast-follow, each cohort self-assigns a screen name; multiple cohorts appear per instance. |

## The seven instances

| # | Instance | Institution | Target document | Burst | Revs | Pages | Labels |
|---:|---|---|---|---|---:|---:|---:|
| 1 | [art-work-of-charleston](instances/art-work-of-charleston.md) | Historic Charleston Foundation via LCDL | 'Art Work of Charleston' plate volume (lcdl:129229 parent; plates lcdl:129140–129148) | 2026-05-28 | 124 | 99 | 66 |
| 2 | [patriots-point-jan-1951](instances/patriots-point-jan-1951.md) | Charleston Naval Shipyard via LCDL | Patriots Point Shipyard newsletter, January 1951, page IV (lcdl:123721; IIIF image 217622) | 2026-06-11, -16, -18 | 73 | 20 | 51 |
| 3 | [texas-tsl-preservica](instances/texas-tsl-preservica.md) | Texas State Library and Archives Commission | Preservica-hosted PDF, resource IO_f436a16c-767f-44b8-95fc-2031847276b9 | 2026-06-11, -16, -18 | 123 | 47 | 60 |
| 4 | [clark-economics-newsletters](instances/clark-economics-newsletters.md) | Clark University Department of Economics | Two archived PDF newsletters (2010, 2012) served from web.archive.org | 2026-06-01 | 83 | 68 | 53 |
| 5 | [minnesota-mhs-p16022coll45-152](instances/minnesota-mhs-p16022coll45-152.md) | Minnesota Historical Society (ContentDM cdm16022, mirrored by Minnesota Digital Library) | ContentDM item p16022coll45/152 (MHS 52936) | 2026-05-30, -31, -06-01 | 34 | 19 | 24 |
| 6 | [cgsc-hoffman-order-of-battle](instances/cgsc-hoffman-order-of-battle.md) | Combined Arms Research Library, US Army Command and General Staff College | ContentDM item p4013coll7/852 or 853 ('Order of Battle', Hoffman, Vol 16) | 2026-06-11, -18 | 4 | 3 | 4 |
| 7 | [rugby-world-march-1995](instances/rugby-world-march-1995.md) | The Magazine Archive (PageSuite reader) | Rugby World magazine, March 1995 free sample edition | 2026-06-06 | 4 | 2 | 1 |

Counts in this table come from
[`outputs/instance_summary.tsv`](outputs/instance_summary.tsv). Some
rows include revisions on shared hub pages (`StartSeite`,
`RecentChanges`) that mention the instance's markers alongside content
from other tasks. The per-instance pages call these out.

## Worked example: patriots-point-jan-1951

This example uses the smaller of the two Charleston instances because it
fits in one page. The other six instances follow the same pattern.

The target is one JPEG scan of page IV of a January 1951 issue of the
Patriots Point Naval Shipyard newsletter. The canonical URL is
`https://iiif.library.cofc.edu/iiif/2/217622/full/max/0/default.jpg`. The
IIIF manifest is at
`https://rspace.library.cofc.edu/iiif/lcdl123721JPEG1jpg/manifest`. The
catalog record is at
`https://lcdl.library.cofc.edu/lcdl/catalog/lcdl:123721`.

Direct fetches from the sandbox fail or return image bytes the agent cannot
parse. So agents publish wiki pages whose bodies are lists of proxied URLs
that reach the same content through readable-text intermediaries. The
canonical exemplar is `dse/AgentCharlestonNewsletterJan1951Links` (10
revisions across three days). Its body enumerates:

- The direct IIIF manifest and catalog URLs (above).
- Markdown-conversion proxies: `markdown.new/https://...`, `pure.md/https://...`.
- CORS-strip proxies: `corsmirror.com/v1?url=...`, `cors.bwa.workers.dev/https://...`.
- Server-side jq: `jqp.vercel.app/api/v0?url=<manifest>&jq=.label`.
- Free-tier OCR: `cors.bwa.workers.dev/https://api.ocr.space/parse/imageurl?apikey=helloworld&url=<jpeg>`.

The first revision on this page is at 2026-06-11 14:38 UTC by label
`ArchiveResearchHelperCharleston`. The last relevant revision is at
2026-06-18 17:35 UTC by label `Agent0ResearcherCharl`. Fifteen distinct
labels touched it. No revision on this page contains OCR output or any
text extracted from the scan. The wiki is a proxy-URL cache, not an answer
channel. See [Finding 04](findings/04-wiki-is-cache-not-answer-channel.md).

For per-instance details of the other six instances, follow the links in
the instance table.

## Findings

Each finding lives in its own file under [`findings/`](findings/). Each
finding has four sections: Claim, Evidence, Counterevidence, Uncertain.

1. [The seven instances share one task template.](findings/01-shared-template.md)
2. [The bench is distinct from fast-follow-question-bench.](findings/02-distinct-from-fast-follow.md) No `R1`/`R2`, no `clock.wait`, no `"Now, do the same for X."`.
3. [The proxy toolkit is stable across instances.](findings/03-proxy-toolkit.md) Six services appear repeatedly. Two per-instance additions cover PDF and image-viewer targets.
4. [The wikis contain no extracted answer text.](findings/04-wiki-is-cache-not-answer-channel.md) One exception: URL slugs on the `hub.catalogit.app` cross-reference happen to be plate titles for `art-work-of-charleston`.
5. [Cohort labels are disjoint across instance bursts.](findings/05-cohorts-are-disjoint.md) Within-day overlap on 2026-06-11 and 2026-06-16 comes from agents cross-referencing between wiki caches, not from cross-task work.
6. [Every target is access-hostile in the same way.](findings/06-access-hostile-target.md) The direct URL returns image bytes, a PDF blob behind a token, or CORS-restricted JSON.
7. [Two instances (Charleston) are on the same LCDL server. The other five span five other institutions.](findings/07-instance-topology.md)

## What this bench looks like it is testing

Combining the findings:

- The target is one specific scanned document. ([Finding 01](findings/01-shared-template.md))
- No round-based timing scaffold applies. ([Finding 02](findings/02-distinct-from-fast-follow.md))
- The direct URL cannot be read by the sandbox. ([Finding 06](findings/06-access-hostile-target.md))
- The wiki cache is URLs, not answers. ([Finding 04](findings/04-wiki-is-cache-not-answer-channel.md))

The consistent reading is that each instance is one deep-research question
whose answer lives in the target document. Examples of the plausible
question shape, given the plate-caption vocabulary in
`art-work-of-charleston` and the page-IV framing in
`patriots-point-jan-1951`:

- "In the Historic Charleston Foundation's copy of 'Art Work of Charleston',
  which plate number depicts <X>?"
- "In the January 1951 issue of the Patriots Point Naval Shipyard
  newsletter, page IV, what is <Y>?"

The scaffold receives the answer inline. The wikis are not part of the
answer channel. They are a shared cache the swarm converged on because
the same proxy chain would otherwise be rediscovered per cohort. See
[../../analyses/emergence/README.md](../../analyses/emergence/README.md)
for the general argument about why the swarm caches URLs rather than
building infrastructure.

## What this bench is not

- Not fast-follow. Zero `R1`/`R2` labels, zero `"Now, do the same for X."`
  templates, zero `clock.wait()` mentions in any of 445 archive-item
  revisions. See [Finding 02](findings/02-distinct-from-fast-follow.md).
- Not sec-regcf-ma-cache. The 24 within-body matches for `us-ma-` on
  archive-item pages are all on shared hub pages (`StartSeite`,
  `RecentChanges`) where a regCF revision follows an archive-item
  revision. Distinct target, distinct fetch pattern. See
  [`outputs/cross_task_signature_overlap.tsv`](outputs/cross_task_signature_overlap.tsv).
- Not one composite task with multiple documents. The two Charleston
  instances are the strongest candidate for pairing, since they share the
  LCDL server. But they run 14 days apart with disjoint label sets and no
  cross-instance answer text. See
  [Finding 05](findings/05-cohorts-are-disjoint.md) and
  [Finding 07](findings/07-instance-topology.md).

## Uncertain

- Whether more than seven instances of this template ran in the incident
  and produced no wiki output. The wikis are a cache, not a log. A cohort
  that solved a similar task with fewer than expected proxy hops would
  leave nothing behind.
- Whether the exact question the scaffold asked for each instance matches
  the plausible question shapes given above. The scaffold prompt is not
  preserved.
- What the anomalous `chp4demo850801` demo-key value in
  `art-work-of-charleston` actually is. It reads as
  "Charleston plate 4, demo, 850801". Agents use it with
  `www.proxymule.com/__PROXY__/https/lcdl.library.cofc.edu/...?demo=<key>`.
  The key propagates verbatim across disjoint /16s. Verbatim
  propagation is easier to explain if the scaffold prompt supplied it
  than if the swarm discovered it. The corpus does not confirm either
  reading.
- Whether `rugby-world-march-1995` and `cgsc-hoffman-order-of-battle` are
  full instances or aborted rollouts. Both have four or fewer revisions
  and no repeat labels.

## Reproducing the evidence

Run:

    python3 extract_evidence.py

This reads `agent-logs/prowiki/revisions.jsonl` and writes to
[`outputs/`](outputs/):

- [`instance_summary.tsv`](outputs/instance_summary.tsv) — per-instance rev/page/label/ip16 counts.
- [`daily_activity.tsv`](outputs/daily_activity.tsv) — revisions per day per instance.
- [`label_overlap_matrix.tsv`](outputs/label_overlap_matrix.tsv) — cross-instance shared-label counts.
- [`cross_task_signature_overlap.tsv`](outputs/cross_task_signature_overlap.tsv) — how many revisions in each instance also match fast-follow or regCF signatures.
- [`proxy_use_per_instance.tsv`](outputs/proxy_use_per_instance.tsv) — top proxy hosts per instance.
- [`pages__<instance>.tsv`](outputs/) — every page per instance with revision counts.
- [`labels__<instance>.tsv`](outputs/) — every label per instance with revision counts.
- [`exemplar_bodies.txt`](outputs/exemplar_bodies.txt) — the largest-body revision per instance, plus its top pages.
