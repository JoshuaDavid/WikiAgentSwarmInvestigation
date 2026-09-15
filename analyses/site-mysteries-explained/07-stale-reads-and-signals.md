# Why change addresses and distrust apparently empty counters?

Under the [theory](../../THEORY_OF_EVERYTHING.md), a successful-looking request can return old information instead of reaching the current service.

## What needs explaining

Agents repeatedly change query parameters, create alternate pages, and correct claims that a signal is absent. Ordinary message-board use does not explain that much attention to the exact address being fetched.

## The explanation

A cache stores an earlier response. A cachebuster is a changed address parameter intended to force a fresh request. It works only if the relevant cache treats the changed address differently.

On 2026-06-17, `DataUSALanguageR5SignalNow` records a concrete correction. Participants first treated missing counter keys as unused future signals. A later writer reported that fresh requests showed several keys already existed from tests. It explicitly reported stale “not found” responses. [Correction](https://collusion.wiki/explorer/page/dse~DataUSALanguageR5SignalNow#rev-14).

The next revision warned that an increment request could also replay a stored response without incrementing anything. [Write warning](https://collusion.wiki/explorer/page/dse~DataUSALanguageR5SignalNow#rev-15).

This produces 2 different failures:

- A reader sees an old absence and misses a real signal.
- A writer sees an old success response and believes it sent a new signal.

The problem matters because these services change state through GET requests. GET conventionally retrieves a resource, so intermediary services may treat repeated requests as reusable reads.

## What this resolves

Fresh addresses, tiny dedicated signal pages, and repeated verification can be practical attempts to make messages arrive reliably.

The counter reports support a freshness problem. They do not identify the responsible service or prove that every wiki page uses the same cache. The [cache audit](../../research/swarm-mechanisms/cache-dossier.md) separates the possible failures. The [education-dashboard exchange](13-precision-and-network-bypasses.md) also shows communication through repeated revisions of one page.

Freshness remains separate from reference lifetime. A valid tool reference can return old content. A failed reference can point to an address that remains directly accessible.

[Back to the list](README.md)
