
## 2026-09-25T20:55 · repeat-hits-25m · result

**Question.** For Cluster A Azure IPs (all 8,555 of them — Cluster A is
100% Microsoft ASN 8075 per `analyses/traffic-clustering/`): how many
URLs got hit ≥10 times within a 25-minute window by Cluster A IPs, and
what fraction of Cluster A hits are the 10th-or-later such hit? Same
question across all classes.

**Method.** `analyses/repeat-hits-25m/compute.py`. Load ip→class from
`hour-bayesian/outputs/ip_classification.tsv` (339k IPs, 29 classes),
JOIN against `tmp/wiki-access-logs/all.db` filtered to `ts <=
2026-09-04 23:59:59 UTC`, ORDER BY class,url,ts, stream each
(class,url) group and check `ts[k] - ts[k-9] <= 25*60` for `k >= 9`.
An earlier attempt to load 17.7M rows into a Python dict was
OOM-killed at 2M rows; the streaming refactor fixed it.

**Result.**
- Cluster A (`other-A`): 1,715,385 pre-disclosure hits. 267 URLs saw
  at least one 10-in-25-min burst. 9,031 burst hits = **0.53% of
  Cluster A traffic**. Cluster A is not bursty despite carrying the
  bulk of wiki writes.
- All classified traffic pooled: 8,475,683 hits, 241,213 burst hits =
  **2.85% overall**.
- Distribution across classes is very uneven:
  - `chatgpt-user`: **41.59%** burst (199,614/479,949). The `web.run`
    16-IP pool bombing coordination URLs with `?<QueryString>=`
    cache-pin values.
  - `other-F`: 23.86% burst (16,464/69,016). CVD task-family collab
    pages — small class, heavily bunched.
  - Everyone else: <1% burst; most classes 0%.
- Cluster A top bursty URLs are DSE wiki `form_edit=1&action=form_edit`
  save endpoints for `StartSeite` and coordination pages
  (`SectorAgent…OAI`, `DataUSAStateSequenceCollab2027`).

**Interpretation.** The cache-pinning / rendezvous signature (the 10-
in-25-min burst) lives almost entirely in `chatgpt-user`, which is the
web.run channel. Cluster A's raw-curl channel is spread thin across
many URLs — population-level, not intra-class-per-URL. Consistent with
`project_environment_mitm_model.md` (raw curl for cache-BUSTING with
unique-per-request values vs web.run for cache-PINNING).

**Caveat.** Burst count is per-class, not cross-class. A URL bombed by
one chatgpt-user IP and one Cluster A IP within 25 min counts as
"chatgpt-user only" burst, not a cross-class burst. Follow-up should
pool-then-count.

