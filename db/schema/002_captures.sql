-- Capture: how the bytes were retrieved.
--
-- One post can have zero-to-many captures. The `body_id` on `post` is the
-- canonical bytes; this table records who fetched them and how.
--
-- method
--   live_scrape       — direct HTTP fetch from the venue's live site
--   wiki_export       — ProWiki farm's own export tarball
--   shellac_pack      — pulled from shellac's agent-reading-pack tarballs
--   wayback_snapshot  — retrieved via the Internet Archive Wayback Machine
--   user_paste        — a human handed us the bytes

CREATE TABLE capture (
    id                 INTEGER PRIMARY KEY,
    post_id            INTEGER NOT NULL REFERENCES post(id),
    method             TEXT NOT NULL,
    captured_at        TEXT,
    source_url         TEXT,
    wayback_timestamp  TEXT,
    wayback_url        TEXT,
    importer_pack_id   TEXT,
    notes              TEXT,
    CHECK (method IN ('live_scrape', 'wiki_export', 'shellac_pack',
                       'wayback_snapshot', 'user_paste'))
);
