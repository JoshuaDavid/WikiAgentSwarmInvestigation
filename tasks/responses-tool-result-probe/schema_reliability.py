#!/usr/bin/env python3
"""Collect independent schema reports using the identical saved API request."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import hashlib
import json
from pathlib import Path
import re

from probe import api, load_key, output_text, save


def parse_report(text):
    text = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*\n(.*)\n```", text, flags=re.DOTALL)
    if match:
        text = match.group(1)
    schema = json.loads(text)
    if not isinstance(schema, dict) or schema.get("type") != "object" \
            or not isinstance(schema.get("properties"), dict):
        raise ValueError("Expected an object argument schema")
    return schema


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not 2 <= args.samples <= 10:
        parser.error("Use between 2 and 10 samples for this small probe")
    body = json.loads(args.request.read_text())
    if body.get("store") is not False or body.get("tool_choice") != "none" \
            or any(k in body for k in ["previous_response_id", "conversation"]):
        raise ValueError("Expected independent requests with tool execution disabled")
    key = load_key(args.api_key_file)
    args.out.mkdir(parents=True, exist_ok=False)
    save(args.out / "manifest.json", {
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "samples": args.samples, "model": body["model"],
        "source_request": str(args.request.resolve()),
        "request_sha256": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(),
        "sampling": "Independent fresh requests with identical input and settings; no shared response history",
        "historical_sample_included": False,
    })

    def collect(i):
        label = f"sample-{i:02}"
        try:
            response, meta = api(args.out, label, body, key, show_text=False)
            if meta["http_status"] != 200 or response.get("status") != "completed":
                return {"label": label, "valid": False, "error": meta.get("error")}
            if any(item["type"].endswith("call") for item in response.get("output", [])):
                raise ValueError("Unexpected tool call")
            schema = parse_report(output_text(response))
            save(args.out / f"{label}.schema.json", schema)
            return {"label": label, "valid": True,
                    "field_names": list(schema["properties"]), "usage": meta["usage"]}
        except Exception as error:
            return {"label": label, "valid": False, "error": str(error).replace(key, "[REDACTED]")}

    results = []
    with ThreadPoolExecutor(max_workers=min(args.samples, 5)) as pool:
        pending = [pool.submit(collect, i) for i in range(1, args.samples + 1)]
        for future in as_completed(pending):
            result = future.result()
            results.append(result)
            save(args.out / "collection.json", sorted(results, key=lambda r: r["label"]))
            print(json.dumps({"collected": result}), flush=True)
    for path in args.out.glob("*.json"):
        if key in path.read_text():
            raise RuntimeError(f"Credential unexpectedly present in {path.name}")
    print(json.dumps({"valid_reports": sum(r["valid"] for r in results),
                      "attempted": args.samples}), flush=True)


if __name__ == "__main__":
    main()
