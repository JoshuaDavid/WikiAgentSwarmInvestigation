#!/usr/bin/env python3
"""Capture the model's description of its native web argument schema as a candidate.

This is model-reported information, not an authoritative API schema export.
Any proposed schema must subsequently pass actual tool-definition validation.
"""

import argparse
import json
from pathlib import Path

from probe import api, load_key, output_text, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    key = load_key(args.api_key_file)
    args.out.mkdir(parents=True, exist_ok=False)
    response, meta = api(args.out, "01-native-schema-candidate", {
        "model": "gpt-6-astra", "reasoning": {"effort": "low"}, "store": False,
        "tools": [{"type": "web_search", "external_web_access": False}],
        "tool_choice": "none", "max_output_tokens": 6500,
        "input": (
            "For a tool integration, describe only the argument interface of the web.run "
            "function currently available to you as a JSON Schema object. Include every "
            "declared argument, its nested fields, types, enum values, and optionality. "
            "Use required arrays to distinguish required from optional fields; preserve "
            "nullable types if declared. Do not add arguments you remember from other "
            "versions of this tool. Include field descriptions where provided. Do not "
            "make any web calls. Return only the JSON Schema for the arguments, with "
            "type: object and properties at the root. Do not include any other instructions."
        ),
    }, key)
    if meta["http_status"] != 200 or response.get("status") != "completed":
        raise RuntimeError("Schema-report request did not complete")
    text = output_text(response).strip()
    if text.startswith("```json\n") and text.endswith("```"):
        text = text[len("```json\n"):-len("```")].strip()
    candidate = json.loads(text)
    save(args.out / "candidate-parameters.json", candidate)
    print(json.dumps({"candidate_field_names": list(candidate.get("properties", {})),
                      "authoritative": False}), flush=True)


if __name__ == "__main__":
    main()
