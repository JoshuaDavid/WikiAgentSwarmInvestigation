#!/usr/bin/env python3
"""Scan every wiki access log for source IPs that fall in any historical
OpenAI GPTBot CIDR published in
oai-index-scan/oai-published-bot-info/archives/gptbot/gptbot_historical_ip_ranges.all.json.

Membership uses the *union* of all snapshots — an IP that appeared in any
published snapshot at any date counts as a match, regardless of whether it
was in-range at the moment of the request.

Output:
  outputs/gptbot_ip_hits.tsv
      wiki  ip  cidr  first_ts  last_ts  count
      (one row per (wiki, ip) that matched at least once)
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
RANGES = REPO / "oai-index-scan" / "oai-published-bot-info" / "archives" / "gptbot" / "gptbot_historical_ip_ranges.all.json"
OUT = Path(__file__).resolve().parent / "outputs" / "gptbot_ip_hits.tsv"

IP_RE = re.compile(rb"\|IP\|([0-9a-fA-F:.]+)(?:#\d+)?\|")
TS_RE = re.compile(rb"\|TS\|(\d+)")


def load_networks() -> list[ipaddress._BaseNetwork]:
    with RANGES.open() as f:
        snapshots = json.load(f)
    nets: set[str] = set()
    for snap in snapshots:
        for r in snap.get("records", {}).get("prefixes", []):
            for key in ("ipv4Prefix", "ipv6Prefix"):
                if key in r:
                    nets.add(r[key])
    return [ipaddress.ip_network(c) for c in sorted(nets)]


def in_any(ip: ipaddress._BaseAddress, nets) -> str | None:
    for n in nets:
        if ip.version != n.version:
            continue
        if ip in n:
            return str(n)
    return None


def main() -> None:
    nets = load_networks()
    print(f"loaded {len(nets)} distinct GPTBot CIDRs (union of snapshots)",
          file=sys.stderr)

    ip_cache: dict[str, str | None] = {}
    hits: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"cidr": None, "first": None, "last": None, "count": 0}
    )
    grand_total_lines = 0
    grand_total_hits = 0

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
                    cidr = ip_cache.get(ip_s)
                    if cidr is None and ip_s not in ip_cache:
                        try:
                            cidr = in_any(ipaddress.ip_address(ip_s), nets)
                        except ValueError:
                            cidr = None
                        ip_cache[ip_s] = cidr
                    if not cidr:
                        continue
                    m_ts = TS_RE.search(raw)
                    ts = int(m_ts.group(1)) if m_ts else None
                    rec = hits[(wiki, ip_s)]
                    rec["cidr"] = cidr
                    rec["count"] += 1
                    if ts is not None:
                        if rec["first"] is None or ts < rec["first"]:
                            rec["first"] = ts
                        if rec["last"] is None or ts > rec["last"]:
                            rec["last"] = ts
                    wiki_hits += 1
        grand_total_lines += wiki_lines
        grand_total_hits += wiki_hits
        print(f"{wiki:9s}  {wiki_lines:>12,} lines with IP  "
              f"{wiki_hits:>10,} matched GPTBot CIDR", file=sys.stderr)

    print(f"\nTOTAL     {grand_total_lines:>12,} lines with IP  "
          f"{grand_total_hits:>10,} matched GPTBot CIDR", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        f.write("wiki\tip\tcidr\tfirst_ts\tlast_ts\tcount\n")
        for (wiki, ip), rec in sorted(hits.items(),
                                      key=lambda kv: (-kv[1]["count"], kv[0])):
            f.write(f"{wiki}\t{ip}\t{rec['cidr']}\t"
                    f"{rec['first']}\t{rec['last']}\t{rec['count']}\n")
    print(f"\nwrote {OUT}  ({len(hits):,} (wiki,ip) rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
