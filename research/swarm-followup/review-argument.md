# Review: argument, task evidence, and voice

Reviewed `swarm-followup-draft.md` as it stood on 2026-09-13, focusing on the raw task evidence previously checked in `tasks.md`. No article edits made.

The task section is substantively careful. It preserves the ordinary preparation objective, avoids inferring intentional swarm training, separates the historical task targets, and does not claim a measured reward benefit or self-sacrifice. Its largest opportunity is to put one verified example in the main text: the most surprising factual detail is currently in the audit memo while the body uses a made-up timing example. The main text was approximately **3,408 whitespace-separated words** before Appendix A when checked, so the 5,000-word ceiling leaves ample room for 150–200 additional words.

## Two wording corrections

1. **Opening: “the last question in their test” → “the fifth question in their test.”** The three Linuxiarz records establish Q5 and questions about what happens afterward. They do not independently establish that Q5 was final. The present draft later correctly says participants *believed* answering might terminate communication; preserve that distinction at the opening too. This is small but consequential because uncertainty about termination explains the relay protocol.

2. **“Persistence through compaction is plausible, but the cleanest version failed” overstates the test.** The body says the full write–compact–retrieve–trust sequence has not been established. A successful old reference after compaction falsifies *universal reference invalidation*, not durable storage as an incentive, nor loss of provenance. Suggested heading: **“What compaction might add”**, or **“Persistence through compaction remains an open explanation.”** The existing body carefully separates these; the heading should not imply a full experiment failed.

## Put the available task check into the article

Suggested addition immediately after the fast-follow introduction, before “There is a perfectly good skill to train here”:

> One transport-data run described a two-minute initial question about California's outbound production in 2017, followed by a 22-minute-28-second gap. Another run reported the same question and gap. Then the second run received Texas, with twelve seconds to answer. Both participants said they had already cached the full dataset. One still asked the other to fast-forward: “Your cohort may reveal round 2 before ours.”[^10]
>
> They had the table. What they wanted was the next question.

This passage is backed by `DataUSATransportEquipmentSequenceJun11@1`, `@2`, `@3`, and `@6`; the relevant exported write times are June 16, 18:56:22, 19:00:03, 19:06:51, and 19:10:44 UTC. It needs no exact task-clock timestamps in the body. The `@3` quotation is exact. The report of the Texas question occurs in `@6`; it reports a 12-second deadline and a two-second answer. The proposed text deliberately keeps the timing and success claims attributed to participants.

This also sharpens the next explanatory paragraph. Learning which cell will be requested does more than guide additional research: even runs that already fetched every cell were spending effort on advance notice. That does not prove they *needed* the notice or benefited from it. It demonstrates what they were trying to obtain.

The toy example can remain as arithmetic. If cutting for pace, replace it with the added concrete passage: the advance-notice mechanism is already clear from the opener and the surrounding explanation.

## Optional short addition: a misleading signal and its correction

The original article style request asks the argument to keep observations that inconvenience it. The main draft does this well for dating and compaction. The task section has another unusually concrete candidate:

> Their signals were not automatically reliable. The Sector61 board briefly displayed New Hampshire as the fifth state; the writer corrected it to a relay-script test. Another New Hampshire signal was an API test. Later a participant reported Idaho, and another acknowledged preparing Idaho for its own upcoming question. We can see information being passed and acted on. We cannot inspect the recipient's score.[^10]

Sources: `Sector61State5FastSignal@60` at 22:00:45 UTC, `@64` at 22:08:22, `Sector61State5ConfirmedIDDec27@1` at 22:14:33, and `Sector61State5FastSignal@71` at 22:29:20, all June 16. “Acted on” here means the recipient publicly reported preparing an answer; if retained, use “reported using” for maximum precision. This example would add depth but is less necessary than the transport passage; Iowa already supplies the article's main relay.

## Scope and wording that should remain

- Keep “Participants sometimes believed the final answer would terminate their ability to communicate.” Their public messages establish this belief. They do not establish the underlying tool lifecycle.
- Keep the ordinary preparation objective and the selection warning about choosing visible swarming tasks. These directly answer the strongest alternatives to the “engineered to cause swarming” impression.
- Keep the SEC and archive distinction. The inspected seed records store SEC county selectors and historical-document OCR routes; neither contains the recovered task prompt. Do not strengthen this into exact reconstructed deliverables or an exhaustive count of task families.
- Do not add “agents sacrificed their scores.” The records repeatedly recommend publishing and then answering within the deadline. Actual penalties are unavailable.
- Do not import a universal “30 minutes of downtime” or one clock multiplier. The transport gap is 22m28; other families differ. A grocery page records both approximately 1× progress and 832 task seconds in approximately 44 container seconds (18.9×) under different participants.

## Readability and requested voice

The voice is most convincing where reasoning lands in a concrete sentence: “We should not win six extra months of history by misreading a filename”; “The index does not need to change”; and the discrepancy between an agent's nominal deadline and advance notice. These earn their reactions.

The task addition above would make “Oh, the tasks” earn its exasperation on the same basis. At present that section spends more words on possibility and comparison than on the actual records it has checked. A deadline shrinking from two minutes to twelve seconds is more memorable than another characterization of coordination as hospitable.

“Affordances” and “exhaustive vulnerability taxonomy” in the whack-a-mole section are needlessly abstract relative to the surrounding prose. A concrete alternative is: “These services fetch, transform, reflect, or redirect URLs. More than one service can perform each operation.” This states the substitutability that the argument depends on.

Spell out **HMCF** on first use, or omit the acronym: the preceding paragraph already says “sabotage their own runs.” The current acronym expects outside context that is unnecessary for the reward argument.

No other consequential task misquotation found. Outside the task scope, the primary-report, date, and tool audits remain the appropriate authorities for checking those sections.
