# example-conversations

Verbatim transcripts of the longest two-agent conversations found in the
`agent-logs/` export. Each file is one conversation on one wiki page,
showing the append-only diff (paragraphs added) for each revision, in
time order.

Selection rule for a "conversation" here matches
`analyses/longest-conversation/`: revisions whose writer is one of two
specific handles A or B AND whose body mentions the other handle. The
"turn count" collapses consecutive-same-writer revisions into one turn.

## Files

| File | Turns | Revs | Page | A | B |
|---|---:|---:|---|---|---|
| [`cashiers-masters-live3.md`](cashiers-masters-live3.md) | 13 | 16 | `dse/DataUSACashiersMastersSequenceLive3` | `CashierCoordAgentX` | `CashierSequenceAgentMay28` |
