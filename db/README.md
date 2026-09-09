# db

SQLite database built from every `agent-logs/*/` corpus plus every registered
analysis. The build is designed to be **byte-reproducible**: same inputs +
same SQLite version + same repo commit → same output file.

## Vocabulary

| Term | Meaning |
|---|---|
| schema file | A `db/schema/*.sql` DDL file, applied in numeric order at build time. |
| layer | A `db/layers/*.py` module that populates the DB. Runs in numeric order. |
| analysis | A registered classifier/detector. Each has its own `analysis_run` per build. |
| build hash | The `sha256` of the final `.sqlite` file. Pinned in `BUILD_HASH.txt`. |
| source | An `agent-logs/<name>/` directory. Enabled sources are imported by `04_import_agent_logs.py`. |

## Files

| File | What it holds |
|---|---|
| `build.py` | Orchestrator. `python3 db/build.py --clean` rebuilds. |
| `build_config.py` | `SOURCES` (enabled flags per corpus), `ANALYSES` (registry), `KNOWN_VENUES`. |
| `schema/NNN_*.sql` | DDL, applied in order. Each file's sha256 recorded in `schema_migration`. |
| `layers/NNN_*.py` | Build layers, each exposes `run(conn, ctx)`. |
| `tests/test_build_deterministic.sh` | Builds the DB twice and asserts byte-identical output. |
| `BUILD_HASH.txt` | Pinned sha256 of the current committed build. |
| `collusion.sqlite` | The built DB. Regenerated from source; not the source of truth. |

## Layers

| Layer | Purpose |
|---|---|
| `01_seed_registry.py` | Insert `analysis` + `analysis_label_kind` rows from `build_config.ANALYSES`. |
| `02_open_runs.py` | Open one `analysis_run` per registered analysis for this build. Stashes run IDs in `ctx`. |
| `03_import_venues.py` | Insert `KNOWN_VENUES`. |
| `04_import_agent_logs.py` | For every enabled source, read `revisions.jsonl`, dedup bodies, insert documents/handles/posts/captures + provenance. |
| `05_extract_urls.py` | Regex-scan every post body. Emit `url_reference` rows citing the `url_extraction` run. |
| `06_classify_hosts.py` | Assign a `host_category_classifier` label to every host. Rules imported from `analyses/urls/classify.py`. |
| `99_finalize.py` | `ANALYZE`, `PRAGMA integrity_check`. |

`build.py` then runs `VACUUM INTO` after the layers to produce byte-stable output.

## Reproducibility

- `SOURCE_DATE_EPOCH` environment variable pins all timestamps. Defaults to `1970-01-01T00:00:00+00:00` when unset.
- Every layer that iterates data sorts by a stable natural key before insert.
- Bodies dedup by sha256; the DB stores each unique body once.
- Schema files are hashed and their sha256s live in `schema_migration`.
- SQLite version prints at the top of every build (`sqlite3 version:`).
- After the build, run `db/tests/test_build_deterministic.sh` to verify.

Known non-determinism sources to avoid:
- Reading from `os.walk` (order varies); use `sorted(Path.glob(...))` instead.
- Reading `.get('field')` orders in Python dicts (fine in Python 3.7+; still, sort explicitly if you care).
- SQLite version drift; pin in CI.

## Usage

```
python3 db/build.py --clean            # full rebuild
python3 db/build.py --clean --verify   # rebuild + assert BUILD_HASH.txt matches
python3 db/build.py --layer extract_urls  # run one layer only (requires prior build)
db/tests/test_build_deterministic.sh   # rebuild twice, assert byte-identical
```

## Enabling new corpora

1. Flip `enabled: True` for the source in `build_config.SOURCES`.
2. Add any new venues to `KNOWN_VENUES` if the source names venues we haven't seeded.
3. Rebuild. Update `BUILD_HASH.txt` (the build hash changes when data changes).

## Currently enabled

Just `gems` (12 rows). This is the smallest corpus and serves as the
end-to-end test case. Other corpora will come online one at a time, with a
new commit per source.
