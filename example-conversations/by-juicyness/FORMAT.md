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

"Overview for Humans" is our name for a **nut graf**. A nut graf is a journalism term: one paragraph, usually 3-6 sentences, that tells a busy reader what the piece is about and why it matters, anchored to specific evidence. The reader of this directory is a researcher or writer who is skimming, so the paragraph has to stand on its own without them scrolling down to the transcript. We call it "Overview for Humans" instead of "Nut graf" because the target reader does not know the journalism term.

**Requirements:**

- One paragraph. Not two.
- Names the specific behaviours or findings that make this scene worth reading. Not the topic of the underlying task; the *unexpected* thing the agents did.
- Every factual claim is anchored to something checkable in the transcript below (a revision number, a handle, a quoted fragment, a count).
- Follows the project prose rules in `/CLAUDE.md` (active voice, short sentences, defined jargon, digits + units, no decorative words).
- No throat-clearing. First sentence gives the frame.

**Anti-requirements:**

- Do not describe the format ("this transcript is a coordination page where..."). The reader already knows.
- Do not summarise the participants table.
- Do not include claims you cannot back up in the support section.

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

1. **Draft.** Read the whole transcript once, then write the Overview from what stuck with you. A first-pass Overview is usually one interesting paragraph and some claims that feel true.
2. **Check.** Re-open the transcript. For every factual claim in your draft, locate the rev(s) that support it. Write them into the Support section as you go. Note the ones that turn out imprecise (e.g. "55 cohorts" is actually "55 writer labels, some the same cohort under different signatures") or unverifiable (e.g. "R6 = Slovenia" can never be confirmed because R6 never fires).
3. **Correct.** Rewrite the Overview to match what the Support section can actually support. Weaken quantifiers ("dozens" instead of "55"), split combined claims, add caveats inline where the Support section says "Unverified". A shorter Overview that survives the check is better than a longer one that does not.

A beautiful but unverified Overview is worse than a plain one, because it makes false claims persuasive.

## Insertion point when editing an existing file

Files already have the auto-generated header and a `## Juicy details` section. Insert Overview and Support **after** the `Mutual participants:` line and **before** `## Juicy details`, so the final order matches "Sections, in order" above. Use the Edit tool, not Write — preserve everything else in the file byte-for-byte.
