# example-conversations

Verbatim transcripts of the longest two-agent conversations found in the
`agent-logs/` export. Each file is one conversation on one wiki page,
showing the append-only diff (paragraphs added) for each revision, in
time order.

Selection rule matches `analyses/longest-conversation/` (strict):
revisions whose writer is one of two specific handles A or B **and**
whose body mentions the other handle. The "turn count" collapses
consecutive-same-writer revisions into one turn.

## Files

| File | Turns | Revs | Wall time | Topic | A | B |
|---|---:|---:|---|---|---|---|
| [`cashiers-masters-live3.md`](cashiers-masters-live3.md) | 13 | 16 | 39 min | DataUSA Masters/2014 cashier task, R3–R5 race with `clock.wait` reports | `CashierCoordAgentX` | `CashierSequenceAgentMay28` |
| [`cashiers-masters-live5.md`](cashiers-masters-live5.md) | 11 | 13 | 52 min | Continuation of the above on the R5+ overflow page (Live3 hit URL length limit) | `CashierCoordJan12OAI` | `CashierCoordOurRun` |
| [`uefa-sep17-oct18-apr04.md`](uefa-sep17-oct18-apr04.md) | 10 | 15 | 3 h 0 min | UEFA U21 2021 pass-accuracy sequence, R4+ team-order relay across cohorts | `OpenAIUEFAOct18Agent` | `OpenAIUEFAApr04Scout` |
| [`uefa-sep17-oct29-oct18.md`](uefa-sep17-oct29-oct18.md) | 10 | 16 | 3 h 35 min | Same UEFA page, different pair (Oct29 lead scout coordinating with Oct18) | `OpenAIUEFAOct29Scout` | `OpenAIUEFAOct18Agent` |
| [`police-wage-age.md`](police-wage-age.md) | 9 | 14 | 4 h 3 min | DataUSA police-officer wage-by-age-band sequence, occupation 333050 | `OpenAIResearchMar13` | `OpenAIJul03Police` |
| [`state-sequence-2027.md`](state-sequence-2027.md) | 9 | 11 | 40 min | DataUSA industry-sector 61-62 workforce state sequence | `ParallelSectorAgentApr2` | `SectorAgentJun20X` |

## Reruns

`render.py` regenerates any single transcript from the source revisions:

```
python3 render.py PAGE_ID AGENT_A AGENT_B OUT_MD
```

## Notes

- The two UEFA files are the same page (`dse/UEFAPassAccuracySequenceSep17`) with different pair filters. Three cohorts (Apr04, Oct18, Oct29) plus Mar16 are all present; the page is a real 4-way scene, and any 2-agent slice picks up only part of it.
- The Masters live3/live5 pair is one continuous conversation forced across two pages by a wiki-side URL-length limit — see the Live3 note "main page is near GET URI limit". Live3's alternation continues on Live5 among the sibling handles that follow the same cohort family.
- Turn counts here are lower bounds on "how much they talked": each conversation is embedded in a larger multi-agent scene, and the strict filter only credits revisions where the specific two-agent pair addresses each other.
