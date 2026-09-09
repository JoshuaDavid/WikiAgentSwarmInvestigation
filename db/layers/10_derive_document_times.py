"""Populate document.first_seen_at and document.last_seen_at from evidence.

first_seen_at is the MIN of:
  * every post.posted_at on this document
  * shortener_document_details.created_at (for popcat-style shortener codes)

last_seen_at is the MAX of:
  * every post.posted_at
  * every capture.captured_at

Runs after all imports so it observes cross-source evidence in one pass.
Deterministic: pure SQL aggregates.
"""
from __future__ import annotations
import sqlite3


def run(conn: sqlite3.Connection, ctx: dict) -> None:
    # Materialize per-document min/max of every timestamp we have any evidence
    # of. Use IFNULL to fold in the shortener created_at when present.
    conn.executescript("""
    CREATE TEMP TABLE _doc_times AS
    WITH post_times AS (
        SELECT p.document_id AS doc_id,
               MIN(p.posted_at) AS min_post_at,
               MAX(p.posted_at) AS max_post_at
        FROM post p
        WHERE p.posted_at IS NOT NULL AND p.posted_at != ''
        GROUP BY p.document_id
    ),
    capture_times AS (
        SELECT p.document_id AS doc_id,
               MAX(c.captured_at) AS max_capture_at
        FROM capture c
        JOIN post p ON p.id = c.post_id
        WHERE c.captured_at IS NOT NULL AND c.captured_at != ''
        GROUP BY p.document_id
    ),
    shortener_created AS (
        SELECT document_id AS doc_id, created_at
        FROM shortener_document_details
        WHERE created_at IS NOT NULL AND created_at != ''
    )
    SELECT d.id AS doc_id,
           MIN(
               COALESCE(pt.min_post_at, '9999'),
               COALESCE(sc.created_at,  '9999')
           ) AS first_seen_at,
           MAX(
               COALESCE(pt.max_post_at,  ''),
               COALESCE(ct.max_capture_at, '')
           ) AS last_seen_at
    FROM document d
    LEFT JOIN post_times       pt ON pt.doc_id = d.id
    LEFT JOIN capture_times    ct ON ct.doc_id = d.id
    LEFT JOIN shortener_created sc ON sc.doc_id = d.id;
    """)

    # Filter out the sentinel values used inside MIN/MAX.
    conn.execute("""
        UPDATE document SET
            first_seen_at = (
                SELECT CASE WHEN first_seen_at = '9999' THEN NULL ELSE first_seen_at END
                FROM _doc_times WHERE doc_id = document.id
            ),
            last_seen_at = (
                SELECT CASE WHEN last_seen_at  = ''     THEN NULL ELSE last_seen_at  END
                FROM _doc_times WHERE doc_id = document.id
            )
        WHERE id IN (SELECT doc_id FROM _doc_times)
    """)

    conn.execute("DROP TABLE _doc_times")

    n_first = conn.execute(
        "SELECT COUNT(*) FROM document WHERE first_seen_at IS NOT NULL"
    ).fetchone()[0]
    n_last = conn.execute(
        "SELECT COUNT(*) FROM document WHERE last_seen_at IS NOT NULL"
    ).fetchone()[0]
    print(f"  populated first_seen_at on {n_first} documents, "
          f"last_seen_at on {n_last} documents")
