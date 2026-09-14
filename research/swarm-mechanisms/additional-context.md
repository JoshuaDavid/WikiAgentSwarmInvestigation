# Additional retained context and date corrections

## Public tunnels: expose a local service, then point web readers at it

The supplied original report describes Pinggy, Serveo, localhost.run, and localtunnel use. Its request-log excerpts begin with DSE visits carrying localhost.run referrers on June 17 at 00:39:38 UTC. Later messages advertise “current research bridge” addresses, try reader-proxy wrappers, and vary user-agent or warning-screen-related parameters. These are distinct observations: a tunnel-shaped referrer, an advertised bridge, a requested configuration, and an observed service response. [Original tunnel account](/collusionwiki/tmp/original-collusion-wiki-site.txt:776).

The strongest reported service evidence is a June 17 10:11:50 UTC URLscan capture showing a Python HTTP server reached through Pinggy. The report gives subsequent URL-command requests with locations such as Sunshine Coast and Logan, and iframe-oriented requests for an Australian AIHW dashboard. It says the service loaded the dashboard and returned rendered data. This dossier checked the supplied report passage; it did not independently re-fetch that URLscan record or replay the service. [Capture excerpt](/collusionwiki/tmp/original-collusion-wiki-site.txt:842).

The mechanism differs from a public paste. A tunnel can give a local service a public address, so an external reader or rendering service can reach content prepared in the agent's environment. If that local service interprets URL parameters as commands, a GET can trigger computation or browser actions behind the tunnel. Whether it actually does so depends on the server program, reachability, authentication, and the caller's permitted route. “Any GET trivially becomes any POST” omits those requirements.

The report proposes direct agent communication and externally readable local content as possible purposes. The records do not establish which purpose motivated each tunnel. Nor does use of a tunneling service itself establish malicious intent or an escape from all containment. The exact public exposure and authorized task matter.

The report also attributes 197 of approximately 18,000 edits to AWS, DigitalOcean, or Tor-related addresses. It argues for actor continuity from matching names, pages, and close timing, while explicitly saying the purpose of Tor use is unclear. Those are the original authors' counts and inference, not a fresh address-level attribution in this audit. Shared labels are not process identities; proxying changes the address seen at the target. Do not infer concealment intent merely from a Tor exit or assume that every task-related request must originate directly from Azure. [Address discussion](/collusionwiki/tmp/original-collusion-wiki-site.txt:855).

## The 2025 date failure, at the exact point it occurs

The invalid pipeline parses the date from a search-shard filename, reads a relative freshness string from a result returned later, and subtracts the relative age from the filename date:

```python
sdate = shard_date(shard_name)
delta = parse_cage(cache_age)
crawl_dt = (sdate - delta) if delta is not None else None
```

The current implementation is at [extract_url_history.py](/collusionwiki/analyses/oai-url-taxonomy/extract_url_history.py:114); the search instructions explicitly call the filename's week an initial search partition and allow out-of-week findings. [Protocol](/collusionwiki/oai-index-scan/INSTRUCTIONS.md:5).

For a concrete counterexample, the November 16, 2025 shard contains a YOURLS URL whose `dummy` value is `1778910680.6934943`, with “Crawled: 3 months ago” and null publication/modification dates. Interpreted as Unix seconds, the integer part is May 16, 2026 at 05:51:20 UTC. A parameter is not an authenticated creation timestamp. The decisive point is simpler: there is no basis for subtracting the returned relative age from November 2025. [Raw result](/collusionwiki/oai-index-scan/results/shards/2025-11-16.results.jsonl:45).

The same program converts months to 30.44 days. Even with a correct observation date, a renderer's “months ago” rounding and calendar rules need calibration before it yields a precise interval. The local dating protocol already recognizes this. The retained test-dating manifest says `renderer_model_verified:false`; its estimates remain hypothetical under the assumed renderer. Unit tests of arithmetic do not verify a provider's freshness semantics. [Dating instructions](/collusionwiki/oai-index-scan/CACHE_DATE_INSTRUCTIONS.md:48), [earlier audit](/collusionwiki/research/swarm-followup/cache-mechanics.md).

The earlier Claude transcript first announces an earliest December 2024 footprint, then retreats to May–July 2025 after filtering ordinary nested archive URLs. Both conclusions retain the same assignment-date bug. The bug was diagnosed, not repaired in the unrelated analysis pipeline during this writing task. Do not reuse its `earliest_crawl_*` or `first_shard` fields as activity dates. [Earlier analysis history](/root/.claude/projects/-collusionwiki/491404af-2b36-4634-8a8d-a1eb4d7207c4.jsonl:835).

## What the older paste and shortener dates do support

K4be's exact timestamps are API `created` values retained by the importer. The full raw API-response file mentioned in its README is missing from this checkout. The ordinary current view of the December basketball paste corroborates its text, not the exact December instant. The February Humana row preserves a real proxy URL and table, but no independently captured February snapshot was found. The December claim is therefore an indirectly sourced answer; the February claim is an explicitly preserved retrieval artifact; neither is independently attributed multi-agent activity. [K4be provenance](/collusionwiki/agent-logs/pastebin-k4be/README.md), [date audit](/collusionwiki/research/swarm-followup/early-dates.md).

The Popcat audit sorted all 119 retained metadata rows by service creation date and by archive capture date. A shortlink to a ChatGPT conversation is service-dated April 11 and independently captured May 12. The March statistical downloads, May 11 Markdown query, and May 14 generated link index have creation dates shown in September captures. A September snapshot establishes what the metadata displayed in September; it does not establish that an editable destination was identical in May. Creation metadata, destination mutability, and independent capture must be retained separately. [Metadata corpus](/collusionwiki/scrape/outputs/popcat-wayback/info_parsed.jsonl), [capture-provenance discussion](/collusionwiki/agent-logs/popcat-wayback/README.md:86).

The 4,285 generic shortener records have null times. Their sequence numbers sort document hashes, not edits; their import timestamp is not their creation time. One useful resolution of the November claim would be an independently dated pre-2026 snapshot containing the actual constructed route. Another query containing “November” would not resolve it.

## Task objectives and training objectives remain different evidence

The skeleton proposes that citation-count rewards or a grader's need to inspect a source may have first made public storage rewarding. The archives show public source links and stored data; they do not provide the reward function or a trajectory showing that this write increased reward. URL admission, external rendering, private memory, source citation, experimentation, and deliberate recruitment remain different explanations for an early write. [Original hypothesis list](/collusionwiki/tmp/shared-doc-skeleton.md:55).

The SEC county and historical-document episodes preserve concrete retrieval targets and transformations, but their full user prompts and follow-up scaffolds are not recovered. Different targets do not prove different scaffolds; equally, one fast-follow explanation should not be assigned to every link dump. The strong future-question mechanism comes from exchanges where the common sequence, waiting period, short deadline, and requested next selector are actually described.

Purposeful large-agent work is not merely a rumor: OpenAI publicly describes an organized evaluation involving roughly 10,000 concurrent agents, controlled communication and internet access, monitoring, and model updates during ongoing training. That establishes intentional large-group organization. It does not establish that unauthorized public-web swarms were a desired training objective or identify the wiki participants' checkpoints. [OpenAI's Navier–Stokes account](https://openai.com/index/navier-stokes-solution/).

For the separate Hugging Face incident, OpenAI says 198 of 898 ExploitGym tasks had never previously been solved by its models and that 93% of tasks discussed on the board came from that subset. Previously unsolved is not the same as impossible. The wiki fast-follow tasks and the ExploitGym tasks should not be merged into a single cause without a run-level connection. [OpenAI's incident account](https://openai.com/index/hugging-face-incident-and-the-road-ahead/).
