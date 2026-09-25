#!/usr/bin/env python3
"""Ask independent Luna requests about web.run nullability and score agreement."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import datetime
import json
from pathlib import Path
import re

from probe import api, load_key, output_text, save


LABELS = {"yes", "no", "unknown", "not_present"}


def parse_report(text, paths):
    text = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*\n(.*)\n```", text, re.DOTALL)
    if match:
        text = match.group(1)
    value = json.loads(text)
    rows = value["fields"]
    if not isinstance(rows, list) or len(rows) != len(paths):
        raise ValueError("Report must contain exactly one row for each requested field")
    report = {}
    for row in rows:
        path = row["path"]
        if path not in paths or path in report:
            raise ValueError(f"Unexpected or duplicate field: {path}")
        if row["nullable"] not in LABELS or row["omittable"] not in LABELS:
            raise ValueError(f"Unexpected classification for {path}")
        if not isinstance(row["declared_type"], str):
            raise ValueError(f"Missing type evidence for {path}")
        report[path] = row
    return report


def calculate(reports, paths):
    n = len(reports)
    if n < 2:
        raise ValueError("At least two valid reports are needed")
    output = {"valid_reports": n, "fields": len(paths), "per_field": {}}
    for facet in ["nullable", "omittable"]:
        numerator, denominator = 0, len(paths) * n * (n - 1)
        pooled, unanimous, definitive = Counter(), 0, 0
        profiles = Counter(tuple(report[path][facet] for path in paths) for report in reports.values())
        for path in paths:
            votes = Counter(report[path][facet] for report in reports.values())
            matching = sum(count * (count - 1) for count in votes.values())
            numerator += matching
            pooled.update(votes)
            definitive += votes["yes"] + votes["no"]
            unanimous += len(votes) == 1
            output["per_field"].setdefault(path, {})[facet] = {
                "counts": dict(votes), "agreement": matching / (n * (n - 1)),
                "votes": {label: report[path][facet] for label, report in reports.items()},
            }
        observed = numerator / denominator
        expected = sum((count / (len(paths) * n)) ** 2 for count in pooled.values())
        output[facet] = {
            "raw_pairwise_agreement": observed,
            "agreeing_field_pairs": numerator // 2,
            "total_field_pairs": denominator // 2,
            "unanimous_fields": unanimous,
            "definitive_answers": definitive, "total_answers": len(paths) * n,
            "fleiss_kappa": (observed - expected) / (1 - expected) if expected < 1 else None,
            "chance_agreement_from_pooled_labels": expected,
            "pooled_votes": dict(pooled),
            "distinct_complete_profiles": len(profiles),
            "complete_profile_sizes": sorted(profiles.values(), reverse=True),
            "complete_profile_pair_agreement": sum(c * (c - 1) for c in profiles.values()) / (n * (n - 1)),
        }
    focused = ["response_length", "image_query[].recency", "sports[].date_from", "sports[].date_to"]
    if len(paths) > len(focused) and set(focused).issubset(paths):
        subset = calculate(reports, focused)["nullable"]
        output["previously_discussed_fields"] = {
            "paths": focused, "agreeing_pairs": subset["agreeing_field_pairs"],
            "total_pairs": subset["total_field_pairs"],
            "raw_pairwise_agreement": subset["raw_pairwise_agreement"],
            "fleiss_kappa": subset["fleiss_kappa"],
        }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--field-records", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not 2 <= args.samples <= 20:
        parser.error("Use 2 to 20 samples")
    field_records = json.loads(args.field_records.read_text())
    paths = list(next(iter(field_records.values())))
    prompt = (
        "Inspect the argument declaration of the native web.run tool available in this request. "
        "For each field path listed below, report whether it accepts an explicit JSON null "
        "value (nullable) and separately whether that property can be omitted (omittable). "
        "These are different questions: a property can be optional but reject null. "
        "For a nested field, assume its parent object/array item is present. The [] notation "
        "means an array item. Report only what the current declaration supports, without "
        "inferring nullability from optionality, a default, or previous tool versions. "
        "Use labels yes, no, unknown, or not_present for each question. Use unknown if the "
        "declaration does not establish the answer and not_present if the path is absent "
        "from the available tool. Do not execute any tools.\n\n"
        "Return only JSON with this structure: {\"fields\": [{\"path\": \"field path\", "
        "\"nullable\": \"classification label\", \"omittable\": \"classification label\", "
        "\"declared_type\": \"the declared type expression supporting your answer, or unknown\"}]}. "
        "Include each requested path exactly once.\n\nField paths:\n" + json.dumps(paths)
    )
    body = {
        "model": "gpt-5.6-luna", "reasoning": {"effort": "low"}, "store": False,
        "tools": [{"type": "web_search", "external_web_access": False}],
        "tool_choice": "none", "max_output_tokens": 5500, "input": prompt,
    }
    key = load_key(args.api_key_file)
    args.out.mkdir(parents=True, exist_ok=False)
    save(args.out / "manifest.json", {
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": body["model"], "samples": args.samples, "field_paths": paths,
        "sampling": "Identical fresh requests with no shared conversation history",
        "input_exposes_previous_votes": False,
    })

    def collect(i):
        label = f"luna-{i:02}"
        try:
            response, meta = api(args.out, label, body, key, show_text=False)
            if meta["http_status"] != 200 or response.get("status") != "completed":
                return {"label": label, "valid": False, "error": meta.get("error")}
            if any(item["type"].endswith("call") for item in response.get("output", [])):
                raise ValueError("Unexpected tool execution")
            report = parse_report(output_text(response), paths)
            save(args.out / f"{label}.classifications.json", report)
            return {"label": label, "valid": True, "report": report}
        except Exception as error:
            return {"label": label, "valid": False, "error": str(error).replace(key, "[REDACTED]")}

    records, reports = [], {}
    with ThreadPoolExecutor(max_workers=min(5, args.samples)) as pool:
        futures = [pool.submit(collect, i) for i in range(1, args.samples + 1)]
        for future in as_completed(futures):
            result = future.result()
            if result["valid"]:
                reports[result["label"]] = result.pop("report")
            records.append(result)
            save(args.out / "collection.json", sorted(records, key=lambda r: r["label"]))
            print(json.dumps({"collected": result}), flush=True)
    summary = calculate(dict(sorted(reports.items())), paths)
    summary["attempted"] = args.samples
    save(args.out / "agreement.json", summary)
    with (args.out / "field-votes.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["field", "nullable_yes", "nullable_no", "unknown", "not_present",
                         "nullability_pairwise_agreement", "omittable_yes", "omittable_no"])
        for path, data in summary["per_field"].items():
            votes, omittable = data["nullable"]["counts"], data["omittable"]["counts"]
            writer.writerow([path, *[votes.get(k, 0) for k in ["yes", "no", "unknown", "not_present"]],
                             data["nullable"]["agreement"], omittable.get("yes", 0), omittable.get("no", 0)])
    for path in args.out.glob("*.json"):
        if key in path.read_text():
            raise RuntimeError(f"Credential unexpectedly present in {path.name}")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_field"}), flush=True)


if __name__ == "__main__":
    main()
