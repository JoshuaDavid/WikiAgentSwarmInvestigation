#!/usr/bin/env python3
"""Codex hook adapter for the oai-index-scan spider orchestrator."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def active_run() -> dict[str, str]:
    run_id = os.environ["OAI_SPIDER_RUN_ID"]
    socket_path = ROOT / "oai-index-scan" / "tmp" / "spider" / run_id / "orchestrator.sock"
    return {"run_id": run_id, "socket": str(socket_path)}


def compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def call_service(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    active = active_run()
    request = {"event": event, "payload": payload}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(25)
        sock.connect(active["socket"])
        sock.sendall((compact(request) + "\n").encode())
        data = b""
        while not data.endswith(b"\n"):
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
    return json.loads(data)


def spool(event: str, payload: dict[str, Any], error: Exception) -> None:
    try:
        active = active_run()
        base = ROOT / "oai-index-scan" / "tmp" / "spider" / active["run_id"] / "spool"
        base.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        identity = hashlib.sha256(compact(payload).encode()).hexdigest()[:16]
        path = base / f"{stamp}__{event}__{identity}.json"
        body = {"event": event, "payload": payload, "client_error": type(error).__name__}
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as out:
            out.write(compact(body) + "\n")
            out.flush()
            os.fsync(out.fileno())
    except Exception:
        pass


def emit(event: str, result: dict[str, Any]) -> None:
    action = result.get("action")
    if event == "subagent-start":
        print(compact({"hookSpecificOutput": {"hookEventName": "SubagentStart",
                                               "additionalContext": result["context"]}}))
    elif event == "pre-tool":
        if action == "deny":
            print(compact({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                   "permissionDecision": "deny",
                                                   "permissionDecisionReason": result["reason"]}}))
    elif event == "post-tool":
        if action == "continue":
            print(compact({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                   "additionalContext": result["context"]}}))
        elif action == "halt":
            print(compact({"continue": False, "stopReason": result["reason"],
                           "systemMessage": result["reason"]}))
    elif event == "subagent-stop" and action == "continue":
        print(compact({"decision": "block", "reason": result["reason"]}))


def main() -> None:
    event = sys.argv[1]
    payload = json.load(sys.stdin)
    worker_id = os.environ.get("OAI_SPIDER_WORKER_ID")
    if worker_id and not payload.get("agent_id"):
        payload["agent_id"] = worker_id
        payload["agent_type"] = "spider_agent"
    if event in ("pre-tool", "post-tool") and payload.get("agent_type") != "spider_agent":
        return
    try:
        result = call_service(event, payload)
    except Exception as error:
        spool(event, payload, error)
        if event == "pre-tool" and payload.get("agent_type") == "spider_agent":
            result = {"action": "deny", "reason": "Spider policy: orchestrator unavailable."}
        elif event == "post-tool" and payload.get("agent_type") == "spider_agent":
            result = {"action": "halt", "reason": "Spider result spooled; orchestrator unavailable. Stop."}
        elif event == "subagent-start":
            result = {"context": "SPIDER ORCHESTRATOR UNAVAILABLE. Call no tools and stop."}
        else:
            result = {"action": "allow"}
    emit(event, result)


if __name__ == "__main__":
    main()
