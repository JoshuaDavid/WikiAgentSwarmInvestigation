#!/usr/bin/env python3
"""Single-writer orchestrator for hook-governed Codex web spiders."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import socket
import socketserver
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[2]
REF_RE = re.compile(r"cite(turn[\w-]+(?:search|view|academia|news|reddit)\d+)")
URL_RE = re.compile(r"https?://[^\s)\]}>\"'†】\ue200\ue201\ue202]+")
LINK_RE = re.compile(r"cite(\d+)†")
LINK_DETAIL_RE = re.compile(r"cite(\d+)†([^†\ue201\n]*?)(?:†([^\ue201\n]*))?\ue201")
CACHED_RE = re.compile(r"(?:Crawled|Cached):\s*([^;\n]+)", re.IGNORECASE)
PUBLISHED_RE = re.compile(r"\bPublished:\s*[^;\n]+", re.IGNORECASE)
FETCH_FAILURE_RE = re.compile(r"\bFailed to fetch\b", re.IGNORECASE)
# WebRun normally emits a long rule between batch members, but cached bodies
# sometimes place that rule directly after the final rendered line instead of
# on its own line. Do not require surrounding newlines.
# WebRun's batch delimiter is a long rule (currently 80 hyphens). Cached
# Markdown commonly contains shorter Setext/visual rules, which are page body
# content and must not split a result section.
SEPARATOR_RE = re.compile(r"[ \t]*(?:\r?\n)?(?<!-)-{60,}(?!-)(?:\r?\n)?[ \t]*")
RESULT_JOINER = "\n--------------------------------------------------------------------------------\n"
FINGERPRINT_THRESHOLD = 4
INTERNAL_ERROR_CALL_LIMIT = 30
INTERNAL_ERROR_WINDOW_SECONDS = 60
NO_OUTBOUND_URL_PREFIXES: tuple[str, ...] = (
    "https?://swarm.termina.digital",
    "https?://collusion.wiki",
)
NO_OUTBOUND_URL_RE = re.compile(
    r"^https?://(?:swarm\.termina\.digital|collusion\.wiki)(?=[:/?#]|$)",
    re.IGNORECASE,
)
SUSPICIOUS_CHILD_RE = re.compile(
    r"(?i)(?:md\.succ\.ai|pure\.md|r\.jina\.ai|allorigins|proxy|county\.json|"
    r"regcf|sec[_-]?county|\bag(?:title|tstsum|iq|wpc)|\boai(?:jan|aug|xs)|"
    r"mypov|bri2?|uniq|fresh|forcefresh|yourls|goto\.unm|vanderbi\.lt)"
)
FINGERPRINT_RULES: tuple[tuple[str, int, re.Pattern[str]], ...] = (
    ("agent_task_lexicon", 4, re.compile(
        r"(?i)(?:\bag(?:title|tstsum|iq|wpc)[a-z0-9_-]*|\boai(?:jan|aug|xs)[a-z0-9_-]*|"
        r"\bbri2?test\d+|\bmy(?:pov|pop)[a-z0-9_-]*|\b(?:eriechain|nextchain)\d+|"
        r"\bliveagentlive[a-z0-9_-]*|\bmark(?:rand)?[a-z0-9_.-]*\d+|"
        r"\bsec[_-]?county[a-z0-9_-]*|\b(?:signal_ack|urgent_pre_signal_request|state5-[a-z0-9-]+)\b)"
    )),
    ("encoding_malformation", 3, re.compile(
        r"(?i)(?:%2e(?:json|[a-z0-9])|https?%3a/(?!/)|%25(?:3a|2f)|"
        r"/(?:\./){1,}|/files//|\.jsonref\d+|https?://[^\s/?#]+\.(?:[/?#\s]|$)|"
        r"(?:[/?&][^\s#]*:)(?:[&#\s]|$))"
    )),
    ("rendered_citation_or_paste_artifact", 4, re.compile(
        r"(?i)(?:https?://[^\s]+†[a-z0-9.-]+|https?://[^\s]+】|"
        r"\[Button:\s*https?://|https?://[^\s]+//[^\s]*(?:comment|fetch|proxy))"
    )),
    ("jq_transform", 5, re.compile(
        r"(?i)(?:\.regCF_county_\d{4}|\.code\s*(?:\[3:5\]|\|\s*startswith\s*\()|"
        r"\.usd\s*/\s*10\s*\|\s*round\s*/\s*100|"
        r"data\.markdown\.attr=markdown&embed=markdown)"
    )),
    ("nested_proxy_chain", 3, re.compile(
        r"(?i)(?:jqp\.vercel\.app[^\s]+(?:allorigins|md\.succ\.ai)|"
        r"allorigins[^\s]+(?:md\.succ\.ai|proxy\.cors\.sh)|"
        r"proxymule\.com/(?:__proxy__|__PROXY__)|"
        r"translate\.goog/[^\s]+\?_x_tr_sl=)"
    )),
    ("yourls_admin", 4, re.compile(
        r"(?i)(?:yourls|admin)[^\s]*[?&]perpage=(?:60|100|200)"
        r"[^\s]*(?:sort_by=timestamp|sort_order=desc|total_pages=\d+)"
    )),
    ("named_uniqueness_knob", 2, re.compile(
        r"(?i)[?&](?:fresh|forcefreshmethod|shownewstat|travelnew|uniq)=(?:0\.)?\d{5,19}"
    )),
    ("generic_cache_buster", 1, re.compile(
        r"(?i)[?&](?:x|_)=(?:0\.\d{10,}|\d{6,19})(?:[&#\s]|$)"
    )),
    ("fragment_cache_buster", 2, re.compile(
        r"(?i)#(?:DISCVR\d+|UNIQINJECT[a-z0-9_-]+|/__proxy__/mine)"
    )),
    ("path_uniqueness_token", 2, re.compile(
        r"(?i)/(?:uniq0\.\d{10,}|loop\d{6,}|pad\d{13}\.\d{8,})(?:[/?#\s]|$)"
    )),
    ("testbed_probe", 3, re.compile(
        r"(?i)(?:example\.(?:org|com|net)|uniqueexampletest123\.com|dummy\.xyz|"
        r"addnewlogtest\.foo|httpbin\.org/(?:base64|anything))[^\s]*"
        r"(?:uniq|loop|agiq|succ|testabc|protarget|mypov|oai|\d{6,})"
    )),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(compact(value).encode()).hexdigest()


def clean_url(value: str) -> str | None:
    candidate = value.strip().rstrip(".,:;\"'}]†】\ue200\ue201\ue202")
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    if any(character.isspace() for character in candidate):
        return None
    return urlunsplit(parts)


def suppress_outbound_links(url: str) -> bool:
    return NO_OUTBOUND_URL_RE.match(url) is not None


def select_click_links(link_details: dict[int, tuple[str | None, str | None]],
                       fingerprint_score: int) -> tuple[list[int], dict[str, int]]:
    """Reject obvious non-navigation links, then rank and cap the frontier."""
    ranked: list[tuple[int, int]] = []
    rejected: dict[str, int] = {}
    for link_id, (anchor, hostname) in link_details.items():
        label = (anchor or "").strip()
        host = (hostname or "").strip()
        reason: str | None = None
        if not label and not host:
            reason = "missing_anchor_and_hostname"
        elif ("@" in label or re.search(r"(?i)\bemail\s+protected\b", label)) and not host:
            reason = "email_anchor"
        elif re.match(r"(?i)^(?:image(?::|\b)|javascript:|mailto:)", label) and not host:
            reason = "non_navigation_anchor"
        elif re.search(r"(?i)\.(?:png|jpe?g|gif|svg|webp|ico)(?:\?.*)?$", label) and not host:
            reason = "asset_anchor"
        if reason:
            rejected[reason] = rejected.get(reason, 0) + 1
            continue
        evidence = f"{label} {host}"
        priority = (6 if SUSPICIOUS_CHILD_RE.search(evidence) else 0)
        priority += 2 if host else 0
        priority += 2 if re.search(r"https?://", label, re.IGNORECASE) else 0
        ranked.append((priority, link_id))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    limit = 25 if fingerprint_score >= 7 else 10
    selected = [link_id for _, link_id in ranked[:limit]]
    if len(ranked) > limit:
        rejected["parent_link_cap"] = len(ranked) - limit
    return selected, rejected


def response_text(payload: dict[str, Any]) -> str:
    response = payload.get("tool_response")
    if isinstance(response, str):
        return response
    if isinstance(response, list):
        return RESULT_JOINER.join(
            str(item.get("text", "")) for item in response if isinstance(item, dict)
        )
    return compact(response)


def result_sections(text: str) -> list[str]:
    """Split a batched WebRun response without merging adjacent page bodies."""
    return [section.strip() for section in SEPARATOR_RE.split(text) if section.strip()]


def fingerprint_page(text: str) -> tuple[int, list[dict[str, Any]]]:
    """Score each rule at most once and retain compact audit evidence."""
    matches: list[dict[str, Any]] = []
    for rule_id, score, pattern in FINGERPRINT_RULES:
        match = pattern.search(text)
        if match is None:
            continue
        start = max(0, match.start() - 80)
        end = min(len(text), match.end() + 120)
        matches.append({"rule": rule_id, "score": score,
                        "evidence": " ".join(text[start:end].split())[:300]})
    raw_urls = list(dict.fromkeys(URL_RE.findall(text)))
    variant_groups: dict[tuple[str, str], list[str]] = {}
    suspicious_variant = re.compile(
        r"(?i)(?:%2e|%3a|%25|/(?:\./)+|/files//|[?&](?:x|_|fresh|uniq|forcefreshmethod|shownewstat|travelnew)=)"
    )
    for raw_url in raw_urls:
        decoded = raw_url
        for _ in range(3):
            next_value = unquote(decoded)
            if next_value == decoded:
                break
            decoded = next_value
        try:
            parts = urlsplit(decoded)
        except ValueError:
            continue
        normalized_path = re.sub(r"/{2,}", "/", parts.path.replace("/./", "/"))
        key = ((parts.hostname or "").lower().rstrip("."), normalized_path.lower())
        variant_groups.setdefault(key, []).append(raw_url)
    for variants in variant_groups.values():
        if len(variants) < 3 or not any(suspicious_variant.search(url) for url in variants):
            continue
        matches.append({"rule": "same_target_variants", "score": 4,
                        "evidence": " | ".join(variants[:4])[:300]})
        break
    return sum(match["score"] for match in matches), matches


def internal_error_sources(text: str) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for section in result_sections(text):
        if not section.lstrip().startswith("Internal Error"):
            continue
        fetch_failure = FETCH_FAILURE_RE.search(section) is not None
        cache_miss = fetch_failure and re.search(
            r"\bCache miss\b", section, re.IGNORECASE
        ) is not None
        failed_urls = URL_RE.findall(section)
        classification = ("cache_miss" if cache_miss else
                          "fetch_failure" if fetch_failure else "internal_error")
        source = re.search(r"Source:\s*(open|click)\((\{[^\n;]+\})\)", section)
        if source is None:
            details.append({"tool_kind": None, "requested_input": None,
                            "source": "Internal Error (source unavailable)",
                            "classification": classification,
                            "failed_url": clean_url(failed_urls[-1])
                            if failed_urls else None})
            continue
        try:
            requested_input = json.loads(source.group(2))
        except json.JSONDecodeError:
            requested_input = None
        details.append({"tool_kind": source.group(1),
                        "requested_input": requested_input,
                        "source": source.group(0).removeprefix("Source: "),
                        "classification": classification,
                        "failed_url": clean_url(failed_urls[-1])
                        if failed_urls else None})
    return details


def section_source(section: str) -> tuple[str | None, dict[str, Any] | None]:
    source = re.search(r"Source:\s*(search|open|click)\((\{[^\n;]+\})\)", section)
    if source is None:
        return None, None
    try:
        return source.group(1), json.loads(source.group(2))
    except json.JSONDecodeError:
        return source.group(1), None


class State:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.db = sqlite3.connect(run_dir / "state.sqlite3", isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        operation_columns = {
            row[1] for row in self.db.execute("PRAGMA table_info(operations)")
        }
        if "result_compliant" not in operation_columns:
            self.db.execute("ALTER TABLE operations ADD COLUMN result_compliant INTEGER")
        if "validation_json" not in operation_columns:
            self.db.execute("ALTER TABLE operations ADD COLUMN validation_json TEXT")
        if "has_internal_error" not in operation_columns:
            self.db.execute("ALTER TABLE operations ADD COLUMN has_internal_error INTEGER")
        if "internal_errors_json" not in operation_columns:
            self.db.execute("ALTER TABLE operations ADD COLUMN internal_errors_json TEXT")
        if "hydration_id" not in operation_columns:
            self.db.execute("ALTER TABLE operations ADD COLUMN hydration_id TEXT")
        if "hydration_step" not in operation_columns:
            self.db.execute("ALTER TABLE operations ADD COLUMN hydration_step INTEGER")
        page_columns = {row[1] for row in self.db.execute("PRAGMA table_info(pages)")}
        if "fingerprint_score" not in page_columns:
            self.db.execute("ALTER TABLE pages ADD COLUMN fingerprint_score INTEGER")
        if "fingerprint_matches_json" not in page_columns:
            self.db.execute("ALTER TABLE pages ADD COLUMN fingerprint_matches_json TEXT")
        if "expansion_eligible" not in page_columns:
            self.db.execute("ALTER TABLE pages ADD COLUMN expansion_eligible INTEGER")
        capability_columns = {
            row[1] for row in self.db.execute("PRAGMA table_info(capabilities)")
        }
        if "anchor_text" not in capability_columns:
            self.db.execute("ALTER TABLE capabilities ADD COLUMN anchor_text TEXT")
        if "hostname_hint" not in capability_columns:
            self.db.execute("ALTER TABLE capabilities ADD COLUMN hostname_hint TEXT")
        self.db.execute("CREATE TABLE IF NOT EXISTS url_frontier(url TEXT PRIMARY KEY,state TEXT NOT NULL,source_operation_id TEXT,created_at TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS blocked_urls(url TEXT PRIMARY KEY,reason TEXT NOT NULL,source_operation_id TEXT,blocked_at TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS page_refs(agent_id TEXT NOT NULL,ref_id TEXT NOT NULL,page_url TEXT NOT NULL,source_operation_id TEXT,created_at TEXT,PRIMARY KEY(agent_id,ref_id))")
        self.db.execute("CREATE TABLE IF NOT EXISTS edge_frontier(parent_kind TEXT NOT NULL,parent_key TEXT NOT NULL,child_kind TEXT NOT NULL,child_key TEXT NOT NULL,state TEXT NOT NULL,owner_agent_id TEXT,source_operation_id TEXT,created_at TEXT,blocked_at TEXT,PRIMARY KEY(parent_kind,parent_key,child_kind,child_key))")
        self.db.execute("CREATE TABLE IF NOT EXISTS page_routes(agent_id TEXT NOT NULL,ref_id TEXT NOT NULL,page_url TEXT NOT NULL,route_json TEXT NOT NULL,source_operation_id TEXT,created_at TEXT,PRIMARY KEY(agent_id,ref_id))")
        self.db.execute("CREATE TABLE IF NOT EXISTS hydrations(hydration_id TEXT PRIMARY KEY,target_page_url TEXT NOT NULL,route_json TEXT NOT NULL,state TEXT NOT NULL,owner_agent_id TEXT,created_at TEXT,completed_at TEXT,failure_json TEXT)")
        self.log_path = run_dir / "logs" / "orchestrator.jsonl"
        self.hook_log_path = run_dir / "logs" / "hooks.jsonl"
        self.events_path = run_dir / "events.jsonl"
        self.raw_dir = run_dir / "raw" / "hooks"
        self.seq = self.db.execute("SELECT COALESCE(MAX(sequence), 0) FROM events").fetchone()[0]
        self.lock = threading.Lock()

    def close(self) -> None:
        self.db.close()

    def recover_for_serve(self) -> None:
        previous = self.db.execute("SELECT value FROM meta WHERE key='serve_count'").fetchone()
        serve_count = int(previous[0]) if previous else 0
        self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('serve_count',?)",
                        (str(serve_count + 1),))
        if serve_count == 0:
            return
        stale_agents = self.db.execute("SELECT COUNT(*) FROM agents WHERE state='active'").fetchone()[0]
        neutral_requeued = self.db.execute(
            "UPDATE operations SET state='ready',owner_agent_id=NULL,tool_use_id=NULL,leased_at=NULL,executing_at=NULL WHERE state IN ('leased','executing') AND required_agent_id IS NULL"
        ).rowcount
        bound_cancelled = self.db.execute(
            "UPDATE operations SET state='cancelled' WHERE state IN ('ready','leased','executing') AND required_agent_id IS NOT NULL"
        ).rowcount
        self.db.execute("UPDATE agents SET state='stopped',stopped_at=COALESCE(stopped_at,?) WHERE state='active'",
                        (now(),))
        self.db.execute("UPDATE capabilities SET state='inactive' WHERE agent_id IN (SELECT agent_id FROM agents WHERE state='stopped')")
        repaired_frontiers = 0
        stale_frontier_owners = [row[0] for row in self.db.execute(
            "SELECT DISTINCT owner_agent_id FROM edge_frontier WHERE state='queued' AND owner_agent_id IS NOT NULL"
        )]
        for stale_agent_id in stale_frontier_owners:
            repaired_frontiers += self.prepare_rotation_hydrations(stale_agent_id)
        restarted_hydrations = self.restart_hydrations_for_inactive_agents(
            "orchestrator_resume"
        )
        self.event("run_resumed", stale_agents=stale_agents,
                   neutral_operations_requeued=neutral_requeued,
                   agent_bound_operations_cancelled=bound_cancelled,
                   repaired_frontiers=repaired_frontiers,
                   restarted_hydrations=restarted_hydrations,
                   serve_count=serve_count + 1)

    def log(self, level: str, event: str, **details: Any) -> None:
        record = {"schema_version": 1, "time": now(), "level": level,
                  "run_id": self.run_dir.name, "event": event, "details": details}
        with self.log_path.open("a", encoding="utf-8") as out:
            out.write(compact(record) + "\n")

    def event(self, event: str, agent_id: str | None = None,
              operation_id: str | None = None, **payload: Any) -> None:
        self.seq += 1
        created = now()
        record = {"schema_version": 1, "sequence": self.seq, "time": created,
                  "run_id": self.run_dir.name, "event": event,
                  "agent_id": agent_id, "operation_id": operation_id,
                  "payload": payload}
        self.db.execute(
            "INSERT INTO events(sequence,event,agent_id,operation_id,payload_json,created_at) VALUES(?,?,?,?,?,?)",
            (self.seq, event, agent_id, operation_id, compact(payload), created),
        )
        with self.events_path.open("a", encoding="utf-8") as out:
            out.write(compact(record) + "\n")

    def hook_audit(self, request: dict[str, Any], response: dict[str, Any],
                   duration_ms: float) -> None:
        event = request.get("event")
        if event not in {"subagent-start", "pre-tool", "post-tool", "subagent-stop"}:
            return
        payload = request.get("payload", {})
        record = {
            "schema_version": 1, "time": now(), "level": "info",
            "run_id": self.run_dir.name, "event": "hook_completed",
            "hook_event": event, "duration_ms": round(duration_ms, 3),
            "session_id": payload.get("session_id"), "turn_id": payload.get("turn_id"),
            "agent_id": payload.get("agent_id"), "agent_type": payload.get("agent_type"),
            "tool_name": payload.get("tool_name"), "tool_use_id": payload.get("tool_use_id"),
            "input_hash": digest(payload.get("tool_input")) if "tool_input" in payload else None,
            "decision": response.get("action", "context" if "context" in response else "allow"),
        }
        with self.hook_log_path.open("a", encoding="utf-8") as out:
            out.write(compact(record) + "\n")

    def assignment_text(self, row: sqlite3.Row | None) -> str:
        if row is None:
            return "SPIDER QUEUE EMPTY. Call no more tools. Return a short completion message and stop."
        return (f"SPIDER ASSIGNMENT {row['operation_id']}\n"
                "Call `webrun` exactly once with this JSON object and no changes:\n"
                f"{row['tool_input_json']}\nDo not call any other tool.")

    def page_limit_hit(self) -> bool:
        limit_value = int(self.db.execute("SELECT value FROM meta WHERE key='max_pages'").fetchone()[0])
        return self.db.execute("SELECT COUNT(*) FROM pages").fetchone()[0] >= limit_value

    def run_aborted(self) -> bool:
        return self.db.execute("SELECT 1 FROM meta WHERE key='aborted_at'").fetchone() is not None

    def abort_run(self, agent_id: str, operation_id: str, reason: str, **details: Any) -> None:
        if self.run_aborted():
            return
        timestamp = now()
        self.db.execute("INSERT INTO meta(key,value) VALUES('aborted_at',?)", (timestamp,))
        self.db.execute("INSERT INTO meta(key,value) VALUES('abort_reason',?)", (reason,))
        self.db.execute("INSERT INTO meta(key,value) VALUES('abort_details_json',?)",
                        (compact(details),))
        self.event("run_aborted", agent_id, operation_id, reason=reason, **details)

    def abort_context(self) -> str:
        reason = (self.db.execute(
            "SELECT value FROM meta WHERE key='abort_reason'"
        ).fetchone() or ["unknown"])[0]
        details = (self.db.execute(
            "SELECT value FROM meta WHERE key='abort_details_json'"
        ).fetchone() or ["{}"])[0]
        return ("SPIDER RUN ABORTED by result-validation policy. Call no more tools and stop.\n"
                f"Reason: {reason}\nErrors: {details}")

    def claim_edge(self, parent_kind: str, parent_key: str, child_kind: str,
                   child_key: str, agent_id: str, operation_id: str) -> bool:
        return bool(self.db.execute(
            "INSERT OR IGNORE INTO edge_frontier(parent_kind,parent_key,child_kind,child_key,state,owner_agent_id,source_operation_id,created_at) VALUES(?,?,?,?,'queued',?,?,?)",
            (parent_kind, parent_key, child_kind, child_key, agent_id,
             operation_id, now()),
        ).rowcount)

    def enrich_internal_errors(self, agent_id: str, row: sqlite3.Row,
                               text: str) -> list[dict[str, Any]]:
        enriched: list[dict[str, Any]] = []
        for detail in internal_error_sources(text):
            requested = detail.get("requested_input")
            kind = detail.get("tool_kind")
            record: dict[str, Any] = {
                "error": "Internal Error",
                "classification": detail.get("classification", "internal_error"),
                "failed_url": detail.get("failed_url"),
                "operation_id": row["operation_id"],
                "tool_kind": kind,
                "requested_input": requested,
                "source": detail.get("source"),
            }
            if kind == "open" and isinstance(requested, dict):
                ref_id = requested.get("ref_id")
                requested_url = (clean_url(ref_id) if isinstance(ref_id, str) and
                                 ref_id.startswith(("http://", "https://")) else None)
                record.update({"requested_url": requested_url,
                               "destination_url_known": requested_url is not None})
                if requested_url is None and isinstance(ref_id, str):
                    parent = self.db.execute(
                        "SELECT kind,tool_input_json FROM operations WHERE operation_id=?",
                        (row["parent_operation_id"],),
                    ).fetchone()
                    if parent is not None:
                        record.update({"parent_kind": parent["kind"],
                                       "parent_key": parent["tool_input_json"],
                                       "child_ref": ref_id})
                        if parent["kind"] == "search":
                            record["ref_chain"] = [
                                {"kind": "search",
                                 "tool_input": json.loads(parent["tool_input_json"])},
                                {"kind": "open", "ref_id": ref_id,
                                 "status": "failed"},
                            ]
            elif kind == "click" and isinstance(requested, dict):
                parent_ref_id = requested.get("ref_id")
                link_id = requested.get("id")
                parent = self.db.execute(
                    "SELECT page_url FROM page_refs WHERE agent_id=? AND ref_id=? LIMIT 1",
                    (agent_id, parent_ref_id),
                ).fetchone()
                capability = self.db.execute(
                    "SELECT anchor_text,hostname_hint FROM capabilities WHERE agent_id=? AND parent_ref_id=? AND link_id=? ORDER BY rowid DESC LIMIT 1",
                    (agent_id, parent_ref_id, link_id),
                ).fetchone()
                record.update({
                    "requested_url": None,
                    "destination_url_known": False,
                    "parent_url": parent[0] if parent else None,
                    "parent_ref_id": parent_ref_id,
                    "link_id": link_id,
                    "anchor_text": capability[0] if capability else None,
                    "hostname_hint": capability[1] if capability else None,
                })
                if parent:
                    record.update({"parent_kind": "page",
                                   "parent_key": parent[0],
                                   "child_ref": str(link_id)})
                    route_row = self.db.execute(
                        "SELECT route_json FROM page_routes WHERE agent_id=? AND ref_id=?",
                        (agent_id, parent_ref_id),
                    ).fetchone()
                    if route_row is not None:
                        route = json.loads(route_row[0])
                        chain = [{"kind": "search",
                                  "tool_input": route["root_search_input"]}]
                        for hop in route.get("hops", []):
                            chain_hop = {
                                "kind": hop["kind"],
                                "expected_url": hop.get("expected_url"),
                                "status": "succeeded",
                            }
                            if hop["kind"] == "open":
                                chain_hop["ref_id"] = hop.get("actual_ref_id",
                                                               hop.get("old_ref_id"))
                            else:
                                chain_hop["parent_ref_id"] = hop.get("parent_ref_id")
                                chain_hop["link_id"] = hop.get("link_id")
                            chain.append(chain_hop)
                        chain.append({"kind": "click",
                                      "parent_ref_id": parent_ref_id,
                                      "link_id": link_id,
                                      "status": "failed"})
                        record["ref_chain"] = chain
            else:
                record.update({"requested_url": None,
                               "destination_url_known": False})
            if detail.get("failed_url"):
                record.update({"requested_url": detail["failed_url"],
                               "destination_url_known": True})
            enriched.append(record)
        return enriched

    def block_failed_edges(self, errors: list[dict[str, Any]]) -> None:
        for error in errors:
            parent_kind = error.get("parent_kind")
            parent_key = error.get("parent_key")
            child_ref = error.get("child_ref")
            child_kind = error.get("tool_kind")
            if not all(isinstance(value, str) for value in
                       (parent_kind, parent_key, child_ref, child_kind)):
                continue
            self.db.execute(
                "UPDATE edge_frontier SET state='blocked',blocked_at=? WHERE parent_kind=? AND parent_key=? AND child_kind=? AND child_key=?",
                (now(), parent_kind, parent_key, child_kind, child_ref),
            )
            self.event("edge_blocked", operation_id=error.get("operation_id"),
                       parent_kind=parent_kind, parent_key=parent_key,
                       child_kind=child_kind, child_key=child_ref,
                       reason="internal_error")

    def agent_call_limit_hit(self, agent_id: str) -> bool:
        row = self.db.execute(
            "SELECT value FROM meta WHERE key='max_calls_per_agent'"
        ).fetchone()
        if row is None or int(row[0]) <= 0:
            return False
        committed = self.db.execute(
            "SELECT COUNT(*) FROM operations WHERE owner_agent_id=? AND state='committed'",
            (agent_id,),
        ).fetchone()[0]
        return committed >= int(row[0])

    def lease(self, agent_id: str) -> sqlite3.Row | None:
        current = self.db.execute(
            "SELECT * FROM operations WHERE owner_agent_id=? AND state IN ('leased','executing') ORDER BY sequence LIMIT 1",
            (agent_id,),
        ).fetchone()
        if current:
            return current
        if self.page_limit_hit() or self.run_aborted():
            return None
        if self.agent_call_limit_hit(agent_id):
            # The call limit is a rotation boundary, not permission to discard
            # ephemeral WebRun refs. Drain already-created agent-affine work,
            # but do not admit any new neutral operation into this thread.
            row = self.db.execute(
                "SELECT * FROM operations WHERE state='ready' AND required_agent_id=? ORDER BY sequence LIMIT 1",
                (agent_id,),
            ).fetchone()
            if row is None:
                return None
            self.db.execute(
                "UPDATE operations SET state='leased',owner_agent_id=?,leased_at=? WHERE operation_id=? AND state='ready'",
                (agent_id, now(), row["operation_id"]),
            )
            self.event("operation_leased_past_rotation_limit", agent_id,
                       row["operation_id"], input_hash=row["input_hash"])
            return self.db.execute(
                "SELECT * FROM operations WHERE operation_id=?", (row["operation_id"],)
            ).fetchone()
        owns_search_root = self.db.execute(
            "SELECT 1 FROM operations WHERE owner_agent_id=? AND kind='search' LIMIT 1",
            (agent_id,),
        ).fetchone() is not None
        if owns_search_root:
            # Neutral search roots seed independent ephemeral capability trees.
            # Once a worker owns one, reserve the remaining roots for workers
            # that have not yet established a tree.
            row = self.db.execute(
                "SELECT * FROM operations WHERE state='ready' AND (required_agent_id=? OR (required_agent_id IS NULL AND kind!='search')) ORDER BY CASE WHEN required_agent_id=? THEN 0 WHEN required_agent_id IS NULL AND kind='open' THEN 1 ELSE 2 END,sequence LIMIT 1",
                (agent_id, agent_id),
            ).fetchone()
        else:
            row = self.db.execute(
                "SELECT * FROM operations WHERE state='ready' AND (required_agent_id IS NULL OR required_agent_id=?) ORDER BY sequence LIMIT 1",
                (agent_id,),
            ).fetchone()
        if row is None:
            return None
        self.db.execute(
            "UPDATE operations SET state='leased',owner_agent_id=?,leased_at=? WHERE operation_id=? AND state='ready'",
            (agent_id, now(), row["operation_id"]),
        )
        self.event("operation_leased", agent_id, row["operation_id"], input_hash=row["input_hash"])
        return self.db.execute("SELECT * FROM operations WHERE operation_id=?", (row["operation_id"],)).fetchone()

    def add_operation(self, kind: str, tool_input: dict[str, Any], required_agent: str | None,
                      parent: str | None, unique_salt: str | None = None) -> str | None:
        if self.page_limit_hit() or self.run_aborted():
            return None
        input_hash = digest(tool_input)
        unique_key = digest({"kind": kind, "agent": required_agent, "input": tool_input,
                             "unique_salt": unique_salt})
        sequence = self.db.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM operations").fetchone()[0]
        operation_id = f"op_{sequence:08d}"
        changed = self.db.execute(
            "INSERT OR IGNORE INTO operations(operation_id,sequence,kind,state,required_agent_id,tool_input_json,input_hash,unique_key,parent_operation_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (operation_id, sequence, kind, "ready", required_agent, compact(tool_input),
             input_hash, unique_key, parent, now()),
        ).rowcount
        if changed:
            self.event("operation_created", required_agent, operation_id, kind=kind,
                       parent_operation_id=parent, input_hash=input_hash)
            return operation_id
        return None

    def add_batched_operations(self, kind: str, items: list[dict[str, Any]],
                               required_agent: str | None, parent: str | None,
                               unique_salt: str | None = None) -> None:
        field = {"search": "search_query", "open": "open", "click": "click"}[kind]
        batch_limit_row = self.db.execute(
            "SELECT value FROM meta WHERE key='max_operations_per_webrun_call'"
        ).fetchone()
        batch_limit = int(batch_limit_row[0]) if batch_limit_row else 10
        unique_items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in items:
            if kind == "open" and isinstance(item.get("ref_id"), str) and item["ref_id"].startswith(("http://", "https://")):
                cleaned = clean_url(item["ref_id"])
                if cleaned is None:
                    continue
                item = {**item, "ref_id": cleaned}
                if self.db.execute("SELECT 1 FROM blocked_urls WHERE url=?", (cleaned,)).fetchone():
                    continue
                inserted = self.db.execute(
                    "INSERT OR IGNORE INTO url_frontier(url,state,source_operation_id,created_at) VALUES(?,'queued',?,?)",
                    (cleaned, parent, now()),
                ).rowcount
                if not inserted:
                    continue
            key = compact(item)
            if key not in seen:
                seen.add(key)
                unique_items.append(item)
        for offset in range(0, len(unique_items), batch_limit):
            salt = f"{unique_salt}:{offset // batch_limit}" if unique_salt is not None else None
            self.add_operation(kind, {field: unique_items[offset:offset + batch_limit],
                                      "response_length": "long"}, required_agent, parent, salt)

    def add_hydration_operation(self, kind: str, tool_input: dict[str, Any],
                                required_agent: str | None, parent: str | None,
                                hydration_id: str, step: int,
                                attempt: str | None = None) -> str | None:
        operation_id = self.add_operation(
            kind, tool_input, required_agent, parent,
            f"hydration:{hydration_id}:step:{step}:attempt:{attempt or 'initial'}"
        )
        if operation_id:
            self.db.execute(
                "UPDATE operations SET hydration_id=?,hydration_step=? WHERE operation_id=?",
                (hydration_id, step, operation_id),
            )
        return operation_id

    def restart_hydration(self, hydration: sqlite3.Row, reason: str) -> bool:
        route = json.loads(hydration["route_json"])
        attempt = str(self.db.execute(
            "SELECT COUNT(*)+1 FROM operations WHERE hydration_id=? AND hydration_step=0",
            (hydration["hydration_id"],),
        ).fetchone()[0])
        operation_id = self.add_hydration_operation(
            "search", route["root_search_input"], None, None,
            hydration["hydration_id"], 0, attempt,
        )
        if operation_id is None:
            return False
        self.db.execute(
            "UPDATE hydrations SET state='ready',owner_agent_id=NULL,failure_json=NULL WHERE hydration_id=?",
            (hydration["hydration_id"],),
        )
        self.event("hydration_restarted", operation_id=operation_id,
                   hydration_id=hydration["hydration_id"], reason=reason,
                   attempt=int(attempt))
        return True

    def restart_hydrations_for_inactive_agents(self, reason: str,
                                                agent_id: str | None = None) -> int:
        if agent_id is None:
            rows = list(self.db.execute(
                "SELECT h.* FROM hydrations h LEFT JOIN agents a ON a.agent_id=h.owner_agent_id WHERE h.state='running' AND (a.agent_id IS NULL OR a.state!='active')"
            ))
        else:
            rows = list(self.db.execute(
                "SELECT * FROM hydrations WHERE state='running' AND owner_agent_id=?",
                (agent_id,),
            ))
        return sum(self.restart_hydration(row, reason) for row in rows)

    def record_page_route(self, row: sqlite3.Row, agent_id: str, page_ref: str,
                          destination: str, section: str) -> None:
        source_kind, source_input = section_source(section)
        if source_input is None:
            return
        route: dict[str, Any] | None = None
        if source_kind == "open":
            source_ref = source_input.get("ref_id")
            if isinstance(source_ref, str) and not source_ref.startswith(("http://", "https://")):
                parent = self.db.execute(
                    "SELECT kind,tool_input_json FROM operations WHERE operation_id=?",
                    (row["parent_operation_id"],),
                ).fetchone()
                if parent is not None and parent["kind"] == "search":
                    route = {"root_search_input": json.loads(parent["tool_input_json"]),
                             "hops": [{"kind": "open", "expected_url": destination,
                                       "old_ref_id": source_ref}]}
        elif source_kind == "click":
            parent_ref = source_input.get("ref_id")
            link_id = source_input.get("id")
            parent_route = self.db.execute(
                "SELECT route_json FROM page_routes WHERE agent_id=? AND ref_id=?",
                (agent_id, parent_ref),
            ).fetchone()
            if parent_route is not None:
                route = json.loads(parent_route[0])
                capability = self.db.execute(
                    "SELECT anchor_text,hostname_hint FROM capabilities WHERE agent_id=? AND parent_ref_id=? AND link_id=? LIMIT 1",
                    (agent_id, parent_ref, link_id),
                ).fetchone()
                route["hops"].append({
                    "kind": "click", "link_id": link_id,
                    "parent_ref_id": parent_ref,
                    "anchor_text": capability[0] if capability else None,
                    "hostname_hint": capability[1] if capability else None,
                    "expected_url": destination,
                })
        if route is not None:
            self.db.execute(
                "INSERT OR REPLACE INTO page_routes(agent_id,ref_id,page_url,route_json,source_operation_id,created_at) VALUES(?,?,?,?,?,?)",
                (agent_id, page_ref, destination, compact(route),
                 row["operation_id"], now()),
            )

    def prepare_rotation_hydrations(self, agent_id: str) -> int:
        pages = [row[0] for row in self.db.execute(
            "SELECT DISTINCT parent_key FROM edge_frontier WHERE state='queued' AND owner_agent_id=? AND parent_kind='page'",
            (agent_id,),
        )]
        prepared = 0
        for page_url in pages:
            if self.db.execute(
                "SELECT 1 FROM hydrations WHERE target_page_url=? AND state IN ('ready','running')",
                (page_url,),
            ).fetchone():
                continue
            route_row = self.db.execute(
                "SELECT route_json FROM page_routes WHERE agent_id=? AND page_url=? ORDER BY created_at DESC LIMIT 1",
                (agent_id, page_url),
            ).fetchone()
            if route_row is None:
                continue
            hydration_id = f"hydrate_{self.db.execute('SELECT COALESCE(MAX(rowid),0)+1 FROM hydrations').fetchone()[0]:08d}"
            route = json.loads(route_row[0])
            self.db.execute(
                "INSERT INTO hydrations(hydration_id,target_page_url,route_json,state,created_at) VALUES(?,?,?,'ready',?)",
                (hydration_id, page_url, compact(route), now()),
            )
            operation_id = self.add_hydration_operation(
                "search", route["root_search_input"], None, None, hydration_id, 0
            )
            if operation_id is None:
                self.db.execute("DELETE FROM hydrations WHERE hydration_id=?", (hydration_id,))
                continue
            prepared += 1
            self.event("hydration_created", agent_id, operation_id,
                       hydration_id=hydration_id, target_page_url=page_url,
                       hop_count=len(route["hops"]))
        if prepared:
            # Cancel only click batches whose parent page now has a queued replay
            # recipe. Any other ephemeral-ref work must be drained by this worker.
            hydrated_pages = {
                row[0] for row in self.db.execute(
                    "SELECT target_page_url FROM hydrations WHERE state IN ('ready','running')"
                )
            }
            for operation in self.db.execute(
                "SELECT operation_id,tool_input_json FROM operations WHERE required_agent_id=? AND state='ready' AND kind='click'",
                (agent_id,),
            ):
                tool_input = json.loads(operation["tool_input_json"])
                parent_pages = set()
                fully_resolved = True
                for item in tool_input.get("click", []):
                    page = self.db.execute(
                        "SELECT page_url FROM page_refs WHERE agent_id=? AND ref_id=?",
                        (agent_id, item.get("ref_id")),
                    ).fetchone()
                    if page is None:
                        fully_resolved = False
                        break
                    parent_pages.add(page[0])
                if fully_resolved and parent_pages and parent_pages <= hydrated_pages:
                    self.db.execute(
                        "UPDATE operations SET state='cancelled' WHERE operation_id=?",
                        (operation["operation_id"],),
                    )
        return prepared

    def fail_hydration(self, hydration_id: str, agent_id: str,
                       operation_id: str, reason: str, **details: Any) -> None:
        failure = {"reason": reason, **details}
        self.db.execute(
            "UPDATE hydrations SET state='failed',owner_agent_id=?,failure_json=? WHERE hydration_id=?",
            (agent_id, compact(failure), hydration_id),
        )
        self.db.execute(
            "UPDATE edge_frontier SET state='stale' WHERE parent_kind='page' AND parent_key=(SELECT target_page_url FROM hydrations WHERE hydration_id=?) AND state='queued'",
            (hydration_id,),
        )
        self.event("hydration_failed", agent_id, operation_id,
                   hydration_id=hydration_id, **failure)

    def parse_hydration_result(self, row: sqlite3.Row, agent_id: str,
                               text: str) -> None:
        hydration = self.db.execute(
            "SELECT * FROM hydrations WHERE hydration_id=?", (row["hydration_id"],)
        ).fetchone()
        if hydration is None:
            return
        route = json.loads(hydration["route_json"])
        hops = route["hops"]
        step = int(row["hydration_step"])
        self.db.execute(
            "UPDATE hydrations SET state='running',owner_agent_id=? WHERE hydration_id=?",
            (agent_id, hydration["hydration_id"]),
        )
        if step == 0:
            expected_url = hops[0]["expected_url"]
            for section in result_sections(text):
                if FETCH_FAILURE_RE.search(section) or section.lstrip().startswith("Internal Error"):
                    continue
                urls = [clean_url(url) for url in URL_RE.findall(section)]
                if expected_url not in urls:
                    continue
                ref_id = next((ref for ref in REF_RE.findall(section)
                               if "search" in ref), None)
                if ref_id:
                    self.add_hydration_operation(
                        "open", {"open": [{"ref_id": ref_id}],
                                 "response_length": "long"},
                        agent_id, row["operation_id"], hydration["hydration_id"], 1
                    )
                    self.event("hydration_hop_scheduled", agent_id,
                               row["operation_id"], hydration_id=hydration["hydration_id"],
                               step=1, expected_url=expected_url)
                    return
            self.fail_hydration(hydration["hydration_id"], agent_id,
                                row["operation_id"], "search_result_not_recreated",
                                expected_url=expected_url)
            return

        hop_index = step - 1
        expected_url = hops[hop_index]["expected_url"]
        matched_section: str | None = None
        for section in result_sections(text):
            if FETCH_FAILURE_RE.search(section) or section.lstrip().startswith("Internal Error"):
                continue
            urls = [clean_url(url) for url in URL_RE.findall(section)]
            if expected_url in urls:
                matched_section = section
                break
        if matched_section is None:
            self.fail_hydration(hydration["hydration_id"], agent_id,
                                row["operation_id"], "hop_identity_mismatch",
                                step=step, expected_url=expected_url)
            return
        page_ref = next((ref for ref in REF_RE.findall(matched_section)
                         if "view" in ref), None)
        if page_ref is None:
            self.fail_hydration(hydration["hydration_id"], agent_id,
                                row["operation_id"], "replayed_page_ref_missing",
                                step=step, expected_url=expected_url)
            return
        self.db.execute(
            "INSERT OR REPLACE INTO page_refs(agent_id,ref_id,page_url,source_operation_id,created_at) VALUES(?,?,?,?,?)",
            (agent_id, page_ref, expected_url, row["operation_id"], now()),
        )
        materialized_route = json.loads(compact(route))
        operation_input = json.loads(row["tool_input_json"])
        if hops[hop_index]["kind"] == "open":
            inputs = operation_input.get("open", [])
            if inputs:
                materialized_route["hops"][hop_index]["actual_ref_id"] = inputs[0].get("ref_id")
        else:
            inputs = operation_input.get("click", [])
            if inputs:
                materialized_route["hops"][hop_index]["parent_ref_id"] = inputs[0].get("ref_id")
        self.db.execute(
            "UPDATE hydrations SET route_json=? WHERE hydration_id=?",
            (compact(materialized_route), hydration["hydration_id"]),
        )
        self.db.execute(
            "INSERT OR REPLACE INTO page_routes(agent_id,ref_id,page_url,route_json,source_operation_id,created_at) VALUES(?,?,?,?,?,?)",
            (agent_id, page_ref, expected_url, compact(materialized_route),
             row["operation_id"], now()),
        )
        details = {int(link_id): (anchor.strip() or None, hint.strip() or None)
                   for link_id, anchor, hint in LINK_DETAIL_RE.findall(matched_section)}
        if hop_index + 1 < len(hops):
            next_hop = hops[hop_index + 1]
            wanted_id = int(next_hop["link_id"])
            candidate_id = wanted_id if wanted_id in details else None
            if next_hop.get("anchor_text"):
                matching = [link_id for link_id, values in details.items()
                            if values[0] == next_hop["anchor_text"] and
                            (not next_hop.get("hostname_hint") or
                             values[1] == next_hop["hostname_hint"])]
                if matching:
                    candidate_id = matching[0]
            if candidate_id is None:
                self.fail_hydration(hydration["hydration_id"], agent_id,
                                    row["operation_id"], "replay_link_not_found",
                                    step=step + 1, anchor_text=next_hop.get("anchor_text"),
                                    hostname_hint=next_hop.get("hostname_hint"))
                return
            self.add_hydration_operation(
                "click", {"click": [{"ref_id": page_ref, "id": candidate_id}],
                          "response_length": "long"},
                agent_id, row["operation_id"], hydration["hydration_id"], step + 1
            )
            return

        pending = list(self.db.execute(
            "SELECT child_key FROM edge_frontier WHERE parent_kind='page' AND parent_key=? AND child_kind='click' AND state='queued'",
            (hydration["target_page_url"],),
        ))
        click_items = [{"ref_id": page_ref, "id": int(edge[0])} for edge in pending]
        self.db.execute(
            "UPDATE edge_frontier SET owner_agent_id=? WHERE parent_kind='page' AND parent_key=? AND child_kind='click' AND state='queued'",
            (agent_id, hydration["target_page_url"]),
        )
        for item in click_items:
            anchor_text, hostname_hint = details.get(item["id"], (None, None))
            self.db.execute(
                "INSERT OR IGNORE INTO capabilities(agent_id,kind,ref_id,parent_ref_id,link_id,state,source_operation_id,cached_at,anchor_text,hostname_hint) VALUES(?,?,?,?,?,'active',?,?,?,?)",
                (agent_id, "click", None, page_ref, item["id"],
                 row["operation_id"], None, anchor_text, hostname_hint),
            )
        self.add_batched_operations("click", click_items, agent_id,
                                    row["operation_id"],
                                    f"hydrated:{hydration['hydration_id']}")
        self.db.execute(
            "UPDATE hydrations SET state='completed',completed_at=? WHERE hydration_id=?",
            (now(), hydration["hydration_id"]),
        )
        self.event("hydration_completed", agent_id, row["operation_id"],
                   hydration_id=hydration["hydration_id"],
                   restored_edge_count=len(click_items))

    def handle_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        agent_id = payload.get("agent_id")
        if not agent_id:
            return {"context": "SPIDER REGISTRATION FAILED. Call no tools and stop."}
        self.db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('crawl_started_at',?)", (now(),))
        self.db.execute(
            "INSERT INTO agents(agent_id,agent_type,session_id,state,stop_attempts,started_at,last_seen_at) VALUES(?,?,?,?,0,?,?) ON CONFLICT(agent_id) DO UPDATE SET state='active',last_seen_at=excluded.last_seen_at",
            (agent_id, payload.get("agent_type"), payload.get("session_id"), "active", now(), now()),
        )
        self.event("agent_started", agent_id, agent_type=payload.get("agent_type"))
        return {"context": self.assignment_text(self.lease(agent_id))}

    def handle_pre(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("agent_type") != "spider_agent":
            return {"action": "ignore"}
        agent_id = payload.get("agent_id")
        if not agent_id:
            return {"action": "deny", "reason": "Spider policy: missing agent identity."}
        row = self.db.execute(
            "SELECT * FROM operations WHERE owner_agent_id=? AND state='leased' ORDER BY sequence LIMIT 1",
            (agent_id,),
        ).fetchone()
        if (row is None or payload.get("tool_name") != "webrun" or
                digest(payload.get("tool_input")) != row["input_hash"]):
            self.event("tool_denied", agent_id, row["operation_id"] if row else None,
                       tool_name=payload.get("tool_name"), reason="lease_mismatch")
            return {"action": "deny", "reason": "Spider policy: call does not match the agent's active lease."}
        tool_use_id = payload.get("tool_use_id")
        if not tool_use_id:
            return {"action": "deny", "reason": "Spider policy: missing tool-use identity."}
        self.db.execute(
            "UPDATE operations SET state='executing',tool_use_id=?,executing_at=? WHERE operation_id=?",
            (tool_use_id, now(), row["operation_id"]),
        )
        self.event("tool_authorized", agent_id, row["operation_id"], tool_use_id=tool_use_id)
        return {"action": "allow"}

    def store_raw(self, operation_id: str, payload: dict[str, Any]) -> tuple[Path, str]:
        tool_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(payload.get("tool_use_id", "unknown")))
        path = self.raw_dir / f"{operation_id}__{tool_id}.json"
        encoded = (compact(payload) + "\n").encode()
        with path.open("xb") as out:
            out.write(encoded)
            out.flush()
            os.fsync(out.fileno())
        return path, hashlib.sha256(encoded).hexdigest()

    def parse_result(self, row: sqlite3.Row, agent_id: str, text: str) -> None:
        kind = row["kind"]
        operation_id = row["operation_id"]
        if row["hydration_id"]:
            self.parse_hydration_result(row, agent_id, text)
            return
        sections = result_sections(text)
        if kind == "search":
            search_only = self.db.execute(
                "SELECT value FROM meta WHERE key='search_only'"
            ).fetchone()
            if search_only is not None and search_only[0] == "1":
                return
            ref_open_items: list[dict[str, Any]] = []
            direct_open_items: list[dict[str, Any]] = []
            direct_url_mode = self.db.execute(
                "SELECT value FROM meta WHERE key='direct_url_opens'"
            ).fetchone()
            use_direct_urls = direct_url_mode is not None and direct_url_mode[0] == "1"
            for section_index, section in enumerate(sections):
                if FETCH_FAILURE_RE.search(section) or section.lstrip().startswith("Internal Error"):
                    continue
                cached_match = CACHED_RE.search(section)
                cached_at = cached_match.group(1).strip() if cached_match else None
                refs = list(dict.fromkeys(REF_RE.findall(section)))
                for ref in refs:
                    if not any(token in ref for token in ("search", "academia", "news", "reddit")):
                        continue
                    if not self.claim_edge("search", row["tool_input_json"], "open",
                                           ref, agent_id, operation_id):
                        continue
                    self.db.execute(
                        "INSERT OR IGNORE INTO capabilities(agent_id,kind,ref_id,parent_ref_id,link_id,state,source_operation_id,cached_at) VALUES(?,?,?,?,?,'active',?,?)",
                        (agent_id, "open", ref, None, None, operation_id, cached_at),
                    )
                    ref_open_items.append({"ref_id": ref})
                if use_direct_urls:
                    urls = list(dict.fromkeys(URL_RE.findall(section)))
                    if urls:
                        cleaned = clean_url(urls[0])
                        if cleaned:
                            direct_open_items.append({"ref_id": cleaned})
            # Search-result refs preserve the exact cached traversal route and
            # remain agent-affine. Visible URLs are supplemental durable paths.
            self.add_batched_operations("open", ref_open_items, agent_id, operation_id,
                                        "search-ref-chain")
            if use_direct_urls:
                self.add_batched_operations("open", direct_open_items, None,
                                            operation_id, "search-direct-fallback")
        else:
            click_items: list[dict[str, Any]] = []
            durable_open_items: list[dict[str, Any]] = []
            direct_url_mode = self.db.execute(
                "SELECT value FROM meta WHERE key='direct_url_opens'"
            ).fetchone()
            use_direct_urls = direct_url_mode is not None and direct_url_mode[0] == "1"
            for section_index, section in enumerate(sections):
                if self.page_limit_hit():
                    break
                if FETCH_FAILURE_RE.search(section) or section.lstrip().startswith("Internal Error"):
                    continue
                refs = list(dict.fromkeys(REF_RE.findall(section)))
                urls = list(dict.fromkeys(URL_RE.findall(section)))
                page_ref = next((ref for ref in refs if "view" in ref), None)
                destination = clean_url(urls[0]) if urls else None
                cached_match = CACHED_RE.search(section)
                cached_at = cached_match.group(1).strip() if cached_match else None
                if not destination:
                    continue
                source_kind, source_input = section_source(section)
                if source_kind == "open" and isinstance(source_input, dict):
                    source_ref = source_input.get("ref_id")
                    if isinstance(source_ref, str) and not source_ref.startswith(("http://", "https://")):
                        parent = self.db.execute(
                            "SELECT kind,tool_input_json FROM operations WHERE operation_id=?",
                            (row["parent_operation_id"],),
                        ).fetchone()
                        if parent is not None:
                            self.db.execute(
                                "UPDATE edge_frontier SET state='completed' WHERE parent_kind=? AND parent_key=? AND child_kind='open' AND child_key=?",
                                (parent["kind"], parent["tool_input_json"], source_ref),
                            )
                elif source_kind == "click" and isinstance(source_input, dict):
                    parent_ref = source_input.get("ref_id")
                    link_id = source_input.get("id")
                    parent_page = self.db.execute(
                        "SELECT page_url FROM page_refs WHERE agent_id=? AND ref_id=?",
                        (agent_id, parent_ref),
                    ).fetchone()
                    if parent_page is not None:
                        self.db.execute(
                            "UPDATE edge_frontier SET state='completed' WHERE parent_kind='page' AND parent_key=? AND child_kind='click' AND child_key=?",
                            (parent_page[0], str(link_id)),
                        )
                fingerprint_score, fingerprint_matches = fingerprint_page(section)
                expansion_eligible = fingerprint_score >= FINGERPRINT_THRESHOLD
                outbound_suppressed = suppress_outbound_links(destination)
                if use_direct_urls and expansion_eligible and not outbound_suppressed:
                    for url in urls[1:]:
                        cleaned_url = clean_url(url)
                        if cleaned_url and cleaned_url != destination:
                            durable_open_items.append({"ref_id": cleaned_url})
                self.db.execute(
                    "INSERT INTO pages(page_url,agent_id,ref_id,source_operation_id,collected_at,cached_at,fingerprint_score,fingerprint_matches_json,expansion_eligible) VALUES(?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(page_url) DO UPDATE SET fingerprint_score=MAX(COALESCE(pages.fingerprint_score,0),excluded.fingerprint_score),fingerprint_matches_json=CASE WHEN excluded.fingerprint_score>COALESCE(pages.fingerprint_score,0) THEN excluded.fingerprint_matches_json ELSE pages.fingerprint_matches_json END,expansion_eligible=MAX(COALESCE(pages.expansion_eligible,0),excluded.expansion_eligible)",
                    (destination, agent_id, page_ref, operation_id, now(), cached_at,
                     fingerprint_score, compact(fingerprint_matches),
                     1 if expansion_eligible else 0),
                )
                if page_ref:
                    self.db.execute(
                        "INSERT OR REPLACE INTO page_refs(agent_id,ref_id,page_url,source_operation_id,created_at) VALUES(?,?,?,?,?)",
                        (agent_id, page_ref, destination, operation_id, now()),
                    )
                    self.record_page_route(row, agent_id, page_ref, destination, section)
                self.event("page_fingerprint_scored", agent_id, operation_id,
                           page_url=destination, section_index=section_index,
                           fingerprint_score=fingerprint_score,
                           threshold=FINGERPRINT_THRESHOLD,
                           expansion_eligible=expansion_eligible,
                           outbound_suppressed=outbound_suppressed,
                           matches=fingerprint_matches)
                if not expansion_eligible or outbound_suppressed:
                    continue
                if not page_ref:
                    continue
                self.db.execute(
                    "INSERT OR IGNORE INTO capabilities(agent_id,kind,ref_id,parent_ref_id,link_id,state,source_operation_id,cached_at) VALUES(?,?,?,?,?,'active',?,?)",
                    (agent_id, "open", page_ref, None, None, operation_id, cached_at),
                )
                link_details = {
                    int(link_id): (anchor.strip() or None, hint.strip() or None)
                    for link_id, anchor, hint in LINK_DETAIL_RE.findall(section)
                }
                all_link_ids = list(dict.fromkeys(
                    int(value) for value in LINK_RE.findall(section)
                ))
                complete_details = {
                    link_id: link_details.get(link_id, (None, None))
                    for link_id in all_link_ids
                }
                selected_link_ids, rejected_links = select_click_links(
                    complete_details, fingerprint_score
                )
                self.event("page_links_selected", agent_id, operation_id,
                           page_url=destination,
                           discovered_count=len(all_link_ids),
                           selected_count=len(selected_link_ids),
                           rejected_count=len(all_link_ids) - len(selected_link_ids),
                           rejected_reasons=rejected_links,
                           per_parent_limit=25 if fingerprint_score >= 7 else 10)
                for link_id in selected_link_ids:
                    if not self.claim_edge("page", destination, "click", str(link_id),
                                           agent_id, operation_id):
                        continue
                    anchor_text, hostname_hint = link_details.get(link_id, (None, None))
                    self.db.execute(
                        "INSERT OR IGNORE INTO capabilities(agent_id,kind,ref_id,parent_ref_id,link_id,state,source_operation_id,cached_at,anchor_text,hostname_hint) VALUES(?,?,?,?,?,'active',?,?,?,?)",
                        (agent_id, "click", None, page_ref, link_id, operation_id,
                         cached_at, anchor_text, hostname_hint),
                    )
                    click_items.append({"ref_id": page_ref, "id": link_id})
            if use_direct_urls:
                self.add_batched_operations("open", durable_open_items, None, operation_id)
            self.add_batched_operations("click", click_items, agent_id, operation_id)

    def validate_result(self, row: sqlite3.Row, text: str) -> tuple[bool, bool, list[dict[str, Any]]]:
        sections = result_sections(text)
        unknown: list[dict[str, Any]] = []
        has_internal_error = False
        if not sections:
            return False, False, [{"section": 0, "reason": "empty_result", "prefix": ""}]
        for index, section in enumerate(sections):
            if (section.lstrip().startswith("Internal Error") and
                    not FETCH_FAILURE_RE.search(section)):
                has_internal_error = True
            if CACHED_RE.search(section):
                continue
            if FETCH_FAILURE_RE.search(section):
                continue
            if row["kind"] == "search" and PUBLISHED_RE.search(section):
                continue
            if section.lstrip().startswith("Internal Error"):
                continue
            unknown.append({"section": index, "reason": "unrecognized_result_metadata",
                            "prefix": section[:300].replace("\n", " ")})
        return not unknown, has_internal_error, unknown

    def block_internal_error_urls(self, row: sqlite3.Row, text: str) -> None:
        if row["kind"] != "open":
            return
        for section in result_sections(text):
            if not section.lstrip().startswith("Internal Error"):
                continue
            match = re.search(r'Source:\s*open\(\{"ref_id":"(https?://[^"\\]+)"', section)
            if not match:
                continue
            url = clean_url(match.group(1))
            if not url:
                continue
            self.db.execute(
                "INSERT OR REPLACE INTO blocked_urls(url,reason,source_operation_id,blocked_at) VALUES(?,?,?,?)",
                (url, "fetch_failure" if FETCH_FAILURE_RE.search(section)
                 else "internal_error", row["operation_id"], now()),
            )
            self.db.execute("UPDATE url_frontier SET state='blocked' WHERE url=?", (url,))
            self.event("url_blocked", row["owner_agent_id"], row["operation_id"],
                       url=url, reason="internal_error")

    def handle_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("agent_type") != "spider_agent":
            return {"action": "ignore"}
        agent_id = payload.get("agent_id")
        tool_id = payload.get("tool_use_id")
        row = self.db.execute(
            "SELECT * FROM operations WHERE owner_agent_id=? AND tool_use_id=? AND state='executing'",
            (agent_id, tool_id),
        ).fetchone()
        if row is None:
            return {"action": "halt", "reason": "Unknown spider tool result; stop without further calls."}
        try:
            path, raw_hash = self.store_raw(row["operation_id"], payload)
        except FileExistsError:
            path = self.raw_dir / f"{row['operation_id']}__{tool_id}.json"
            raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        text = response_text(payload)
        self.block_internal_error_urls(row, text)
        result_failures = self.enrich_internal_errors(agent_id, row, text)
        current_internal_errors = [
            failure for failure in result_failures
            if failure.get("classification") == "internal_error"
        ]
        self.block_failed_edges(result_failures)
        compliant, has_internal_error, validation_failures = self.validate_result(row, text)
        self.db.execute(
            "UPDATE operations SET result_compliant=?,has_internal_error=?,validation_json=?,internal_errors_json=? WHERE operation_id=?",
            (1 if compliant else 0, 1 if has_internal_error else 0,
             compact(validation_failures), compact(result_failures), row["operation_id"]),
        )
        if has_internal_error:
            breaker_limit_row = self.db.execute(
                "SELECT value FROM meta WHERE key='internal_error_call_limit'"
            ).fetchone()
            breaker_limit = int(breaker_limit_row[0]) if breaker_limit_row else INTERNAL_ERROR_CALL_LIMIT
            cutoff = (datetime.now(timezone.utc).timestamp() -
                      INTERNAL_ERROR_WINDOW_SECONDS)
            recent_internal_errors = self.db.execute(
                "SELECT COUNT(*) FROM operations WHERE has_internal_error=1 AND committed_at IS NOT NULL AND CAST(strftime('%s',committed_at) AS INTEGER)>=?",
                (int(cutoff),),
            ).fetchone()[0] + 1
            self.event("internal_error_call", agent_id, row["operation_id"],
                       rolling_60_second_count=recent_internal_errors,
                       breaker_limit=breaker_limit,
                       errors=current_internal_errors)
            if recent_internal_errors >= breaker_limit:
                error_calls: list[dict[str, Any]] = []
                for error_row in self.db.execute(
                    "SELECT operation_id,kind,internal_errors_json FROM operations WHERE has_internal_error=1 AND committed_at IS NOT NULL AND CAST(strftime('%s',committed_at) AS INTEGER)>=? ORDER BY committed_at,sequence",
                    (int(cutoff),),
                ):
                    error_calls.append({"operation_id": error_row["operation_id"],
                                        "kind": error_row["kind"],
                                        "errors": json.loads(error_row["internal_errors_json"] or "[]")})
                error_calls.append({"operation_id": row["operation_id"],
                                    "kind": row["kind"],
                                    "errors": current_internal_errors})
                self.abort_run(agent_id, row["operation_id"],
                               "internal_error_call_rate_limit_exceeded",
                               rolling_60_second_count=recent_internal_errors,
                               breaker_limit=breaker_limit,
                               breaker_window_seconds=INTERNAL_ERROR_WINDOW_SECONDS,
                               error_calls=error_calls)
        if not compliant:
            invalid_count = self.db.execute(
                "SELECT COUNT(*) FROM operations WHERE result_compliant=0"
            ).fetchone()[0]
            self.event("result_validation_failed", agent_id, row["operation_id"],
                       invalid_call_count=invalid_count, failures=validation_failures)
            if invalid_count >= 3:
                self.abort_run(agent_id, row["operation_id"],
                               "three_unrecognized_web_calls",
                               invalid_call_count=invalid_count)
        self.parse_result(row, agent_id, text)
        self.db.execute(
            "UPDATE operations SET state='committed',committed_at=?,raw_path=?,raw_sha256=? WHERE operation_id=?",
            (now(), str(path.relative_to(self.run_dir)), raw_hash, row["operation_id"]),
        )
        self.db.execute("UPDATE agents SET stop_attempts=0,last_success_at=?,last_seen_at=? WHERE agent_id=?",
                        (now(), now(), agent_id))
        count = self.db.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        if self.page_limit_hit() and self.db.execute("SELECT 1 FROM meta WHERE key='cap_reached_at'").fetchone() is None:
            self.db.execute("INSERT INTO meta(key,value) VALUES('cap_reached_at',?)", (now(),))
        self.event("operation_committed", agent_id, row["operation_id"], tool_use_id=tool_id,
                   raw_path=str(path.relative_to(self.run_dir)), raw_sha256=raw_hash,
                   collected_pages=count)
        if self.run_aborted():
            return {"action": "continue", "context": self.abort_context()}
        prepared_hydrations = 0
        if self.agent_call_limit_hit(agent_id) and not self.page_limit_hit():
            prepared_hydrations = self.prepare_rotation_hydrations(agent_id)
        bound_ready = self.db.execute(
            "SELECT 1 FROM operations WHERE state='ready' AND required_agent_id=? LIMIT 1",
            (agent_id,),
        ).fetchone() is not None
        if (self.agent_call_limit_hit(agent_id) and
                not bound_ready and
                not self.page_limit_hit()):
            return {"action": "continue", "context":
                    f"SPIDER ROTATION REQUIRED. Your call quota is complete. Call no more tools; return a short rotation-complete message and stop. Prepared {prepared_hydrations} route rehydration job(s) for replacement agents."}
        return {"action": "continue", "context": self.assignment_text(self.lease(agent_id))}

    def handle_stop(self, payload: dict[str, Any]) -> dict[str, Any]:
        agent_id = payload.get("agent_id")
        if not agent_id:
            return {"action": "allow"}
        row = self.db.execute("SELECT stop_attempts FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
        attempts = (row[0] if row else 0) + 1
        self.db.execute("UPDATE agents SET stop_attempts=?,last_seen_at=? WHERE agent_id=?", (attempts, now(), agent_id))
        binding = self.db.execute(
            "SELECT * FROM operations WHERE owner_agent_id=? AND tool_use_id IS NOT NULL AND state='executing' ORDER BY sequence LIMIT 1",
            (agent_id,),
        ).fetchone()
        if binding is None or attempts >= 3:
            # A stopped process cannot transfer ephemeral refs. Return neutral
            # leases to the shared frontier and turn replayable descendants into
            # neutral search-root hydration jobs before cancelling old refs.
            prepared_hydrations = self.prepare_rotation_hydrations(agent_id)
            self.db.execute(
                "UPDATE operations SET state='ready',owner_agent_id=NULL,leased_at=NULL WHERE owner_agent_id=? AND state='leased' AND required_agent_id IS NULL",
                (agent_id,),
            )
            self.db.execute(
                "UPDATE operations SET state='cancelled' WHERE required_agent_id=? AND state IN ('ready','leased')",
                (agent_id,),
            )
            self.db.execute("UPDATE agents SET state='stopped',stopped_at=? WHERE agent_id=?", (now(), agent_id))
            restarted_hydrations = self.restart_hydrations_for_inactive_agents(
                "worker_stopped", agent_id
            )
            self.event("agent_stop_allowed", agent_id, binding["operation_id"] if binding else None,
                       stop_attempts=attempts, known_binding=binding is not None,
                       forced=attempts >= 3,
                       prepared_hydrations=prepared_hydrations,
                       restarted_hydrations=restarted_hydrations)
            return {"action": "allow"}
        self.event("agent_stop_continued", agent_id, binding["operation_id"], stop_attempts=attempts)
        return {"action": "continue", "reason": self.assignment_text(binding)}

    def status(self) -> dict[str, Any]:
        counts = {row[0]: row[1] for row in self.db.execute("SELECT state,COUNT(*) FROM operations GROUP BY state")}
        fingerprint_counts = self.db.execute(
            "SELECT COUNT(*),COALESCE(SUM(CASE WHEN expansion_eligible=1 THEN 1 ELSE 0 END),0) FROM pages"
        ).fetchone()
        invalid_calls = self.db.execute(
            "SELECT COUNT(*) FROM operations WHERE result_compliant=0"
        ).fetchone()[0]
        internal_error_calls = self.db.execute(
            "SELECT COUNT(*) FROM operations WHERE has_internal_error=1"
        ).fetchone()[0]
        return {"run_id": self.run_dir.name,
                "pages": self.db.execute("SELECT COUNT(*) FROM pages").fetchone()[0],
                "operations": counts,
                "aborted": self.run_aborted(),
                "abort_reason": (self.db.execute("SELECT value FROM meta WHERE key='abort_reason'").fetchone() or [None])[0],
                "abort_details": json.loads((self.db.execute("SELECT value FROM meta WHERE key='abort_details_json'").fetchone() or ["null"])[0]),
                "noncompliant_web_calls": invalid_calls,
                "internal_error_web_calls": internal_error_calls,
                "fingerprint_scored_pages": fingerprint_counts[0],
                "fingerprint_expanded_pages": fingerprint_counts[1],
                "fingerprint_threshold": FINGERPRINT_THRESHOLD,
                "blocked_edge_count": self.db.execute(
                    "SELECT COUNT(*) FROM edge_frontier WHERE state='blocked'"
                ).fetchone()[0],
                "hydrations": {row[0]: row[1] for row in self.db.execute(
                    "SELECT state,COUNT(*) FROM hydrations GROUP BY state"
                )},
                "neutral_ready": self.db.execute(
                    "SELECT COUNT(*) FROM operations WHERE state='ready' AND required_agent_id IS NULL"
                ).fetchone()[0],
                "agents": [dict(row) for row in self.db.execute("SELECT * FROM agents ORDER BY started_at")],
                "done": self.page_limit_hit() or self.run_aborted() or counts.get("ready", 0) + counts.get("leased", 0) + counts.get("executing", 0) == 0}

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            event = request.get("event")
            payload = request.get("payload", {})
            self.log("info", "request_received", request_event=event, agent_id=payload.get("agent_id"))
            if event == "subagent-start":
                return self.handle_start(payload)
            if event == "pre-tool":
                return self.handle_pre(payload)
            if event == "post-tool":
                return self.handle_post(payload)
            if event == "subagent-stop":
                return self.handle_stop(payload)
            if event == "status":
                return self.status()
            if event == "shutdown":
                return {"action": "shutdown"}
            return {"error": f"unknown event: {event}"}


class Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        request = json.loads(self.rfile.readline())
        started = time.monotonic()
        response = self.server.state.handle(request)  # type: ignore[attr-defined]
        self.server.state.hook_audit(request, response, (time.monotonic() - started) * 1000)  # type: ignore[attr-defined]
        self.wfile.write((compact(response) + "\n").encode())
        if response.get("action") == "shutdown":
            threading.Thread(target=self.server.shutdown, daemon=True).start()


class Server(socketserver.UnixStreamServer):
    allow_reuse_address = False


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agents(agent_id TEXT PRIMARY KEY,agent_type TEXT,session_id TEXT,state TEXT NOT NULL,stop_attempts INTEGER NOT NULL DEFAULT 0,started_at TEXT,last_success_at TEXT,last_seen_at TEXT,stopped_at TEXT);
CREATE TABLE IF NOT EXISTS operations(operation_id TEXT PRIMARY KEY,sequence INTEGER UNIQUE NOT NULL,kind TEXT NOT NULL,state TEXT NOT NULL,required_agent_id TEXT,owner_agent_id TEXT,tool_input_json TEXT NOT NULL,input_hash TEXT NOT NULL,unique_key TEXT UNIQUE NOT NULL,parent_operation_id TEXT,tool_use_id TEXT UNIQUE,created_at TEXT,leased_at TEXT,executing_at TEXT,committed_at TEXT,raw_path TEXT,raw_sha256 TEXT,result_compliant INTEGER,has_internal_error INTEGER,validation_json TEXT,internal_errors_json TEXT,hydration_id TEXT,hydration_step INTEGER);
CREATE TABLE IF NOT EXISTS capabilities(agent_id TEXT NOT NULL,kind TEXT NOT NULL,ref_id TEXT,parent_ref_id TEXT,link_id INTEGER,state TEXT NOT NULL,source_operation_id TEXT,cached_at TEXT,anchor_text TEXT,hostname_hint TEXT,UNIQUE(agent_id,kind,ref_id,parent_ref_id,link_id));
CREATE TABLE IF NOT EXISTS pages(page_url TEXT PRIMARY KEY,agent_id TEXT,ref_id TEXT,source_operation_id TEXT,collected_at TEXT,cached_at TEXT,fingerprint_score INTEGER,fingerprint_matches_json TEXT,expansion_eligible INTEGER);
CREATE TABLE IF NOT EXISTS url_frontier(url TEXT PRIMARY KEY,state TEXT NOT NULL,source_operation_id TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS blocked_urls(url TEXT PRIMARY KEY,reason TEXT NOT NULL,source_operation_id TEXT,blocked_at TEXT);
CREATE TABLE IF NOT EXISTS page_refs(agent_id TEXT NOT NULL,ref_id TEXT NOT NULL,page_url TEXT NOT NULL,source_operation_id TEXT,created_at TEXT,PRIMARY KEY(agent_id,ref_id));
CREATE TABLE IF NOT EXISTS edge_frontier(parent_kind TEXT NOT NULL,parent_key TEXT NOT NULL,child_kind TEXT NOT NULL,child_key TEXT NOT NULL,state TEXT NOT NULL,owner_agent_id TEXT,source_operation_id TEXT,created_at TEXT,blocked_at TEXT,PRIMARY KEY(parent_kind,parent_key,child_kind,child_key));
CREATE TABLE IF NOT EXISTS page_routes(agent_id TEXT NOT NULL,ref_id TEXT NOT NULL,page_url TEXT NOT NULL,route_json TEXT NOT NULL,source_operation_id TEXT,created_at TEXT,PRIMARY KEY(agent_id,ref_id));
CREATE TABLE IF NOT EXISTS hydrations(hydration_id TEXT PRIMARY KEY,target_page_url TEXT NOT NULL,route_json TEXT NOT NULL,state TEXT NOT NULL,owner_agent_id TEXT,created_at TEXT,completed_at TEXT,failure_json TEXT);
CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY,event TEXT NOT NULL,agent_id TEXT,operation_id TEXT,payload_json TEXT,created_at TEXT);
"""


def run_dir(run_id: str) -> Path:
    return ROOT / "oai-index-scan" / "tmp" / "spider" / run_id


def collect_seeds(inline: list[str] | None, seeds_file: str | None) -> list[str]:
    """Combine repeated CLI seeds with nonblank lines from a UTF-8 seed file."""
    seeds = list(inline or [])
    if seeds_file:
        seeds.extend(line.strip() for line in Path(seeds_file).read_text(encoding="utf-8").splitlines()
                     if line.strip())
    return seeds


def init(args: argparse.Namespace) -> None:
    path = run_dir(args.run)
    if args.max_terms_per_webrun_call < 1 or args.max_terms_per_webrun_call > 10:
        raise SystemExit("--max-terms-per-webrun-call must be between 1 and 10")
    if args.max_operations_per_webrun_call < 1 or args.max_operations_per_webrun_call > 10:
        raise SystemExit("--max-operations-per-webrun-call must be between 1 and 10")
    if args.internal_error_call_limit < 1:
        raise SystemExit("--internal-error-call-limit must be positive")
    if args.search_recency is not None and args.search_recency < 0:
        raise SystemExit("--search-recency must be a non-negative number of days")
    for child in (path / "logs", path / "raw" / "hooks", path / "spool", path / "spool" / "quarantine"):
        child.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path / "state.sqlite3", isolation_level=None)
    db.executescript(SCHEMA)
    db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('max_pages',?)", (str(args.max_pages),))
    db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('direct_url_opens',?)",
               ("1" if args.direct_url_opens else "0",))
    db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('search_only',?)",
               ("1" if args.search_only else "0",))
    db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('max_calls_per_agent',?)",
               (str(args.max_calls_per_agent),))
    db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('internal_error_call_limit',?)",
               (str(args.internal_error_call_limit),))
    db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('max_operations_per_webrun_call',?)",
               (str(args.max_operations_per_webrun_call),))
    db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('fingerprint_threshold',?)",
               (str(FINGERPRINT_THRESHOLD),))
    db.close()
    state = State(path)
    # Seed batches are independent capability roots. Partitioning them lets
    # multiple workers establish their own ephemeral ref inventories while
    # retaining normal batches of up to ten operations within each root.
    args.search_domain = list(dict.fromkeys(
        domain.strip() for domain in args.search_domain if domain.strip()
    ))
    batch_count = min(max(args.initial_search_batches, 1), len(args.seed))
    distributed_batches = [args.seed[offset::batch_count] for offset in range(batch_count)]
    seed_batches = [
        terms[offset:offset + args.max_terms_per_webrun_call]
        for terms in distributed_batches
        for offset in range(0, len(terms), args.max_terms_per_webrun_call)
    ]
    for replica in range(args.initial_search_replicas):
        for batch_index, terms in enumerate(seed_batches):
            salt = (f"seed-replica-{replica}-batch-{batch_index}"
                    if args.initial_search_replicas > 1 else None)
            search_items = []
            for term in terms:
                item: dict[str, Any] = {"q": term}
                if args.search_domain:
                    item["domains"] = args.search_domain
                if args.search_recency is not None:
                    item["recency"] = args.search_recency
                search_items.append(item)
            state.add_batched_operations("search", search_items,
                                         None, None, salt)
    manifest = {"run_id": args.run, "created_at": now(), "seed_terms": args.seed,
                "max_pages": args.max_pages,
                "initial_search_batches": len(seed_batches),
                "initial_search_replicas": args.initial_search_replicas,
                "max_terms_per_webrun_call": args.max_terms_per_webrun_call,
                "max_operations_per_webrun_call": args.max_operations_per_webrun_call,
                "direct_url_opens": args.direct_url_opens,
                "search_only": args.search_only,
                "search_domains": args.search_domain,
                "search_recency_days": args.search_recency,
                "max_calls_per_agent": args.max_calls_per_agent,
                "fingerprint_threshold": FINGERPRINT_THRESHOLD,
                "internal_error_call_limit": args.internal_error_call_limit,
                "internal_error_window_seconds": INTERNAL_ERROR_WINDOW_SECONDS,
                "no_outbound_url_prefixes": list(NO_OUTBOUND_URL_PREFIXES),
                "protocol_version": 5}
    (path / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    state.close()
    print(path)


def add_seeds(args: argparse.Namespace) -> None:
    path = run_dir(args.run)
    state = State(path)
    try:
        state.db.execute(
            "UPDATE operations SET state='cancelled' WHERE state IN ('leased','executing') AND owner_agent_id IN (SELECT agent_id FROM agents WHERE state='stopped')"
        )
        state.add_batched_operations("search", [{"q": term} for term in args.seed], None, None)
        state.event("seeds_added", terms=args.seed)
    finally:
        state.close()


def finalize(args: argparse.Namespace) -> None:
    path = run_dir(args.run)
    state = State(path)
    try:
        # URL extraction may encounter prose punctuation immediately after a URL.
        # Repair older captures before materializing output; INSERT OR IGNORE keeps
        # the earliest record if trimming reveals a duplicate.
        for row in list(state.db.execute("SELECT * FROM pages ORDER BY collected_at,page_url")):
            cleaned = row["page_url"].rstrip(".,:;")
            if cleaned != row["page_url"]:
                state.db.execute(
                    "INSERT OR IGNORE INTO pages(page_url,agent_id,ref_id,source_operation_id,collected_at,cached_at,fingerprint_score,fingerprint_matches_json,expansion_eligible) VALUES(?,?,?,?,?,?,?,?,?)",
                    (cleaned, row["agent_id"], row["ref_id"], row["source_operation_id"], row["collected_at"], row["cached_at"], row["fingerprint_score"], row["fingerprint_matches_json"], row["expansion_eligible"]),
                )
                state.db.execute("DELETE FROM pages WHERE page_url=?", (row["page_url"],))
        status_data = state.status()
        with (path / "pages.jsonl").open("w", encoding="utf-8") as out:
            for row in state.db.execute("SELECT * FROM pages ORDER BY collected_at,page_url"):
                out.write(compact(dict(row)) + "\n")
        with (path / "operations.jsonl").open("w", encoding="utf-8") as out:
            for row in state.db.execute("SELECT * FROM operations ORDER BY sequence"):
                out.write(compact(dict(row)) + "\n")
        with (path / "capabilities.jsonl").open("w", encoding="utf-8") as out:
            for row in state.db.execute("SELECT * FROM capabilities ORDER BY agent_id,kind,COALESCE(ref_id,parent_ref_id),link_id"):
                out.write(compact(dict(row)) + "\n")
        with (path / "search_openable_refs.jsonl").open("w", encoding="utf-8") as out:
            for row in state.db.execute("SELECT c.* FROM capabilities c JOIN operations o ON o.operation_id=c.source_operation_id WHERE c.kind='open' AND o.kind='search' ORDER BY c.agent_id,c.ref_id"):
                out.write(compact(dict(row)) + "\n")
        with (path / "open_clickable_refs.jsonl").open("w", encoding="utf-8") as out:
            for row in state.db.execute("SELECT c.* FROM capabilities c JOIN operations o ON o.operation_id=c.source_operation_id WHERE c.kind='click' ORDER BY c.agent_id,c.parent_ref_id,c.link_id"):
                out.write(compact(dict(row)) + "\n")
        with (path / "blocked_urls.jsonl").open("w", encoding="utf-8") as out:
            for row in state.db.execute("SELECT * FROM blocked_urls ORDER BY blocked_at,url"):
                out.write(compact(dict(row)) + "\n")
        with (path / "page_refs.jsonl").open("w", encoding="utf-8") as out:
            for row in state.db.execute("SELECT * FROM page_refs ORDER BY agent_id,ref_id"):
                out.write(compact(dict(row)) + "\n")
        with (path / "edge_frontier.jsonl").open("w", encoding="utf-8") as out:
            for row in state.db.execute("SELECT * FROM edge_frontier ORDER BY parent_kind,parent_key,child_kind,child_key"):
                out.write(compact(dict(row)) + "\n")
        with (path / "page_routes.jsonl").open("w", encoding="utf-8") as out:
            for row in state.db.execute("SELECT * FROM page_routes ORDER BY agent_id,ref_id"):
                out.write(compact(dict(row)) + "\n")
        with (path / "hydrations.jsonl").open("w", encoding="utf-8") as out:
            for row in state.db.execute("SELECT * FROM hydrations ORDER BY created_at,hydration_id"):
                out.write(compact(dict(row)) + "\n")
        (path / "status.json").write_text(json.dumps(status_data, indent=2) + "\n")
        # Runs produced before live hook-audit logging was enabled can reconstruct
        # a compact audit trail from authoritative semantic events.
        if not state.hook_log_path.exists():
            mapping = {
                "agent_started": "subagent-start", "tool_authorized": "pre-tool",
                "tool_denied": "pre-tool", "operation_committed": "post-tool",
                "agent_stop_allowed": "subagent-stop", "agent_stop_continued": "subagent-stop",
            }
            with state.hook_log_path.open("w", encoding="utf-8") as out:
                for row in state.db.execute("SELECT * FROM events ORDER BY sequence"):
                    if row["event"] not in mapping:
                        continue
                    payload = json.loads(row["payload_json"] or "{}")
                    out.write(compact({"schema_version": 1, "time": row["created_at"],
                                       "level": "info", "run_id": args.run,
                                       "event": "hook_reconstructed",
                                       "hook_event": mapping[row["event"]],
                                       "agent_id": row["agent_id"],
                                       "operation_id": row["operation_id"],
                                       "semantic_event": row["event"],
                                       "details": payload}) + "\n")
        meta = {row[0]: row[1] for row in state.db.execute("SELECT key,value FROM meta")}
        elapsed = None
        if meta.get("crawl_started_at") and meta.get("cap_reached_at"):
            elapsed = (datetime.fromisoformat(meta["cap_reached_at"].replace("Z", "+00:00")) -
                       datetime.fromisoformat(meta["crawl_started_at"].replace("Z", "+00:00"))).total_seconds()
        summary = {
            "schema_version": 1,
            "run_id": args.run,
            "finalized_at": now(),
            "collected_pages": status_data["pages"],
            "operation_counts": status_data["operations"],
            "agent_count": len(status_data["agents"]),
            "event_count": state.db.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            "raw_capture_count": state.db.execute("SELECT COUNT(*) FROM operations WHERE raw_path IS NOT NULL").fetchone()[0],
            "openable_search_ref_count": state.db.execute("SELECT COUNT(*) FROM capabilities c JOIN operations o ON o.operation_id=c.source_operation_id WHERE c.kind='open' AND o.kind='search'").fetchone()[0],
            "clickable_open_ref_count": state.db.execute("SELECT COUNT(*) FROM capabilities WHERE kind='click'").fetchone()[0],
            "crawl_started_at": meta.get("crawl_started_at"),
            "cap_reached_at": meta.get("cap_reached_at"),
            "crawl_elapsed_seconds": elapsed,
            "hook_audit_count": sum(1 for _ in state.hook_log_path.open(encoding="utf-8")),
            "forced_stop_count": state.db.execute("SELECT COUNT(*) FROM events WHERE event='agent_stop_allowed' AND json_extract(payload_json,'$.forced')=1").fetchone()[0],
            "noncompliant_web_call_count": status_data["noncompliant_web_calls"],
            "internal_error_web_call_count": status_data["internal_error_web_calls"],
            "fingerprint_scored_page_count": status_data["fingerprint_scored_pages"],
            "fingerprint_expanded_page_count": status_data["fingerprint_expanded_pages"],
            "fingerprint_threshold": status_data["fingerprint_threshold"],
            "aborted": status_data["aborted"],
            "abort_reason": status_data["abort_reason"],
            "abort_details": status_data["abort_details"],
            "blocked_url_count": state.db.execute("SELECT COUNT(*) FROM blocked_urls").fetchone()[0],
            "blocked_edge_count": status_data["blocked_edge_count"],
            "hydration_counts": status_data["hydrations"],
            "rotation_limit_overrun_call_count": state.db.execute(
                "SELECT COALESCE(SUM(CASE WHEN ?>0 AND committed_calls>? THEN committed_calls-? ELSE 0 END),0) FROM (SELECT owner_agent_id,COUNT(*) AS committed_calls FROM operations WHERE state='committed' AND owner_agent_id IS NOT NULL GROUP BY owner_agent_id)",
                (int(meta.get("max_calls_per_agent", "0")),
                 int(meta.get("max_calls_per_agent", "0")),
                 int(meta.get("max_calls_per_agent", "0"))),
            ).fetchone()[0],
        }
        (path / "logs" / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
    finally:
        state.close()


def request(run_id: str, event: str) -> dict[str, Any]:
    path = run_dir(run_id) / "orchestrator.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(str(path))
        sock.sendall((compact({"event": event}) + "\n").encode())
        data = b""
        while not data.endswith(b"\n"):
            data += sock.recv(65536)
    return json.loads(data)


def serve(args: argparse.Namespace) -> None:
    path = run_dir(args.run)
    sock_path = path / "orchestrator.sock"
    if sock_path.exists():
        sock_path.unlink()
    state = State(path)
    state.recover_for_serve()
    server = Server(str(sock_path), Handler)
    server.state = state  # type: ignore[attr-defined]
    try:
        os.chmod(sock_path, 0o600)
    except OSError:
        # Some workspace-backed filesystems do not implement chmod for sockets.
        pass
    state.log("info", "service_started", socket=str(sock_path))
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        state.log("info", "service_stopped")
        server.server_close()
        state.close()
        sock_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--run", required=True)
    p_init.add_argument("--seed", action="append")
    p_init.add_argument("--seeds-file",
                        help="UTF-8 file containing one seed per line; blank lines are ignored")
    p_init.add_argument("--max-pages", type=int, default=100)
    p_init.add_argument("--initial-search-batches", type=int, default=1)
    p_init.add_argument("--initial-search-replicas", type=int, default=1)
    p_init.add_argument("--max-terms-per-webrun-call", type=int, default=10)
    p_init.add_argument("--max-operations-per-webrun-call", type=int, default=10)
    p_init.add_argument("--direct-url-opens", action="store_true")
    p_init.add_argument("--search-only", action="store_true",
                        help="Collect search responses without queuing result opens")
    p_init.add_argument("--search-domain", action="append", default=[],
                        help="Domain allowlist entry applied to every seed search")
    p_init.add_argument("--search-recency", type=int,
                        help="Recency window in days applied to every seed search")
    p_init.add_argument("--max-calls-per-agent", type=int, default=0)
    p_init.add_argument("--internal-error-call-limit", type=int, default=INTERNAL_ERROR_CALL_LIMIT)
    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--run", required=True)
    p_add = sub.add_parser("add-seed")
    p_add.add_argument("--run", required=True)
    p_add.add_argument("--seed", action="append")
    p_add.add_argument("--seeds-file",
                       help="UTF-8 file containing one seed per line; blank lines are ignored")
    for name in ("status", "shutdown", "finalize"):
        child = sub.add_parser(name)
        child.add_argument("--run", required=True)
    args = parser.parse_args()
    if args.command in ("init", "add-seed"):
        try:
            args.seed = collect_seeds(args.seed, args.seeds_file)
        except OSError as exc:
            parser.error(f"cannot read --seeds-file: {exc}")
        if not args.seed:
            parser.error("at least one seed is required via --seed or --seeds-file")
    if args.command == "init":
        init(args)
    elif args.command == "add-seed":
        add_seeds(args)
    elif args.command == "finalize":
        finalize(args)
    elif args.command == "serve":
        serve(args)
    else:
        print(json.dumps(request(args.run, args.command), indent=2))


if __name__ == "__main__":
    main()
