#!/usr/bin/env python3
"""Launch Codex search workers and maintain resumable cache-age dating runs."""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "oai-index-scan" / "tmp" / "cache-dating"
FINAL_BASE = ROOT / "oai-index-scan" / "results" / "cache-dating"
WORKER_POOL = ROOT / "oai-index-scan" / "spider" / "worker_pool.py"
TOOLS = ROOT / "oai-index-scan" / "tools"
sys.path.insert(0, str(TOOLS))
from cache_age_bounds import UNIT_MS, implied_bounds, intersection  # noqa: E402


RUN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
SEPARATOR_RE = re.compile(r"\n?-{40,}\n?")
HEADING_RE = re.compile(r"^(.+?) \((https?://[^\s]+)\)\s*$")
CACHE_RE = re.compile(r"\b(Crawled|Cached):\s*([^;\n]+)", re.IGNORECASE)
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def iso_utc(value: int | None = None) -> str:
    value = now_ms() if value is None else value
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")


def dump_line(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=False) + "\n"


def read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(dump_line(row))
        output.flush()
    temporary.replace(path)


def response_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    response = payload.get("tool_response")
    if isinstance(response, str):
        return response
    if isinstance(response, list):
        return "\n\n".join(
            str(item.get("text", "")) for item in response if isinstance(item, dict)
        )
    return ""


def parse_results(text: str) -> list[dict[str, str | None]]:
    results: list[dict[str, str | None]] = []
    for section in SEPARATOR_RE.split(text):
        lines = section.strip().splitlines()
        if not lines:
            continue
        heading = HEADING_RE.match(lines[0].strip())
        if heading is None:
            continue
        cache = CACHE_RE.search(section)
        results.append({
            "title": heading.group(1).strip(),
            "page_url": heading.group(2).strip(),
            "cache_field": cache.group(1).title() if cache else None,
            "raw_cache_age": cache.group(2).strip() if cache else None,
        })
    return results


def parse_structured_results(document: dict[str, object]) -> list[dict[str, str | None]]:
    """Extract typed results included on Responses web_search_call items."""
    parsed = []
    for item in document.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "web_search_call":
            continue
        for result in item.get("results", []):
            if not isinstance(result, dict) or result.get("type") != "text_result":
                continue
            snippet = result.get("snippet") if isinstance(result.get("snippet"), str) else ""
            cache = CACHE_RE.search(snippet)
            parsed.append({
                "title": result.get("title") if isinstance(result.get("title"), str) else None,
                "page_url": result.get("url") if isinstance(result.get("url"), str) else None,
                "cache_field": cache.group(1).title() if cache else None,
                "raw_cache_age": cache.group(2).strip() if cache else None,
                "snippet": snippet,
            })
    return parsed


def load_api_key(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").strip()
    key = raw.split("=", 1)[1].strip().strip("'\"") \
        if raw.startswith("OPENAI_API_KEY=") else raw
    if not key:
        raise ValueError(f"empty API key file: {path}")
    return key


def responses_search(query: str, api_key: str,
                     endpoint: str = OPENAI_RESPONSES_URL) -> tuple[bytes, int, int]:
    """Perform one cache-only structured search and return body plus time envelope."""
    payload = {
        "model": "gpt-5.6-luna",
        "reasoning": {"effort": "low"},
        "tools": [{"type": "web_search", "external_web_access": False}],
        "tool_choice": {"type": "web_search"},
        "include": ["web_search_call.results", "web_search_call.action.sources"],
        "input": ("Search the web for this exact query. Do not browse or fetch live pages. "
                  f"Briefly report what the indexed search returns: {query}"),
        "max_output_tokens": 600,
    }
    request = urllib.request.Request(
        endpoint, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
    )
    started = now_ms()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise RuntimeError(f"Responses API HTTP {error.code}: {detail[:2000]}") from error
    finished = now_ms()
    return body, started, finished


class DatingRun:
    def __init__(self, run_id: str):
        if not RUN_RE.fullmatch(run_id):
            raise ValueError("run ID may contain only letters, digits, underscore, and hyphen")
        self.run_id = run_id
        self.path = BASE / run_id

    @contextmanager
    def locked(self) -> Iterator[None]:
        self.path.mkdir(parents=True, exist_ok=True)
        with (self.path / ".lock").open("a+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield

    def require(self) -> None:
        if not (self.path / "manifest.json").exists():
            raise ValueError(f"cache-dating run does not exist: {self.run_id}")

    def event(self, event_type: str, **details: object) -> None:
        path = self.path / "events.jsonl"
        sequence = len(read_jsonl(path)) + 1
        record = {"event_sequence": sequence, "event_time": iso_utc(),
                  "run_id": self.run_id, "event_type": event_type, **details}
        with path.open("a", encoding="utf-8") as output:
            output.write(dump_line(record))
            output.flush()

    def init(self, precision_ms: int, model_verified: bool) -> None:
        if (self.path / "manifest.json").exists():
            raise ValueError("run already exists")
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / "raw").mkdir(exist_ok=True)
        manifest = {
            "run_id": self.run_id, "protocol_version": "1.0",
            "created_at": iso_utc(), "renderer_model": "floor_fixed_duration_v1",
            "renderer_model_verified": model_verified,
            "target_precision_ms": precision_ms,
        }
        (self.path / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        for name in ("targets.jsonl", "events.jsonl", "observations.jsonl",
                     "estimates.jsonl", "schedule.jsonl"):
            (self.path / name).touch()

    def add_target(self, target_id: str, query: str, page_url: str,
                   title_contains: str | None, series_id: str) -> None:
        self.add_targets([{"target_id": target_id, "query": query,
                           "page_url": page_url, "title_contains": title_contains,
                           "series_id": series_id}])

    def add_targets(self, incoming: list[dict[str, object]]) -> None:
        """Validate and atomically register one or more targets."""
        self.require()
        targets = read_jsonl(self.path / "targets.jsonl")
        schedule = read_jsonl(self.path / "schedule.jsonl")
        existing_ids = {str(row["target_id"]) for row in targets}
        incoming_ids: set[str] = set()
        normalized = []
        for number, row in enumerate(incoming, 1):
            target_id = row.get("target_id")
            query = row.get("query")
            page_url = row.get("page_url")
            if not all(isinstance(value, str) and value for value in
                       (target_id, query, page_url)):
                raise ValueError(
                    f"target row {number} requires nonempty string target_id, query, and page_url"
                )
            if target_id in existing_ids or target_id in incoming_ids:
                raise ValueError(f"duplicate target ID: {target_id}")
            incoming_ids.add(target_id)
            normalized.append({
                "target_id": target_id,
                "series_id": row.get("series_id", "web-default"),
                "query": query,
                "page_url": page_url,
                "title_contains": row.get("title_contains"),
            })
        registered_at = now_ms()
        for target in normalized:
            targets.append(target)
            probe_id = f"p{len(schedule) + 1:08d}"
            scheduled = {"probe_id": probe_id, "target_id": target["target_id"],
                         "series_id": target["series_id"],
                         "planned_at_unix_ms": registered_at,
                         "reason": "initial", "state": "pending"}
            schedule.append(scheduled)
            self.event("target_registered", target_id=target["target_id"],
                       series_id=target["series_id"], details=target)
            self.event("probe_scheduled", target_id=target["target_id"],
                       series_id=target["series_id"], operation_id=probe_id,
                       details=scheduled)
        write_jsonl(self.path / "targets.jsonl", targets)
        write_jsonl(self.path / "schedule.jsonl", schedule)
    def due(self, force: bool = False) -> list[dict[str, object]]:
        cutoff = now_ms()
        return [row for row in read_jsonl(self.path / "schedule.jsonl")
                if row["state"] == "pending" and
                (force or int(row["planned_at_unix_ms"]) <= cutoff)]

    def recover_running(self) -> None:
        """Requeue claims left behind by a terminated scheduler process."""
        schedule = read_jsonl(self.path / "schedule.jsonl")
        changed = False
        for row in schedule:
            if row["state"] != "running":
                continue
            row["state"] = "pending"
            row["recovered_at_unix_ms"] = now_ms()
            self.event("probe_scheduled", target_id=row["target_id"],
                       series_id=row["series_id"], operation_id=row["probe_id"],
                       details={"reason": "recovered_interrupted_claim"})
            changed = True
        if changed:
            write_jsonl(self.path / "schedule.jsonl", schedule)

    def launch(self, probes: list[dict[str, object]], workers: int) -> list[dict[str, object]]:
        targets = {row["target_id"]: row for row in
                   read_jsonl(self.path / "targets.jsonl")}
        batch = len(list((self.path / "raw").glob("search_*"))) + 1
        child_id = f"dating_{self.run_id}_{batch:06d}"
        child_path = ROOT / "oai-index-scan" / "tmp" / "spider" / child_id
        seeds = self.path / f".batch_{batch:06d}.seeds.txt"
        seeds.write_text("\n".join(str(targets[p["target_id"]]["query"])
                                   for p in probes) + "\n", encoding="utf-8")
        schedule = read_jsonl(self.path / "schedule.jsonl")
        probe_ids = {p["probe_id"] for p in probes}
        claimed_at = now_ms()
        for row in schedule:
            if row["probe_id"] in probe_ids:
                row["state"] = "running"
                row["claimed_at_unix_ms"] = claimed_at
                self.event("search_claimed", target_id=row["target_id"],
                           series_id=row["series_id"], operation_id=row["probe_id"],
                           details={"child_run_id": child_id})
        write_jsonl(self.path / "schedule.jsonl", schedule)
        command = [sys.executable, str(WORKER_POOL), "--run", child_id,
                   "--seeds-file", str(seeds), "--max-pages",
                   str(max(20, len(probes) * 20)), "--workers",
                   str(min(workers, len(probes))), "--max-calls-per-worker", "1",
                   "--max-terms-per-webrun-call", "1",
                   "--max-operations-per-webrun-call", "1",
                   "--no-direct-url-opens", "--search-only"]
        completed = subprocess.run(command, cwd=ROOT, check=False)
        finished_at = now_ms()
        try:
            return self.ingest(child_id, probes, claimed_at, finished_at,
                               completed.returncode, targets)
        finally:
            seeds.unlink(missing_ok=True)

    def launch_responses(self, probes: list[dict[str, object]], workers: int,
                         api_key_file: Path) -> list[dict[str, object]]:
        """Run one direct structured Responses search per due target."""
        key = load_api_key(api_key_file)
        targets = {row["target_id"]: row for row in
                   read_jsonl(self.path / "targets.jsonl")}
        schedule = read_jsonl(self.path / "schedule.jsonl")
        probe_ids = {row["probe_id"] for row in probes}
        for row in schedule:
            if row["probe_id"] in probe_ids:
                row["state"] = "running"
                row["claimed_at_unix_ms"] = now_ms()
                self.event("search_claimed", target_id=row["target_id"],
                           series_id=row["series_id"], operation_id=row["probe_id"],
                           details={"backend": "responses_api",
                                    "external_web_access": False})
        write_jsonl(self.path / "schedule.jsonl", schedule)
        completed: dict[object, tuple[bytes, int, int]] = {}
        with ThreadPoolExecutor(max_workers=min(workers, len(probes))) as executor:
            futures = {
                executor.submit(responses_search,
                                str(targets[probe["target_id"]]["query"]), key): probe
                for probe in probes
            }
            for future in as_completed(futures):
                completed[futures[future]["probe_id"]] = future.result()
        observations = read_jsonl(self.path / "observations.jsonl")
        new_observations = []
        schedule = read_jsonl(self.path / "schedule.jsonl")
        for probe in probes:
            body, before, after = completed[probe["probe_id"]]
            document = json.loads(body)
            raw_sequence = len(list((self.path / "raw").glob("search_*"))) + 1
            raw_name = f"raw/search_{raw_sequence:06d}.json"
            (self.path / raw_name).write_bytes(body)
            target = targets[probe["target_id"]]
            observation = self.make_structured_observation(
                probe, target, document, before, after, raw_name
            )
            observation["observation_id"] = f"o{len(observations) + 1:08d}"
            observations.append(observation)
            new_observations.append(observation)
            for row in schedule:
                if row["probe_id"] == probe["probe_id"]:
                    row["state"] = "complete"
                    row["completed_at_unix_ms"] = after
                    row["observation_id"] = observation["observation_id"]
            self.event("search_completed", target_id=probe["target_id"],
                       series_id=probe["series_id"], operation_id=probe["probe_id"],
                       details={"backend": "responses_api",
                                "external_web_access": False,
                                "raw_response": raw_name,
                                "response_id": document.get("id")})
            self.event("observation_recorded", target_id=probe["target_id"],
                       series_id=probe["series_id"], operation_id=probe["probe_id"],
                       details=observation)
        write_jsonl(self.path / "observations.jsonl", observations)
        write_jsonl(self.path / "schedule.jsonl", schedule)
        self.rematerialize()
        return new_observations

    def make_structured_observation(
        self, probe: dict[str, object], target: dict[str, object],
        document: dict[str, object], before: int, after: int, raw_name: str,
    ) -> dict[str, object]:
        candidates = parse_structured_results(document)
        exact = [result for result in candidates
                 if result["page_url"] == target["page_url"] and
                 (not target.get("title_contains") or
                  str(target["title_contains"]) in str(result["title"]))]
        status = "exact" if len(exact) == 1 else "missing" if not exact else "ambiguous"
        midpoint = (before + after) // 2
        uncertainty = math.ceil((after - before) / 2)
        result = exact[0] if len(exact) == 1 else {}
        observation: dict[str, object] = {
            "observation_id": "pending", "probe_id": probe["probe_id"],
            "target_id": probe["target_id"], "series_id": probe["series_id"],
            "request_started_unix_ms": before,
            "response_received_unix_ms": after,
            "retrieved_at_unix_ms": midpoint, "retrieved_at_utc": iso_utc(midpoint),
            "clock_source": "system_utc", "clock_uncertainty_ms": uncertainty,
            "query": target["query"], "backend": "responses_api",
            "external_web_access": False, "response_id": document.get("id"),
            "result_page_url": result.get("page_url"), "match_status": status,
            "cache_field": result.get("cache_field"),
            "raw_cache_age": result.get("raw_cache_age"),
            "raw_response": raw_name, "returned_results": candidates,
        }
        self.add_implied_bound(observation)
        return observation

    @staticmethod
    def add_implied_bound(observation: dict[str, object]) -> None:
        if observation["match_status"] != "exact" or not observation.get("raw_cache_age"):
            return
        try:
            bound = implied_bounds(
                int(observation["retrieved_at_unix_ms"]),
                str(observation["raw_cache_age"]),
                int(observation["clock_uncertainty_ms"]),
            )
            observation.update({
                "parsed_value": bound["parsed_value"],
                "parsed_unit": bound["parsed_unit"],
                "renderer_model": bound["renderer_model"],
                "implied_lower_unix_ms": bound["lower_unix_ms"],
                "implied_lower_inclusive": bound["lower_inclusive"],
                "implied_upper_unix_ms": bound["upper_unix_ms"],
                "implied_upper_inclusive": bound["upper_inclusive"],
            })
        except ValueError as exc:
            observation["parse_error"] = str(exc)

    def ingest(self, child_id: str, probes: list[dict[str, object]], start_ms: int,
               end_ms: int, returncode: int,
               targets: dict[object, dict[str, object]]) -> list[dict[str, object]]:
        child_path = ROOT / "oai-index-scan" / "tmp" / "spider" / child_id
        responses: dict[str, tuple[str, int, int]] = {}
        db_path = child_path / "state.sqlite3"
        if db_path.exists():
            db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            db.row_factory = sqlite3.Row
            try:
                rows = db.execute(
                    "SELECT tool_input_json,raw_path,leased_at,committed_at "
                    "FROM operations WHERE kind='search' AND raw_path IS NOT NULL"
                )
                for row in rows:
                    query = json.loads(row["tool_input_json"])["search_query"][0]["q"]
                    payload = json.loads((child_path / row["raw_path"]).read_text())
                    leased = parse_db_time(row["leased_at"], start_ms)
                    committed = parse_db_time(row["committed_at"], end_ms)
                    responses[query] = (response_text(payload), leased, committed)
            finally:
                db.close()
        schedule = read_jsonl(self.path / "schedule.jsonl")
        observations = read_jsonl(self.path / "observations.jsonl")
        new_observations: list[dict[str, object]] = []
        for probe in probes:
            target = targets[probe["target_id"]]
            query = str(target["query"])
            response = responses.get(query)
            raw_sequence = len(list((self.path / "raw").glob("search_*.txt"))) + 1
            raw_name = f"raw/search_{raw_sequence:06d}.txt"
            text, before, after = response if response else ("", start_ms, end_ms)
            (self.path / raw_name).write_text(text, encoding="utf-8")
            observation = self.make_observation(probe, target, text, before, after,
                                                raw_name, returncode)
            observation["observation_id"] = f"o{len(observations) + 1:08d}"
            observations.append(observation)
            new_observations.append(observation)
            for row in schedule:
                if row["probe_id"] == probe["probe_id"]:
                    row["state"] = "complete"
                    row["completed_at_unix_ms"] = after
                    row["observation_id"] = observation["observation_id"]
            self.event("search_completed", target_id=probe["target_id"],
                       series_id=probe["series_id"], operation_id=probe["probe_id"],
                       details={"child_run_id": child_id, "returncode": returncode,
                                "raw_response": raw_name})
            self.event("observation_recorded", target_id=probe["target_id"],
                       series_id=probe["series_id"], operation_id=probe["probe_id"],
                       details=observation)
        write_jsonl(self.path / "observations.jsonl", observations)
        write_jsonl(self.path / "schedule.jsonl", schedule)
        self.rematerialize()
        return new_observations

    def make_observation(self, probe: dict[str, object], target: dict[str, object],
                         text: str, before: int, after: int, raw_name: str,
                         returncode: int) -> dict[str, object]:
        exact = [result for result in parse_results(text)
                 if result["page_url"] == target["page_url"] and
                 (not target.get("title_contains") or
                  str(target["title_contains"]) in str(result["title"]))]
        status = "exact" if len(exact) == 1 else "missing" if not exact else "ambiguous"
        if returncode and not text:
            status = "tool_error"
        midpoint = (before + after) // 2
        uncertainty = math.ceil((after - before) / 2)
        result = exact[0] if len(exact) == 1 else {}
        candidates = parse_results(text)
        observation: dict[str, object] = {
            "observation_id": f"o{len(read_jsonl(self.path / 'observations.jsonl')) + 1:08d}",
            "probe_id": probe["probe_id"], "target_id": probe["target_id"],
            "series_id": probe["series_id"], "request_started_unix_ms": before,
            "response_received_unix_ms": after, "retrieved_at_unix_ms": midpoint,
            "retrieved_at_utc": iso_utc(midpoint), "clock_source": "system_utc",
            "clock_uncertainty_ms": uncertainty, "query": target["query"],
            "backend": "codex",
            "result_page_url": result.get("page_url"), "match_status": status,
            "cache_field": result.get("cache_field"),
            "raw_cache_age": result.get("raw_cache_age"), "raw_response": raw_name,
            "returned_results": candidates,
        }
        self.add_implied_bound(observation)
        return observation

    def rematerialize(self) -> None:
        manifest = json.loads((self.path / "manifest.json").read_text())
        observations = read_jsonl(self.path / "observations.jsonl")
        estimates = []
        schedule = read_jsonl(self.path / "schedule.jsonl")
        targets = read_jsonl(self.path / "targets.jsonl")
        for target in targets:
            all_valid = [row for row in observations
                         if row["target_id"] == target["target_id"] and
                         row["series_id"] == target["series_id"] and
                         "implied_lower_unix_ms" in row]
            active_backend = (str(all_valid[-1].get("backend", "codex"))
                              if all_valid else None)
            valid = [row for row in all_valid
                     if str(row.get("backend", "codex")) == active_backend]
            if not valid:
                estimates.append({"target_id": target["target_id"],
                                  "series_id": target["series_id"],
                                  "status": "monitoring", "observation_count": 0})
                observed = [row for row in observations
                            if row["target_id"] == target["target_id"] and
                            row["series_id"] == target["series_id"]]
                pending = any(row["target_id"] == target["target_id"] and
                              row["series_id"] == target["series_id"] and
                              row["state"] in {"pending", "running"}
                              for row in schedule)
                if observed and not pending:
                    planned = now_ms() + UNIT_MS["day"]
                    probe_id = f"p{len(schedule) + 1:08d}"
                    row = {"probe_id": probe_id, "target_id": target["target_id"],
                           "series_id": target["series_id"],
                           "planned_at_unix_ms": planned,
                           "planned_at_utc": iso_utc(planned),
                           "reason": "coarse_or_unparsed_label_monitor",
                           "state": "pending"}
                    schedule.append(row)
                    self.event("probe_scheduled", target_id=target["target_id"],
                               series_id=target["series_id"],
                               operation_id=probe_id, details=row)
                continue
            inputs = [{"lower_unix_ms": row["implied_lower_unix_ms"],
                       "lower_inclusive": row["implied_lower_inclusive"],
                       "upper_unix_ms": row["implied_upper_unix_ms"],
                       "upper_inclusive": row["implied_upper_inclusive"]}
                      for row in valid]
            estimate = intersection(inputs)
            estimate.update({"target_id": target["target_id"],
                             "series_id": target["series_id"],
                             "backend": active_backend,
                             "model_verified": manifest["renderer_model_verified"]})
            if estimate["status"] == "bounded" and not manifest["renderer_model_verified"]:
                estimate["status"] = "unverified_model"
            precision = manifest["target_precision_ms"]
            precise_enough = (estimate.get("width_ms") is not None and
                              estimate["width_ms"] <= precision)
            complete = precise_enough and manifest["renderer_model_verified"]
            if complete:
                estimate["status"] = "complete"
            estimates.append(estimate)
            self.event("estimate_updated", target_id=target["target_id"],
                       series_id=target["series_id"], details=estimate)
            pending = any(row["target_id"] == target["target_id"] and
                          row["series_id"] == target["series_id"] and
                          row["state"] in {"pending", "running"} for row in schedule)
            if not complete and estimate["status"] != "conflict" and not pending:
                latest = valid[-1]
                unit = UNIT_MS[str(latest["parsed_unit"])]
                midpoint = (int(estimate["lower_unix_ms"]) +
                            int(estimate["upper_unix_ms"])) // 2
                k = int(latest["parsed_value"]) + 1
                planned = midpoint + k * unit
                while planned <= now_ms():
                    k += 1
                    planned = midpoint + k * unit
                probe_id = f"p{len(schedule) + 1:08d}"
                row = {"probe_id": probe_id, "target_id": target["target_id"],
                       "series_id": target["series_id"],
                       "planned_at_unix_ms": planned, "planned_at_utc": iso_utc(planned),
                       "reason": "midpoint_transition", "boundary_label_value": k,
                       "state": "pending"}
                schedule.append(row)
                self.event("probe_scheduled", target_id=target["target_id"],
                           series_id=target["series_id"], operation_id=probe_id,
                           details=row)
            elif complete:
                self.event("target_completed", target_id=target["target_id"],
                           series_id=target["series_id"], details=estimate)
        write_jsonl(self.path / "estimates.jsonl", estimates)
        write_jsonl(self.path / "schedule.jsonl", schedule)

    def status(self) -> dict[str, object]:
        self.require()
        schedule = read_jsonl(self.path / "schedule.jsonl")
        return {"run_id": self.run_id,
                "target_count": len(read_jsonl(self.path / "targets.jsonl")),
                "observation_count": len(read_jsonl(self.path / "observations.jsonl")),
                "schedule": {state: sum(row["state"] == state for row in schedule)
                             for state in ("pending", "running", "complete")},
                "next_probe_at": min((row["planned_at_unix_ms"] for row in schedule
                                      if row["state"] == "pending"), default=None),
                "estimates": read_jsonl(self.path / "estimates.jsonl")}

    def finalize(self) -> Path:
        self.require()
        destination = FINAL_BASE / self.run_id
        if destination.exists():
            raise ValueError(f"final output already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.path, destination, ignore=shutil.ignore_patterns(".lock"))
        return destination


def read_target_import(path: Path) -> list[dict[str, object]]:
    """Read the strict three-field bulk-import format."""
    rows = read_jsonl(path)
    required = {"target_id", "query", "page_url"}
    for number, row in enumerate(rows, 1):
        if set(row) != required:
            raise ValueError(
                f"{path}: row {number} must contain exactly target_id, query, page_url"
            )
    return rows


def parse_db_time(value: str | None, fallback: int) -> int:
    if not value:
        return fallback
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return int(datetime.fromisoformat(normalized).timestamp() * 1000)


def print_observation(run: DatingRun, observation: dict[str, object],
                      show_raw: bool) -> None:
    raw_path = run.path / str(observation["raw_response"])
    print(f"probe {observation['probe_id']} target={observation['target_id']} "
          f"status={observation['match_status']}")
    if observation.get("raw_cache_age"):
        print(f"  {observation.get('cache_field')}: "
              f"{observation['raw_cache_age']}")
    if observation.get("implied_lower_unix_ms") is not None:
        lower = iso_utc(int(observation["implied_lower_unix_ms"]))
        upper = iso_utc(int(observation["implied_upper_unix_ms"]))
        width = (int(observation["implied_upper_unix_ms"]) -
                 int(observation["implied_lower_unix_ms"]))
        print(f"  implied entry interval: ({lower}, {upper}] width_ms={width}")
    candidates = observation.get("returned_results", [])
    print(f"  returned_results={len(candidates) if isinstance(candidates, list) else 0} "
          f"raw={raw_path}")
    if observation["match_status"] != "exact" and isinstance(candidates, list):
        for candidate in candidates[:5]:
            print(f"  candidate: {candidate.get('page_url')} "
                  f"[{candidate.get('cache_field')}: {candidate.get('raw_cache_age')}]")
        if len(candidates) > 5:
            print(f"  ... {len(candidates) - 5} more candidates in raw response")
    if show_raw:
        print(f"--- raw response for {observation['probe_id']} ---")
        print(raw_path.read_text(encoding="utf-8"), end="\n")


def print_batch_summary(observations: list[dict[str, object]]) -> None:
    statuses: dict[str, int] = {}
    for observation in observations:
        status = str(observation["match_status"])
        statuses[status] = statuses.get(status, 0) + 1
    rendered = " ".join(f"{key}={statuses[key]}" for key in sorted(statuses))
    print(f"batch complete: probes={len(observations)} {rendered}".rstrip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "add-target", "run", "status", "finalize"):
        command = sub.add_parser(name)
        command.add_argument("--run", required=True)
        if name == "init":
            command.add_argument("--precision-ms", type=int, default=86_400_000)
            command.add_argument("--model-verified", action="store_true")
        elif name == "add-target":
            source = command.add_mutually_exclusive_group(required=True)
            source.add_argument("--target-id")
            source.add_argument("--targets-jsonl", type=Path,
                                help="JSONL with exactly target_id, query, page_url")
            command.add_argument("--query")
            command.add_argument("--page-url")
            command.add_argument("--title-contains")
            command.add_argument("--series-id", default="web-default")
        elif name == "run":
            command.add_argument("--workers", type=int, default=4)
            command.add_argument("--backend", choices=("responses", "codex"),
                                 default="responses")
            command.add_argument("--api-key-file", type=Path,
                                 default=Path("/tmp/swarmchasers.txt"))
            command.add_argument("--force", action="store_true")
            command.add_argument("--show-raw", action="store_true",
                                 help="print complete raw search responses after summaries")
            command.add_argument("--wait", action="store_true",
                                 help="remain running and launch probes as they become due")
            command.add_argument("--poll-seconds", type=int, default=60)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    run = DatingRun(args.run)
    try:
        if args.command == "run":
            if args.workers < 1 or args.poll_seconds < 1:
                parser.error("worker and poll limits must be positive")
            while True:
                with run.locked():
                    run.require()
                    run.recover_running()
                    probes = run.due(args.force)
                    if probes:
                        if args.backend == "responses":
                            completed = run.launch_responses(
                                probes, args.workers, args.api_key_file
                            )
                        else:
                            completed = run.launch(probes, args.workers)
                        for observation in completed:
                            print_observation(run, observation, args.show_raw)
                        print_batch_summary(completed)
                        args.force = False
                    pending = [row for row in read_jsonl(run.path / "schedule.jsonl")
                               if row["state"] == "pending"]
                if not args.wait or not pending:
                    if not probes:
                        print("no probes due")
                    break
                delay = max(0, min(int(row["planned_at_unix_ms"])
                                   for row in pending) - now_ms()) / 1000
                time.sleep(min(args.poll_seconds, max(0.05, delay)))
            return 0
        with run.locked():
            if args.command == "init":
                if args.precision_ms < 1:
                    parser.error("--precision-ms must be positive")
                run.init(args.precision_ms, args.model_verified)
            elif args.command == "add-target":
                if args.targets_jsonl:
                    if args.query or args.page_url or args.title_contains or \
                            args.series_id != "web-default":
                        parser.error("bulk import cannot be combined with per-target options")
                    imported = read_target_import(args.targets_jsonl)
                    run.add_targets(imported)
                    print(f"added {len(imported)} targets from {args.targets_jsonl}")
                else:
                    if not args.query or not args.page_url:
                        parser.error("--target-id requires --query and --page-url")
                    run.add_target(args.target_id, args.query, args.page_url,
                                   args.title_contains, args.series_id)
                    print(f"added target {args.target_id}")
            elif args.command == "status":
                print(json.dumps(run.status(), indent=2))
            elif args.command == "finalize":
                print(run.finalize())
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
