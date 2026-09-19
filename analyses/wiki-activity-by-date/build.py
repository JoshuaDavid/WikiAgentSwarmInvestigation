#!/usr/bin/env python3
"""Aggregate wiki access logs into per-day, per-wiki request counts.

Input:  tmp/wiki-access-logs/<wiki>/log_YYMM
        Each line has trailing "...|TS|<unix_seconds>". One line = one request.

Output: outputs/daily_by_wiki.tsv with columns: date  wiki  count
        (date is UTC YYYY-MM-DD; sorted by date then wiki.)
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
LOG_ROOT = REPO / "tmp" / "wiki-access-logs"
OUT = Path(__file__).resolve().parent / "outputs" / "daily_by_wiki.tsv"


def iter_timestamps(path: Path):
    """Yield unix timestamps from the trailing |TS|<int> field of every line."""
    # Log files are ISO-8859; encoding does not matter for the TS field, but
    # decode permissively so a stray high byte in a URL cannot kill the parse.
    with path.open("rb") as f:
        for raw in f:
            i = raw.rfind(b"|TS|")
            if i < 0:
                continue
            try:
                yield int(raw[i + 4:].strip())
            except ValueError:
                continue


def main() -> None:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    wikis = sorted(p.name for p in LOG_ROOT.iterdir() if p.is_dir())
    for wiki in wikis:
        wiki_dir = LOG_ROOT / wiki
        total = 0
        for logfile in sorted(wiki_dir.glob("log_*")):
            for ts in iter_timestamps(logfile):
                d = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
                counts[(d, wiki)] += 1
                total += 1
        print(f"{wiki}: {total:,} requests", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        f.write("date\twiki\tcount\n")
        for (d, wiki) in sorted(counts):
            f.write(f"{d}\t{wiki}\t{counts[(d, wiki)]}\n")
    print(f"wrote {OUT}  ({len(counts):,} rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
