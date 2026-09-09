-- URLs referenced from post bodies.
--
-- host          — DNS name, exactly as it appeared in the URL string.
-- decoded_name  — percent-decoded / entity-decoded canonical form.
--                 For non-obfuscated hosts, equals `name`.
-- web_resource  — a specific URL string. UNIQUE on the full string.
-- url_reference — one row per URL match in a post body. Cites the
--                 analysis_run that extracted it, so re-runs are versioned.

CREATE TABLE host (
    id             INTEGER PRIMARY KEY,
    name           TEXT NOT NULL UNIQUE,
    decoded_name   TEXT NOT NULL
);

CREATE TABLE web_resource (
    id        INTEGER PRIMARY KEY,
    host_id   INTEGER NOT NULL REFERENCES host(id),
    url_full  TEXT NOT NULL UNIQUE
);

CREATE TABLE url_reference (
    id                INTEGER PRIMARY KEY,
    post_id           INTEGER NOT NULL REFERENCES post(id),
    web_resource_id   INTEGER NOT NULL REFERENCES web_resource(id),
    byte_offset       INTEGER NOT NULL,
    scheme            TEXT NOT NULL,
    analysis_run_id   INTEGER NOT NULL REFERENCES analysis_run(id)
);
