#!/bin/sh
set -eu
repo_root=$(git rev-parse --show-toplevel)
log_path="$repo_root/.codex/hook-web-agent-test/raw-hook-events.jsonl"
sed -n '1,$p' >> "$log_path"
printf '\n' >> "$log_path"
