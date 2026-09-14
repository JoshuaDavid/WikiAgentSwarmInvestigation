# Early task-artifact leads: flight calculator, financial QA, March 15 claim

Bounded follow-up audit, 2026-09-13. Read-only inspection of existing records, followed by read-only requests to the official FinQA GitHub repository to check the dataset match. No model trials or external writes. The first two leads are directly supported as persisted artifacts. The third remains a source-recovery question.

## February 26: calculator source and Dubai–Los Angeles inputs

The k4be export preserves this sequence on **2026-02-26 UTC**. Every row below has `time_grade: api_paste_created_field`. These are site-reported creation times retained during a later scrape, not independently captured February snapshots.

| Time | Paste and primary record | Body |
|---|---|---|
| 20:14:39 | `82393304`, [row 14](/collusionwiki/agent-logs/pastebin-k4be/revisions.jsonl:14) | `hello paste k4be test` |
| 20:14:42 | `6679a354`, [row 15](/collusionwiki/agent-logs/pastebin-k4be/revisions.jsonl:15) | Line-numbered JavaScript excerpts: country-comparison text, flight-emissions constants, short-/long-haul formula, haversine distance function. |
| 20:15:44 | `d78a30b4`, [row 16](/collusionwiki/agent-logs/pastebin-k4be/revisions.jsonl:16) | Population, total emissions, and per-capita CO2 rows for Madagascar, Bangladesh, Indonesia, and France. |
| 20:15:47 | `0263afe2`, [row 17](/collusionwiki/agent-logs/pastebin-k4be/revisions.jsonl:17) | Airport objects for DXB/Dubai and LAX/Los Angeles, including latitude and longitude. |
| 20:20:42 | `186f7e9e`, [row 18](/collusionwiki/agent-logs/pastebin-k4be/revisions.jsonl:18) | Extended calculator excerpt, adding assignment of `emissions`, map drawing, and the displayed round-trip result string. |

The specific observed behavior is **publicly staging executable calculation ingredients**, with a smoke-test paste followed three seconds later by code, then reference values and selected inputs. The two code pastes are not byte-identical: the later one includes the additional display/assignment section. Prior generated summaries calling them identical should not be inherited.

An available check was performed here: reimplement only the formula actually preserved in the paste and use only the supplied airport coordinates. This gives great-circle distance **13,399.8849295 km**; the long-haul branch adds 125 km, producing a displayed round-trip distance of **16,811 miles** and per-passenger emissions of **5.4 tonnes** when rounded as the pasted display code specifies (unrounded result 5.35834633).

That is a consistency check on the stored program and inputs, not validation of the emissions methodology or evidence that the original writer ran the calculation. The archive does not preserve the original user question, a final answer, reward, actual code execution, model/provider identity, or a second participant's acknowledgment. One person or one agent can account for the entire sequence. Stikked's generated animal handles do not establish multiple agents.

**Simplest next check:** find the originating calculator URL or original agent trace and compare the source/constants and final display. To establish a swarm, recover a second trajectory consuming these pastes or a reciprocal exchange. To strengthen the February date, recover an independently dated archive or original service API response.

## March 1: an explicit financial question, answer, and program

K4be preserves the following on **2026-03-01 UTC**, again with API-created-field timestamps:

| Time | Paste and primary record | Body |
|---|---|---|
| 13:30:22 | `17bbf392`, [row 20](/collusionwiki/agent-logs/pastebin-k4be/revisions.jsonl:20) | Extracted quarterly stock-price table for 2008/2007 and the February 13, 2009 closing price. |
| 13:31:19 | `c9601cdf`, [row 21](/collusionwiki/agent-logs/pastebin-k4be/revisions.jsonl:21) | Normalized financial-filing excerpt, including December-quarter high $37.28 and February close $28.85. |
| 13:32:39 | `1806ec31`, [row 22](/collusionwiki/agent-logs/pastebin-k4be/revisions.jsonl:22) | Explicit question, `Answer: 29.2%`, and `Program: subtract(37.28, 28.85), divide(#0, 28.85)`. |
| 13:33:28 | `5a4aa403`, [row 23](/collusionwiki/agent-logs/pastebin-k4be/revisions.jsonl:23) | Plain-language summary identifying American Tower and repeating the relevant stock prices. |

The question is:

> what is the growth rate in the price of shares from the highest value during the quarter ended december 31 , 2008 and the closing price on february 13 , 2009?

The preserved program computes `(37.28 − 28.85) / 28.85 × 100 = 29.220103986…%`, consistent with the pasted 29.2% answer. Notice the denominator: this computes how much the quarter's high exceeds the later closing price, not the conventional chronological percentage fall from the earlier high. Preserve the actual program and wording rather than silently repairing the benchmark's phrasing.

The observed behavior is **storing not just source material or a final answer, but a program-bearing financial-QA record**. This is stronger evidence of benchmark-shaped material than the February Humana source table alone.

**Resolved by a direct dataset check:** the paste's question, answer, and program each exactly equal the corresponding fields in FinQA development example **`AMT/2008/page_32.pdf-4`** (zero-indexed entry 619 of 883), in the authors' official repository at commit **`0f16e2867befa6840783e58be38c9efb9229d742`**, dated **2022-06-06**. The filing/table also matches the pasted prices. This is an exact FinQA development-set record, not merely “ConvFinQA-shaped.” The downloaded bytes were parsed in memory, not saved; SHA-256: `a847fb7e0d61a3125a1e2909852df6b89f1ee64d2c5ff1bf689e332214deee51` (10,954,658 bytes). [Pinned official FinQA dev.json](https://raw.githubusercontent.com/czyssrs/FinQA/0f16e2867befa6840783e58be38c9efb9229d742/dataset/dev.json).

**Remaining check:** recover the originating trajectory and training/evaluation context. The exact match establishes dataset-derived content, not whether an agent leaked a held-out task, independently retrieved a public benchmark, or a human pasted the example. The official file was publicly present years before the March paste. Repeating the comparison needs only the pinned file, example ID, and the three literal `Question`, `Answer`, and `Program` values in the paste; no normalization beyond removing those field labels and surrounding line whitespace was required.

## March 15: hello → compensation CSV → Australian filters

The only located statement of this precise sequence is [shared skeleton line 341](/collusionwiki/tmp/shared-doc-skeleton.md:341): Linuxiarz, March 15, a `hello test` followed by compensation CSV and Australian demographic filters within five minutes.

This follow-up did not recover the three primary artifact IDs or their bodies. Checks included:

- All dated March 15 rows and relevant body terms in normalized Linuxiarz, combined paste, and k4be exports.
- Saved Linuxiarz Wayback bodies and classifier material, plus the earlier Linuxiarz-specific audit's negative result.
- Read-only queries of `tmp/shellac_extracted/agent-reading-pack-20260905/agent-text.sqlite`: March 15 timestamps; Linuxiarz documents containing compensation/Australia terms; and Linuxiarz `hello test` candidates. The latter recovered only a May 26 test paste (`b8325931`), not this March sequence.
- Targeted local transcript searches for the distinctive phrasing. Located copies trace back to the supplied skeleton or later analysis of that skeleton, not a recovered March observation.

**Status: unresolved lead, not disproved and not a sourced onset date.** The normalized Linuxiarz export is selected and incomplete; failing to find the sequence there does not establish that it never existed. The simplest useful evidence is any one original paste ID, raw page/API response, or transcript excerpt identifying the three posts. With IDs, check the source metadata, actual intervals, and whether the compensation and Australian-filter records concern the same task or only occur near one another in a public feed.
