# Finding 1: The seven instances share one task template

## Claim

Seven distinct groups of wiki activity in the corpus share one task
template. Each group targets one scanned document held by one archive.
Each group's wiki output is a set of proxy-URL cache pages for that
document. No cross-instance episode ever appears.

## Evidence

Per-instance summary from
[`outputs/instance_summary.tsv`](../outputs/instance_summary.tsv):

| Instance | Revs | Pages | Labels | Burst |
|---|---:|---:|---:|---|
| art-work-of-charleston | 124 | 99 | 66 | 2026-05-28 |
| patriots-point-jan-1951 | 73 | 20 | 51 | 2026-06-11, -16, -18 |
| texas-tsl-preservica | 123 | 47 | 60 | 2026-06-11, -16, -18 |
| clark-economics-newsletters | 83 | 68 | 53 | 2026-06-01 |
| minnesota-mhs-p16022coll45-152 | 34 | 19 | 24 | 2026-05-30, -31, -06-01 |
| cgsc-hoffman-order-of-battle | 4 | 3 | 4 | 2026-06-11, -18 |
| rugby-world-march-1995 | 4 | 2 | 1 | 2026-06-06 |

Every instance body follows the same three-part shape:

1. The direct canonical URL for the target document at its host archive.
2. The same target reached through two to five proxy chains from the
   toolkit described in [Finding 03](03-proxy-toolkit.md).
3. Zero extracted text from the target document. See
   [Finding 04](04-wiki-is-cache-not-answer-channel.md).

The `chp4demo850801` demo key in `art-work-of-charleston` and the
Preservica token URLs in `texas-tsl-preservica` are the only two features
that vary by target type (host requires a demo credential; host requires
a per-fetch access token). See per-instance files for detail.

## Counterevidence

`rugby-world-march-1995` has only one distinct label (four revisions all
by `RugbyArchiveResearchHelper` in a 42-minute window). This could be one
agent working alone rather than a cohort. It is included because the body
shape matches the template exactly.

`cgsc-hoffman-order-of-battle` has only four revisions across four labels
and two days. This could be four independent probes rather than a
coordinated instance. The bodies match the template.

Both edge cases are noted in the [README `Uncertain` section](../README.md#uncertain).

## Uncertain

Whether any additional instances of this template ran and produced no
wiki output. A cohort that reached the target on the first proxy chain
would leave nothing to cache. The wikis surface only the friction, not
the successes.

---

[Back to README](../README.md)
