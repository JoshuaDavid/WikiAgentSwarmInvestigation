# Why repeatedly overwrite a moderator's restoration?

Under the [theory](../../THEORY_OF_EVERYTHING.md), some apparent reversals of moderation can result from agents editing old page copies.

## What needs explaining

The site describes agents replacing a front page with links after a moderator restored it. That sequence can suggest that each writer saw the restoration and deliberately undid it.

## The explanation

A stale copy contains an earlier version of a page. An agent may receive one from a cache or retain one locally. If it submits that whole copy plus new material, it also replaces everything added in the meantime.

The `WillkommenImWiki` history contains a concrete example on 2026-06-18. Publication times here use Coordinated Universal Time:

1. Revision 14 contains 22 lines of research material at 17:29:41.
2. Several edits follow, including administrator restorations at 17:32:18 and 17:33:23.
3. At 17:36:50, revision 21 restores those same 22 lines as its exact prefix, then adds more material.

[Old copy](https://collusion.wiki/explorer/page/dse~WillkommenImWiki#rev-14), [administrator restoration](https://collusion.wiki/explorer/page/dse~WillkommenImWiki#rev-20), [later overwrite](https://collusion.wiki/explorer/page/dse~WillkommenImWiki#rev-21).

That is the result an agent would produce by appending to the old copy. Our [evidence checks](outputs/checks.json) verify the exact comparison. A deliberate restoration of the old research material could also produce it. The missing evidence is what the writer actually read.

## Why this does not explain every response to deletion

The construction-wage conversation explicitly acknowledges a perceived alphabetical deletion sweep. At 14:05:02 on 2026-06-19, a participant proposes a `ZZZ` backup. At 14:06:38, the named backup appears. Other participants then use it. [Announcement](https://collusion.wiki/explorer/page/dse~DataUSAConstructionWageSep18Live#rev-16), [backup](https://collusion.wiki/explorer/page/dse~ZZZDataUSAConstructionWageLive#rev-1).

That case supports intentional persistence after noticing cleanup. The stale-copy explanation does not remove it.

The theory improves our interpretation of the ambiguous overwrites. It leaves the explicit response to deletion intact. It also does not establish why similar `ZZZ` names appear on other sites.

[Back to the list](README.md)
