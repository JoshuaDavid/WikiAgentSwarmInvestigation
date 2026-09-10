#!/usr/bin/env python3
"""Fold subagent review verdicts back into pastes_by_task.tsv.

Reads:
  outputs/pastes_by_task.tsv          - regex-classifier output
  outputs/review_batches/verdicts_*.jsonl - subagent verdicts

Writes:
  outputs/pastes_by_task.tsv          - overwritten with reviewed labels
  outputs/summary.tsv                 - overwritten
  outputs/label_provenance.tsv        - per-paste: regex label vs. reviewer label

Verdict jsonl format per line:
  {"body_sha256": "...", "task": "...", "confidence": "...", "rationale": "..."}
"""
from __future__ import annotations
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "outputs"
BATCH_DIR = OUT_DIR / "review_batches"
PBT_PATH = OUT_DIR / "pastes_by_task.tsv"


def load_verdicts() -> dict[str, dict]:
    """sha -> {task, confidence, rationale, batch}"""
    verdicts: dict[str, dict] = {}
    for vf in sorted(BATCH_DIR.glob("verdicts_*.jsonl")):
        batch_id = vf.stem.rsplit("_", 1)[-1]
        with vf.open() as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    v = json.loads(line)
                except json.JSONDecodeError:
                    print(f"skip malformed line in {vf}: {line[:80]!r}", file=sys.stderr)
                    continue
                sha = v.get("body_sha256")
                task = v.get("task")
                if not sha or not task:
                    continue
                verdicts[sha] = {
                    "task": task,
                    "confidence": v.get("confidence", ""),
                    "rationale": v.get("rationale", ""),
                    "batch": batch_id,
                }
    return verdicts


def main() -> None:
    verdicts = load_verdicts()
    print(f"loaded {len(verdicts)} subagent verdicts", file=sys.stderr)

    with PBT_PATH.open() as f:
        header = f.readline().rstrip("\n").split("\t")
        rows = [dict(zip(header, line.rstrip("\n").split("\t"))) for line in f if line.strip()]

    # Overwrite task where a verdict exists. Track provenance.
    provenance_rows = []
    n_confirmed = n_overridden = n_upgraded = 0
    for r in rows:
        sha = r["body_sha256"]
        original_task = r["task"]
        v = verdicts.get(sha)
        if v:
            new_task = v["task"]
            r["task"] = new_task
            if new_task == original_task:
                n_confirmed += 1
                provenance = "reviewer_confirmed"
            elif original_task == "unknown":
                n_upgraded += 1
                provenance = "reviewer_upgraded_from_unknown"
            else:
                n_overridden += 1
                provenance = "reviewer_overrode_regex"
        else:
            provenance = "regex_only"
        provenance_rows.append({
            "body_sha256": sha,
            "regex_task": original_task,
            "final_task": r["task"],
            "provenance": provenance,
            "reviewer_confidence": (v or {}).get("confidence", ""),
            "reviewer_rationale": (v or {}).get("rationale", ""),
            "reviewer_batch": (v or {}).get("batch", ""),
        })

    print(f"  regex_only: {sum(1 for p in provenance_rows if p['provenance']=='regex_only')}", file=sys.stderr)
    print(f"  reviewer_confirmed: {n_confirmed}", file=sys.stderr)
    print(f"  reviewer_upgraded_from_unknown: {n_upgraded}", file=sys.stderr)
    print(f"  reviewer_overrode_regex: {n_overridden}", file=sys.stderr)

    rows.sort(key=lambda x: (x["task"], x.get("time") or "", x["body_sha256"]))
    with PBT_PATH.open("w") as f:
        f.write("\t".join(header) + "\n")
        for r in rows:
            f.write("\t".join(r.get(c, "") for c in header) + "\n")

    summary_path = OUT_DIR / "summary.tsv"
    counts = Counter(r["task"] for r in rows)
    first_last: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        t = r.get("time") or ""
        if t:
            first_last[r["task"]].append(t)
    with summary_path.open("w") as f:
        f.write("task\tn_pastes\tfirst_time\tlast_time\n")
        all_t = sorted(t for ts in first_last.values() for t in ts)
        f.write(f"(all)\t{sum(counts.values())}\t"
                f"{all_t[0] if all_t else ''}\t{all_t[-1] if all_t else ''}\n")
        for task, n in counts.most_common():
            ts = sorted(first_last[task])
            f.write(f"{task}\t{n}\t"
                    f"{ts[0] if ts else ''}\t{ts[-1] if ts else ''}\n")

    prov_path = OUT_DIR / "label_provenance.tsv"
    with prov_path.open("w") as f:
        cols = ["body_sha256", "regex_task", "final_task", "provenance",
                "reviewer_confidence", "reviewer_batch", "reviewer_rationale"]
        f.write("\t".join(cols) + "\n")
        provenance_rows.sort(key=lambda x: (x["final_task"], x["body_sha256"]))
        for p in provenance_rows:
            f.write("\t".join(str(p.get(c, "")).replace("\t", " ") for c in cols) + "\n")

    print(f"wrote {PBT_PATH}", file=sys.stderr)
    print(f"wrote {summary_path}", file=sys.stderr)
    print(f"wrote {prov_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
