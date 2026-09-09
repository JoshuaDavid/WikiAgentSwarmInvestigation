"""Import raw revision + page + label + manifest data from every enabled source
in build_config.SOURCES.

Produces domain rows (venue → document → post + body + handle) plus a full
import_row_provenance trail so any post traces back to its JSONL line.

Deterministic ordering:
  * Sources iterated in build_config.SOURCES order.
  * Within a source, rows sorted by (name, seq) before insert.
  * Bodies deduped globally by sha256.
"""
from __future__ import annotations
import base64
import hashlib
import json
import sqlite3
from pathlib import Path


def _decode_body(body_str: str, encoding: str) -> bytes:
    if encoding in ("ascii", "utf8", "latin1"):
        try:
            return base64.b64decode(body_str)
        except Exception:
            return body_str.encode("utf-8", errors="replace")
    return body_str.encode("utf-8", errors="replace")


def _upsert_body(conn: sqlite3.Connection, raw: bytes,
                 body_cache: dict[str, int]) -> int:
    sha = hashlib.sha256(raw).hexdigest()
    if sha in body_cache:
        return body_cache[sha]
    row = conn.execute("SELECT id FROM body WHERE sha256 = ?", (sha,)).fetchone()
    if row:
        body_cache[sha] = row[0]
        return row[0]
    cur = conn.execute(
        "INSERT INTO body (sha256, byte_len, content_bytes) VALUES (?, ?, ?)",
        (sha, len(raw), raw),
    )
    body_cache[sha] = cur.lastrowid
    return cur.lastrowid


def _venue_id(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT id FROM venue WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise RuntimeError(f"venue not seeded: {name!r} — add to KNOWN_VENUES")
    return row[0]


def _upsert_handle(conn: sqlite3.Connection, name_str: str, venue_id: int,
                   handle_cache: dict[tuple[str, int], int]) -> int:
    key = (name_str, venue_id)
    if key in handle_cache:
        return handle_cache[key]
    row = conn.execute(
        "SELECT id FROM handle WHERE name_str = ? AND venue_id = ? "
        "AND disambiguation_notes IS NULL",
        (name_str, venue_id),
    ).fetchone()
    if row:
        handle_cache[key] = row[0]
        return row[0]
    cur = conn.execute(
        "INSERT INTO handle (name_str, venue_id, actor_id, disambiguation_notes) "
        "VALUES (?, ?, NULL, NULL)",
        (name_str, venue_id),
    )
    handle_cache[key] = cur.lastrowid
    return cur.lastrowid


def _upsert_document(conn: sqlite3.Connection, venue_id: int,
                     canonical_name: str,
                     doc_cache: dict[tuple[int, str], int]) -> int:
    key = (venue_id, canonical_name)
    if key in doc_cache:
        return doc_cache[key]
    row = conn.execute(
        "SELECT id FROM document WHERE venue_id = ? AND canonical_name = ?",
        (venue_id, canonical_name),
    ).fetchone()
    if row:
        doc_cache[key] = row[0]
        return row[0]
    cur = conn.execute(
        "INSERT INTO document (venue_id, canonical_name) VALUES (?, ?)",
        (venue_id, canonical_name),
    )
    doc_cache[key] = cur.lastrowid
    return cur.lastrowid


def _record_provenance(conn: sqlite3.Connection, subject_tbl: str,
                       subject_id: int, batch_id: int, source_file: str,
                       line_no: int) -> None:
    conn.execute(
        "INSERT INTO import_row_provenance "
        "(subject_tbl, subject_id, import_batch_id, source_file, source_line_no) "
        "VALUES (?, ?, ?, ?, ?)",
        (subject_tbl, subject_id, batch_id, source_file, line_no),
    )


def _import_source(conn: sqlite3.Connection, ctx: dict, src: dict) -> None:
    cfg = ctx["cfg"]
    src_dir = cfg.AGENT_LOGS / src["dir"]
    revs_path = src_dir / "revisions.jsonl"
    if not revs_path.exists():
        print(f"  (no revisions.jsonl in {src['dir']}; skipping)")
        return

    # One import_batch per source per build.
    cur = conn.execute(
        "INSERT INTO import_batch "
        "(source_dir, tool_version, imported_at, row_counts_json, notes) "
        "VALUES (?, ?, ?, NULL, NULL)",
        (str(src_dir.relative_to(cfg.REPO_ROOT)),
         "build.py",
         ctx["build_started_at"]),
    )
    batch_id = cur.lastrowid

    # Store manifest.json and SHA256SUMS if present.
    manifest = src_dir / "manifest.json"
    if manifest.exists():
        conn.execute(
            "INSERT INTO raw_manifest "
            "(import_batch_id, filename, content_json) VALUES (?, ?, ?)",
            (batch_id, "manifest.json", manifest.read_text()),
        )
    sha256sums = src_dir / "SHA256SUMS"
    if sha256sums.exists():
        for line in sha256sums.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            digest, fname = parts
            conn.execute(
                "INSERT INTO raw_file_integrity "
                "(import_batch_id, filename, sha256) VALUES (?, ?, ?)",
                (batch_id, fname, digest),
            )

    # Load and sort rows for deterministic insertion.
    rows: list[tuple[int, dict]] = []
    with revs_path.open() as f:
        for line_no, line in enumerate(f, start=1):
            rows.append((line_no, json.loads(line)))
    rows.sort(key=lambda t: (t[1].get("name") or "", t[1].get("seq") or 0,
                              t[1].get("rev_id") or ""))

    # Per-source caches to avoid re-querying.
    body_cache: dict[str, int] = {}
    doc_cache: dict[tuple[int, str], int] = {}
    handle_cache: dict[tuple[str, int], int] = {}

    # Default venue for the source.
    default_venue_id = None
    if src["venue_name"]:
        default_venue_id = _venue_id(conn, src["venue_name"])

    for line_no, rev in rows:
        # Venue: per-row `wiki` field when the source spans multiple venues.
        venue_name = src["venue_name"] or rev.get("wiki")
        if not venue_name:
            raise RuntimeError(
                f"{src['dir']} line {line_no}: no venue name available"
            )
        venue_id = default_venue_id or _venue_id(conn, venue_name)

        doc_id = _upsert_document(conn, venue_id, rev.get("name") or "", doc_cache)

        label = rev.get("label") or ""
        handle_id = _upsert_handle(conn, label, venue_id, handle_cache)

        raw_body = _decode_body(rev.get("body") or "", rev.get("body_encoding") or "raw_utf8")
        body_id = _upsert_body(conn, raw_body, body_cache)

        cur = conn.execute(
            "INSERT INTO post "
            "(document_id, handle_id, network_block_id, body_id, sequence_no, "
            " previous_post_id, posted_at, posted_at_grade, "
            " posted_at_source_clock, uncertainty_seconds, change_summary) "
            "VALUES (?, ?, NULL, ?, ?, NULL, ?, ?, ?, ?, ?)",
            (doc_id, handle_id, body_id, rev.get("seq") or 1,
             rev.get("time"), rev.get("time_grade"),
             rev.get("winning_clock"), rev.get("uncertainty_seconds"),
             rev.get("change_summary")),
        )
        post_id = cur.lastrowid

        # Wiki-side details (only present on wiki-farm sources).
        if src["kind"] in ("wiki_farm", "wiki"):
            conn.execute(
                "INSERT INTO wiki_post_details "
                "(post_id, revision_id_str, rcs_revision_number, "
                " is_new_page, is_minor_edit, write_date, request_time, "
                " success_time, recent_changes_time, "
                " related_moderation_id, related_kind) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)",
                (post_id, rev.get("rev_id"), rev.get("rcs_rev"),
                 int(bool(rev.get("is_new_page"))) if rev.get("is_new_page") is not None else None,
                 int(bool(rev.get("is_minor_edit"))) if rev.get("is_minor_edit") is not None else None,
                 rev.get("write_date"), rev.get("request_time"),
                 rev.get("success_time"), rev.get("recent_changes_time"),
                 rev.get("relation_type")),
            )

        # Shellac paste-detail fields (present on shellac-imported sources).
        if rev.get("shellac_doc_id") is not None:
            conn.execute(
                "INSERT INTO paste_post_details "
                "(post_id, archived_at, shellac_doc_id, shellac_source_type, "
                " shellac_source_group, shellac_source_url, shellac_title, "
                " shellac_occurrences, shellac_timestamp_basis) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (post_id, rev.get("archived_at"), rev.get("shellac_doc_id"),
                 rev.get("shellac_source_type"), rev.get("shellac_source_group"),
                 rev.get("shellac_source_url"), rev.get("shellac_title"),
                 rev.get("shellac_occurrences"),
                 rev.get("shellac_timestamp_basis")),
            )

        # capture: one row per post recording how we got the bytes.
        method = "shellac_pack" if rev.get("shellac_doc_id") else "wiki_export"
        conn.execute(
            "INSERT INTO capture (post_id, method, captured_at, source_url, "
            "wayback_timestamp, wayback_url, importer_pack_id, notes) "
            "VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL)",
            (post_id, method,
             rev.get("archived_at"),
             rev.get("shellac_source_url")),
        )

        _record_provenance(conn, "post", post_id, batch_id,
                            f"{src['dir']}/revisions.jsonl", line_no)


def run(conn: sqlite3.Connection, ctx: dict) -> None:
    cfg = ctx["cfg"]
    for src in cfg.SOURCES:
        if not src.get("enabled"):
            continue
        print(f"  importing {src['dir']}")
        _import_source(conn, ctx, src)
