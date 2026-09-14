"""Run a real app-server compaction and a matched new-turn reference control."""

import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import tomllib

base = Path(__file__).resolve().parent
version, variant, action = sys.argv[1:4]
assert action in {"compact", "new-turn"}
run_dir = base / version / variant
probe_home = run_dir / "home"
config = tomllib.loads((probe_home / "config.toml").read_text())
child_env = os.environ.copy()
child_env["CODEX_HOME"] = str(probe_home)
command = [str(base / version / "codex"), "app-server", "--listen", "stdio://"]
transcript = (run_dir / "server-events.jsonl").open("w")
errors = (run_dir / "stderr.log").open("w")
messages = queue.Queue()
history = []
pending = []
write_lock = threading.Lock()
metadata = {"version": version, "variant": variant, "action": action,
            "model": config.get("model"), "web_search": config.get("web_search"),
            "standalone_web_search": config.get("features", {}).get("standalone_web_search", False),
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "command": command}
(run_dir / "run.json").write_text(json.dumps(metadata, indent=2))
process = subprocess.Popen(command, env=child_env, stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=errors, text=True, bufsize=1)


def record(direction, message):
    with write_lock:
        transcript.write(json.dumps({"timestamp": time.time(), "direction": direction,
                                     "message": message}) + "\n")
        transcript.flush()


def read_messages():
    for line in process.stdout:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            record("unparsed", line)
            continue
        record("received", message)
        history.append(message)
        messages.put(message)
    messages.put(None)


threading.Thread(target=read_messages, daemon=True).start()


def send(message):
    record("sent", message)
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()


def wait_for(predicate, timeout=240):
    for index, message in enumerate(pending):
        if predicate(message):
            return pending.pop(index)
    deadline = time.monotonic() + timeout
    while True:
        message = messages.get(timeout=max(0.1, deadline - time.monotonic()))
        if message is None:
            raise RuntimeError("App server exited before the expected event")
        if predicate(message):
            return message
        if message.get("method") == "error" and not message.get("params", {}).get("willRetry", False):
            raise RuntimeError("App-server error: " + json.dumps(message["params"]["error"]))
        if "method" in message and "id" in message:
            send({"id": message["id"], "error": {
                "code": -32601, "message": "This read-only test does not handle server requests"}})
            raise RuntimeError("Unexpected server request: " + message["method"])
        pending.append(message)
        if time.monotonic() >= deadline:
            raise TimeoutError("Timed out waiting for an app-server event")


request_number = 0


def rpc(method, params):
    global request_number
    request_number += 1
    request_id = request_number
    send({"id": request_id, "method": method, "params": params})
    response = wait_for(lambda m: m.get("id") == request_id and "method" not in m)
    if "error" in response:
        raise RuntimeError(json.dumps(response["error"]))
    return response["result"]


def wait_turn(thread_id, turn_id):
    message = wait_for(lambda m: m.get("method") == "turn/completed"
                       and m.get("params", {}).get("threadId") == thread_id
                       and m.get("params", {}).get("turn", {}).get("id") == turn_id)
    if message["params"]["turn"]["status"] != "completed":
        raise RuntimeError("Turn did not complete: " + json.dumps(message["params"]["turn"]))


def run_turn(thread_id, prompt, schema):
    result = rpc("turn/start", {"threadId": thread_id,
                 "input": [{"type": "text", "text": prompt}], "outputSchema": schema})
    turn_id = result["turn"]["id"]
    wait_turn(thread_id, turn_id)
    outputs = [m["params"]["item"]["text"] for m in history
               if m.get("method") == "item/completed"
               and m.get("params", {}).get("threadId") == thread_id
               and m.get("params", {}).get("turnId") == turn_id
               and m.get("params", {}).get("item", {}).get("type") == "agentMessage"]
    if not outputs:
        raise RuntimeError("No completed agent message found for turn " + turn_id)
    return {"turn_id": turn_id, "result": json.loads(outputs[-1])}


def schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


report = {}
try:
    rpc("initialize", {"clientInfo": {"name": "codex_ref_history_probe", "version": "0.1"},
                       "capabilities": {"experimentalApi": True}})
    send({"method": "initialized", "params": {}})
    started = rpc("thread/start", {"model": "gpt-5.5", "cwd": str(base / "workdir"),
                                   "experimentalRawEvents": True})
    thread_id = started["thread"]["id"]
    report["thread_id"] = thread_id
    print(json.dumps({"variant": variant, "stage": "thread_started", "thread_id": thread_id}), flush=True)
    baseline_schema = schema({
        "original_ref": {"type": "string"}, "original_ok": {"type": "boolean"},
        "original_ref_turn_number": {"type": "integer"},
        "original_ref_view_number": {"type": "integer"},
        "baseline_ref": {"type": "string"}, "baseline_ok": {"type": "boolean"},
        "details": {"type": "string"},
    })
    report["baseline"] = run_turn(thread_id,
        "Read-only reference experiment: use only web.run, no other tools or agents. "
        "First open https://www.python.org/ with exactly one open operation. "
        "Then, in a separate web call, open the exact reference returned by that first call. "
        "Never batch these calls. Record the first returned reference as original_ref and "
        "the second as baseline_ref. Mark original_ok and baseline_ok true only if real "
        "Python.org page content returned, not an Internal Error. Return the required JSON "
        "with actual page titles or exact error details. The reference means the literal "
        "turnNviewM token, NOT the page URL. Also copy the two observed integers N and M "
        "from the FIRST returned reference into original_ref_turn_number and "
        "original_ref_view_number. This numeric representation avoids any output "
        "formatting that replaces reference strings with URLs. Never invent a reference.", baseline_schema)
    original = report["baseline"]["result"]
    if not original["original_ok"] or not original["baseline_ok"]:
        raise RuntimeError("Baseline did not produce a working reference")
    original_ref = ("turn" + str(original["original_ref_turn_number"]) + "view"
                    + str(original["original_ref_view_number"]))
    if not re.fullmatch(r"turn\d+view\d+", original_ref):
        raise RuntimeError("Invalid numeric reference components")
    report["tested_original_ref"] = original_ref
    print(json.dumps({"variant": variant, "stage": "baseline", **original}), flush=True)
    if action == "compact":
        rpc("thread/compact/start", {"threadId": thread_id})
        compacted = wait_for(lambda m: m.get("method") == "item/completed"
                            and m.get("params", {}).get("threadId") == thread_id
                            and m.get("params", {}).get("item", {}).get("type") == "contextCompaction")
        report["compaction_event"] = compacted
        wait_turn(thread_id, compacted["params"]["turnId"])
        print(json.dumps({"variant": variant, "stage": "compaction_completed"}), flush=True)
    after_schema = schema({
        "original_ref": {"type": "string"}, "ref_ok": {"type": "boolean"},
        "ref_result_ref": {"type": "string"}, "ref_details": {"type": "string"},
        "url_ok": {"type": "boolean"}, "url_result_ref": {"type": "string"},
        "url_details": {"type": "string"},
    })
    report["after"] = run_turn(thread_id,
        "Continue the read-only reference test. The original reference is "
        + json.dumps(original_ref) + ". Your FIRST tool call must open that "
        "exact ref using web.run and exactly one open operation. Do not search or substitute "
        "a URL. Then make a SEPARATE web call opening https://www.python.org/ as a control. "
        "Use no other tools or agents. Return the required JSON: actual refs, page titles or "
        "exact errors, with ref_ok/url_ok true only for real Python.org content. The ref was "
        "supplied explicitly so the test does not depend on remembering it.", after_schema)
    metadata["status"] = "completed"
    print(json.dumps({"variant": variant, "stage": "result", **report["after"]["result"]}), flush=True)
except Exception as exc:
    metadata["status"] = "failed"
    metadata["error"] = str(exc) or type(exc).__name__
    print(json.dumps({"variant": variant, "error": metadata["error"]}), flush=True)
finally:
    (run_dir / "report.json").write_text(json.dumps(report, indent=2))
    process.stdin.close()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    metadata["process_exit_code"] = process.returncode
    metadata["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (run_dir / "run.json").write_text(json.dumps(metadata, indent=2))
    transcript.close()
    errors.close()
