#!/usr/bin/env python3
"""Merge corpus + scrape + verdicts into agent-logs/<name>/ for one host.

For live-stikked hosts, the schema mirrors agent-logs/pastebin-k4be/.
For wayback hosts, the schema mirrors agent-logs/paste-linuxiarz/.

Usage:
    python3 write_export.py --name <slug> --host <base_url> \\
        --route <live_stikked_lists|live_stikked_api_random|wayback_view> \\
        --source-kind <live_stikked|wayback> \\
        [--corpus-prefix <shellac_prefix>] \\
        [--export-name <agent_logs_dir_name>] \\
        [--include-verdicts swarm unclear] \\
        [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_OUT = Path(__file__).parent / "outputs"

REPLY_URL_RE = re.compile(r"https?://[^/]+/view/([a-z0-9]+)")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_bodies(name: str) -> dict[str, dict]:
    p = ROOT / "scrape" / "outputs" / name / "bodies.jsonl"
    by_pid = {}
    if not p.exists():
        return by_pid
    for line in p.open():
        r = json.loads(line)
        pid = r.get("pid") or (r.get("body_json") or {}).get("pid")
        if pid:
            by_pid[pid] = r
    return by_pid


def load_shellac_rows(prefix: str) -> list[dict]:
    p = ROOT / "agent-logs" / "pastes" / "revisions.jsonl"
    needle = f"pastes/{prefix}/"
    out = []
    if not p.exists() or not prefix:
        return out
    for line in p.open():
        r = json.loads(line)
        if r.get("page_id", "").startswith(needle):
            out.append(r)
    return out


def load_verdicts(name: str) -> dict[str, dict]:
    d = LOCAL_OUT / name / "verdicts"
    verdicts: dict[str, dict] = {}
    if not d.exists():
        return verdicts
    for path in sorted(d.glob("verdict_*.json")):
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


def _extract_reply_parent(j: dict) -> tuple[str | None, str | None, str | None]:
    inreply = j.get("inreply") if isinstance(j, dict) else None
    if not isinstance(inreply, dict):
        return None, None, None
    url = inreply.get("url") or ""
    m = REPLY_URL_RE.match(url)
    return (m.group(1) if m else None, inreply.get("title"), inreply.get("name"))


def build_live_revision(body_row: dict, inclusion: dict, export_name: str) -> dict:
    j = body_row.get("body_json") or {}
    if not isinstance(j, dict):
        j = {}
    pid = body_row.get("pid") or j.get("pid")
    # Prefer body_json.raw; fall back to view_raw_body for API-key-gated hosts.
    raw = j.get("raw") or body_row.get("view_raw_body") or ""
    body_bytes = raw.encode("utf-8", errors="replace")
    created_str = j.get("created")
    try:
        created_int = int(created_str) if created_str is not None else None
    except (TypeError, ValueError):
        created_int = None
    write_date = (
        dt.datetime.fromtimestamp(created_int, tz=dt.timezone.utc).isoformat()
        if created_int is not None else None
    )
    expire_str = j.get("expire")
    try:
        expire_int = int(expire_str) if expire_str is not None else 0
    except (TypeError, ValueError):
        expire_int = 0
    expire_utc = (
        dt.datetime.fromtimestamp(expire_int, tz=dt.timezone.utc).isoformat()
        if expire_int > 0 else None
    )
    replyto_pid, replyto_title, replyto_name = _extract_reply_parent(j)

    return {
        "rev_id": f"{export_name}~{pid}@1",
        "page_id": f"{export_name}/{pid}",
        "page_key": f"{export_name}~{pid}",
        "wiki": export_name,
        "name": pid,
        "seq": 1,
        "body_len": len(body_bytes),
        "body_sha256": hashlib.sha256(body_bytes).hexdigest() if raw else None,
        "lines": raw.count("\n") + (1 if raw else 0),
        "diff_base": f"{export_name}/{replyto_pid}" if replyto_pid else None,
        "diff_base_reason": "stikked_replyto_chain" if replyto_pid else "single_revision_paste_site",
        "hunks": None,
        "replyto_pid": replyto_pid,
        "replyto_title": replyto_title,
        "replyto_name": replyto_name,
        "label": j.get("name") or body_row.get("index_name") or "",
        "label_source": "stikked_api_paste_name",
        "ip16": None,
        "time": write_date,
        "time_grade": "api_paste_created_field",
        "winning_clock": "stikked_created_utc",
        "uncertainty_seconds": None,
        "write_date": write_date,
        "archived_at": body_row.get("request_time_utc"),
        "body": raw,
        "body_encoding": "raw_utf8" if raw else None,
        "is_new_page": True,
        "is_minor_edit": None,
        "body_availability": "full_source" if raw else "empty_body",
        "source_url": j.get("url"),
        "source_title": j.get("title") or body_row.get("index_title") or "",
        "source_api_endpoint": j.get("url") and j["url"].replace("/view/", "/api/paste/"),
        "site_hits": j.get("hits"),
        "site_hits_updated": j.get("hits_updated"),
        "site_lang_code": j.get("lang_code"),
        "site_lang": j.get("lang"),
        "site_expire_utc": expire_utc,
        "inclusion_reason": inclusion["reason"],
        "verdict": inclusion.get("verdict"),
        "verdict_rationale": inclusion.get("rationale"),
        "verdict_confidence": inclusion.get("confidence"),
        "verdict_batch_index": inclusion.get("batch_index"),
    }


def build_wayback_revision(body_row: dict, inclusion: dict, export_name: str, host: str) -> dict:
    pid = body_row["pid"]
    raw = body_row.get("raw_body") or ""
    body_bytes = raw.encode("utf-8", errors="replace")
    ago = body_row.get("view_ago") or ""
    return {
        "rev_id": f"{export_name}~{pid}@1",
        "page_id": f"{export_name}/{pid}",
        "page_key": f"{export_name}~{pid}",
        "wiki": export_name,
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
        "label_source": "stikked_view_page_from_field",
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
        "source_url": f"{host}view/{pid}",
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
        "reply_names_on_view_page": [
            rp.get("name") for rp in (body_row.get("view_replies") or [])
        ],
        "inclusion_reason": inclusion["reason"],
        "verdict": inclusion.get("verdict"),
        "verdict_rationale": inclusion.get("rationale"),
        "verdict_confidence": inclusion.get("confidence"),
        "verdict_batch_index": inclusion.get("batch_index"),
    }


def build_shellac_revision(r: dict, export_name: str) -> dict:
    pid = r["page_id"].split("/", 2)[2]
    return {
        "rev_id": f"{export_name}~{pid}@1",
        "page_id": f"{export_name}/{pid}",
        "page_key": f"{export_name}~{pid}",
        "wiki": export_name,
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
        "inclusion_reason": "shellac_import",
        "verdict": None,
        "verdict_rationale": None,
        "verdict_confidence": None,
        "verdict_batch_index": None,
        "shellac_doc_id": r.get("shellac_doc_id"),
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


def build_label(name: str, wiki: str, count: int) -> dict:
    return {"label": name, "wiki": wiki, "n_revisions": count}


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--host", required=True)
    ap.add_argument("--route", required=True,
                    choices=["live_stikked_lists", "live_stikked_api_random", "wayback_view"])
    ap.add_argument("--source-kind", required=True, choices=["live_stikked", "wayback"])
    ap.add_argument("--corpus-prefix", default=None)
    ap.add_argument("--export-name", default=None,
                    help="agent-logs/<export_name>/; default: --name")
    ap.add_argument("--include-verdicts", nargs="+", default=["swarm", "unclear"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    export_name = args.export_name or args.name
    export_dir = ROOT / "agent-logs" / export_name

    bodies = load_bodies(args.name)
    shellac = load_shellac_rows(args.corpus_prefix) if args.corpus_prefix else []
    verdicts = load_verdicts(args.name)

    revisions: list[dict] = []
    inclusion_counts = {"shellac_import": 0, "subagent_verdict": 0}
    verdict_dist: dict[str, int] = {}
    excluded_counts: dict[str, int] = {}

    shellac_pids: set[str] = set()
    for r in shellac:
        pid = r["page_id"].split("/", 2)[2]
        shellac_pids.add(pid)
        revisions.append(build_shellac_revision(r, export_name))
        inclusion_counts["shellac_import"] += 1

    host_norm = args.host if args.host.endswith("/") else args.host + "/"
    for pid, body_row in bodies.items():
        if pid in shellac_pids:
            continue
        v = verdicts.get(pid)
        if not v:
            excluded_counts["unrated"] = excluded_counts.get("unrated", 0) + 1
            continue
        verdict = v.get("verdict")
        verdict_dist[verdict] = verdict_dist.get(verdict, 0) + 1
        if verdict in args.include_verdicts:
            inclusion = {"reason": "subagent_verdict", "verdict": verdict,
                         "rationale": v.get("rationale"),
                         "confidence": v.get("confidence"),
                         "batch_index": v.get("batch_index")}
            if args.source_kind == "live_stikked":
                revisions.append(build_live_revision(body_row, inclusion, export_name))
            else:
                revisions.append(build_wayback_revision(body_row, inclusion, export_name, host_norm))
            inclusion_counts["subagent_verdict"] += 1
        else:
            excluded_counts[verdict] = excluded_counts.get(verdict, 0) + 1

    revisions.sort(key=lambda r: (r.get("write_date") is None, r.get("write_date") or ""))
    pages = [build_page(r) for r in revisions]
    events = [build_event(r) for r in revisions]
    label_counts: dict[str, int] = {}
    for r in revisions:
        label_counts[r["label"]] = label_counts.get(r["label"], 0) + 1
    labels = [build_label(n, export_name, c) for n, c in sorted(label_counts.items(), key=lambda x: -x[1])]

    print(f"[{args.name}] revisions written: {len(revisions)}")
    print(f"  inclusion_counts: {inclusion_counts}")
    print(f"  verdict distribution: {verdict_dist}")
    print(f"  excluded: {excluded_counts}")

    if args.dry_run:
        return 0

    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "revisions.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in revisions) + ("\n" if revisions else "")
    )
    (export_dir / "pages.jsonl").write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in pages) + ("\n" if pages else "")
    )
    (export_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + ("\n" if events else "")
    )
    (export_dir / "labels.jsonl").write_text(
        "\n".join(json.dumps(l, ensure_ascii=False) for l in labels) + ("\n" if labels else "")
    )

    manifest = {
        "generated_at": utc_now(),
        "source": {
            "wiki_name": export_name,
            "kind": "public_paste_site",
            "base_url": host_norm,
            "engine": "stikked",
            "route": args.route,
            "scraper": "scrape/stikked_scrape.py" if args.source_kind == "live_stikked" else "scrape/paste_linuxiarz_wayback.py",
            "classifier": "analyses/paste-sites-classify/",
        },
        "cut": {
            "kind": ("shellac_import_plus_live_scrape" if args.source_kind == "live_stikked" and shellac
                     else "shellac_import_plus_wayback" if shellac
                     else "live_scrape_only" if args.source_kind == "live_stikked"
                     else "wayback_only"),
            "included_verdicts": args.include_verdicts,
            "inclusion_counts": inclusion_counts,
            "excluded_counts": excluded_counts,
            "verdict_distribution": verdict_dist,
        },
        "counts": {
            "revisions": {"value": len(revisions)},
            "pages": {"value": len(pages)},
            "labels": {"value": len(labels)},
            "events": {"value": len(events)},
        },
        "per_wiki": {
            export_name: {
                "revisions": {"value": len(revisions)},
                "pages": {"value": len(pages)},
                "body_bytes": {"value": sum((r.get("body_len") or 0) for r in revisions)},
            }
        },
        "limitations": [
            "Every include is either shellac-imported (labelled by shellac's weak-signal author recovery) or subagent-verdict (agent-reviewed one-line rationale).",
            "The classifier deliberately errs on the side of inclusion; `unclear` rows are shipped alongside `swarm`. Filter by verdict for higher precision.",
        ] + ([
            "This host is a live scrape; timestamps are the stikked `created` field (unix epoch UTC).",
        ] if args.source_kind == "live_stikked" else [
            "This host was fetched via the Internet Archive Wayback Machine because the live site blocks anon access.",
            "Wayback rows have no absolute UTC time; the `N Years ago` string is preserved in time_grade.",
            "Wayback often archived only /view/<pid>, not /view/raw/<pid>. Rows without recovered text carry body_availability='wayback_view_page_only'.",
        ]),
    }
    (export_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    files_for_sums = ["manifest.json", "revisions.jsonl", "pages.jsonl", "events.jsonl", "labels.jsonl"]
    lines = []
    for name in files_for_sums:
        p = export_dir / name
        if p.exists():
            lines.append(f"{sha256sum(p)}  {name}")
    (export_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    print(f"[{args.name}] wrote export to {export_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
