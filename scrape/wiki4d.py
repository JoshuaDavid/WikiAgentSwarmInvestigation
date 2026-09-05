#!/usr/bin/env python3
"""Scrape prowiki.org/wiki4d (a ProWiki wiki using the STANDARD skin) into
agent-logs/<name>/ layout.

Forked from scrape/wikiservice_scrape.py. Same engine (ProWiki, UseModWiki
derivative). Different site skin: the content is inside `<div id="content">`
and terminates at `<div id="content-menu">`, not `<td class="content">` inside
a shell table. The RC and body pages are served as UTF-8; the RSS feed is
served as ISO-8859-1. Dates in this wiki are US English (`September 4, 2026`)
just like the milk wiki.

What differs vs wikiservice_scrape.py:
  * `extract_content_html` uses div boundaries.
  * `fetch` prefers UTF-8, falls back to iso-8859-1.
  * Nothing else. RC row structure, RSS structure, diff table markup, and the
    time/label semantics are identical, so those parsers are reused verbatim.
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
DEFAULT_SLEEP = 3.0  # four ProWiki agents run concurrently against this farm
LOCK_BACKOFFS = (60, 300)  # seconds to wait between Lock retries; keep short so we can move on and refetch later

# --------------------------------------------------------------------- HTTP

# When ProWiki rate-limits an anon client it serves a short "Wiki4D: Lock"
# document (~360 bytes). It is not an HTTP error - status is 200 - so the
# only signal is the response body.
LOCK_TITLE_RE = re.compile(r"<TITLE>[^<]*:\s*Lock</TITLE>", re.IGNORECASE)
LOCK_RATE_RE = re.compile(r"your access rate is too high", re.IGNORECASE)


def _looks_like_lock(text: str) -> bool:
    return bool(LOCK_TITLE_RE.search(text) or LOCK_RATE_RE.search(text))


def fetch(url: str, *, sleep: float = DEFAULT_SLEEP) -> tuple[str, str]:
    """Return (text, content_type). HTML on wiki4d is UTF-8; the RSS feed
    declares ISO-8859-1. Try both, in that order.

    Retries when the server returns its "Lock" rate-limit page: back off for a
    growing interval and try again. Gives up after LOCK_BACKOFFS is exhausted,
    then returns whatever the last response was so the caller can decide.
    """
    def _do_fetch():
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
        for enc in ("utf-8", "iso-8859-1"):
            try:
                return raw.decode(enc), ctype
            except UnicodeDecodeError:
                continue
        return raw.decode("iso-8859-1", errors="replace"), ctype

    text, ctype = _do_fetch()
    backoffs = list(LOCK_BACKOFFS)
    while _looks_like_lock(text) and backoffs:
        wait = backoffs.pop(0)
        print(f"[fetch] Lock page from {url!r}; backing off {wait}s", file=sys.stderr)
        time.sleep(wait)
        text, ctype = _do_fetch()
    time.sleep(sleep)
    return text, ctype


# --------------------------------------------------------------------- HTML utils

# The wiki4d skin wraps the article body in `<div id="content"> ... </div>`
# and the next sibling is `<div id="content-menu">`. There is no nested div
# with a class we could use for a tighter fence. Match on the opening tag and
# stop at the content-menu sibling.
CONTENT_START_RE = re.compile(
    r'<div\s+id="content"[^>]*>', re.IGNORECASE
)
CONTENT_END_RE = re.compile(
    r'<div\s+id="content-menu"', re.IGNORECASE
)
TITLE_H1_RE = re.compile(
    r'<h1>\s*<a[^>]*class=[\'"]title[\'"][^>]*>.*?</a>\s*</h1>', re.DOTALL | re.IGNORECASE
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
    # Strip the leading <h1><a class=title>...</a></h1> title block.
    inner = TITLE_H1_RE.sub("", inner)
    # And the empty <strong></strong> that follows it.
    inner = re.sub(r"<strong>\s*</strong>", "", inner)
    return inner


def strip_content_to_text(inner_html: str) -> str:
    """Turn the content HTML into a lossy plain-text approximation of wiki source."""
    inner_html = ANCHOR_TEXT_RE.sub(lambda m: m.group(1), inner_html)
    inner_html = BR_RE.sub("\n", inner_html)
    inner_html = P_RE.sub("\n", inner_html)
    inner_html = HTML_TAG_RE.sub("", inner_html)
    text = html.unescape(inner_html)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = MULTIBLANK_RE.sub("\n\n", text).strip()
    return text


# --------------------------------------------------------------------- RecentChanges

# Same row shape as milk wiki:
#   <li><a href='wiki.cgi?action=browse&amp;diff=4&amp;id=Page' ...>(diff)</a>
#       <a href='wiki.cgi?Page' class='body'>Page</a> HH:MM
#       <strong>[summary]</strong> . . . . .
#       <a href='wiki.cgi?Editor' class='body'>Editor</a></li>
RC_DATE_RE = re.compile(
    r"<p>\s*<strong>\s*([A-Za-z]+ \d{1,2}, \d{4})\s*</strong>\s*</p>", re.IGNORECASE
)
RC_ITEM_RE = re.compile(r"<li>(.*?)</li>", re.DOTALL | re.IGNORECASE)
RC_PAGE_RE = re.compile(
    r"<a\s+href='wiki\.cgi\?([A-Za-z0-9_][A-Za-z0-9_./-]*)'[^>]*class='body'[^>]*>([^<]+)</a>",
    re.IGNORECASE,
)
RC_TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")
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
        if m_time:
            h, mm = m_time.group(1).split(":")
            hhmm = f"{int(h):02d}:{mm}"
        else:
            hhmm = None
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
    for r in rss_items:
        d = r.get("date_iso") or ""
        m = RSS_TZ_RE.search(d)
        if m:
            return "+00:00" if m.group(1) == "Z" else m.group(1)
    return None


def rc_datetime(date_str: str | None, hhmm: str | None, tz_offset: str | None) -> str | None:
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


# --------------------------------------------------------------------- Main scrape

def scrape(base: str, name: str, out: Path, days: int, sanity: bool,
           sleep: float = DEFAULT_SLEEP) -> None:
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

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
    locked_pages: list[str] = []
    for pn in page_names:
        print(f"[{name}] page {pn}: body ...", file=sys.stderr)
        body_html, _ = fetch(build_url(base, action="browse", id=pn), sleep=sleep)
        if _looks_like_lock(body_html):
            print(f"[{name}] page {pn}: LOCKED after retries; skipping body/diff", file=sys.stderr)
            locked_pages.append(pn)
            continue
        page_bodies[pn] = strip_content_to_text(extract_content_html(body_html))
        print(f"[{name}] page {pn}: diff ...", file=sys.stderr)
        diff_html, _ = fetch(build_url(base, action="browse", diff="4", id=pn), sleep=sleep)
        if _looks_like_lock(diff_html):
            print(f"[{name}] page {pn}: diff LOCKED after retries; leaving diff empty", file=sys.stderr)
            page_diffs[pn] = {"hunks": [], "no_previous_revision": False, "lock": True}
        else:
            page_diffs[pn] = parse_diff(diff_html)

    if locked_pages:
        print(f"[{name}] WARNING: {len(locked_pages)} pages locked out and skipped", file=sys.stderr)

    if sanity:
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

    out.mkdir(parents=True, exist_ok=True)
    build_output(name=name, out=out, base=base, days=days, started=started,
                 merged=merged, page_names=page_names,
                 page_bodies=page_bodies, page_diffs=page_diffs,
                 rc_html=rc_html, rss_items=rss_items, wiki_tz=wiki_tz,
                 locked_pages=locked_pages)


def build_output(*, name: str, out: Path, base: str, days: int, started: str,
                 merged: list[dict], page_names: list[str],
                 page_bodies: dict[str, str], page_diffs: dict[str, dict],
                 rc_html: str, rss_items: list[dict], wiki_tz: str | None,
                 locked_pages: list[str] | None = None) -> None:
    locked_pages = locked_pages or []
    def sortable_time(r):
        t = r.get("time_iso") or ""
        return t
    merged_sorted = sorted(merged, key=sortable_time)

    locked_set = set(locked_pages)
    seq_by_page: Counter[str] = Counter()
    revisions_out = []
    events_out = []
    for r in merged_sorted:
        pn = r["page_name"]
        seq_by_page[pn] += 1
        seq = seq_by_page[pn]
        is_head = (r == next((x for x in reversed(merged_sorted) if x["page_name"] == pn), None))
        body = page_bodies.get(pn) if is_head else None
        body_bytes = body.encode("utf-8") if body is not None else None
        body_sha = hashlib.sha256(body_bytes).hexdigest() if body_bytes is not None else None
        diff = page_diffs.get(pn) if is_head else None
        if is_head:
            body_avail = "lock_denied" if pn in locked_set else "head_only"
        else:
            body_avail = "metadata_only"
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
            "body_availability": body_avail,
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

    manifest = {
        "generated_at": started,
        "source": {
            "wiki_name": name,
            "base_url": base,
            "engine": "prowiki (usemod-derived, standard skin)",
            "scraper": "scrape/wiki4d.py",
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
            "locked_pages": {"value": len(locked_pages)},
        },
        "locked_pages": sorted(locked_pages),
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
            "Pages listed in manifest.locked_pages had their head body/diff blocked "
            "by the wiki's anti-scrape 'Wiki4D: Lock' response even after retries. "
            "Those pages' head rev has body=null and body_availability='lock_denied'; "
            "downstream can re-fetch them by name on a subsequent run.",
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
    p.add_argument("--base", required=True, help="Base URL, e.g. https://prowiki.org/wiki4d/wiki.cgi")
    p.add_argument("--name", required=True, help="Short wiki name, used in output IDs, e.g. 'wiki4d'")
    p.add_argument("--out", type=Path, help="Output directory (default: agent-logs/<name>/)")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--sanity", action="store_true", help="Fetch minimum viable subset, print summary, don't write files")
    p.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Seconds between requests")
    args = p.parse_args()

    out = args.out or Path("agent-logs") / args.name
    scrape(args.base, args.name, out, args.days, args.sanity, args.sleep)


if __name__ == "__main__":
    main()
