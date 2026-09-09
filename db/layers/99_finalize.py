"""Post-load housekeeping: ANALYZE for query planner, PRAGMA integrity_check.
VACUUM is done in build.py's finalize step (needs to be outside any transaction).
"""
from __future__ import annotations
import sqlite3


def run(conn: sqlite3.Connection, ctx: dict) -> None:
    conn.execute("ANALYZE")
    row = conn.execute("PRAGMA integrity_check").fetchone()
    if row and row[0] != "ok":
        raise RuntimeError(f"integrity_check failed: {row}")
    print("  integrity_check: ok")
