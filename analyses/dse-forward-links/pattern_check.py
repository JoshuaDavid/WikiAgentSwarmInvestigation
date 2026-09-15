"""Grep-level tests for the "expected but unconfirmed" coordination patterns.

Tests:
1. Timestamp-encoded page names: dse page names ending in a 10-digit
   number that decodes to a plausible 2026 Unix second.
2. Chunked continuation: page names matching <prefix><digits>, with
   siblings <prefix><digits+1> etc. (numeric suffix, same prefix).
3. Counter/beacon hosts in bodies (counterapi, hits, view, pixel, ...).
4. Cross-wiki name mirroring: dse pages whose exact name also exists on
   any other wiki in agent-logs.
5. Deletion-as-signal: swarm-labelled deletions in dse (label != known
   admins), and their temporal density relative to swarm answer bursts.
"""
import json
import re
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

DSE_PAGES = "/collusionwiki/agent-logs/dse/pages.jsonl"
DSE_REVS = "/collusionwiki/agent-logs/dse/revisions.jsonl"
PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"
AGENT_LOGS = "/collusionwiki/agent-logs"

URL_RE = re.compile(r'https?://[^\s\]"\)]+')
KNOWN_ADMINS = {"MarkusLude"}


def parse(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def load_dse_pages():
    names = []
    with open(DSE_PAGES) as f:
        for line in f:
            names.append(json.loads(line)["name"])
    return names


def timestamp_names():
    names = load_dse_pages()
    ten_digit = re.compile(r"(\d{10})")
    epoch_2026_start = 1767225600  # 2026-01-01 UTC
    epoch_2027_start = 1798761600  # 2027-01-01 UTC
    hits = []
    for n in names:
        for m in ten_digit.findall(n):
            ts = int(m)
            if epoch_2026_start <= ts < epoch_2027_start:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                hits.append((n, m, dt.isoformat()))
                break
    print(f"=== 1. Timestamp-encoded page names ===")
    print(f"total dse pages: {len(names)}")
    print(f"pages with 10-digit substring decoding to 2026 UTC: {len(hits)}")
    for h in hits[:15]:
        print(f"  {h[0]:<50}  ts={h[1]}  ->  {h[2]}")
    if len(hits) > 15:
        print(f"  ... and {len(hits) - 15} more")
    # Also try milliseconds (13 digits) and 8-digit truncated forms.
    ms_re = re.compile(r"(\d{13})")
    ms_hits = []
    for n in names:
        for m in ms_re.findall(n):
            ts = int(m) // 1000
            if epoch_2026_start <= ts < epoch_2027_start:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                ms_hits.append((n, m, dt.isoformat()))
                break
    print(f"pages with 13-digit ms-timestamp substring: {len(ms_hits)}")
    for h in ms_hits[:10]:
        print(f"  {h[0]:<50}  {h[1]}  ->  {h[2]}")
    print()


def chunked_continuation():
    names = load_dse_pages()
    # Group by (prefix, numeric-suffix length) where the tail is digits.
    tail = re.compile(r"^(.*?)(\d+)$")
    groups = defaultdict(list)
    for n in names:
        m = tail.match(n)
        if not m:
            continue
        prefix, num = m.group(1), int(m.group(2))
        if prefix and len(prefix) >= 6:  # skip short prefixes -> noise
            groups[prefix].append(num)
    # Keep groups whose numeric suffixes form a contiguous or near-contiguous
    # run (>=3 members and >=50% of the range covered).
    chains = []
    for prefix, nums in groups.items():
        nums = sorted(set(nums))
        if len(nums) < 3:
            continue
        span = nums[-1] - nums[0]
        if span == 0:
            continue
        density = len(nums) / (span + 1)
        if density >= 0.5 and len(nums) >= 3:
            chains.append((prefix, nums, density))
    chains.sort(key=lambda c: (-len(c[1]), c[0]))
    print("=== 2. Chunked continuation (same prefix + numeric suffix run) ===")
    print(f"candidate chain-groups found: {len(chains)}")
    for prefix, nums, density in chains[:15]:
        rng = f"[{nums[0]}..{nums[-1]}]" if len(nums) > 1 else str(nums[0])
        print(f"  {prefix}<N>   count={len(nums)}  {rng}  density={density:.2f}")
        print(f"    e.g.  {prefix}{nums[0]}, {prefix}{nums[1]}, {prefix}{nums[-1]}")
    if len(chains) > 15:
        print(f"  ... and {len(chains) - 15} more")
    print()


def counter_hosts():
    hosts = Counter()
    examples = defaultdict(list)
    with open(PROWIKI) as f:
        for line in f:
            r = json.loads(line)
            if r.get("wiki") != "dse":
                continue
            body = r.get("body") or ""
            for u in URL_RE.findall(body):
                if "wikiservice.at" in u:
                    continue
                try:
                    h = urlparse(u).hostname
                except Exception:
                    continue
                if not h:
                    continue
                if re.search(r"(counter|hits?\.|pixel|beacon|hit-counter|counterapi"
                             r"|view-counter|counter-api|ping)", h):
                    hosts[h] += 1
                    if len(examples[h]) < 3:
                        examples[h].append((r["name"], r["rev_id"], u[:120]))
    print("=== 3. Counter/beacon hosts ===")
    if not hosts:
        print("  no counter-shaped hosts in dse bodies")
    for h, n in hosts.most_common():
        print(f"  {h}   used {n}x")
        for ex in examples[h]:
            print(f"    {ex[0]:<40}  {ex[1]}")
            print(f"    {ex[2]}")
    print()


def cross_wiki_mirror():
    dse = set(load_dse_pages())
    hits = defaultdict(set)  # name -> set of other wikis
    # prowiki is a differently-cut scrape of the same host, so it isn't a
    # real "other wiki" for the mirror test.
    SKIP = {"dse", "prowiki"}
    for entry in os.listdir(AGENT_LOGS):
        if entry in SKIP:
            continue
        path = os.path.join(AGENT_LOGS, entry, "pages.jsonl")
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                for line in f:
                    obj = json.loads(line)
                    n = obj.get("name")
                    if n in dse:
                        hits[n].add(entry)
        except Exception:
            continue
    print("=== 4. Cross-wiki name mirroring ===")
    print(f"dse pages whose exact name appears in another wiki dataset: "
          f"{len(hits)}")
    for name, wikis in sorted(hits.items())[:30]:
        print(f"  {name:<45}  also in: {sorted(wikis)}")
    if len(hits) > 30:
        print(f"  ... and {len(hits) - 30} more")
    print()


def deletion_signals():
    dels_by_hour = Counter()
    writes_by_hour = Counter()
    del_labels = Counter()
    with open(DSE_REVS) as f:
        for line in f:
            r = json.loads(line)
            summary = (r.get("change_summary") or "")
            t = parse(r["time"])
            hour = t.replace(minute=0, second=0, microsecond=0).isoformat()
            if "gelöscht" in summary:
                dels_by_hour[hour] += 1
                del_labels[r.get("label")] += 1
            else:
                writes_by_hour[hour] += 1
    print("=== 5. Deletion-as-signal ===")
    print(f"total delete events: {sum(dels_by_hour.values())}")
    print("deletions by editor label (top 10):")
    for lbl, n in del_labels.most_common(10):
        print(f"  {n:>5}  {lbl}")
    # Non-admin deletions
    non_admin = {k: v for k, v in del_labels.items() if k not in KNOWN_ADMINS}
    print(f"non-MarkusLude deletion events: {sum(non_admin.values())}")
    # Hours where deletions >5 and coincide with write bursts
    print()
    print("hours with >=5 deletions, sorted by deletion count:")
    for hour, n in sorted(dels_by_hour.items(), key=lambda kv: -kv[1])[:10]:
        writes = writes_by_hour.get(hour, 0)
        print(f"  {hour}  deletes={n:>4}  writes(same-hour)={writes}")
    print()


if __name__ == "__main__":
    timestamp_names()
    chunked_continuation()
    counter_hosts()
    cross_wiki_mirror()
    deletion_signals()
