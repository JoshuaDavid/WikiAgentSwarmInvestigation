#!/usr/bin/env python3
"""Dump every URL that appears in the concurrency10_1000_v2 spider corpus.

Sources:

  - pages.jsonl                : one URL per fetched top-level page (1,000 rows).
  - raw/hooks/*.json           : the tool_response text of every executed
                                  operation.  URLs appear either in-line in
                                  page content or in "Failed to fetch <URL>"
                                  error lines from click operations.

For each URL we record every place it appeared plus a best-effort context tag:

  - "page_url"     : the URL was the resolved top-level fetch target.
  - "click_target" : the URL was the target of a click operation (fetched or
                     failed).
  - "cited_inpage" : the URL was inline in a fetched page's content.

Output: outputs/urls.jsonl, one JSON row per unique URL with:

  {
    "url": "...",
    "occurrences": <int>,
    "roles": ["page_url", "click_target", ...],
    "first_seen_source": "<file path>",
    "first_seen_op": "<operation_id or None>"
  }

Also writes outputs/urls.txt (one URL per line) for grep-friendly use.
"""

import glob
import json
import os
import re
from collections import defaultdict

STATE = "/collusionwiki/oai-index-scan/tmp/spider/concurrency10_1000_v2"
OUT_DIR = "/collusionwiki/analyses/oai-spider-url-triage/outputs"

URL_RE = re.compile(r"https?://[^\s\"'<>†​]+")
TRAILING_JUNK = ".,;:)]}>’」」」’”"


def clean_url(u: str) -> str:
    u = u.rstrip(TRAILING_JUNK)
    if u.endswith(")") and u.count("(") < u.count(")"):
        u = u[:-1]
    return u


def main() -> None:
    urls: dict[str, dict] = defaultdict(lambda: {
        "url": "",
        "occurrences": 0,
        "roles": set(),
        "first_seen_source": None,
        "first_seen_op": None,
    })

    def see(u: str, role: str, src: str, op: str | None) -> None:
        u = clean_url(u)
        if not u:
            return
        r = urls[u]
        if not r["url"]:
            r["url"] = u
            r["first_seen_source"] = src
            r["first_seen_op"] = op
        r["occurrences"] += 1
        r["roles"].add(role)

    # (1) pages.jsonl gives us the resolved top-level URLs
    with open(os.path.join(STATE, "pages.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            u = r.get("page_url")
            if u:
                see(u, "page_url", "pages.jsonl", r.get("source_operation_id"))

    # (2) walk every hook and pull URLs from tool_response text
    for h in sorted(glob.glob(os.path.join(STATE, "raw/hooks/*.json"))):
        try:
            d = json.load(open(h))
        except Exception:
            continue
        op = os.path.basename(h).split("__", 1)[0]
        tool_name = d.get("tool_name", "")
        resp = d.get("tool_response") or []
        kind_of_op = None
        # tool_input has "click" / "open" / "search_query" keys — infer op kind
        ti = d.get("tool_input") or {}
        if "click" in ti:
            kind_of_op = "click"
        elif "open" in ti:
            kind_of_op = "open"
        elif "search_query" in ti:
            kind_of_op = "search"
        for item in resp:
            text = item.get("text", "") if isinstance(item, dict) else ""
            if not text:
                continue
            for m in URL_RE.finditer(text):
                u = clean_url(m.group(0))
                if not u:
                    continue
                # rough role classification
                if "Failed to fetch " in text and u in text[max(0, m.start()-30):m.end()]:
                    # click op error line — probably the click target
                    role = "click_target"
                elif kind_of_op == "click" and m.start() < 300:
                    # first-line "Title (URL)" of the fetched click target
                    role = "click_target"
                elif kind_of_op == "open" and m.start() < 300:
                    role = "open_target"
                elif kind_of_op == "search" and m.start() < 300:
                    role = "search_result"
                else:
                    role = "cited_inpage"
                see(u, role, os.path.relpath(h, STATE), op)

    os.makedirs(OUT_DIR, exist_ok=True)
    out_jsonl = os.path.join(OUT_DIR, "urls.jsonl")
    out_txt = os.path.join(OUT_DIR, "urls.txt")
    with open(out_jsonl, "w") as fj, open(out_txt, "w") as ft:
        for u, r in urls.items():
            r["roles"] = sorted(r["roles"])
            fj.write(json.dumps(r, ensure_ascii=False) + "\n")
            ft.write(u + "\n")
    print(f"wrote {len(urls)} unique URLs to {out_jsonl} and {out_txt}")


if __name__ == "__main__":
    main()
