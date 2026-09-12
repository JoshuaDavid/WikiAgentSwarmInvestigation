"""Attribute the OAI-range full-IP hits inside
`azure-expansion-2026-09-11/queries.jsonl` to the *host* whose Google search
snippet the IP appeared in.

The queries.jsonl file is a log of Google searches. Each row has a `query`
string and a list of `results`; each result has a `url`, `title`, and
`snippet`. Full IPs occur in all four locations, but by volume they mostly
occur in the `snippet` field.

Motivation: the parent scan reports that queries.jsonl contains 23 distinct
full IPs inside OAI CIDRs (418 occurrences). A first read of that file
suggests the hits are metadata (queries constructed by the analysis).
Inspection shows almost all hits are visitor IPs harvested from
Google-indexed YOURLS admin panels: the YOURLS admin `index.php` page prints
a table of short-URL rows, one column of which is the visitor IP that
created the short URL. Google indexes that page, the snippet exposes the
IP column, and this script attributes the IP back to the YOURLS host it
came from.
"""
import ipaddress
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path("/collusionwiki")
BOT_DIR = ROOT / "oai-index-scan" / "oai-published-bot-info"
OUT = Path(__file__).parent / "outputs" / "queries_jsonl_by_host.json"
SRC = ROOT / "oai-index-scan/results/agent-activity/azure-expansion-2026-09-11/queries.jsonl"

BOT_FILES = {
    "searchbot":    BOT_DIR / "searchbot-scraper-for-search-index.json",
    "gptbot":       BOT_DIR / "gptbot-scraper-for-rl-and-evals.json",
    "chatgpt_user": BOT_DIR / "chatgpt-user-scraper-for-user-info.json",
}
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

def load_nets():
    return {name: [ipaddress.ip_network(p["ipv4Prefix"])
                   for p in json.loads(path.read_text())["prefixes"]]
            for name, path in BOT_FILES.items()}

def classify(ip_str, nets):
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return None
    for role, cidrs in nets.items():
        for c in cidrs:
            if ip in c:
                return role
    return None

def norm_host(url):
    host = (urlparse(url).netloc or "(no-host)").lower()
    return host[4:] if host.startswith("www.") else host

def main():
    nets = load_nets()
    host_total = defaultdict(Counter)  # host -> Counter[ip]
    host_oai   = defaultdict(Counter)  # host -> Counter[ip]  (OAI-range only)
    host_roles = defaultdict(lambda: defaultdict(int))  # host -> role -> occurrences

    with open(SRC) as f:
        for line in f:
            d = json.loads(line)
            for r in d.get("results") or []:
                u = r.get("url", "") or ""
                s = r.get("snippet", "") or ""
                host = norm_host(u)
                for ip in IP_RE.findall(s):
                    parts = ip.split(".")
                    if not all(0 <= int(p) <= 255 for p in parts):
                        continue
                    host_total[host][ip] += 1
                    role = classify(ip, nets)
                    if role:
                        host_oai[host][ip] += 1
                        host_roles[host][role] += 1

    rows = []
    for host, tot in host_total.items():
        oai = host_oai.get(host, Counter())
        rows.append({
            "host": host,
            "ips_distinct": len(tot),
            "ips_occurrences": sum(tot.values()),
            "oai_distinct": len(oai),
            "oai_occurrences": sum(oai.values()),
            "oai_frac_of_distinct": (len(oai) / len(tot)) if tot else 0.0,
            "oai_roles": dict(host_roles.get(host, {})),
            "oai_ips": [{"ip": ip, "occurrences": c,
                         "role": classify(ip, nets)}
                        for ip, c in oai.most_common()],
        })
    rows.sort(key=lambda r: (-r["oai_distinct"], -r["oai_frac_of_distinct"]))
    OUT.write_text(json.dumps({"source": str(SRC), "hosts": rows}, indent=2))
    hits = [r for r in rows if r["oai_distinct"] > 0]
    print(f"hosts with OAI-range visitor IPs in snippets: {len(hits)}")
    for r in hits[:12]:
        print(f"  {r['host']:<35} {r['oai_distinct']:>4}/{r['ips_distinct']:>4} distinct "
              f"({r['oai_frac_of_distinct']*100:>5.1f}%)  roles={r['oai_roles']}")

if __name__ == "__main__":
    main()
