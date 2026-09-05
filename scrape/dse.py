#!/usr/bin/env python3
"""Scrape the wikiservice.at/dse ProWiki (STANDARD skin) into agent-logs/<name>/.

Fork of scrape/wikiservice_scrape.py adapted for the DseWiki HTML shell, which
differs from the user/<slug>/ wikis:

  * The STANDARD skin has no `<td class="content">` wrapper. The RC list sits
    directly in `<body>` between two `<hr>` bars.
  * Date headers use German long form: "4. September 2026".
  * Diff markers are German: Hinzugefügt / Gelöscht / Verändert.
  * Deletion is recorded as a revision whose change_summary is "Seite gelöscht.",
    made by the admin (MarkusLude). Fetching the deleted page returns a stub
    body ("created" / "Beschreibe hier die neue Seite.").

Same public-scrape limits as its parent: no raw wiki source, no full history,
no IPs, only head bodies.

For dse specifically the corpus is ~22,445 revisions across ~3,900 pages, and
per-page body/diff fetches at --sleep 3 would take multiple hours. Use
--body-strategy=metadata_only (default) to skip per-page fetches, or
--body-strategy=head_pages_bounded --body-limit=N to fetch bodies for the N
most-recently-edited pages, or --body-strategy=all to fetch everything.

Usage:
    dse.py --base BASE --name NAME --out OUTDIR [--days N] [--sanity]
           [--body-strategy metadata_only|head_pages_bounded|all]
           [--body-limit N]
"""
from __future__ import annotations

import argparse
import datetime as dt
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
DEFAULT_DAYS = 500  # dse activity spans ~2 months but we want the fullest picture
DEFAULT_SLEEP = 3.0  # concurrent agents on the same shared host; be polite

# --------------------------------------------------------------------- HTTP

def fetch(url: str, *, sleep: float = DEFAULT_SLEEP) -> tuple[str, str]:
    """Return (text, content_type). Decodes iso-8859-1 (ProWiki default)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    time.sleep(sleep)
    for enc in ("iso-8859-1", "utf-8"):
        try:
            return raw.decode(enc), ctype
        except UnicodeDecodeError:
            continue
    return raw.decode("iso-8859-1", errors="replace"), ctype


# --------------------------------------------------------------------- HTML utils

# STANDARD-skin content region: between the first `<hr>` in <body> (after the
# top nav row) and the closing `<hr>` before the bottom nav row.
CONTENT_HR_SPLIT_RE = re.compile(r"<hr>", re.IGNORECASE)
BODY_OPEN_RE = re.compile(r"<body[^>]*>", re.IGNORECASE)
TITLE_SPAN_RE = re.compile(
    r'<span class="title">.*?</span>', re.DOTALL | re.IGNORECASE
)
HTML_TAG_RE = re.compile(r"<[^>]+>")
ANCHOR_TEXT_RE = re.compile(r"<a\b[^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
P_RE = re.compile(r"<p\s*/?>|</p>", re.IGNORECASE)
MULTIBLANK_RE = re.compile(r"\n{3,}")


def extract_content_html(page_html: str) -> str:
    """Content is between the first `<hr>` and the last `<hr>` inside `<body>`.

    On the STANDARD skin the page consists of:
        <body>
            <table>...top strip...</table>
            <font>...title...</font>
            <nav>...top nav bar...</nav><br />

            <hr>
            ...content...
            <hr>
            <nav>...bottom nav bar...</nav>
            <form>...search...</form>
        </body>

    The first `<hr>` marks content start; the last (before nav footer) marks
    end.
    """
    body_m = BODY_OPEN_RE.search(page_html)
    body_start = body_m.end() if body_m else 0
    body = page_html[body_start:]
    hrs = list(CONTENT_HR_SPLIT_RE.finditer(body))
    if len(hrs) < 2:
        return ""
    start = hrs[0].end()
    end = hrs[-1].start()
    inner = body[start:end]
    inner = TITLE_SPAN_RE.sub("", inner)
    inner = re.sub(r"<b>\s*</b>", "", inner)
    return inner


def strip_content_to_text(inner_html: str) -> str:
    """Turn the content HTML into a lossy plain-text approximation."""
    inner_html = ANCHOR_TEXT_RE.sub(lambda m: m.group(1), inner_html)
    inner_html = BR_RE.sub("\n", inner_html)
    inner_html = P_RE.sub("\n", inner_html)
    inner_html = HTML_TAG_RE.sub("", inner_html)
    text = html.unescape(inner_html)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = MULTIBLANK_RE.sub("\n\n", text).strip()
    return text


# Stubs that indicate a page whose body is unavailable to us.
# "created" = admin-deleted, "Beschreibe hier die neue Seite." = never existed.
DELETED_STUB_RE = re.compile(r"^\s*created\s*$", re.IGNORECASE)
NEVER_EXISTED_RE = re.compile(r"^\s*Beschreibe hier die neue Seite\.?\s*$", re.IGNORECASE)


def classify_body(text: str) -> str:
    """Return one of head_only | deleted_or_404 based on the extracted body text."""
    if not text:
        return "deleted_or_404"
    if DELETED_STUB_RE.match(text):
        return "deleted_or_404"
    if NEVER_EXISTED_RE.match(text):
        return "deleted_or_404"
    return "head_only"


# --------------------------------------------------------------------- RecentChanges

# German date header: <p><strong>4. September 2026</strong></p>
RC_DATE_RE = re.compile(
    r"<p>\s*<strong>\s*(\d{1,2}\.\s+[A-Za-zäöüÄÖÜß]+\s+\d{4})\s*</strong>\s*</p>",
    re.IGNORECASE,
)
RC_ITEM_RE = re.compile(r"<li>(.*?)</li>", re.DOTALL | re.IGNORECASE)
# Page anchor: `<a href='wiki.cgi?PageName' class='body'>Display Name</a>`. Page
# names may contain slashes (ForumSeite/Context) and dots.
RC_PAGE_RE = re.compile(
    r"<a\s+href='wiki\.cgi\?([A-Za-z0-9_][A-Za-z0-9_./-]*)'[^>]*class='body'[^>]*>([^<]+)</a>",
    re.IGNORECASE,
)
# HH:MM with 1- or 2-digit hour. The RC display uses e.g. `9:58` not `09:58`.
RC_TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")
# NEW / Minor markers do not appear on dse but keep them for parity.
RC_NEW_RE = re.compile(r"<strong>NEW</strong>", re.IGNORECASE)
RC_SUMMARY_RE = re.compile(r"<strong>\[([^\]]*)\]</strong>", re.IGNORECASE)
RC_MINOR_RE = re.compile(r"<em>Minor edit</em>", re.IGNORECASE)


def parse_rc(html_text: str) -> list[dict]:
    content = extract_content_html(html_text)
    revisions: list[dict] = []
    current_date: str | None = None
    pos = 0
    while pos < len(content):
        m_date = RC_DATE_RE.search(content, pos)
        m_item = RC_ITEM_RE.search(content, pos)
        if m_item is None:
            break
        if m_date is not None and m_date.start() < m_item.start():
            current_date = m_date.group(1)
            pos = m_date.end()
            continue
        item = m_item.group(1)
        pos = m_item.end()
        anchors = list(RC_PAGE_RE.finditer(item))
        body_anchors = [a for a in anchors if "class='body'" in item[a.start():a.end()]]
        if len(body_anchors) < 2:
            continue
        page_anchor = body_anchors[0]
        label_anchor = body_anchors[-1]
        page_name = page_anchor.group(1)
        label = label_anchor.group(1)
        m_time = RC_TIME_RE.search(item)
        hhmm = m_time.group(1) if m_time else None
        # Normalise to zero-padded HH:MM to match RSS's HH:MM.
        if hhmm and len(hhmm.split(":")[0]) == 1:
            hhmm = "0" + hhmm
        m_sum = RC_SUMMARY_RE.search(item)
        summary = html.unescape(m_sum.group(1)) if m_sum else None
        is_new = bool(RC_NEW_RE.search(item))
        is_minor = bool(RC_MINOR_RE.search(item))
        revisions.append({
            "date": current_date,
            "hhmm": hhmm,
            "page_name": urllib.parse.unquote(page_name),
            "label": urllib.parse.unquote(label),
            "change_summary": summary,
            "is_new_page": is_new,
            "is_minor_edit": is_minor,
        })
    return revisions


# --------------------------------------------------------------------- RSS parse

RSS_ITEM_RE = re.compile(r"<item\b[^>]*>(.*?)</item>", re.DOTALL | re.IGNORECASE)
RSS_TAG_RE = re.compile(r"<([a-z0-9:]+)>([^<]*)</\1>", re.IGNORECASE)
RSS_ABOUT_RE = re.compile(r'rdf:about="([^"]+)"', re.IGNORECASE)


def parse_rss(rss_text: str) -> list[dict]:
    out = []
    for m in RSS_ITEM_RE.finditer(rss_text):
        item = m.group(1)
        tags: dict[str, str] = {}
        for t in RSS_TAG_RE.finditer(item):
            tags[t.group(1).lower()] = html.unescape(t.group(2))
        about_m = RSS_ABOUT_RE.search(m.group(0)[:400])
        about = html.unescape(about_m.group(1)) if about_m else ""
        q = urllib.parse.urlparse(about).query
        params = urllib.parse.parse_qs(q)
        revision = params.get("revision", [None])[0]
        page_id = params.get("id", [None])[0]
        out.append({
            "page_name": page_id,
            "title": tags.get("title"),
            "date_iso": tags.get("dc:date"),
            "creator": tags.get("dc:creator"),
            "description": tags.get("description"),
            "revision": int(revision) if revision else None,
            "status": tags.get("wiki:status"),
            "importance": tags.get("wiki:importance"),
        })
    return out


# --------------------------------------------------------------------- Diff parse

# German diff markers: Hinzugefügt / Gelöscht / Verändert (case-insensitive).
DIFF_MARKER_RE = re.compile(
    r"<strong>(Added|Deleted|Changed|Hinzugefügt|Gelöscht|Verändert):\s*([^<]+?)\s*</strong>",
    re.IGNORECASE,
)
DIFF_YELLOW_RE = re.compile(
    r"<table[^>]*bgcolor=#ffffaf[^>]*><tr><td>(.*?)</td></tr></table>",
    re.DOTALL | re.IGNORECASE,
)
DIFF_GREEN_RE = re.compile(
    r"<table[^>]*bgcolor=#cfffcf[^>]*><tr><td>(.*?)</td></tr></table>",
    re.DOTALL | re.IGNORECASE,
)

DIFF_OP_MAP = {
    "added": "added",
    "deleted": "deleted",
    "changed": "changed",
    "hinzugefügt": "added",
    "gelöscht": "deleted",
    "verändert": "changed",
}


def parse_diff(diff_html: str) -> dict:
    inner = extract_content_html(diff_html)
    markers = list(DIFF_MARKER_RE.finditer(inner))
    if not markers:
        # STANDARD-skin diff pages have no "no other diffs" text observed; use
        # the marker absence as the signal.
        no_prev = "Veränderung" not in inner and "Difference" not in inner
        return {"hunks": [], "no_previous_revision": no_prev}
    hunks = []
    for i, m in enumerate(markers):
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(inner)
        slice_html = inner[start:end]
        y = DIFF_YELLOW_RE.search(slice_html)
        g = DIFF_GREEN_RE.search(slice_html)
        op_raw = m.group(1).lower()
        hunks.append({
            "op": DIFF_OP_MAP.get(op_raw, op_raw),
            "span": m.group(2).strip(),
            "removed_text": strip_content_to_text(y.group(1)) if y else "",
            "added_text": strip_content_to_text(g.group(1)) if g else "",
        })
    return {"hunks": hunks, "no_previous_revision": False}


# --------------------------------------------------------------------- Time

# German month names (as used in DseWiki RC date headers).
MONTHS_DE = {
    "Januar": 1, "Februar": 2, "März": 3, "April": 4,
    "Mai": 5, "Juni": 6, "Juli": 7, "August": 8,
    "September": 9, "Oktober": 10, "November": 11, "Dezember": 12,
}
# Also accept English month names, just in case ProWiki flips language.
MONTHS_EN = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}


RSS_TZ_RE = re.compile(r"([+-]\d{2}:\d{2}|Z)$")


def derive_wiki_tz(rss_items: list[dict]) -> str | None:
    for r in rss_items:
        d = r.get("date_iso") or ""
        m = RSS_TZ_RE.search(d)
        if m:
            return "+00:00" if m.group(1) == "Z" else m.group(1)
    return None


DE_DATE_RE = re.compile(r"^(\d{1,2})\.\s+([A-Za-zäöüÄÖÜß]+)\s+(\d{4})$")


def rc_datetime(date_str: str | None, hhmm: str | None, tz_offset: str | None) -> str | None:
    """Reconstruct ISO time from `DD. Month YYYY` + `HH:MM`. Falls back to English
    month names if the wiki is ever set to English."""
    if not date_str or not hhmm:
        return None
    m = DE_DATE_RE.match(date_str)
    if not m:
        return None
    day = int(m.group(1))
    month_name = m.group(2)
    year = int(m.group(3))
    month = MONTHS_DE.get(month_name) or MONTHS_EN.get(month_name)
    if not month:
        return None
    h, mm = hhmm.split(":")
    suffix = tz_offset if tz_offset else ""
    return f"{year:04d}-{month:02d}-{day:02d}T{int(h):02d}:{int(mm):02d}:00{suffix}"


# --------------------------------------------------------------------- URL helpers

def build_url(base: str, **params) -> str:
    q = urllib.parse.urlencode(params, safe="")
    return f"{base}?{q}"


def base_root(base: str) -> str:
    return base.rsplit("/", 1)[0] if base.endswith(".cgi") else base


# --------------------------------------------------------------------- Merge RC + RSS

RSS_ISO_HHMM_RE = re.compile(r"T(\d{2}:\d{2})")


def _rss_hhmm(date_iso: str | None) -> str | None:
    if not date_iso:
        return None
    m = RSS_ISO_HHMM_RE.search(date_iso)
    return m.group(1) if m else None


def merge_rc_rss(rc: list[dict], rss: list[dict], tz_offset: str | None = None) -> list[dict]:
    rss_by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rss:
        key = (r.get("page_name") or "", _rss_hhmm(r.get("date_iso")) or "")
        if key[0] and key[1]:
            rss_by_key[key].append(r)

    merged = []
    for entry in rc:
        pn = entry["page_name"]
        hhmm = entry.get("hhmm") or ""
        candidates = rss_by_key.get((pn, hhmm)) or []
        rss_match = candidates.pop(0) if candidates else None
        entry["rss"] = rss_match
        if rss_match and rss_match.get("date_iso"):
            entry["time_iso"] = rss_match["date_iso"]
            entry["time_source"] = "rss"
        else:
            entry["time_iso"] = rc_datetime(entry.get("date"), entry.get("hhmm"), tz_offset)
            entry["time_source"] = "rc_wall" if tz_offset else "rc_wall_naive"
        entry["revision_number"] = rss_match["revision"] if rss_match else None
        merged.append(entry)
    return merged


# --------------------------------------------------------------------- Body strategies

BODY_STRATEGY_METADATA_ONLY = "metadata_only"
BODY_STRATEGY_HEAD_PAGES_BOUNDED = "head_pages_bounded"
BODY_STRATEGY_ALL = "all"


def select_body_pages(page_names: list[str], strategy: str, limit: int) -> list[str]:
    """`page_names` is ordered newest-first (from RC). Pick which pages to
    body-fetch based on the strategy."""
    if strategy == BODY_STRATEGY_METADATA_ONLY:
        return []
    if strategy == BODY_STRATEGY_HEAD_PAGES_BOUNDED:
        return page_names[:limit]
    if strategy == BODY_STRATEGY_ALL:
        return list(page_names)
    raise ValueError(f"unknown body strategy: {strategy!r}")


# --------------------------------------------------------------------- Main scrape

def scrape(base: str, name: str, out: Path, days: int, sanity: bool,
           sleep: float, body_strategy: str, body_limit: int) -> None:
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    print(f"[{name}] fetching RC (days={days},all=1) ...", file=sys.stderr)
    rc_url = build_url(base, action="browse", id="RecentChanges", days=str(days), all="1")
    rc_html, _ = fetch(rc_url, sleep=sleep)
    revs = parse_rc(rc_html)
    print(f"[{name}]   RC parsed: {len(revs)} revision rows", file=sys.stderr)

    print(f"[{name}] fetching RSS (days={days}) ...", file=sys.stderr)
    rss_url = build_url(base, action="browse", id="RecentChangesRss", days=str(days))
    try:
        rss_text, _ = fetch(rss_url, sleep=sleep)
        rss_items = parse_rss(rss_text)
    except Exception as e:
        print(f"[{name}]   RSS fetch failed: {e}", file=sys.stderr)
        rss_items = []
    print(f"[{name}]   RSS parsed: {len(rss_items)} items", file=sys.stderr)

    wiki_tz = derive_wiki_tz(rss_items)
    print(f"[{name}]   wiki TZ offset: {wiki_tz or 'unknown'}", file=sys.stderr)

    merged = merge_rc_rss(revs, rss_items, wiki_tz)

    page_names: list[str] = []
    seen = set()
    for r in merged:
        if r["page_name"] not in seen:
            page_names.append(r["page_name"])
            seen.add(r["page_name"])
    print(f"[{name}]   {len(page_names)} unique pages", file=sys.stderr)

    body_targets = select_body_pages(page_names, body_strategy, body_limit)
    print(
        f"[{name}] body strategy: {body_strategy} "
        f"(fetching bodies for {len(body_targets)} of {len(page_names)} pages)",
        file=sys.stderr,
    )

    if sanity:
        # In sanity mode, always fetch at most 2 bodies regardless of strategy.
        body_targets = page_names[:2]
        print(f"[{name}] SANITY: limiting body fetches to {len(body_targets)} pages",
              file=sys.stderr)

    page_bodies: dict[str, str] = {}
    page_body_availability: dict[str, str] = {}
    page_diffs: dict[str, dict] = {}
    for i, pn in enumerate(body_targets):
        if i % 50 == 0 and i > 0:
            print(f"[{name}]   ...body/diff progress {i}/{len(body_targets)}",
                  file=sys.stderr)
        try:
            body_html, _ = fetch(build_url(base, action="browse", id=pn), sleep=sleep)
            text = strip_content_to_text(extract_content_html(body_html))
            avail = classify_body(text)
            page_bodies[pn] = text if avail == "head_only" else ""
            page_body_availability[pn] = avail
        except Exception as e:
            print(f"[{name}]   page {pn}: body fetch failed: {e}", file=sys.stderr)
            page_bodies[pn] = ""
            page_body_availability[pn] = "fetch_error"
        try:
            diff_html, _ = fetch(build_url(base, action="browse", diff="4", id=pn), sleep=sleep)
            page_diffs[pn] = parse_diff(diff_html)
        except Exception as e:
            print(f"[{name}]   page {pn}: diff fetch failed: {e}", file=sys.stderr)
            page_diffs[pn] = {"hunks": [], "no_previous_revision": None}

    if sanity:
        print("\n=== SANITY SUMMARY ===")
        print(f"  base: {base}")
        print(f"  days window: {days}")
        print(f"  wiki tz offset: {wiki_tz or 'unknown'}")
        print(f"  rc rows: {len(revs)}  rss items: {len(rss_items)}  unique pages: {len(seen)}")
        for r in merged[:5]:
            print(f"  rev: {r['page_name']}  time={r.get('time_iso')} label={r['label']} "
                  f"summary={r.get('change_summary')!r} rev#={r.get('revision_number')}")
        for pn, body in list(page_bodies.items())[:2]:
            avail = page_body_availability.get(pn)
            print(f"\n--- {pn} head body ({len(body)} bytes, availability={avail}) ---")
            print(body[:400])
        return

    out.mkdir(parents=True, exist_ok=True)
    build_output(
        name=name, out=out, base=base, days=days, started=started,
        merged=merged, page_names=page_names, body_targets=set(body_targets),
        body_strategy=body_strategy, body_limit=body_limit,
        page_bodies=page_bodies, page_diffs=page_diffs,
        page_body_availability=page_body_availability,
        rc_html=rc_html, rss_items=rss_items, wiki_tz=wiki_tz,
    )


def _not_fetched_availability(body_strategy: str) -> str:
    if body_strategy == BODY_STRATEGY_METADATA_ONLY:
        return "not_fetched_size_budget"
    if body_strategy == BODY_STRATEGY_HEAD_PAGES_BOUNDED:
        return "not_fetched_size_budget"
    return "metadata_only"


def build_output(*, name: str, out: Path, base: str, days: int, started: str,
                 merged: list[dict], page_names: list[str], body_targets: set[str],
                 body_strategy: str, body_limit: int,
                 page_bodies: dict[str, str], page_diffs: dict[str, dict],
                 page_body_availability: dict[str, str],
                 rc_html: str, rss_items: list[dict], wiki_tz: str | None) -> None:
    def sortable_time(r):
        return r.get("time_iso") or ""
    merged_sorted = sorted(merged, key=sortable_time)

    seq_by_page: Counter[str] = Counter()
    revisions_out = []
    events_out = []
    # Pre-compute the head (last chronological) row per page.
    head_row_by_page: dict[str, dict] = {}
    for r in merged_sorted:
        head_row_by_page[r["page_name"]] = r

    for r in merged_sorted:
        pn = r["page_name"]
        seq_by_page[pn] += 1
        seq = seq_by_page[pn]
        is_head = (r is head_row_by_page[pn])
        is_body_target = pn in body_targets

        if is_head and is_body_target:
            body = page_bodies.get(pn) or None
            avail = page_body_availability.get(pn, "fetch_error")
            diff = page_diffs.get(pn)
        elif is_head:
            body = None
            avail = _not_fetched_availability(body_strategy)
            diff = None
        else:
            body = None
            avail = "metadata_only"
            diff = None

        body_bytes = body.encode("utf-8") if body else None
        body_sha = hashlib.sha256(body_bytes).hexdigest() if body_bytes else None

        rev_id = f"{name}~{pn}@{seq}"
        page_id = f"{name}/{pn}"
        page_key = f"{name}~{pn}"
        revisions_out.append({
            "rev_id": rev_id,
            "page_id": page_id,
            "page_key": page_key,
            "wiki": name,
            "name": pn,
            "seq": seq,
            "rcs_rev": None,
            "rcs_path": None,
            "body": body,
            "body_len": len(body) if body is not None else None,
            "body_sha256": body_sha,
            "lines": body.count("\n") + 1 if body else None,
            "diff_base": None,
            "diff_base_reason": None,
            "hunks": diff["hunks"] if diff else None,
            "label": r["label"],
            "ip16": None,
            "time": r.get("time_iso"),
            "time_grade": r.get("time_source"),
            "winning_clock": "rss_dc_date" if r.get("time_source") == "rss" else "recent_changes_wall",
            "uncertainty_seconds": 1 if r.get("time_source") == "rss" else 60,
            "request_time": None,
            "success_time": None,
            "recent_changes_time": r.get("time_iso"),
            "write_date": None,
            "archived_at": started,
            "request_action": None,
            "change_summary": r.get("change_summary"),
            "related_event_id": None,
            "relation_type": None,
            "round_id": None,
            "body_encoding": "html_stripped_utf8" if body else None,
            "wiki_revision_number": r.get("revision_number"),
            "is_new_page": r.get("is_new_page"),
            "is_minor_edit": r.get("is_minor_edit"),
            "body_availability": avail,
        })
        events_out.append({
            "event_id": f"save:{rev_id}",
            "event_type": "save",
            "time": r.get("time_iso"),
            "time_grade": r.get("time_source"),
            "wiki": name,
            "revision_ref": rev_id,
        })

    pages_out = []
    for pn in sorted({r["page_name"] for r in merged_sorted}):
        rows_for_page = [r for r in merged_sorted if r["page_name"] == pn]
        head = rows_for_page[-1]
        head_body = page_bodies.get(pn) or ""
        head_avail = page_body_availability.get(pn) if pn in body_targets else _not_fetched_availability(body_strategy)
        deleted_live = head_avail == "deleted_or_404"
        labels_seen = sorted({r["label"] for r in rows_for_page})
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
            "n_revs": len(rows_for_page),
            "n_revs_before": None,
            "first_write": rows_for_page[0].get("time_iso"),
            "last_write": head.get("time_iso"),
            "body_bytes": len(head_body.encode("utf-8")) if head_body else 0,
            "deleted_live": deleted_live,
            "live_body_variant": "html_stripped",
            "head_differs_from_live": False,
            "n_deletions": 0,
            "n_recreations": 0,
            "labels": labels_seen,
            "n_labels": len(labels_seen),
            "n_ips": None,
            "n_ip16": None,
            "wiki_head_revision_number": head.get("revision_number"),
        })

    labels_group: dict[str, list[dict]] = defaultdict(list)
    for r in merged_sorted:
        labels_group[r["label"]].append(r)
    labels_out = []
    for label in sorted(labels_group):
        rows = labels_group[label]
        pages = sorted({f"{name}/{r['page_name']}" for r in rows})
        labels_out.append({
            "label": label,
            "stored_revisions": len(rows),
            "first_write": rows[0].get("time_iso"),
            "last_write": rows[-1].get("time_iso"),
            "stored_revision_ips": None,
            "stored_revision_ip16": None,
            "pages": pages,
            "stored_revision_pages": len(pages),
            "wikis": [name],
            "is_human_handle": None,
            "save_requests": None,
            "save_request_ips": None,
            "save_request_ip16": None,
            "save_request_pages": None,
            "save_request_source": None,
        })

    def dump(path: Path, rows: Iterable[dict]) -> None:
        with path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    dump(out / "pages.jsonl", pages_out)
    dump(out / "revisions.jsonl", revisions_out)
    dump(out / "events.jsonl", events_out)
    dump(out / "labels.jsonl", labels_out)

    # Body-availability breakdown for the manifest.
    availability_counts: Counter[str] = Counter()
    for rev in revisions_out:
        availability_counts[rev["body_availability"]] += 1

    limitations = [
        "Body is HTML-stripped rendered output, not raw wiki source. "
        "Wiki markup (WikiLinks, bold/italic, headings) is largely lost; "
        "raw URLs survive because they appear verbatim in the render.",
        "Bodies are only captured for the HEAD revision of each page, and only "
        "for the subset selected by --body-strategy. Non-head revisions in "
        "this cut have body=null (body_availability='metadata_only'). Head "
        "rows for pages skipped by the body strategy are marked "
        "'not_fetched_size_budget'.",
        "Deleted / never-existed pages return a stub body (\"created\" or "
        "\"Beschreibe hier die neue Seite.\"). We detect these and mark "
        "body_availability='deleted_or_404' so downstream analyses can "
        "distinguish them from real head content.",
        "No IPs are exposed (n_ips/n_ip16/ip16 are all null). The wiki UI only "
        "shows the editor's label (nickname).",
        "Time precision: RSS entries are second-accurate with timezone offset. "
        "RC-only rows are minute-accurate wall time and get "
        "uncertainty_seconds=60. RSS is capped at a small number of most-recent "
        "items, so for a 500-day window nearly all rows fall back to RC-wall "
        "time.",
        "n_revs_before is unknown - RecentChanges window is our only visibility "
        "into revision counts, and older revisions may exist that we can't see.",
    ]
    if body_strategy == BODY_STRATEGY_METADATA_ONLY:
        limitations.append(
            "body_strategy=metadata_only: per-page body/diff fetches were "
            "skipped entirely because the dse corpus has ~22k revisions across "
            "~3.9k pages and full body+diff fetches at --sleep 3 would take "
            "several hours. All head rows are marked "
            "body_availability='not_fetched_size_budget'."
        )
    elif body_strategy == BODY_STRATEGY_HEAD_PAGES_BOUNDED:
        limitations.append(
            f"body_strategy=head_pages_bounded (limit={body_limit}): bodies "
            f"were fetched only for the {body_limit} most-recently-edited "
            "pages, sorted by newest first-seen in the RC listing. Other head "
            "rows are marked body_availability='not_fetched_size_budget'."
        )

    manifest = {
        "generated_at": started,
        "source": {
            "wiki_name": name,
            "base_url": base,
            "engine": "prowiki (usemod-derived, STANDARD skin)",
            "scraper": "scrape/dse.py",
        },
        "cut": {
            "kind": "recent_changes_window",
            "days": days,
            "endpoint": build_url(base, action="browse", id="RecentChanges", days=str(days), all="1"),
        },
        "body_strategy": {
            "kind": body_strategy,
            "limit": body_limit if body_strategy == BODY_STRATEGY_HEAD_PAGES_BOUNDED else None,
            "pages_targeted": len(body_targets),
            "pages_total": len({r["page_name"] for r in merged_sorted}),
        },
        "wiki_tz_offset": wiki_tz,
        "counts": {
            "revisions": {"value": len(revisions_out)},
            "pages": {"value": len(pages_out)},
            "labels": {"value": len(labels_out)},
        },
        "per_wiki": {
            name: {
                "revisions": {"value": len(revisions_out)},
                "pages": {"value": len(pages_out)},
                "body_bytes": {"value": sum(p["body_bytes"] for p in pages_out)},
            }
        },
        "body_availability_breakdown": dict(availability_counts),
        "limitations": limitations,
        "endpoints_probed": {
            "recent_changes_html": build_url(base, action="browse", id="RecentChanges", days=str(days), all="1"),
            "recent_changes_rss": build_url(base, action="browse", id="RecentChangesRss", days=str(days)),
            "history_admin_gated": build_url(base, action="log", id="<page>"),
            "archive_admin_gated": build_url(base, action="archive", id="<page>"),
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
        print(f"  {fname:20s} {size:>10d} bytes", file=sys.stderr)


# --------------------------------------------------------------------- CLI

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", required=True, help="Base URL, e.g. https://www.wikiservice.at/dse/wiki.cgi")
    p.add_argument("--name", required=True, help="Short wiki name, e.g. 'dse'")
    p.add_argument("--out", type=Path, help="Output directory (default: agent-logs/<name>/)")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--sanity", action="store_true", help="Fetch minimum viable subset, print summary, don't write files")
    p.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Seconds between requests")
    p.add_argument(
        "--body-strategy",
        choices=[BODY_STRATEGY_METADATA_ONLY, BODY_STRATEGY_HEAD_PAGES_BOUNDED, BODY_STRATEGY_ALL],
        default=BODY_STRATEGY_METADATA_ONLY,
        help="Which head bodies to fetch",
    )
    p.add_argument("--body-limit", type=int, default=200,
                   help="Cap for head_pages_bounded strategy (default 200)")
    args = p.parse_args()

    out = args.out or Path("agent-logs") / args.name
    scrape(args.base, args.name, out, args.days, args.sanity, args.sleep,
           args.body_strategy, args.body_limit)


if __name__ == "__main__":
    main()
