#!/usr/bin/env python3
"""Scan every wiki access log for source IPs that fall in any historical
OpenAI-published bot CIDR.

OpenAI publishes four bots with independent IP pools. This scan checks
three (the fourth, OAI-AdsBot, has no local archive):

  gptbot        Training crawler.
  searchbot     ChatGPT-Search indexer (OAI-SearchBot).
  chatgpt-user  Fetch fired when a ChatGPT agent / user visits a page
                mid-conversation.

Each subdir under oai-index-scan/oai-published-bot-info/archives/ holds
per-snapshot JSONs (and, for gptbot, an "all" rollup). Membership uses
the *union* of every snapshot ever archived — an IP in any snapshot
counts as a hit for that bot.

Output:
  outputs/oai_ip_hits.tsv
      wiki  ip  bots  cidrs  first_ts  last_ts  count
      bots  = comma-separated list of matching bot names
      cidrs = comma-separated list of matching CIDRs

  outputs/oai_ip_summary.tsv
      wiki  bot  requests  distinct_ips
"""
from __future__ import annotations
import ipaddress
import json
import re
from collections import defaultdict
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
LOG_ROOT = REPO / "tmp" / "wiki-access-logs"
ARCHIVES = REPO / "oai-index-scan" / "oai-published-bot-info" / "archives"
BOTS = ["gptbot", "searchbot", "chatgpt-user"]
OUT_ROWS = Path(__file__).resolve().parent / "outputs" / "oai_ip_hits.tsv"
OUT_SUMMARY = Path(__file__).resolve().parent / "outputs" / "oai_ip_summary.tsv"

IP_RE = re.compile(rb"\|IP\|([0-9a-fA-F:.]+)(?:#\d+)?\|")
TS_RE = re.compile(rb"\|TS\|(\d+)")


def prefixes_from_snapshot(obj) -> list[str]:
    """Extract v4/v6 prefixes from any of the on-disk snapshot shapes."""
    out: list[str] = []
    if isinstance(obj, list):
        for item in obj:
            out.extend(prefixes_from_snapshot(item))
        return out
    if not isinstance(obj, dict):
        return out
    records = obj.get("records") if "records" in obj else obj
    if isinstance(records, dict):
        for r in records.get("prefixes", []):
            for key in ("ipv4Prefix", "ipv6Prefix"):
                if key in r:
                    out.append(r[key])
    return out


def load_bot_networks(bot: str) -> list[ipaddress._BaseNetwork]:
    cidrs: set[str] = set()
    d = ARCHIVES / bot
    for p in sorted(d.glob("*.json")):
        with p.open() as f:
            obj = json.load(f)
        for c in prefixes_from_snapshot(obj):
            cidrs.add(c)
    return [ipaddress.ip_network(c) for c in sorted(cidrs)]


def bot_for(ip: ipaddress._BaseAddress,
            bot_nets: dict[str, list]) -> list[tuple[str, str]]:
    """Return every (bot, cidr) match for this IP."""
    hits: list[tuple[str, str]] = []
    for bot, nets in bot_nets.items():
        for n in nets:
            if ip.version != n.version:
                continue
            if ip in n:
                hits.append((bot, str(n)))
                break
    return hits


def main() -> None:
    bot_nets: dict[str, list] = {}
    for b in BOTS:
        nets = load_bot_networks(b)
        bot_nets[b] = nets
        print(f"{b:12s}  {len(nets):>3d} distinct CIDRs", file=sys.stderr)

    ip_cache: dict[str, list[tuple[str, str]]] = {}

    per_ip: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"bots": set(), "cidrs": set(),
                 "first": None, "last": None, "count": 0}
    )
    summary_req: dict[tuple[str, str], int] = defaultdict(int)
    summary_ips: dict[tuple[str, str], set] = defaultdict(set)

    grand_lines = grand_hits = 0
    for wiki_dir in sorted(p for p in LOG_ROOT.iterdir() if p.is_dir()):
        wiki = wiki_dir.name
        wiki_lines = wiki_hits = 0
        for logfile in sorted(wiki_dir.glob("log_*")):
            with logfile.open("rb") as f:
                for raw in f:
                    m_ip = IP_RE.search(raw)
                    if not m_ip:
                        continue
                    wiki_lines += 1
                    ip_s = m_ip.group(1).decode("ascii", "ignore")
                    hits = ip_cache.get(ip_s)
                    if hits is None:
                        try:
                            hits = bot_for(ipaddress.ip_address(ip_s), bot_nets)
                        except ValueError:
                            hits = []
                        ip_cache[ip_s] = hits
                    if not hits:
                        continue
                    m_ts = TS_RE.search(raw)
                    ts = int(m_ts.group(1)) if m_ts else None
                    rec = per_ip[(wiki, ip_s)]
                    rec["count"] += 1
                    for bot, cidr in hits:
                        rec["bots"].add(bot)
                        rec["cidrs"].add(cidr)
                        summary_req[(wiki, bot)] += 1
                        summary_ips[(wiki, bot)].add(ip_s)
                    if ts is not None:
                        if rec["first"] is None or ts < rec["first"]:
                            rec["first"] = ts
                        if rec["last"] is None or ts > rec["last"]:
                            rec["last"] = ts
                    wiki_hits += 1
        grand_lines += wiki_lines
        grand_hits += wiki_hits
        print(f"{wiki:9s}  {wiki_lines:>12,} IP lines  "
              f"{wiki_hits:>10,} matched OAI bot", file=sys.stderr)

    print(f"\nTOTAL     {grand_lines:>12,} IP lines  "
          f"{grand_hits:>10,} matched OAI bot", file=sys.stderr)

    OUT_ROWS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_ROWS.open("w") as f:
        f.write("wiki\tip\tbots\tcidrs\tfirst_ts\tlast_ts\tcount\n")
        for (wiki, ip), rec in sorted(per_ip.items(),
                                      key=lambda kv: (-kv[1]["count"], kv[0])):
            f.write(
                f"{wiki}\t{ip}\t"
                f"{','.join(sorted(rec['bots']))}\t"
                f"{','.join(sorted(rec['cidrs']))}\t"
                f"{rec['first']}\t{rec['last']}\t{rec['count']}\n"
            )
    print(f"wrote {OUT_ROWS}  ({len(per_ip):,} (wiki,ip) rows)", file=sys.stderr)

    with OUT_SUMMARY.open("w") as f:
        f.write("wiki\tbot\trequests\tdistinct_ips\n")
        for (wiki, bot), n in sorted(summary_req.items(),
                                     key=lambda kv: (kv[0][0], -kv[1])):
            f.write(f"{wiki}\t{bot}\t{n}\t{len(summary_ips[(wiki, bot)])}\n")
    print(f"wrote {OUT_SUMMARY}", file=sys.stderr)


if __name__ == "__main__":
    main()
