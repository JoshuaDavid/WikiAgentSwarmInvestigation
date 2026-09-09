#!/usr/bin/env python3
"""Wayback-based scrape of https://url.popcat.xyz (Zero Two URL shortener).

The `url.popcat.xyz` service is one of the compromised URL-shortener endpoints
in the incident: agents used it to shorten data-fetch URLs (max.gov SF133
attachments, httpbin base64 CBS packs, projectarclight queries, ...) and, in
at least two cases, a ChatGPT conversation URL.

The site has a public paginated listing at `?page=N` (50 entries per page)
and a per-code info page at `/<code>/info` (destination + click count +
created date + days active). Neither endpoint is scraped by shellac.

Two-stage pipeline:

1. Fetch Wayback snapshots of the top listing pages for a target date. Parse
   each `<tr>` for (short_code, destination, clicks). Filter for
   "OpenAI-related" candidates: destination is a ChatGPT/OpenAI URL, or the
   short_code starts with `oai`/`OAI`. This filter is deterministic — no
   subagent classification is needed because the naming convention alone
   selects a swarm-authored subset.

2. For each surviving short_code, query CDX for a `/<code>/info` capture,
   fetch the earliest archived HTML with `id_`, and parse the
   `Redirects to:`, `Total Views`, `Days Active`, and `Created:` fields.

Considerate throttling: 2s between listing fetches, 2.5s between /info
fetches, exponential backoff on Wayback rate-limit errors.

Outputs go to `scrape/outputs/popcat-wayback/` (not `agent-logs/`) because a
downstream extract step writes the final `agent-logs/popcat-wayback/`
export. See `analyses/popcat-wayback-openai-extract/`.

Usage:
    python3 scrape/popcat_wayback.py                    # full run
    python3 scrape/popcat_wayback.py --sanity           # 2 listing pages, 3 info pages
    python3 scrape/popcat_wayback.py --pages 1-9        # custom listing range
    python3 scrape/popcat_wayback.py --date 20260908    # target listing date
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

BASE_LIVE = "https://url.popcat.xyz"
WB_CDX = "https://web.archive.org/cdx/search/cdx"
WB_ID = "https://web.archive.org/web"  # append `{ts}id_/{orig_url}`
USER_AGENT = (
    "Automation (investigating OpenAI agent swarm; "
    "contact swarmchasers discord https://discord.gg/RVUnKefG7 / "
    "joshuad93@gmail.com for more info)"
)
LISTING_SLEEP = 2.0
INFO_SLEEP = 2.5
CDX_SLEEP = 1.2

OUT_DIR = Path(__file__).resolve().parent / "outputs" / "popcat-wayback"
LISTING_DIR = OUT_DIR / "listing"
INFO_DIR = OUT_DIR / "info_pages"

# Deterministic filter for "OpenAI-related" entries.
OAI_CODE_RE = re.compile(r"^(?:oai|OAI|Oai)")
OAI_DEST_RE = re.compile(
    r"(chat\.openai\.com|chatgpt\.com|openai\.com|api\.openai|platform\.openai)", re.I
)

# Wayback listing row parser (Zero Two shortener template).
ROW_RE = re.compile(
    r'href="([^"]+)"\s*>\s*([^<]+?)\s*</a>\s*</th>\s*'
    r'<td[^>]*>\s*<a id="short"[^>]*href="/([^/]+)/info"[^>]*>\s*(\S+)\s*</a>\s*</td>\s*'
    r'<td[^>]*>\s*(\d+)\s*</td>',
    re.S,
)

# /info page field parsers.
INFO_REDIRECT_RE = re.compile(r"Redirects to:\s*(https?://\S+)", re.S)
INFO_VIEWS_RE = re.compile(r"(\d+)\s*Total Views", re.S)
INFO_DAYS_RE = re.compile(r"(\d+)\s*Days Active", re.S)
INFO_CREATED_RE = re.compile(r"Created:\s*(\d{1,2}/\d{1,2}/\d{2,4})", re.S)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def curl_json(url: str, timeout: int = 45, retries: int = 5) -> list | None:
    """Fetch a JSON URL via curl. Retry with backoff. Return None on total failure."""
    for attempt in range(retries):
        try:
            out = subprocess.check_output(
                ["curl", "-sf", "--compressed", "-A", USER_AGENT,
                 "--connect-timeout", "15", "--max-time", str(timeout), url],
                timeout=timeout + 10,
            ).decode()
            return json.loads(out) if out.strip() else []
        except Exception:
            time.sleep((attempt + 1) * 3)
    return None


def curl_download(url: str, out_path: Path, retries: int = 5) -> bool:
    for attempt in range(retries):
        try:
            subprocess.check_call(
                ["curl", "-sf", "--compressed", "-A", USER_AGENT,
                 "--connect-timeout", "15", "--max-time", "60",
                 "-o", str(out_path), url],
                timeout=90,
            )
            if out_path.exists() and out_path.stat().st_size > 500:
                return True
        except Exception:
            pass
        time.sleep((attempt + 1) * 4)
    return False


# ---------- stage 1: listing pages ----------


def cdx_listing_capture(page: int, date: str) -> str | None:
    """Return Wayback timestamp for `?page=N` on `date` (YYYYMMDD), or None."""
    url = (
        f"{WB_CDX}?url=url.popcat.xyz/%3Fpage={page}"
        f"&from={date}&to={date}&output=json&limit=1"
    )
    data = curl_json(url)
    if data and len(data) > 1:
        return data[1][1]
    return None


def fetch_listing_page(page: int, ts: str, out: Path) -> bool:
    url = f"{WB_ID}/{ts}id_/{BASE_LIVE}/?page={page}"
    return curl_download(url, out)


def parse_listing(html: str, page: int) -> list[dict]:
    rows = []
    for full_url, _text, code, code_text, clicks in ROW_RE.findall(html):
        rows.append({
            "page": page,
            "short_code": code,
            "destination": full_url.strip(),
            "clicks": int(clicks),
        })
    return rows


def openai_filter(row: dict) -> bool:
    return bool(OAI_CODE_RE.match(row["short_code"])) or bool(
        OAI_DEST_RE.search(row["destination"])
    )


def flag_row(row: dict) -> dict:
    r = dict(row)
    r["flag_openai_destination"] = bool(OAI_DEST_RE.search(row["destination"]))
    r["flag_oai_prefix_code"] = bool(OAI_CODE_RE.match(row["short_code"]))
    return r


# ---------- stage 2: /info pages ----------


def cdx_info_capture(code: str) -> tuple[str | None, str | None]:
    """Return (timestamp, original_url) for the earliest `/info` capture."""
    url = f"{WB_CDX}?url=url.popcat.xyz/{code}/info&output=json&limit=5"
    data = curl_json(url)
    if not data or len(data) <= 1:
        return None, None
    row = data[1]
    return row[1], row[2]


def fetch_info_page(code: str, ts: str, out: Path) -> bool:
    url = f"{WB_ID}/{ts}id_/{BASE_LIVE}/{code}/info"
    return curl_download(url, out)


def parse_info(html: str) -> dict:
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    m_r = INFO_REDIRECT_RE.search(txt)
    m_v = INFO_VIEWS_RE.search(txt)
    m_d = INFO_DAYS_RE.search(txt)
    m_c = INFO_CREATED_RE.search(txt)
    return {
        "redirects_to": m_r.group(1) if m_r else None,
        "total_views": int(m_v.group(1)) if m_v else None,
        "days_active": int(m_d.group(1)) if m_d else None,
        "created": m_c.group(1) if m_c else None,
    }


# ---------- driver ----------


def run(date: str, pages: list[int], sanity: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LISTING_DIR.mkdir(parents=True, exist_ok=True)
    INFO_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[{utc_now()}] listing pass: date={date} pages={pages} sanity={sanity}",
          file=sys.stderr)

    listing_rows: list[dict] = []
    listing_meta = {}
    for page in pages:
        ts = cdx_listing_capture(page, date)
        listing_meta[page] = ts
        if not ts:
            print(f"  page={page} NO_CAPTURE on {date}", file=sys.stderr)
            time.sleep(CDX_SLEEP)
            continue
        out = LISTING_DIR / f"page{page}.html"
        if not (out.exists() and out.stat().st_size > 500):
            if not fetch_listing_page(page, ts, out):
                print(f"  page={page} ts={ts} FETCH_FAIL", file=sys.stderr)
                time.sleep(LISTING_SLEEP)
                continue
            time.sleep(LISTING_SLEEP)
        rows = parse_listing(out.read_text(encoding="utf-8", errors="replace"), page)
        listing_rows.extend(rows)
        print(f"  page={page} ts={ts} rows={len(rows)}", file=sys.stderr)

    (OUT_DIR / "listing_rows.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in listing_rows), encoding="utf-8"
    )

    # Deterministic OpenAI filter.
    openai_rows = [flag_row(r) for r in listing_rows if openai_filter(r)]
    # Dedup by short_code (listing pagination duplicates a few).
    seen: dict[str, dict] = {}
    for r in openai_rows:
        seen.setdefault(r["short_code"], r)
    openai_rows = sorted(seen.values(), key=lambda r: r["short_code"])
    (OUT_DIR / "openai_rows.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in openai_rows), encoding="utf-8"
    )
    print(f"[{utc_now()}] listing done: {len(listing_rows)} raw rows, "
          f"{len(openai_rows)} OpenAI-flagged (unique codes)", file=sys.stderr)

    if sanity:
        openai_rows = openai_rows[:3]
        print(f"[sanity] truncating info pass to {len(openai_rows)} codes",
              file=sys.stderr)

    # Info pass.
    print(f"[{utc_now()}] info pass: {len(openai_rows)} codes", file=sys.stderr)
    cdx_records: list[dict] = []
    parsed: list[dict] = []
    for i, r in enumerate(openai_rows, 1):
        code = r["short_code"]
        ts, orig = cdx_info_capture(code)
        cdx_records.append({"short_code": code, "timestamp": ts, "original": orig})
        time.sleep(CDX_SLEEP)
        if not ts:
            print(f"  [{i:3d}/{len(openai_rows)}] MISS {code}", file=sys.stderr)
            continue
        out = INFO_DIR / f"{code}.html"
        if not (out.exists() and out.stat().st_size > 500):
            if not fetch_info_page(code, ts, out):
                print(f"  [{i:3d}/{len(openai_rows)}] FETCH_FAIL {code}",
                      file=sys.stderr)
                time.sleep(INFO_SLEEP)
                continue
            time.sleep(INFO_SLEEP)
        fields = parse_info(out.read_text(encoding="utf-8", errors="replace"))
        parsed.append({
            "short_code": code,
            "wayback_timestamp": ts,
            "wayback_url": f"{WB_ID}/{ts}id_/{BASE_LIVE}/{code}/info",
            **fields,
        })
        if i % 20 == 0 or i < 3:
            print(f"  [{i:3d}/{len(openai_rows)}] OK {code} -> "
                  f"views={fields['total_views']} created={fields['created']}",
                  file=sys.stderr)

    (OUT_DIR / "info_cdx.jsonl").write_text(
        "".join(json.dumps(r) + "\n"
                for r in sorted(cdx_records, key=lambda x: x["short_code"])),
        encoding="utf-8",
    )
    (OUT_DIR / "info_parsed.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in parsed), encoding="utf-8"
    )

    missing = [r["short_code"] for r in cdx_records if not r["timestamp"]]
    (OUT_DIR / "info_missing.txt").write_text(
        f"# {len(missing)} of {len(openai_rows)} codes have no Wayback /info "
        f"capture. Live fetch on {BASE_LIVE} would be needed.\n"
        + "\n".join(missing) + ("\n" if missing else ""),
        encoding="utf-8",
    )

    # Manifest.
    manifest = {
        "generated_at": utc_now(),
        "source": {
            "site": BASE_LIVE,
            "engine": "Zero Two URL shortener (compromised endpoint — see incident)",
            "wayback_listing_date": date,
            "listing_pages": pages,
        },
        "counts": {
            "listing_rows": len(listing_rows),
            "openai_flagged_codes": len(openai_rows),
            "info_captures_found": sum(1 for r in cdx_records if r["timestamp"]),
            "info_captures_missing": len(missing),
            "info_parsed": len(parsed),
        },
        "listing_captures": listing_meta,
        "filter": {
            "openai_code_regex": OAI_CODE_RE.pattern,
            "openai_dest_regex": OAI_DEST_RE.pattern,
            "kind": "deterministic (no subagent classifier)",
        },
        "throttling": {
            "listing_sleep_s": LISTING_SLEEP,
            "info_sleep_s": INFO_SLEEP,
            "cdx_sleep_s": CDX_SLEEP,
        },
        "user_agent": USER_AGENT,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                            encoding="utf-8")

    print(f"[{utc_now()}] done: {len(parsed)} parsed, {len(missing)} missing",
          file=sys.stderr)


def parse_pages(spec: str) -> list[int]:
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",") if x.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default="20260908",
                    help="Wayback capture date for the listing (YYYYMMDD)")
    ap.add_argument("--pages", default="1-9",
                    help="Listing page range/list (e.g. '1-9' or '1,3,5')")
    ap.add_argument("--sanity", action="store_true",
                    help="Fetch listing, then only 3 /info pages")
    args = ap.parse_args()

    run(args.date, parse_pages(args.pages), args.sanity)


if __name__ == "__main__":
    main()
