#!/usr/bin/env python3
"""Aggregate wiki access logs into per-bucket, per-wiki request counts
within an inclusive UTC date window.

Input:  tmp/wiki-access-logs/<wiki>/log_YYMM  (as in build.py)
Output: outputs/bucketed_by_wiki_<start>_<end>_<mins>min.tsv
        Columns: bucket  wiki  count
        Bucket label = "YYYY-MM-DD HH" for --bucket-minutes 60, otherwise
        "YYYY-MM-DD HH:MM" aligned to the bucket start.

--bucket-minutes must evenly divide 60 or be a whole-hour multiple.
Default window: 2026-06-13 through 2026-06-20 inclusive; default bucket 60.
"""
from __future__ import annotations
import argparse
import calendar
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
LOG_ROOT = REPO / "tmp" / "wiki-access-logs"
OUT_DIR = Path(__file__).resolve().parent / "outputs"


def iter_timestamps(path: Path):
    with path.open("rb") as f:
        for raw in f:
            i = raw.rfind(b"|TS|")
            if i < 0:
                continue
            try:
                yield int(raw[i + 4:].strip())
            except ValueError:
                continue


def parse_iso(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def logfiles_covering(wiki_dir: Path, start: datetime, end_exclusive: datetime):
    """Log files are named log_YYMM. Return the subset whose month overlaps
    the window [start, end_exclusive)."""
    keep: list[Path] = []
    for p in sorted(wiki_dir.glob("log_*")):
        try:
            yymm = p.name.split("_")[1]
            year = 2000 + int(yymm[:2])
            mon = int(yymm[2:])
        except (IndexError, ValueError):
            continue
        m_start = datetime(year, mon, 1, tzinfo=timezone.utc)
        last_day = calendar.monthrange(year, mon)[1]
        m_end = datetime(year, mon, last_day, 23, 59, 59, tzinfo=timezone.utc)
        if m_end < start or m_start >= end_exclusive:
            continue
        keep.append(p)
    return keep


def bucket_label(ts: int, bucket_secs: int) -> str:
    aligned = (ts // bucket_secs) * bucket_secs
    dt = datetime.fromtimestamp(aligned, tz=timezone.utc)
    if bucket_secs % 3600 == 0:
        return dt.strftime("%Y-%m-%d %H")
    return dt.strftime("%Y-%m-%d %H:%M")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-06-13", help="inclusive UTC date")
    ap.add_argument("--end", default="2026-06-20", help="inclusive UTC date")
    ap.add_argument("--bucket-minutes", type=int, default=60,
                    help="bucket width in minutes; must divide 60 or be a "
                         "whole-hour multiple")
    args = ap.parse_args()

    bm = args.bucket_minutes
    if bm <= 0 or (bm < 60 and 60 % bm != 0) or (bm >= 60 and bm % 60 != 0):
        raise SystemExit(f"--bucket-minutes={bm} does not tile the day cleanly")
    bucket_secs = bm * 60

    start = parse_iso(args.start)
    end_incl = parse_iso(args.end)
    end_exclusive = datetime(end_incl.year, end_incl.month, end_incl.day,
                             23, 59, 59, tzinfo=timezone.utc)
    start_ts = int(start.timestamp())
    end_ts = int(end_exclusive.timestamp())

    counts: dict[tuple[str, str], int] = defaultdict(int)
    wikis = sorted(p.name for p in LOG_ROOT.iterdir() if p.is_dir())
    for wiki in wikis:
        wiki_dir = LOG_ROOT / wiki
        total = 0
        for logfile in logfiles_covering(wiki_dir, start, end_exclusive):
            for ts in iter_timestamps(logfile):
                if ts < start_ts or ts > end_ts:
                    continue
                bucket = bucket_label(ts, bucket_secs)
                counts[(bucket, wiki)] += 1
                total += 1
        print(f"{wiki}: {total:,} requests in window", file=sys.stderr)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"bucketed_by_wiki_{args.start}_{args.end}_{bm}min.tsv"
    with out.open("w") as f:
        f.write("bucket\twiki\tcount\n")
        for (h, wiki) in sorted(counts):
            f.write(f"{h}\t{wiki}\t{counts[(h, wiki)]}\n")
    print(f"wrote {out}  ({len(counts):,} rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
