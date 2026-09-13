"""Find hub→slot batch patterns in the dse wiki.

A hub→slot batch is a single revision whose body links to a batch of pages
that share a naming stem plus an enumerated suffix, where at the time of the
revision none of the linked pages have been created yet.

Source: /collusionwiki/agent-logs/prowiki/revisions.jsonl (wiki=dse subset).
The prowiki cut is the only one with revision bodies, so links can only be
extracted from that window (2026-05-24 to 2026-07-02).

Method:
1. Load every dse revision. Record the earliest `write_date` per page name
   as the page's first-observed creation.
2. For every revision with a body, extract targets from
   `wikiservice.at/dse/wiki.cgi?...id=<Name>` link URLs. Drop self-links.
3. Cluster each revision's link targets by shared prefix (>=6 chars, >=3
   targets per cluster). Keep clusters whose suffixes look enumerated:
   all-digit runs, or all-letter runs, or short (<=6 char) mixed suffixes.
4. For each cluster, count how many targets are "forward" at the revision's
   time: target's first-observed write happens strictly later, or target is
   never observed at all. A cluster is a hub-slot batch if >=3 targets are
   forward and >=1 of them is later created by a label distinct from the
   hub-revision's label.
5. Deduplicate to one row per (source_page, prefix) — the earliest revision
   where the batch first appears in the source page's body.

Outputs:
- outputs/hub_slot_batches.jsonl — one row per (source_page, prefix) match.
- outputs/report.txt — human-readable narrative of the matches.
"""
import json
import re
from collections import defaultdict
from datetime import datetime

PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"
OUT_JSON = "/collusionwiki/analyses/hub-slot-batches/outputs/hub_slot_batches.jsonl"
OUT_TXT = "/collusionwiki/analyses/hub-slot-batches/outputs/report.txt"

WIKI_CGI_ID = re.compile(
    r"wikiservice\.at/dse/wiki\.cgi\?[^\s\]]*?\bid=([A-Za-z0-9_/\-]+)"
)

MIN_PREFIX = 6
MIN_CLUSTER = 3
MIN_FORWARD = 3


def parse(ts):
    return datetime.fromisoformat(ts)


def common_prefix(strs):
    if not strs:
        return ""
    p = strs[0]
    for s in strs[1:]:
        while not s.startswith(p):
            p = p[:-1]
            if not p:
                return ""
    return p


def cluster_targets(targets, min_prefix, min_group):
    """Group targets by shared prefix. Greedy: each target attaches to the
    first seed target that shares a >=min_prefix common prefix."""
    targets = sorted(set(targets))
    clusters = []
    used = set()
    for i, t in enumerate(targets):
        if t in used:
            continue
        cluster = [t]
        for u in targets:
            if u in used or u == t:
                continue
            if len(common_prefix([t, u])) >= min_prefix:
                cluster.append(u)
        cp = common_prefix(cluster)
        if len(cluster) >= min_group and len(cp) >= min_prefix:
            clusters.append((cp, cluster))
            used.update(cluster)
    return clusters


def common_suffix(strs):
    """Longest common suffix across all strings."""
    if not strs:
        return ""
    p = strs[0]
    for s in strs[1:]:
        while not s.endswith(p):
            p = p[1:]
            if not p:
                return ""
    return p


def is_enumerated(prefix, cluster):
    """True if the suffixes past `prefix` look like a coordinated batch.

    Four shapes admit a cluster as enumerated:
    1. All suffixes match `[_-]?\d+` — digit slot IDs like `_01, _02`.
    2. All suffixes are short (<=6 chars) alphanumeric — letter slots
       like `Alpha, Beta, Gamma, Delta, ALL`.
    3. All slot names share both a non-trivial common prefix (already
       ensured) AND a common trailing substring of >=3 chars — e.g.
       `AgentNext{Conv,Filter,Raw,Sec}JuneA{B,C,D,E}` share `June` in the
       middle and letter-pair variation at the tail.
    4. All suffixes have the same length AND some run of >=3 characters
       matches across every suffix at the same offset.
    """
    suffixes = [t[len(prefix):] for t in cluster]
    if all(re.fullmatch(r"[_\-]?\d+", s) for s in suffixes):
        return True
    if all(len(s) <= 6 and re.fullmatch(r"[A-Za-z0-9]+", s) for s in suffixes):
        return True
    tail = common_suffix(cluster)
    if len(tail) >= 3 and len(tail) < min(len(t) - len(prefix) for t in cluster):
        return True
    from difflib import SequenceMatcher
    if len(suffixes) >= 3:
        shared = None
        for i in range(1, len(suffixes)):
            sm = SequenceMatcher(None, suffixes[0], suffixes[i])
            m = sm.find_longest_match(0, len(suffixes[0]), 0, len(suffixes[i]))
            piece = suffixes[0][m.a:m.a + m.size]
            if shared is None:
                shared = piece
            else:
                sm2 = SequenceMatcher(None, shared, piece)
                m2 = sm2.find_longest_match(0, len(shared), 0, len(piece))
                shared = shared[m2.a:m2.a + m2.size]
        if shared and len(shared) >= 3:
            return True
    lengths = {len(s) for s in suffixes}
    if len(lengths) == 1:
        L = lengths.pop()
        max_run = 0
        i = 0
        while i < L:
            j = i
            while j < L and len({s[j] for s in suffixes}) == 1:
                j += 1
            max_run = max(max_run, j - i)
            i = j + 1 if j == i else j
        if max_run >= 3:
            return True
    return False


def load_dse():
    rev_by_id = {}
    first_by_name = {}
    with open(PROWIKI) as f:
        for line in f:
            r = json.loads(line)
            if r.get("wiki") != "dse":
                continue
            t = r.get("write_date") or r.get("time")
            if not t:
                continue
            r["_t"] = parse(t)
            rev_by_id[r["rev_id"]] = r
            name = r["name"]
            if name not in first_by_name or r["_t"] < first_by_name[name][0]:
                first_by_name[name] = (r["_t"], r["rev_id"], r.get("label"), r.get("ip16"))
    return rev_by_id, first_by_name


def main():
    rev_by_id, first_by_name = load_dse()

    # For each (source_page, prefix), track the earliest revision where the
    # batch cluster appears with all cluster members forward-linked at that
    # revision's time.
    earliest_batch = {}

    for r in rev_by_id.values():
        body = r.get("body")
        if not body:
            continue
        source = r["name"]
        targets = [t for t in set(WIKI_CGI_ID.findall(body)) if t != source]
        if len(targets) < MIN_CLUSTER:
            continue
        for prefix, cluster in cluster_targets(targets, MIN_PREFIX, MIN_CLUSTER):
            if not is_enumerated(prefix, cluster):
                continue
            n_forward = 0
            n_never = 0
            creators = set()
            slot_rows = []
            for tgt in cluster:
                first = first_by_name.get(tgt)
                if first is None:
                    n_forward += 1
                    n_never += 1
                    slot_rows.append({
                        "target": tgt, "first_time": None, "first_label": None,
                        "first_ip16": None, "forward": True, "gap_s": None,
                    })
                    continue
                ft, fr, fl, fip = first
                forward = ft > r["_t"]
                slot_rows.append({
                    "target": tgt, "first_time": ft.isoformat(),
                    "first_rev": fr, "first_label": fl, "first_ip16": fip,
                    "forward": forward,
                    "gap_s": (ft - r["_t"]).total_seconds(),
                })
                if forward:
                    n_forward += 1
                    if fl:
                        creators.add(fl)
            if n_forward < MIN_FORWARD:
                continue
            other_label_creators = sorted(l for l in creators if l != r.get("label"))
            if not other_label_creators and (n_forward - n_never) > 0:
                # If any slot got created but only by the hub's own label,
                # this isn't the "different agents fill slots" pattern.
                # Keep only if no slots were created — that's still a hub
                # batch just with abandoned slots.
                if n_never != n_forward:
                    continue
            row = {
                "source_page": source,
                "hub_revision": r["rev_id"],
                "hub_time": r["_t"].isoformat(),
                "hub_label": r.get("label"),
                "hub_ip16": r.get("ip16"),
                "prefix": prefix,
                "n_cluster": len(cluster),
                "n_forward": n_forward,
                "n_never": n_never,
                "n_created_by_other_labels": len(other_label_creators),
                "other_label_creators": other_label_creators,
                "slots": slot_rows,
            }
            key = (source, prefix)
            existing = earliest_batch.get(key)
            if existing is None or row["hub_time"] < existing["hub_time"]:
                earliest_batch[key] = row

    rows = sorted(
        earliest_batch.values(),
        key=lambda x: (-x["n_forward"], -x["n_cluster"], x["hub_time"]),
    )

    with open(OUT_JSON, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    # Human report.
    with open(OUT_TXT, "w") as f:
        f.write(f"Total hub→slot batches found: {len(rows)}\n")
        f.write(f"  parameters: MIN_PREFIX={MIN_PREFIX} MIN_CLUSTER={MIN_CLUSTER} MIN_FORWARD={MIN_FORWARD}\n\n")

        # Group by prefix in case multiple hub pages announce the same batch.
        by_prefix = defaultdict(list)
        for row in rows:
            by_prefix[row["prefix"]].append(row)

        for prefix, group in sorted(by_prefix.items(), key=lambda kv: -max(r["n_forward"] for r in kv[1])):
            f.write("=" * 78 + "\n")
            f.write(f"SLOT BATCH: prefix={prefix!r}\n")
            n_hubs = len(group)
            f.write(f"  {n_hubs} hub revision{'s' if n_hubs != 1 else ''}\n")
            slots_ever_seen = {s["target"]: s for row in group for s in row["slots"]}
            n_created = sum(1 for s in slots_ever_seen.values() if s["first_time"])
            n_total = len(slots_ever_seen)
            f.write(f"  {n_total} distinct slot targets across all hubs\n")
            f.write(f"  {n_created} of {n_total} slot targets got created within prowiki window\n\n")

            for row in sorted(group, key=lambda r: r["hub_time"]):
                f.write(f"  HUB {row['source_page']} @ rev {row['hub_revision']}\n")
                f.write(f"      time  : {row['hub_time']}\n")
                f.write(f"      label : {row['hub_label']} (ip16 {row['hub_ip16']})\n")
                f.write(f"      cluster size (in this hub): {row['n_cluster']}\n")
                f.write(f"      forward slots at hub time  : {row['n_forward']}\n")
                f.write(f"      never observed              : {row['n_never']}\n")
                f.write(f"      other-label slot creators   : {row['other_label_creators']}\n")
                f.write("      slots:\n")
                for s in sorted(row["slots"], key=lambda x: x["target"]):
                    if s["first_time"] is None:
                        tag = "NEVER"
                        detail = "never observed"
                    else:
                        tag = "FWD" if s["forward"] else "PRE"
                        detail = f"first@{s['first_time']} ({s['first_label']}) gap={s['gap_s']}s"
                    f.write(f"        [{tag}] {s['target']:<52} {detail}\n")
                f.write("\n")

    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_TXT}")
    print(f"{len(rows)} hub-slot batch rows")


if __name__ == "__main__":
    main()
