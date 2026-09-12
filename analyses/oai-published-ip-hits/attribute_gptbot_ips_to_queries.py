"""Attribute each occurrence of a chosen set of gptbot-range IPs in the
weekly OpenAI search index scrapes back to the search query that produced it.

The weekly scrapes live in two paired locations:

- `oai-index-scan/tmp/raw/<week>.group_<NNN>.txt` — the raw text dump of
  every result the OpenAI search API returned for a single `group_number`
  during that week's run. One IP-of-interest can appear in many result
  snippets inside one group file.
- `oai-index-scan/results/shards/<week>.queries.jsonl` — the query log for
  that week. Each row has `group_number`, `query_sequence`, and `query`.
  All queries with the same `group_number` in a week share a group file.

For each (week, group) whose raw file contains any target IP, this script
looks up the query text and tallies how many weeks each query fired in.
Answers: were the gptbot-range visitor IPs on yourls.shop retrieved by a
consistent set of search terms, or by ad-hoc drilldowns?

Reads:
- Constant list of gptbot-range IPs picked from queries.jsonl top hits.
- `oai-index-scan/tmp/raw/*.txt`
- `oai-index-scan/results/shards/*.queries.jsonl`

Writes:
- `outputs/gptbot_ip_query_attribution.json`
"""
import json
import os
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path("/collusionwiki")
RAW_DIR = ROOT / "oai-index-scan/tmp/raw"
SHARD_DIR = ROOT / "oai-index-scan/results/shards"
OUT = Path(__file__).parent / "outputs" / "gptbot_ip_query_attribution.json"

TARGET_IPS = [
    "74.7.227.151", "74.7.227.165", "74.7.241.37", "74.7.227.138",
    "74.7.241.17",  "74.7.227.36",  "74.7.243.202",
]

GROUP_FILE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\.group_(\d+)\.txt")

def scan_raw_files():
    """(week, group) -> sorted list of matched target IPs."""
    hits = defaultdict(set)
    for fn in os.listdir(RAW_DIR):
        m = GROUP_FILE_RE.match(fn)
        if not m: continue
        week, group = m.group(1), int(m.group(2))
        try:
            with open(RAW_DIR / fn, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        for ip in TARGET_IPS:
            if ip.encode() in data:
                hits[(week, group)].add(ip)
    return {k: sorted(v) for k, v in hits.items()}

def load_queries_index():
    """week -> {group_number -> [(query_sequence, query), ...]}"""
    idx = {}
    for fn in os.listdir(SHARD_DIR):
        if not fn.endswith(".queries.jsonl"): continue
        week = fn.split(".")[0]
        wk = idx.setdefault(week, {})
        with open(SHARD_DIR / fn) as f:
            for line in f:
                d = json.loads(line)
                g = d.get("group_number")
                wk.setdefault(g, []).append((d.get("query_sequence"),
                                              d.get("query")))
    return idx

def main():
    hits = scan_raw_files()
    q_idx = load_queries_index()

    per_query = defaultdict(lambda: {"weeks": set(),
                                      "group_hits": 0,
                                      "matched_ips": set()})
    unresolved = []
    for (week, group), ips in hits.items():
        rows = q_idx.get(week, {}).get(group)
        if not rows:
            unresolved.append({"week": week, "group": group, "ips": ips})
            continue
        # A group can hold multiple queries; the raw file blends them, so
        # attribute the hit to every query that ran in that group.
        for _seq, q in rows:
            if q is None: continue
            per_query[q]["weeks"].add(week)
            per_query[q]["group_hits"] += 1
            per_query[q]["matched_ips"].update(ips)

    rows_out = []
    for q, info in per_query.items():
        weeks = sorted(info["weeks"])
        rows_out.append({
            "query": q,
            "n_weeks_fired": len(weeks),
            "first_week": weeks[0] if weeks else None,
            "last_week": weeks[-1] if weeks else None,
            "group_hits_across_weeks": info["group_hits"],
            "matched_ips": sorted(info["matched_ips"]),
        })
    rows_out.sort(key=lambda r: (-r["n_weeks_fired"], -r["group_hits_across_weeks"]))

    n_weeks_available = len(q_idx)
    result = {
        "target_ips": TARGET_IPS,
        "n_weeks_of_shards_available": n_weeks_available,
        "n_group_files_with_any_target_ip": len(hits),
        "n_distinct_queries_that_hit": len(rows_out),
        "queries_hitting_every_week": [
            r["query"] for r in rows_out if r["n_weeks_fired"] == n_weeks_available
        ],
        "queries": rows_out,
        "unresolved_group_files": unresolved,
    }
    OUT.write_text(json.dumps(result, indent=2))

    print(f"weeks of shards available: {n_weeks_available}")
    print(f"group files matched:       {len(hits)}")
    print(f"distinct queries:          {len(rows_out)}\n")
    print("Queries firing every week:")
    for q in result["queries_hitting_every_week"]:
        print(f"  {q}")
    print("\nTop queries by week-coverage:")
    for r in rows_out[:10]:
        print(f"  {r['n_weeks_fired']:>2}/{n_weeks_available} weeks  "
              f"{r['group_hits_across_weeks']:>3} group hits  {r['query']}")

if __name__ == "__main__":
    main()
