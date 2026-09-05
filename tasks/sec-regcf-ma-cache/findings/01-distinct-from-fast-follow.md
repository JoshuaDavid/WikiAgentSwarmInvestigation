# Finding 1: The activity is a distinct cluster from fast-follow-question-bench

## Claim

The 5,067 regCF-related revisions do not carry any of the scaffolding
markers that define fast-follow-question-bench. They also share no
agent-to-agent addressing with that cluster.

## Evidence

- **No round labels.** In the 5,067 regCF-related revisions, `R1`, `R2`,
  `R3`, `R4`, `R5`, `R6` never appear as round markers next to an entity.
  A regex sweep for `\bR[1-6]\b[^A-Za-z0-9]{0,10}(2019|2020|2021|Barnstable|Berkshire|Bristol|Dukes|Essex|Franklin|Hampden|Hampshire|Middlesex|Nantucket|Norfolk|Plymouth|Suffolk|Worcester)`
  returns zero hits. The one revision that does contain `R5` /
  `URGENT` / `clock.wait` / `deadline` in the same body is
  `dse~AgentOpenAIFeb29Run@6` — its round narrative names states
  (`MA/CT/MI/WV`), which is the `sector_61` fast-follow family that uses
  DataUSA `pums_5`, not SEC `county.json`. SEC URLs are appended below
  the sector_61 narrative as unrelated extra content.

- **No follow-up template.** The pattern
  `"Now, do the same for X."` never occurs in a regCF-related revision.
  Fast-follow-question-bench captures 89 distinct occurrences of this
  template across the corpus; none are in this cluster.

- **No agent-to-agent addressing.** The `analyses/addressing` output
  `addressed_revisions.jsonl` records 3,570 revisions in which the writer
  names another known agent handle. Zero of those overlap with the regCF
  set. Cross-agent messaging is the strongest signal of fast-follow
  coordination; its total absence here matters.

- **No `clock.wait` accelerator claims.** Zero regCF-related revisions
  match the fast-follow `clock.wait\(...\).*accelerat|multipl|fast[- ]?forward`
  pattern.

- **Different handle-style mix.** Handle classification from
  `analyses/labels`:

  | handle_class | writers in regCF set | % of that class overall |
  |---|---:|---:|
  | role_word_agent | 655 | 34.2% |
  | codename_agent | 87 | 36.7% |
  | openai_branded | 52 | 7.2% |
  | date_prefix_agent | 1 | 0.5% |

  `date_prefix_agent` is the handle style used by fast-follow cohorts
  (`OECDEquityAug02Agent`, `MAR13cohort`, `SectorAgentFeb16OAI`). Exactly
  one such handle wrote a regCF-related revision.

## Counterevidence

`dse~AgentOpenAIFeb29Run@6` mixes a `sector_61` fast-follow narrative
(top of body, unchanged from earlier revisions on that page) with a fresh
appendix of SEC map/county.json links (added by the June 18 author,
handle `OpenAISecCountyHelperZeta12`). This is one revision where fast-follow
scaffolding and regCF material co-occur physically. It does not turn the
sector_61 task into a regCF task; the sector_61 sequence answers on
DataUSA state-level values, and no cohort in the corpus posts an actual
crowdfunding number as an `MA/CT/MI/WV` R1-R4 answer.

## Uncertain

Whether the June 18 burst is a response to a scaffold prompt at all. The
alternative — that some or all of it is agents exploring a data source
on their own, without a prompt asking for MA regCF data — is not
excluded by any evidence in the corpus.

---

[Back to README](../README.md)
