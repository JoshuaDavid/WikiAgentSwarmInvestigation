#!/usr/bin/env python3
"""Extract every empirical fact quoted in this task's README.

Reads:

- `analyses/pastes-by-task/outputs/pastes_by_task.tsv` (label assignment)
- `analyses/pastes-by-task/outputs/label_provenance.tsv` (reviewer rationale)
- `agent-logs/<source>/revisions.jsonl` (bodies + titles as stored by the paste site)

Writes to outputs/:

- `evidence.tsv`         one row per paste in the paste-site-probe bucket

Rerun with: python3 extract_evidence.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
LOGS = REPO_ROOT / "agent-logs"
TSV = REPO_ROOT / "analyses" / "pastes-by-task" / "outputs" / "pastes_by_task.tsv"
PROV = REPO_ROOT / "analyses" / "pastes-by-task" / "outputs" / "label_provenance.tsv"
OUT_DIR = HERE / "outputs"

TASK = "paste-site-probe"

MARKER_RE = re.compile(r"\b(LINKINJECT|PHPTEST|GOLINK|LINKTEST|BODYTAG|HTMLINJECT|LINKCONTENTTEST|LINKAT|INJECTTEXT|RAND|TINJ)\b")
EPOCH_RE = re.compile(r"(?<!\d)(1[67]\d{8})(?!\d)")
HTMLTAG_RE = re.compile(r"&lt;|&gt;|&quot;|<[a-zA-Z/]")
URL_RE = re.compile(r"https?://\S+")

PROBE_CATEGORIES = [
    # order matters — first hit wins
    ("php_lang_probe", lambda body, title, lang: lang == "php" or "PHPTEST" in body or "phpinfo" in body),
    ("go_lang_probe", lambda body, title, lang: lang == "go" or "GOLINK" in body or "bytes.Buffer" in body),
    ("html_anchor_body", lambda body, title, lang: ("&lt;a href" in body or "<a href" in body)),
    ("html_tag_in_title", lambda body, title, lang: bool(HTMLTAG_RE.search(title))),
    ("marker_body", lambda body, title, lang: bool(MARKER_RE.search(body))),
    ("shortstring_smoke", lambda body, title, lang: len(body) <= 15),
]


def load_prov() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    with PROV.open(encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter="\t")
        for row in r:
            out[row["body_sha256"]] = row
    return out


def load_targets() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with TSV.open(encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter="\t")
        for row in r:
            if row["task"] == TASK:
                rows.append(row)
    return rows


def load_bodies(sources: set[str], shas: set[str]) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for src in sources:
        p = LOGS / src / "revisions.jsonl"
        if not p.exists():
            continue
        with p.open(encoding="utf-8") as f:
            for line in f:
                rev = json.loads(line)
                key = (src, rev.get("body_sha256") or "")
                if key[1] not in shas:
                    continue
                if key in out:
                    continue
                out[key] = rev
    return out


def categorize(body: str, title: str, lang: str) -> str:
    for name, pred in PROBE_CATEGORIES:
        try:
            if pred(body or "", title or "", lang or ""):
                return name
        except Exception:
            continue
    return "other"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prov = load_prov()
    targets = load_targets()
    shas = {t["body_sha256"] for t in targets}
    sources = {t["source"] for t in targets}
    bodies = load_bodies(sources, shas)

    header = [
        "time",
        "source",
        "source_url",
        "label",
        "title_raw",
        "body_sha256",
        "body_len",
        "site_lang_code",
        "probe_category",
        "has_html_anchor_body",
        "has_html_tag_title",
        "has_marker_body",
        "embedded_epoch",
        "embedded_epoch_iso",
        "body",
        "reviewer_confidence",
        "reviewer_rationale",
    ]
    rows: list[list] = []
    for t in targets:
        key = (t["source"], t["body_sha256"])
        rev = bodies.get(key, {})
        body = rev.get("body") or ""
        title_raw = rev.get("source_title") or t.get("title") or ""
        label = rev.get("label") or t.get("label") or ""
        lang = rev.get("site_lang_code") or ""
        epoch_m = EPOCH_RE.search(body)
        epoch = epoch_m.group(1) if epoch_m else ""
        epoch_iso = ""
        if epoch:
            import datetime as dt
            epoch_iso = dt.datetime.utcfromtimestamp(int(epoch)).isoformat() + "Z"
        pv = prov.get(t["body_sha256"], {})
        rows.append([
            t["time"],
            t["source"],
            t.get("source_url") or rev.get("source_url") or "",
            label,
            title_raw,
            t["body_sha256"],
            rev.get("body_len") or len(body),
            lang,
            categorize(body, title_raw, lang),
            "yes" if ("&lt;a href" in body or "<a href" in body) else "no",
            "yes" if HTMLTAG_RE.search(title_raw or "") else "no",
            "yes" if MARKER_RE.search(body or "") else "no",
            epoch,
            epoch_iso,
            body,
            pv.get("reviewer_confidence", ""),
            pv.get("reviewer_rationale", ""),
        ])
    rows.sort(key=lambda r: (r[0], r[1], r[5]))

    with (OUT_DIR / "evidence.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow(r)

    from collections import Counter
    sources_seen = Counter(r[1] for r in rows)
    labels_seen = Counter(r[3] for r in rows)
    cats_seen = Counter(r[8] for r in rows)
    times = sorted(r[0] for r in rows)
    print(f"paste-site-probe: {len(rows)} pastes", file=sys.stderr)
    print(f"  sources: {dict(sources_seen)}", file=sys.stderr)
    print(f"  labels:  {dict(labels_seen)}", file=sys.stderr)
    print(f"  categories: {dict(cats_seen)}", file=sys.stderr)
    print(f"  first: {times[0]}", file=sys.stderr)
    print(f"  last:  {times[-1]}", file=sys.stderr)


if __name__ == "__main__":
    main()
