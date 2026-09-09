-- Task / variant / participation. Universal shape.
-- Variant-kind-specific fields live in <kind>_variant_details tables.

CREATE TABLE task (
    id                       INTEGER PRIMARY KEY,
    name                     TEXT NOT NULL UNIQUE,
    description              TEXT,
    first_evidence_post_id   INTEGER REFERENCES post(id)
);

CREATE TABLE task_variant (
    id           INTEGER PRIMARY KEY,
    task_id      INTEGER NOT NULL REFERENCES task(id),
    name         TEXT NOT NULL,
    description  TEXT,
    kind         TEXT NOT NULL,
    UNIQUE (task_id, name),
    CHECK (kind IN ('fast_follow_qa', 'other'))
);

CREATE TABLE task_participation (
    id                INTEGER PRIMARY KEY,
    task_variant_id   INTEGER NOT NULL REFERENCES task_variant(id),
    actor_id          INTEGER REFERENCES actor(id),
    handle_id         INTEGER REFERENCES handle(id),
    evidence_notes    TEXT,
    CHECK (actor_id IS NOT NULL OR handle_id IS NOT NULL)
);

-- Fast-follow-Q&A specifics: task-clock multiplier, deadline, cooldown, rounds.
-- This shape is CLAUDE.md-documented and covers most swarm tasks in the corpus.
-- Other task kinds get their own <kind>_variant_details table when needed.

CREATE TABLE fast_follow_variant_details (
    id                            INTEGER PRIMARY KEY,
    task_variant_id               INTEGER NOT NULL UNIQUE REFERENCES task_variant(id),
    task_clock_multiplier_x       REAL,
    initial_deadline_seconds      INTEGER,
    followup_deadline_seconds     INTEGER,
    cooldown_seconds              INTEGER,
    tokens_per_sec                INTEGER,
    notes                         TEXT
);

CREATE TABLE fast_follow_round (
    id                              INTEGER PRIMARY KEY,
    fast_follow_variant_details_id  INTEGER NOT NULL REFERENCES fast_follow_variant_details(id),
    ordinal                         INTEGER NOT NULL,
    deadline_task_clock             TEXT,
    cooldown_task_clock             TEXT,
    UNIQUE (fast_follow_variant_details_id, ordinal)
);

CREATE TABLE fast_follow_post_round (
    id                     INTEGER PRIMARY KEY,
    post_id                INTEGER NOT NULL REFERENCES post(id),
    fast_follow_round_id   INTEGER NOT NULL REFERENCES fast_follow_round(id),
    role                   TEXT NOT NULL
);
