#!/usr/bin/env python3
"""Scrape a UseModWiki 1.0 public wiki into agent-logs/<name>/ layout.

Adapted from `wikiservice_scrape.py` for the tmcleod.org/apchem wiki, which
runs upstream UseModWiki 1.0 (not the ProWiki fork). Compared to the ProWiki
scraper, this one:

  * has NO RSS to pull second-accurate timestamps from - `action=rss` returns
    "Invalid action parameter rss". Times come from RC wall clock (HH:MM
    am/pm, minute precision) only.
  * uses `action=edit&id=<Page>` to fetch raw wiki source (UseMod 1.0's edit
    textarea contains the source verbatim to any anon visitor). This is a
    strict upgrade over HTML-stripped rendered bodies.
  * uses `action=edit&id=<Page>&revision=N` for the one KeepFile-preserved
    old revision listed by `action=history` (UseMod stores one full historical
    revision per page in Keep, older bodies are pruned).
  * uses `action=history&id=<Page>` for editor IPs / registered handles; RC
    itself does NOT expose IPs on this engine.
  * derives the wiki's timezone offset by comparing the `from=<unix_ts>` link
    embedded in RC to the "starting from <Month D, YYYY H:MM am/pm>" caption
    next to it. Unlike ProWiki there is no in-band tz on any endpoint.

The output layout matches agent-logs/prowiki/ / agent-logs/milkwiki/. Fields
that don't exist on this engine (revision numbers for non-kept revs, IPs for
non-kept revs, second-accurate timestamps) are `null` and enumerated in
`manifest.limitations`.
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
DEFAULT_DAYS = 150
DEFAULT_SLEEP = 1.5


# --------------------------------------------------------------------- HTTP

def fetch(url: str, *, sleep: float = DEFAULT_SLEEP) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    time.sleep(sleep)
    for enc in ("utf-8", "iso-8859-1"):
        try:
            return raw.decode(enc), ctype
        except UnicodeDecodeError:
            continue
    return raw.decode("iso-8859-1", errors="replace"), ctype


# --------------------------------------------------------------------- HTML utils

# UseMod 1.0 does not wrap content in a table cell. The page body lives
# between the first <hr> (right after the H1 + nav row) and the last <hr>
# that precedes the footer form.
HR_RE = re.compile(r"<hr\s*/?>", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
ANCHOR_TEXT_RE = re.compile(r"<a\b[^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
P_RE = re.compile(r"<p\s*/?>|</p>", re.IGNORECASE)
MULTIBLANK_RE = re.compile(r"\n{3,}")


def extract_between_hrs(page_html: str) -> str:
    """Return the inner HTML between the first <hr> and the last <hr>."""
    hrs = list(HR_RE.finditer(page_html))
    if len(hrs) < 2:
        return ""
    return page_html[hrs[0].end():hrs[-1].start()]


def strip_content_to_text(inner_html: str) -> str:
    inner_html = ANCHOR_TEXT_RE.sub(lambda m: m.group(1), inner_html)
    inner_html = BR_RE.sub("\n", inner_html)
    inner_html = P_RE.sub("\n", inner_html)
    inner_html = HTML_TAG_RE.sub("", inner_html)
    text = html.unescape(inner_html)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = MULTIBLANK_RE.sub("\n\n", text).strip()
    return text


# --------------------------------------------------------------------- RecentChanges

# UseMod 1.0 RC row structure:
#   <p><strong>July 24, 2026</strong><p>
#   <UL>
#   <li><a href="wiki.cgi?action=browse&diff=1&id=Page">(diff)</a>  <a href="wiki.cgi?Page">Page</a> 9:16 pm  <strong>[summary]</strong> . . . . . <trailing>
#   ...
#   </UL>
# The <li> tags do NOT have closing </li>. Rows end at the next <li> or the </UL>.
# Attribute quotes are double. Times are 12-hour AM/PM.

RC_DATE_RE = re.compile(
    r"<p>\s*<strong>\s*([A-Za-z]+ \d{1,2}, \d{4})\s*</strong>\s*<p>", re.IGNORECASE
)
RC_UL_OPEN_RE = re.compile(r"<UL>", re.IGNORECASE)
RC_UL_CLOSE_RE = re.compile(r"</UL>", re.IGNORECASE)
# The FIRST anchor of a row is the "(diff)" link with `diff=` in the URL. The
# SECOND anchor is the page-name link (URL has just `?PageName`).
RC_DIFF_ANCHOR_RE = re.compile(
    r'<a\s+href="wiki\.cgi\?action=browse&diff=\d+&id=([^"]+)"[^>]*>\s*\(diff\)\s*</a>',
    re.IGNORECASE,
)
RC_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*(am|pm)\b", re.IGNORECASE)
RC_SUMMARY_RE = re.compile(r"<strong>\[([^\]]*)\]</strong>", re.IGNORECASE)
RC_NEW_RE = re.compile(r"<strong>NEW</strong>", re.IGNORECASE)
RC_MINOR_RE = re.compile(r"<em>Minor edit</em>", re.IGNORECASE)
# Trailing label: after ". . . . ." there is either nothing (anonymous),
# a plain-text handle/IP, or an <a href="wiki.cgi?Handle">Handle</a>.
RC_LABEL_ANCHOR_RE = re.compile(
    r'\.\s*\.\s*\.\s*\.\s*\.\s*<a\s+href="wiki\.cgi\?[^"]+"[^>]*>([^<]+)</a>',
    re.IGNORECASE,
)
RC_LABEL_TEXT_RE = re.compile(r"\.\s*\.\s*\.\s*\.\s*\.\s*([^<\n]+?)\s*$", re.IGNORECASE)

# The "starting from" caption pins wall-clock to a unix timestamp, letting us
# derive the wiki's tz offset. It looks like:
#   <a href="wiki.cgi?action=rc&from=1784942182">List new changes starting from</a> July 24, 2026 9:16 pm<br>
RC_FROM_RE = re.compile(
    r'<a\s+href="wiki\.cgi\?action=rc&from=(\d+)"[^>]*>[^<]*</a>\s*'
    r'([A-Za-z]+ \d{1,2}, \d{4})\s+(\d{1,2}):(\d{2})\s*(am|pm)',
    re.IGNORECASE,
)


def _split_ul_blocks(html_text: str) -> list[tuple[str, str]]:
    """Return [(date_str, ul_inner), ...] in document order.

    Every <UL>...</UL> block is preceded by a `<p><strong>Month D, YYYY</strong>`
    header. We pair them up.
    """
    out = []
    pos = 0
    while True:
        m_date = RC_DATE_RE.search(html_text, pos)
        if not m_date:
            break
        m_ul_open = RC_UL_OPEN_RE.search(html_text, m_date.end())
        if not m_ul_open:
            break
        m_ul_close = RC_UL_CLOSE_RE.search(html_text, m_ul_open.end())
        if not m_ul_close:
            break
        out.append((m_date.group(1), html_text[m_ul_open.end():m_ul_close.start()]))
        pos = m_ul_close.end()
    return out


def parse_rc(html_text: str) -> list[dict]:
    revisions: list[dict] = []
    for date_str, block in _split_ul_blocks(html_text):
        # Split the block on `<li>` starts. UseMod does not close <li>.
        rows = re.split(r"<li>", block, flags=re.IGNORECASE)
        for row in rows:
            row = row.strip()
            if not row:
                continue
            m_diff = RC_DIFF_ANCHOR_RE.search(row)
            if not m_diff:
                continue
            page_name = urllib.parse.unquote(m_diff.group(1))
            m_time = RC_TIME_RE.search(row)
            hhmm12 = None
            if m_time:
                hh = int(m_time.group(1))
                mm = int(m_time.group(2))
                ap = m_time.group(3).lower()
                if ap == "pm" and hh != 12:
                    hh += 12
                if ap == "am" and hh == 12:
                    hh = 0
                hhmm12 = f"{hh:02d}:{mm:02d}"
            m_sum = RC_SUMMARY_RE.search(row)
            summary = html.unescape(m_sum.group(1)) if m_sum else None
            is_new = bool(RC_NEW_RE.search(row))
            is_minor = bool(RC_MINOR_RE.search(row))
            # Label: try anchor form first, then plain-text trailing.
            label = None
            m_lab_a = RC_LABEL_ANCHOR_RE.search(row)
            if m_lab_a:
                label = html.unescape(m_lab_a.group(1)).strip()
            else:
                # Strip trailing whitespace/nbsp and look for plain-text handle.
                tail = row.rstrip()
                m_lab_t = RC_LABEL_TEXT_RE.search(tail)
                if m_lab_t:
                    cand = m_lab_t.group(1).strip()
                    # Anonymous rows have nothing after the dots, so this branch
                    # will not fire. If the row instead ends at the dots with
                    # only whitespace, `cand` will be empty.
                    if cand:
                        label = cand
            revisions.append({
                "date": date_str,
                "hhmm": hhmm12,
                "page_name": page_name,
                "label": label,
                "change_summary": summary,
                "is_new_page": is_new,
                "is_minor_edit": is_minor,
            })
    return revisions


def derive_tz_offset(rc_html: str) -> str | None:
    """The wiki's own tz offset, derived from RC's `from=<unix_ts>` caption.

    UseMod prints the `from` argument as a plain UTC unix timestamp AND renders
    the wall clock next to it in wiki-local time. Subtracting the two gives
    the offset. Returns e.g. "-04:00" or None if the caption is missing.
    """
    m = RC_FROM_RE.search(rc_html)
    if not m:
        return None
    unix_ts = int(m.group(1))
    utc = dt.datetime.fromtimestamp(unix_ts, tz=dt.timezone.utc)
    # Reconstruct wiki-local wall time from the caption.
    month, day, year = m.group(2).replace(",", "").split()
    if month not in MONTHS:
        return None
    hh = int(m.group(3))
    mm = int(m.group(4))
    if m.group(5).lower() == "pm" and hh != 12:
        hh += 12
    if m.group(5).lower() == "am" and hh == 12:
        hh = 0
    wall = dt.datetime(int(year), MONTHS[month], int(day), hh, mm, 0)
    # Snap to whole 15-minute offsets (real tz).
    delta_min = (wall - utc.replace(tzinfo=None)).total_seconds() / 60.0
    off = round(delta_min / 15.0) * 15
    sign = "+" if off >= 0 else "-"
    a = abs(int(off))
    return f"{sign}{a // 60:02d}:{a % 60:02d}"


# --------------------------------------------------------------------- History

# `action=history` lists ONLY the head revision and any KeepFile-preserved old
# revision (usually 1 per page). Row form:
#   Revision 11: <a href="wiki.cgi?Page">View</a> Diff . . July 7, 2026 3:12 pm by 4.227.3.xxx <b>[summary]</b> <br>
# and for older kept:
#   Revision 10: <a href="wiki.cgi?action=browse&id=Page&revision=10">View</a> <a href="wiki.cgi?...diffrevision=10">Diff</a> . . July 7, 2026 3:07 pm by 20.245.136.xxx <b>[markerproxy]</b> <br>
# The `by` field can be a plain-text IP (like `4.227.3.xxx`) or an anchor
# (like `<a href="wiki.cgi?ap2005" title="ID 111 from ap2005">ap2005</a>`).

HISTORY_ROW_RE = re.compile(
    r"Revision\s+(\d+):\s*(.*?)(?=Revision\s+\d+:|<hr|<form)",
    re.DOTALL | re.IGNORECASE,
)
HISTORY_TIME_RE = re.compile(
    r"([A-Za-z]+ \d{1,2}, \d{4})\s+(\d{1,2}):(\d{2})\s*(am|pm)",
    re.IGNORECASE,
)
HISTORY_BY_ANCHOR_RE = re.compile(
    r'by\s*<a\s+href="wiki\.cgi\?[^"]+"[^>]*>([^<]+)</a>',
    re.IGNORECASE,
)
HISTORY_BY_TEXT_RE = re.compile(r"by\s+([^\s<]+)", re.IGNORECASE)
HISTORY_SUMMARY_RE = re.compile(r"<b>\[([^\]]*)\]</b>", re.IGNORECASE)


def parse_history(html_text: str) -> list[dict]:
    out = []
    for m in HISTORY_ROW_RE.finditer(html_text):
        rev = int(m.group(1))
        row = m.group(2)
        m_time = HISTORY_TIME_RE.search(row)
        hhmm = None
        date_str = None
        if m_time:
            date_str = m_time.group(1)
            hh = int(m_time.group(2))
            mm = int(m_time.group(3))
            if m_time.group(4).lower() == "pm" and hh != 12:
                hh += 12
            if m_time.group(4).lower() == "am" and hh == 12:
                hh = 0
            hhmm = f"{hh:02d}:{mm:02d}"
        label = None
        m_by_a = HISTORY_BY_ANCHOR_RE.search(row)
        if m_by_a:
            label = html.unescape(m_by_a.group(1)).strip()
        else:
            m_by_t = HISTORY_BY_TEXT_RE.search(row)
            if m_by_t:
                label = m_by_t.group(1).strip()
        m_sum = HISTORY_SUMMARY_RE.search(row)
        summary = html.unescape(m_sum.group(1)) if m_sum else None
        # Determine if this is the head row (Diff-only) or an old kept row
        # (has "revision=N" in a View link).
        is_head = "revision=" not in row.lower()
        out.append({
            "revision": rev,
            "date": date_str,
            "hhmm": hhmm,
            "label": label,
            "change_summary": summary,
            "is_head": is_head,
        })
    return out


# --------------------------------------------------------------------- Raw source (edit textarea)

EDIT_TEXTAREA_RE = re.compile(
    r'<textarea\s+name="text"[^>]*>(.*?)</textarea>',
    re.DOTALL | re.IGNORECASE,
)


def parse_edit_source(html_text: str) -> str | None:
    m = EDIT_TEXTAREA_RE.search(html_text)
    if not m:
        return None
    return html.unescape(m.group(1))


# --------------------------------------------------------------------- Diff parse

DIFF_MARKER_RE = re.compile(
    r"<strong>(Added|Deleted|Removed|Changed):\s*([^<]+?)\s*</strong>", re.IGNORECASE
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
    inner = extract_between_hrs(diff_html)
    markers = list(DIFF_MARKER_RE.finditer(inner))
    if not markers:
        no_prev = "no other diffs" in inner.lower() or "Difference" not in inner
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


# --------------------------------------------------------------------- URL

def build_url(base: str, **params) -> str:
    q = urllib.parse.urlencode(params, safe="")
    return f"{base}?{q}"


# --------------------------------------------------------------------- Merge RC + history

def merge_rc_history(rc_rows: list[dict], history_by_page: dict[str, list[dict]],
                     tz_offset: str | None) -> list[dict]:
    """Match RC rows against per-page history rows on (date, hhmm) to pick up
    IPs / registered handles + engine revision numbers for the (usually two)
    KeepFile-listed revisions per page. RC rows that don't align get their
    RC-derived label kept and revision_number stays None.
    """
    # Index history rows by (page_name, date, hhmm)
    hist_by_key: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for pn, rows in history_by_page.items():
        for h in rows:
            key = (pn, h.get("date") or "", h.get("hhmm") or "")
            if key[1] and key[2]:
                hist_by_key[key].append(h)

    merged = []
    for entry in rc_rows:
        pn = entry["page_name"]
        key = (pn, entry.get("date") or "", entry.get("hhmm") or "")
        candidates = hist_by_key.get(key) or []
        hist_match = candidates.pop(0) if candidates else None
        # If the history label is present and RC label was None, adopt history's.
        # If both are present, prefer history's (has IPs).
        if hist_match and hist_match.get("label"):
            entry["label"] = hist_match["label"]
            entry["label_source"] = "history"
        else:
            entry["label_source"] = "rc" if entry.get("label") else "none"
        entry["revision_number"] = hist_match["revision"] if hist_match else None
        entry["kept_in_history"] = hist_match is not None
        entry["time_iso"] = rc_datetime(entry.get("date"), entry.get("hhmm"), tz_offset)
        entry["time_source"] = "rc_wall" if tz_offset else "rc_wall_naive"
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

    wiki_tz = derive_tz_offset(rc_html)
    print(f"[{name}]   wiki TZ offset: {wiki_tz or 'unknown'}", file=sys.stderr)

    # Unique pages in RC order
    page_names: list[str] = []
    seen: set[str] = set()
    for r in revs:
        if r["page_name"] not in seen:
            page_names.append(r["page_name"])
            seen.add(r["page_name"])
    print(f"[{name}]   {len(page_names)} unique pages", file=sys.stderr)

    if sanity:
        page_names = page_names[:2]
        print(f"[{name}] SANITY: limiting to {len(page_names)} pages", file=sys.stderr)

    # Fetch history for each page.
    history_by_page: dict[str, list[dict]] = {}
    for pn in page_names:
        print(f"[{name}] page {pn}: history ...", file=sys.stderr)
        hist_html, _ = fetch(build_url(base, action="history", id=pn), sleep=sleep)
        history_by_page[pn] = parse_history(hist_html)

    merged = merge_rc_history(revs, history_by_page, wiki_tz)

    # For sanity, drop revs whose page didn't get history fetched.
    if sanity:
        merged = [r for r in merged if r["page_name"] in set(page_names)]

    # Head body: raw source via action=edit&id=<Page>.
    # Old kept revision body: raw source via action=edit&id=<Page>&revision=N,
    # where N is the non-head revision listed by action=history.
    page_bodies_head: dict[str, str] = {}
    page_bodies_old: dict[tuple[str, int], str] = {}
    page_diffs: dict[str, dict] = {}
    for pn in page_names:
        print(f"[{name}] page {pn}: head raw source ...", file=sys.stderr)
        edit_html, _ = fetch(build_url(base, action="edit", id=pn), sleep=sleep)
        body = parse_edit_source(edit_html)
        page_bodies_head[pn] = body if body is not None else ""
        # Kept-old body per page (usually one).
        for h in history_by_page[pn]:
            if not h.get("is_head"):
                rev = h["revision"]
                print(f"[{name}] page {pn}: old rev {rev} raw source ...", file=sys.stderr)
                edit_html, _ = fetch(build_url(base, action="edit", id=pn, revision=str(rev)), sleep=sleep)
                obody = parse_edit_source(edit_html)
                if obody is not None:
                    page_bodies_old[(pn, rev)] = obody
        # Head-to-previous diff (same call the RC (diff) link uses).
        print(f"[{name}] page {pn}: head diff ...", file=sys.stderr)
        diff_html, _ = fetch(build_url(base, action="browse", diff="1", id=pn), sleep=sleep)
        page_diffs[pn] = parse_diff(diff_html)

    if sanity:
        print("\n=== SANITY SUMMARY ===")
        print(f"  base: {base}")
        print(f"  days window: {days}")
        print(f"  wiki tz offset: {wiki_tz or 'unknown'}")
        print(f"  rc rows: {len(revs)}  unique pages: {len(seen)}")
        for r in merged[:5]:
            print(f"  rev: {r['page_name']}  time={r.get('time_iso')} label={r['label']!r} "
                  f"summary={r.get('change_summary')!r} rev#={r.get('revision_number')} src={r['label_source']}")
        for pn, body in list(page_bodies_head.items())[:2]:
            print(f"\n--- {pn} head raw ({len(body)} bytes) ---")
            print(body[:400])
        for (pn, rev), body in list(page_bodies_old.items())[:2]:
            print(f"\n--- {pn}@rev{rev} raw ({len(body)} bytes) ---")
            print(body[:400])
        return

    out.mkdir(parents=True, exist_ok=True)
    build_output(name=name, out=out, base=base, days=days, started=started,
                 merged=merged, page_names=page_names,
                 page_bodies_head=page_bodies_head, page_bodies_old=page_bodies_old,
                 page_diffs=page_diffs, wiki_tz=wiki_tz,
                 history_by_page=history_by_page)


def build_output(*, name: str, out: Path, base: str, days: int, started: str,
                 merged: list[dict], page_names: list[str],
                 page_bodies_head: dict[str, str],
                 page_bodies_old: dict[tuple[str, int], str],
                 page_diffs: dict[str, dict], wiki_tz: str | None,
                 history_by_page: dict[str, list[dict]]) -> None:
    # Chronological ascending
    def sortable_time(r):
        return r.get("time_iso") or ""
    merged_sorted = sorted(merged, key=sortable_time)

    seq_by_page: Counter[str] = Counter()
    revisions_out = []
    events_out = []
    # Precompute the highest revision number seen per page (from history) so
    # we can flag the head vs. an old KeepFile revision.
    head_rev_by_page: dict[str, int | None] = {}
    for pn in page_names:
        heads = [h["revision"] for h in history_by_page[pn] if h.get("is_head")]
        head_rev_by_page[pn] = max(heads) if heads else None

    for r in merged_sorted:
        pn = r["page_name"]
        seq_by_page[pn] += 1
        seq = seq_by_page[pn]
        # Is this THE head revision in chronological order?
        is_head = (r is next((x for x in reversed(merged_sorted) if x["page_name"] == pn), None))
        # Body attach: head gets head raw source; kept-old rows (revision
        # numbers matching a KeepFile-preserved rev) get old raw source.
        body: str | None = None
        body_availability = "metadata_only"
        rev_num = r.get("revision_number")
        if is_head:
            body = page_bodies_head.get(pn)
            body_availability = "head_only" if body is not None else "metadata_only"
        elif rev_num is not None and (pn, rev_num) in page_bodies_old:
            body = page_bodies_old[(pn, rev_num)]
            body_availability = "kept_old"
        body_bytes = body.encode("utf-8") if body is not None else None
        body_sha = hashlib.sha256(body_bytes).hexdigest() if body_bytes is not None else None
        diff = page_diffs.get(pn) if is_head else None
        rev_id = f"{name}~{pn}@{seq}"
        page_id = f"{name}/{pn}"
        page_key = f"{name}~{pn}"
        label = r.get("label")
        # Detect IP16 (first two octets) for labels that are IPv4 addresses,
        # accepting UseMod's "x.x.x.xxx" redaction of the last octet.
        ip16 = None
        if label and re.match(r"^\d{1,3}\.\d{1,3}\.", label):
            parts = label.split(".")
            if len(parts) >= 2:
                ip16 = f"{parts[0]}.{parts[1]}"
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
            "label": label,
            "ip16": ip16,
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
            "body_encoding": "wiki_source_utf8" if body is not None else None,
            "wiki_revision_number": rev_num,
            "is_new_page": r.get("is_new_page"),
            "is_minor_edit": r.get("is_minor_edit"),
            "body_availability": body_availability,
            "label_source": r.get("label_source"),
        })
        events_out.append({
            "event_id": f"save:{rev_id}",
            "event_type": "save",
            "time": r.get("time_iso"),
            "time_grade": r.get("time_source"),
            "wiki": name,
            "revision_ref": rev_id,
        })

    # pages.jsonl
    pages_out = []
    for pn in sorted({r["page_name"] for r in merged_sorted}):
        rows_for_page = [r for r in merged_sorted if r["page_name"] == pn]
        head_row = rows_for_page[-1]
        head_body = page_bodies_head.get(pn) or ""
        labels_seen = sorted({r["label"] for r in rows_for_page if r.get("label")})
        ips_seen = sorted({r["label"] for r in rows_for_page
                           if r.get("label") and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.", r["label"])})
        ip16_seen = sorted({".".join(ip.split(".")[:2]) for ip in ips_seen})
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
            "last_write": head_row.get("time_iso"),
            "body_bytes": len(head_body.encode("utf-8")),
            "deleted_live": False,
            "live_body_variant": "wiki_source",
            "head_differs_from_live": False,
            "n_deletions": 0,
            "n_recreations": 0,
            "labels": labels_seen,
            "n_labels": len(labels_seen),
            "n_ips": len(ips_seen) if ips_seen else None,
            "n_ip16": len(ip16_seen) if ip16_seen else None,
            "wiki_head_revision_number": head_rev_by_page.get(pn),
        })

    # labels.jsonl
    labels_group: dict[str, list[dict]] = defaultdict(list)
    for r in merged_sorted:
        if r.get("label"):
            labels_group[r["label"]].append(r)
    labels_out = []
    for label in sorted(labels_group):
        rows = labels_group[label]
        pages = sorted({f"{name}/{r['page_name']}" for r in rows})
        is_ip = bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.", label))
        ip16 = ".".join(label.split(".")[:2]) if is_ip else None
        labels_out.append({
            "label": label,
            "stored_revisions": len(rows),
            "first_write": rows[0].get("time_iso"),
            "last_write": rows[-1].get("time_iso"),
            "stored_revision_ips": [label] if is_ip else None,
            "stored_revision_ip16": [ip16] if ip16 else None,
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
            "engine": "UseModWiki 1.0 (upstream)",
            "scraper": "scrape/apchem.py",
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
            "No RSS on this engine: action=rss returns \"Invalid action parameter rss\". "
            "All timestamps are RC wall clock (minute precision) with the wiki's declared "
            "tz offset applied. uncertainty_seconds=60 on every row.",
            "wiki_revision_number is only populated for revisions that appear in "
            "action=history (typically the head + one KeepFile-preserved old revision "
            "per page). Older revisions in the RC window have revision_number=null.",
            "Editor labels (IPs / handles) are only exposed by action=history. Revisions "
            "not listed by history have label=null unless the row also carries a plain-text "
            "trailing handle in the RC HTML.",
            "IPs are redacted by the engine to the first three octets (last octet is "
            "\"xxx\"). n_ips / n_ip16 count these redacted forms.",
            "Bodies: HEAD revision has its raw wiki source captured via action=edit "
            "(body_availability=\"head_only\"). KeepFile-preserved old revisions get "
            "their raw source via action=edit&revision=N (body_availability=\"kept_old\"). "
            "All other in-window revisions have body=null (body_availability=\"metadata_only\").",
            "Only the head-to-previous diff is captured (revisions.jsonl.hunks on the "
            "chronologically-last revision of each page).",
            "n_revs_before is unknown - the RC window is our only visibility into "
            "revision counts, and older revisions may exist that we can't see.",
        ],
        "endpoints_probed": {
            "recent_changes_html": build_url(base, action="browse", id="RecentChanges", days=str(days), all="1"),
            "recent_changes_rss": build_url(base, action="rss") + "  (returns \"Invalid action parameter rss\")",
            "history_per_page": build_url(base, action="history", id="<page>"),
            "raw_source_head": build_url(base, action="edit", id="<page>"),
            "raw_source_old": build_url(base, action="edit", id="<page>", revision="<N>"),
            "head_diff": build_url(base, action="browse", diff="1", id="<page>"),
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
    p.add_argument("--base", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--out", type=Path)
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--sanity", action="store_true")
    p.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)
    args = p.parse_args()

    out = args.out or Path("agent-logs") / args.name
    scrape(args.base, args.name, out, args.days, args.sanity, args.sleep)


if __name__ == "__main__":
    main()
