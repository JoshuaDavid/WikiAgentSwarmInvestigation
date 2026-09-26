#!/usr/bin/env python3
"""Control: pause at an application-managed web tool and branch its result."""

import argparse
import datetime
import json
from pathlib import Path
import secrets

from probe import api, load_key, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-6-astra")
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--native-result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    key = load_key(args.api_key_file)
    source = json.loads(args.native_result.read_text())
    web_calls = [item for item in source["output"] if item["type"] == "web_search_call"]
    if len(web_calls) != 1 or not web_calls[0].get("results"):
        raise ValueError("Expected exactly one successful native web result")
    original = "\n\n".join(result["snippet"] for result in web_calls[0]["results"])
    args.out.mkdir(parents=True, exist_ok=False)
    tool = {
        "type": "function", "name": "web_run",
        "description": "Open a webpage by URL or reference and return its text.",
        "strict": True,
        "parameters": {"type": "object", "properties": {
            "open": {"type": "array", "items": {
                "type": "object", "properties": {"ref_id": {"type": "string"}},
                "required": ["ref_id"], "additionalProperties": False,
            }},
        }, "required": ["open"], "additionalProperties": False},
    }
    base = {
        "model": args.model, "reasoning": {"effort": "low"}, "store": False,
        "max_output_tokens": 1000, "tools": [tool],
        "include": ["reasoning.encrypted_content"], "parallel_tool_calls": False,
    }
    user = {"role": "user", "content": (
        "Open https://example.com/ once and report only the page's main heading. "
        "Use only the tool result, not prior knowledge. "
        "If the tool reports a cache miss, reply CACHE_MISS. Do not search or retry."
    )}
    pending, pending_meta = api(args.out, "01-pending-call", {
        **base, "input": [user],
        "tool_choice": {"type": "function", "name": "web_run"},
    }, key)
    calls = [item for item in pending.get("output", []) if item["type"] == "function_call"]
    if pending.get("status") != "completed" or len(calls) != 1:
        raise RuntimeError("Expected one pending function call")
    call = calls[0]
    if json.loads(call["arguments"]) != {"open": [{"ref_id": "https://example.com/"}]}:
        raise RuntimeError("Unexpected web request; see saved response")
    # The application is now free to wait indefinitely for a human. The model
    # receives no result until a continuation is submitted. No external fetch
    # was performed by this function call.
    marker = "REPLACED_HEADING_" + secrets.token_hex(12)
    results = {
        "02-original": original,
        "03-replaced": '\ue200cite\ue202turn0view0\ue201 [wordlim: 200] Content type: text/html; '
                       'Source: open({"ref_id":"https://example.com/","lineno":null}); '
                       f'Total lines: 1\nL0: # {marker}',
        "04-cache-miss": 'Failed to fetch https://example.com/: Cache miss',
    }
    branches = {}
    for label, result in results.items():
        response, meta = api(args.out, label, {
            **base, "tool_choice": "none",
            "input": [user, *pending["output"], {
                "type": "function_call_output", "call_id": call["call_id"],
                "output": result,
            }],
        }, key)
        branches[label] = meta
    summary = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": args.model, "marker": marker, "pending": pending_meta,
        "branches": branches,
        "original_observed": branches["02-original"]["text"].strip() == "Example Domain",
        "replacement_observed": branches["03-replaced"]["text"].strip() == marker,
        "cache_miss_observed": branches["04-cache-miss"]["text"].strip() == "CACHE_MISS",
        "all_completed": all(meta["http_status"] == 200 and meta["status"] == "completed"
                             for meta in [pending_meta, *branches.values()]),
    }
    save(args.out / "summary.json", summary)
    for path in args.out.glob("*.json"):
        if key in path.read_text():
            raise RuntimeError(f"Credential unexpectedly present in {path.name}")
    print(json.dumps({"summary": summary}), flush=True)
    if not all(summary[name] for name in ["original_observed", "replacement_observed",
                                          "cache_miss_observed", "all_completed"]):
        raise SystemExit("One or more controls failed; see summary")


if __name__ == "__main__":
    main()
