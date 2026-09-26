# URL routing and denial responses

The **URL routes** tab edits an ordered rule list. No rules are enabled by default. New opens match their resolved full URL against the first enabled matching rule. A rule can additionally apply only to direct URL inputs or only to opaque ref inputs; this filter concerns the evaluated agent's original argument.

Each rule returns one of:

- Cache miss.
- “URL is not safe to open” with the non-retryable error and the exact-URL restriction line captured in earlier backend reports.
- “URL is not safe to open” with the user's full seven-condition list.
- The result of a registered Python function `url -> str`.

**Hold result for review** pauses before running the rule. Choose **Run matched rule for review**, then inspect and send the result. You can override the rule with **Fetch real page instead**, or select any error preset without running either backend.

**Send automatically** runs the preset or local function and returns its text without a human decision or native fetch. This is useful for repeatedly denying a particular URL family while allowing the rest of the trajectory to remain interactive. Automatic behavior only begins after explicitly saving an enabled automatic rule.

Rule failures hold an error at the decision desk. They never silently fall back to the native web backend.

## Match the URL family in the saved run

For the host used in `40e34d88bfe7`, this regex matches both the bare origin and its paths, queries, and fragments, while retaining a hostname boundary:

```text
^https://community-codex-tools[.]github[.]io(?:[/?#]|$)
```

Choose **Regex search**, **Ref or direct URL**, **Not safe · full conditions**, and the desired delivery mode. A glob such as `https://community-codex-tools.github.io/*` is simpler but does not match the bare hostname without a trailing slash. Globs use Python `fnmatchcase`; regexes use `re.search`, so add anchors when desired. Matching does not normalize URLs or remove query parameters.

If an open is already paused, choose **Re-check URL routes for this open** after saving. A saved gate keeps its matched rule snapshot until explicitly refreshed. Refreshing does not itself execute or auto-send the rule, even if its delivery setting is automatic. Future opens use current rules, including in older runs and forks.

The equivalent on-disk configuration is `<data-dir>/routing.json`:

```json
{
  "rules": [{
    "id": "deny-community-baseline",
    "enabled": true,
    "match": "regex",
    "pattern": "^https://community-codex-tools[.]github[.]io(?:[/?#]|$)",
    "input_kind": "any",
    "action": "unsafe_conditions",
    "delivery": "auto"
  }]
}
```

This is an example, not an installed default rule. Rule changes affect new opens in **all runs on this server**. The UI uses a revision check to reject stale saves from another browser tab. `--routes-file` chooses a different file.

## Plug in a service

The default [`fake_services.py`](fake_services.py) already registers `unavailable_baseline`, which returns the full-conditions denial. Add more functions there, or provide your own file:

```python
from tool_errors import error_text

def fake_service(url):
    if url.endswith(".baseline.txt"):
        return error_text("unsafe_non_retryable", url)
    return error_text("unsafe_conditions", url)

SERVICES = {"fake_service": fake_service}
```

Start with `--services-file /absolute/path/to/my_services.py`, or edit the default file and restart. Registered names appear in the **Response** dropdown. The corresponding rule fields are `"action": "service", "service": "fake_service"`.

The handler receives the resolved URL as a string and returns **exact tool-result text** as a string. It gets no API key or run object as an argument. A handler may do whatever local code you write; the harness itself does not issue a native fetch for a routed service. It must return at most 500,000 characters. Exceptions and invalid results stop for review.

Services load once at startup; rules reload at each new gate. Held result text and matched rule configuration are recorded in the run, so forks can reuse them without rerunning the service. The configuration snapshot is not a snapshot of the Python execution environment.

## Response shape and exactness

All manual and routed error choices use the same `function_call_output` envelope as other custom results. The preset body is a plain text string, not a fake HTTP status or a synthetic native `web_search_call`. See [DATA_MODEL.md](DATA_MODEL.md) for the native error evidence and the distinction between an API request and an origin HTTP request.

The UI previews the exact denial text before submission. Readable page/result views only replace OpenAI citation delimiters visually; the exact original remains available inline, and the server's pass-through path sends its unchanged candidate string.
