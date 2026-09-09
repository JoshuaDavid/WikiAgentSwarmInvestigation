#!/usr/bin/env bash
# Rebuild the DB twice; the two output files must be byte-identical.
# Exits 0 on success, 1 on any mismatch.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

TMP1="$(mktemp)"
TMP2="$(mktemp)"
trap 'rm -f "$TMP1" "$TMP2"' EXIT

python3 db/build.py --clean --db "$TMP1" > /dev/null 2>&1
python3 db/build.py --clean --db "$TMP2" > /dev/null 2>&1

H1="$(sha256sum "$TMP1" | cut -d' ' -f1)"
H2="$(sha256sum "$TMP2" | cut -d' ' -f1)"

if [ "$H1" != "$H2" ]; then
    echo "FAIL: build produced different bytes on two runs"
    echo "  run 1: $H1"
    echo "  run 2: $H2"
    exit 1
fi

echo "OK: builds are byte-identical ($H1)"
