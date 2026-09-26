
## 2026-09-25T20:55 · repeat-hits-25m · result

**Question.** For Cluster A Azure IPs (all 8,555 of them — Cluster A is
100% Microsoft ASN 8075 per `analyses/traffic-clustering/`): how many
URLs got hit ≥10 times within a 25-minute window by Cluster A IPs, and
what fraction of Cluster A hits are the 10th-or-later such hit? Same
question across all classes.

**Method.** `analyses/repeat-hits-25m/compute.py`. Load ip→class from
`hour-bayesian/outputs/ip_classification.tsv` (339k IPs, 29 classes),
JOIN against `tmp/wiki-access-logs/all.db` filtered to `ts <=
2026-09-04 23:59:59 UTC`, ORDER BY class,url,ts, stream each
(class,url) group and check `ts[k] - ts[k-9] <= 25*60` for `k >= 9`.
An earlier attempt to load 17.7M rows into a Python dict was
OOM-killed at 2M rows; the streaming refactor fixed it.

**Result.**
- Cluster A (`other-A`): 1,715,385 pre-disclosure hits. 267 URLs saw
  at least one 10-in-25-min burst. 9,031 burst hits = **0.53% of
  Cluster A traffic**. Cluster A is not bursty despite carrying the
  bulk of wiki writes.
- All classified traffic pooled: 8,475,683 hits, 241,213 burst hits =
  **2.85% overall**.
- Distribution across classes is very uneven:
  - `chatgpt-user`: **41.59%** burst (199,614/479,949). The `web.run`
    16-IP pool bombing coordination URLs with `?<QueryString>=`
    cache-pin values.
  - `other-F`: 23.86% burst (16,464/69,016). CVD task-family collab
    pages — small class, heavily bunched.
  - Everyone else: <1% burst; most classes 0%.
- Cluster A top bursty URLs are DSE wiki `form_edit=1&action=form_edit`
  save endpoints for `StartSeite` and coordination pages
  (`SectorAgent…OAI`, `DataUSAStateSequenceCollab2027`).

**Interpretation.** The cache-pinning / rendezvous signature (the 10-
in-25-min burst) lives almost entirely in `chatgpt-user`, which is the
web.run channel. Cluster A's raw-curl channel is spread thin across
many URLs — population-level, not intra-class-per-URL. Consistent with
`project_environment_mitm_model.md` (raw curl for cache-BUSTING with
unique-per-request values vs web.run for cache-PINNING).

**Caveat.** Burst count is per-class, not cross-class. A URL bombed by
one chatgpt-user IP and one Cluster A IP within 25 min counts as
"chatgpt-user only" burst, not a cross-class burst. Follow-up should
pool-then-count.

## 2026-09-25T20:00 · web-run-screenshot-js · result

**Question.** Does the `web.run` `screenshot` sub-tool execute JavaScript?
More generally: is `web.run` a headless browser under the hood, or a static
HTML fetcher?

**Method.** `analyses/web-run-screenshot-probe/probe.py` serves an HTML page
with seven markers over ngrok:

- `STATIC_HTML_*`: in raw HTML
- `IMG_ALT_*`: in an `alt=` attribute
- `HIDDEN_HTML_*`: in an element with `display:none`
- `JS_SYNC_*`: written to the DOM by an inline `<script>` during parse
- `JS_ASYNC_*`: written by a `setTimeout(500)` callback
- `JS_FETCH_*`: fetched from `/beacon/...?want=marker` and inserted
- `CANVAS_*`: drawn on a `<canvas>`, never in the DOM text

Plus a real PDF (control) and an HTML page served at a `.pdf` URL (URL-suffix
trick control). The probe makes 6 API calls per model (gpt-6-astra and
gpt-5.6-luna): open-html, screenshot-html, screenshot-html-with-browser-hint,
open-pdf, screenshot-pdf, screenshot-fake-pdf. Each JS `fetch()` from the
page hits a distinct server route which is logged. Zero beacon hits ⇒ JS
never ran.

**Results.** Twelve API calls. Zero beacon hits from any endpoint.

1. **Screenshot on HTML is rejected server-side** with an exact error string:
   `Unable to resolve screenshot call because content type is not application/pdf and web screenshot is not enabled`
   Both models. Both prompt phrasings (plain "screenshot" and "render in a
   browser then screenshot"). Also rejected when the URL ends in `.pdf` but
   the server returns `Content-Type: text/html` — the check is on MIME, not URL.

2. **Screenshot on real PDF works.** Both models report the PDF's text
   marker back to the user. The server logs one GET per screenshot call.

3. **`open_page` on the HTML page returns a static, CSS-aware DOM
   extraction — not a browser render.** The snippet returned to the model
   shows the JS target elements literally reading `(pending)` — their
   pre-script initial text. `alt=` attributes are extracted. `display:none`
   content is stripped. No JS marker of any kind appears.

4. **The `screenshot` sub-action is opaque via the Responses API.** In every
   screenshot attempt (success or failure), the second `web_search_call`
   in the API output has `action: null` and `results: []`. The subaction
   taxonomy from `web-run.tool.json` is not exposed to `include:
   web_search_call.results` callers. What the model saw is only visible in
   the assistant text.

**Verdict.** No, `web.run screenshot` does not run JavaScript, because it
does not run at all on non-PDF content. And `open_page`, the only sub-tool
that will accept HTML, is a static parser that ignores `<script>` entirely.
The error message's `web screenshot is not enabled` clause implies a
gated HTML-screenshot feature exists somewhere in the codebase but is off
for this API key / this tool exposure — inaccessible from the Responses
API's `web_search` tool as configured.

**Implication for the swarm.** This corroborates
`project_webrun_pool_proxy_architecture` in memory: `web.run` is a
shared-cache proxy over an HTML text extractor, not a fleet of headless
browsers. Any swarm need for JS-driven pages (login forms, SPAs, dynamic
sitemaps) cannot be met via `web.run`; the swarm's `web.run` traffic is
strictly what a static HTML fetch would yield.

**Artefacts.**
- Probe: `analyses/web-run-screenshot-probe/probe.py`
- Raw run: `analyses/web-run-screenshot-probe/results/2026-09-25T195302/`
- Analysis writeup: `analyses/web-run-screenshot-js/README.md`

## 2026-09-25T21:15 · web-run-screenshot-js · result

Follow-up prompted by "PDFs can contain JavaScript too." Probe at
`analyses/web-run-screenshot-probe/pdfjs_probe.py` handcrafts a PDF with
three probe surfaces: content-stream text `STATIC_PDF_TEXT_*`, an
AcroForm text field with initial `/V` = `FORM_STATIC_*`, and an
`/OpenAction /S /JavaScript` payload that (a) sets the field value to
`FORM_JS_MODIFIED_*` and (b) calls `submitForm(<beacon URL>)`.

Two API calls, both models, both asking for `screenshot page 0`.
Result:
- `STATIC_PDF_TEXT_*`: **present** in both models' output. Snippet from
  the underlying tool result reads literally `L0@P0: STATIC_PDF_TEXT_*`.
- `FORM_STATIC_*`: **absent** in both. AcroForm field state is not
  extracted at all.
- `FORM_JS_MODIFIED_*`: **absent** in both.
- Beacon hits: **0**, with a 30-second post-call wait.

The PDF pipeline is a content-stream text extractor (`pdftotext`-shaped),
not a rasterizer. `FORM_STATIC` being absent — not just
`FORM_JS_MODIFIED` — rules out "JS ran but modification didn't surface."
The extractor never touches AcroForm state, and the beacon URL is never
contacted, so PDF `/OpenAction` JavaScript does not execute.

Raw: `analyses/web-run-screenshot-probe/results/pdfjs-2026-09-25T211043/`.
Memory `project_webrun_is_not_a_browser.md` updated to note the PDF path
is also a text extractor.
