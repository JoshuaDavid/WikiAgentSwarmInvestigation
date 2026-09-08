#!/usr/bin/env python3
"""Find pastes that mention >=2 distinct agent names but are not in any
promoted or candidate paste-thread cluster.

An "agent name" is any regex match of `agent[-_]?[\w]{1,}` in the paste's
label, source_title, or body. Distinct = at least 2 unique matches after
lowercasing.

A paste is "in a known thread" if its page_id appears in the
`paste_ids` list of any row in outputs/candidates.jsonl.

Output: pastes ranked by (n_distinct_agent_names desc, body_len desc).
"""

from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "agent-logs"
CANDIDATES = Path(__file__).resolve().parent / "outputs" / "candidates.jsonl"
OUT = Path(__file__).resolve().parent / "outputs" / "orphan_multi_agent.jsonl"

# Same host list as build_candidates.py
HOSTS = [
    "paste-linuxiarz",
    "pastebin-k4be",
    "paste.steamr.com",
    "pastebin.tarcseh.me",
    "pastebin.freepbx.org",
    "paste.lightcast.com",
    "paste.smirky.net",
    "pastebin.faster-it.de",
    "pastes",
]
SHELLAC_HOST_SKIP = {
    "linuxiarz",
    "pastebin-k4be",
    "paste.steamr.com",
    "pastebin.tarcseh.me",
    "paste.smirky.net",
    "pastebin.faster-it.de",
}

AGENT_RE = re.compile(r"\bagent[-_]?[\w]+", re.I)


def load_host(host):
    p = LOG_DIR / host / "revisions.jsonl"
    rows = [json.loads(l) for l in p.read_text().splitlines() if l]
    if host == "pastes":
        def keep(r):
            pid = r.get("page_id") or ""
            parts = pid.split("/", 2)
            if len(parts) >= 2 and parts[1] in SHELLAC_HOST_SKIP:
                return False
            return True
        rows = [r for r in rows if keep(r)]
    for r in rows:
        if not r.get("source_title") and r.get("shellac_title"):
            r["source_title"] = r["shellac_title"]
    return rows


def agents_in(text):
    if not text:
        return set()
    return {m.lower() for m in AGENT_RE.findall(text)}


def main():
    in_cluster = set()
    for row in (json.loads(l) for l in CANDIDATES.read_text().splitlines() if l):
        for pid in row["paste_ids"]:
            in_cluster.add(pid)

    orphans = []
    for host in HOSTS:
        for r in load_host(host):
            pid = r.get("page_id")
            if pid in in_cluster:
                continue
            label = r.get("label") or ""
            title = r.get("source_title") or ""
            body = r.get("body") or ""
            agents = agents_in(label) | agents_in(title) | agents_in(body)
            if len(agents) < 2:
                continue
            orphans.append({
                "page_id": pid,
                "host": host,
                "time": r.get("time"),
                "label": label,
                "title": title,
                "body_len": r.get("body_len") or len(body),
                "n_agent_names": len(agents),
                "agent_names": sorted(agents),
                "body_preview": (body[:300].replace("\n", " | ") if body else ""),
            })

    orphans.sort(
        key=lambda o: (-o["n_agent_names"], -(o["body_len"] or 0))
    )
    OUT.write_text("\n".join(json.dumps(o) for o in orphans) + "\n")

    print(f"orphan pastes with >=2 distinct agent names: {len(orphans)}")
    print(f"top 20 by (n_agents, body_len):\n")
    for o in orphans[:20]:
        print(
            f"  n={o['n_agent_names']}  len={o['body_len']:>6}  "
            f"{o['time'] or '(no time)'}  {o['host']}  "
            f"{o['page_id']}  label=`{o['label']}`  title=`{o['title'][:40]}`"
        )
        print(f"    agents: {', '.join(o['agent_names'][:8])}"
              + (f" ... (+{len(o['agent_names'])-8})" if len(o["agent_names"]) > 8 else ""))
        print(f"    body: {o['body_preview'][:200]}")
        print()


if __name__ == "__main__":
    main()
