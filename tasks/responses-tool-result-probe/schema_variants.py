#!/usr/bin/env python3
"""Check a few explicit schema-representation hypotheses for reserved web.run."""

import argparse
import json
from pathlib import Path

from build_web_tool import build
from probe import api, load_key, save


def strip_metadata(value):
    if isinstance(value, dict):
        return {key: strip_metadata(child) for key, child in value.items()
                if key not in {"description", "title", "default", "format", "minimum"}}
    if isinstance(value, list):
        return [strip_metadata(child) for child in value]
    return value


def pydantic_style(value):
    if isinstance(value, list):
        return [pydantic_style(child) for child in value]
    if not isinstance(value, dict):
        return value
    node = {key: pydantic_style(child) for key, child in value.items()}
    if node.get("type") == ["array", "null"] or node.get("type") == ["integer", "null"] \
            or node.get("type") == ["string", "null"]:
        kind = node.pop("type")[0]
        inner = {"type": kind}
        for key in ["items", "minimum", "format"]:
            if key in node:
                inner[key] = node.pop(key)
        node["anyOf"] = [inner, {"type": "null"}]
    for name, prop in node.get("properties", {}).items():
        prop["title"] = name.replace("_", " ").title()
        if prop.get("description") == prop["title"]:
            del prop["description"]
    return node


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    key = load_key(args.api_key_file)
    args.out.mkdir(parents=True, exist_ok=False)
    candidate = json.loads(args.candidate.read_text())
    variations = {}
    bare = build()
    bare["tools"][0]["parameters"] = strip_metadata(candidate)
    variations["01-no-parameter-metadata"] = bare
    pydantic = build()
    pydantic["tools"][0]["parameters"] = pydantic_style(candidate)
    variations["02-pydantic-representation"] = pydantic
    unspecified = build()
    del unspecified["tools"][0]["parameters"]
    variations["03-unspecified-parameters"] = unspecified
    summary = {}
    for label, tool in variations.items():
        response, meta = api(args.out, label, {
            "model": "gpt-6-astra", "reasoning": {"effort": "low"}, "store": False,
            "tools": [tool], "tool_choice": "auto", "max_output_tokens": 1000,
            "parallel_tool_calls": False,
            "input": 'Search for "IANA example domains".',
        }, key)
        summary[label] = {**meta, "output_types": [i["type"] for i in response.get("output", [])]}
        # A successful candidate needs a full continuation probe, not more guessing.
        if meta["http_status"] == 200:
            save(args.out / "accepted-tool.json", tool)
            break
    save(args.out / "summary.json", summary)
    for path in args.out.glob("*.json"):
        if key in path.read_text():
            raise RuntimeError(f"Credential unexpectedly present in {path.name}")


if __name__ == "__main__":
    main()
