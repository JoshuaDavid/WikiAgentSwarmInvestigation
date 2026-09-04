#!/usr/bin/env python3
"""Scrape a ProWiki-farm public wiki into agent-logs/<name>/ layout.

The wikis on wikiservice.at (and its ProWiki-engine siblings) do not expose
raw wiki source or full history to unauthenticated users. What we CAN capture:

  * RecentChanges with `days=N&all=1` - one row per revision within the window
    (page, timestamp, editor label, edit-summary bracketed text).
  * RSS feed for the same window - precise ISO timestamps + per-page revision
    numbers.
  * Current rendered body of every page seen (HTML-stripped).
  * The head-to-previous diff for every page (hunks; also lets us reconstruct
    a lossy version of the previous body).

What we CANNOT capture (admin-only): raw wiki source, revision bodies older
than N-1, action=log / action=archive, IPs, request-level metadata.

Output layout mirrors agent-logs/prowiki as far as this input allows. Fields
that don't exist for the public-scrape are `null`; a `manifest.limitations`
list records what's missing so downstream analyses don't silently assume it.

Usage:
    scrape.py --base BASE --name NAME --out OUTDIR [--days N] [--sanity]

  --sanity  fetch RC + RSS only, plus at most two pages worth of body/diff,
            print a summary to stdout, do not write output files. Cheap smoke
            test before pointing the script at all 50 sibling wikis.
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
DEFAULT_DAYS = 120
DEFAULT_SLEEP = 1.0  # be polite; wikiservice.at is a small shared host

# --------------------------------------------------------------------- HTTP

def fetch(url: str, *, sleep: float = DEFAULT_SLEEP) -> tuple[str, str]:
    """Return (text, content_type). Decodes iso-8859-1 (ProWiki default) then falls back."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    time.sleep(sleep)
    # ProWiki serves iso-8859-1; RSS is also iso-8859-1. Try that first.
    for enc in ("iso-8859-1", "utf-8"):
        try:
            return raw.decode(enc), ctype
        except UnicodeDecodeError:
            continue
    return raw.decode("iso-8859-1", errors="replace"), ctype


# --------------------------------------------------------------------- HTML utils

# The content <td> contains a nested table structure in diff mode, so a
# non-greedy `.*?</td>` cuts off inside the first inner </td>. Instead we
# anchor on the opening td and stop at the next outer-shell row (navbar).
CONTENT_START_RE = re.compile(
    r'<td[^>]*class="content"[^>]*>', re.IGNORECASE
)
CONTENT_END_RE = re.compile(
    r"<tr>\s*<td[^>]*class=\"navbar\"", re.IGNORECASE
)
TITLE_SPAN_RE = re.compile(
    r'<span class="title">.*?</span>', re.DOTALL | re.IGNORECASE
)
HTML_TAG_RE = re.compile(r"<[^>]+>")
ANCHOR_TEXT_RE = re.compile(r"<a\b[^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
P_RE = re.compile(r"<p\s*/?>|</p>", re.IGNORECASE)
MULTIBLANK_RE = re.compile(r"\n{3,}")


def extract_content_html(page_html: str) -> str:
    m = CONTENT_START_RE.search(page_html)
    if not m:
        return ""
    after = page_html[m.end():]
    end = CONTENT_END_RE.search(after)
    inner = after[:end.start()] if end else after
    inner = TITLE_SPAN_RE.sub("", inner)
    inner = re.sub(r"<b>\s*</b>", "", inner)
    return inner


def strip_content_to_text(inner_html: str) -> str:
    """Turn the content HTML into a lossy plain-text approximation of wiki source."""
    # Anchors: keep visible text (which for URL-only pages equals the raw URL).
    inner_html = ANCHOR_TEXT_RE.sub(lambda m: m.group(1), inner_html)
    inner_html = BR_RE.sub("\n", inner_html)
    inner_html = P_RE.sub("\n", inner_html)
    inner_html = HTML_TAG_RE.sub("", inner_html)
    text = html.unescape(inner_html)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = MULTIBLANK_RE.sub("\n\n", text).strip()
    return text


# --------------------------------------------------------------------- RecentChanges

# One RC list item looks like:
#   <li><a href='wiki.cgi?action=browse&amp;diff=4&amp;id=SandBox' ...>(diff)</a>
#       <a href='wiki.cgi?SandBox' class='body'>SandBox</a> 14:34
#       <strong>[edit summary]</strong> . . . . .
#       <a href='wiki.cgi?ResearchTester' class='body'>ResearchTester</a></li>
# On days without edits there's no <ul>. Dates are `<p><strong>Month D, YYYY</strong></p>`.

RC_DATE_RE = re.compile(
    r"<p>\s*<strong>\s*([A-Za-z]+ \d{1,2}, \d{4})\s*</strong>\s*</p>", re.IGNORECASE
)
# Match a single <li> with its full inner text
RC_ITEM_RE = re.compile(r"<li>(.*?)</li>", re.DOTALL | re.IGNORECASE)
RC_PAGE_RE = re.compile(
    r"<a\s+href='wiki\.cgi\?([A-Za-z0-9_][A-Za-z0-9_./-]*)'[^>]*class='body'[^>]*>([^<]+)</a>",
    re.IGNORECASE,
)
RC_TIME_RE = re.compile(r"\b(\d{2}:\d{2})\b")
RC_NEW_RE = re.compile(r"<strong>NEW</strong>", re.IGNORECASE)
RC_SUMMARY_RE = re.compile(r"<strong>\[([^\]]*)\]</strong>", re.IGNORECASE)
RC_MINOR_RE = re.compile(r"<em>Minor edit</em>", re.IGNORECASE)


def parse_rc(html_text: str) -> list[dict]:
    """Return one dict per <li>, keyed loosely to what we can pull from HTML."""
    # Trim to just the content-block region so we don't match navbars.
    content = extract_content_html(html_text)
    revisions: list[dict] = []
    current_date: str | None = None
    # Walk the content in order, alternating date-headers and li items.
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
        # First body-class anchor after "(diff)" is the page; the last body-class
        # anchor is the label.
        anchors = list(RC_PAGE_RE.finditer(item))
        # Skip the leading (diff) anchor which has no class='body'.
        body_anchors = [a for a in anchors if "class='body'" in item[a.start():a.end()]]
        if len(body_anchors) < 2:
            continue
        page_anchor = body_anchors[0]
        label_anchor = body_anchors[-1]
        page_name = page_anchor.group(1)
        label = label_anchor.group(1)
        m_time = RC_TIME_RE.search(item)
        hhmm = m_time.group(1) if m_time else None
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
        # Pull revision= from the about URL
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

# Diff page has one or more `<strong>OP: A,Bc C,D</strong>` markers, each followed
# by zero, one, or two colored tables (yellow #ffffaf = removed side, green
# #cfffcf = added side). We split the content on the marker positions and read
# the tables from each slice.
DIFF_MARKER_RE = re.compile(
    r"<strong>(Added|Deleted|Changed):\s*([^<]+?)\s*</strong>", re.IGNORECASE
)
DIFF_YELLOW_RE = re.compile(
    r"<table[^>]*bgcolor=#ffffaf[^>]*><tr><td>(.*?)</td></tr></table>",
    re.DOTALL | re.IGNORECASE,
)
DIFF_GREEN_RE = re.compile(
    r"<table[^>]*bgcolor=#cfffcf[^>]*><tr><td>(.*?)</td></tr></table>",
    re.DOTALL | re.IGNORECASE,
)


def parse_diff(diff_html: str) -> dict:
    inner = extract_content_html(diff_html)
    markers = list(DIFF_MARKER_RE.finditer(inner))
    if not markers:
        no_prev = "no other diffs" in inner or "Difference (last change)" not in inner
        return {"hunks": [], "no_previous_revision": no_prev}
    hunks = []
    for i, m in enumerate(markers):
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(inner)
        slice_html = inner[start:end]
        y = DIFF_YELLOW_RE.search(slice_html)
        g = DIFF_GREEN_RE.search(slice_html)
        hunks.append({
            "op": m.group(1).lower(),
            "span": m.group(2).strip(),
            "removed_text": strip_content_to_text(y.group(1)) if y else "",
            "added_text": strip_content_to_text(g.group(1)) if g else "",
        })
    return {"hunks": hunks, "no_previous_revision": False}


# --------------------------------------------------------------------- Time

MONTHS = {m: i for i, m in enumerate(
    ["January","February","March","April","May","June","July","August","September","October","November","December"], start=1)}


RSS_TZ_RE = re.compile(r"([+-]\d{2}:\d{2}|Z)$")


def derive_wiki_tz(rss_items: list[dict]) -> str | None:
    """Return the wiki's declared timezone offset by sampling RSS dc:date fields.
    All items on a single wiki share one offset in ProWiki - we return whichever
    offset shows up first. Returns e.g. '+01:00' or None if unknown.
    """
    for r in rss_items:
        d = r.get("date_iso") or ""
        m = RSS_TZ_RE.search(d)
        if m:
            return "+00:00" if m.group(1) == "Z" else m.group(1)
    return None


def rc_datetime(date_str: str | None, hhmm: str | None, tz_offset: str | None) -> str | None:
    """Reconstruct an ISO time from RC's wall clock. `tz_offset` should be the
    wiki's declared offset (e.g. '+01:00') derived from RSS; if unknown we mark
    the offset as '' and callers should treat time_grade='rc_wall_naive'.
    """
    if not date_str or not hhmm:
        return None
    parts = date_str.replace(",", "").split()
    if len(parts) != 3:
        return None
    month, day, year = parts
    if month not in MONTHS:
        return None
    h, m = hhmm.split(":")
    suffix = tz_offset if tz_offset else ""
    return f"{int(year):04d}-{MONTHS[month]:02d}-{int(day):02d}T{int(h):02d}:{int(m):02d}:00{suffix}"


# --------------------------------------------------------------------- URL helpers

def build_url(base: str, **params) -> str:
    q = urllib.parse.urlencode(params, safe="")
    return f"{base}?{q}"


def base_root(base: str) -> str:
    """Strip trailing /wiki.cgi from the base URL."""
    return base.rsplit("/", 1)[0] if base.endswith(".cgi") else base


# --------------------------------------------------------------------- Merge RC + RSS

RSS_ISO_HHMM_RE = re.compile(r"T(\d{2}:\d{2})")


def _rss_hhmm(date_iso: str | None) -> str | None:
    if not date_iso:
        return None
    m = RSS_ISO_HHMM_RE.search(date_iso)
    return m.group(1) if m else None


def merge_rc_rss(rc: list[dict], rss: list[dict], tz_offset: str | None = None) -> list[dict]:
    """Match RC and RSS entries by (page_name, hh:mm). The RSS feed emits one
    or more items per page (up to the feed cap) with second-accurate ISO
    timestamps whose wall-clock HH:MM matches the RC HTML's minute-precision
    display. RC has one row per revision within the window; RSS has whatever
    fits in the feed cap. For rows that don't align, fall back to reconstructing
    time from RC's `Month DD, YYYY` + `HH:MM` wall clock.
    """
    # Index RSS by (page_name, hh:mm). Each key can have multiple items in
    # theory; keep them as a list and consume in order.
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


# --------------------------------------------------------------------- Main scrape

def scrape(base: str, name: str, out: Path, days: int, sanity: bool,
           sleep: float = DEFAULT_SLEEP) -> None:
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    root = base_root(base)

    print(f"[{name}] fetching RC (days={days},all=1) ...", file=sys.stderr)
    rc_html, _ = fetch(build_url(base, action="browse", id="RecentChanges", days=str(days), all="1"), sleep=sleep)
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

    # Unique pages in order of first-seen (newest-first from RC)
    page_names: list[str] = []
    seen = set()
    for r in merged:
        if r["page_name"] not in seen:
            page_names.append(r["page_name"])
            seen.add(r["page_name"])
    print(f"[{name}]   {len(page_names)} unique pages", file=sys.stderr)

    if sanity:
        page_names = page_names[:2]
        print(f"[{name}] SANITY: limiting to {len(page_names)} pages", file=sys.stderr)

    page_bodies: dict[str, str] = {}
    page_diffs: dict[str, dict] = {}
    for pn in page_names:
        print(f"[{name}] page {pn}: body ...", file=sys.stderr)
        body_html, _ = fetch(build_url(base, action="browse", id=pn), sleep=sleep)
        page_bodies[pn] = strip_content_to_text(extract_content_html(body_html))
        print(f"[{name}] page {pn}: diff ...", file=sys.stderr)
        diff_html, _ = fetch(build_url(base, action="browse", diff="4", id=pn), sleep=sleep)
        page_diffs[pn] = parse_diff(diff_html)

    if sanity:
        # Summary only; don't write files
        print("\n=== SANITY SUMMARY ===")
        print(f"  base: {base}")
        print(f"  days window: {days}")
        print(f"  wiki tz offset: {wiki_tz or 'unknown'}")
        print(f"  rc rows: {len(revs)}  rss items: {len(rss_items)}  unique pages: {len(seen)}")
        for r in merged[:5]:
            print(f"  rev: {r['page_name']}  time={r.get('time_iso')} label={r['label']} summary={r.get('change_summary')!r} rev#={r.get('revision_number')}")
        for pn, body in list(page_bodies.items())[:2]:
            print(f"\n--- {pn} head body ({len(body)} bytes) ---")
            print(body[:400])
        return

    # ---- Emit output ----
    out.mkdir(parents=True, exist_ok=True)
    build_output(name=name, out=out, base=base, days=days, started=started,
                 merged=merged, page_names=page_names,
                 page_bodies=page_bodies, page_diffs=page_diffs,
                 rc_html=rc_html, rss_items=rss_items, wiki_tz=wiki_tz)


def build_output(*, name: str, out: Path, base: str, days: int, started: str,
                 merged: list[dict], page_names: list[str],
                 page_bodies: dict[str, str], page_diffs: dict[str, dict],
                 rc_html: str, rss_items: list[dict], wiki_tz: str | None) -> None:
    # Ordering: chronological ascending by time_iso (RC is descending).
    def sortable_time(r):
        t = r.get("time_iso") or ""
        return t
    merged_sorted = sorted(merged, key=sortable_time)

    # seq per page in chronological order
    seq_by_page: Counter[str] = Counter()
    revisions_out = []
    events_out = []
    for r in merged_sorted:
        pn = r["page_name"]
        seq_by_page[pn] += 1
        seq = seq_by_page[pn]
        # Body only for the head revision of each page (== last in chronological order).
        is_head = (r == next((x for x in reversed(merged_sorted) if x["page_name"] == pn), None))
        body = page_bodies.get(pn) if is_head else None
        body_bytes = body.encode("utf-8") if body is not None else None
        body_sha = hashlib.sha256(body_bytes).hexdigest() if body_bytes is not None else None
        diff = page_diffs.get(pn) if is_head else None
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
            "body_encoding": "html_stripped_utf8" if body is not None else None,
            "wiki_revision_number": r.get("revision_number"),
            "is_new_page": r.get("is_new_page"),
            "is_minor_edit": r.get("is_minor_edit"),
            "body_availability": "head_only" if is_head else "metadata_only",
        })
        events_out.append({
            "event_id": f"save:{rev_id}",
            "event_type": "save",
            "time": r.get("time_iso"),
            "time_grade": r.get("time_source"),
            "wiki": name,
            "revision_ref": rev_id,
        })

    # ---- pages.jsonl ----
    pages_out = []
    for pn in sorted({r["page_name"] for r in merged_sorted}):
        rows_for_page = [r for r in merged_sorted if r["page_name"] == pn]
        head = rows_for_page[-1]
        head_body = page_bodies.get(pn) or ""
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
            "body_bytes": len(head_body.encode("utf-8")),
            "deleted_live": False,
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

    # ---- labels.jsonl ----
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

    # ---- Write ----
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
            "engine": "prowiki (usemod-derived)",
            "scraper": "scrape/wikiservice_scrape.py",
        },
        "cut": {
            "kind": "recent_changes_window",
            "days": days,
            "endpoint": build_url(base, action="browse", id="RecentChanges", days=str(days), all="1"),
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
        "limitations": [
            "Body is HTML-stripped rendered output, not raw wiki source. "
            "Wiki markup (WikiLinks, bold/italic, headings) is largely lost; "
            "raw URLs survive because they appear verbatim in the render.",
            "Bodies are only captured for the HEAD revision of each page. "
            "Non-head revisions in this cut have body=null (body_availability='metadata_only').",
            "The head-to-previous diff hunks ARE captured (revisions.jsonl.hunks "
            "for the head row) - but only that one diff, since action=log and "
            "action=archive are admin-gated on this engine.",
            "No IPs are exposed (n_ips/n_ip16/ip16 are all null). The wiki UI "
            "only shows the editor's label (nickname).",
            "Time precision: RSS entries are second-accurate with timezone offset. "
            "RC-only rows are minute-accurate wall time and get uncertainty_seconds=60.",
            "n_revs_before is unknown - RecentChanges window is our only visibility "
            "into revision counts, and older revisions may exist that we can't see.",
        ],
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
    p.add_argument("--base", required=True, help="Base URL, e.g. https://www.wikiservice.at/user/milk/wiki.cgi")
    p.add_argument("--name", required=True, help="Short wiki name, used in output IDs, e.g. 'milk'")
    p.add_argument("--out", type=Path, help="Output directory (default: agent-logs/<name>/)")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--sanity", action="store_true", help="Fetch minimum viable subset, print summary, don't write files")
    p.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Seconds between requests")
    args = p.parse_args()

    out = args.out or Path("agent-logs") / args.name
    scrape(args.base, args.name, out, args.days, args.sanity, args.sleep)


if __name__ == "__main__":
    main()
