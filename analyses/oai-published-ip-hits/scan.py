"""Scan every jsonl file in the repository for IP addresses that match
OpenAI's published bot IP ranges.

Two passes:

1. **Full-IP pass.** Extract every dotted-quad string from each jsonl file and
   check whether it falls in a searchbot, gptbot, or chatgpt-user CIDR.
2. **ip16 pass.** Many corpus files record only the first two octets in an
   `ip16` field. For each such file, count how many ip16 values sit inside a
   /16 that hosts at least one OAI CIDR. A match here is a *corridor* hit only:
   the specific IP might or might not fall in the OAI CIDR, we cannot tell.

Reads:
- `oai-index-scan/oai-published-bot-info/searchbot-scraper-for-search-index.json`
- `oai-index-scan/oai-published-bot-info/gptbot-scraper-for-rl-and-evals.json`
- `oai-index-scan/oai-published-bot-info/chatgpt-user-scraper-for-user-info.json`

Writes:
- `outputs/full_ip_hits.json`
- `outputs/ip16_corridor_hits.json`
- `outputs/summary.md`
"""
import ipaddress
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/collusionwiki")
BOT_DIR = ROOT / "oai-index-scan" / "oai-published-bot-info"
OUT_DIR = Path(__file__).parent / "outputs"
OUT_DIR.mkdir(exist_ok=True)

BOT_FILES = {
    "searchbot":    BOT_DIR / "searchbot-scraper-for-search-index.json",
    "gptbot":       BOT_DIR / "gptbot-scraper-for-rl-and-evals.json",
    "chatgpt_user": BOT_DIR / "chatgpt-user-scraper-for-user-info.json",
}

IP_RE   = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IP16_RE = re.compile(r'"ip16":"(\d+\.\d+)"')

def load_networks():
    out = {}
    for name, path in BOT_FILES.items():
        d = json.loads(path.read_text())
        out[name] = [ipaddress.ip_network(p["ipv4Prefix"]) for p in d["prefixes"]]
    return out

def slash16_index(nets):
    """Return {"a.b" -> {role -> [cidr_str,...]}} covering every /16 an OAI CIDR touches."""
    idx = {}
    for role, cidrs in nets.items():
        for c in cidrs:
            first_a, first_b, *_ = c.network_address.packed
            last_a, last_b, *_   = c.broadcast_address.packed
            cur = (first_a, first_b)
            end = (last_a, last_b)
            while cur <= end:
                key = f"{cur[0]}.{cur[1]}"
                idx.setdefault(key, {}).setdefault(role, []).append(str(c))
                nb = cur[1] + 1
                cur = (cur[0] + 1, 0) if nb > 255 else (cur[0], nb)
    return idx

def classify_ip(ip_str, nets):
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return []
    roles = []
    for role, cidrs in nets.items():
        for c in cidrs:
            if ip in c:
                roles.append(role); break
    return roles

def list_jsonl_files():
    r = subprocess.run(
        ["find", str(ROOT), "-name", "*.jsonl", "-not", "-path", "*/.git/*",
         "-not", "-path", "*/node_modules/*"],
        capture_output=True, text=True, check=True,
    )
    return sorted(Path(p) for p in r.stdout.splitlines() if p)

def scan_full_ips(paths, nets):
    per_file = {}
    for p in paths:
        matched = defaultdict(lambda: {"count": 0, "roles": set()})
        try:
            with open(p, "rb") as f:
                for raw in f:
                    line = raw.decode("utf-8", "replace")
                    for ip in IP_RE.findall(line):
                        roles = classify_ip(ip, nets)
                        if roles:
                            matched[ip]["count"] += 1
                            matched[ip]["roles"].update(roles)
        except Exception as e:
            per_file[str(p)] = {"error": repr(e)}
            continue
        if matched:
            per_file[str(p)] = {
                "n_distinct_matched_ips": len(matched),
                "total_occurrences": sum(v["count"] for v in matched.values()),
                "ips": [
                    {"ip": ip, "occurrences": v["count"], "roles": sorted(v["roles"])}
                    for ip, v in sorted(matched.items(), key=lambda kv: (-kv[1]["count"], kv[0]))
                ],
            }
    return per_file

def scan_ip16(paths, slash16):
    per_file = {}
    for p in paths:
        ctr = Counter()
        try:
            with open(p, "rb") as f:
                for raw in f:
                    line = raw.decode("utf-8", "replace")
                    for ip16 in IP16_RE.findall(line):
                        ctr[ip16] += 1
        except Exception:
            continue
        if not ctr:
            continue
        hits = [(k, v) for k, v in ctr.items() if k in slash16]
        if hits:
            per_file[str(p)] = {
                "n_ip16_records": sum(ctr.values()),
                "n_distinct_ip16": len(ctr),
                "n_matching_distinct_ip16": len(hits),
                "n_matching_occurrences": sum(v for _, v in hits),
                "ip16_hits": [
                    {"ip16": k, "occurrences": v, "roles": sorted(slash16[k].keys())}
                    for k, v in sorted(hits, key=lambda kv: -kv[1])
                ],
            }
    return per_file

def main():
    nets = load_networks()
    slash16 = slash16_index(nets)
    paths = list_jsonl_files()

    full = scan_full_ips(paths, nets)
    ip16 = scan_ip16(paths, slash16)

    full_out = {
        "n_files_scanned": len(paths),
        "n_files_with_matches": sum(1 for v in full.values() if "n_distinct_matched_ips" in v),
        "files": [ {"path": p, **v} for p, v in sorted(full.items()) ],
    }
    ip16_out = {
        "n_files_scanned": len(paths),
        "n_files_with_corridor_hits": len(ip16),
        "files": sorted(
            [ {"path": p, **v} for p, v in ip16.items() ],
            key=lambda x: -x["n_matching_occurrences"],
        ),
    }
    (OUT_DIR / "full_ip_hits.json").write_text(json.dumps(full_out, indent=2))
    (OUT_DIR / "ip16_corridor_hits.json").write_text(json.dumps(ip16_out, indent=2))

    lines = []
    lines.append(f"# OAI-published IP range hits\n")
    lines.append(f"Scanned {len(paths)} jsonl files under `/collusionwiki/`.\n")
    lines.append(f"## Full-IP matches\n")
    lines.append(f"Files with at least one full IPv4 falling in an OAI CIDR: "
                 f"**{full_out['n_files_with_matches']}**.\n")
    if full_out["n_files_with_matches"] == 0:
        lines.append("No file contained any full IPv4 address that fell inside "
                     "the published searchbot, gptbot, or chatgpt-user ranges.\n")
    else:
        for f in full_out["files"]:
            if "n_distinct_matched_ips" not in f: continue
            lines.append(f"- `{f['path']}`: "
                         f"{f['n_distinct_matched_ips']} distinct IPs, "
                         f"{f['total_occurrences']} occurrences\n")
    lines.append(f"\n## ip16 corridor hits (first-two-octet-only)\n")
    lines.append("Many corpus files record only the first two octets of each IP "
                 "in an `ip16` field. The rows below list files where at least "
                 "one `ip16` value falls inside a /16 that hosts an OAI CIDR. "
                 "A row here is *not* a confirmed hit: only 1/65536 of any given "
                 "/16 is covered by the narrowest OAI /28. It marks a candidate "
                 "corridor only.\n")
    lines.append(f"Files with corridor hits: **{ip16_out['n_files_with_corridor_hits']}**.\n")
    lines.append("| file | ip16 records | distinct ip16 | matching distinct | matching records |\n")
    lines.append("|------|-------------:|--------------:|------------------:|-----------------:|\n")
    for f in ip16_out["files"]:
        lines.append(f"| `{f['path']}` | {f['n_ip16_records']} | "
                     f"{f['n_distinct_ip16']} | {f['n_matching_distinct_ip16']} | "
                     f"{f['n_matching_occurrences']} |\n")
    (OUT_DIR / "summary.md").write_text("".join(lines))

    print(f"scanned {len(paths)} files")
    print(f"  full-IP hits: {full_out['n_files_with_matches']} files")
    print(f"  ip16 corridor hits: {ip16_out['n_files_with_corridor_hits']} files")

if __name__ == "__main__":
    main()
