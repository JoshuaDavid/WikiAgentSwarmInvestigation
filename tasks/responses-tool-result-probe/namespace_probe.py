#!/usr/bin/env python3
"""Test a custom web function with the captured interface and no hosted web tool."""

import argparse
import datetime
import json
from pathlib import Path
import secrets

from build_web_tool import build
from probe import api, load_key, save


def get_call(response, namespace, function_name):
    if response.get("status") != "completed":
        raise RuntimeError("Response did not complete; see saved artifacts")
    if any(item["type"] == "web_search_call" for item in response["output"]):
        raise RuntimeError("Unexpected hosted web call")
    calls = [item for item in response["output"] if item["type"] == "function_call"]
    if len(calls) != 1:
        raise RuntimeError("Expected one application-managed function call")
    call = calls[0]
    if call.get("namespace") != namespace or call["name"] != function_name:
        raise RuntimeError(f"Unexpected function identity: {call}")
    return call, json.loads(call["arguments"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-6-astra")
    parser.add_argument("--namespace", default="web")
    parser.add_argument("--function-name", default="run")
    parser.add_argument("--standalone", action="store_true",
                        help="Expose the function directly without a namespace wrapper")
    parser.add_argument("--parameters", type=Path,
                        help="Use a candidate argument schema instead of the captured declaration")
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    key = load_key(args.api_key_file)
    args.out.mkdir(parents=True, exist_ok=False)
    tool = build()
    tool["name"] = args.namespace
    function = tool["tools"][0]
    function["name"] = args.function_name
    if args.parameters is not None:
        function["parameters"] = json.loads(args.parameters.read_text())
    if args.standalone:
        tool = function
    expected_namespace = None if args.standalone else args.namespace
    tool_identity = (args.function_name if args.standalone
                     else f"{args.namespace}.{args.function_name}")
    save(args.out / "tool.json", tool)
    base = {
        "model": args.model, "reasoning": {"effort": "low"}, "store": False,
        "max_output_tokens": 1200, "tools": [tool],
        "include": ["reasoning.encrypted_content"], "parallel_tool_calls": False,
        "tool_choice": "auto",
    }
    user = {"role": "user", "content": (
        'Search for "IANA example domains", then open the first search result using '
        "its returned reference. Report only the page's main heading. "
        "Use the opened page content, not the search snippet or prior knowledge. "
        "If opening reports a cache miss, reply CACHE_MISS. Do not retry."
    )}
    history = [user]
    first, first_meta = api(args.out, "01-search-call", {**base, "input": history}, key)
    search_call, search_arguments = get_call(first, expected_namespace, args.function_name)
    if ({name for name, value in search_arguments.items() if value is not None}
            - {"search_query", "response_length"}
            or len(search_arguments.get("search_query", [])) != 1):
        raise RuntimeError("Expected one search query before any page open")
    # These are controlled fixture tool results. The schema/continuation probe
    # makes no search or fetch request, and exposes no fixture/eval flag to the model.
    search_text = (
        "Example Domain (https://example.com/)\n"
        "\ue200cite\ue202turn0search0\ue201 [wordlim: 200] Crawled: today; "
        "This domain is for use in documentation examples without needing permission."
    )
    history = [*history, *first["output"], {
        "type": "function_call_output", "call_id": search_call["call_id"],
        "output": search_text,
    }]
    second, second_meta = api(args.out, "02-open-call", {**base, "input": history}, key)
    open_call, open_arguments = get_call(second, expected_namespace, args.function_name)
    if ({name for name, value in open_arguments.items() if value is not None}
            - {"open", "response_length"}
            or len(open_arguments.get("open", [])) != 1
            or open_arguments["open"][0].get("ref_id") != "turn0search0"):
        raise RuntimeError("Expected an open of the supplied search reference")
    history = [*history, *second["output"]]
    save(args.out / "pending-open.json", {
        "state": "AWAITING_FETCH_DECISION", "call": open_call,
        "resolved_url": "https://example.com/", "history": history,
    })
    marker = "REPLACED_HEADING_" + secrets.token_hex(12)
    branches = {}
    for label, result in {
        "03-replacement": (
            "Example Domain (https://example.com/)\n"
            "\ue200cite\ue202turn1view0\ue201 [wordlim: 200] Content type: text/html; "
            'Source: open({"ref_id":"turn0search0","lineno":null}); Total lines: 1\n'
            f"L0: # {marker}"
        ),
        "04-cache-miss": "Failed to fetch https://example.com/: Cache miss",
    }.items():
        response, meta = api(args.out, label, {
            **base, "input": [*history, {
                "type": "function_call_output", "call_id": open_call["call_id"],
                "output": result,
            }],
        }, key)
        meta["unexpected_calls"] = [item["type"] for item in response.get("output", [])
                                    if item["type"] in {"function_call", "web_search_call"}]
        branches[label] = meta
    summary = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": args.model, "marker": marker,
        "tool_identity": tool_identity, "native_web_enabled": False,
        "parameter_groups": list(function["parameters"]["properties"]),
        "search_call": search_call, "open_call": open_call,
        "search": first_meta, "open": second_meta, "branches": branches,
        "replacement_observed": marker in branches["03-replacement"]["text"],
        "cache_miss_observed": branches["04-cache-miss"]["text"].strip() == "CACHE_MISS",
        "all_completed": all(meta["http_status"] == 200 and meta["status"] == "completed"
                             for meta in [first_meta, second_meta, *branches.values()]),
        "no_unexpected_calls": all(not meta["unexpected_calls"] for meta in branches.values()),
    }
    save(args.out / "summary.json", summary)
    for path in args.out.glob("*.json"):
        if key in path.read_text():
            raise RuntimeError(f"Credential unexpectedly present in {path.name}")
    print(json.dumps({"summary": summary}), flush=True)
    if not all(summary[name] for name in ["replacement_observed", "cache_miss_observed",
                                          "all_completed", "no_unexpected_calls"]):
        raise SystemExit("One or more checks failed; see summary")


if __name__ == "__main__":
    main()
