-- Moderation and probe events.

CREATE TABLE moderation_event (
    id                INTEGER PRIMARY KEY,
    document_id       INTEGER NOT NULL REFERENCES document(id),
    admin_handle_id   INTEGER REFERENCES handle(id),
    network_block_id  INTEGER REFERENCES network_block(id),
    kind              TEXT NOT NULL,
    requested_at      TEXT,
    succeeded_at      TEXT,
    rclog_at          TEXT,
    change_summary    TEXT,
    was_page_held     INTEGER,
    CHECK (kind IN ('delete', 'revert'))
);

CREATE TABLE probe (
    id                INTEGER PRIMARY KEY,
    venue_id          INTEGER NOT NULL REFERENCES venue(id),
    network_block_id  INTEGER REFERENCES network_block(id),
    param_family      TEXT,
    request_action    TEXT,
    requested_at      TEXT
);
