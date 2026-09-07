#!/usr/bin/env python3
"""Merge shellac corpus + wayback scrape + subagent verdicts into agent-logs/paste-linuxiarz/.

Inputs
------
  * agent-logs/pastes/revisions.jsonl - shellac-imported linuxiarz pastes
    (219 rows). Every row is treated as swarm-verdict by definition.
  * scrape/outputs/paste-linuxiarz/bodies.jsonl - one row per wayback-fetched
    paste (~193 rows for wayback-only pids, given the --skip-known-shellac
    flag).
  * outputs/verdicts/verdict_*.json - subagent output per batch.

Output
------
  * agent-logs/paste-linuxiarz/{README.md, manifest.json, revisions.jsonl,
    pages.jsonl, events.jsonl, labels.jsonl, SHA256SUMS}

The wayback-only bodies may have raw_body == "" when wayback did not archive
/view/raw/<pid>. In that case we still keep the row (title, name, ago from
the /view page carry information) but flag body_availability = "wayback_view_page_only".
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BODIES = ROOT / "scrape" / "outputs" / "paste-linuxiarz" / "bodies.jsonl"
CORPUS = ROOT / "agent-logs" / "pastes" / "revisions.jsonl"

OUT_DIR_LOCAL = Path(__file__).parent / "outputs"
VERDICT_DIR = OUT_DIR_LOCAL / "verdicts"

EXPORT = ROOT / "agent-logs" / "paste-linuxiarz"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_shellac_linuxiarz() -> list[dict]:
    """Return the shellac corpus rows for linuxiarz pastes."""
    out = []
    with CORPUS.open() as f:
        for line in f:
            r = json.loads(line)
            if r.get("page_id", "").startswith("pastes/linuxiarz/"):
                out.append(r)
    return out


def load_wayback_bodies() -> dict[str, dict]:
    if not BODIES.exists():
        return {}
    by_pid = {}
    with BODIES.open() as f:
        for line in f:
            r = json.loads(line)
            if r.get("pid"):
                by_pid[r["pid"]] = r
    return by_pid


def load_verdicts() -> dict[str, dict]:
    verdicts: dict[str, dict] = {}
    if not VERDICT_DIR.exists():
        return verdicts
    for path in sorted(VERDICT_DIR.glob("verdict_*.json")):
        payload = json.loads(path.read_text())
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


def build_shellac_revision(r: dict) -> dict:
    """Rewrap a shellac corpus row into the paste-linuxiarz schema."""
    pid = r["page_id"].split("/", 2)[2]
    return {
        "rev_id": f"paste-linuxiarz~{pid}@1",
        "page_id": f"paste-linuxiarz/{pid}",
        "page_key": f"paste-linuxiarz~{pid}",
        "wiki": "paste-linuxiarz",
        "name": pid,
        "seq": 1,
        "body_len": r.get("body_len"),
        "body_sha256": r.get("body_sha256"),
        "lines": r.get("lines"),
        "diff_base": None,
        "diff_base_reason": "shellac_import_no_reply_graph",
        "hunks": None,
        "replyto_pid": None,
        "replyto_title": None,
        "replyto_name": None,
        "label": r.get("label", ""),
        "label_source": "shellac_recovered_author",
        "ip16": None,
        "time": r.get("time"),
        "time_grade": r.get("time_grade"),
        "winning_clock": r.get("winning_clock"),
        "uncertainty_seconds": r.get("uncertainty_seconds"),
        "write_date": r.get("write_date"),
        "archived_at": r.get("archived_at"),
        "body": r.get("body", ""),
        "body_encoding": "raw_utf8",
        "is_new_page": True,
        "is_minor_edit": None,
        "body_availability": r.get("body_availability", "full_source"),
        "source_url": r.get("shellac_source_url"),
        "source_title": r.get("shellac_title", ""),
        "source_api_endpoint": None,
        "site_hits": None,
        "site_hits_updated": None,
        "site_lang_code": None,
        "site_lang": None,
        "site_expire_utc": None,
        "inclusion_reason": "shellac_import",
        "verdict": None,
        "verdict_rationale": None,
        "verdict_confidence": None,
        "verdict_batch_index": None,
        "shellac_doc_id": r.get("shellac_doc_id"),
    }


def build_wayback_revision(body_row: dict, verdict: dict) -> dict:
    pid = body_row["pid"]
    raw = body_row.get("raw_body") or ""
    body_bytes = raw.encode("utf-8", errors="replace")
    ago = body_row.get("view_ago") or ""
    return {
        "rev_id": f"paste-linuxiarz~{pid}@1",
        "page_id": f"paste-linuxiarz/{pid}",
        "page_key": f"paste-linuxiarz~{pid}",
        "wiki": "paste-linuxiarz",
        "name": pid,
        "seq": 1,
        "body_len": len(body_bytes),
        "body_sha256": hashlib.sha256(body_bytes).hexdigest() if raw else None,
        "lines": raw.count("\n") + (1 if raw else 0),
        "diff_base": None,
        "diff_base_reason": "wayback_scrape_no_reply_graph",
        "hunks": None,
        "replyto_pid": None,
        "replyto_title": None,
        "replyto_name": None,
        "label": body_row.get("view_name") or "",
        "label_source": "linuxiarz_view_page_from_field",
        "ip16": None,
        "time": None,
        "time_grade": f"wayback_ago_field:{ago!r}",
        "winning_clock": None,
        "uncertainty_seconds": None,
        "write_date": None,
        "archived_at": body_row.get("request_time_utc"),
        "body": raw,
        "body_encoding": "raw_utf8" if raw else None,
        "is_new_page": True,
        "is_minor_edit": None,
        "body_availability": "full_source" if raw else "wayback_view_page_only",
        "source_url": f"https://paste.linuxiarz.pl/view/{pid}",
        "source_title": body_row.get("view_title", ""),
        "source_api_endpoint": None,
        "site_hits": body_row.get("view_hits"),
        "site_hits_updated": None,
        "site_lang_code": None,
        "site_lang": body_row.get("view_lang"),
        "site_expire_utc": None,
        "wb_timestamp": body_row.get("wb_timestamp"),
        "wb_raw_url": body_row.get("raw_url"),
        "wb_view_url": body_row.get("view_url"),
        "inclusion_reason": "subagent_verdict",
        "verdict": verdict.get("verdict"),
        "verdict_rationale": verdict.get("rationale"),
        "verdict_confidence": verdict.get("confidence"),
        "verdict_batch_index": verdict.get("batch_index"),
        "reply_names_on_view_page": [
            rp.get("name") for rp in (body_row.get("view_replies") or [])
        ],
    }


def build_page(rev: dict) -> dict:
    return {
        "page_id": rev["page_id"],
        "page_key": rev["page_key"],
        "wiki": rev["wiki"],
        "name": rev["name"],
        "n_revisions": 1,
        "first_seen": rev.get("write_date") or rev.get("archived_at"),
        "last_seen": rev.get("write_date") or rev.get("archived_at"),
        "source_url": rev.get("source_url"),
        "title": rev.get("source_title"),
    }


def build_event(rev: dict) -> dict:
    return {
        "event_id": f"{rev['rev_id']}#save",
        "page_id": rev["page_id"],
        "rev_id": rev["rev_id"],
        "wiki": rev["wiki"],
        "time": rev.get("write_date") or rev.get("archived_at"),
        "action": "save",
        "label": rev.get("label"),
    }


def build_label(name: str, count: int) -> dict:
    return {"label": name, "wiki": "paste-linuxiarz", "n_revisions": count}


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-verdicts", nargs="+", default=["swarm", "unclear"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    shellac_rows = load_shellac_linuxiarz()
    wayback = load_wayback_bodies()
    verdicts = load_verdicts()

    revisions: list[dict] = []
    inclusion_counts = {"shellac_import": 0, "subagent_verdict": 0}
    verdict_dist: dict[str, int] = {}
    excluded_counts: dict[str, int] = {"human": 0, "unrated": 0}

    shellac_pids: set[str] = set()
    for r in shellac_rows:
        pid = r["page_id"].split("/", 2)[2]
        shellac_pids.add(pid)
        revisions.append(build_shellac_revision(r))
        inclusion_counts["shellac_import"] += 1

    for pid, body_row in wayback.items():
        if pid in shellac_pids:
            continue
        v = verdicts.get(pid)
        if not v:
            excluded_counts["unrated"] += 1
            continue
        verdict = v.get("verdict")
        verdict_dist[verdict] = verdict_dist.get(verdict, 0) + 1
        if verdict in args.include_verdicts:
            revisions.append(build_wayback_revision(body_row, v))
            inclusion_counts["subagent_verdict"] += 1
        else:
            excluded_counts[verdict or "unrated"] = excluded_counts.get(verdict or "unrated", 0) + 1

    revisions.sort(key=lambda r: (r.get("write_date") is None, r.get("write_date") or ""))

    pages = [build_page(r) for r in revisions]
    events = [build_event(r) for r in revisions]

    label_counts: dict[str, int] = {}
    for r in revisions:
        label_counts[r["label"]] = label_counts.get(r["label"], 0) + 1
    labels = [build_label(n, c) for n, c in sorted(label_counts.items(), key=lambda x: -x[1])]

    print(f"revisions written: {len(revisions)}")
    print(f"  inclusion_counts: {inclusion_counts}")
    print(f"  verdict distribution: {verdict_dist}")
    print(f"  excluded (human or unrated): {excluded_counts}")

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
            "wiki_name": "paste-linuxiarz",
            "kind": "public_paste_site",
            "base_url": "https://paste.linuxiarz.pl",
            "engine": "stikked (see tmp/stikked-src/)",
            "route": "wayback_machine_fallback",
            "note": "Live paste.linuxiarz.pl blocks /api/* (403) and /lists, /view/* (404) as of 2026-09-07. Bodies fetched via Internet Archive.",
            "endpoints": {
                "wayback_cdx": "https://web.archive.org/cdx/search/cdx?url=paste.linuxiarz.pl/view/*",
                "wayback_raw": "https://web.archive.org/web/{ts}id_/https://paste.linuxiarz.pl/view/raw/{pid}",
                "wayback_view": "https://web.archive.org/web/{ts}/https://paste.linuxiarz.pl/view/{pid}",
            },
            "scraper": "scrape/paste_linuxiarz_wayback.py",
            "classifier": "analyses/paste-linuxiarz-full-classify/",
        },
        "cut": {
            "kind": "shellac_import_plus_wayback_agent_filter",
            "included_verdicts": args.include_verdicts,
            "inclusion_counts": inclusion_counts,
            "excluded_counts": excluded_counts,
            "verdict_distribution": verdict_dist,
        },
        "wiki_tz_offset": None,
        "counts": {
            "revisions": {"value": len(revisions)},
            "pages": {"value": len(pages)},
            "labels": {"value": len(labels)},
            "events": {"value": len(events)},
        },
        "per_wiki": {
            "paste-linuxiarz": {
                "revisions": {"value": len(revisions)},
                "pages": {"value": len(pages)},
                "body_bytes": {"value": sum((r.get("body_len") or 0) for r in revisions)},
            }
        },
        "limitations": [
            "Live site blocks anon requests. Wayback Machine is the only route to this content today.",
            "Wayback only holds ~370 distinct pids for this host. The live site had 1300+ paste offsets in /lists indexes; we cannot enumerate the full paste history.",
            "Wayback lacks /view/raw/<pid> archives for many pids. Those rows carry body_availability='wayback_view_page_only'.",
            "Shellac timestamps carry through unchanged. Wayback rows have write_date=null because /api/paste/<pid>.created is unavailable; the /view page 'N Years ago' text is captured as time_grade and does not resolve to an absolute UTC time.",
            "Some archived pastes contain personal WiFi/API credentials. The subagent classifier deliberately leans human on this host to avoid re-publishing personal data. Downstream analyses that want higher recall of swarm content should re-run the subagents with a different bias.",
            "IPs are unavailable everywhere.",
        ],
        "endpoints_probed_on_live_site": {
            "/api/random": 403,
            "/api/paste/<pid>": 403,
            "/lists": 404,
            "/lists/<offset>": 404,
            "/view/<pid>": 404,
            "/view/raw/<pid>": 404,
            "/": 200,
            "/about": 200,
        },
    }
    (EXPORT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

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
