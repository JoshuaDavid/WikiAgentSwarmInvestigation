# Finding 1: The task is a multi-turn chat between a scripted user and one agent

## Claim

Each episode is a sequence of user messages and agent replies. The user is
scripted. The messages arrive on a task-clock schedule. There is one agent
per episode.

## Evidence

1. Verbatim initial-turn quote (`dse~OECDEducationEquitySequence@1`):

    > Initial prompt: "For Czech Republic, regarding the share of private expenditure in the early years of education (2018), ... value (to two decimal places) for Pre-Primary education."

2. Verbatim follow-up quotes (`dse~CashierBachelors2015SequenceJan31OAI@2`
   and cognates). See [`outputs/followup_templates.tsv`](../outputs/followup_templates.tsv)
   for the full list of 16 distinct variants across 263 occurrences.

3. [`outputs/initial_prompt_quotes.txt`](../outputs/initial_prompt_quotes.txt)
   contains 89 paraphrases from 89 distinct pages. Every paraphrase
   describes a user message that arrives at a specific task-clock time.

## Counterevidence

None. Every family page in the corpus fits this shape. The only pages that
do not fit are OCR / image caption pages. Those pages carry no round or
timer language. They appear to be scratch caches rather than task pages.
See [Finding 10](10-public-sources.md).

## Uncertain

The corpus contains no verbatim quote of a system prompt. Agents never say
"the system prompt says...". Two explanations are consistent with the data:

1. No system prompt exists. The initial user turn carries all instructions.
2. A system prompt exists. Agents choose not to relay it.

---

[Back to README](../README.md)
