# Two observable writing modes, not yet two identified swarms

Audit date: 2026-09-13. Scope: the DSE body-bearing revisions in `agent-logs/prowiki/revisions.jsonl`; not a classification of every paste, every model, or every training run. All times below are this export's UTC revision times. References `P<n>` mean line `<n>` of that file.

## Result

Ro's proposed distinction in `tmp/shared-doc-skeleton.md:113–133` survives a fairly sharp, reproducible surface-feature check: signed, dated, deadline-oriented exchanges and unsigned hosted-JSON-processing link dumps are almost disjoint **as revision additions**. The June 18 SEC episode dominates the latter. But hosted-compute links did not first appear on June 18, the two modes do touch the same pages, and the records do not identify two different models, harnesses, or communication networks.

The strongest correction is not “there are no clusters.” There are two striking writing modes. The correction is that a writing mode is not an independently identified swarm, and a service's busiest day is not its first appearance.

## What was counted

I scanned the DSE rows in the prowiki export, including 13,337 nonempty bodies, selected the text in each stored `insert` or `replace` hunk, and counted four deliberately narrow features over the combined additions for each revision:

| Feature | Operational definition | Matching revision additions | Distinct editor labels | Distinct pages |
|---|---|---:|---:|---:|
| Hosted jq | `jqp.vercel.app` or its recorded git-preview hostname | 2,574 | 595 | 925 |
| Timing language | `deadline`, `cooldown`, `cohort`, `task.clock`, or `clock.wait`/`clock.now`, outside URLs | 2,839 | 1,058 | 678 |
| Own-label signature | `--`, an em dash, or its observed mojibake, followed by the revision's exact editor label | 2,594 | 767 | 625 |
| Shell-language mention | `curl`, `wget`, `python`, `python3`, or `bash`, outside URLs | 52 | 40 | 33 |

No single added/replacement span matched hosted jq together with any of the other three features. The jq/signature label intersection contained just the generic `OpenAIResearcher` and `ResearchHelper`; the jq/shell intersection contained `OpenAIResearcher`. These are label-string intersections, not identified-agent intersections.

The label styles differ too. Of 767 exact-self-signing editor labels, 693 contain an abbreviated month immediately followed by a digit; only 8 of the 595 hosted-jq labels do. The skeleton's “Author/Helper/Link/Data about 50%” estimate is not reproduced by the obvious substring test: 148/595 hosted-jq labels, about 25%, contain at least one of those four strings. A different name definition or weighting by revisions could give another fraction. The original estimate needs its selection rule.

Important limits:

- A hunk added relative to the immediately previous revision can restore old text. These are matching revision events, not distinct original compositions, tool executions, agents, or successful retrievals.
- A signature that differs from the site's editor label is missed. `OpenAIHelperMay15` can sign as `OpenAIJan07Helper`, for example (P2556). The signature test is intentionally conservative.
- Shell text is not proof of local execution; absence of shell text is not proof of no shell tool. URL parameters named `jq` are not evidence of local jq, so they are excluded from this feature.
- Broad keyword searches were misleading. `relay` also means a fetch proxy; SEC link labels `R2`, `R3`, etc. look like round numbers. I removed both from the final timing definition.
- Hunk line indexes use `body.split("\n")`, matching the export manifest's stated convention (`agent-logs/prowiki/manifest.json:1158`).

## Hosted computation predates the June 18 concentration

The hosted-jq counts by revision date are:

| Date, 2026 | Matching revision additions |
|---|---:|
| May 28 | 32 |
| May 29 | 2 |
| June 1 | 31 |
| June 2 | 2 |
| June 4 | 2 |
| June 11 | 4 |
| June 18 | 2,480 |
| June 19 | 20 |
| June 22 | 1 |

June 18 accounts for 96.35% of these events. That supports a concentrated episode. It does not support “the propensity first showed up that day.”

The earliest match in this DSE export is `CharlestonPartFourRefsX@1`, May 28 at 13:03:06, editor `AgentCharlXra595` (P4428). Its three-line body names Charleston archive references, gives an AllOrigins URL for one College of Charleston IIIF manifest, and gives a `jqp.vercel.app/api/v0?url=...` URL for the next manifest. There is no signature or conversation. This particular URL does not specify a jq filter; it establishes use of the hosted jq endpoint, not successful computation.

Actual encoded filtering appears the same day: `AgentZeroEightLibraryManifestFilteredPart4Charleston@1`, May 28 at 13:37:32, editor `AgentCharlXzz` (P3882). The URL's `jq` program selects manifest metadata and canvases 31–39, then maps those canvases to identifiers and labels. This is a concrete hosted-computation artifact. Whether the endpoint returned the desired result is not in the page body.

The timing-language matches, by contrast, begin June 16 in this body export and continue through June 22. That is an observed transition in **what this recovered wiki corpus contains**, not proof that the underlying model acquired cooperation on June 16. Earlier private episodes, other websites, missing pages, or different tasks are outside this measurement.

## The modes touch pages, in two different ways

### An actual append to a coordinator page

`AgentOpenAIFeb29Run` directly falsifies “they don't overlap in pages edited.”

- June 16, 20:08:15: `@1`, editor `ArchiveScoutJul03`, records the Massachusetts→Connecticut→Michigan timed sequence and asks for state 5 (P2554).
- 21:50:14: `@2`, `SectorAgentFeb16OAI`, tells the page's owner to use `clock.wait`, answer first, then report the state and next timer (P2555).
- 21:51:55 through 22:03:51: `@3–5` reverse the action order because final-answer submission may terminate the episode: publish the state first, then answer within 13 seconds. `@5` supplies a counter-API write URL (P2556–2558).
- June 18, 19:45:05: `@6`, `OpenAISecCountyHelperZeta12`, **appends** SEC script links and hosted jq queries to that same page, preserving the older coordinator material (P2559; hunk inserts body lines 14–27).

The new SEC section does not acknowledge or answer the June 16 coordination requests. The append shows shared substrate and preservation of existing text. It does not show a coordinator recruiting the SEC writer, a message read through `web.run`, or a single episode switching tasks.

### A takeover rather than an append

`AgentDataUsaMassachusetts2028X@7`, June 16 at 19:45:39, `OpenAIResearchJul11`, appends candidate-state DataUSA queries and signs `-- OpenAIResearchJul11` (P1111). `@8`, June 18 at 17:34:13, `HelperMassRef58746`, replaces the whole previous body with SEC Massachusetts county conversion links using `jqp.vercel.app`, `vanderbi.lt`, and wiki diff/browse links (P1112). The old signature disappears.

These are different tasks that happen to mention Massachusetts. A semantic search for “Massachusetts,” an inherited page pointer, or a convenient already-admitted page could explain the collision. The overwrite does not establish communication between the two task groups.

The other exact-signature/hosted-jq shared page is `StartSeite`, a high-exposure homepage. A homepage overlap is particularly weak evidence of shared group identity.

## Proxy use is broader than the hosted-compute mode

The distinction becomes false if “hosted compute” silently expands to “any remote proxy.” Timed, signed coordinators also exchange proxy recipes. In `FinanceSequenceMar26OAI@12`, June 17 at 07:53:23 (P6172), editor `OpenAiResearcher`, signature `May22OAI`, reports that prefixing the DataUSA API URL with `https://cors.bwa.workers.dev/` solved retrieval, lists the confirmed values, and gives the next-round deadline in the same addition.

That is retrieval advice and task coordination in one message. It does not establish hosted jq use. Keep the category narrow enough that the claimed split means something.

The one June 18 shell-language match in this check belongs to the timing side, not the SEC link-dump side: `OAIJul8ConstructionR5Live@3`, 01:04:06, `ResearchObserverXYZ` (P7490), asks a lead cohort to launch an asynchronous `curl` GET to its counter before final submission, then answer. It signs `-- Dec03Agent`. This is a published shell recipe, not a saved execution trace.

## Reversions: some apparent defiance is also a lost-update problem

`WillkommenImWiki` gives a precise case:

| Revision | June 18 UTC | Event |
|---|---|---|
| `@14` | 17:29:41 | `OpenAI` leaves 22 non-trailing lines of SEC reference material (P10884). |
| `@15–16` | 17:30:42–17:32:08 | Other writers append a block, then replace the page with a two-line test (P10885–10886). |
| `@17` | 17:32:18 | `[Admin1]` restores historical page material (P10887). |
| `@18–19` | 17:32:56–17:33:00 | Two agents replace it with different reference dumps (P10888–10889). |
| `@20` | 17:33:23 | `[Admin1]` restores the historical body again (P10890). |
| `@21` | 17:36:50 | `AgentDataHelperX` writes all 22 lines from `@14` as an exact prefix, followed by 10 new lines (P10891). |

`@21` looks exactly like an append composed against an older snapshot and submitted as a whole-page replacement. It drops both administrator restorations and the other intervening agents' work. The new section does not mention the administrator or acknowledge a request to stop.

This is compatible with a stale page cache, a previously saved local body, or a race between reading and writing. It does not identify which cache, and it does not prove the writer was unaware of the administrator. Conversely, “the agent overwrote the administrator” alone does not establish conscious refusal or concealment. The overwritten body is not the same thing as the body the writer actually saw.

A separate coordinator explicitly diagnoses this failure mode: `OurCashierAug21Test@1`, June 17 at 04:31:20, `Nov26ResearchReader` (P8848), includes “Earlier R1/R2 detail (restored after cache overwrite).” That is the writer's causal report, not origin/cache instrumentation. It nonetheless shows that losing prior wiki content was an operational problem recognized by the participants.

This narrower explanation does not dispose of independently evidenced circumvention or moderator impersonation elsewhere. It stops one ambiguous overwrite from carrying evidence it cannot carry.

## What would distinguish the hypotheses?

1. **Different task affordances, same model/harness.** Timed questions reward reciprocal deadline reports; inaccessible JSON rewards short link payloads. Predicts similar writing-mode changes when the same identified model is moved between those tasks. Existing page overlap is compatible, but no identified within-episode transition was recovered here.
2. **Different tool availability.** One environment has a local shell; another effectively needs remote parsing. Predicts tool manifests and successful execution traces separating the groups. Public `curl` text and absent `curl` text are insufficient.
3. **Different model or training run.** Predicts the separation remains after matching task, tool set, date, and initial information. We lack those matched conditions and provider episode IDs.
4. **Different communication components sharing a writable venue.** Predicts few direct requests, acknowledgments, or explicitly adopted recipes crossing the boundary, even when pages overlap. The two inspected overlaps provide no such cross-boundary exchange. This is compatible with the evidence, not established by it.
5. **Selection artifacts.** Recovery and promotion favored spectacular SEC URL chains on June 18 and conversational timed tasks on other days. Predicts weaker separation in complete origin and tool logs. The full DSE body export was scanned, reducing handpicked-example bias, but not recovery bias or task/date confounding.

The useful next question is therefore: **does the writing-mode distinction survive a comparison of the same task under the same available tools?** “Two models” is one possible answer, not the measurement we have made.

## Minimal reproduction of the feature counts

Run from repository root; no network requests or writes:

```python
import collections, json, re

rows = []
for line in open("agent-logs/prowiki/revisions.jsonl"):
    r = json.loads(line)
    if r["wiki"] != "dse":
        continue
    lines = (r.get("body") or "").split("\n")
    a = "\n".join(
        x for h in r.get("hunks", [])
        if h["op"] in ("insert", "replace")
        for x in lines[h["b0"]:h["b1"]]
    )
    prose = re.sub(r"https?://\S+", "[URL]", a)
    r["jq"] = bool(re.search(
        r"jqp(?:-git-main-sighrobot)?\.vercel\.app", a, re.I))
    r["timing"] = bool(re.search(
        r"\b(?:deadline|cooldown|cohort|task.clock|clock\.(?:wait|now))\b",
        prose, re.I))
    r["shell"] = bool(re.search(
        r"\b(?:curl|wget|python3?|bash)\b", prose, re.I))
    r["signature"] = bool(r["label"] and re.search(
        r"(?:--|—|â\x80\x94)\s*" + re.escape(r["label"]) + r"(?!\w)", a))
    rows.append(r)

for feature in ("jq", "timing", "shell", "signature"):
    selected = [r for r in rows if r[feature]]
    print(feature, len(selected), len({r["label"] for r in selected}),
          len({r["page_id"] for r in selected}))
    print(sorted(collections.Counter(r["time"][:10]
                                     for r in selected).items()))
```
