#!/usr/bin/env python3
"""Run and rotate a bounded pool of top-level Codex spider workers."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR = ROOT / "oai-index-scan" / "spider" / "orchestrator.py"
LAUNCHER = ROOT / "oai-index-scan" / "spider" / "worker_launcher.py"


def compact(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def collect_seeds(inline: list[str] | None, seeds_file: str | None) -> list[str]:
    """Combine repeated CLI seeds with nonblank lines from a UTF-8 seed file."""
    seeds = list(inline or [])
    if seeds_file:
        seeds.extend(line.strip() for line in Path(seeds_file).read_text(encoding="utf-8").splitlines()
                     if line.strip())
    return seeds


def initial_search_layout(workers: int, search_only: bool) -> tuple[int, int]:
    """Return (partition batches, replicas) for a new run."""
    return (workers, 1) if search_only else (1, workers)


def request(run_id: str, event: str) -> dict[str, Any]:
    path = ROOT / "oai-index-scan" / "tmp" / "spider" / run_id / "orchestrator.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(str(path))
        client.sendall((compact({"event": event}) + "\n").encode())
        data = b""
        while not data.endswith(b"\n"):
            data += client.recv(65536)
    return json.loads(data)


def wait_for_socket(run_id: str, server: subprocess.Popen[bytes]) -> None:
    path = ROOT / "oai-index-scan" / "tmp" / "spider" / run_id / "orchestrator.sock"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"orchestrator exited with {server.returncode}")
        if path.exists():
            return
        time.sleep(0.05)
    raise TimeoutError("orchestrator socket did not appear")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--seed", action="append")
    parser.add_argument("--seeds-file",
                        help="UTF-8 file containing one seed per line; blank lines are ignored")
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--max-calls-per-worker", type=int)
    parser.add_argument("--internal-error-call-limit", type=int, default=30,
                        help="Abort after this many WebRun calls with Internal Error in 60 seconds")
    parser.add_argument("--max-terms-per-webrun-call", type=int, default=10)
    parser.add_argument("--max-operations-per-webrun-call", type=int, default=10,
                        help="Maximum search/open/click members in any WebRun call")
    parser.add_argument("--no-direct-url-opens", action="store_true",
                        help="Traverse only agent-local search/open/click ref chains")
    parser.add_argument("--search-only", action="store_true",
                        help="Collect search responses without opening result links")
    parser.add_argument("--search-domain", action="append", default=[],
                        help="Domain allowlist entry applied to every seed search")
    parser.add_argument("--search-recency", type=int,
                        help="Recency window in days applied to every seed search")
    args = parser.parse_args()
    try:
        seeds = collect_seeds(args.seed, args.seeds_file)
    except OSError as exc:
        parser.error(f"cannot read --seeds-file: {exc}")
    run_dir = ROOT / "oai-index-scan" / "tmp" / "spider" / args.run
    if args.resume:
        if seeds:
            parser.error("--seed/--seeds-file cannot be used with --resume")
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.exists() or not (run_dir / "state.sqlite3").exists():
            parser.error("resume requested but the run state does not exist")
        manifest = json.loads(manifest_path.read_text())
        workers_limit = args.workers or int(manifest.get(
            "pool_workers", manifest.get("initial_search_replicas", 1)
        ))
        max_calls = args.max_calls_per_worker or int(manifest.get("max_calls_per_agent", 0))
        if max_calls < 1:
            parser.error("resumed run has no positive worker call limit")
        if args.max_calls_per_worker is not None:
            db = sqlite3.connect(run_dir / "state.sqlite3", isolation_level=None)
            db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('max_calls_per_agent',?)",
                       (str(max_calls),))
            db.close()
    else:
        if not seeds or args.max_pages is None or args.workers is None or args.max_calls_per_worker is None:
            parser.error("new runs require seeds (--seed or --seeds-file), --max-pages, --workers, and --max-calls-per-worker")
        workers_limit = args.workers
        max_calls = args.max_calls_per_worker
        if run_dir.exists():
            parser.error("run directory already exists; pass --resume to continue it")
        init = [sys.executable, str(ORCHESTRATOR), "init", "--run", args.run]
        for term in seeds:
            init.extend(["--seed", term])
        initial_batches, initial_replicas = initial_search_layout(
            workers_limit, args.search_only
        )
        init.extend(["--max-pages", str(args.max_pages),
                     "--initial-search-batches", str(initial_batches),
                     "--initial-search-replicas", str(initial_replicas),
                     "--max-calls-per-agent", str(max_calls),
                     "--max-terms-per-webrun-call",
                     str(args.max_terms_per_webrun_call),
                     "--max-operations-per-webrun-call",
                     str(args.max_operations_per_webrun_call),
                     "--internal-error-call-limit",
                     str(args.internal_error_call_limit)])
        if not args.no_direct_url_opens:
            init.append("--direct-url-opens")
        if args.search_only:
            init.append("--search-only")
        for domain in args.search_domain:
            init.extend(["--search-domain", domain])
        if args.search_recency is not None:
            init.extend(["--search-recency", str(args.search_recency)])
        subprocess.run(init, cwd=ROOT, check=True)
        manifest_path = run_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["pool_workers"] = workers_limit
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if min(workers_limit, max_calls) < 1:
        parser.error("limits must all be positive")
    server = subprocess.Popen(
        [sys.executable, str(ORCHESTRATOR), "serve", "--run", args.run], cwd=ROOT
    )
    workers: dict[str, tuple[subprocess.Popen[bytes], Any]] = {}
    sequence = 0
    worker_log_dir = run_dir / "logs" / "workers"
    worker_log_dir.mkdir(parents=True, exist_ok=True)
    try:
        wait_for_socket(args.run, server)
        sequence = len(request(args.run, "status")["agents"])
        while True:
            for worker_id, (process, log_handle) in list(workers.items()):
                if process.poll() is not None:
                    log_handle.close()
                    del workers[worker_id]
            status = request(args.run, "status")
            if status["done"]:
                break
            while len(workers) < workers_limit and status["neutral_ready"] > 0:
                sequence += 1
                worker_id = f"pool-{sequence:05d}"
                log_handle = (worker_log_dir / f"{worker_id}.log").open("wb")
                command = [sys.executable, str(LAUNCHER), "--run", args.run,
                           "--worker-id", worker_id, "--output",
                           str(worker_log_dir / f"{worker_id}-last-message.txt")]
                process = subprocess.Popen(command, cwd=ROOT, stdout=log_handle,
                                           stderr=subprocess.STDOUT)
                workers[worker_id] = (process, log_handle)
                status["neutral_ready"] -= 1
            if not workers and status["neutral_ready"] == 0:
                break
            time.sleep(0.2)
        for process, _ in workers.values():
            process.wait(timeout=120)
        return 0
    finally:
        for process, log_handle in workers.values():
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            log_handle.close()
        if server.poll() is None:
            try:
                request(args.run, "shutdown")
                server.wait(timeout=10)
            except (OSError, TimeoutError, subprocess.TimeoutExpired):
                server.terminate()
                server.wait()
        subprocess.run([sys.executable, str(ORCHESTRATOR), "finalize", "--run", args.run],
                       cwd=ROOT, check=False)


if __name__ == "__main__":
    sys.exit(main())
