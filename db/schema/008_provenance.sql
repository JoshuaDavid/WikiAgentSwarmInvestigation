-- Import provenance and raw-log pointers.
--
-- import_batch          — one entry per agent-logs/<name>/ ingest run
-- import_row_provenance — morph: trace any domain row back to its JSONL line
-- raw_manifest          — the source's manifest.json, preserved as JSON text
-- raw_file_integrity    — the source's SHA256SUMS, one row per file
-- raw_source_ref        — morph: point at raw operational logs the exporter cited
--                          (rclog, reqlog, attacklog, shellac source, wayback snapshot)
--
-- schema_migration      — DDL provenance: which schema files were applied

CREATE TABLE schema_migration (
    id           INTEGER PRIMARY KEY,
    filename     TEXT NOT NULL UNIQUE,
    sha256       TEXT NOT NULL,
    applied_at   TEXT NOT NULL
);

CREATE TABLE import_batch (
    id               INTEGER PRIMARY KEY,
    source_dir       TEXT NOT NULL,
    tool_version     TEXT,
    imported_at      TEXT NOT NULL,
    row_counts_json  TEXT,
    notes            TEXT
);

CREATE TABLE import_row_provenance (
    id                INTEGER PRIMARY KEY,
    subject_tbl       TEXT NOT NULL,
    subject_id        INTEGER NOT NULL,
    import_batch_id   INTEGER NOT NULL REFERENCES import_batch(id),
    source_file       TEXT NOT NULL,
    source_line_no    INTEGER
);

CREATE TABLE raw_manifest (
    id                INTEGER PRIMARY KEY,
    import_batch_id   INTEGER NOT NULL REFERENCES import_batch(id),
    filename          TEXT NOT NULL,
    content_json      TEXT NOT NULL
);

CREATE TABLE raw_file_integrity (
    id                INTEGER PRIMARY KEY,
    import_batch_id   INTEGER NOT NULL REFERENCES import_batch(id),
    filename          TEXT NOT NULL,
    sha256            TEXT NOT NULL
);

CREATE TABLE raw_source_ref (
    id            INTEGER PRIMARY KEY,
    subject_tbl   TEXT NOT NULL,
    subject_id    INTEGER NOT NULL,
    ref_kind      TEXT NOT NULL,
    ref_path      TEXT NOT NULL,
    ref_lineno    INTEGER,
    CHECK (ref_kind IN ('rclog', 'reqlog', 'attacklog',
                         'shellac_source', 'wayback_snapshot'))
);

-- Layer input hashing: which layers have run against which inputs.
-- Lets `build.py` skip layers whose inputs are unchanged.

CREATE TABLE layer_input_hash (
    id            INTEGER PRIMARY KEY,
    layer_name    TEXT NOT NULL,
    input_path    TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    UNIQUE (layer_name, input_path)
);
