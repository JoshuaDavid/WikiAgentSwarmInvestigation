-- A `message` is a span of text in a post that points at one or more subjects.
-- Intent (coordination / decorative / void-dump / gratitude / reply) is applied
-- via the analysis_label system on the message row, not encoded here.
--
-- One message can point at multiple subjects (see message_reference).

CREATE TABLE message (
    id                 INTEGER PRIMARY KEY,
    from_post_id       INTEGER NOT NULL REFERENCES post(id),
    byte_offset_start  INTEGER NOT NULL,
    byte_offset_end    INTEGER NOT NULL,
    quoted_text        TEXT,
    analysis_run_id    INTEGER NOT NULL REFERENCES analysis_run(id)
);

CREATE TABLE message_reference (
    id           INTEGER PRIMARY KEY,
    message_id   INTEGER NOT NULL REFERENCES message(id),
    subject_tbl  TEXT NOT NULL,
    subject_id   INTEGER NOT NULL,
    CHECK (subject_tbl IN ('handle', 'actor', 'post', 'document',
                            'task_variant', 'fast_follow_round', 'host'))
);
