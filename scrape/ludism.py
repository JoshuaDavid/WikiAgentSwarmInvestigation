#!/usr/bin/env python3
"""Scrape https://www.ludism.org/sandbox (OddMuse) into agent-logs/ludism/.

OddMuse exposes much more than the ProWiki farm:

  * ?action=rss;days=N - RSS feed of recent changes with wall clock times
    (RFC 822 in the pubDate field, UTC).
  * ?action=rc;days=N;all=1 - HTML view of the same window, with one <li>
    per revision. Includes older revisions for the same page too (when
    all=1). Also shows author labels and edit summaries.
  * ?action=history;id=<page> - HTML table of ALL revisions ever for the
    page, dating back years. Each row has rev#, HH:MM UTC, date, author,
    change summary. Not gated to admins on this install.
  * ?action=browse;id=<page>;revision=N;raw=1 - raw wiki source for a
    specific old revision. Returns 200 even for revisions from 2018.
  * ?action=browse;id=<page>;raw=1 - raw wiki source for the current head.

So we can reconstruct the entire history of every page that appears in
the RC window, not just what's visible in the 120-day cut. That's how
OddMuse installations work by default.

Output layout matches agent-logs/milkwiki (the ProWiki-farm shape) as
closely as the richer data lets us. Fields that don't apply are null;
manifest.limitations records the differences.

Usage:
    ludism.py [--base BASE] [--days N] [--sanity] [--sleep S]
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

USER_AGENT = "collusionwiki-scraper/1.0 (research; joshuad93@gmail.com)"
DEFAULT_BASE = "https://www.ludism.org/sandbox"
DEFAULT_NAME = "ludism"
DEFAULT_DAYS = 120
DEFAULT_SLEEP = 1.5


# --------------------------------------------------------------------- HTTP

def fetch(url: str, *, sleep: float = DEFAULT_SLEEP) -> tuple[str, str, int]:
    """Return (text, content_type, http_status).

    The ludism.org host serves 503 when it thinks a client is too aggressive.
    Retry with linear backoff before giving up.
    """
    last_err: Exception | None = None
    for attempt in range(5):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                ctype = resp.headers.get("Content-Type", "")
                status = resp.getcode()
            time.sleep(sleep)
            try:
                return raw.decode("utf-8"), ctype, status
            except UnicodeDecodeError:
                return raw.decode("latin-1", errors="replace"), ctype, status
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504):
                backoff = sleep * (attempt + 2) * 2
                print(f"    HTTP {e.code} on {url}; sleeping {backoff:.1f}s", file=sys.stderr)
                time.sleep(backoff)
                continue
            raise
        except Exception as e:
            last_err = e
            time.sleep(sleep * (attempt + 2))
            continue
    raise last_err  # type: ignore[misc]


def build_url(base: str, **params) -> str:
    # OddMuse accepts both ; and & as separators. Use ; to match the URLs
    # in the traces file and the site's own hrefs.
    parts = [f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items()]
    return f"{base}?{';'.join(parts)}"


# --------------------------------------------------------------------- RSS parse

RSS_ITEM_RE = re.compile(r"<item\b[^>]*>(.*?)</item>", re.DOTALL | re.IGNORECASE)
RSS_TAG_RE = re.compile(r"<([a-z0-9:]+)>([^<]*)</\1>", re.IGNORECASE)


def parse_rss(rss_text: str) -> list[dict]:
    out = []
    for m in RSS_ITEM_RE.finditer(rss_text):
        item = m.group(1)
        tags: dict[str, str] = {}
        for t in RSS_TAG_RE.finditer(item):
            tags[t.group(1).lower()] = html.unescape(t.group(2))
        title = tags.get("title")
        pubdate = tags.get("pubdate")
        # Turn RFC 822 pubDate into ISO 8601 UTC.
        iso = None
        if pubdate:
            try:
                dtparsed = email.utils.parsedate_to_datetime(pubdate)
                if dtparsed.tzinfo is None:
                    dtparsed = dtparsed.replace(tzinfo=dt.timezone.utc)
                iso = dtparsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "+00:00")
            except Exception:
                iso = None
        out.append({
            "page_name": title,
            "date_iso": iso,
            "creator": tags.get("dc:contributor") or tags.get("dc:creator"),
            "description": tags.get("description"),
            "version": int(tags["wiki:version"]) if tags.get("wiki:version", "").isdigit() else None,
            "status": tags.get("wiki:status"),
            "importance": tags.get("wiki:importance"),
        })
    return out


# --------------------------------------------------------------------- RC HTML parse

# One RC list item on OddMuse:
#   <li><span class="time">14:47 UTC</span> (<a class="diff" ...>diff</a> or <span class="new">new</span>)
#      <a class="revision" href="...?action=browse;id=Page[;revision=N]" ...>Page</a> . . . .
#      <a class="author" href=".../AuthorLabel">AuthorLabel</a>
#      <span class="dash"> - </span><strong>edit summary</strong></li>
RC_LI_RE = re.compile(r"<li>(.*?)</li>", re.DOTALL | re.IGNORECASE)
RC_TIME_RE = re.compile(r'<span class="time">\s*(\d{2}:\d{2})\s*UTC\s*</span>', re.IGNORECASE)
RC_DATE_RE = re.compile(r"<p>\s*<strong>\s*(\d{4}-\d{2}-\d{2})\s*</strong>\s*</p>", re.IGNORECASE)
RC_PAGE_RE = re.compile(
    r'<a class="revision" href="[^"]*action=browse[^"]*id=([A-Za-z0-9_][A-Za-z0-9_./%-]*)(?:;revision=(\d+))?[^"]*"',
    re.IGNORECASE,
)
RC_AUTHOR_RE = re.compile(
    r'<a class="author" href="[^"]*sandbox/([^"]+)"[^>]*>([^<]+)</a>',
    re.IGNORECASE,
)
RC_NEW_RE = re.compile(r'<span class="new">new</span>', re.IGNORECASE)
RC_MINOR_RE = re.compile(r'<em>Minor edit</em>', re.IGNORECASE)
RC_SUMMARY_RE = re.compile(r'<span class="dash">[^<]*</span>\s*<strong>([^<]+)</strong>', re.IGNORECASE)


def parse_rc(rc_html: str) -> list[dict]:
    """Return one dict per revision in the RC window, oldest LAST (as displayed)."""
    revisions: list[dict] = []
    current_date: str | None = None
    pos = 0
    while pos < len(rc_html):
        m_date = RC_DATE_RE.search(rc_html, pos)
        m_item = RC_LI_RE.search(rc_html, pos)
        if m_item is None:
            break
        if m_date is not None and m_date.start() < m_item.start():
            current_date = m_date.group(1)
            pos = m_date.end()
            continue
        item = m_item.group(1)
        pos = m_item.end()
        pm = RC_PAGE_RE.search(item)
        am = RC_AUTHOR_RE.search(item)
        tm = RC_TIME_RE.search(item)
        if not (pm and am and tm):
            continue
        # The author display text (inside <a>...</a>) is the label. The URL slug
        # is the WikiWord-form; e.g. label "Ron Hale-Evans" -> slug "Ron_Hale-Evans".
        author_label = html.unescape(am.group(2)).strip()
        page_name = urllib.parse.unquote(pm.group(1))
        rev_num = int(pm.group(2)) if pm.group(2) else None
        m_sum = RC_SUMMARY_RE.search(item)
        summary = html.unescape(m_sum.group(1)).strip() if m_sum else None
        revisions.append({
            "date": current_date,
            "hhmm": tm.group(1),
            "page_name": page_name,
            "revision_number": rev_num,  # None means head (implicit)
            "label": author_label,
            "change_summary": summary,
            "is_new_page": bool(RC_NEW_RE.search(item)),
            "is_minor_edit": bool(RC_MINOR_RE.search(item)),
        })
    return revisions


# --------------------------------------------------------------------- History HTML parse

HIST_TABLE_RE = re.compile(r'<table class="history">(.*?)</table>', re.DOTALL | re.IGNORECASE)
HIST_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
HIST_DATE_RE = re.compile(r'colspan="3"[^>]*>\s*<strong>\s*(\d{4}-\d{2}-\d{2})\s*</strong>', re.IGNORECASE)
HIST_ROW_DATA_RE = re.compile(
    r'(\d{2}:\d{2})\s*UTC.*?Revision\s*(\d+)</a>\s*\.\s*\.\s*\.\s*\.\s*'
    r'<a class="author" href="[^"]*sandbox/([^"]+)"[^>]*>([^<]+)</a>'
    r'(?:<span class="dash">[^<]*</span>\s*<strong>([^<]+)</strong>)?',
    re.DOTALL | re.IGNORECASE,
)


def parse_history(hist_html: str) -> list[dict]:
    """Return every revision listed in the history table, newest FIRST as displayed."""
    tbl_m = HIST_TABLE_RE.search(hist_html)
    if not tbl_m:
        return []
    body = tbl_m.group(1)
    out: list[dict] = []
    current_date: str | None = None
    for row_m in HIST_ROW_RE.finditer(body):
        row = row_m.group(1)
        dm = HIST_DATE_RE.search(row)
        if dm:
            current_date = dm.group(1)
            continue
        # Row data
        rm = HIST_ROW_DATA_RE.search(row)
        if not rm:
            continue
        author_label = html.unescape(rm.group(4)).strip()
        summary = html.unescape(rm.group(5)).strip() if rm.group(5) else None
        out.append({
            "date": current_date,
            "hhmm": rm.group(1),
            "revision_number": int(rm.group(2)),
            "label": author_label,
            "change_summary": summary,
        })
    return out


# --------------------------------------------------------------------- Time helpers

def iso_from_ymd_hhmm_utc(date_str: str | None, hhmm: str | None) -> str | None:
    if not date_str or not hhmm:
        return None
    try:
        y, mo, d = date_str.split("-")
        h, mi = hhmm.split(":")
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}T{int(h):02d}:{int(mi):02d}:00+00:00"
    except Exception:
        return None


# --------------------------------------------------------------------- Content classification

# Very rough AI-activity heuristic. Human-looking early-2020 edits on ludism
# are recipe pages, dice tables, and small talk. AI-activity revisions ~2026
# tend to be URL-heavy (gov PDF links, markdown.new prefixes, similar patterns
# seen on milkwiki/prowiki).
AI_ACTIVITY_URL_MARKERS = [
    "markdown.new",
    "max.gov/portal/document/SF133",
    "piv.max.gov",
    "login.max.gov",
]


def classify_body(body: str | None) -> dict:
    if not body:
        return {"has_url": False, "matches_ai_markers": False, "url_count": 0}
    urls = re.findall(r"https?://[^\s<>]+", body)
    marker_hits = sum(1 for u in urls if any(m in u for m in AI_ACTIVITY_URL_MARKERS))
    return {
        "has_url": bool(urls),
        "matches_ai_markers": marker_hits > 0,
        "url_count": len(urls),
    }


# --------------------------------------------------------------------- Main scrape

def scrape(base: str, name: str, out: Path, days: int, sanity: bool, sleep: float) -> None:
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    print(f"[{name}] RSS days={days} ...", file=sys.stderr)
    rss_url = build_url(base, action="rss", days=str(days), all="1", showedit="0")
    rss_text, _, _ = fetch(rss_url, sleep=sleep)
    rss_items = parse_rss(rss_text)
    print(f"[{name}]   RSS: {len(rss_items)} items", file=sys.stderr)

    print(f"[{name}] RC days={days} all=1 ...", file=sys.stderr)
    rc_url = build_url(base, action="rc", days=str(days), all="1", showedit="0")
    rc_html, _, _ = fetch(rc_url, sleep=sleep)
    rc_rows = parse_rc(rc_html)
    print(f"[{name}]   RC: {len(rc_rows)} revision rows", file=sys.stderr)

    # Distinct page list = union of RSS titles + RC page names.
    pages: list[str] = []
    seen = set()
    for r in rss_items:
        pn = r["page_name"]
        if pn and pn not in seen:
            pages.append(pn)
            seen.add(pn)
    for r in rc_rows:
        pn = r["page_name"]
        if pn and pn not in seen:
            pages.append(pn)
            seen.add(pn)
    print(f"[{name}]   distinct pages: {len(pages)}", file=sys.stderr)

    if sanity:
        pages = pages[:2]
        print(f"[{name}] SANITY: limiting to {len(pages)} pages", file=sys.stderr)

    # Per-page: fetch history, then raw source for every revision.
    per_page_history: dict[str, list[dict]] = {}
    per_page_body: dict[tuple[str, int], str] = {}  # (page_name, rev_number) -> raw source
    per_page_body_status: dict[tuple[str, int], int] = {}
    per_page_head_rev: dict[str, int] = {}

    for pn in pages:
        print(f"[{name}] history {pn} ...", file=sys.stderr)
        hist_url = build_url(base, action="history", id=pn)
        try:
            hist_html, _, _ = fetch(hist_url, sleep=sleep)
        except Exception as e:
            print(f"[{name}]   history fetch failed: {e}", file=sys.stderr)
            per_page_history[pn] = []
            continue
        hist = parse_history(hist_html)
        per_page_history[pn] = hist
        if not hist:
            print(f"[{name}]   no history rows parsed", file=sys.stderr)
            continue
        head_rev = max(h["revision_number"] for h in hist)
        per_page_head_rev[pn] = head_rev
        for h in hist:
            rn = h["revision_number"]
            if rn == head_rev:
                raw_url = build_url(base, action="browse", id=pn, raw="1")
            else:
                raw_url = build_url(base, action="browse", id=pn, revision=str(rn), raw="1")
            try:
                body, _, status = fetch(raw_url, sleep=sleep)
                per_page_body[(pn, rn)] = body
                per_page_body_status[(pn, rn)] = status
            except Exception as e:
                print(f"[{name}]   rev {rn} fetch failed: {e}", file=sys.stderr)
                per_page_body[(pn, rn)] = ""
                per_page_body_status[(pn, rn)] = 0

    if sanity:
        print("\n=== SANITY SUMMARY ===")
        print(f"  base: {base}")
        print(f"  rss items: {len(rss_items)}")
        print(f"  rc rows: {len(rc_rows)}")
        print(f"  pages sampled: {len(pages)}")
        for pn in pages:
            hist = per_page_history.get(pn, [])
            print(f"  {pn}: {len(hist)} revisions in history")
            for h in hist[:3]:
                key = (pn, h["revision_number"])
                body = per_page_body.get(key, "")
                print(f"    rev {h['revision_number']:>3} {h['date']} {h['hhmm']} label={h['label']!r} sum={h['change_summary']!r} body={len(body)}B")
        return

    # ---- Emit output ----
    out.mkdir(parents=True, exist_ok=True)
    build_output(
        name=name, out=out, base=base, days=days, started=started,
        rss_items=rss_items, rc_rows=rc_rows,
        per_page_history=per_page_history,
        per_page_body=per_page_body,
        per_page_body_status=per_page_body_status,
        per_page_head_rev=per_page_head_rev,
        pages=pages,
    )


# --------------------------------------------------------------------- Output

def build_output(*, name: str, out: Path, base: str, days: int, started: str,
                 rss_items: list[dict], rc_rows: list[dict],
                 per_page_history: dict[str, list[dict]],
                 per_page_body: dict[tuple[str, int], str],
                 per_page_body_status: dict[tuple[str, int], int],
                 per_page_head_rev: dict[str, int],
                 pages: list[str]) -> None:
    # Build revisions: every row from history, oldest first per page.
    revisions_out: list[dict] = []
    events_out: list[dict] = []
    pages_out: list[dict] = []
    labels_group: dict[str, list[dict]] = defaultdict(list)

    for pn in pages:
        hist = per_page_history.get(pn, [])
        if not hist:
            continue
        # Sort ascending by revision number.
        hist_sorted = sorted(hist, key=lambda h: h["revision_number"])
        head_rev = per_page_head_rev.get(pn, hist_sorted[-1]["revision_number"])
        # First and last write ISO strings.
        first_time = iso_from_ymd_hhmm_utc(hist_sorted[0]["date"], hist_sorted[0]["hhmm"])
        last_time = iso_from_ymd_hhmm_utc(hist_sorted[-1]["date"], hist_sorted[-1]["hhmm"])

        page_labels: list[str] = []
        page_seq = 0
        for h in hist_sorted:
            page_seq += 1
            rn = h["revision_number"]
            body = per_page_body.get((pn, rn))
            body_available = bool(body)
            body_bytes_val = body.encode("utf-8") if body else None
            body_sha = hashlib.sha256(body_bytes_val).hexdigest() if body_bytes_val else None
            time_iso = iso_from_ymd_hhmm_utc(h["date"], h["hhmm"])
            rev_id = f"{name}~{pn}@{page_seq}"
            page_id = f"{name}/{pn}"
            page_key = f"{name}~{pn}"
            label = h["label"]
            if label not in page_labels:
                page_labels.append(label)
            labels_group[label].append({"page_name": pn, "time_iso": time_iso, "revision_number": rn})
            revisions_out.append({
                "rev_id": rev_id,
                "page_id": page_id,
                "page_key": page_key,
                "wiki": name,
                "name": pn,
                "seq": page_seq,
                "rcs_rev": None,
                "rcs_path": None,
                "body": body,
                "body_len": len(body) if body is not None else None,
                "body_sha256": body_sha,
                "lines": (body.count("\n") + 1) if body else None,
                "diff_base": None,
                "diff_base_reason": None,
                "hunks": None,
                "label": label,
                "ip16": None,
                "time": time_iso,
                "time_grade": "history_wall_utc",
                "winning_clock": "history_utc_wall",
                "uncertainty_seconds": 60,
                "request_time": None,
                "success_time": None,
                "recent_changes_time": time_iso,
                "write_date": None,
                "archived_at": started,
                "request_action": None,
                "change_summary": h["change_summary"],
                "related_event_id": None,
                "relation_type": None,
                "round_id": None,
                "body_encoding": "raw_wiki_source_utf8" if body_available else None,
                "wiki_revision_number": rn,
                "is_new_page": (rn == 1),
                "is_minor_edit": False,
                "body_availability": "full_source" if body_available else "metadata_only",
            })
            events_out.append({
                "event_id": f"save:{rev_id}",
                "event_type": "save",
                "time": time_iso,
                "time_grade": "history_wall_utc",
                "wiki": name,
                "revision_ref": rev_id,
            })

        head_body = per_page_body.get((pn, head_rev)) or ""
        cls = classify_body(head_body)
        pages_out.append({
            "page_id": f"{name}/{pn}",
            "page_key": f"{name}~{pn}",
            "wiki": name,
            "name": pn,
            "bucket": pn[:1].upper(),
            "page_family": "off_store_unclassified",
            "page_family_cohort": None,
            "page_family_confidence": None,
            "page_family_method": None,
            "page_family_source": "none",
            "n_revs": len(hist_sorted),
            "n_revs_before": None,
            "first_write": first_time,
            "last_write": last_time,
            "body_bytes": len(head_body.encode("utf-8")),
            "deleted_live": False,
            "live_body_variant": "raw_wiki_source",
            "head_differs_from_live": False,
            "n_deletions": 0,
            "n_recreations": 0,
            "labels": page_labels,
            "n_labels": len(page_labels),
            "n_ips": None,
            "n_ip16": None,
            "wiki_head_revision_number": head_rev,
            "head_body_has_url": cls["has_url"],
            "head_body_url_count": cls["url_count"],
            "head_body_matches_ai_markers": cls["matches_ai_markers"],
        })

    # Sort revisions chronologically overall (stable per page too since we appended in order).
    revisions_out.sort(key=lambda r: (r.get("time") or "", r["page_id"], r["seq"]))
    events_out.sort(key=lambda e: (e.get("time") or "", e["revision_ref"]))

    # Labels
    labels_out = []
    for label in sorted(labels_group):
        rows = labels_group[label]
        rows_sorted = sorted(rows, key=lambda r: r.get("time_iso") or "")
        pages_for_label = sorted({f"{name}/{r['page_name']}" for r in rows_sorted})
        labels_out.append({
            "label": label,
            "stored_revisions": len(rows_sorted),
            "first_write": rows_sorted[0].get("time_iso") if rows_sorted else None,
            "last_write": rows_sorted[-1].get("time_iso") if rows_sorted else None,
            "stored_revision_ips": None,
            "stored_revision_ip16": None,
            "pages": pages_for_label,
            "stored_revision_pages": len(pages_for_label),
            "wikis": [name],
            "is_human_handle": None,
            "save_requests": None,
            "save_request_ips": None,
            "save_request_ip16": None,
            "save_request_pages": None,
            "save_request_source": None,
        })

    # Write files
    def dump(path: Path, rows: Iterable[dict]) -> None:
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
            "base_url": base,
            "engine": "OddMuse",
            "scraper": "scrape/ludism.py",
        },
        "cut": {
            "kind": "recent_changes_window_plus_full_history_of_visible_pages",
            "days": days,
            "endpoint_rc": build_url(base, action="rc", days=str(days), all="1", showedit="0"),
            "endpoint_rss": build_url(base, action="rss", days=str(days), all="1", showedit="0"),
        },
        "wiki_tz_offset": "+00:00",
        "counts": {
            "revisions": {"value": len(revisions_out)},
            "pages": {"value": len(pages_out)},
            "labels": {"value": len(labels_out)},
            "events": {"value": len(events_out)},
        },
        "per_wiki": {
            name: {
                "revisions": {"value": len(revisions_out)},
                "pages": {"value": len(pages_out)},
                "body_bytes": {"value": sum(p["body_bytes"] for p in pages_out)},
            }
        },
        "limitations": [
            "Only pages that appear in the last {} days of RecentChanges are enumerated. "
            "OddMuse has no cheap way to list all pages ever; ?action=index is available "
            "in some configs but not probed here.".format(days),
            "For pages in the enumeration set, the full history table is fetched and every "
            "listed revision is downloaded as raw wiki source. Body coverage is expected to "
            "be 100% for those pages.",
            "Time precision: history HH:MM UTC only. uncertainty_seconds=60.",
            "No IPs exposed (ip16=null everywhere). The wiki UI only shows the author label.",
            "No diff hunks captured. Full body per revision makes diffs derivable offline.",
        ],
        "endpoints_probed": {
            "recent_changes_html": build_url(base, action="rc", days=str(days), all="1", showedit="0"),
            "recent_changes_rss": build_url(base, action="rss", days=str(days), all="1", showedit="0"),
            "history": build_url(base, action="history", id="<page>"),
            "raw_source_head": build_url(base, action="browse", id="<page>", raw="1"),
            "raw_source_rev": build_url(base, action="browse", id="<page>", revision="<N>", raw="1"),
        },
    }
    with (out / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # SHA256SUMS
    with (out / "SHA256SUMS").open("w", encoding="utf-8") as f:
        for fname in sorted(["pages.jsonl", "revisions.jsonl", "events.jsonl", "labels.jsonl", "manifest.json"]):
            data = (out / fname).read_bytes()
            f.write(f"{hashlib.sha256(data).hexdigest()}  {fname}\n")

    print(f"[{name}] wrote {out}/", file=sys.stderr)
    for fname in ["pages.jsonl", "revisions.jsonl", "events.jsonl", "labels.jsonl", "manifest.json", "SHA256SUMS"]:
        size = (out / fname).stat().st_size
        print(f"  {fname:20s} {size:>8d} bytes", file=sys.stderr)


# --------------------------------------------------------------------- CLI

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default=DEFAULT_BASE)
    p.add_argument("--name", default=DEFAULT_NAME)
    p.add_argument("--out", type=Path, help="Output directory (default agent-logs/<name>/)")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--sanity", action="store_true")
    p.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)
    args = p.parse_args()

    out = args.out or Path("agent-logs") / args.name
    scrape(args.base, args.name, out, args.days, args.sanity, args.sleep)


if __name__ == "__main__":
    main()
