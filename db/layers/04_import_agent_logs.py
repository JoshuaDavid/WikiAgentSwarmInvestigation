"""Import every enabled source from build_config.SOURCES into the domain
tables.

Idempotency: if a (document_id, sequence_no) post already exists (from a
prior source), we do NOT insert a second post — we insert a new `capture`
row pointing at the additional bytes source. Same paste captured through
shellac and through a per-site scrape yields one post with two captures.

Venue resolution:
  single_venue_*                  — use `src['venue_name']` for every row
  multi_venue_wiki_farm           — use each row's `wiki` field
  multi_venue_paste_aggregate     — map `name` prefix via NAME_PREFIX_TO_VENUE
  multi_venue_shortener_aggregate — same

Deterministic ordering: sources iterated in SOURCES order; rows within a
source sorted by (canonical_name, seq, rev_id); bodies deduped by sha256.
"""
from __future__ import annotations
import base64
import hashlib
import json
import re
import sqlite3
from pathlib import Path


# ------------- helpers ----------------------------------------------------

def _decode_body(body_str: str, encoding: str) -> bytes:
    """Recover the original bytes from a revisions.jsonl `body` field.

    prowiki uses `body_encoding` in {ascii, utf8, latin1} — the JSON string
    is produced by decoding the byte payload as latin-1, so encoding the
    string as latin-1 round-trips to the original bytes. Shellac-imported
    corpora use `raw_utf8`, meaning the JSON string is the text itself.
    """
    if encoding in ("ascii", "utf8", "latin1"):
        return body_str.encode("latin-1", errors="replace")
    return body_str.encode("utf-8", errors="replace")


def _bool_or_none(v):
    return int(bool(v)) if v is not None else None


class _Caches:
    """Per-build caches (populated on demand, safe across sources)."""
    def __init__(self):
        self.body: dict[str, int] = {}
        self.venue: dict[str, int] = {}
        self.doc: dict[tuple[int, str], int] = {}
        self.handle: dict[tuple[str, int], int] = {}
        self.network_block: dict[str, int] = {}


def _venue_id(conn, name: str, caches: _Caches) -> int:
    if name in caches.venue:
        return caches.venue[name]
    row = conn.execute("SELECT id FROM venue WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise RuntimeError(f"venue not seeded: {name!r} — add to KNOWN_VENUES")
    caches.venue[name] = row[0]
    return row[0]


def _upsert_body(conn, raw: bytes, caches: _Caches) -> int:
    sha = hashlib.sha256(raw).hexdigest()
    if sha in caches.body:
        return caches.body[sha]
    row = conn.execute("SELECT id FROM body WHERE sha256 = ?", (sha,)).fetchone()
    if row:
        caches.body[sha] = row[0]
        return row[0]
    cur = conn.execute(
        "INSERT INTO body (sha256, byte_len, content_bytes) VALUES (?, ?, ?)",
        (sha, len(raw), raw),
    )
    caches.body[sha] = cur.lastrowid
    return cur.lastrowid


def _upsert_handle(conn, name_str: str, venue_id: int, caches: _Caches) -> int:
    key = (name_str, venue_id)
    if key in caches.handle:
        return caches.handle[key]
    row = conn.execute(
        "SELECT id FROM handle WHERE name_str = ? AND venue_id = ? "
        "AND disambiguation_notes IS NULL",
        (name_str, venue_id),
    ).fetchone()
    if row:
        caches.handle[key] = row[0]
        return row[0]
    cur = conn.execute(
        "INSERT INTO handle (name_str, venue_id, actor_id, disambiguation_notes) "
        "VALUES (?, ?, NULL, NULL)",
        (name_str, venue_id),
    )
    caches.handle[key] = cur.lastrowid
    return cur.lastrowid


def _upsert_document(conn, venue_id: int, canonical_name: str,
                     caches: _Caches) -> int:
    key = (venue_id, canonical_name)
    if key in caches.doc:
        return caches.doc[key]
    row = conn.execute(
        "SELECT id FROM document WHERE venue_id = ? AND canonical_name = ?",
        (venue_id, canonical_name),
    ).fetchone()
    if row:
        caches.doc[key] = row[0]
        return row[0]
    cur = conn.execute(
        "INSERT INTO document (venue_id, canonical_name) VALUES (?, ?)",
        (venue_id, canonical_name),
    )
    caches.doc[key] = cur.lastrowid
    return cur.lastrowid


def _upsert_network_block(conn, cidr: str, caches: _Caches) -> int:
    if cidr in caches.network_block:
        return caches.network_block[cidr]
    row = conn.execute(
        "SELECT id FROM network_block WHERE cidr = ?", (cidr,)
    ).fetchone()
    if row:
        caches.network_block[cidr] = row[0]
        return row[0]
    cur = conn.execute(
        "INSERT INTO network_block (cidr) VALUES (?)", (cidr,)
    )
    caches.network_block[cidr] = cur.lastrowid
    return cur.lastrowid


def _record_provenance(conn, subject_tbl: str, subject_id: int,
                       batch_id: int, source_file: str, line_no: int) -> None:
    conn.execute(
        "INSERT INTO import_row_provenance "
        "(subject_tbl, subject_id, import_batch_id, source_file, source_line_no) "
        "VALUES (?, ?, ?, ?, ?)",
        (subject_tbl, subject_id, batch_id, source_file, line_no),
    )


_REF_KIND_RE = re.compile(r"(rclog|reqlog|attacklog)", re.I)


def _record_source_refs(conn, subject_tbl: str, subject_id: int,
                         refs: list[str]) -> None:
    """Split an exporter `source_refs` entry like
    `corpus/live/rclog.jsonl:131972` into ref_path + ref_lineno + ref_kind."""
    for s in refs:
        path, sep, lno = s.rpartition(":")
        if not sep or not lno.isdigit():
            path, lno = s, None
        else:
            lno = int(lno)
        m = _REF_KIND_RE.search(path or s)
        kind = m.group(1).lower() if m else "rclog"
        conn.execute(
            "INSERT INTO raw_source_ref "
            "(subject_tbl, subject_id, ref_kind, ref_path, ref_lineno) "
            "VALUES (?, ?, ?, ?, ?)",
            (subject_tbl, subject_id, kind, path or s, lno),
        )


def _capture_method_for(source_kind: str, rev: dict) -> str:
    if source_kind == "multi_venue_wiki_farm" or source_kind == "single_venue_wiki":
        return "wiki_export"
    if source_kind == "single_venue_shortener" and rev.get("wayback_timestamp"):
        return "wayback_snapshot"
    return "shellac_pack"


# ------------- venue resolution ------------------------------------------

def _resolve_venue_name(cfg, src: dict, rev: dict, line_no: int) -> str:
    kind = src["source_kind"]
    if kind in ("single_venue_wiki", "single_venue_paste_site",
                 "single_venue_shortener", "gem_registry"):
        return src["venue_name"]
    if kind == "multi_venue_wiki_farm":
        w = rev.get("wiki")
        if not w:
            raise RuntimeError(f"{src['dir']} line {line_no}: no wiki field")
        return w
    if kind in ("multi_venue_paste_aggregate",
                 "multi_venue_shortener_aggregate"):
        name = rev.get("name") or ""
        prefix = name.split("/", 1)[0] if "/" in name else name
        venue = cfg.NAME_PREFIX_TO_VENUE.get(prefix)
        if venue is None:
            raise RuntimeError(
                f"{src['dir']} line {line_no}: unknown name prefix {prefix!r} — "
                f"add to NAME_PREFIX_TO_VENUE"
            )
        return venue
    raise RuntimeError(f"unhandled source_kind: {kind}")


def _resolve_canonical_name(src: dict, rev: dict) -> str:
    """For multi-venue aggregates the name carries a `<venue-prefix>/<real-name>`
    shape; strip the prefix so the canonical_name matches what a per-site scrape
    stores.

    Special case: shorteners/popcat/* rows are shellac-BUNDLES — each `seq` is
    a distinct popcat code, not a version of one code. Extract the real code
    from the body (line 2 of the popcat-info format). Downstream we also force
    sequence_no=1 for those rows.
    """
    kind = src["source_kind"]
    name = rev.get("name") or ""
    if (kind == "multi_venue_shortener_aggregate"
            and name.startswith("popcat/")):
        body = rev.get("body") or ""
        lines = body.split("\n")
        code = lines[2].strip() if len(lines) >= 3 else ""
        if code:
            return code
        # Fall back to the shellac path if the body doesn't fit the format.
        return name.split("/", 1)[1] if "/" in name else name
    if kind in ("multi_venue_paste_aggregate",
                 "multi_venue_shortener_aggregate") and "/" in name:
        return name.split("/", 1)[1]
    return name


def _resolve_sequence_no(src: dict, rev: dict) -> int:
    """Override the row's `seq` for cases where the shellac bundling doesn't
    correspond to real versions. Popcat bundles: each row is a distinct
    document, so sequence_no is always 1."""
    name = rev.get("name") or ""
    if (src["source_kind"] == "multi_venue_shortener_aggregate"
            and name.startswith("popcat/")):
        return 1
    return rev.get("seq") or 1


# ------------- per-source import -----------------------------------------

def _load_and_sort_rows(path: Path) -> list[tuple[int, dict]]:
    rows: list[tuple[int, dict]] = []
    with path.open() as f:
        for line_no, line in enumerate(f, start=1):
            rows.append((line_no, json.loads(line)))
    rows.sort(key=lambda t: (t[1].get("name") or "",
                              t[1].get("seq") or 0,
                              t[1].get("rev_id") or ""))
    return rows


def _import_pages_jsonl(conn, cfg, src: dict, batch_id: int,
                        caches: _Caches) -> None:
    """Read pages.jsonl. Only wiki sources populate wiki_document_details.
    Aggregate paste/shortener sources still walk pages.jsonl to record the
    document + provenance, but do not fill in wiki-specific columns."""
    p = cfg.AGENT_LOGS / src["dir"] / "pages.jsonl"
    if not p.exists():
        return
    is_wiki_source = src["source_kind"] in ("multi_venue_wiki_farm",
                                              "single_venue_wiki")
    for line_no, line in enumerate(open(p), start=1):
        page = json.loads(line)
        # Reuse the revisions.jsonl venue resolver so aggregate sources get
        # per-row venues instead of the aggregate stub name.
        venue_name = _resolve_venue_name(cfg, src, page, line_no)
        venue_id = _venue_id(conn, venue_name, caches)
        canonical_name = _resolve_canonical_name(src, page)
        doc_id = _upsert_document(conn, venue_id, canonical_name, caches)

        if is_wiki_source:
            existing = conn.execute(
                "SELECT 1 FROM wiki_document_details WHERE document_id = ?",
                (doc_id,),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO wiki_document_details "
                    "(document_id, page_family, page_family_source, "
                    " page_family_confidence, page_family_method, bucket, "
                    " rcs_path, live_body_variant, head_differs_from_live) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (doc_id, page.get("page_family"),
                     page.get("page_family_source"),
                     page.get("page_family_confidence"),
                     page.get("page_family_method"),
                     page.get("bucket"), page.get("rcs_path"),
                     page.get("live_body_variant"),
                     _bool_or_none(page.get("head_differs_from_live"))),
                )
                _record_provenance(conn, "document", doc_id, batch_id,
                                    f"{src['dir']}/pages.jsonl", line_no)


_PROBE_WIKI_RE = re.compile(r"attacklog_raw_([a-z0-9]+)_\d+\.jsonl", re.I)


def _probe_venue_name(ev: dict) -> str | None:
    """Prowiki's probe rows have no `wiki` field. Extract the wiki name from
    the source_refs entry that points at an attacklog file
    (`attacklog_raw_<wiki>_YYMM.jsonl`)."""
    for s in ev.get("source_refs") or []:
        m = _PROBE_WIKI_RE.search(s)
        if m:
            return m.group(1)
    return None


def _import_events_jsonl(conn, cfg, src: dict, batch_id: int,
                          caches: _Caches) -> None:
    """Populate moderation_event + probe from events.jsonl for wiki sources.
    `save` events duplicate what revisions.jsonl already carries and are
    skipped."""
    p = cfg.AGENT_LOGS / src["dir"] / "events.jsonl"
    if not p.exists():
        return
    for line_no, line in enumerate(open(p), start=1):
        ev = json.loads(line)
        etype = ev.get("event_type")
        if etype not in ("delete", "revert", "probe"):
            continue

        if etype in ("delete", "revert"):
            venue_name = (src["venue_name"] or ev.get("wiki"))
            if not venue_name:
                continue
            venue_id = _venue_id(conn, venue_name, caches)
            # The exporter's field name for the page varies. prowiki uses
            # `page`; sister wikis may use `page_name` or `name`; some rows
            # only have `page_id` = `<wiki>/<page>`.
            page_name = (ev.get("page") or ev.get("page_name")
                          or ev.get("name")
                          or (ev.get("page_id") or "").split("/", 1)[-1])
            if not page_name:
                continue
            doc_id = _upsert_document(conn, venue_id, page_name, caches)
            actor_label = ev.get("actor_label")
            handle_id = None
            if actor_label is not None:
                handle_id = _upsert_handle(conn, actor_label, venue_id, caches)
            network_block_id = None
            ip16 = ev.get("ip16")
            if ip16:
                network_block_id = _upsert_network_block(conn, ip16, caches)
            cur = conn.execute(
                "INSERT INTO moderation_event "
                "(document_id, admin_handle_id, network_block_id, kind, "
                " requested_at, succeeded_at, rclog_at, change_summary, "
                " was_page_held) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (doc_id, handle_id, network_block_id, etype,
                 ev.get("request_time"), ev.get("success_time"),
                 ev.get("rclog_time") or ev.get("rcs_date"),
                 ev.get("change_summary"),
                 _bool_or_none(ev.get("page_held"))),
            )
            _record_source_refs(conn, "moderation_event", cur.lastrowid,
                                 ev.get("source_refs") or [])
            _record_provenance(conn, "moderation_event", cur.lastrowid,
                                batch_id, f"{src['dir']}/events.jsonl", line_no)

        elif etype == "probe":
            venue_name = _probe_venue_name(ev) or ev.get("wiki") or src["venue_name"]
            if not venue_name:
                continue
            venue_id = _venue_id(conn, venue_name, caches)
            network_block_id = None
            ip16 = ev.get("ip16")
            if ip16:
                network_block_id = _upsert_network_block(conn, ip16, caches)
            cur = conn.execute(
                "INSERT INTO probe "
                "(venue_id, network_block_id, param_family, request_action, "
                " requested_at) VALUES (?, ?, ?, ?, ?)",
                (venue_id, network_block_id, ev.get("param_family"),
                 ev.get("request_action"), ev.get("request_time")),
            )
            _record_source_refs(conn, "probe", cur.lastrowid,
                                 ev.get("source_refs") or [])
            _record_provenance(conn, "probe", cur.lastrowid, batch_id,
                                f"{src['dir']}/events.jsonl", line_no)


def _import_source(conn: sqlite3.Connection, ctx: dict, src: dict,
                    caches: _Caches) -> None:
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
         "build.py", ctx["build_started_at"]),
    )
    batch_id = cur.lastrowid

    # Manifest + integrity.
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

    # Pages first (wiki_document_details), then revisions (posts).
    _import_pages_jsonl(conn, cfg, src, batch_id, caches)

    n_posts = n_captures_only = 0
    for line_no, rev in _load_and_sort_rows(revs_path):
        venue_name = _resolve_venue_name(cfg, src, rev, line_no)
        venue_id = _venue_id(conn, venue_name, caches)
        canonical_name = _resolve_canonical_name(src, rev)
        doc_id = _upsert_document(conn, venue_id, canonical_name, caches)

        raw_body = _decode_body(rev.get("body") or "",
                                 rev.get("body_encoding") or "raw_utf8")
        body_id = _upsert_body(conn, raw_body, caches)

        seq = _resolve_sequence_no(src, rev)

        # Idempotency: if this document already has a post at this seq, add
        # only a capture row.
        existing = conn.execute(
            "SELECT id FROM post WHERE document_id = ? AND sequence_no = ?",
            (doc_id, seq),
        ).fetchone()

        if existing:
            post_id = existing[0]
            n_captures_only += 1
        else:
            label = rev.get("label") or ""
            handle_id = _upsert_handle(conn, label, venue_id, caches)
            network_block_id = None
            if rev.get("ip16"):
                network_block_id = _upsert_network_block(conn, rev["ip16"], caches)
            cur = conn.execute(
                "INSERT INTO post "
                "(document_id, handle_id, network_block_id, body_id, sequence_no, "
                " previous_post_id, posted_at, posted_at_grade, "
                " posted_at_source_clock, uncertainty_seconds, change_summary) "
                "VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)",
                (doc_id, handle_id, network_block_id, body_id, seq,
                 rev.get("time"), rev.get("time_grade"),
                 rev.get("winning_clock"), rev.get("uncertainty_seconds"),
                 rev.get("change_summary")),
            )
            post_id = cur.lastrowid
            n_posts += 1

            # Wiki-side details (only present on wiki-shaped sources).
            if src["source_kind"] in ("multi_venue_wiki_farm",
                                       "single_venue_wiki"):
                conn.execute(
                    "INSERT INTO wiki_post_details "
                    "(post_id, revision_id_str, rcs_revision_number, "
                    " is_new_page, is_minor_edit, write_date, request_time, "
                    " success_time, recent_changes_time, "
                    " related_moderation_id, related_kind) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)",
                    (post_id, rev.get("rev_id"), rev.get("rcs_rev"),
                     _bool_or_none(rev.get("is_new_page")),
                     _bool_or_none(rev.get("is_minor_edit")),
                     rev.get("write_date"), rev.get("request_time"),
                     rev.get("success_time"), rev.get("recent_changes_time"),
                     rev.get("relation_type")),
                )

            # Paste-side (shellac-imported) details.
            if rev.get("shellac_doc_id") is not None:
                conn.execute(
                    "INSERT INTO paste_post_details "
                    "(post_id, archived_at, shellac_doc_id, shellac_source_type, "
                    " shellac_source_group, shellac_source_url, shellac_title, "
                    " shellac_occurrences, shellac_timestamp_basis) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (post_id, rev.get("archived_at"), rev.get("shellac_doc_id"),
                     rev.get("shellac_source_type"),
                     rev.get("shellac_source_group"),
                     rev.get("shellac_source_url"), rev.get("shellac_title"),
                     rev.get("shellac_occurrences"),
                     rev.get("shellac_timestamp_basis")),
                )

            # Shortener-document details (properties of the shortener code
            # itself, not any single retrieval).
            if src["source_kind"] == "single_venue_shortener" and (
                    rev.get("popcat_created_date")
                    or rev.get("popcat_days_active")
                    or rev.get("popcat_total_views")
                    or rev.get("popcat_redirects_to")):
                exists = conn.execute(
                    "SELECT 1 FROM shortener_document_details WHERE document_id = ?",
                    (doc_id,),
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO shortener_document_details "
                        "(document_id, created_at, days_active, total_views, "
                        " current_redirects_to) VALUES (?, ?, ?, ?, ?)",
                        (doc_id, rev.get("popcat_created_date"),
                         rev.get("popcat_days_active"),
                         rev.get("popcat_total_views"),
                         rev.get("popcat_redirects_to")),
                    )

            _record_provenance(conn, "post", post_id, batch_id,
                                f"{src['dir']}/revisions.jsonl", line_no)

        # One capture per import for this post, always inserted (post may be
        # new or pre-existing).
        method = _capture_method_for(src["source_kind"], rev)
        conn.execute(
            "INSERT INTO capture "
            "(post_id, method, captured_at, source_url, wayback_timestamp, "
            " wayback_url, importer_pack_id, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (post_id, method, rev.get("archived_at"),
             rev.get("shellac_source_url"),
             rev.get("wayback_timestamp"), rev.get("wayback_url"),
             rev.get("shellac_source_group"), None),
        )

    # Events last: needs documents to exist.
    _import_events_jsonl(conn, cfg, src, batch_id, caches)

    print(f"  {src['dir']}: {n_posts} new posts, {n_captures_only} additional captures")


def run(conn: sqlite3.Connection, ctx: dict) -> None:
    cfg = ctx["cfg"]
    caches = _Caches()
    for src in cfg.SOURCES:
        if not src.get("enabled"):
            continue
        _import_source(conn, ctx, src, caches)
