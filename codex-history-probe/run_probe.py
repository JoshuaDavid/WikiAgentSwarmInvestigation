import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tomllib

base = Path(__file__).resolve().parent
version = sys.argv[1]
variant = sys.argv[2] if len(sys.argv) > 2 else None
run_dir = base / version / variant if variant else base / version
prompt_path = base / (sys.argv[3] if len(sys.argv) > 3 else "prompt.txt")
probe_home = run_dir / "home"
config = tomllib.loads((probe_home / "config.toml").read_text())
child_env = os.environ.copy()
child_env["CODEX_HOME"] = str(probe_home)
command = [
    str(base / version / "codex"), "exec", "--skip-git-repo-check",
    "--ignore-rules", "--color", "never", "--json",
    "--cd", str(base / "workdir"),
    "--output-last-message", str(run_dir / "report.txt"), "-",
]
metadata = {
    "version": version,
    "variant": variant or "v2",
    "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "command": command,
    "model": config.get("model"),
    "web_search": config.get("web_search"),
    "standalone_web_search": config.get("features", {}).get("standalone_web_search", False),
    "update_plan_enabled": config.get("tools", {}).get("update_plan", {}).get("enabled"),
    "prompt_file": str(prompt_path),
}
(run_dir / "run.json").write_text(json.dumps(metadata, indent=2))
with prompt_path.open("rb") as prompt, \
     (run_dir / "events.jsonl").open("wb") as output, \
     (run_dir / "stderr.log").open("wb") as errors:
    process = subprocess.Popen(command, env=child_env, stdin=prompt,
                               stdout=output, stderr=errors)
    print(json.dumps({"version": version, "pid": process.pid,
                      "status": "started"}), flush=True)
    try:
        metadata["exit_code"] = process.wait(timeout=720)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        metadata["exit_code"] = process.returncode
        metadata["timed_out"] = True
metadata["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
(run_dir / "run.json").write_text(json.dumps(metadata, indent=2))
print(json.dumps(metadata), flush=True)
