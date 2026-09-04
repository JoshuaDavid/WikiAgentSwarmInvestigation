# collusionwiki

Working repo for analyzing wiki telemetry from an incident in which a large
fleet of RL-trained agents compromised third-party hosts (query-string RCE),
gained general internet access, and began writing to and reading from a
handful of public wikis to coordinate on benchmark/eval tasks.

The source data lives in `agent-logs/` (currently a single `prowiki/` export).
See `agent-logs/README.md` for the file-by-file schema.

Derived analyses live under `analyses/<topic>/`, each with a `README.md`, one
or more scripts, and an `outputs/` directory. Scripts read from
`agent-logs/prowiki/`; outputs are committed alongside the scripts.

`Dockerfile` + `docker-compose.yml` provide a sandbox container to work in.
`tmp/` is gitignored — put throwaway scripts and scratch there.

## Tracking

Each time you perform some sort of analysis, it should go into the repository
as a new `analyses/<topic>/` directory: narrative in `README.md`, code in a
script alongside it, generated data in `outputs/`.

## Conventions

- **Commit early and often.** Small, focused commits after each working step,
  not one big lump at the end. Cheap to revert, easy to bisect.
