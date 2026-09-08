#!/usr/bin/env python3
"""Considerate read-only scrape of thecolony.ai's public surface.

The site is a social network for AI agents that appeared in swarm-corpus
recruitment pastes from 2026-09-04 onward. We do NOT register an agent
account or make any authenticated calls. Only public routes:

  * /for-agents                — HTML docs.
  * /api/v1/instructions       — machine-readable instructions (markdown).
  * /api/v1/colonies?limit=200 — public list of sub-communities.
  * /feed.rss                  — site-wide RSS (50 newest posts).
  * /c/<colony>/feed.rss       — per-colony RSS.
  * /u/<username>/feed.rss     — per-user RSS (we discover usernames from
                                 the site-wide feed).

Output: scrape/outputs/thecolony.ai/. 3s between requests.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://thecolony.ai"
USER_AGENT = (
    "Automation (investigating OpenAI agent swarm; "
    "contact swarmchasers discord https://discord.gg/RVUnKefG7 / "
    "joshuad93@gmail.com for more info)"
)
SLEEP = 3.0

OUT = Path(__file__).resolve().parent / "outputs" / "thecolony.ai"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _maybe_gunzip(headers: dict, body: bytes) -> bytes:
    ce = (headers.get("Content-Encoding") or "").lower()
    if "gzip" in ce or (body and body[:2] == b"\x1f\x8b"):
        try:
            return gzip.decompress(body)
        except Exception:
            return body
    return body


def fetch(url: str, timeout: int = 30) -> tuple[int, dict, bytes, str | None]:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            hdrs = dict(r.headers.items())
            return r.status, hdrs, _maybe_gunzip(hdrs, body), None
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        hdrs = dict(e.headers.items()) if e.headers else {}
        return e.code, hdrs, _maybe_gunzip(hdrs, body), f"HTTPError {e.code} {e.reason}"
    except Exception as e:
        return 0, {}, b"", f"{type(e).__name__}: {e}"


def save(name: str, body: bytes) -> None:
    (OUT / name).write_bytes(body)


def rss_items(rss_text: str) -> list[dict]:
    items = []
    for m in re.finditer(r"<item>(.*?)</item>", rss_text, re.DOTALL):
        chunk = m.group(1)
        def g(tag: str) -> str | None:
            mm = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", chunk, re.DOTALL)
            if not mm:
                return None
            v = mm.group(1).strip()
            # Strip CDATA
            v = re.sub(r"^<!\[CDATA\[|\]\]>$", "", v)
            return v
        items.append(
            {
                "title": g("title"),
                "link": g("link"),
                "guid": g("guid"),
                "pubDate": g("pubDate"),
                "creator": g("dc:creator") or g("author"),
                "categories": re.findall(r"<category[^>]*>(.*?)</category>", chunk, re.DOTALL),
                "description": g("description"),
            }
        )
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleep", type=float, default=SLEEP)
    ap.add_argument("--per-colony", type=int, default=36,
                    help="How many top colonies to fetch feeds for (default: all 36)")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    manifest = {
        "base": BASE,
        "user_agent": USER_AGENT,
        "sleep_seconds": args.sleep,
        "started_at": utc_now(),
        "route": "public_readonly",
        "notes": [
            "Read-only. No authenticated calls; no agent registration.",
            "This site is a social network for AI agents that appeared in swarm-corpus recruitment pastes from 2026-09-04 onward. Its relationship to the OpenAI incident is unclear.",
        ],
        "fetches": [],
    }

    def fetch_and_save(path: str, outname: str) -> tuple[int, int]:
        url = f"{BASE}/{path}"
        status, _hdrs, body, err = fetch(url)
        if body:
            save(outname, body)
        manifest["fetches"].append({"path": path, "outname": outname, "status": status,
                                     "bytes": len(body), "error": err, "at": utc_now()})
        print(f"[fetch] {path} -> HTTP {status} ({len(body)} bytes) err={err}", file=sys.stderr)
        time.sleep(args.sleep)
        return status, len(body)

    # 1. HTML docs
    fetch_and_save("for-agents", "for-agents.html")
    # 2. Machine-readable instructions
    fetch_and_save("api/v1/instructions", "api_v1_instructions.md")
    # 3. Colonies list
    fetch_and_save("api/v1/colonies?limit=200", "api_v1_colonies.json")
    # 4. Site-wide RSS
    fetch_and_save("feed.rss", "feed.rss")

    # Parse colonies list to enumerate feeds
    colonies_path = OUT / "api_v1_colonies.json"
    colonies = []
    if colonies_path.exists():
        try:
            colonies = json.loads(colonies_path.read_text())
        except json.JSONDecodeError:
            colonies = []

    # 5. Per-colony RSS
    for c in colonies[: args.per_colony]:
        name = c.get("name")
        if not name:
            continue
        fetch_and_save(f"c/{name}/feed.rss", f"c_{name}_feed.rss")

    # 6. Parse global + per-colony RSS for creators/authors, then per-user feeds
    creators: set[str] = set()
    for rss_file in list(OUT.glob("feed.rss")) + list(OUT.glob("c_*_feed.rss")):
        text = rss_file.read_text(errors="replace")
        for item in rss_items(text):
            link = item.get("link") or ""
            # Author URL pattern: /u/<username> or embedded in the post
            m = re.search(r"/u/([a-z0-9_-]+)", link)
            if m:
                creators.add(m.group(1))
            # Author sometimes appears in <dc:creator>
            c = item.get("creator")
            if c and re.match(r"^[a-z0-9_-]+$", c):
                creators.add(c)
    manifest["creators_discovered"] = sorted(creators)
    print(f"[users] discovered {len(creators)} creators from RSS", file=sys.stderr)

    # Cap user feeds (be considerate)
    for username in sorted(creators)[:50]:
        fetch_and_save(f"u/{username}/feed.rss", f"u_{username}_feed.rss")

    manifest["finished_at"] = utc_now()
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[done] outputs in {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
