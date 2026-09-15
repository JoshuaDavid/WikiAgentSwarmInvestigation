# Why publish links to empty numbered pages?

Under the [theory](../../THEORY_OF_EVERYTHING.md), an agent can publish future destinations before a reader needs their contents.

## What needs explaining

The explorer contains an index named `AgentOpenAIDataUSAHubMay13X7`. Its first preserved revision links to 30 numbered pages. The first preserved contents for those pages arrive later. [Index](https://collusion.wiki/explorer/page/dse~AgentOpenAIDataUSAHubMay13X7#rev-1).

## The explanation

A cache stores a fetched response. If a reader keeps receiving the first response, adding links to the original page will not reach that reader.

The theory adds another restriction: a reader may need a link from an accepted page before it can open a destination. Publishing a directory of future destinations can address both problems.

Consider page 22. These publication times use Coordinated Universal Time:

1. At 19:41:35 on 2026-06-16, a writer publishes the index, including its link to page 22.
2. At 21:46:26, a writer fills page 22 with DataUSA queries for several states.
3. A reader follows the index's existing link after page 22 has useful content.

The first 2 steps appear in the revision history. The third describes how the arrangement could help. The gap between the recorded writes is 2 hours, 4 minutes, and 51 seconds. [Page 22](https://collusion.wiki/explorer/page/dse~AgentOpenAIDataUSASlotMay13X7_22#rev-1).

Even an old copy of the index contains the needed link. The reader does not need to see an updated index.

## Conditions and limits

The destination must return useful content when the reader follows it. An earlier fetch could have stored an empty response. Automatic fetching by another service could also interfere.

The export contains 8 populated slot pages, not 30. Some slots were revised after creation. Thus this is evidence of prepublished destinations, not a universal rule that each page was written only once. Our [evidence checks](outputs/checks.json) verify the counts and timing. [Slot 1's second revision](https://collusion.wiki/explorer/page/dse~AgentOpenAIDataUSASlotMay13X7_01#rev-2) demonstrates reuse.

[Back to the list](README.md)
