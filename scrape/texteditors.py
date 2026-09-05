#!/usr/bin/env python3
"""Scrape a UseModWiki (upstream) public wiki into agent-logs/<name>/ layout.

Forked from `wikiservice_scrape.py`, which targets the ProWiki fork on
wikiservice.at. This variant is tuned to run against `texteditors.org`, an
upstream UseModWiki install. The differences from the ProWiki fork:

- URL extension is `.pl`, not `.cgi`. Parsers must accept either.
- HTML uses double-quoted attributes and lacks the `<td class="content">`
  content-block shell entirely. Content is delimited by `<div class=allwiki>`
  and the trailing `<form>` (the edit-search form).
- No RSS. `action=rss` returns "Invalid action parameter rss";
  `RecentChangesRss` is treated as a normal (nonexistent) page name. So we
  have no second-precision timestamps and no engine-side revision numbers.
- RC times are in AM/PM form: `3:14 pm`, `11:38 am`, converted to 24h ISO.
- Labels are usually a raw IP or a reverse-DNS hostname printed after the
  ` . . . . . ` separator, not an `<a>` anchor. Both forms must be accepted.

What we CANNOT capture (admin-only): raw wiki source, revision bodies older
than N-1, `action=log` / `action=archive`, IPs beyond what appears as a
label, request-level metadata, engine revision numbers.

Time zone is derived by comparing the wiki's own "Page generated ..." wall
clock against the HTTP `Date` header on the same response. For texteditors,
one probe put wiki wall 20:13 vs HTTP Date 01:13 UTC (next day) - a -05:00
offset. Cached in the manifest as `wiki_tz_offset` when derivable, else
`null` and rows use `time_grade='rc_wall_naive'`.

Output layout mirrors agent-logs/milkwiki. Fields that don't exist for the
UseMod-upstream scrape (`wiki_revision_number` etc.) are `null`; a
`manifest.limitations` list records what's missing.

Usage:
    texteditors.py --base BASE --name NAME --out OUTDIR [--days N] [--sanity]
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils as email_utils
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
DEFAULT_SLEEP = 1.5  # texteditors.org is a small private host

# --------------------------------------------------------------------- HTTP

def fetch(url: str, *, sleep: float = DEFAULT_SLEEP) -> tuple[str, str, str | None]:
    """Return (text, content_type, http_date_header).
    UseMod defaults to ISO-8859-1; the `Date` header is used to derive TZ."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        ctype = resp.headers.get("Content-Type", "")
        http_date = resp.headers.get("Date")
    time.sleep(sleep)
    for enc in ("iso-8859-1", "utf-8"):
        try:
            return raw.decode(enc), ctype, http_date
        except UnicodeDecodeError:
            continue
    return raw.decode("iso-8859-1", errors="replace"), ctype, http_date


# --------------------------------------------------------------------- HTML utils

# UseModWiki upstream lacks the ProWiki `<td class="content">` shell. Content
# sits inside `<div class=allwiki>` and ends where the footer <form> starts
# (the edit-search form). We anchor there.
CONTENT_START_RE = re.compile(
    r'<div\s+class=["\']?allwiki["\']?[^>]*>', re.IGNORECASE
)
CONTENT_END_RE = re.compile(
    r'<form\b[^>]*action=["\']?wiki\.(?:pl|cgi)["\']?', re.IGNORECASE
)
# Strip the h1 header block (contains title + top navbar).
HEADER_STRIP_RE = re.compile(
    r'<h1>.*?</h1>\s*(?:<a[^>]*>[^<]*</a>\s*(?:\|\s*)?)*<br\s*/?>\s*<hr>',
    re.DOTALL | re.IGNORECASE,
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
    """Return the middle content region of a UseMod page.

    Some pages open the content region with `<div class=allwiki>` and end it
    with the footer form; others have ad-injection blocks inside the h1 that
    we cut past with HEADER_STRIP_RE.
    """
    m = CONTENT_START_RE.search(page_html)
    if not m:
        return ""
    after = page_html[m.end():]
    end = CONTENT_END_RE.search(after)
    inner = after[:end.start()] if end else after
    inner = HEADER_STRIP_RE.sub("", inner)
    inner = TITLE_SPAN_RE.sub("", inner)
    inner = re.sub(r"<b>\s*</b>", "", inner)
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

# One RC list item on UseMod-upstream looks like:
#   <li><a href="wiki.pl?action=browse&diff=1&id=WikiSandbox">(diff)</a>
#       <a href="wiki.pl?WikiSandbox">WikiSandbox</a> 3:14 pm
#       <strong>[collusion.wiki test marker]</strong>
#       . . . . . 170.62.100.190
#
# The trailing label after ` . . . . . ` may be either:
#   * a raw IP (e.g. `170.62.100.190`)
#   * a hostname (e.g. `ool-45763c3e.dyn.optonline.net`)
#   * an `<a href="wiki.pl?Handle">Handle</a>` anchor (rare on this wiki)
# Dates are `<p><strong>Month D, YYYY</strong><p>` (unclosed p is legal HTML3).

RC_DATE_RE = re.compile(
    r"<p>\s*<strong>\s*([A-Za-z]+ \d{1,2}, \d{4})\s*</strong>\s*<p>", re.IGNORECASE
)
# We do NOT anchor on </li> because UseMod emits <li> with no closer inside <UL>.
# Instead we split on the next <li> or the closing </UL>.
RC_ITEM_SPLIT_RE = re.compile(r"<li>", re.IGNORECASE)
RC_ITEM_END_RE = re.compile(r"</ul>|<li>|<p>", re.IGNORECASE)

# Page anchor: <a href="wiki.pl?PageName">visible</a>, single OR double quote OK.
# We look for the SECOND page anchor after the leading `(diff)` anchor.
RC_PAGE_RE = re.compile(
    r"""<a\s+href=["']wiki\.(?:pl|cgi)\?([A-Za-z0-9_][A-Za-z0-9_./()%-]*?)["'][^>]*>([^<]+)</a>""",
    re.IGNORECASE,
)
# AM/PM time: `3:14 pm`, `11:38 am` (also allow `12:07 pm`).
RC_TIME_AMPM_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*([ap]m)\b", re.IGNORECASE)
# 24h fallback (in case a variant of the wiki uses it):
RC_TIME_24H_RE = re.compile(r"\b(\d{2}):(\d{2})\b")
RC_NEW_RE = re.compile(r"<strong>NEW</strong>", re.IGNORECASE)
RC_SUMMARY_RE = re.compile(r"<strong>\[([^\]]*)\]</strong>", re.IGNORECASE)
RC_MINOR_RE = re.compile(r"<em>Minor edit</em>", re.IGNORECASE)
# Everything after the ` . . . . . ` separator up to end of <li>-like content.
RC_LABEL_TAIL_RE = re.compile(r"\.\s+\.\s+\.\s+\.\s+\.\s+(.*?)(?:$)", re.DOTALL)


def _hhmm_to_24h(m: re.Match) -> str:
    """Convert AM/PM HH:MM to 24h HH:MM string."""
    hh = int(m.group(1))
    mm = int(m.group(2))
    ap = m.group(3).lower()
    if ap == "am":
        hh = 0 if hh == 12 else hh
    else:
        hh = 12 if hh == 12 else hh + 12
    return f"{hh:02d}:{mm:02d}"


def _extract_label_from_tail(tail: str) -> str | None:
    """Given the text after ` . . . . . `, extract the actor label.

    Two forms accepted:
      * Anchor: `<a href="wiki.pl?Handle">Handle</a>` - use anchor text.
      * Plain: `170.62.100.190` or `ool-abc.example.com` - use raw string.
    """
    anchor = RC_PAGE_RE.search(tail)
    if anchor:
        return html.unescape(anchor.group(2)).strip()
    text = HTML_TAG_RE.sub("", tail)
    text = html.unescape(text).strip()
    # Some tails have trailing markup fragments; take the first whitespace-terminated token.
    m = re.match(r"([\S]+)", text)
    return m.group(1) if m else None


def parse_rc(html_text: str) -> list[dict]:
    """Return one dict per RC row on a UseMod-upstream RecentChanges page."""
    content = extract_content_html(html_text)
    # Split content into date-headed chunks. RC_DATE_RE finds the day headers.
    date_positions = [(m.start(), m.end(), m.group(1)) for m in RC_DATE_RE.finditer(content)]
    revisions: list[dict] = []
    if not date_positions:
        return revisions
    for i, (dstart, dend, date_str) in enumerate(date_positions):
        chunk_end = date_positions[i + 1][0] if i + 1 < len(date_positions) else len(content)
        chunk = content[dend:chunk_end]
        # Split chunk into <li>...</li>-ish rows. UseMod doesn't close <li>; each row
        # runs until the next <li>, </UL>, or end of chunk.
        for row in _split_rc_rows(chunk):
            entry = _parse_rc_row(row, date_str)
            if entry:
                revisions.append(entry)
    return revisions


def _split_rc_rows(chunk: str) -> list[str]:
    """Split a per-day chunk into per-<li> row strings."""
    rows = []
    lower = chunk.lower()
    idx = 0
    while True:
        li_pos = lower.find("<li>", idx)
        if li_pos == -1:
            break
        start = li_pos + 4
        # end at the next <li> or </UL>
        next_li = lower.find("<li>", start)
        next_ul = lower.find("</ul>", start)
        candidates = [p for p in (next_li, next_ul) if p != -1]
        end = min(candidates) if candidates else len(chunk)
        rows.append(chunk[start:end])
        idx = end
    return rows


def _parse_rc_row(row: str, date_str: str) -> dict | None:
    """Parse one RC row. Returns dict or None if row is not a revision entry.

    RC rows begin with `<a href="wiki.pl?action=...&id=X">(diff)</a>` (this
    anchor contains `&` and won't match RC_PAGE_RE, which only matches plain
    `wiki.pl?PageName` links) followed by `<a href="wiki.pl?PageName">PageName</a>`.
    We use the first anchor whose visible text is not `(diff)` as the page.
    """
    anchors = [a for a in RC_PAGE_RE.finditer(row) if a.group(2).strip() != "(diff)"]
    if not anchors:
        return None
    page_anchor = anchors[0]
    page_name = urllib.parse.unquote(page_anchor.group(1))
    # Time: try AM/PM first, then 24h.
    m_time = RC_TIME_AMPM_RE.search(row)
    hhmm = _hhmm_to_24h(m_time) if m_time else None
    if hhmm is None:
        m24 = RC_TIME_24H_RE.search(row)
        if m24:
            hhmm = f"{int(m24.group(1)):02d}:{int(m24.group(2)):02d}"
    # Summary bracket.
    m_sum = RC_SUMMARY_RE.search(row)
    summary = html.unescape(m_sum.group(1)) if m_sum else None
    is_new = bool(RC_NEW_RE.search(row))
    is_minor = bool(RC_MINOR_RE.search(row))
    # Label: everything after the page anchor and the time and (optional) summary,
    # after the ` . . . . . ` separator. We slice the row starting at the page-anchor
    # end so we don't accidentally treat the page anchor as the label.
    after_page = row[page_anchor.end():]
    label = None
    m_tail = RC_LABEL_TAIL_RE.search(after_page)
    if m_tail:
        label = _extract_label_from_tail(m_tail.group(1))
    if not label:
        # Fallback: strip tags and take last token.
        text = HTML_TAG_RE.sub("", after_page)
        text = html.unescape(text).strip()
        tokens = text.split()
        if tokens:
            label = tokens[-1]
    return {
        "date": date_str,
        "hhmm": hhmm,
        "page_name": page_name,
        "label": label,
        "change_summary": summary,
        "is_new_page": is_new,
        "is_minor_edit": is_minor,
    }


# --------------------------------------------------------------------- Diff parse

# Diff page has one or more `<strong>OP: A,Bc C,D</strong>` markers, followed
# by yellow (removed) and green (added) tables. Same as ProWiki, just with
# double-quoted attrs on this wiki.
DIFF_MARKER_RE = re.compile(
    r"<strong>(Added|Deleted|Changed):\s*([^<]+?)\s*</strong>", re.IGNORECASE
)
DIFF_YELLOW_RE = re.compile(
    r"<table[^>]*bgcolor=[\"']?#ffffaf[\"']?[^>]*><tr><td>(.*?)</td></tr></table>",
    re.DOTALL | re.IGNORECASE,
)
DIFF_GREEN_RE = re.compile(
    r"<table[^>]*bgcolor=[\"']?#cfffcf[\"']?[^>]*><tr><td>(.*?)</td></tr></table>",
    re.DOTALL | re.IGNORECASE,
)


def parse_diff(diff_html: str) -> dict:
    inner = extract_content_html(diff_html)
    markers = list(DIFF_MARKER_RE.finditer(inner))
    if not markers:
        no_prev = "no other diffs" in inner or "Difference" not in inner
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

# `Page generated September 4, 2026 8:13 pm` on any UseMod-upstream page.
PAGE_GENERATED_RE = re.compile(
    r"Page generated\s+([A-Za-z]+ \d{1,2}, \d{4})\s+(\d{1,2}):(\d{2})\s*([ap]m)",
    re.IGNORECASE,
)


def derive_tz_from_headers(page_html: str, http_date: str | None) -> str | None:
    """Compare the wiki's own `Page generated ...` wall clock against the HTTP
    Date header captured on the same response. Return an ISO offset like
    `-05:00` or `None` if either side is unparseable.

    The wiki does not declare its offset; this is the only reliable derivation.
    """
    if not http_date:
        return None
    m = PAGE_GENERATED_RE.search(page_html)
    if not m:
        return None
    try:
        date_part = m.group(1)  # "September 4, 2026"
        hh = int(m.group(2))
        mm = int(m.group(3))
        ap = m.group(4).lower()
        if ap == "am":
            hh = 0 if hh == 12 else hh
        else:
            hh = 12 if hh == 12 else hh + 12
        parts = date_part.replace(",", "").split()
        month, day, year = parts
        wiki_wall = dt.datetime(int(year), MONTHS[month], int(day), hh, mm, 0)
        # Parse RFC 2822 date from HTTP header; produces UTC datetime.
        http_dt = email_utils.parsedate_to_datetime(http_date)
        if http_dt is None:
            return None
        # If tz-aware, convert to UTC.
        if http_dt.tzinfo is not None:
            http_dt = http_dt.astimezone(dt.timezone.utc).replace(tzinfo=None)
        # offset = wiki_wall - http_utc (approximate, rounded to nearest 15 min).
        delta = wiki_wall - http_dt
        # Round to nearest 15 minutes.
        total_min = round(delta.total_seconds() / 60.0)
        # Snap to nearest 15.
        total_min = int(round(total_min / 15.0) * 15)
        sign = "+" if total_min >= 0 else "-"
        total_min = abs(total_min)
        oh = total_min // 60
        om = total_min % 60
        return f"{sign}{oh:02d}:{om:02d}"
    except (ValueError, KeyError):
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
    """Strip trailing /wiki.pl or /wiki.cgi from the base URL."""
    if base.endswith(".pl") or base.endswith(".cgi"):
        return base.rsplit("/", 1)[0]
    return base


# --------------------------------------------------------------------- Main scrape

def scrape(base: str, name: str, out: Path, days: int, sanity: bool,
           sleep: float = DEFAULT_SLEEP) -> None:
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    print(f"[{name}] fetching RC (days={days},all=1) ...", file=sys.stderr)
    rc_url = build_url(base, action="browse", id="RecentChanges", days=str(days), all="1")
    rc_html, _, rc_http_date = fetch(rc_url, sleep=sleep)
    revs = parse_rc(rc_html)
    print(f"[{name}]   RC parsed: {len(revs)} revision rows", file=sys.stderr)

    wiki_tz = derive_tz_from_headers(rc_html, rc_http_date)
    print(f"[{name}]   wiki TZ offset (derived): {wiki_tz or 'unknown'}", file=sys.stderr)

    # No RSS - populate the fields we can with `rc_wall` (or `rc_wall_naive`).
    for r in revs:
        r["rss"] = None
        r["revision_number"] = None
        r["time_iso"] = rc_datetime(r.get("date"), r.get("hhmm"), wiki_tz)
        r["time_source"] = "rc_wall" if wiki_tz else "rc_wall_naive"

    # Unique pages in order of first-seen (newest-first from RC).
    page_names: list[str] = []
    seen = set()
    for r in revs:
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
        body_html, _, _ = fetch(build_url(base, action="browse", id=pn), sleep=sleep)
        page_bodies[pn] = strip_content_to_text(extract_content_html(body_html))
        print(f"[{name}] page {pn}: diff ...", file=sys.stderr)
        diff_html, _, _ = fetch(build_url(base, action="browse", diff="1", id=pn), sleep=sleep)
        page_diffs[pn] = parse_diff(diff_html)

    if sanity:
        print("\n=== SANITY SUMMARY ===")
        print(f"  base: {base}")
        print(f"  days window: {days}")
        print(f"  wiki tz offset: {wiki_tz or 'unknown'}")
        print(f"  rc rows: {len(revs)}  unique pages: {len(seen)}")
        for r in revs[:8]:
            print(f"  rev: {r['page_name']}  time={r.get('time_iso')} label={r['label']!r} summary={r.get('change_summary')!r}")
        for pn, body in list(page_bodies.items())[:2]:
            print(f"\n--- {pn} head body ({len(body)} bytes) ---")
            print(body[:400])
        return

    # ---- Emit output ----
    out.mkdir(parents=True, exist_ok=True)
    build_output(name=name, out=out, base=base, days=days, started=started,
                 merged=revs, page_names=page_names,
                 page_bodies=page_bodies, page_diffs=page_diffs,
                 rc_html=rc_html, wiki_tz=wiki_tz)


def build_output(*, name: str, out: Path, base: str, days: int, started: str,
                 merged: list[dict], page_names: list[str],
                 page_bodies: dict[str, str], page_diffs: dict[str, dict],
                 rc_html: str, wiki_tz: str | None) -> None:
    # Chronological ascending. RC-only times can tie at the minute; sort stable
    # by RC's original reverse-chronological reading (revs are newest-first, so
    # we invert index to get earliest-first as a tiebreak).
    for idx, r in enumerate(merged):
        r["_rc_index"] = idx
    def sortable_time(r):
        return (r.get("time_iso") or "", -r["_rc_index"])
    merged_sorted = sorted(merged, key=sortable_time)

    seq_by_page: Counter[str] = Counter()
    revisions_out = []
    events_out = []
    # Head-per-page = latest chronological revision of that page.
    head_ids: dict[str, int] = {}
    for i, r in enumerate(merged_sorted):
        head_ids[r["page_name"]] = i  # last write wins.
    for i, r in enumerate(merged_sorted):
        pn = r["page_name"]
        seq_by_page[pn] += 1
        seq = seq_by_page[pn]
        is_head = (head_ids.get(pn) == i)
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
            "winning_clock": "recent_changes_wall",
            "uncertainty_seconds": 60,
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
            "wiki_revision_number": None,
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
        labels_seen = sorted({r["label"] for r in rows_for_page if r["label"]})
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
            "wiki_head_revision_number": None,
        })

    # ---- labels.jsonl ----
    labels_group: dict[str, list[dict]] = defaultdict(list)
    for r in merged_sorted:
        if r["label"] is None:
            continue
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
            "engine": "usemodwiki (upstream)",
            "scraper": "scrape/texteditors.py",
        },
        "cut": {
            "kind": "recent_changes_window",
            "days": days,
            "endpoint": build_url(base, action="browse", id="RecentChanges", days=str(days), all="1"),
        },
        "wiki_tz_offset": wiki_tz,
        "wiki_tz_derivation": "compared 'Page generated ...' wall clock to HTTP Date header",
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
            "Upstream UseModWiki has no RSS. `action=rss` returns "
            "'Invalid action parameter rss'. All revision times come from "
            "RecentChanges HTML wall clock, minute-precision only "
            "(uncertainty_seconds=60).",
            "`wiki_revision_number` and `wiki_head_revision_number` are always "
            "null on this export - the engine does not expose per-revision "
            "counters to the unauthenticated HTML/RC surface.",
            "Wiki timezone is not declared. It is derived by comparing the "
            "wiki's own 'Page generated ...' wall clock against the HTTP Date "
            "header on the same response, rounded to the nearest 15 minutes. "
            "If derivation fails, rows are `time_grade='rc_wall_naive'` and "
            "the ISO time has no offset suffix.",
            "Labels are the raw string printed after the ` . . . . . ` "
            "separator on RecentChanges. On this wiki that is usually a raw "
            "IPv4 or a reverse-DNS hostname (this is a public wiki with anon "
            "editing enabled and no obligatory nickname). A minority of labels "
            "are anchor-style handle names.",
            "Body is HTML-stripped rendered output, not raw wiki source. "
            "Wiki markup (WikiLinks, bold/italic, headings) is largely lost; "
            "raw URLs survive because they appear verbatim in the render.",
            "Bodies are only captured for the HEAD revision of each page. "
            "Non-head revisions in this cut have body=null "
            "(body_availability='metadata_only').",
            "The head-to-previous diff hunks ARE captured (revisions.jsonl.hunks "
            "for the head row) - but only that one diff, since action=log and "
            "action=archive are admin-gated on this engine.",
            "No IPs are exposed beyond what appears as a label. `ip16`, "
            "`n_ips`, `n_ip16` are all null - they exist for schema parity "
            "with prowiki, not because we have the data.",
            "n_revs_before is unknown - RecentChanges window is our only "
            "visibility into revision counts, and older revisions may exist "
            "that we can't see.",
        ],
        "endpoints_probed": {
            "recent_changes_html": build_url(base, action="browse", id="RecentChanges", days=str(days), all="1"),
            "rss_unavailable": build_url(base, action="rss"),
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
    p.add_argument("--base", required=True, help="Base URL, e.g. https://texteditors.org/cgi-bin/wiki.pl")
    p.add_argument("--name", required=True, help="Short wiki name, used in output IDs, e.g. 'texteditors'")
    p.add_argument("--out", type=Path, help="Output directory (default: agent-logs/<name>/)")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--sanity", action="store_true", help="Fetch minimum viable subset, print summary, don't write files")
    p.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Seconds between requests")
    args = p.parse_args()

    out = args.out or Path("agent-logs") / args.name
    scrape(args.base, args.name, out, args.days, args.sanity, args.sleep)


if __name__ == "__main__":
    main()
