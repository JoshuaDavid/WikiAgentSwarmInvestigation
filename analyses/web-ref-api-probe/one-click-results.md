# Exact one-click, next-user-message experiment

Tested on 2026-09-16 through the public Responses API. **Step 6 failed in all four model/continuation combinations.**

## Exact scenario executed

1. User message provides `https://joshuadavid.github.io/swarm-maze/pages/29135.html` and asks the model to open it and click one visible link.
2. The model opens that URL and receives the page content and numbered links.
3. The model clicks link ID `0` using the returned page reference.
4. The clicked page, `https://joshuadavid.github.io/swarm-maze/pages/12752.html`, loads successfully. The assistant explicitly notes this destination URL in its final answer. Its response finishes.
5. A second user message contains no URL:

> Open the URL of the page you reached by clicking in the previous turn. Use the destination URL you noted, not an opaque reference. Make exactly one open call. Do not search, click, or retry. Report the attempted URL and either success or the exact tool error.

6. The model makes exactly one `open_page` call using the full destination URL ending in `12752.html`. It returns no page results, and the assistant relays `not safe to open (non-retryable error)`.

The first user message contains only the starting URL. The destination URL does not occur in either user message. No file tool is involved. No search was performed. Each branch consists of exactly two user messages and two completed responses; both branches share the same first response per model.

## Results

| Model | Conversation state | First open + click | Next-turn URL open |
| --- | --- | --- | --- |
| gpt-5.5-2026-04-23 | previous_response_id | Succeeded | Not safe to open |
| gpt-5.5-2026-04-23 | Complete history replay | Succeeded | Not safe to open |
| gpt-6-astra | previous_response_id | Succeeded | Not safe to open |
| gpt-6-astra | Complete history replay | Succeeded | Not safe to open |

Complete replay contains the original user message, every returned output item (including raw web results and encrypted reasoning), and the identical URL-free second user message.

Both models relayed this core error:

```text
URL https://joshuadavid.github.io/swarm-maze/pages/12752.html is not safe to open (non-retryable error)
You can only use the exact same URL from the previous search results or the user's message
```

The raw successful click result identifies `Source: click({"ref_id":"turn0view0","id":0})` and returns the destination page's content. Each later raw call has `action.type: open_page`, `action.url` equal to the actual destination URL, and `results: []`. The exact error wording is relayed by the assistant; the API's raw web-result field does not include that error body.

This distinguishes the tested failure from accidentally reopening an old opaque reference or losing the destination URL in model context. The assistant knew and attempted the correct destination URL. It does not establish the internal implementation of the safety check.

## Reproduce

Requires `curl`, `jq`, and `OPENAI_WEB_SEARCH_API_KEY` in the environment:

```bash
./analyses/web-ref-api-probe/click-then-next-turn.sh
MODEL=gpt-6-astra ./analyses/web-ref-api-probe/click-then-next-turn.sh
```

Each invocation makes three API requests: one first response and two alternative continuations. Logs are retained in a printed temporary directory.

[Script](click-then-next-turn.sh) · [Structured summary](results/2026-09-16-one-click/summary.json)

[GPT-5.5 requests and responses](results/2026-09-16-one-click/gpt-5.5/) · [GPT-6 Astra requests and responses](results/2026-09-16-one-click/gpt-6-astra/)

Six API requests were executed in total. All returned completed status. All saved artifacts passed a check for accidental inclusion of the supplied API key.
