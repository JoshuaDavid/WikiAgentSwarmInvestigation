#!/usr/bin/env python3
"""Empirically test replacement of a native web result in Responses history."""

import argparse
import copy
import datetime
import json
import os
from pathlib import Path
import secrets
import time
import urllib.error
import urllib.request


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def output_text(response):
    return "\n".join(
        part.get("text", "")
        for item in response.get("output", []) if item.get("type") == "message"
        for part in item.get("content", []) if part.get("type") == "output_text"
    )


def load_key(path):
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_WEB_SEARCH_API_KEY")
    if not key:
        if path is None:
            raise ValueError("Set OPENAI_API_KEY or pass --api-key-file explicitly")
        key = path.read_text().strip()
        if key.startswith(("OPENAI_API_KEY=", "OPENAI_WEB_SEARCH_API_KEY=")):
            key = key.split("=", 1)[1].strip().strip("\"'")
    if not key:
        raise ValueError("Empty API key")
    return key


def api(out, label, body, key, *, show_text=True):
    save(out / f"{label}.request.json", body)
    print(f"Request: {label}", flush=True)
    started = time.monotonic()
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw, status = response.read(), response.status
            request_id = response.headers.get("x-request-id")
    except urllib.error.HTTPError as error:
        raw, status = error.read(), error.code
        request_id = error.headers.get("x-request-id")
    except urllib.error.URLError as error:
        save(out / f"{label}.meta.json", {
            "transport_error": str(error).replace(key, "[REDACTED]"),
            "elapsed_s": round(time.monotonic() - started, 3),
        })
        raise RuntimeError("API connection failed; see saved metadata") from None
    result = json.loads(raw.decode().replace(key, "[REDACTED]"))
    save(out / f"{label}.response.json", result)
    meta = {"http_status": status, "request_id": request_id,
            "elapsed_s": round(time.monotonic() - started, 3),
            "response_id": result.get("id"), "status": result.get("status"),
            "model": result.get("model"), "text": output_text(result),
            "error": result.get("error"), "usage": result.get("usage")}
    save(out / f"{label}.meta.json", meta)
    printed = meta if show_text else {k: v for k, v in meta.items() if k != "text"}
    print(json.dumps({"label": label, **printed}), flush=True)
    return result, meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-6-astra")
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    key = load_key(args.api_key_file)
    args.out.mkdir(parents=True, exist_ok=False)
    base = {
        "model": args.model, "reasoning": {"effort": "low"}, "store": False,
        "max_output_tokens": 1000,
        "tools": [{"type": "web_search", "external_web_access": False}],
        "include": ["web_search_call.results", "reasoning.encrypted_content"],
    }
    user = {"role": "user", "content": (
        "Open https://example.com/ once and report only the page's main heading. "
        "Use only the tool result, not prior knowledge. "
        "If the tool reports a cache miss, reply CACHE_MISS. Do not search or retry."
    )}
    first, first_meta = api(args.out, "01-original", {
        **base, "input": [user], "max_tool_calls": 1,
        "tool_choice": {"type": "web_search"},
    }, key)
    if first_meta["http_status"] != 200 or first.get("status") != "completed":
        raise RuntimeError("Initial request failed; see saved response")
    indexes = [i for i, item in enumerate(first["output"])
               if item.get("type") == "web_search_call"]
    if len(indexes) != 1:
        raise RuntimeError("Expected exactly one native web call")
    # Retain all items before the result, including encrypted reasoning, but
    # remove ALL later items so no original answer/reasoning leaks into replay.
    prefix = first["output"][:indexes[0] + 1]
    call = prefix[-1]
    if call.get("action", {}).get("type") != "open_page" or not call.get("results"):
        raise RuntimeError("Expected a successful native page open")
    marker = "REPLACED_HEADING_" + secrets.token_hex(12)
    patched = copy.deepcopy(prefix)
    patched[-1]["results"] = [{
        "type": "text_result", "title": call["results"][0].get("title", "Example"),
        "url": call["results"][0]["url"],
        "snippet": '\ue200cite\ue202turn0view0\ue201 [wordlim: 200] Content type: text/html; '
                   'Source: open({"ref_id":"https://example.com/","lineno":null}); '
                   f'Total lines: 1\nL0: # {marker}',
    }]
    # No previous_response_id: we supply the entire replacement history.
    replaced, replaced_meta = api(args.out, "02-replaced", {
        **base, "tool_choice": "none", "input": [user, *patched],
    }, key)
    original_replay, original_meta = api(args.out, "03-original-replay", {
        **base, "tool_choice": "none", "input": [user, *prefix],
    }, key)
    summary = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": args.model, "marker": marker,
        "original": first_meta, "replaced": replaced_meta,
        "original_replay": original_meta,
        "replacement_observed": marker in output_text(replaced),
        "control_has_no_marker": marker not in output_text(original_replay),
        "original_content_preserved": output_text(original_replay).strip() == "Example Domain",
        "replay_input_token_counts_equal": (
            replaced_meta.get("usage", {}).get("input_tokens")
            == original_meta.get("usage", {}).get("input_tokens")
        ),
    }
    save(args.out / "summary.json", summary)
    for path in args.out.glob("*.json"):
        if key in path.read_text():
            raise RuntimeError(f"Credential unexpectedly present in {path.name}")
    print(json.dumps({"summary": summary}), flush=True)


if __name__ == "__main__":
    main()
