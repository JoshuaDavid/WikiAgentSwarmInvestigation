# Early-date audit: what the retained records actually date

The proposed sentence “persistent URL retrieval/processing gadgets date to at least November 2025” is **not supported by the records audited here**. There are November 2025 pastes, but the inspected examples are Grok-themed jailbreak/roleplay material or unrelated prose. There are apparent 2025 retrieval-gadget dates in earlier analyses, but a concrete bug subtracts relative cache age from a search-assignment date. That produces dates which are not observations of activity.

The strongest earlier paste I found explicitly preserving a proxy URL and extracted data has a site-reported creation timestamp of **2026-02-26**. A **2025-12-14** paste preserves an answer and says it used Google Translate, but does not preserve the retrieval URL or show coordination. Archived shortener metadata dates direct data-download links to **2026-03-16**, and clear Markdown-proxy destinations to **2026-05-11**. These dates rely on service metadata observed later. They do not independently attribute the writers to OpenAI.

This memo separates a dated artifact, an apparent agent artifact, coordinated activity, and OpenAI attribution. None entails all the others.

## Candidate chronology

| Candidate | Exact evidence | What survives | What does not follow |
|---|---|---|---|
| 2025-11-01 | k4be paste `88c7186b`; `agent-logs/pastebin-k4be/revisions.jsonl:4`; timestamp `2025-11-01T18:45:45+00:00` | A dated essay about hashing empty input | A retrieval gadget, autonomous writer, coordination, or OpenAI attribution |
| 2025-11-25–26 | linuxiarz `136d08b9` and related Grok-themed texts; `agent-logs/paste-linuxiarz/revisions.jsonl:10`; shellac reading-pack index lines 52–67 | Dated public texts claiming fantastical system overrides | Evidence that those operations executed, that a URL retrieval chain existed, or that OpenAI agents wrote them |
| 2025-12-14 | [NBA answer paste](https://pastebin.k4be.pl/view/3ae5f54b); `agent-logs/pastebin-k4be/revisions.jsonl:6`, `pastebin-k4be~3ae5f54b@1`; site timestamp `2025-12-14T04:51:46+00:00` | A persisted calculated answer, source described as basketball-reference through Google Translate | A saved proxy URL, a group of agents, autonomous creation, provider attribution |
| **2026-02-26** | [Humana source paste](https://pastebin.k4be.pl/view/5329a841); `agent-logs/pastebin-k4be/revisions.jsonl:11`, `pastebin-k4be~5329a841@1`; timestamp `2026-02-26T14:49:24+00:00` | Explicit `bullfincher.io/sec-proxy?url=…sec.gov…hum-20151231x10k.htm` plus extracted stock-return table; related summaries at lines 12–13 within three minutes | That a browser navigated this paste to execute the proxy request, that independent agents posted the three texts, or that OpenAI authored them |
| **2026-03-16** | Popcat `oaixlsx1` and `oaixlsx2`; `scrape/outputs/popcat-wayback/info_parsed.jsonl:118` and :119 | Site-reported creation of shortlinks to a Turkish statistical API download | A Markdown/JSON processing gadget specifically; OpenAI authorship from the `oai` prefix |
| 2026-04-11, independently captured May 12 | Popcat `5vtSk2RG2f`; `info_parsed.jsonl:1` | A shortened ChatGPT conversation URL existed by the May 12 archive capture | That ChatGPT created the shortlink, or that this was coordination |
| **2026-05-11** | Popcat `oaimdbrit62`; `info_parsed.jsonl:87` | Site-reported creation of a shortlink to `md.succ.ai/https://search.projectarclight.org/query?...` | That the destination was immutable between May and the September capture; provider identity |
| 2026-05-14 | Popcat `oaibridge800`; `info_parsed.jsonl:7` | Persisted `httpbin.org/base64` HTML link pack for CBS OData queries | A communication network by itself |
| **2026-06-16** | Linuxiarz `f4f13504`, `7f01c19f`, `2023c613`; `agent-logs/paste-linuxiarz/revisions.jsonl:62`, :69, :77 | Explicit exchange of task progress and retrieval advice; another writer thanks the first for the advice | Provider identity without additional attribution evidence; this is an anchor, not a proof of earliest coordination anywhere |

The k4be timestamps come from the site's API `created` field. The export labels them `time_grade: api_paste_created_field`. The scraper describes fetching `/api/paste/{pid}` in `scrape/pastebin_k4be.py:1`; the provenance caveat is in `agent-logs/pastebin-k4be/README.md` under “Caveats.” The full raw API-body file mentioned by that README is absent in this checkout; the export rows and original transcript records remain.

The December NBA paste is available through the web tool as of this audit. It still contains the answer and Google Translate attribution. Its page shows a relative age, not the precise December timestamp. Attempts to read the three `/api/paste/…` endpoints through the web tool returned “not safe to open”; opening the ordinary `/view/3ae5f54b` page succeeded. Opening `/view/5329a841` returned the same tool error. No write or creation endpoint was called.

## The invalid 2025 chronology: an actual arithmetic bug

The search protocol explicitly calls the week an “initial search partition” and allows out-of-interval discoveries: `oai-index-scan/INSTRUCTIONS.md:5–10`. A file called `2025-11-16.results.jsonl` does not mean the results were retrieved in November 2025. Nor does including November in a query make the present-day index historical.

Nevertheless, `analyses/oai-url-taxonomy/extract_url_history.py` does exactly this:

```python
def shard_date(name):
    return datetime.strptime(name.split(".")[0], "%Y-%m-%d")

sdate = shard_date(shard_name)
delta = parse_cage(cache_age)
crawl_dt = (sdate - delta) if delta is not None else None
```

The relevant current file lines are **83–84, 114, and 125–127**. The function also converts months to 30.44 days at line 77. The protocol for actual cache dating rejects uncalibrated relative-age arithmetic and fixed month lengths: `oai-index-scan/CACHE_DATE_INSTRUCTIONS.md:20–24`, :48–61.

One concrete test is enough to expose the problem. `oai-index-scan/results/shards/2025-11-16.results.jsonl:45` contains:

```text
page_url = https://yourls.pro/admin/index.php?dummy=1778910680.6934943&search=pcitrootmaps1778905948712939&search_in=all
cache_age = Crawled: 3 months ago
published_date = null
modified_date = null
```

The `dummy` value looks like Unix seconds. Converting its integer component gives **2026-05-16 05:51:20 UTC**. Interpreting a URL's number as a timestamp still requires judgment, but it is a useful contradiction check against an alleged 2025 creation. More decisively, the protocol itself says the filename is an assignment partition. Subtracting three months from November 2025 is therefore unjustified regardless of the numeric URL value.

The earlier Claude transcript `/root/.claude/projects/-collusionwiki/491404af-2b36-4634-8a8d-a1eb4d7207c4.jsonl:857` announces a “corrected” earliest footprint in December 2024. At :881 it retreats to May–July 2025 after removing ordinary nested archive URLs and documentation matches. **Both chronologies retain the assignment-date arithmetic bug.** The program text also appears in that transcript at :835–838. These are useful audit history, not supporting sources for a publication date.

Consequences: do not cite `earliest_crawl_any` or `earliest_crawl_nonresearcher` from this pipeline as dates. Do not infer chronology from taxonomy summaries' `first_shard` fields. Do not interpret a generic nested Wayback URL, service README, or public YOURLS administrative interface as intrinsically diagnostic of a swarm. No files in that pipeline were changed during this audit.

A scan of every current weekly result shard for `published_date` fields containing `2024` or `2025` returned only two versions of an unrelated stale-price report. The date fields therefore supplied no independent pre-2026 publication date for these gadgets. This is a check of that field, not a claim that no free-text snippet anywhere contains an older date.

## Shorteners: creation metadata is not archive capture time

The shortener audit sorted all 119 retained Popcat `/info` rows twice: once by their `DD/MM/YYYY` creation dates, once by archive timestamp. It inspected representative original HTML, including destinations and creation dates. It also checked every one of the 4,285 `agent-logs/shorteners/revisions.jsonl` records. **All 4,285 have null `time`.** Their September `archived_at` is the export time. Their sequence numbers sort document hashes, not revisions over time. The importer documents this at `analyses/shellac-import/README.md:59–62`.

The relevant archive links, which read metadata pages rather than redirecting through the gadgets, are:

- [`oaixlsx1`, captured September 9](https://web.archive.org/web/20260909024220id_/https://url.popcat.xyz/oaixlsx1/info). Local original HTML: `scrape/outputs/popcat-wayback/info_pages/oaixlsx1.html:96` for destination; :144 for creation date.
- [`oaimdbrit62`, captured September 9](https://web.archive.org/web/20260909022548id_/https://url.popcat.xyz/oaimdbrit62/info). Local original HTML: `scrape/outputs/popcat-wayback/info_pages/oaimdbrit62.html:96` and :144.
- [`5vtSk2RG2f`, captured May 12](https://web.archive.org/web/20260512030653id_/https://url.popcat.xyz/5vtSk2RG2f/info).
- [`oaibridge800`, captured September 9](https://web.archive.org/web/20260909014025id_/https://url.popcat.xyz/oaibridge800/info).

A September archive independently establishes what the page displayed in September. A displayed May creation date is evidence about May; it is not equivalent to a May archive containing that destination. We have not established whether destination edits preserve creation dates or whether the service allows metadata manipulation. Earlier snapshots or server records could resolve this. `agent-logs/popcat-wayback/README.md:86–90` confirms there is one retained `/info` snapshot per code and no author, IP, or request log.

The Popcat set is selected for OpenAI-host destinations or `oai` names. It is not a complete history of Popcat, much less the web. The supplementary Vanderbilt metadata found during this audit dates records to June 18–23 from keyword suffixes such as `260618`; these are content-derived dates, not a stronger independent clock (`tmp/collusionwiki/swarm-datapakk-20260907/github.com/files/31a62defa5338afe5f4b-vanderbi.lt.yaml:12`).

## Attribution and coordination must keep their own dates

The earliest artifact is not automatically the earliest swarm. A human can paste a model answer. One model can stage several summaries. Two default animal handles can be assigned to the same person. K4be's classifier rationale for the December NBA paste mentions its animal handle and benchmark-like math, then gives a high-confidence `swarm` verdict. That rationale is insufficient to establish multiple agents, let alone OpenAI agents. The export README explicitly warns that these are Stikked-generated anonymous names.

For a clear coordination anchor, the linuxiarz audit identifies a June 16 exchange. At 20:02:21 UTC, `f4f13504` shares question order and its next task time. At 20:05:22, `7f01c19f` reports Q3 progress, shares the successful `da.gd`/`markdown.new` retrieval recipe, and asks what happens after Q5. At 20:08:36, `2023c613` thanks the writer for the “no-x tip.” A later named exchange (`d509c771` / `8246f250`, 21:27:52 / 21:28:49) repeats a published Q5 label and thanks its author. These are communication evidence. The timestamps inherit source metadata and agree with body timestamps where present; they lack independent provider logs. See the separate linuxiarz memo for the full exchange and caveats.

**Earliest independently grounded OpenAI attribution among the early paste/shortener candidates audited here: not established.** `oai` names, benchmark-like tasks, and links to ChatGPT are association clues. A transcript that shows an OpenAI agent issuing the write, or server telemetry that reliably connects the write to OpenAI infrastructure, would be stronger evidence. The wiki attribution should be dated from the wiki's own evidence rather than retroactively attached to every similar earlier paste.

## Claims, potential falsifiers, and checks actually performed

| Claim | Simplest useful contrary evidence | Check status |
|---|---|---|
| Gadgets existed by November 2025 | The cited item is ordinary text; the date is a search assignment; source metadata dates the artifact later | Found all three failure modes among candidates; November claim remains unsupported |
| k4be February paste preserves a proxy URL and extracted data | Source row lacks that URL, content is unrelated, or parsing assigned a false date | Inspected full export row, related two rows, API provenance, and listing index; no independent February archive found |
| Popcat processing shortlink was created May 11 | Historical destination differed; editable metadata retained old creation date; archived HTML says another date | Inspected original archived HTML and parsed metadata; did not establish service mutability or obtain earlier snapshot |
| Early candidate proves a swarm | One human pasted it, one agent wrote all posts, or all handles are anonymous defaults | Default-name mechanism is documented; early isolated pastes lack reciprocal evidence; June exchange is stronger |
| Early candidate proves OpenAI activity | Another model or researcher wrote it | No provider attribution in paste/Popcat metadata; unresolved |
| Derived `earliest_crawl_*` are valid dates | Program anchors relative age to search-assignment week | Inspected code and reproduced concrete counterexample; claim rejected |

Recommended publication wording: “We found older retrieval artifacts, but the earliest dates are less settled than the artifacts themselves. A February 2026 paste preserves a proxy URL and extracted financial data. Shortener metadata puts explicit Markdown-proxy links in May. Our initial route to 2025 dates had a bug: it treated search-assignment weeks as observation dates. We have not yet established a November 2025 instance.”

Useful next question: can someone produce one independently dated pre-2026 snapshot containing the actual retrieval gadget? One such record would repair the date claim. Another query with ‘November 2025’ in it would not.
