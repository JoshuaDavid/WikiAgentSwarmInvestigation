-- Secondary indexes for common query patterns.
-- Kept in a separate file so index-only churn doesn't move the schema hash
-- of the entity-defining files.

-- Actor / handle joins ("all posts by actor X")
CREATE INDEX idx_handle_actor       ON handle (actor_id);
CREATE INDEX idx_post_handle        ON post (handle_id);
CREATE INDEX idx_post_document      ON post (document_id);
CREATE INDEX idx_post_posted_at     ON post (posted_at);
CREATE INDEX idx_post_body          ON post (body_id);
CREATE INDEX idx_post_previous      ON post (previous_post_id);

-- Document lookups by venue
CREATE INDEX idx_document_venue     ON document (venue_id);

-- URL analysis
CREATE INDEX idx_url_ref_post       ON url_reference (post_id);
CREATE INDEX idx_url_ref_web        ON url_reference (web_resource_id);
CREATE INDEX idx_web_resource_host  ON web_resource (host_id);

-- Analysis label lookups by (subject_tbl, subject_id) and by kind
CREATE INDEX idx_label_subject      ON analysis_label (subject_tbl, subject_id);
CREATE INDEX idx_label_kind         ON analysis_label (analysis_label_kind_id);
CREATE INDEX idx_label_run          ON analysis_label (analysis_run_id);

-- Message lookups
CREATE INDEX idx_message_from_post  ON message (from_post_id);
CREATE INDEX idx_msg_ref_subject    ON message_reference (subject_tbl, subject_id);
CREATE INDEX idx_msg_ref_message    ON message_reference (message_id);

-- Provenance
CREATE INDEX idx_prov_subject       ON import_row_provenance (subject_tbl, subject_id);
CREATE INDEX idx_prov_batch         ON import_row_provenance (import_batch_id);
CREATE INDEX idx_raw_ref_subject    ON raw_source_ref (subject_tbl, subject_id);

-- Capture lookups (find how we got a post's bytes)
CREATE INDEX idx_capture_post       ON capture (post_id);
