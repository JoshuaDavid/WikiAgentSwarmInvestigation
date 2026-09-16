import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "agent-logs/pastebin-k4be/revisions.jsonl"


def epoch(row):
    return datetime.fromisoformat(row["time"]).timestamp()


def main():
    rows = []
    with SOURCE.open() as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            row["source_line"] = line_number
            rows.append(row)

    pads = []
    for row in rows:
        title = re.fullmatch(r"PAD(\d+)x(\d+)", row.get("source_title", ""))
        if not title:
            continue
        body = re.fullmatch(r"pad-([0-9.]+)-(\d+)", row["body"].strip())
        if not body or int(body[2]) != int(title[1]):
            raise ValueError(f"Mismatched padding record: {row['name']}")
        pads.append({
            "index": int(title[1]), "pid": row["name"], "source_line": row["source_line"],
            "title": row["source_title"], "site_time": row["time"],
            "site_epoch": epoch(row), "body_epoch": float(body[1]),
            "body_time_utc": datetime.fromtimestamp(float(body[1]), timezone.utc).isoformat(timespec="milliseconds"),
            "site_minus_body_seconds": epoch(row) - float(body[1]),
        })
    pads.sort(key=lambda row: row["index"])
    if [row["index"] for row in pads] != list(range(70)):
        raise ValueError("Expected 70 consecutive indices")
    start = min(row["site_epoch"] for row in pads)
    end = max(row["site_epoch"] for row in pads)
    embedded_intervals = [b["body_epoch"] - a["body_epoch"] for a, b in zip(pads, pads[1:])]

    targets = []
    for row in rows:
        if "nsx9pi" not in row["body"]:
            continue
        before = sum(epoch(row) < epoch(other) < start for other in rows)
        after = sum(epoch(row) < epoch(other) <= end for other in rows)
        targets.append({
            "pid": row["name"], "title": row["source_title"], "source_line": row["source_line"],
            "site_time": row["time"], "replyto_pid": row.get("replyto_pid"),
            "retained_newer_pastes_before": before, "retained_newer_pastes_after": after,
            "modeled_list_offset_before": before // 15 * 15,
            "modeled_list_offset_after": after // 15 * 15,
        })

    summary = {
        "unique_padding_pids": len({row["pid"] for row in pads}),
        "index_range": [pads[0]["index"], pads[-1]["index"]],
        "site_span_seconds": end - start,
        "embedded_span_seconds": pads[-1]["body_epoch"] - pads[0]["body_epoch"],
        "mean_embedded_interval_seconds": (pads[-1]["body_epoch"] - pads[0]["body_epoch"]) / (len(pads) - 1),
        "min_embedded_interval_seconds": min(embedded_intervals),
        "max_embedded_interval_seconds": max(embedded_intervals),
        "first_site_minus_body_seconds": pads[0]["site_minus_body_seconds"],
        "last_site_minus_body_seconds": pads[-1]["site_minus_body_seconds"],
        "site_time_reversals_in_counter_order": [[a["index"], b["index"]] for a, b in zip(pads, pads[1:]) if b["site_epoch"] < a["site_epoch"]],
        "target_links": targets,
        "model_assumptions": "15 entries per page, newest first; ranks use retained records, not a complete May snapshot. No historical reads or motive are inferred by this script.",
    }
    output = HERE / "outputs"
    output.mkdir(exist_ok=True)
    with (output / "padding.tsv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(pads[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(pads)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
