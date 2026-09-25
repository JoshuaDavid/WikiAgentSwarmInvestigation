#!/usr/bin/env python3
"""Apply observed majority nullability/omittability votes to a full schema."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from probe import save


def majority(counts):
    total = sum(counts.values())
    winners = [label for label, count in counts.items() if count > total / 2]
    if len(winners) != 1 or winners[0] not in {"yes", "no"}:
        raise ValueError(f"No definite strict majority: {counts}")
    return winners[0] == "yes"


def field_nodes(schema):
    result = {}

    def visit(node, path=""):
        for name, child in node.get("properties", {}).items():
            field_path = f"{path}.{name}" if path else name
            result[field_path] = (node, name, child)
            visit(child, field_path)
        if isinstance(node.get("items"), dict):
            visit(node["items"], path + "[]")

    visit(schema)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--votes", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = json.loads(args.base.read_text())
    votes = json.loads(args.votes.read_text())["per_field"]
    schema = copy.deepcopy(base)
    nodes = field_nodes(schema)
    if nodes.keys() != votes.keys():
        raise ValueError("Schema and vote field inventories differ")
    decisions = {}
    for path, (parent, name, node) in nodes.items():
        nullable = majority(votes[path]["nullable"]["counts"])
        omittable = majority(votes[path]["omittable"]["counts"])
        old = copy.deepcopy(node)
        types = node["type"] if isinstance(node["type"], list) else [node["type"]]
        if nullable and "null" not in types:
            node["type"] = [*types, "null"]
        elif not nullable and "null" in types:
            types = [kind for kind in types if kind != "null"]
            node["type"] = types[0] if len(types) == 1 else types
        if "enum" in node:
            if nullable and None not in node["enum"]:
                node["enum"].append(None)
            elif not nullable and None in node["enum"]:
                node["enum"] = [value for value in node["enum"] if value is not None]
        required = parent.setdefault("required", [])
        old_required = name in required
        if omittable and old_required:
            required.remove(name)
        elif not omittable and not old_required:
            required.append(name)
        decisions[path] = {"nullable": nullable, "omittable": omittable,
                           "changed": old != node or old_required != (not omittable)}
    args.out.mkdir(parents=True, exist_ok=False)
    save(args.out / "parameters.json", schema)
    summary = {
        "base": str(args.base), "votes": str(args.votes),
        "fields": len(nodes), "decisions": decisions,
        "changed_fields": [p for p, d in decisions.items() if d["changed"]],
        "identical_to_base": schema == base,
        "schema_sha256": hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest(),
        "unpolled_details": "Non-null types, constraints, defaults, descriptions, and representation retained from the full-schema base",
    }
    save(args.out / "construction.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "decisions"}), flush=True)


if __name__ == "__main__":
    main()
