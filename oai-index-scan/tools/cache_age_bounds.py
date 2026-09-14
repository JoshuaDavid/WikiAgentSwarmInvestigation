#!/usr/bin/env python3
"""Convert fixed-duration relative cache ages into auditable time bounds."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone


AGE_RE = re.compile(
    r"^\s*(?P<value>\d+)\s+(?P<unit>seconds?|minutes?|hours?|days?|weeks?)\s+ago\s*$",
    re.IGNORECASE,
)
UNIT_MS = {
    "second": 1_000,
    "minute": 60_000,
    "hour": 3_600_000,
    "day": 86_400_000,
    "week": 604_800_000,
}


def parse_time(value: str) -> int:
    """Parse an integer Unix-ms value or an ISO-8601 timestamp."""
    try:
        return int(value)
    except ValueError:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            raise ValueError("ISO timestamp must include a timezone")
        return int(parsed.timestamp() * 1000)


def iso_utc(unix_ms: int) -> str:
    return datetime.fromtimestamp(unix_ms / 1000, timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")


def implied_bounds(retrieved_ms: int, raw_age: str,
                   uncertainty_ms: int = 0) -> dict[str, object]:
    """Return bounds for a verified floor/fixed-duration renderer."""
    match = AGE_RE.fullmatch(raw_age)
    if not match:
        raise ValueError(
            "unsupported age; months, years, and special labels require an "
            "empirically verified provider model"
        )
    value = int(match.group("value"))
    unit = match.group("unit").lower().rstrip("s")
    duration = UNIT_MS[unit]
    lower = retrieved_ms - (value + 1) * duration - uncertainty_ms
    upper = retrieved_ms - value * duration + uncertainty_ms
    return {
        "raw_cache_age": raw_age,
        "parsed_value": value,
        "parsed_unit": unit,
        "renderer_model": "floor_fixed_duration_v1",
        "retrieved_at_unix_ms": retrieved_ms,
        "retrieved_at_utc": iso_utc(retrieved_ms),
        "clock_uncertainty_ms": uncertainty_ms,
        "lower_unix_ms": lower,
        "lower_utc": iso_utc(lower),
        "lower_inclusive": False,
        "upper_unix_ms": upper,
        "upper_utc": iso_utc(upper),
        "upper_inclusive": True,
        "width_ms": upper - lower,
    }


def intersection(bounds: list[dict[str, object]]) -> dict[str, object]:
    if not bounds:
        raise ValueError("at least one bound is required")
    lower = max(int(item["lower_unix_ms"]) for item in bounds)
    upper = min(int(item["upper_unix_ms"]) for item in bounds)
    lower_inclusive = all(
        bool(item["lower_inclusive"])
        for item in bounds if int(item["lower_unix_ms"]) == lower
    )
    upper_inclusive = all(
        bool(item["upper_inclusive"])
        for item in bounds if int(item["upper_unix_ms"]) == upper
    )
    conflict = lower > upper or (lower == upper and not (
        lower_inclusive and upper_inclusive
    ))
    return {
        "status": "conflict" if conflict else "bounded",
        "lower_unix_ms": lower,
        "lower_utc": iso_utc(lower),
        "lower_inclusive": lower_inclusive,
        "upper_unix_ms": upper,
        "upper_utc": iso_utc(upper),
        "upper_inclusive": upper_inclusive,
        "width_ms": None if conflict else upper - lower,
        "observation_count": len(bounds),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    initial = subparsers.add_parser("initial")
    initial.add_argument("--retrieved-at", required=True)
    initial.add_argument("--age", required=True)
    initial.add_argument("--uncertainty-ms", type=int, default=0)
    combine = subparsers.add_parser("intersect")
    combine.add_argument(
        "files", nargs="+", help="JSON files produced by the initial command"
    )
    args = parser.parse_args()
    if args.command == "initial":
        if args.uncertainty_ms < 0:
            parser.error("--uncertainty-ms cannot be negative")
        result = implied_bounds(
            parse_time(args.retrieved_at), args.age, args.uncertainty_ms
        )
    else:
        records = []
        for filename in args.files:
            with open(filename, encoding="utf-8") as handle:
                records.append(json.load(handle))
        result = intersection(records)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
