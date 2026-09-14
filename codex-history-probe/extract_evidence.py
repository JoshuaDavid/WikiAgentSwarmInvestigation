"""Extract experiment events without copying credentials or instruction catalogs."""

import json
from pathlib import Path
import sys

base = Path(__file__).resolve().parent
for version in sys.argv[1:] or ["0.129.0-alpha.10", "0.129.0-alpha.12"]:
    version_dir = base / version
    run_dirs = [version_dir] + sorted(p for p in version_dir.iterdir() if p.is_dir())
    for run_dir in run_dirs:
        if not (run_dir / "home").is_dir():
            continue
        records = []
        for path in sorted((run_dir / "home/sessions").rglob("*.jsonl")):
            for line_number, line in enumerate(path.read_text().splitlines(), 1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = row.get("payload", {})
                outer_type = row.get("type")
                inner_type = payload.get("type")
                if outer_type == "session_meta":
                    payload = {key: payload[key] for key in [
                        "id", "timestamp", "cli_version", "source", "model_provider"
                    ] if key in payload}
                elif outer_type == "compacted":
                    payload = {"replacement_history_items": len(payload.get("replacement_history") or [])}
                elif outer_type == "response_item" and inner_type in {
                    "web_search_call", "function_call", "function_call_output"
                }:
                    pass
                elif outer_type == "event_msg" and inner_type in {
                    "agent_message", "web_search_end", "task_complete", "error"
                }:
                    pass
                else:
                    continue
                records.append({
                    "source": str(path.relative_to(base)),
                    "line": line_number,
                    "timestamp": row.get("timestamp"),
                    "type": outer_type,
                    "payload": payload,
                })
        (run_dir / "evidence.json").write_text(json.dumps(records, indent=2))
        print(str(run_dir.relative_to(base)), len(records), "evidence records")
