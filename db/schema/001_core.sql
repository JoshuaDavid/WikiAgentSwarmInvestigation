-- Core domain: actors, handles, venues, documents, bodies, posts.
--
-- Vocabulary
--   actor    — a real intelligence behind one or more handles. Analyst-declared.
--   handle   — a name used to publish on a venue. Belongs to at most one actor.
--   venue    — a publishing surface (wiki, paste site, gem registry, shortener).
--              Wayback / shellac / live scrape are RETRIEVAL methods, not venues.
--   document — a named thing on a venue (wiki page, paste ID, gem filename, shortener code).
--   post     — one version of a document, published at a moment.
--   body     — deduplicated content bytes, keyed by sha256.

CREATE TABLE actor (
    id            INTEGER PRIMARY KEY,
    display_name  TEXT NOT NULL,
    notes         TEXT
);

CREATE TABLE network_block (
    id    INTEGER PRIMARY KEY,
    cidr  TEXT NOT NULL UNIQUE
);

CREATE TABLE venue (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    kind         TEXT NOT NULL,
    base_domain  TEXT,
    CHECK (kind IN ('wiki', 'paste_site', 'gem_registry', 'shortener'))
);

CREATE TABLE handle (
    id                   INTEGER PRIMARY KEY,
    name_str             TEXT NOT NULL,
    venue_id             INTEGER NOT NULL REFERENCES venue(id),
    actor_id             INTEGER REFERENCES actor(id),
    disambiguation_notes TEXT
    -- No UNIQUE on (name_str, venue_id). Two actors may share a name; the
    -- analyst splits by adding a second row with disambiguation notes.
);

CREATE TABLE handle_network_block (
    id                INTEGER PRIMARY KEY,
    handle_id         INTEGER NOT NULL REFERENCES handle(id),
    network_block_id  INTEGER NOT NULL REFERENCES network_block(id),
    n_posts           INTEGER,
    UNIQUE (handle_id, network_block_id)
);

CREATE TABLE document (
    id              INTEGER PRIMARY KEY,
    venue_id        INTEGER NOT NULL REFERENCES venue(id),
    canonical_name  TEXT NOT NULL,
    first_seen_at   TEXT,
    last_seen_at    TEXT,
    is_live         INTEGER,
    is_deleted      INTEGER,
    UNIQUE (venue_id, canonical_name)
);

CREATE TABLE wiki_document_details (
    id                       INTEGER PRIMARY KEY,
    document_id              INTEGER NOT NULL UNIQUE REFERENCES document(id),
    page_family              TEXT,
    page_family_source       TEXT,
    page_family_confidence   REAL,
    page_family_method       TEXT,
    bucket                   TEXT,
    rcs_path                 TEXT,
    live_body_variant        TEXT,
    head_differs_from_live   INTEGER
);

CREATE TABLE shortener_document_details (
    id                    INTEGER PRIMARY KEY,
    document_id           INTEGER NOT NULL UNIQUE REFERENCES document(id),
    created_at            TEXT,
    days_active           INTEGER,
    total_views           INTEGER,
    current_redirects_to  TEXT
);

CREATE TABLE body (
    id             INTEGER PRIMARY KEY,
    sha256         TEXT NOT NULL UNIQUE,
    byte_len       INTEGER NOT NULL,
    content_bytes  BLOB NOT NULL
);

CREATE TABLE post (
    id                       INTEGER PRIMARY KEY,
    document_id              INTEGER NOT NULL REFERENCES document(id),
    handle_id                INTEGER REFERENCES handle(id),
    network_block_id         INTEGER REFERENCES network_block(id),
    body_id                  INTEGER NOT NULL REFERENCES body(id),
    sequence_no              INTEGER NOT NULL,
    previous_post_id         INTEGER REFERENCES post(id),
    posted_at                TEXT,
    posted_at_grade          TEXT,
    posted_at_source_clock   TEXT,
    uncertainty_seconds      REAL,
    change_summary           TEXT,
    UNIQUE (document_id, sequence_no)
);

CREATE TABLE wiki_post_details (
    id                    INTEGER PRIMARY KEY,
    post_id               INTEGER NOT NULL UNIQUE REFERENCES post(id),
    revision_id_str       TEXT,
    rcs_revision_number   INTEGER,
    is_new_page           INTEGER,
    is_minor_edit         INTEGER,
    write_date            TEXT,
    request_time          TEXT,
    success_time          TEXT,
    recent_changes_time   TEXT,
    related_moderation_id INTEGER,
    related_kind          TEXT
);

CREATE TABLE paste_post_details (
    id                        INTEGER PRIMARY KEY,
    post_id                   INTEGER NOT NULL UNIQUE REFERENCES post(id),
    archived_at               TEXT,
    shellac_doc_id            TEXT,
    shellac_source_type       TEXT,
    shellac_source_group      TEXT,
    shellac_source_url        TEXT,
    shellac_title             TEXT,
    shellac_occurrences       INTEGER,
    shellac_timestamp_basis   TEXT
);
