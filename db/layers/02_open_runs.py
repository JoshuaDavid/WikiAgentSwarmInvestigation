"""Open one analysis_run per registered analysis for this build.

The run version is 'build:<git_sha>' when git_sha is available, else
'build:<build_started_at>'. Stashes {analysis_name: run_id} in ctx for
downstream layers.
"""
from __future__ import annotations
import sqlite3


def run(conn: sqlite3.Connection, ctx: dict) -> None:
    cfg = ctx["cfg"]
    git_sha = ctx.get("git_sha")
    started = ctx["build_started_at"]
    version = f"build:{git_sha}" if git_sha else f"build:{started}"

    run_ids: dict[str, int] = {}
    for a in cfg.ANALYSES:
        analysis_id = conn.execute(
            "SELECT id FROM analysis WHERE name = ?", (a["name"],)
        ).fetchone()[0]
        row = conn.execute(
            "SELECT id FROM analysis_run WHERE analysis_id = ? AND version = ?",
            (analysis_id, version),
        ).fetchone()
        if row:
            run_ids[a["name"]] = row[0]
            continue
        cur = conn.execute(
            "INSERT INTO analysis_run "
            "(analysis_id, version, git_sha, run_at, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (analysis_id, version, git_sha, started, "auto-opened by build.py"),
        )
        run_ids[a["name"]] = cur.lastrowid

    ctx["analysis_run_id_by_name"] = run_ids
