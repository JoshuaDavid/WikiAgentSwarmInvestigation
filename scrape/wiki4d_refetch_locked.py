#!/usr/bin/env python3
"""Re-fetch bodies and diffs for pages that were locked out by ProWiki during
a previous wiki4d scrape.

Reads manifest.json to find `locked_pages`, then re-fetches each one and
patches revisions.jsonl / pages.jsonl / SHA256SUMS. If more pages are still
locked after this pass, the manifest's locked_pages is left non-empty and
another pass can be run later.

Usage:
    python3 scrape/wiki4d_refetch_locked.py \
        --base https://prowiki.org/wiki4d/wiki.cgi \
        --out agent-logs/wiki4d --sleep 5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

# Reuse the primary scraper's helpers.
sys.path.insert(0, str(Path(__file__).parent))
import wiki4d as W  # type: ignore  # same-dir sibling


def refetch(base: str, out: Path, sleep: float) -> None:
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    locked = list(manifest.get("locked_pages") or [])
    if not locked:
        print("no locked pages recorded; nothing to do", file=sys.stderr)
        return
    print(f"refetching {len(locked)} pages: {locked[:5]}...", file=sys.stderr)

    still_locked: list[str] = []
    fresh_bodies: dict[str, str] = {}
    fresh_diffs: dict[str, dict] = {}
    for pn in locked:
        print(f"[refetch] {pn}: body ...", file=sys.stderr)
        body_html, _ = W.fetch(W.build_url(base, action="browse", id=pn), sleep=sleep)
        if W._looks_like_lock(body_html):
            print(f"[refetch] {pn}: still LOCKED", file=sys.stderr)
            still_locked.append(pn)
            continue
        fresh_bodies[pn] = W.strip_content_to_text(W.extract_content_html(body_html))
        print(f"[refetch] {pn}: diff ...", file=sys.stderr)
        diff_html, _ = W.fetch(W.build_url(base, action="browse", diff="4", id=pn), sleep=sleep)
        if W._looks_like_lock(diff_html):
            print(f"[refetch] {pn}: diff still locked; leaving hunks empty", file=sys.stderr)
            fresh_diffs[pn] = {"hunks": [], "no_previous_revision": False, "lock": True}
        else:
            fresh_diffs[pn] = W.parse_diff(diff_html)

    # Patch revisions.jsonl in-place.
    rev_path = out / "revisions.jsonl"
    revs = [json.loads(l) for l in rev_path.read_text().splitlines() if l.strip()]
    # Build page -> head_rev_index. Head is the last (in chronological order) row per page.
    last_seq_by_page: dict[str, int] = {}
    for i, r in enumerate(revs):
        last_seq_by_page[r["name"]] = i  # scan overwrites so we end with the last
    for pn, body in fresh_bodies.items():
        i = last_seq_by_page.get(pn)
        if i is None:
            print(f"[refetch] WARN: {pn} not in revisions.jsonl", file=sys.stderr)
            continue
        rev = revs[i]
        rev["body"] = body
        rev["body_len"] = len(body)
        rev["body_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
        rev["lines"] = body.count("\n") + 1 if body else None
        rev["body_encoding"] = "html_stripped_utf8"
        rev["body_availability"] = "head_only"
        diff = fresh_diffs.get(pn) or {}
        rev["hunks"] = diff.get("hunks") or []

    with rev_path.open("w", encoding="utf-8") as f:
        for r in revs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Patch pages.jsonl body_bytes.
    pages_path = out / "pages.jsonl"
    pages = [json.loads(l) for l in pages_path.read_text().splitlines() if l.strip()]
    for p in pages:
        if p["name"] in fresh_bodies:
            p["body_bytes"] = len(fresh_bodies[p["name"]].encode("utf-8"))
    with pages_path.open("w", encoding="utf-8") as f:
        for p in pages:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # Update manifest.locked_pages / counts / body_bytes.
    manifest["locked_pages"] = sorted(still_locked)
    manifest.setdefault("counts", {})["locked_pages"] = {"value": len(still_locked)}
    wiki = manifest["source"]["wiki_name"]
    manifest.setdefault("per_wiki", {}).setdefault(wiki, {})["body_bytes"] = {
        "value": sum(p["body_bytes"] for p in pages)
    }
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Rewrite SHA256SUMS.
    with (out / "SHA256SUMS").open("w", encoding="utf-8") as f:
        for fname in sorted(["pages.jsonl", "revisions.jsonl", "events.jsonl", "labels.jsonl", "manifest.json"]):
            data = (out / fname).read_bytes()
            f.write(f"{hashlib.sha256(data).hexdigest()}  {fname}\n")

    print(f"refetched {len(fresh_bodies)} pages; still locked: {len(still_locked)}", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--sleep", type=float, default=5.0)
    args = p.parse_args()
    refetch(args.base, args.out, args.sleep)


if __name__ == "__main__":
    main()
