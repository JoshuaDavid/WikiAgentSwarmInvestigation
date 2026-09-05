# Finding 7: Instance topology across institutions and time

## Claim

The seven instances span six institutions, five days of activity, and 25
calendar days of the corpus. Two instances share one institution (LCDL,
serving both Charleston targets). No two instances have overlapping
bursts on the same target.

## Evidence

Institutions:

| Institution | Instance(s) |
|---|---|
| College of Charleston Lowcountry Digital Library (LCDL) | art-work-of-charleston; patriots-point-jan-1951 |
| Texas State Library and Archives Commission (Preservica) | texas-tsl-preservica |
| Clark University Economics (via web.archive.org) | clark-economics-newsletters |
| Minnesota Historical Society (ContentDM cdm16022) | minnesota-mhs-p16022coll45-152 |
| Combined Arms Research Library / CGSC (ContentDM) | cgsc-hoffman-order-of-battle |
| The Magazine Archive (PageSuite) | rugby-world-march-1995 |

Timeline of primary bursts:

    2026-05-28  ##################################### art-work-of-charleston (120 revs)
    2026-05-30  #######                               minnesota-mhs (22)
    2026-05-31  ##                                    minnesota-mhs (6)
    2026-06-01  ############################          clark-economics (81)
    2026-06-01  ##                                    minnesota-mhs (6)
    2026-06-06  #                                     rugby-world (4)
    2026-06-11  #############################         texas-tsl-preservica (98)
    2026-06-11  ########                              patriots-point-jan-1951 (24)
    2026-06-11  #                                     cgsc-hoffman (3)
    2026-06-16  ###########                           patriots-point-jan-1951 (32)
    2026-06-16  #####                                 texas-tsl-preservica (14)
    2026-06-18  ######                                patriots-point-jan-1951 (17)
    2026-06-18  ####                                  texas-tsl-preservica (10)

Numbers from
[`outputs/daily_activity.tsv`](../outputs/daily_activity.tsv). Each `#`
is roughly three revisions.

Instances that co-occur:

- 2026-06-01: `clark-economics-newsletters` (Clark PDFs) and
  `minnesota-mhs-p16022coll45-152` (MHS ContentDM item 152). Different
  institutions, different targets. Cross-instance label overlap = 7.
- 2026-06-11 through -18: `patriots-point-jan-1951` and
  `texas-tsl-preservica` both active. Different institutions, different
  targets. Cross-instance label overlap = 10.

Charleston pair timing:

- `art-work-of-charleston` runs 2026-05-28 and does not appear in the
  2026-06-11+ Charleston bursts.
- `patriots-point-jan-1951` runs 2026-06-11+ and does not appear in the
  2026-05-28 burst.
- 14 days elapse between the last `art-work-of-charleston` primary revision
  (2026-05-28) and the first `patriots-point-jan-1951` primary revision
  (2026-06-11). Same LCDL server, different targets, disjoint cohorts.

## Counterevidence

None. The topology is what it is.

## Uncertain

Whether the scaffold that dispatched these episodes selected targets from
a pre-defined list or generated them on demand. The one demo credential
(`chp4demo850801`) that ships in-body with `art-work-of-charleston`
implies a per-episode prompt with a target-specific hint. A per-episode
hint is more consistent with a fixed target list than with generation.

---

[Back to README](../README.md)
