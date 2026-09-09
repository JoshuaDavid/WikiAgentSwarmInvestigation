"""Seed the analysis registry: one row per registered analysis, plus its label
kinds. Idempotent — re-runs are no-ops."""
from __future__ import annotations
import sqlite3


def run(conn: sqlite3.Connection, ctx: dict) -> None:
    cfg = ctx["cfg"]
    for a in cfg.ANALYSES:
        cur = conn.execute(
            "INSERT OR IGNORE INTO analysis (name, description) VALUES (?, ?)",
            (a["name"], a["description"]),
        )
        analysis_id = conn.execute(
            "SELECT id FROM analysis WHERE name = ?", (a["name"],)
        ).fetchone()[0]
        for k in a["kinds"]:
            conn.execute(
                "INSERT OR IGNORE INTO analysis_label_kind "
                "(analysis_id, name, description) VALUES (?, ?, ?)",
                (analysis_id, k, None),
            )
