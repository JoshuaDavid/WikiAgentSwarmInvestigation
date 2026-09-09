#!/usr/bin/env python3
"""Materialize compact classification tasks so Haiku-agent workers can classify
without loading the full revisions.jsonl corpus themselves.

Reads comms.jsonl, merges A→B and B→A into undirected {A,B} pairs, and for
each pair inlines up to N page-excerpts (A's and B's revision bodies on their
shared pages, truncated). Writes ordered task cards to
`outputs/batches/tasks_all.jsonl`, sorted by max_shared_pages descending so
the earliest slices cover the highest-signal pairs.

Splitting into worker slices is done at kickoff time with `split`.
"""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
LOGS = REPO_ROOT / "agent-logs"
OUT = ROOT / "outputs"
BATCH_DIR = OUT / "batches"

MAX_BODY_CHARS_PER_REV = 900
MAX_REVS_PER_SIDE = 6
MAX_PAGES_PER_PAIR = 6


def load_revisions_by_id():
    best = {}
    for d in sorted(LOGS.iterdir()):
        if not d.is_dir():
            continue
        rp = d / "revisions.jsonl"
        if not rp.exists():
            continue
        with rp.open() as f:
            for line in f:
                rev = json.loads(line)
                rid = rev.get("rev_id")
                if not rid:
                    continue
                body = rev.get("body")
                if rid in best and best[rid].get("body") and not body:
                    continue
                best[rid] = {"body": body or "", "label": rev.get("label", ""), "time": rev.get("time", "")}
    return best


def merge_undirected():
    by_key = {}
    with (OUT / "comms.jsonl").open() as f:
        for line in f:
            row = json.loads(line)
            a, b = row["from"], row["to"]
            key = tuple(sorted([a, b]))
            if key not in by_key:
                by_key[key] = {
                    "a": key[0], "b": key[1],
                    "n_shared_pages": 0, "n_encounters": 0,
                    "pages": {}, "max_shared_pages": 0,
                }
            rec = by_key[key]
            rec["n_encounters"] += row["n_encounters"]
            rec["max_shared_pages"] = max(rec["max_shared_pages"], row["n_shared_pages"])
            for s in row.get("sample_pages", []):
                pid = s["page_id"]
                if pid not in rec["pages"]:
                    rec["pages"][pid] = s
    for rec in by_key.values():
        rec["n_shared_pages"] = len(rec["pages"])
    return by_key


def _resolve_side(rid, revisions, a, b):
    """Return ("a"|"b", body) for a rev id, using its actual writer label."""
    if not rid:
        return None, None
    r = revisions.get(rid)
    if not r:
        return None, None
    writer = r.get("label", "")
    body = (r.get("body") or "").strip()
    if writer == a:
        return "a", body
    if writer == b:
        return "b", body
    return None, None


def build_task(rec, revisions):
    a, b = rec["a"], rec["b"]
    pages = list(rec["pages"].values())[:MAX_PAGES_PER_PAIR]
    a_revs = []
    b_revs = []
    for s in pages:
        for rid in (s.get("a_rev"), s.get("b_rev")):
            side, body = _resolve_side(rid, revisions, a, b)
            if not side or not body:
                continue
            excerpt = body[:MAX_BODY_CHARS_PER_REV]
            if len(body) > MAX_BODY_CHARS_PER_REV:
                excerpt += "…"
            r = revisions.get(rid)
            entry = {
                "page": s["page_id"], "rev": rid,
                "time": r.get("time", ""), "excerpt": excerpt,
            }
            (a_revs if side == "a" else b_revs).append(entry)
    a_revs = a_revs[:MAX_REVS_PER_SIDE]
    b_revs = b_revs[:MAX_REVS_PER_SIDE]
    return {
        "a": a, "b": b,
        "n_shared_pages": rec["n_shared_pages"],
        "n_encounters": rec["n_encounters"],
        "a_revs": a_revs,
        "b_revs": b_revs,
    }


def has_bodies(rec, revisions):
    """Return True iff both sides have >=1 body-bearing revision on shared pages."""
    a, b = rec["a"], rec["b"]
    a_body = b_body = False
    for s in rec["pages"].values():
        for rid in (s.get("a_rev"), s.get("b_rev")):
            side, body = _resolve_side(rid, revisions, a, b)
            if not side or not body:
                continue
            if side == "a":
                a_body = True
            else:
                b_body = True
            if a_body and b_body:
                return True
    return a_body and b_body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=0, help="Only include top-N pairs by max_shared_pages (0 = all)")
    args = ap.parse_args()

    BATCH_DIR.mkdir(exist_ok=True)
    print("loading revisions…")
    revisions = load_revisions_by_id()
    print(f"  {len(revisions)} revision bodies loaded")

    print("merging comms into undirected pairs…")
    merged = merge_undirected()
    all_pairs = sorted(merged.values(), key=lambda r: (-r["max_shared_pages"], r["a"], r["b"]))
    print(f"  {len(all_pairs)} undirected pairs total")

    print("filtering to pairs with >=1 bodied revision on both sides…")
    pairs = [p for p in all_pairs if has_bodies(p, revisions)]
    print(f"  {len(pairs)} classifiable pairs after filter")

    if args.top:
        pairs = pairs[:args.top]
    print(f"  {len(pairs)} pairs to materialize")

    out_path = BATCH_DIR / "tasks_all.jsonl"
    n_written = 0
    with out_path.open("w") as fh:
        for rec in pairs:
            task = build_task(rec, revisions)
            fh.write(json.dumps(task, ensure_ascii=False) + "\n")
            n_written += 1
    print(f"wrote {n_written} tasks to {out_path}")


if __name__ == "__main__":
    main()
