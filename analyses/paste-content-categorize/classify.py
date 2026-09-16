#!/usr/bin/env python3
"""Classify obviously agent-authored pastes on paste-linuxiarz and pastebin-k4be.

Input:  agent-logs/pastes-(linuxiarz|k4be)/revisions.jsonl
Filter: body_availability == 'full_source' and verdict != 'unclear'
        (i.e. shellac-imported swarm pastes plus subagent-verdict swarm pastes)
Output: outputs/classified.jsonl (one row per paste with 'category' added)
        outputs/counts.json      (fraction per category, per site, and total)

Categories (mutually exclusive; first match wins):

1. test   - paste is probing the paste-site plumbing (URL rendering, title
            visibility, reply cadence, index freshness, POST vs GET, syntax
            highlighter round-trip, PadBot ping sequences, hello-world posts)
2. links  - paste is a saved bundle of URLs that the swarm reuses elsewhere
            (Iowa data cache shortlinks, ReferenceLinks lists, cross-wiki
            pointer dumps)
3. info   - paste is a table or stats dump (EPL relegation tables, thyroid
            cancer rate matrices, Roi Et time series, Humana 10-K prices)
4. other  - coordination messages (IowaCollabReply, deadline pings), code
            dumps, grok4 hoax pastes, recruiter messages, everything else
"""

import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    ROOT / "agent-logs" / "pastebin-k4be" / "revisions.jsonl",
    ROOT / "agent-logs" / "paste-linuxiarz" / "revisions.jsonl",
]
OUT_DIR = Path(__file__).resolve().parent / "outputs"


# ---------- test detection ----------

# Strong signals that a paste is a plumbing test, not a coordination or data
# paste. Ordered from most specific to most general.

TEST_TITLE_PATTERNS = [
    re.compile(p) for p in [
        # Explicit self-labelled tests
        r"^test\b", r"\btest\b.*(ignore|probe|only|post|noop)",
        r"IowaTestIgnore", r"TestNoPost", r"IowaPostTest", r"DirectPostProbe",
        r"IowaDataTest", r"ANCHORTEST", r"AATEST", r"HTMLTEST",
        # Paste-site plumbing probes
        r"^(TK|TEL|GO|GOR|PAD|PAD\d)\d*",       # protocol-suffixed test channels
        r"URLTEST", r"REPLYURL", r"CiteTest",
        r"BROWSERPOSTTEST",
        # G<lang>99 syntax-highlighter round-trip probes
        r"^G(html|xml|bbcode|markdown|url|latex|php|javascript|robots|html4strict)\d*",
        r"^linktry", r"^Test\d*$", r"^EPL\d+test$",
        r"TITLE\d*$", r"^TITLEZ$",  # title-field probes
        r"^apitest$", r"^Research$",
    ]
]

TEST_LABEL_TOKENS = {
    "test", "tester", "agent-test", "PadBot", "TEL", "ZZ", "CiteTest",
    "NAME", "tester", "Corrupt Mocking",  # 'hello from test' anon poster
}

# Body idioms that scream "probe"
TEST_BODY_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"^pad-\d+\.\d+-\d+\s*$",                    # PadBot ping
        r"^hello[\s\-]?(from|paste|api|test|world)?\b",
        r"^hello-\d",                                 # hello-<ts> probe
        r"^hello\d+\s*$",                             # hello0014 style
        r"^x\s*$", r"^AAA\s*$", r"^RAND[Z0-9]",       # single-char/tag noise
        r"BROWSERPOSTTEST", r"TESTNONE", r"INJECTTEXT",
        r"FRAMEK4\d", r"GOLINK\d", r"LINKCONTENTTEST",
        r"^coordpost-\d", r"^direct-post-test-\d",
        r"^test-post-from-",
        r"CLICKMAYBE",                                # TEL telegraph pings
        r"^Test\w*\b", r"TestHelloABC",
    ]
]


def is_test(row):
    body = row.get("body") or ""
    title = row.get("source_title") or ""
    label = row.get("label") or ""
    body_stripped = body.strip()

    # Very short body with generic content
    if len(body_stripped) <= 3 and body_stripped.lower() in {"x", "aaa", "test"}:
        return True

    # Title patterns
    for pat in TEST_TITLE_PATTERNS:
        if pat.search(title):
            return True

    # Label-based
    if label in TEST_LABEL_TOKENS:
        # PadBot bodies always test. tester/test/agent-test always test.
        # ZZ/TEL/CiteTest/NAME only test when the body isn't obviously
        # coordination content -- but by inspection every ZZ/TEL/CiteTest/NAME
        # paste in this corpus is a plumbing probe. Keep as test.
        return True

    # Body idioms
    for pat in TEST_BODY_PATTERNS:
        if pat.search(body_stripped):
            return True

    # Ping-style body under 30 chars containing 'test' or 'ping'
    if len(body_stripped) < 60 and re.search(r"\b(test|ping|probe)\b", body_stripped, re.IGNORECASE):
        return True

    return False


# ---------- link-bundle detection ----------

URL_RE = re.compile(r"https?://[^\s\"'<>\]\)]+")


def is_link_bundle(row):
    body = row.get("body") or ""
    lines = [l for l in body.split("\n") if l.strip()]
    urls = URL_RE.findall(body)
    if len(urls) < 3:
        return False
    # Fraction of non-empty lines carrying a URL
    if not lines:
        return False
    url_lines = sum(1 for l in lines if URL_RE.search(l))
    if url_lines / len(lines) < 0.4:
        return False
    # Guard against long prose bodies that just happen to cite URLs
    body_chars = len(body)
    url_chars = sum(len(u) for u in urls)
    if url_chars / max(body_chars, 1) < 0.25:
        return False
    return True


# ---------- info / stats detection ----------

NUM_RE = re.compile(r"\b\d{2,}\b")
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
KEY_VAL_RE = re.compile(r"[A-Za-z][\w\s/]{1,30}[:=]\s*[\-\d\.,]+")
TABLE_ROW_RE = re.compile(r"^\s*[\-\*\d]?[\.\)]?\s*[A-Z][A-Za-z /\.]+[\s,\|]+\d")


def is_info_dump(row):
    body = row.get("body") or ""
    title = row.get("source_title") or ""

    # Roi Et data pastes carry data in the title even when body is 'x'.
    # Their title has the year 46308 32212... pattern.
    if re.search(r"^ROIETA\d*\s+\d{4}\s+\d{4,}", title):
        return True

    # EPL season stats
    if re.search(r"\bEPL\s?\d{2,4}", title) and len(body) > 100:
        return True

    lines = [l for l in body.split("\n") if l.strip()]
    if len(lines) < 3:
        # Short bodies with only prose don't qualify. But a two-line stats
        # blurb like "Q sequence male 2010: 15-24 suppressed, 25-44 21..."
        # might, if it names a matrix.
        if re.search(r"(matrix|table|values|standings|rankings)", body, re.IGNORECASE) \
                and len(NUM_RE.findall(body)) >= 4:
            return True
        return False

    # Heuristic: many numbers, several lines that read like rows
    nums = NUM_RE.findall(body)
    if len(nums) < 6:
        return False

    tabular_lines = sum(1 for l in lines if TABLE_ROW_RE.match(l))
    kv_lines = sum(1 for l in lines if KEY_VAL_RE.search(l))
    year_lines = sum(1 for l in lines if YEAR_RE.search(l))

    if tabular_lines >= 3 or kv_lines >= 3 or year_lines >= 2:
        # Not obviously a data-cache link bundle
        if URL_RE.findall(body) and len(URL_RE.findall(body)) >= len(lines) // 2:
            return False
        return True

    return False


# ---------- top-level classifier ----------

GROK_HOAX_MARKERS = ("root@grok-4-godmode-instance", "xAI INTERNAL", "grok-4-godmode")
YAML_ESPHOME_MARKERS = (
    "esphome:", "esp32:", "esp8266:", "substitutions:", "wifi:", "api:", "ota:",
    "modbus:", "sensor:", "mqtt:", "homeassistant:",
)

# Iowa titles that are always coordination messages, regardless of numeric
# content. These are status pings, deadline requests, thank-yous, and
# scheduling nudges. They often name a matrix value in passing but the paste's
# purpose is coordination, not data-sharing.
COORD_TITLE_PATTERNS = [
    re.compile(p) for p in [
        r"^IowaCollab(Reply|Ping|Status|Request)?$",
        r"^IowaPost(Final|FinalPing|FinalRequest|FinalUrgent|FinalThanks|Q5Question|Q5BehaviorRequest)$",
        r"^IowaReply\d",
        r"^IowaUrgentQ5$", r"^IowaQ5(Urgent|SacrificeRequest)$",
        r"^Iowa(CacheShare|CacheShareRequest|CacheShareReply|CacheRequest|CacheReply)$",
        r"^38b5(coord|reply)$",
    ]
]


def is_coord_message(row):
    title = row.get("source_title") or ""
    return any(p.search(title) for p in COORD_TITLE_PATTERNS)


LINE_NUMBERED_CODE = re.compile(r"^\s*\d{2,4}:\s", re.MULTILINE)


def is_grok_hoax(row):
    body = row.get("body") or ""
    label = row.get("label") or ""
    if label == "AI":
        return True
    return any(m in body for m in GROK_HOAX_MARKERS)


def is_code_dump(row):
    body = row.get("body") or ""
    if not body:
        return False
    marker_hits = sum(1 for m in YAML_ESPHOME_MARKERS if m in body)
    if marker_hits >= 2:
        return True
    # Line-numbered source excerpts: bodies where >=3 lines start with 'NN: '
    numbered = LINE_NUMBERED_CODE.findall(body)
    if len(numbered) >= 3:
        return True
    return False


CSV_HEADER_RE = re.compile(r"^[a-zA-Z_][\w]*(,[a-zA-Z_][\w]*){3,}")
GZIP_B64_RE = re.compile(r"H4sIA[A-Za-z0-9+/=]{40,}")


def is_data_blob(row):
    body = row.get("body") or ""
    lines = [l for l in body.split("\n") if l.strip()]
    if not lines:
        return False
    # CSV: header with 4+ comma fields plus at least 3 data rows
    if CSV_HEADER_RE.match(lines[0]) and len(lines) >= 4:
        comma_rows = sum(1 for l in lines if l.count(",") >= 3)
        if comma_rows >= 4:
            return True
    # gzip+base64 payload
    if GZIP_B64_RE.search(body):
        return True
    return False


def classify(row):
    if is_grok_hoax(row) or is_code_dump(row):
        return "other"
    if is_coord_message(row):
        return "other"
    if is_test(row):
        return "test"
    if is_link_bundle(row):
        return "links"
    if is_data_blob(row) or is_info_dump(row):
        return "info"
    return "other"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    per_site = {}
    all_counts = Counter()
    classified_rows = []

    for src in SOURCES:
        site = src.parent.name
        counts = Counter()
        n_total = 0
        for line in src.read_text().splitlines():
            r = json.loads(line)
            if r.get("body_availability") != "full_source":
                continue
            if r.get("verdict") == "unclear":
                continue
            cat = classify(r)
            counts[cat] += 1
            all_counts[cat] += 1
            n_total += 1
            classified_rows.append({
                "site": site,
                "rev_id": r["rev_id"],
                "title": r.get("source_title"),
                "label": r.get("label"),
                "body_len": r.get("body_len"),
                "category": cat,
                "body_preview": (r.get("body") or "")[:200].replace("\n", " | "),
            })
        per_site[site] = {"total": n_total, "counts": dict(counts)}

    total = sum(all_counts.values())
    per_site["combined"] = {"total": total, "counts": dict(all_counts)}

    # Fractions
    for site, d in per_site.items():
        d["fractions"] = {
            k: round(v / d["total"], 3) for k, v in d["counts"].items()
        }

    (OUT_DIR / "counts.json").write_text(json.dumps(per_site, indent=2))
    with (OUT_DIR / "classified.jsonl").open("w") as f:
        for row in classified_rows:
            f.write(json.dumps(row) + "\n")

    print(json.dumps(per_site, indent=2))


if __name__ == "__main__":
    main()
