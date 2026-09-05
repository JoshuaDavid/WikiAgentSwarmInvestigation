#!/usr/bin/env python3
"""Scrape the ProbierWiki (wikiservice.at/probier) into agent-logs/<name>/ layout.

Forked from wikiservice_scrape.py. Two things differ from the milk-wiki base
that force a fork rather than a flag:

  1. Page shell has no <td class="content"> wrapper. The whole ProWiki-STANDARD
     skin is inline: nav, then <hr>, then page content, then <hr>, then nav.
     Content extraction anchors on the outer <hr> pair, not on a content <td>.
  2. Language is German. RecentChanges date headers read "5. September 2026",
     not "September 5, 2026". Diff-hunk markers read "Verändert" / "Entfernt" /
     "Eingefügt", not "Changed" / "Deleted" / "Added". Both parsers must accept
     the German vocabulary; we keep the English mappings so a bilingual page
     still parses.

Everything else - RC list structure, RSS shape, hunk table colors, URL scheme -
matches the milk-wiki scraper. This file therefore duplicates the RSS parser,
the merge logic, the CLI, and the output writer verbatim. Only the HTML-shell
extractor, the RC-date parser, and the diff-marker regex are changed.

Usage:
    scrape/probier.py --sanity
    scrape/probier.py --sleep 3.0        # full scrape into agent-logs/probier/
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
DEFAULT_BASE = "https://www.wikiservice.at/probier/wiki.cgi"
DEFAULT_NAME = "probier"
DEFAULT_DAYS = 120
# Four ProWiki-farm agents share one small host. Be extra polite.
DEFAULT_SLEEP = 3.0

# --------------------------------------------------------------------- HTTP

def fetch(url: str, *, sleep: float = DEFAULT_SLEEP) -> tuple[str, str]:
    """Return (text, content_type). ProWiki serves iso-8859-1."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
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

# The ProWiki-STANDARD skin brackets the actual page content with a pair of
# horizontal rules. Outer structure of every page (RC, browse, diff):
#
#   <nav bar>...<hr>
#   <PAGE CONTENT>
#   <hr>
#   <nav bar>...<form>...</body></HTML>
#
# We take the substring between the first "<hr>" and the last "<hr>". Diff
# pages sometimes emit "<hr />" inside the content on the "before" body render;
# taking last-<hr> catches the true page-end rule.
HR_RE = re.compile(r"<hr\s*/?\s*>", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
ANCHOR_TEXT_RE = re.compile(r"<a\b[^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
P_RE = re.compile(r"<p\s*/?>|</p>", re.IGNORECASE)
MULTIBLANK_RE = re.compile(r"\n{3,}")


def extract_content_html(page_html: str) -> str:
    """Slice the region between the first and the last <hr> on the page.

    ProWiki-STANDARD skin has two navbar strips separated by <hr>s. The page
    body sits between them. If the page has only one <hr> (defensive; not
    observed on probier) we take everything after it. If it has none we return
    the whole page - the fallback the rest of the pipeline tolerates.
    """
    hrs = list(HR_RE.finditer(page_html))
    if len(hrs) < 2:
        if len(hrs) == 1:
            return page_html[hrs[0].end():]
        return page_html
    start = hrs[0].end()
    end = hrs[-1].start()
    return page_html[start:end]


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

# German date header: "<p><strong>5. September 2026</strong></p>".
# English is accepted defensively so a bilingual dump still parses.
RC_DATE_DE_RE = re.compile(
    r"<p>\s*<strong>\s*(\d{1,2})\.\s*([A-Za-zä-üÄ-Ü]+)\s+(\d{4})\s*</strong>\s*</p>",
    re.IGNORECASE,
)
RC_DATE_EN_RE = re.compile(
    r"<p>\s*<strong>\s*([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})\s*</strong>\s*</p>",
    re.IGNORECASE,
)
RC_ITEM_RE = re.compile(r"<li>(.*?)</li>", re.DOTALL | re.IGNORECASE)
RC_PAGE_RE = re.compile(
    # `%` is present because ProWiki URL-encodes non-ASCII page names in the
    # href (e.g. "J%fcrgenMargetich" -> "JürgenMargetich"). Without % here
    # the anchor doesn't match and the row is silently dropped.
    r"<a\s+href='wiki\.cgi\?([A-Za-z0-9_%][A-Za-z0-9_.%/-]*)'[^>]*class='body'[^>]*>([^<]+)</a>",
    re.IGNORECASE,
)
RC_TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")
RC_NEW_RE = re.compile(r"<strong>NEW</strong>", re.IGNORECASE)
RC_SUMMARY_RE = re.compile(r"<strong>\[([^\]]*)\]</strong>", re.IGNORECASE)
RC_MINOR_RE = re.compile(r"<em>Minor edit</em>", re.IGNORECASE)
# Anonymous edits: instead of the trailing "class='body'" anchor there is a
# plain IPv4 text after the ". . . . ." separator.
RC_IP_TRAILING_RE = re.compile(r"\.\s*\.\s*\.\s*\.\s*\.\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*$")

# Month names in German (also accepts English fallback for mixed dumps).
MONTHS_DE = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
    "oktober": 10, "november": 11, "dezember": 12,
}
MONTHS_EN = {
    m.lower(): i for i, m in enumerate(
        ["January","February","March","April","May","June","July","August",
         "September","October","November","December"], start=1)
}


def _rc_date_iter(content: str):
    """Yield (start, end, "YYYY-MM-DD") for each date header in content order.

    Accepts both German ("5. September 2026") and English ("September 5, 2026")
    date-header forms so a bilingual RC (rare, but possible via ?lang=1) parses.
    """
    hits = []
    for m in RC_DATE_DE_RE.finditer(content):
        day, month, year = m.group(1), m.group(2).lower(), m.group(3)
        mnum = MONTHS_DE.get(month) or MONTHS_EN.get(month)
        if mnum is None:
            continue
        hits.append((m.start(), m.end(), f"{int(year):04d}-{mnum:02d}-{int(day):02d}"))
    for m in RC_DATE_EN_RE.finditer(content):
        month, day, year = m.group(1).lower(), m.group(2), m.group(3)
        mnum = MONTHS_EN.get(month) or MONTHS_DE.get(month)
        if mnum is None:
            continue
        hits.append((m.start(), m.end(), f"{int(year):04d}-{mnum:02d}-{int(day):02d}"))
    hits.sort()
    return hits


def parse_rc(html_text: str) -> list[dict]:
    """Return one dict per <li>, keyed loosely to what we can pull from HTML.

    Handles two RC row shapes on probier:
      (a) Labeled edit: two `class='body'` anchors after the leading (diff)
          anchor - first is the page, last is the editor label.
      (b) Anonymous edit: one `class='body'` page anchor and a trailing plain
          IPv4 as the editor label.
    """
    content = extract_content_html(html_text)
    date_hits = _rc_date_iter(content)
    revisions: list[dict] = []
    pos = 0
    di = 0
    current_date: str | None = None
    while pos < len(content):
        while di < len(date_hits) and date_hits[di][0] < pos:
            di += 1
        m_item = RC_ITEM_RE.search(content, pos)
        if m_item is None:
            break
        # Advance current_date past any date headers that precede this item.
        while di < len(date_hits) and date_hits[di][0] < m_item.start():
            current_date = date_hits[di][2]
            di += 1
        item = m_item.group(1)
        pos = m_item.end()
        anchors = list(RC_PAGE_RE.finditer(item))
        body_anchors = [a for a in anchors if "class='body'" in item[a.start():a.end()]]
        if len(body_anchors) < 2:
            # Anonymous-edit shape: one body anchor + trailing IPv4.
            if len(body_anchors) == 1:
                page_anchor = body_anchors[0]
                page_name = page_anchor.group(1)
                m_ip = RC_IP_TRAILING_RE.search(item.rstrip())
                if not m_ip:
                    continue
                label = m_ip.group(1)
            else:
                continue
        else:
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
            # ProWiki URL-encodes non-ASCII page names in the ISO-8859-1
            # charset (%fc = ü), not UTF-8. Decode with latin-1 so
            # J%fcrgenMargetich becomes "JürgenMargetich", not mojibake.
            "page_name": urllib.parse.unquote(page_name, encoding="iso-8859-1"),
            "label": urllib.parse.unquote(label, encoding="iso-8859-1"),
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

# German diff marker vocabulary. English accepted defensively.
DIFF_MARKER_RE = re.compile(
    r"<strong>(Added|Deleted|Changed|Eingef(?:ü|&uuml;)gt|Entfernt|Ver(?:ä|&auml;)ndert)"
    r":\s*([^<]+?)\s*</strong>",
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
    "added": "added", "eingefügt": "added", "eingef&uuml;gt": "added",
    "deleted": "deleted", "entfernt": "deleted",
    "changed": "changed", "verändert": "changed", "ver&auml;ndert": "changed",
}


def parse_diff(diff_html: str) -> dict:
    inner = extract_content_html(diff_html)
    markers = list(DIFF_MARKER_RE.finditer(inner))
    if not markers:
        # "keine anderen Diffs" is the German for "no other diffs"; the
        # English string appears on English-language wikis.
        no_prev = (
            "keine anderen diffs" in inner.lower()
            or "no other diffs" in inner.lower()
        )
        return {"hunks": [], "no_previous_revision": no_prev}
    hunks = []
    for i, m in enumerate(markers):
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(inner)
        slice_html = inner[start:end]
        y = DIFF_YELLOW_RE.search(slice_html)
        g = DIFF_GREEN_RE.search(slice_html)
        op = DIFF_OP_MAP.get(m.group(1).lower(), m.group(1).lower())
        hunks.append({
            "op": op,
            "span": m.group(2).strip(),
            "removed_text": strip_content_to_text(y.group(1)) if y else "",
            "added_text": strip_content_to_text(g.group(1)) if g else "",
        })
    return {"hunks": hunks, "no_previous_revision": False}


# --------------------------------------------------------------------- Time

RSS_TZ_RE = re.compile(r"([+-]\d{2}:\d{2}|Z)$")


def derive_wiki_tz(rss_items: list[dict]) -> str | None:
    for r in rss_items:
        d = r.get("date_iso") or ""
        m = RSS_TZ_RE.search(d)
        if m:
            return "+00:00" if m.group(1) == "Z" else m.group(1)
    return None


def rc_datetime(date_ymd: str | None, hhmm: str | None, tz_offset: str | None) -> str | None:
    """Reconstruct an ISO time. `date_ymd` is already in YYYY-MM-DD form."""
    if not date_ymd or not hhmm:
        return None
    h, m = hhmm.split(":")
    suffix = tz_offset if tz_offset else ""
    return f"{date_ymd}T{int(h):02d}:{int(m):02d}:00{suffix}"


# --------------------------------------------------------------------- URL helpers

def build_url(base: str, **params) -> str:
    # ProWiki reads path params as ISO-8859-1. If we send %C3%BC (UTF-8 for ü)
    # the server treats those bytes as literal characters and can't find the
    # page. Round-trip any str value through iso-8859-1 bytes before quoting
    # so ü comes out as %FC (Latin-1), not %C3%BC (UTF-8). Fall back to UTF-8
    # for characters that don't fit in Latin-1.
    coerced: dict[str, bytes | str] = {}
    for k, v in params.items():
        if isinstance(v, str):
            try:
                coerced[k] = v.encode("iso-8859-1")
            except UnicodeEncodeError:
                coerced[k] = v
        else:
            coerced[k] = v
    q = urllib.parse.urlencode(coerced, safe="")
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


def _norm_hhmm(hhmm: str | None) -> str:
    """RC shows single-digit hours as "0:09"; RSS reports "00:09". Zero-pad
    so the two representations key-compare cleanly."""
    if not hhmm:
        return ""
    h, m = hhmm.split(":")
    return f"{int(h):02d}:{int(m):02d}"


def merge_rc_rss(rc: list[dict], rss: list[dict], tz_offset: str | None = None) -> list[dict]:
    rss_by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rss:
        key = (r.get("page_name") or "", _rss_hhmm(r.get("date_iso")) or "")
        if key[0] and key[1]:
            rss_by_key[key].append(r)

    merged = []
    for entry in rc:
        pn = entry["page_name"]
        hhmm = _norm_hhmm(entry.get("hhmm"))
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
            hunks = page_diffs.get(pn, {}).get("hunks") or []
            print(f"  diff hunks: {len(hunks)}")
            for h in hunks[:3]:
                print(f"    op={h['op']} span={h['span']!r}")
                if h["removed_text"]:
                    print(f"      -: {h['removed_text'][:80]}")
                if h["added_text"]:
                    print(f"      +: {h['added_text'][:80]}")
        return

    out.mkdir(parents=True, exist_ok=True)
    build_output(name=name, out=out, base=base, days=days, started=started,
                 merged=merged, page_names=page_names,
                 page_bodies=page_bodies, page_diffs=page_diffs,
                 rc_html=rc_html, rss_items=rss_items, wiki_tz=wiki_tz)


def build_output(*, name: str, out: Path, base: str, days: int, started: str,
                 merged: list[dict], page_names: list[str],
                 page_bodies: dict[str, str], page_diffs: dict[str, dict],
                 rc_html: str, rss_items: list[dict], wiki_tz: str | None) -> None:
    def sortable_time(r):
        return r.get("time_iso") or ""
    merged_sorted = sorted(merged, key=sortable_time)

    seq_by_page: Counter[str] = Counter()
    revisions_out = []
    events_out = []
    # Precompute the last (chronologically newest) row per page so the
    # is_head check is O(1) instead of O(N) per revision.
    last_row_by_page = {}
    for r in merged_sorted:
        last_row_by_page[r["page_name"]] = r
    for r in merged_sorted:
        pn = r["page_name"]
        seq_by_page[pn] += 1
        seq = seq_by_page[pn]
        is_head = last_row_by_page[pn] is r
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
            "engine": "prowiki (usemod-derived); STANDARD skin (no content <td>)",
            "language": "de",
            "scraper": "scrape/probier.py",
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
            "No usernames are hidden, but anonymous edits expose the raw IPv4 "
            "as the label. label rows whose value matches a dotted IPv4 are "
            "anonymous edits, not named handles. n_ips/n_ip16/ip16 remain null "
            "because we do not separately track the IP field.",
            "Time precision: RSS entries are second-accurate with timezone offset. "
            "RC-only rows are minute-accurate wall time and get uncertainty_seconds=60.",
            "n_revs_before is unknown - RecentChanges window is our only visibility "
            "into revision counts, and older revisions may exist that we can't see.",
            "German RC/diff vocabulary: date headers are 'D. Month YYYY', diff "
            "markers are Verändert/Entfernt/Eingefügt. Parser accepts both German "
            "and English forms; op values are normalized to English (added/deleted/changed).",
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
    p.add_argument("--base", default=DEFAULT_BASE, help=f"Base URL (default: {DEFAULT_BASE})")
    p.add_argument("--name", default=DEFAULT_NAME, help=f"Short wiki name (default: {DEFAULT_NAME})")
    p.add_argument("--out", type=Path, help="Output directory (default: agent-logs/<name>/)")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--sanity", action="store_true", help="Fetch minimum viable subset, print summary, don't write files")
    p.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Seconds between requests")
    args = p.parse_args()

    out = args.out or Path("agent-logs") / args.name
    scrape(args.base, args.name, out, args.days, args.sanity, args.sleep)


if __name__ == "__main__":
    main()
