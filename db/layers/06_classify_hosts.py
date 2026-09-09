"""Assign a host_category_classifier label to every host row.

Uses the classification rules from analyses/urls/classify.py to keep the DB
consistent with the standalone URL analysis.
"""
from __future__ import annotations
import importlib.util
import sqlite3
import sys
from pathlib import Path


def _load_classifier():
    """Import analyses/urls/classify.py without executing its __main__ block."""
    repo_root = Path(__file__).resolve().parents[2]
    p = repo_root / "analyses" / "urls" / "classify.py"
    spec = importlib.util.spec_from_file_location("_classify", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def run(conn: sqlite3.Connection, ctx: dict) -> None:
    run_id = ctx["analysis_run_id_by_name"]["host_category_classifier"]
    analysis_id = conn.execute(
        "SELECT analysis_id FROM analysis_run WHERE id = ?", (run_id,)
    ).fetchone()[0]

    # Pre-cache label_kind lookups so we bail fast if the classifier ever
    # emits a category not registered in build_config.
    kind_ids = dict(conn.execute(
        "SELECT name, id FROM analysis_label_kind WHERE analysis_id = ?",
        (analysis_id,),
    ).fetchall())

    classify = _load_classifier()

    hosts = conn.execute("SELECT id, name FROM host ORDER BY id").fetchall()
    n = 0
    for host_id, name in hosts:
        decoded = classify.decode_host(name)
        cat = classify.category_from_decoded(decoded, name)
        if cat not in kind_ids:
            raise RuntimeError(
                f"classifier produced unregistered category {cat!r} for host {name!r} "
                "— add it to build_config.ANALYSES['host_category_classifier']['kinds']"
            )
        conn.execute(
            "INSERT INTO analysis_label "
            "(analysis_run_id, analysis_label_kind_id, subject_tbl, subject_id, "
            " confidence, evidence_notes) "
            "VALUES (?, ?, 'host', ?, NULL, NULL)",
            (run_id, kind_ids[cat], host_id),
        )
        n += 1
    print(f"  classified {n} hosts")
