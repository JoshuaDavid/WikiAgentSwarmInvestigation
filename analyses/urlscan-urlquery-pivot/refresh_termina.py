#!/usr/bin/env python3
"""Refresh the small swarm.termina.digital tables used for dedup.

Downloads pub/manifest.json and the venue, venue_link, lead, evidence, claim,
and tracker tables into scrape/outputs/swarm.termina.digital/pub/. Existing
files are only replaced when the download returns HTTP 200. The site answers
503 "public exports are temporarily unavailable" during its maintenance
windows; the script reports that and leaves the mirror untouched.
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DEST = os.path.join(REPO, "scrape", "outputs", "swarm.termina.digital", "pub")
BASE = "https://swarm.termina.digital/pub/"
FILES = ["manifest.json", "venue.jsonl", "venue_link.jsonl", "lead.jsonl",
         "evidence.jsonl", "claim.jsonl", "tracker.jsonl", "incident.jsonl"]
UA = "collusionwiki-research/0.1"


def main() -> int:
    os.makedirs(DEST, exist_ok=True)
    ok = 0
    for name in FILES:
        req = urllib.request.Request(BASE + name, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            with open(os.path.join(DEST, name), "wb") as f:
                f.write(data)
            print(f"{name}: {len(data)} bytes")
            ok += 1
        except urllib.error.HTTPError as e:
            print(f"{name}: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:80]}")
        except Exception as ex:
            print(f"{name}: {ex!r}")
    print(f"{ok}/{len(FILES)} refreshed")
    return 0 if ok == len(FILES) else 1


if __name__ == "__main__":
    sys.exit(main())
