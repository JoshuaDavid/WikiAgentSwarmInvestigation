# OAI-published IP range hits
Scanned 24367 jsonl files under `/collusionwiki/`.
## Full-IP matches
Files with at least one full IPv4 falling in an OAI CIDR: **3**.
- `/collusionwiki/oai-index-scan/results/agent-activity/azure-expansion-2026-09-11/queries.jsonl`: 23 distinct IPs, 418 occurrences
- `/collusionwiki/tmp/collusionwiki/swarm-datapakk-20260907/tmcleod.org/index.jsonl`: 1 distinct IPs, 2 occurrences
- `/collusionwiki/tmp/collusionwiki/swarm-datapakk-20260907/www.wikiservice.at/index.jsonl`: 1 distinct IPs, 4 occurrences

## ip16 corridor hits (first-two-octet-only)
Many corpus files record only the first two octets of each IP in an `ip16` field. The rows below list files where at least one `ip16` value falls inside a /16 that hosts an OAI CIDR. A row here is *not* a confirmed hit: only 1/65536 of any given /16 is covered by the narrowest OAI /28. It marks a candidate corridor only.
Files with corridor hits: **4**.
| file | ip16 records | distinct ip16 | matching distinct | matching records |
|------|-------------:|--------------:|------------------:|-----------------:|
| `/collusionwiki/agent-logs/prowiki/revisions.jsonl` | 14591 | 191 | 39 | 4144 |
| `/collusionwiki/analyses/blank-labels/outputs/blank_nonstub.jsonl` | 375 | 91 | 25 | 103 |
| `/collusionwiki/tmp/blank_nonstub.jsonl` | 375 | 91 | 25 | 103 |
| `/collusionwiki/agent-logs/prowiki/events.jsonl` | 5322 | 50 | 14 | 19 |
