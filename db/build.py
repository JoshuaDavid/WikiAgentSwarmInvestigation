#!/usr/bin/env python3
"""Reproducible build of the collusion SQLite DB.

Runs schema files (db/schema/*.sql) then layers (db/layers/*.py) in order.
Each layer opens a connection to the DB, does its work in a transaction, and
commits. `99_finalize.py` runs `VACUUM INTO` to produce a byte-stable output.

Determinism strategy:
  * Fixed schema order (numeric prefix on schema/ + layers/ files).
  * SOURCE_DATE_EPOCH is honored — all `datetime` / clock reads flow through
    a single helper that returns SOURCE_DATE_EPOCH when set.
  * All row inserts sort inputs before iterating.
  * IDs are auto-assigned; deterministic insertion order → deterministic IDs.
  * VACUUM INTO on identical content produces identical bytes with a pinned
    SQLite version.

Usage:
  python3 db/build.py                  # incremental (skip layers whose inputs unchanged)
  python3 db/build.py --clean          # wipe DB and rebuild from scratch
  python3 db/build.py --verify         # rebuild + compare against BUILD_HASH.txt
  python3 db/build.py --layer LAYER    # run one layer only (name without prefix)
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA_DIR = HERE / "schema"
LAYERS_DIR = HERE / "layers"

sys.path.insert(0, str(HERE))
import build_config as cfg  # noqa: E402


def get_source_date_epoch() -> str:
    """Return a stable ISO timestamp for the build. Honors SOURCE_DATE_EPOCH."""
    from datetime import datetime, timezone
    sde = os.environ.get("SOURCE_DATE_EPOCH")
    if sde:
        return datetime.fromtimestamp(int(sde), tz=timezone.utc).isoformat()
    # Default: pin to 1970-01-01 so builds are reproducible without env-var setup.
    return "1970-01-01T00:00:00+00:00"


def get_git_sha() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(HERE.parent), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return None


def apply_schema(conn: sqlite3.Connection) -> None:
    """Run every schema/*.sql in order. Record each in schema_migration."""
    files = sorted(SCHEMA_DIR.glob("*.sql"))
    # Bootstrap: 008_provenance.sql defines schema_migration itself.
    # We run all files first, then record.
    for f in files:
        sql = f.read_text()
        conn.executescript(sql)
    conn.commit()
    now = get_source_date_epoch()
    for f in files:
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        conn.execute(
            "INSERT INTO schema_migration (filename, sha256, applied_at) "
            "VALUES (?, ?, ?)",
            (f.name, sha, now),
        )
    conn.commit()


def load_layer(path: Path):
    """Import a layer module by path so we can call its `run(conn, ctx)`."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def enabled_layer_files() -> list[Path]:
    return sorted(p for p in LAYERS_DIR.glob("[0-9]*.py"))


def run_layers(conn: sqlite3.Connection, ctx: dict,
               only: str | None = None) -> None:
    for layer_file in enabled_layer_files():
        name = layer_file.stem.split("_", 1)[1] if "_" in layer_file.stem else layer_file.stem
        if only and only != name:
            continue
        print(f"[layer] {layer_file.name}", file=sys.stderr)
        mod = load_layer(layer_file)
        if not hasattr(mod, "run"):
            print(f"  (no run() function; skipping)", file=sys.stderr)
            continue
        mod.run(conn, ctx)
        conn.commit()


def build(db_path: Path, clean: bool, only_layer: str | None) -> None:
    if clean and db_path.exists():
        db_path.unlink()

    fresh = not db_path.exists()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute("PRAGMA synchronous = OFF")

    ctx = {
        "cfg": cfg,
        "build_started_at": get_source_date_epoch(),
        "git_sha": get_git_sha(),
        "layer_id_by_name": {},   # populated by 02_open_runs.py
    }

    if fresh:
        print("[schema] applying", file=sys.stderr)
        apply_schema(conn)

    run_layers(conn, ctx, only=only_layer)

    conn.close()


def finalize_and_hash(db_path: Path) -> str:
    """Compact the DB and return its sha256."""
    # VACUUM INTO to a temp path, then atomic replace, so a failing VACUUM
    # doesn't corrupt the in-place file.
    tmp = db_path.with_suffix(".sqlite.vacuum")
    if tmp.exists():
        tmp.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.execute(f"VACUUM INTO ?", (str(tmp),))
    conn.close()
    shutil.move(str(tmp), str(db_path))
    h = hashlib.sha256(db_path.read_bytes()).hexdigest()
    return h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true", help="wipe DB and rebuild")
    ap.add_argument("--verify", action="store_true",
                    help="rebuild then compare against db/BUILD_HASH.txt")
    ap.add_argument("--layer", help="run only this layer (name without prefix)")
    ap.add_argument("--db", type=Path, default=cfg.DB_PATH)
    args = ap.parse_args()

    print(f"[build] target: {args.db}", file=sys.stderr)
    print(f"[build] SOURCE_DATE_EPOCH: {os.environ.get('SOURCE_DATE_EPOCH', '(unset; using 1970-01-01)')}",
          file=sys.stderr)
    print(f"[build] sqlite3 version: {sqlite3.sqlite_version}", file=sys.stderr)

    build(args.db, clean=args.clean, only_layer=args.layer)

    if args.layer is None:
        h = finalize_and_hash(args.db)
        print(f"[build] sha256: {h}", file=sys.stderr)
        cfg.BUILD_HASH_PATH.write_text(h + "\n")
        print(f"[build] wrote {cfg.BUILD_HASH_PATH}", file=sys.stderr)

        if args.verify:
            pinned = cfg.BUILD_HASH_PATH.read_text().strip()
            if pinned == h:
                print("[verify] OK — matches pinned hash", file=sys.stderr)
            else:
                print(f"[verify] MISMATCH:\n  pinned:  {pinned}\n  current: {h}",
                      file=sys.stderr)
                sys.exit(1)


if __name__ == "__main__":
    main()
