-- Analysis system: replaces all ad-hoc classification tables.
--
-- analysis            — a classifier / detector definition
-- analysis_run        — one execution of an analysis (pinned to a git_sha)
-- analysis_label_kind — the specific label values an analysis can emit
-- analysis_label      — one application of a label to a subject
--
-- Query pattern: "when did agents first do X" → find the label_kind, join to
-- analysis_label, then to `post` via (subject_tbl, subject_id), then MIN(posted_at).

CREATE TABLE analysis (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    description  TEXT
);

CREATE TABLE analysis_run (
    id           INTEGER PRIMARY KEY,
    analysis_id  INTEGER NOT NULL REFERENCES analysis(id),
    version      TEXT NOT NULL,
    git_sha      TEXT,
    run_at       TEXT NOT NULL,
    notes        TEXT,
    UNIQUE (analysis_id, version)
);

CREATE TABLE analysis_label_kind (
    id           INTEGER PRIMARY KEY,
    analysis_id  INTEGER NOT NULL REFERENCES analysis(id),
    name         TEXT NOT NULL,
    description  TEXT,
    UNIQUE (analysis_id, name)
);

CREATE TABLE analysis_label (
    id                       INTEGER PRIMARY KEY,
    analysis_run_id          INTEGER NOT NULL REFERENCES analysis_run(id),
    analysis_label_kind_id   INTEGER NOT NULL REFERENCES analysis_label_kind(id),
    subject_tbl              TEXT NOT NULL,
    subject_id               INTEGER NOT NULL,
    confidence               REAL,
    evidence_notes           TEXT,
    CHECK (subject_tbl IN ('post', 'message', 'handle', 'actor',
                            'document', 'host', 'web_resource',
                            'task_variant', 'venue'))
);
