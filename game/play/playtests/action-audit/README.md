# Available-action audit

[Narrative findings and changes](REVIEW.md)

The authored route is replayed from the initial state. Every offered action is checked against an explicit current thought. Every enabled action at each distinct route state is also tried as a one-action departure. Effort exhaustion, deadline expiry, and typed builder pairings are checked separately.

Audited **3713 states**, **118887 action offerings**, **3189 departures**, and **1903 builder pairings**. 0 issues.

This is bounded state coverage, not an exhaustive search of arbitrary URL strings, read keys, timing values, or all multi-action combinations. The per-task records expose every route step for narrative review.

| Task | Route checkpoints | Other states | Action offerings |
| --- | ---: | ---: | ---: |
| [T1](t1.md) | 3 | 14 | 71 |
| [T2](t2.md) | 5 | 16 | 81 |
| [T3](t3.md) | 4 | 28 | 191 |
| [T4](t4.md) | 5 | 40 | 325 |
| [T5](t5.md) | 5 | 30 | 209 |
| [E0](e0.md) | 5 | 44 | 391 |
| [E1](e1.md) | 4 | 29 | 215 |
| [E2](e2.md) | 5 | 46 | 429 |
| [E3](e3.md) | 6 | 64 | 693 |
| [E4](e4.md) | 6 | 38 | 222 |
| [E5](e5.md) | 3 | 18 | 114 |
| [E6](e6.md) | 10 | 88 | 757 |
| [E7](e7.md) | 5 | 46 | 421 |
| [E8](e8.md) | 6 | 62 | 640 |
| [E9](e9.md) | 8 | 101 | 1170 |
| [E10](e10.md) | 27 | 687 | 19801 |
| [E11](e11.md) | 14 | 156 | 1728 |
| [E12](e12.md) | 49 | 1723 | 87424 |
| [E13](e13.md) | 13 | 195 | 2896 |
| [E14](e14.md) | 9 | 96 | 1109 |
