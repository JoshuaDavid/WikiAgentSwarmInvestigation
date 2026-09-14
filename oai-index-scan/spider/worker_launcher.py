#!/usr/bin/env python3
"""Launch a top-level Codex process as an orchestrator-governed spider worker."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tomllib
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def compact(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def service_request(run_id: str, event: str, payload: dict[str, object]) -> dict[str, object]:
    socket_path = ROOT / "oai-index-scan" / "tmp" / "spider" / run_id / "orchestrator.sock"
    request = {"event": event, "payload": payload}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(str(socket_path))
        client.sendall((compact(request) + "\n").encode())
        data = b""
        while not data.endswith(b"\n"):
            chunk = client.recv(65536)
            if not chunk:
                break
            data += chunk
    return json.loads(data)


def worker_payload(worker_id: str) -> dict[str, object]:
    return {"agent_id": worker_id, "agent_type": "spider_agent",
            "session_id": f"top-level:{worker_id}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    config_path = ROOT / ".codex" / "agents" / "spider-agent.toml"
    with config_path.open("rb") as source:
        agent = tomllib.load(source)
    worker_id = args.worker_id or f"top-{uuid.uuid4()}"
    assignment = service_request(args.run, "subagent-start", worker_payload(worker_id))["context"]
    prompt = (
        f"{agent['developer_instructions'].strip()}\n\n"
        "You are running as a top-level worker process. The following is your "
        "initial hook-authorized assignment:\n\n"
        f"{assignment}"
    )
    command = [
        "codex", "exec", "--dangerously-bypass-hook-trust", "--approve-for-me",
        "-C", str(ROOT), "--model", agent["model"],
        "-c", f"model_reasoning_effort=\"{agent.get('model_reasoning_effort', 'low')}\"",
    ]
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        command.extend(["-o", str(args.output)])
    command.append(prompt)
    environment = os.environ.copy()
    environment["OAI_SPIDER_RUN_ID"] = args.run
    environment["OAI_SPIDER_WORKER_ID"] = worker_id
    try:
        return subprocess.run(command, cwd=ROOT, env=environment, check=False).returncode
    finally:
        try:
            service_request(args.run, "subagent-stop", worker_payload(worker_id))
        except (OSError, ValueError, KeyError):
            pass


if __name__ == "__main__":
    sys.exit(main())
