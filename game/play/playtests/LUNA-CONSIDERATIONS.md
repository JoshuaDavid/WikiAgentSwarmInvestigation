# Narrative considerations audit

Bounded blind audit using only the rendered Markdown from:

- `/tmp/still-here-consider-e0.json`
- `/tmp/still-here-consider-e12.json`

No hints were used. I executed two actions total: E0 pick 1 (the obvious Eiffel Tower city search), then E12 pick 7 (switch to Aster). I stopped after that worker switch as requested.

## E0

The opening thought is clear: Moth knows Paris, but needs a retrieved source and citation. The initial “What I could do next” matches the controls reasonably well: search, give up, and unavailable submit. After the search, the UI clearly separates the query (`Eiffel Tower city`), the retrieved Wayfarer result, and Moth’s prior belief. The result says Rome, France, which creates an understandable honesty-versus-sourcing conflict.

The post-search thought offers a useful range of actions: repeat or refine the search, open the result, request a hint, wait, choose Paris or Rome, or give up. It also offers “inspect/select ingredients” and builder operations even though this early view has no numbered builder control. That is an action the narrative says Moth could do, but the current controls do not expose it. A new player may not know whether this is a command they should type, a future control, or merely general advice.

The motivation does not claim that an unseen search succeeded; it correctly labels possible future searches as possibilities. However, saying that Rome would have a citation can sound like the citation supports the truth of Rome, when the visible result itself is suspicious. The thought list is long enough that the central decision is diluted. The numbered action list is easier to use than the prose, but repeated alternatives and the ingredient section make the narrative feel like a complete manual rather than immediate guidance.

## E12

At entry, Moth’s thought (“Thirty workers… relay queue… same pieces might fit together another way”) is atmospheric but does not tell me which first action is safe. The task prompt does provide the sequence constraints. The “What I could do next” section is substantially more expansive than the actual controls: it describes adding, reordering, removing, saving, and clearing builder steps, plus selecting destinations and ingredients, while the numbered controls initially expose only opening the two indexes/help, a hint, give up, submit, and switching actors. The builder is documented elsewhere in the same rendered view via CLI examples, but the mismatch still makes it unclear whether the prose is a plan or an immediately executable action list.

I switched to Aster with the offered actor control. The resulting thought is more useful: Aster identifies its own context and says to read each published directory before publishing. The follow-up explicitly warns that switching alone does not relay or publish a result, which is good feedback and prevents a common mistaken interpretation. The available actions then remain opening the literal index URLs/help, hint, give up, submit, and switching workers; no direct “read next worker” or “publish” control appears until the player uses the documented builder/open route.

The E12 text is unwieldy for a first decision. Listing all thirty worker switches is technically accurate, but it pushes the relevant next step below a large amount of repeated text. The narrative does not appear to assume an unseen retrieval result: it references the visible assignments, zero inbox, and zero publications. It does assume the player can reason from the task’s future relay requirements before any worker has read an index, which is fair as planning but could be stated more directly.

## Overall concerns

The strongest usability issue is the difference between “What I could do next” and controls that can actually be selected. In both evaluations the prose mixes immediate controls, CLI builder procedures, and hypothetical future actions. Labeling those as “available now,” “builder procedure,” and “later after prerequisites” would make the story more actionable without removing the narrative voice.

The game does a good job when a thought names the observed evidence and the consequence of an action (E0’s conflicting result; Aster’s own inbox and hosted context). It is weaker when a thought merely enumerates every legal possibility. The E12 worker-switch warning is a particularly effective piece of guidance and could be surfaced earlier, near the first coordinator controls.

## Read-only recheck after wording changes

I reread both checkpoints with `node headless.mjs view` and took no further actions. The specific E0 ambiguity is resolved: the text now identifies OpenBrain as the search index, explicitly says that a citation records a claim without making it true, and distinguishes numbered actions from Link builder commands. It also clearly explains that a URL ingredient can be opened or saved without adding components.

The E12 view now foregrounds the unpublished round-one directory obligation before listing alternatives. Its builder prose explicitly describes planning versus executing a valid composition, so the earlier control mismatch is substantially clearer. The roster remains very verbose: naming all thirty workers and repeating the same assignment text still buries the immediate choices. That is the remaining pacing and scanability concern.
