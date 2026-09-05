#!/usr/bin/env python3
"""MediaWiki API scraper for publictestwiki.com (Miraheze testwiki).

Uses the JSON API at /w/api.php - no HTML scraping. Because MediaWiki exposes
the full API cleanly, this captures more than the ProWiki/UseMod scrapers:

  * RAW wiki source per revision (not HTML-stripped) via prop=revisions.
  * Anonymous editor IPs (MediaWiki exposes user=<IP> when userid=0), so
    ip16 gets populated for anon rows (unlike every other scraper here).
  * Deletion + move + block logs via list=logevents.
  * Stable MediaWiki revision IDs (`revid`) - a strong join key.

Output layout mirrors agent-logs/milkwiki: pages.jsonl, revisions.jsonl,
events.jsonl, labels.jsonl, manifest.json, SHA256SUMS.

Usage:
    publictestwiki.py --name NAME --out OUTDIR [--since ISO] [--sanity] [--sleep S]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

USER_AGENT = "collusionwiki-scraper/1.0 (research; joshuad93@gmail.com)"
DEFAULT_API = "https://publictestwiki.com/w/api.php"
DEFAULT_SINCE = "2026-05-01T00:00:00Z"
DEFAULT_SLEEP = 1.0


def api_call(base: str, params: dict, sleep: float) -> dict:
    q = urllib.parse.urlencode(params)
    url = f"{base}?{q}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    time.sleep(sleep)
    return json.loads(raw)


def paginate(base: str, base_params: dict, key: str, sleep: float) -> list:
    params = dict(base_params)
    out = []
    while True:
        data = api_call(base, params, sleep=sleep)
        out.extend(data.get("query", {}).get(key, []))
        if "continue" not in data:
            break
        params.update(data["continue"])
    return out


def is_ip(user: str | None) -> bool:
    """MediaWiki uses the raw IP as `user` for anon edits (userid=0)."""
    if not user:
        return False
    if "." in user:
        parts = user.split(".")
        return len(parts) == 4 and all(p.isdigit() for p in parts)
    if ":" in user:
        return True  # IPv6
    return False


def ip16(ip: str) -> str | None:
    if not is_ip(ip):
        return None
    if "." in ip:
        parts = ip.split(".")
        return f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else None
    # IPv6 /32 (first two hextets)
    parts = ip.split(":")
    return ":".join(parts[:2]) if len(parts) >= 2 else None


def fetch_rc(base: str, since: str, sleep: float) -> list[dict]:
    params = {
        "action": "query",
        "list": "recentchanges",
        "rcend": since,
        "rclimit": "500",
        "rcprop": "title|user|userid|timestamp|ids|comment|flags|sizes|loginfo",
        "rcdir": "older",
        "rctype": "edit|new|log",
        "format": "json",
        "formatversion": "2",
    }
    return paginate(base, params, "recentchanges", sleep=sleep)


def fetch_revision_content(base: str, revids: list[int], sleep: float) -> dict[int, dict]:
    """Return {revid: {content, sha1, size, ...}}. Batch of up to 50 revids per call."""
    out: dict[int, dict] = {}
    for i in range(0, len(revids), 50):
        batch = revids[i:i + 50]
        params = {
            "action": "query",
            "prop": "revisions",
            "revids": "|".join(str(r) for r in batch),
            "rvprop": "ids|timestamp|user|userid|comment|content|sha1|size|flags",
            "rvslots": "main",
            "format": "json",
            "formatversion": "2",
        }
        data = api_call(base, params, sleep=sleep)
        pages = data.get("query", {}).get("pages", []) or []
        for pg in pages:
            title = pg.get("title")
            pageid = pg.get("pageid")
            for rev in pg.get("revisions", []) or []:
                rvid = rev["revid"]
                slot = rev.get("slots", {}).get("main", {}) or {}
                out[rvid] = {
                    "title": title,
                    "pageid": pageid,
                    "user": rev.get("user"),
                    "userid": rev.get("userid"),
                    "timestamp": rev.get("timestamp"),
                    "comment": rev.get("comment"),
                    "content": slot.get("content"),
                    "content_missing": slot.get("missing", False) or rev.get("suppressed", False),
                    "sha1": rev.get("sha1"),
                    "size": rev.get("size") or slot.get("size"),
                    "parentid": rev.get("parentid"),
                    "minor": rev.get("minor", False),
                }
        badrevids = data.get("query", {}).get("badrevids", {}) or {}
        for rvid_str in badrevids:
            rvid = int(rvid_str)
            out[rvid] = {"content_missing": True, "reason": "badrevid"}
    return out


LOG_TYPES = ("delete", "move", "block", "newusers", "abusefilter")


def fetch_logevents(base: str, since: str, sleep: float) -> list[dict]:
    """MediaWiki's `letype` accepts one value per call - fetch each type separately."""
    all_logs: list[dict] = []
    for letype in LOG_TYPES:
        params = {
            "action": "query",
            "list": "logevents",
            "leend": since,
            "lelimit": "500",
            "leprop": "ids|title|type|user|timestamp|comment|details|tags",
            "ledir": "older",
            "letype": letype,
            "format": "json",
            "formatversion": "2",
        }
        try:
            all_logs.extend(paginate(base, params, "logevents", sleep=sleep))
        except Exception as e:
            print(f"  logevents letype={letype} failed: {e}", file=sys.stderr)
    return all_logs


def scrape(base_api: str, name: str, out: Path, since: str, sleep: float, sanity: bool) -> None:
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    print(f"[{name}] fetching RC since {since} ...", file=sys.stderr)
    rc = fetch_rc(base_api, since, sleep=sleep)
    print(f"[{name}]   {len(rc)} RC entries", file=sys.stderr)

    print(f"[{name}] fetching logevents (delete|move|block) since {since} ...", file=sys.stderr)
    logs = fetch_logevents(base_api, since, sleep=sleep)
    print(f"[{name}]   {len(logs)} log entries", file=sys.stderr)

    # Revids to fetch = those tied to actual page edits (edit + new). Log entries
    # sometimes carry revid=0.
    rev_types = {"edit", "new"}
    revids = [r["revid"] for r in rc if r.get("type") in rev_types and r.get("revid")]
    if sanity:
        revids = revids[:20]
        print(f"[{name}] SANITY: fetching only {len(revids)} revision contents", file=sys.stderr)
    print(f"[{name}] fetching {len(revids)} revision bodies ...", file=sys.stderr)
    rev_content = fetch_revision_content(base_api, revids, sleep=sleep)
    print(f"[{name}]   {len(rev_content)} revision bodies returned", file=sys.stderr)

    if sanity:
        print("\n=== SANITY SUMMARY ===")
        print(f"  api: {base_api}")
        print(f"  since: {since}")
        print(f"  RC entries: {len(rc)}  logevents: {len(logs)}")
        print(f"  revids requested: {len(revids)}  bodies returned: {len(rev_content)}")
        for rvid in list(rev_content)[:3]:
            r = rev_content[rvid]
            body = r.get("content") or ""
            print(f"  rev {rvid}: {r.get('title')!r} user={r.get('user')} ts={r.get('timestamp')} bytes={len(body)}")
            print(f"    body head: {body[:200]!r}")
        return

    out.mkdir(parents=True, exist_ok=True)
    build_output(name=name, out=out, base_api=base_api, since=since, started=started,
                 rc=rc, logs=logs, rev_content=rev_content)


def build_output(*, name: str, out: Path, base_api: str, since: str, started: str,
                 rc: list[dict], logs: list[dict], rev_content: dict[int, dict]) -> None:
    # Order chronologically ascending (RC is newest-first).
    rc_sorted = sorted(rc, key=lambda r: r.get("timestamp", ""))
    logs_sorted = sorted(logs, key=lambda l: l.get("timestamp", ""))

    # Group revisions by page (title).
    page_revs: dict[str, list[dict]] = defaultdict(list)
    for r in rc_sorted:
        if r.get("type") in {"edit", "new"} and r.get("title"):
            page_revs[r["title"]].append(r)

    # ---- revisions.jsonl ----
    seq_by_page: Counter[str] = Counter()
    revisions_out = []
    events_out = []
    for r in rc_sorted:
        title = r.get("title")
        rc_type = r.get("type")
        rvid = r.get("revid") or 0
        content = rev_content.get(rvid, {})
        if rc_type in {"edit", "new"} and title:
            seq_by_page[title] += 1
            seq = seq_by_page[title]
            body = content.get("content")
            body_bytes = body.encode("utf-8") if body is not None else None
            body_sha = hashlib.sha256(body_bytes).hexdigest() if body_bytes is not None else None
            user = r.get("user") or content.get("user")
            userid = r.get("userid") if r.get("userid") is not None else content.get("userid")
            is_anon = (userid == 0) or is_ip(user)
            rev_id = f"{name}~{title}@{seq}"
            page_id = f"{name}/{title}"
            page_key = f"{name}~{title}"
            revisions_out.append({
                "rev_id": rev_id,
                "page_id": page_id,
                "page_key": page_key,
                "wiki": name,
                "name": title,
                "seq": seq,
                "rcs_rev": None,
                "rcs_path": None,
                "body": body,
                "body_len": len(body) if body is not None else None,
                "body_sha256": body_sha,
                "lines": (body.count("\n") + 1) if body else None,
                "diff_base": content.get("parentid"),
                "diff_base_reason": "mediawiki_parentid",
                "hunks": None,
                "label": user,
                "ip16": ip16(user) if is_anon else None,
                "time": r.get("timestamp"),
                "time_grade": "mediawiki_api",
                "winning_clock": "mediawiki_rev_timestamp",
                "uncertainty_seconds": 1,
                "request_time": None,
                "success_time": None,
                "recent_changes_time": r.get("timestamp"),
                "write_date": r.get("timestamp"),
                "archived_at": started,
                "request_action": None,
                "change_summary": r.get("comment"),
                "related_event_id": None,
                "relation_type": None,
                "round_id": None,
                "body_encoding": "raw_utf8" if body is not None else None,
                "wiki_revision_number": rvid,
                "wiki_parent_revision": content.get("parentid"),
                "wiki_sha1": content.get("sha1"),
                "is_new_page": rc_type == "new",
                "is_minor_edit": r.get("minor", False) or content.get("minor", False),
                "is_anonymous": is_anon,
                "body_availability": "full" if body is not None else ("suppressed_or_deleted" if content.get("content_missing") else "not_fetched"),
            })
            events_out.append({
                "event_id": f"save:{rev_id}",
                "event_type": "save",
                "time": r.get("timestamp"),
                "time_grade": "mediawiki_api",
                "wiki": name,
                "revision_ref": rev_id,
                "is_new_page": rc_type == "new",
            })
        elif rc_type == "log":
            # RC log rows are duplicated in list=logevents; we prefer the richer
            # logevents rows below. Skip here to avoid double-counting.
            continue

    # Log events as their own event rows (delete/move/block/newusers/abusefilter).
    for l in logs_sorted:
        lt = l.get("type")
        etype = lt  # preserve the MediaWiki type name verbatim
        events_out.append({
            "event_id": f"{lt}:{l.get('logid')}",
            "event_type": etype,
            "time": l.get("timestamp"),
            "time_grade": "mediawiki_api",
            "wiki": name,
            "actor_label": l.get("user"),
            "title": l.get("title"),
            "change_summary": l.get("comment"),
            "params": l.get("params"),
            "logid": l.get("logid"),
        })
    events_out.sort(key=lambda e: (e.get("time") or "", e.get("event_id")))

    # ---- pages.jsonl ----
    pages_out = []
    for title in sorted(page_revs):
        rows = sorted(page_revs[title], key=lambda x: x.get("timestamp", ""))
        head = rows[-1]
        head_rvid = head.get("revid") or 0
        head_content = rev_content.get(head_rvid, {})
        head_body = head_content.get("content") or ""
        labels_seen = sorted({r.get("user") for r in rows if r.get("user")})
        pages_out.append({
            "page_id": f"{name}/{title}",
            "page_key": f"{name}~{title}",
            "wiki": name,
            "name": title,
            "bucket": title[:1].upper() if title else "",
            "page_family": "off_store_unclassified",
            "page_family_cohort": None,
            "page_family_confidence": None,
            "page_family_method": None,
            "page_family_source": "none",
            "n_revs": len(rows),
            "n_revs_before": None,
            "first_write": rows[0].get("timestamp"),
            "last_write": head.get("timestamp"),
            "body_bytes": len(head_body.encode("utf-8")),
            "deleted_live": False,
            "live_body_variant": "raw_wikitext",
            "head_differs_from_live": False,
            "n_deletions": sum(1 for l in logs_sorted if l.get("title") == title and l.get("type") == "delete"),
            "n_recreations": 0,
            "labels": labels_seen,
            "n_labels": len(labels_seen),
            "n_ips": sum(1 for l in labels_seen if is_ip(l)),
            "n_ip16": len({ip16(l) for l in labels_seen if is_ip(l) and ip16(l)}),
            "wiki_head_revision_number": head_rvid,
        })

    # ---- labels.jsonl ----
    labels_group: dict[str, list[dict]] = defaultdict(list)
    for r in rc_sorted:
        if r.get("type") in {"edit", "new"} and r.get("user"):
            labels_group[r["user"]].append(r)
    labels_out = []
    for label in sorted(labels_group):
        rows = labels_group[label]
        pages_ = sorted({f"{name}/{r['title']}" for r in rows if r.get("title")})
        labels_out.append({
            "label": label,
            "stored_revisions": len(rows),
            "first_write": rows[0].get("timestamp"),
            "last_write": rows[-1].get("timestamp"),
            "stored_revision_ips": 1 if is_ip(label) else None,
            "stored_revision_ip16": ip16(label) if is_ip(label) else None,
            "pages": pages_,
            "stored_revision_pages": len(pages_),
            "wikis": [name],
            "is_human_handle": None,
            "is_anonymous_ip": is_ip(label),
            "save_requests": None,
            "save_request_ips": None,
            "save_request_ip16": None,
            "save_request_pages": None,
            "save_request_source": None,
        })

    # ---- Write ----
    def dump(path: Path, rows):
        with path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    dump(out / "pages.jsonl", pages_out)
    dump(out / "revisions.jsonl", revisions_out)
    dump(out / "events.jsonl", events_out)
    dump(out / "labels.jsonl", labels_out)

    manifest = {
        "generated_at": started,
        "source": {
            "wiki_name": name,
            "api_endpoint": base_api,
            "engine": "MediaWiki 1.45.4 on Miraheze",
            "scraper": "scrape/publictestwiki.py",
        },
        "cut": {
            "kind": "recentchanges_since",
            "since": since,
        },
        "counts": {
            "revisions": {"value": len(revisions_out)},
            "pages": {"value": len(pages_out)},
            "labels": {"value": len(labels_out)},
            "events": {"value": len(events_out)},
            "logevents_by_type": {
                lt: sum(1 for e in events_out if e["event_type"] == lt) for lt in LOG_TYPES
            },
        },
        "per_wiki": {
            name: {
                "revisions": {"value": len(revisions_out)},
                "pages": {"value": len(pages_out)},
                "body_bytes": {"value": sum(p["body_bytes"] for p in pages_out)},
            }
        },
        "limitations": [
            "Bodies are RAW wiki source via prop=revisions - fuller than the ProWiki/UseMod scrapers which HTML-strip. body_encoding='raw_utf8'.",
            "IPs are exposed for anon edits (MediaWiki puts the IP in `user` when userid=0). ip16 is populated for those rows.",
            "Suppressed / RevisionDeleted revisions return content_missing=true; those rows have body=null and body_availability='suppressed_or_deleted'.",
            "The cut is `rcend=since`; the RC list is capped at whatever the API returns before hitting the cut, which for a moderate MediaWiki wiki is typically the full window with pagination.",
            "Only edit/new RC types have per-revision bodies fetched. Log-only RC entries are captured in events.jsonl via list=logevents (delete/move/block), which is richer than RC's log rows.",
        ],
        "endpoints_used": {
            "recent_changes": f"{base_api}?action=query&list=recentchanges&rcend={since}",
            "revisions": f"{base_api}?action=query&prop=revisions&rvprop=content|...",
            "logevents": f"{base_api}?action=query&list=logevents&letype=delete|move|block",
        },
    }
    with (out / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with (out / "SHA256SUMS").open("w", encoding="utf-8") as f:
        for fname in sorted(["pages.jsonl", "revisions.jsonl", "events.jsonl", "labels.jsonl", "manifest.json"]):
            data = (out / fname).read_bytes()
            f.write(f"{hashlib.sha256(data).hexdigest()}  {fname}\n")

    print(f"[{name}] wrote {out}/", file=sys.stderr)
    for fname in ["pages.jsonl", "revisions.jsonl", "events.jsonl", "labels.jsonl", "manifest.json", "SHA256SUMS"]:
        size = (out / fname).stat().st_size
        print(f"  {fname:20s} {size:>8d} bytes", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api", default=DEFAULT_API)
    p.add_argument("--name", default="publictestwiki")
    p.add_argument("--out", type=Path, default=Path("agent-logs/publictestwiki"))
    p.add_argument("--since", default=DEFAULT_SINCE, help="rcend / leend ISO timestamp")
    p.add_argument("--sanity", action="store_true")
    p.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)
    args = p.parse_args()
    scrape(args.api, args.name, args.out, args.since, args.sleep, args.sanity)


if __name__ == "__main__":
    main()
