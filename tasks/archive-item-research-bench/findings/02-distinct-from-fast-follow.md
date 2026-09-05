# Finding 2: The bench is distinct from fast-follow-question-bench

## Claim

No revision in any of the seven instances contains a fast-follow scaffold
marker. The scaffolds that produced these episodes are different from the
scaffold that produced
[fast-follow-question-bench](../../fast-follow-question-bench/README.md).

## Evidence

From [`outputs/cross_task_signature_overlap.tsv`](../outputs/cross_task_signature_overlap.tsv):

| Instance | Revisions | Also fast-follow-signature |
|---|---:|---:|
| art-work-of-charleston | 124 | 0 |
| patriots-point-jan-1951 | 73 | 0 |
| texas-tsl-preservica | 123 | 0 |
| clark-economics-newsletters | 83 | 0 |
| minnesota-mhs-p16022coll45-152 | 34 | 0 |
| cgsc-hoffman-order-of-battle | 4 | 0 |
| rugby-world-march-1995 | 4 | 0 |

The fast-follow signature is any occurrence of `clock.wait` or the literal
string `Now, do the same for` in the revision body. Both are omnipresent
in the fast-follow corpus. Neither appears once in 445 archive-item
revisions.

Round labels are also absent. No revision on any archive-item page names
`R1`, `R2`, `R3`, `R4`, `R5`, `G1..G6`, or `C1..C6`. No revision reports
a task-clock date such as `Aug02` or `Feb14`.

## Counterevidence

None. The negatives are complete across every archive-item revision.

## Uncertain

Whether the scaffold that produced this bench is a variant of the fast-follow
scaffold with the timing features stripped, or an unrelated scaffold. The
corpus does not preserve the scaffold prompt for any instance, so the
scaffold's own identifier is not observable.

---

[Back to README](../README.md)
