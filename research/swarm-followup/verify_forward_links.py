"""Read-only audit of links preceding a target's earliest preserved revision.

Run from any directory. No network calls and no output files are written.
This reproduces the original explicit-URL extraction, then also counts unique
source/target pairs so repeated copies in successive revisions are visible.
"""

import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "agent-logs/prowiki/revisions.jsonl"
PATTERN = re.compile(
    r"wikiservice\.at/dse/wiki\.cgi\?[^\s\]]*?\bid=([A-Za-z0-9_/\-]+)"
)
SELECTED = {
    "dse~AgentJSLinks99172@2",
    "dse~AgentSlashCountyMoreUnique123@1",
    "dse~AgentOpenAIDataUSAHubMay13X7@1",
    "dse~AgentOpenAIDataUSASlotMay13X7_22@1",
}


def main():
    records = {}
    source_lines = {}
    with CORPUS.open() as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            if row.get("wiki") != "dse":
                continue
            timestamp = row.get("write_date") or row.get("time")
            if not timestamp:
                continue
            row["parsed_time"] = datetime.fromisoformat(timestamp)
            records[row["rev_id"]] = row
            source_lines[row["rev_id"]] = line_number

    first = {}
    for row in records.values():
        old = first.get(row["name"])
        if old is None or row["parsed_time"] < old["parsed_time"]:
            first[row["name"]] = row

    events = []
    extracted = self_links = missing = 0
    for row in records.values():
        for target_name in set(PATTERN.findall(row.get("body") or "")):
            extracted += 1
            if target_name == row["name"]:
                self_links += 1
                continue
            target = first.get(target_name)
            if target is None:
                missing += 1
                continue
            gap = (target["parsed_time"] - row["parsed_time"]).total_seconds()
            if gap > 0:
                events.append({
                    "source": row["name"],
                    "source_rev": row["rev_id"],
                    "source_line": source_lines[row["rev_id"]],
                    "target": target_name,
                    "target_rev": target["rev_id"],
                    "target_line": source_lines[target["rev_id"]],
                    "gap_seconds": gap,
                    "same_label": row.get("label") == target.get("label"),
                })

    print(json.dumps({
        "corpus": str(CORPUS.relative_to(ROOT)),
        "dse_revisions_with_bodies": sum(bool(r.get("body")) for r in records.values()),
        "explicit_link_events": extracted,
        "self_links": self_links,
        "targets_missing_from_export": missing,
        "forward_link_events": len(events),
        "forward_link_source_pages": len({e["source"] for e in events}),
        "forward_link_unique_page_pairs": len({(e["source"], e["target"]) for e in events}),
        "shortest_examples": sorted(events, key=lambda e: (e["gap_seconds"], e["source_rev"]))[:3],
    }, indent=2))
    for revision_id in sorted(SELECTED):
        row = records[revision_id]
        print(json.dumps({
            "revision_id": revision_id,
            "source_line": source_lines[revision_id],
            "write_date": row.get("write_date"),
            "label": row.get("label"),
            "body": row.get("body"),
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
