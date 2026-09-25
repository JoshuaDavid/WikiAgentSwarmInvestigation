#!/usr/bin/env python3
"""Calculate raw pairwise agreement among the saved independent schema reports."""

import argparse
from collections import Counter
from itertools import combinations
import json
from pathlib import Path

from probe import save


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def normalize(value, key=None):
    """Ignore prose/default annotations and set ordering; retain constraints.

    These reports use inline schemas with type arrays. Fail on alternate schema
    compositions instead of implying a general JSON Schema equivalence checker.
    """
    if isinstance(value, dict):
        unsupported = set(value) & {"$ref", "$defs", "definitions", "anyOf", "oneOf", "allOf"}
        if unsupported:
            raise ValueError(f"Unsupported representation needs explicit review: {unsupported}")
        result = {k: normalize(v, k) for k, v in value.items()
                  if k not in {"description", "title", "default", "examples", "$schema", "$id"}}
        if result.get("type") == "object":
            result.setdefault("required", [])
            result.setdefault("additionalProperties", True)
        return result
    if isinstance(value, list):
        items = [normalize(v) for v in value]
        return sorted(items, key=encoded) if key in {"type", "enum", "required"} else items
    return value


ABSENT = {"not_reported": True}


def fields(schema):
    records = {}

    def visit(node, path=""):
        for name, value in node.get("properties", {}).items():
            field_path = f"{path}.{name}" if path else name
            normalized = normalize(value)
            kind = normalized.get("type", ABSENT)
            kind = [kind] if isinstance(kind, str) else kind
            constraints = {k: v for k, v in normalized.items()
                           if k not in {"type", "enum", "properties", "items", "required"}}
            record = {
                "type": kind, "required": name in node.get("required", []),
                "enum": normalized.get("enum", ABSENT),
                "default": value.get("default", ABSENT), "constraints": constraints,
            }
            if "items" in value:
                item_type = value["items"].get("type", ABSENT)
                record["item_type"] = [item_type] if isinstance(item_type, str) else item_type
            records[field_path] = record
            visit(value, field_path)
        if isinstance(node.get("items"), dict):
            visit(node["items"], path + "[]")

    visit(schema)
    return records


def agreement(values):
    pairs = list(combinations(values, 2))
    agreeing = sum(a == b for a, b in pairs)
    return {"agreeing_pairs": agreeing, "total_pairs": len(pairs),
            "fraction": agreeing / len(pairs)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    reports = {p.name.split(".")[0]: json.loads(p.read_text())
               for p in sorted(args.run.glob("sample-*.schema.json"))}
    if len(reports) < 2:
        raise ValueError("Need at least two valid reports")
    record_sets = {label: fields(schema) for label, schema in reports.items()}
    paths = sorted(set.union(*(set(r) for r in record_sets.values())))
    facets = ["type", "required", "enum", "default", "constraints", "item_type"]
    field_metrics, differences = {}, []
    for facet in facets:
        score, pairs, unanimous = 0, 0, 0
        for path in paths:
            values = [r.get(path, {}).get(facet, ABSENT) for r in record_sets.values()]
            result = agreement(values)
            score += result["agreeing_pairs"]
            pairs += result["total_pairs"]
            same = result["agreeing_pairs"] == result["total_pairs"]
            unanimous += same
            if not same:
                groups = {}
                for label, value in zip(record_sets, values):
                    group = groups.setdefault(encoded(value), {"value": value, "reports": []})
                    group["reports"].append(label)
                differences.append({"path": path, "facet": facet, "variants": list(groups.values())})
        field_metrics[facet] = {"agreeing_pairs": score, "total_pairs": pairs,
                               "fraction": score / pairs, "unanimous_fields": unanimous,
                               "fields": len(paths)}
    normalized = [normalize(schema) for schema in reports.values()]
    groups = Counter(encoded(schema) for schema in normalized)
    pair_table = []
    for (a, ra), (b, rb) in combinations(reports.items(), 2):
        pair_table.append({"a": a, "b": b, "exact_json_equal": ra == rb,
                           "normalized_equal": normalize(ra) == normalize(rb)})
    summary = {
        "attempted": len(json.loads((args.run / "collection.json").read_text())),
        "valid_reports": len(reports), "named_field_paths": len(paths),
        "top_level_fields": list(next(iter(reports.values()))["properties"]),
        "whole_schema": {
            "exact_json": agreement(list(reports.values())),
            "normalized_constraints": agreement(normalized),
            "top_level_field_sets": agreement([sorted(s["properties"]) for s in reports.values()]),
            "all_named_field_sets": agreement([sorted(r) for r in record_sets.values()]),
            "normalized_variant_sizes": sorted(groups.values(), reverse=True),
        },
        "field_metrics": field_metrics, "differences": differences, "pair_table": pair_table,
        "metric": "Raw mean pairwise agreement; not chance-corrected kappa",
        "limitation": "Five fresh samples of one model/prompt measure repeatability, not correctness or independent expert corroboration",
    }
    save(args.run / "agreement.json", summary)
    save(args.run / "field-records.json", record_sets)
    for label, schema in reports.items():
        save(args.run / f"{label}.normalized.json", normalize(schema))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
