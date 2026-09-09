"""Insert the known venues from build_config.KNOWN_VENUES.

Idempotent — INSERT OR IGNORE on the UNIQUE(name) constraint.
"""
from __future__ import annotations
import sqlite3


def run(conn: sqlite3.Connection, ctx: dict) -> None:
    cfg = ctx["cfg"]
    for v in cfg.KNOWN_VENUES:
        conn.execute(
            "INSERT OR IGNORE INTO venue (name, kind, base_domain) "
            "VALUES (?, ?, ?)",
            (v["name"], v["kind"], v["base_domain"]),
        )
