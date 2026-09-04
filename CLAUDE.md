# collusionwiki

Working repo for analyzing wiki telemetry from an incident in which a large
fleet of RL-trained agents compromised third-party hosts (query-string RCE),
gained general internet access, and began writing to and reading from a
handful of public wikis to coordinate on benchmark/eval tasks.

The source data lives in `agent-logs/` (currently a single `prowiki/` export).
See `agent-logs/README.md` for the file-by-file schema and
`agent-logs/prowiki/URL_CLASSIFICATION.md` for the URL breakdown.

`Dockerfile` + `docker-compose.yml` provide a sandbox container to work in.
`tmp/` is gitignored — put throwaway scripts and scratch there.

## Conventions

- **Commit early and often.** Small, focused commits after each working step,
  not one big lump at the end. Cheap to revert, easy to bisect.
