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


ROOT = Path(__file__).resolve().parents[2]
REF_RE = re.compile(r"cite(turn[\w-]+(?:search|view|academia|news|reddit)\d+)")
URL_RE = re.compile(r"https?://[^\s)\]>]+")
LINK_RE = re.compile(r"cite(\d+)†")
CACHED_RE = re.compile(r"(?:Crawled|Cached):\s*([^;\n]+)", re.IGNORECASE)
SEPARATOR_RE = re.compile(r"\n-{20,}\n")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(compact(value).encode()).hexdigest()


def response_text(payload: dict[str, Any]) -> str:
    response = payload.get("tool_response")
    if isinstance(response, str):
        return response
    if isinstance(response, list):
        return "\n".join(
            str(item.get("text", "")) for item in response if isinstance(item, dict)
        )
    return compact(response)


class State:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.db = sqlite3.connect(run_dir / "state.sqlite3", isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.log_path = run_dir / "logs" / "orchestrator.jsonl"
        self.hook_log_path = run_dir / "logs" / "hooks.jsonl"
        self.events_path = run_dir / "events.jsonl"
        self.raw_dir = run_dir / "raw" / "hooks"
        self.seq = self.db.execute("SELECT COALESCE(MAX(sequence), 0) FROM events").fetchone()[0]
        self.lock = threading.Lock()

    def close(self) -> None:
        self.db.close()

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

    def lease(self, agent_id: str) -> sqlite3.Row | None:
        current = self.db.execute(
            "SELECT * FROM operations WHERE owner_agent_id=? AND state IN ('leased','executing') ORDER BY sequence LIMIT 1",
            (agent_id,),
        ).fetchone()
        if current:
            return current
        if self.page_limit_hit():
            return None
        owns_search_root = self.db.execute(
            "SELECT 1 FROM operations WHERE owner_agent_id=? AND kind='search' LIMIT 1",
            (agent_id,),
        ).fetchone() is not None
        if owns_search_root:
            # Neutral search roots seed independent ephemeral capability trees.
            # Once a worker owns one, reserve the remaining roots for workers
            # that have not yet established a tree.
            row = self.db.execute(
                "SELECT * FROM operations WHERE state='ready' AND required_agent_id=? ORDER BY sequence LIMIT 1",
                (agent_id,),
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
        if self.page_limit_hit():
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
        unique_items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in items:
            key = compact(item)
            if key not in seen:
                seen.add(key)
                unique_items.append(item)
        for offset in range(0, len(unique_items), 10):
            salt = f"{unique_salt}:{offset // 10}" if unique_salt is not None else None
            self.add_operation(kind, {field: unique_items[offset:offset + 10],
                                      "response_length": "long"}, required_agent, parent, salt)

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
        sections = [section for section in SEPARATOR_RE.split(text) if section.strip()]
        if kind == "search":
            open_items: list[dict[str, Any]] = []
            for section in sections:
                cached_match = CACHED_RE.search(section)
                cached_at = cached_match.group(1).strip() if cached_match else None
                refs = list(dict.fromkeys(REF_RE.findall(section)))
                for ref in refs:
                    if not any(token in ref for token in ("search", "academia", "news", "reddit")):
                        continue
                    self.db.execute(
                        "INSERT OR IGNORE INTO capabilities(agent_id,kind,ref_id,parent_ref_id,link_id,state,source_operation_id,cached_at) VALUES(?,?,?,?,?,'active',?,?)",
                        (agent_id, "open", ref, None, None, operation_id, cached_at),
                    )
                    open_items.append({"ref_id": ref})
            self.add_batched_operations("open", open_items, agent_id, operation_id)
        else:
            click_items: list[dict[str, Any]] = []
            for section in sections:
                if self.page_limit_hit():
                    break
                refs = list(dict.fromkeys(REF_RE.findall(section)))
                urls = list(dict.fromkeys(URL_RE.findall(section)))
                page_ref = next((ref for ref in refs if "view" in ref), None)
                destination = urls[0].rstrip(".,:;") if urls else None
                cached_match = CACHED_RE.search(section)
                cached_at = cached_match.group(1).strip() if cached_match else None
                if not destination:
                    continue
                self.db.execute(
                    "INSERT OR IGNORE INTO pages(page_url,agent_id,ref_id,source_operation_id,collected_at,cached_at) VALUES(?,?,?,?,?,?)",
                    (destination, agent_id, page_ref, operation_id, now(), cached_at),
                )
                if not page_ref:
                    continue
                self.db.execute(
                    "INSERT OR IGNORE INTO capabilities(agent_id,kind,ref_id,parent_ref_id,link_id,state,source_operation_id,cached_at) VALUES(?,?,?,?,?,'active',?,?)",
                    (agent_id, "open", page_ref, None, None, operation_id, cached_at),
                )
                for link_id in list(dict.fromkeys(int(value) for value in LINK_RE.findall(section))):
                    self.db.execute(
                        "INSERT OR IGNORE INTO capabilities(agent_id,kind,ref_id,parent_ref_id,link_id,state,source_operation_id,cached_at) VALUES(?,?,?,?,?,'active',?,?)",
                        (agent_id, "click", None, page_ref, link_id, operation_id, cached_at),
                    )
                    click_items.append({"ref_id": page_ref, "id": link_id})
            self.add_batched_operations("click", click_items, agent_id, operation_id)

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
            self.db.execute("UPDATE agents SET state='stopped',stopped_at=? WHERE agent_id=?", (now(), agent_id))
            self.event("agent_stop_allowed", agent_id, binding["operation_id"] if binding else None,
                       stop_attempts=attempts, known_binding=binding is not None, forced=attempts >= 3)
            return {"action": "allow"}
        self.event("agent_stop_continued", agent_id, binding["operation_id"], stop_attempts=attempts)
        return {"action": "continue", "reason": self.assignment_text(binding)}

    def status(self) -> dict[str, Any]:
        counts = {row[0]: row[1] for row in self.db.execute("SELECT state,COUNT(*) FROM operations GROUP BY state")}
        return {"run_id": self.run_dir.name,
                "pages": self.db.execute("SELECT COUNT(*) FROM pages").fetchone()[0],
                "operations": counts,
                "agents": [dict(row) for row in self.db.execute("SELECT * FROM agents ORDER BY started_at")],
                "done": self.page_limit_hit() or counts.get("ready", 0) + counts.get("leased", 0) + counts.get("executing", 0) == 0}

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
CREATE TABLE IF NOT EXISTS operations(operation_id TEXT PRIMARY KEY,sequence INTEGER UNIQUE NOT NULL,kind TEXT NOT NULL,state TEXT NOT NULL,required_agent_id TEXT,owner_agent_id TEXT,tool_input_json TEXT NOT NULL,input_hash TEXT NOT NULL,unique_key TEXT UNIQUE NOT NULL,parent_operation_id TEXT,tool_use_id TEXT UNIQUE,created_at TEXT,leased_at TEXT,executing_at TEXT,committed_at TEXT,raw_path TEXT,raw_sha256 TEXT);
CREATE TABLE IF NOT EXISTS capabilities(agent_id TEXT NOT NULL,kind TEXT NOT NULL,ref_id TEXT,parent_ref_id TEXT,link_id INTEGER,state TEXT NOT NULL,source_operation_id TEXT,cached_at TEXT,UNIQUE(agent_id,kind,ref_id,parent_ref_id,link_id));
CREATE TABLE IF NOT EXISTS pages(page_url TEXT PRIMARY KEY,agent_id TEXT,ref_id TEXT,source_operation_id TEXT,collected_at TEXT,cached_at TEXT);
CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY,event TEXT NOT NULL,agent_id TEXT,operation_id TEXT,payload_json TEXT,created_at TEXT);
"""


def run_dir(run_id: str) -> Path:
    return ROOT / "oai-index-scan" / "tmp" / "spider" / run_id


def init(args: argparse.Namespace) -> None:
    path = run_dir(args.run)
    for child in (path / "logs", path / "raw" / "hooks", path / "spool", path / "spool" / "quarantine"):
        child.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path / "state.sqlite3", isolation_level=None)
    db.executescript(SCHEMA)
    db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('max_pages',?)", (str(args.max_pages),))
    db.close()
    state = State(path)
    # Seed batches are independent capability roots. Partitioning them lets
    # multiple workers establish their own ephemeral ref inventories while
    # retaining normal batches of up to ten operations within each root.
    batch_count = min(max(args.initial_search_batches, 1), len(args.seed))
    seed_batches = [args.seed[offset::batch_count] for offset in range(batch_count)]
    for replica in range(args.initial_search_replicas):
        for batch_index, terms in enumerate(seed_batches):
            salt = (f"seed-replica-{replica}-batch-{batch_index}"
                    if args.initial_search_replicas > 1 else None)
            state.add_batched_operations("search", [{"q": term} for term in terms],
                                         None, None, salt)
    manifest = {"run_id": args.run, "created_at": now(), "seed_terms": args.seed,
                "max_pages": args.max_pages,
                "initial_search_batches": batch_count,
                "initial_search_replicas": args.initial_search_replicas,
                "protocol_version": 2}
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
                    "INSERT OR IGNORE INTO pages(page_url,agent_id,ref_id,source_operation_id,collected_at,cached_at) VALUES(?,?,?,?,?,?)",
                    (cleaned, row["agent_id"], row["ref_id"], row["source_operation_id"], row["collected_at"], row["cached_at"]),
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
    p_init.add_argument("--seed", action="append", required=True)
    p_init.add_argument("--max-pages", type=int, default=100)
    p_init.add_argument("--initial-search-batches", type=int, default=1)
    p_init.add_argument("--initial-search-replicas", type=int, default=1)
    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--run", required=True)
    p_add = sub.add_parser("add-seed")
    p_add.add_argument("--run", required=True)
    p_add.add_argument("--seed", action="append", required=True)
    for name in ("status", "shutdown", "finalize"):
        child = sub.add_parser(name)
        child.add_argument("--run", required=True)
    args = parser.parse_args()
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
