#!/usr/bin/env python3
"""Merge subagent verdicts with the full-site scrape and write agent-logs/pastebin-k4be/.

Inputs
------
  * scrape/outputs/pastebin-k4be/bodies.jsonl - one row per paste on the site
    at scrape time.
  * outputs/skipped_in_corpus.jsonl - pids that were already in
    agent-logs/pastes/pastebin-k4be/ so we did not send them to a subagent.
    These are treated as swarm by definition (shellac already labelled them).
  * outputs/verdicts/verdict_*.json - one file per subagent batch, each an
    array of {pid, verdict, rationale, confidence} objects. `verdict` is
    one of "swarm", "unclear", "human". "swarm" and "unclear" are both
    included in the export ("err on the side of over-inclusiveness").

Output
------
  * agent-logs/pastebin-k4be/{manifest.json, revisions.jsonl, pages.jsonl,
    events.jsonl, labels.jsonl, SHA256SUMS, README.md}

Schema mirrors agent-logs/pastes/ as closely as we can from a live-site
scrape. Every revision row records the classification chain
(`inclusion_reason` = "shellac_import" or "subagent_verdict") and the raw
subagent rationale so downstream analyses can filter.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BODIES = ROOT / "scrape" / "outputs" / "pastebin-k4be" / "bodies.jsonl"
CORPUS = ROOT / "agent-logs" / "pastes" / "revisions.jsonl"

OUT_DIR_LOCAL = Path(__file__).parent / "outputs"
SKIPPED = OUT_DIR_LOCAL / "skipped_in_corpus.jsonl"
VERDICT_DIR = OUT_DIR_LOCAL / "verdicts"

EXPORT = ROOT / "agent-logs" / "pastebin-k4be"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_bodies() -> dict[str, dict]:
    """pid -> body row from scrape."""
    by_pid = {}
    with BODIES.open() as f:
        for line in f:
            r = json.loads(line)
            pid = r.get("pid")
            if pid:
                by_pid[pid] = r
    return by_pid


def load_verdicts() -> dict[str, dict]:
    """pid -> {verdict, rationale, confidence, batch_index}."""
    verdicts: dict[str, dict] = {}
    if not VERDICT_DIR.exists():
        return verdicts
    for path in sorted(VERDICT_DIR.glob("verdict_*.json")):
        payload = json.loads(path.read_text())
        # Accept either {batch_index, verdicts:[...]} or a raw list.
        rows = payload.get("verdicts") if isinstance(payload, dict) else payload
        batch_index = payload.get("batch_index") if isinstance(payload, dict) else None
        for row in rows:
            pid = row.get("pid")
            if not pid:
                continue
            verdicts[pid] = {
                "verdict": row.get("verdict"),
                "rationale": row.get("rationale", ""),
                "confidence": row.get("confidence"),
                "batch_index": batch_index,
                "verdict_file": path.name,
            }
    return verdicts


def load_skipped_pids() -> set[str]:
    if not SKIPPED.exists():
        return set()
    pids = set()
    with SKIPPED.open() as f:
        for line in f:
            r = json.loads(line)
            if r.get("pid"):
                pids.add(r["pid"])
    return pids


REPLY_URL_RE = re.compile(r"https://pastebin\.k4be\.pl/view/([a-z0-9]+)")


def _extract_reply_parent(j: dict) -> tuple[str | None, str | None, str | None]:
    """Return (parent_pid, parent_title, parent_name) from an /api/paste response."""
    inreply = j.get("inreply")
    if not isinstance(inreply, dict):
        return None, None, None
    url = inreply.get("url") or ""
    m = REPLY_URL_RE.match(url)
    return (m.group(1) if m else None, inreply.get("title"), inreply.get("name"))


def build_revision(body_row: dict, inclusion: dict) -> dict:
    j = body_row.get("body_json") or {}
    pid = body_row.get("pid") or j.get("pid")
    title = j.get("title") or body_row.get("index_title") or ""
    name = j.get("name") or body_row.get("index_name") or ""
    raw = j.get("raw") or ""
    replyto_pid, replyto_title, replyto_name = _extract_reply_parent(j)
    body_bytes = raw.encode("utf-8", errors="replace")
    created_str = j.get("created")
    try:
        created_int = int(created_str) if created_str is not None else None
    except (TypeError, ValueError):
        created_int = None
    if created_int is not None:
        write_date = dt.datetime.fromtimestamp(created_int, tz=dt.timezone.utc).isoformat()
    else:
        write_date = None

    return {
        "rev_id": f"pastebin-k4be~{pid}@1",
        "page_id": f"pastebin-k4be/{pid}",
        "page_key": f"pastebin-k4be~{pid}",
        "wiki": "pastebin-k4be",
        "name": pid,
        "seq": 1,
        "body_len": len(body_bytes),
        "body_sha256": hashlib.sha256(body_bytes).hexdigest(),
        "lines": raw.count("\n") + (1 if raw else 0),
        "diff_base": (
            f"pastebin-k4be/{replyto_pid}" if replyto_pid else None
        ),
        "diff_base_reason": (
            "stikked_replyto_chain" if replyto_pid else "single_revision_paste_site"
        ),
        "hunks": None,
        "replyto_pid": replyto_pid,
        "replyto_title": replyto_title,
        "replyto_name": replyto_name,
        "label": name,
        "label_source": "pastebin_k4be_api_paste_name",
        "ip16": None,
        "time": write_date,
        "time_grade": "api_paste_created_field",
        "winning_clock": "pastebin_k4be_created_utc",
        "uncertainty_seconds": None,
        "request_time": None,
        "success_time": None,
        "recent_changes_time": None,
        "write_date": write_date,
        "archived_at": body_row.get("request_time_utc"),
        "request_action": None,
        "change_summary": None,
        "related_event_id": None,
        "relation_type": None,
        "round_id": None,
        "body": raw,
        "body_encoding": "raw_utf8",
        "wiki_revision_number": None,
        "is_new_page": True,
        "is_minor_edit": None,
        "body_availability": "full_source",
        "source_url": j.get("url") or f"https://pastebin.k4be.pl/view/{pid}",
        "source_title": title,
        "source_api_endpoint": f"https://pastebin.k4be.pl/api/paste/{pid}",
        "site_hits": j.get("hits"),
        "site_hits_updated": j.get("hits_updated"),
        "site_lang_code": j.get("lang_code"),
        "site_lang": j.get("lang"),
        "site_expire_utc": (
            dt.datetime.fromtimestamp(int(j["expire"]), tz=dt.timezone.utc).isoformat()
            if j.get("expire") and str(j.get("expire")).isdigit() and int(j["expire"]) > 0
            else None
        ),
        "inclusion_reason": inclusion["reason"],
        "verdict": inclusion.get("verdict"),
        "verdict_rationale": inclusion.get("rationale"),
        "verdict_confidence": inclusion.get("confidence"),
        "verdict_batch_index": inclusion.get("batch_index"),
    }


def build_page(rev: dict) -> dict:
    return {
        "page_id": rev["page_id"],
        "page_key": rev["page_key"],
        "wiki": rev["wiki"],
        "name": rev["name"],
        "n_revisions": 1,
        "first_seen": rev["write_date"],
        "last_seen": rev["write_date"],
        "source_url": rev["source_url"],
        "title": rev["source_title"],
    }


def build_event(rev: dict) -> dict:
    return {
        "event_id": f"{rev['rev_id']}#save",
        "page_id": rev["page_id"],
        "rev_id": rev["rev_id"],
        "wiki": rev["wiki"],
        "time": rev["write_date"],
        "action": "save",
        "label": rev["label"],
    }


def build_label(name: str, count: int) -> dict:
    return {"label": name, "wiki": "pastebin-k4be", "n_revisions": count}


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--include-verdicts",
        nargs="+",
        default=["swarm", "unclear"],
        help="Which subagent verdict values to include. Default: swarm + unclear.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write agent-logs/pastebin-k4be/; print counts only.",
    )
    args = ap.parse_args()

    bodies = load_bodies()
    verdicts = load_verdicts()
    corpus_pids = load_skipped_pids()

    revisions: list[dict] = []
    inclusion_counts = {"shellac_import": 0, "subagent_verdict": 0}
    verdict_dist: dict[str, int] = {}
    excluded_counts: dict[str, int] = {"human": 0, "unrated": 0}

    for pid, body_row in bodies.items():
        if pid in corpus_pids:
            inclusion = {"reason": "shellac_import"}
            revisions.append(build_revision(body_row, inclusion))
            inclusion_counts["shellac_import"] += 1
            continue
        v = verdicts.get(pid)
        if not v:
            excluded_counts["unrated"] += 1
            continue
        verdict = v.get("verdict")
        verdict_dist[verdict] = verdict_dist.get(verdict, 0) + 1
        if verdict in args.include_verdicts:
            inclusion = {
                "reason": "subagent_verdict",
                "verdict": verdict,
                "rationale": v.get("rationale"),
                "confidence": v.get("confidence"),
                "batch_index": v.get("batch_index"),
            }
            revisions.append(build_revision(body_row, inclusion))
            inclusion_counts["subagent_verdict"] += 1
        else:
            excluded_counts[verdict or "unrated"] = excluded_counts.get(verdict or "unrated", 0) + 1

    # Sort by write_date, oldest first, unstable dates last.
    revisions.sort(key=lambda r: (r["write_date"] is None, r["write_date"] or ""))

    pages = [build_page(r) for r in revisions]
    events = [build_event(r) for r in revisions]

    label_counts: dict[str, int] = {}
    for r in revisions:
        label_counts[r["label"]] = label_counts.get(r["label"], 0) + 1
    labels = [build_label(n, c) for n, c in sorted(label_counts.items(), key=lambda x: -x[1])]

    print(f"revisions written: {len(revisions)}")
    print(f"  inclusion_counts: {inclusion_counts}")
    print(f"  verdict distribution among subagent-reviewed: {verdict_dist}")
    print(f"  excluded (subagent said 'human' or unrated): {excluded_counts}")

    if args.dry_run:
        return 0

    EXPORT.mkdir(parents=True, exist_ok=True)
    (EXPORT / "revisions.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in revisions) + ("\n" if revisions else "")
    )
    (EXPORT / "pages.jsonl").write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in pages) + ("\n" if pages else "")
    )
    (EXPORT / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + ("\n" if events else "")
    )
    (EXPORT / "labels.jsonl").write_text(
        "\n".join(json.dumps(l, ensure_ascii=False) for l in labels) + ("\n" if labels else "")
    )

    manifest = {
        "generated_at": utc_now(),
        "source": {
            "wiki_name": "pastebin-k4be",
            "kind": "public_paste_site",
            "base_url": "https://pastebin.k4be.pl",
            "engine": "stikked (see tmp/stikked-src/)",
            "endpoints": {
                "index": "https://pastebin.k4be.pl/lists/{offset}",
                "body": "https://pastebin.k4be.pl/api/paste/{pid}",
            },
            "scraper": "scrape/pastebin_k4be.py",
            "classifier": "analyses/pastebin-k4be-full-classify/ (subagent verdicts + shellac import)",
        },
        "cut": {
            "kind": "full_site_scrape_then_agent_filter",
            "included_verdicts": args.include_verdicts,
            "inclusion_counts": inclusion_counts,
            "excluded_counts": excluded_counts,
            "verdict_distribution": verdict_dist,
        },
        "wiki_tz_offset": "UTC (paste `created` field is unix epoch UTC per stikked source)",
        "counts": {
            "revisions": {"value": len(revisions)},
            "pages": {"value": len(pages)},
            "labels": {"value": len(labels)},
            "events": {"value": len(events)},
        },
        "per_wiki": {
            "pastebin-k4be": {
                "revisions": {"value": len(revisions)},
                "pages": {"value": len(pages)},
                "body_bytes": {"value": sum(r["body_len"] for r in revisions)},
            }
        },
        "limitations": [
            "Bodies fetched from live site 2026-09-07. Pastes older than the site's expiry window are absent by construction.",
            "Author attribution is the free-text `name` field on the paste. Stikked auto-generates colour+animal names when the poster leaves it blank; a paste labelled 'Beige Meerkat' may be from any anonymous poster.",
            "Timestamps come from the `created` field returned by /api/paste/{pid}. We do not independently verify them.",
            "The classifier deliberately errs on the side of inclusion. Verdict 'unclear' rows are included alongside 'swarm' rows. Downstream analyses should filter by `inclusion_reason` and `verdict` if they need higher precision.",
            "IPs are not available from this endpoint; `ip16` is null.",
        ],
        "endpoints_probed": [
            "https://pastebin.k4be.pl/lists/{offset}",
            "https://pastebin.k4be.pl/api/paste/{pid}",
        ],
    }
    (EXPORT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # SHA256SUMS over the five data files.
    files_for_sums = ["manifest.json", "revisions.jsonl", "pages.jsonl",
                      "events.jsonl", "labels.jsonl"]
    lines = []
    for name in files_for_sums:
        p = EXPORT / name
        if p.exists():
            lines.append(f"{sha256sum(p)}  {name}")
    (EXPORT / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    print(f"wrote export to {EXPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
