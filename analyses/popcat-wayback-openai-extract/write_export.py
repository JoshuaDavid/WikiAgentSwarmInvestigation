#!/usr/bin/env python3
"""Turn scrape/outputs/popcat-wayback/ into agent-logs/popcat-wayback/.

Schema follows agent-logs/shorteners/ (shellac reading pack shape):
one page per short_code, one revision per /info snapshot, one save event
per revision, one label row (empty string) covering everything.

See ./README.md for full pipeline documentation.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRAPE = REPO / "scrape" / "outputs" / "popcat-wayback"
OUT = REPO / "agent-logs" / "popcat-wayback"
INFO_DIR = SCRAPE / "info_pages"

WIKI = "popcat-wayback"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def parse_ddmmyyyy(s: str | None) -> str | None:
    """Return ISO-8601 date for 'DD/MM/YYYY'."""
    if not s:
        return None
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", s.strip())
    if not m:
        return None
    d, mo, y = m.groups()
    y_i = int(y)
    if y_i < 100:
        y_i += 2000
    try:
        return dt.date(y_i, int(mo), int(d)).isoformat()
    except ValueError:
        return None


def wayback_ts_to_iso(ts: str) -> str:
    """'20260909024251' -> '2026-09-09T02:42:51+00:00'."""
    return (
        f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}T"
        f"{ts[8:10]}:{ts[10:12]}:{ts[12:14]}+00:00"
    )


def body_from_info(code: str, dest: str, clicks: int) -> str:
    """Reproduce the 5-line body shape used by shorteners/popcat/*."""
    return f"{dest}\n{dest}\n{code}\n/{code}/info\n{clicks}"


def main() -> None:
    parsed = [json.loads(l) for l in (SCRAPE / "info_parsed.jsonl").open()]
    parsed.sort(key=lambda r: r["short_code"])

    # Load listing_rows so we know the click count observed on the listing
    # (in case /info parse missed views for one). We prefer /info views.
    listing_by_code: dict[str, dict] = {}
    for l in (SCRAPE / "listing_rows.jsonl").open():
        r = json.loads(l)
        listing_by_code.setdefault(r["short_code"], r)

    now = utc_now()

    pages = []
    revisions = []
    events = []
    for rec in parsed:
        code = rec["short_code"]
        page_id = f"{WIKI}/{code}"
        page_key = f"{WIKI}~{code}"
        rev_id = f"{page_key}@1"
        event_id = f"save:{rev_id}"

        dest = rec.get("redirects_to") or ""
        clicks = rec.get("total_views")
        if clicks is None:
            # fall back to listing click count
            clicks = listing_by_code.get(code, {}).get("clicks", 0)
        body = body_from_info(code, dest, int(clicks))
        body_bytes = body.encode("utf-8")

        ts_iso = wayback_ts_to_iso(rec["wayback_timestamp"])
        created_iso = parse_ddmmyyyy(rec.get("created"))

        pages.append({
            "page_id": page_id,
            "page_key": page_key,
            "wiki": WIKI,
            "name": code,
            "bucket": code[:1],
            "page_family": "off_store_unclassified",
            "page_family_cohort": None,
            "page_family_confidence": None,
            "page_family_method": None,
            "page_family_source": "none",
            "n_revs": 1,
            "n_revs_before": None,
            "first_write": ts_iso,
            "last_write": ts_iso,
            "body_bytes": len(body_bytes),
            "deleted_live": None,
            "live_body_variant": None,
            "head_differs_from_live": None,
            "n_deletions": 0,
            "n_recreations": 0,
            "labels": [""],
            "n_labels": 1,
            "n_ips": None,
            "n_ip16": None,
            "wiki_head_revision_number": None,
            "source_group": f"popcat/{code}",
            "source_url_example": rec["wayback_url"],
        })

        revisions.append({
            "rev_id": rev_id,
            "page_id": page_id,
            "page_key": page_key,
            "wiki": WIKI,
            "name": code,
            "seq": 1,
            "rcs_rev": None,
            "rcs_path": None,
            "body_len": len(body_bytes),
            "body_sha256": sha256_bytes(body_bytes),
            "lines": body.count("\n") + 1,
            "diff_base": None,
            "diff_base_reason": "not_captured_by_shellac_pack",
            "hunks": None,
            "label": "",
            "label_source": "unknown",
            "ip16": None,
            "time": ts_iso,
            "time_grade": "wayback_capture_time",
            "winning_clock": "wayback_capture_time_utc",
            "uncertainty_seconds": None,
            "request_time": None,
            "success_time": None,
            "recent_changes_time": None,
            "write_date": ts_iso,
            "archived_at": now,
            "request_action": None,
            "change_summary": None,
            "related_event_id": None,
            "relation_type": None,
            "round_id": None,
            "body": body,
            "body_encoding": "raw_utf8",
            "wiki_revision_number": None,
            "is_new_page": True,
            "is_minor_edit": None,
            "body_availability": "full_source",
            "shellac_doc_id": None,
            "shellac_source_type": None,
            "shellac_source_group": None,
            "shellac_source_url": None,
            "shellac_title": None,
            "shellac_occurrences": None,
            "shellac_timestamp_basis": None,
            "wayback_timestamp": rec["wayback_timestamp"],
            "wayback_url": rec["wayback_url"],
            "popcat_created_date": created_iso,
            "popcat_days_active": rec.get("days_active"),
            "popcat_total_views": rec.get("total_views"),
            "popcat_redirects_to": dest,
        })

        events.append({
            "event_id": event_id,
            "event_type": "save",
            "time": ts_iso,
            "time_grade": "wayback_capture_time",
            "wiki": WIKI,
            "revision_ref": rev_id,
        })

    labels = [{
        "label": "",
        "stored_revisions": len(revisions),
        "first_write": min((r["time"] for r in revisions), default=None),
        "last_write": max((r["time"] for r in revisions), default=None),
        "stored_revision_ips": None,
        "stored_revision_ip16": None,
        "pages": sorted(p["page_id"] for p in pages),
        "stored_revision_pages": len(pages),
        "wikis": [WIKI],
        "is_human_handle": None,
        "save_requests": None,
        "save_request_ips": None,
        "save_request_ip16": None,
        "save_request_pages": None,
        "save_request_source": "wayback_popcat_scrape_2026-09-08",
    }]

    total_body_bytes = sum(p["body_bytes"] for p in pages)

    manifest = {
        "generated_at": now,
        "source": {
            "wiki_name": WIKI,
            "kind": "public_url_shortener_redirect_info_pages",
            "hosts_observed": ["url.popcat.xyz"],
            "engine": "Zero Two URL shortener (compromised endpoint - see incident)",
            "scraper": "scrape/popcat_wayback.py (Wayback Machine, id_ playback)",
        },
        "cut": {
            "kind": "wayback_listing_openai_filter",
            "wayback_listing_date": "20260908",
            "listing_pages": [1, 2, 3, 4, 5, 6, 7, 8, 9],
            "openai_code_regex": r"^(?:oai|OAI|Oai)",
            "openai_dest_regex": r"(chat\.openai\.com|chatgpt\.com|openai\.com|api\.openai|platform\.openai)",
        },
        "wiki_tz_offset": 0,  # /info pages are UTC on Wayback timestamps
        "counts": {
            "revisions": {"value": len(revisions)},
            "pages": {"value": len(pages)},
            "labels": {"value": len(labels)},
            "events": {"value": len(events)},
        },
        "per_wiki": {
            WIKI: {
                "revisions": {"value": len(revisions)},
                "pages": {"value": len(pages)},
                "body_bytes": {"value": total_body_bytes},
            }
        },
        "limitations": [
            "One /info snapshot per short_code, not a time-series.",
            "9 of 128 openai-flagged short_codes had no Wayback /info capture "
            "and are excluded from this export. See "
            "scrape/outputs/popcat-wayback/info_missing.txt for the list.",
            "No author, no IP, no request-level metadata.",
            "Wayback rate-limited some fetches; snapshot dates vary "
            "(2026-05 to 2026-09) depending on which capture the CDX call "
            "returned first.",
            "Filter is deterministic (regex on code / destination). It selects "
            "swarm-authored codes with high precision but is not exhaustive - "
            "swarm codes not starting with `oai` and not pointing at an OpenAI "
            "host are excluded.",
        ],
        "endpoints_probed": None,
        "attribution": {
            "prepared_by": "collusionwiki investigator",
            "scrape_run_utc": now,
            "note": "Wayback Machine snapshots of https://url.popcat.xyz/ listing "
                    "pages (?page=1..9 on 2026-09-08) and /<code>/info pages "
                    "for the openai-flagged subset. Body shape mirrors "
                    "agent-logs/shorteners/popcat/*.",
        },
    }

    # Wipe + rewrite output dir.
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*"):
        if p.is_file():
            p.unlink()

    def dump_jsonl(fname: str, rows: list[dict]) -> None:
        (OUT / fname).write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
        )

    dump_jsonl("pages.jsonl", pages)
    dump_jsonl("revisions.jsonl", revisions)
    dump_jsonl("events.jsonl", events)
    dump_jsonl("labels.jsonl", labels)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                        encoding="utf-8")

    # SHA256SUMS covers all .jsonl + manifest.json.
    sums_lines = []
    for name in sorted(["events.jsonl", "labels.jsonl", "manifest.json",
                        "pages.jsonl", "revisions.jsonl"]):
        sums_lines.append(f"{sha256_file(OUT / name)}  {name}")
    (OUT / "SHA256SUMS").write_text("\n".join(sums_lines) + "\n",
                                     encoding="utf-8")

    print(f"wrote {len(pages)} pages / {len(revisions)} revisions to {OUT}")


if __name__ == "__main__":
    main()
