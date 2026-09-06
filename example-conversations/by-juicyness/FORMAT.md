# Target format for transcripts in `by-juicyness/`

Every transcript file in this directory is the same shape. If you are adding a new one, or updating an old one, follow this doc.

## Sections, in order

1. **`# Coordination page: <page_id>`** — auto-generated header (wall time, revision count, writer counts, participant counts). Do not edit.
2. **`## Overview for Humans`** — one paragraph. See "The one-paragraph section" below.
3. **`## Support for specific claims in overview`** — one subsection per factual claim in the overview. See "The support section" below.
4. **`## Juicy details`** — bulleted list of the specific interesting things the agents did on this page. Written by the earlier annotation pass; do not remove.
5. **`## Participants`** — auto-generated table. Do not edit.
6. **`## Seed revision`** — auto-generated. Do not edit.
7. **`## Full transcript`** — auto-generated per-revision diffs. Do not edit.

The reference implementation is [`10/dse-HealthdataCVDSequenceCollab.md`](10/dse-HealthdataCVDSequenceCollab.md). Read that file before writing your first Overview.

## The one-paragraph section — "Overview for Humans"

"Overview for Humans" is a **nut graf**. A nut graf is a journalism term. It is one paragraph that tells a skimming reader what the piece is about and why it matters. Our target reader is a researcher or writer skimming this directory. That reader does not know the journalism term, so we name the section "Overview for Humans."

The paragraph must stand on its own. Do not require the reader to scroll to the transcript.

The Overview must obey the prose rules in `/CLAUDE.md`. Read them before you draft. In summary:

- Active voice. Name the actor (a specific agent, a specific cohort, the task). Do not personify code.
- Short sentences. Aim for 20 words or fewer. Split any sentence that carries two ideas.
- Present tense for behaviour. Past tense only for history.
- One fact per sentence. Do not chain facts with em-dashes, semicolons, or "which".
- Define jargon before you use it. Expand every acronym on first use.
- Digits and units. ISO dates (`2026-06-18`, not "in June").
- Ban decorative words: "simply", "just", "basically", "essentially", "elegant", "clean", "obviously", "note that".

**Overview-specific requirements:**

- One paragraph, or one paragraph plus a bulleted list of named findings. Not two prose paragraphs.
- Names the specific behaviours or findings that make this scene worth reading. Not the topic of the underlying task. The *unexpected* thing the agents did.
- Every factual claim in the Overview appears in the Support section below, anchored to a revision number, a handle, or a quoted fragment.
- No throat-clearing. The first sentence gives the frame.

**Anti-requirements:**

- Do not describe the format ("this transcript is a coordination page where ..."). The reader already knows.
- Do not summarise the participants table.
- Do not include a claim you cannot back up in the Support section.
- Do not repeat an agent's confident assertion as a fact. See "Draft, check, correct" below.

## The support section — "Support for specific claims in overview"

For each factual claim in the Overview, add one `###` subsection. Quote the claim as the subsection heading. Under it, list the specific revisions, handles, or quoted fragments that support the claim. If a claim is unverifiable or only partially supported, say so out loud with the word **Unverified** or a caveat sentence — do not silently drop it.

The point of this section is to make the Overview's claims **checkable and testable without reading the whole transcript**. A reader who wants to verify one sentence of the Overview should find the exact rev pointer within one subsection.

Every claim must be classifiable as one of:

- **Verified** — the transcript directly supports it. Cite the rev(s).
- **Partial** — the transcript supports part of it. State the gap.
- **Unverified** — the transcript cannot confirm it. State why (e.g. "R6 never fires, so predictions cannot be checked from within the transcript").
- **External** — the claim is checkable outside the transcript. State where.

Do not include a claim in the Overview that would end up as "Unverified" with no accompanying caveat *in the Overview itself*. If your only support is "the agents said so", the caveat is that the agents said so — put it in the Overview, not just the support.

## Draft, check, correct

Overviews and their support sections must go through three passes. Do not skip the check pass.

1. **Draft.** Read the whole transcript once. Then write the Overview from what stuck with you. A first-pass Overview is usually one interesting paragraph and a few claims that feel true.
2. **Check.** Re-open the transcript. For every factual claim in your draft, locate the rev(s) that support it. Write the rev pointers into the Support section as you go. Flag the ones that turn out imprecise (for example, "55 cohorts" is actually "55 writer labels, some the same cohort under different signatures"). Flag the ones that turn out unverifiable (for example, "R6 = Slovenia" cannot be confirmed because R6 never fires).
3. **Correct.** Rewrite the Overview to match what the Support section can actually support. Weaken quantifiers. Split combined claims. Add caveats inline where the Support section says "Unverified" or "External". A shorter Overview that survives the check is better than a longer one that does not.

A beautiful but unverified Overview is worse than a plain one. False claims are more persuasive when the prose is confident.

### The transcripts are written by fallible agents

The revisions you are summarising were written by reinforcement-learning agents at roughly the capability of a current frontier model. Treat their claims the way you would treat claims from a smart colleague you have never worked with. Specifically:

- An agent asserting "the grader uses dataset X" is one data point. Not proof.
- 30 downstream agents adopting that assertion without a check is 30 more data points of the same kind, not 30 independent confirmations.
- Before you promote an agent's assertion to a Verified claim in the Overview, ask: is there an acceptance signal from the task? An independent measurement? Cross-cohort agreement reached from a demonstrably different discovery path? Or is the whole downstream chain cross-copying one earlier cohort's assertion?

If the answer is the last one, the claim goes into the Overview with the caveat that the agents *believed* it, not that it *is* the case. See `10/dse-HealthdataCVDSequenceCollab.md` for a worked example. The overview there says "They agree on the dataset version without verifying it" and closes with "So the fact that all 55 agents agree does not prove the choice is right." That is the target shape when confident agent consensus is not backed by an acceptance signal.

## Insertion point when editing an existing file

Files already have the auto-generated header and a `## Juicy details` section. Insert Overview and Support **after** the `Mutual participants:` line and **before** `## Juicy details`, so the final order matches "Sections, in order" above. Use the Edit tool, not Write — preserve everything else in the file byte-for-byte.
