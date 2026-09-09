#!/usr/bin/env python3
"""Enumerate agent labels and co-editorship edges across every wiki export.

"A→B is a co-editorship edge iff there exists a page P and a revision r_B by B
at time t_B such that A wrote some revision on P at time t_A < t_B."

That is: A wrote first on P, B wrote later on the same P. A's write is
visible to any subsequent reader of P, so this is the loosest possible
one-way "A could have communicated with B via P" relation. Whether the two
labels actually addressed each other in prose is a downstream question,
handled by `classify.py`.

Follows `../agent-graph/extract.py` for corpus loading:
    - scans every `../../agent-logs/*/{labels,revisions}.jsonl`
    - dedupes revisions by `rev_id`, preferring the body-bearing row
    - filters labels to `len >= 6`, non-blank, non-redacted admin/user tags

Writes to `outputs/`:
    agents.jsonl   -- one row per label with edit counts and wiki/page reach
    comms.jsonl    -- one row per directed A→B edge with shared-page stats
    summary.txt    -- corpus scan + edge-count summary
"""
from __future__ import annotations
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
LOGS = REPO_ROOT / "agent-logs"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

MIN_HANDLE_LEN = 6
REDACTED_RE = re.compile(r"^\[(Person|Admin|User)\d+\]$")

# Labels confirmed (out-of-band) to be humans, not swarm agents. Their
# edits are spam cleanup / admin housekeeping and must not contribute
# to any per-agent or per-pair aggregation.
# `labels.jsonl.is_human_handle` only tags the pre-redacted `[Admin##]`
# style handles and does not cover these.
HUMAN_LABELS = frozenset({
    "MarkusLude",
})

# Cap the number of shared-page samples embedded per edge row.
# Pairs on the giant lobby pages (WillkommenImWiki, StartSeite) can share
# hundreds of pages; the classifier only needs a handful to make its call.
SHARED_PAGE_SAMPLE_CAP = 8

# Cap the number of family/cohort rows embedded per agent or per pair.
TOP_K_FAMILIES = 8
TOP_K_COHORTS = 8

# Which families count as "substantive tasks" vs mere infrastructure.
# An agent that touches >=2 substantive families is flagged as a probable
# name-collision (the same handle string being reused by different task
# runs). Infrastructure families -- lobby pages, relay/loop coordination,
# probe test pages, and the "we don't know" buckets -- are excluded
# because almost every agent touches at least one of them and doing so
# says nothing about task identity.
INFRA_FAMILY_PREFIXES = (
    "source-cache-url-list",
    "source-or-unclassified",
    "relay-coordination",
    "loop-chain-infrastructure",
    "probe-test",
    "off_store_unclassified",
    "unknown",
)


def is_substantive_family(fam):
    if not fam:
        return False
    if fam in INFRA_FAMILY_PREFIXES:
        return False
    return True


def iter_wiki_dirs():
    for p in sorted(LOGS.iterdir()):
        if p.is_dir() and (p / "labels.jsonl").exists() and (p / "revisions.jsonl").exists():
            yield p


def load_handle_set():
    handles = set()
    per_wiki = Counter()
    for d in iter_wiki_dirs():
        with (d / "labels.jsonl").open() as f:
            for line in f:
                row = json.loads(line)
                label = (row.get("label") or "").strip()
                if not label or len(label) < MIN_HANDLE_LEN:
                    continue
                if REDACTED_RE.match(label):
                    continue
                if label in HUMAN_LABELS:
                    continue
                handles.add(label)
                per_wiki[d.name] += 1
    return handles, per_wiki


def load_page_families():
    """Return page_id -> (family, cohort). Prowiki is the only wiki with real
    classifications; other wikis' pages map to (None, None)."""
    fam = {}
    for d in iter_wiki_dirs():
        pp = d / "pages.jsonl"
        if not pp.exists():
            continue
        with pp.open() as f:
            for line in f:
                row = json.loads(line)
                pid = row.get("page_id")
                if not pid:
                    continue
                f_val = row.get("page_family")
                if f_val in ("off_store_unclassified", None):
                    f_val = None
                c_val = row.get("page_family_cohort") or None
                # Later exports override earlier only if they carry a
                # non-null family (prowiki wins over the standalone dse
                # scrape which has None).
                if pid in fam and fam[pid][0] and not f_val:
                    continue
                fam[pid] = (f_val, c_val)
    return fam


def collect_best_rows():
    """Pick the body-bearing row per rev_id across overlapping exports."""
    best = {}
    seen_sources = defaultdict(Counter)
    for d in iter_wiki_dirs():
        with (d / "revisions.jsonl").open() as f:
            for line in f:
                rev = json.loads(line)
                rid = rev.get("rev_id")
                if not rid:
                    continue
                wiki = rev.get("wiki", d.name)
                seen_sources[wiki][d.name] += 1
                if rid in best:
                    incumbent = best[rid][1]
                    if incumbent.get("body") or not rev.get("body"):
                        continue
                best[rid] = (d.name, rev)
    return best, seen_sources


def build(handles):
    best, seen_sources = collect_best_rows()
    families = load_page_families()

    # Per-page revision list, chronological.
    #   page_id -> list of (time_str, label, rev_id)
    page_revs = defaultdict(list)
    # Per-label edit stats.
    per_label_revs = Counter()
    per_label_pages = defaultdict(set)
    per_label_wikis = defaultdict(set)
    per_label_families = defaultdict(Counter)   # label -> Counter(family -> n_pages)
    per_label_cohorts = defaultdict(Counter)    # label -> Counter(cohort -> n_pages)
    per_wiki_unique = Counter()
    per_wiki_kept = Counter()

    seen_label_page = set()  # to count each (label, page) once for family stats

    for rid, (_src, rev) in best.items():
        wiki = rev.get("wiki") or ""
        per_wiki_unique[wiki] += 1
        label = (rev.get("label") or "").strip()
        if label not in handles:
            continue
        page_id = rev.get("page_id")
        if not page_id:
            continue
        t = rev.get("time") or ""
        per_wiki_kept[wiki] += 1
        page_revs[page_id].append((t, label, rid))
        per_label_revs[label] += 1
        per_label_pages[label].add(page_id)
        per_label_wikis[label].add(wiki)
        if (label, page_id) not in seen_label_page:
            seen_label_page.add((label, page_id))
            fam, cohort = families.get(page_id, (None, None))
            if fam:
                per_label_families[label][fam] += 1
            if cohort:
                per_label_cohorts[label][cohort] += 1
    del seen_label_page

    # For each page, sort chronologically. For each revision r_B, every
    # distinct earlier author A on P yields a directed edge A→B.
    #
    # Track per-edge:
    #   n_shared_pages -- distinct pages where edge fires at least once
    #   n_encounters   -- total (A,B) triggers across all pages
    #   sample_pages   -- up to SHARED_PAGE_SAMPLE_CAP pages, with the
    #                     earliest-triggering (a_time, b_time, a_rev, b_rev)
    #   first_seen     -- earliest overall (page, a_time, b_time)
    edges = defaultdict(lambda: {
        "n_shared_pages": 0,
        "n_encounters": 0,
        "samples": {},  # page_id -> first-trigger dict
        "first": None,
        "families": Counter(),  # family -> shared-page count
        "cohorts": Counter(),   # cohort -> shared-page count
    })

    for page_id, revs in page_revs.items():
        revs.sort(key=lambda r: (r[0], r[2]))
        page_fam, page_cohort = families.get(page_id, (None, None))
        earlier_authors = {}  # label -> (first_time, first_rev_id)
        for t_b, label_b, rid_b in revs:
            for label_a, (t_a, rid_a) in earlier_authors.items():
                if label_a == label_b:
                    continue
                key = (label_a, label_b)
                e = edges[key]
                e["n_encounters"] += 1
                if page_id not in e["samples"]:
                    e["n_shared_pages"] += 1
                    e["samples"][page_id] = {
                        "page_id": page_id,
                        "a_time": t_a,
                        "a_rev": rid_a,
                        "b_time": t_b,
                        "b_rev": rid_b,
                    }
                    if page_fam:
                        e["families"][page_fam] += 1
                    if page_cohort:
                        e["cohorts"][page_cohort] += 1
                    trig = (t_b, page_id)
                    if e["first"] is None or trig < (e["first"]["b_time"], e["first"]["page_id"]):
                        e["first"] = {
                            "page_id": page_id,
                            "a_time": t_a,
                            "a_rev": rid_a,
                            "b_time": t_b,
                            "b_rev": rid_b,
                        }
            if label_b not in earlier_authors:
                earlier_authors[label_b] = (t_b, rid_b)

    # agents.jsonl -- deterministic order by label
    def _topk(counter, k):
        return [{"name": n, "n_pages": c} for n, c in counter.most_common(k)]

    agents_rows = []
    n_collisions = 0
    for label in sorted(handles):
        n_revs = per_label_revs.get(label, 0)
        fam_counter = per_label_families.get(label, Counter())
        coh_counter = per_label_cohorts.get(label, Counter())
        substantive = sorted(f for f in fam_counter if is_substantive_family(f))
        is_collision = len(substantive) >= 2
        if is_collision:
            n_collisions += 1
        agents_rows.append({
            "label": label,
            "n_revs": n_revs,
            "n_pages": len(per_label_pages.get(label, set())),
            "wikis": sorted(per_label_wikis.get(label, set())),
            "families": _topk(fam_counter, TOP_K_FAMILIES),
            "cohorts": _topk(coh_counter, TOP_K_COHORTS),
            "n_substantive_families": len(substantive),
            "substantive_families": substantive,
            "is_probable_name_collision": is_collision,
        })
    with (OUT / "agents.jsonl").open("w") as fh:
        for row in agents_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # comms.jsonl -- sort by (-n_shared_pages, from, to) for browsability
    comms_rows = []
    for (a, b), e in edges.items():
        # Trim samples to cap, keeping earliest by b_time.
        samples_sorted = sorted(e["samples"].values(), key=lambda s: (s["b_time"], s["page_id"]))
        samples = samples_sorted[:SHARED_PAGE_SAMPLE_CAP]
        fam_top = _topk(e["families"], TOP_K_FAMILIES)
        coh_top = _topk(e["cohorts"], TOP_K_COHORTS)
        dominant = fam_top[0]["name"] if fam_top else None
        comms_rows.append({
            "from": a,
            "to": b,
            "n_shared_pages": e["n_shared_pages"],
            "n_encounters": e["n_encounters"],
            "first_seen": e["first"],
            "sample_pages": samples,
            "shared_families": fam_top,
            "shared_cohorts": coh_top,
            "dominant_family": dominant,
        })
    comms_rows.sort(key=lambda r: (-r["n_shared_pages"], r["from"], r["to"]))
    with (OUT / "comms.jsonl").open("w") as fh:
        for row in comms_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "n_handles": len(handles),
        "n_agents_rows": len(agents_rows),
        "n_agents_with_revs": sum(1 for r in agents_rows if r["n_revs"] > 0),
        "n_directed_edges": len(comms_rows),
        "n_undirected_pairs": len({tuple(sorted(k)) for k in edges}),
        "n_pages_with_kept_revs": len(page_revs),
        "n_pages_with_family": sum(1 for pid in page_revs if families.get(pid, (None, None))[0]),
        "n_agents_with_collision": n_collisions,
        "per_wiki_unique": per_wiki_unique,
        "per_wiki_kept": per_wiki_kept,
        "per_wiki_sources": seen_sources,
        "total_encounters": sum(e["n_encounters"] for e in edges.values()),
    }


def main():
    handles, per_wiki_handles = load_handle_set()
    print(f"handle set: {len(handles)} from {len(per_wiki_handles)} wikis")
    stats = build(handles)

    lines = []
    lines.append("agent-comms: per-wiki scan (dedup by rev_id, body-bearing row preferred):")
    kept = stats["per_wiki_kept"]
    uniq = stats["per_wiki_unique"]
    for w in sorted(set(uniq) | set(kept)):
        srcs = stats["per_wiki_sources"].get(w, {})
        src_str = ",".join(f"{k}:{v}" for k, v in sorted(srcs.items()))
        lines.append(
            f"  {w:20s} unique={uniq.get(w, 0):6d}  kept={kept.get(w, 0):6d}  "
            f"sources={{{src_str}}}"
        )
    lines.append("")
    lines.append(f"agents rows (handles in filtered set): {stats['n_agents_rows']}")
    lines.append(f"  of which have >=1 kept revision: {stats['n_agents_with_revs']}")
    lines.append(f"  of which are probable name collisions (>=2 substantive families): {stats['n_agents_with_collision']}")
    lines.append(f"pages with >=1 kept revision: {stats['n_pages_with_kept_revs']}")
    lines.append(f"  of which have a real page_family classification: {stats['n_pages_with_family']}")
    lines.append(f"total co-editor encounters (page-level A→B triggers): {stats['total_encounters']}")
    lines.append(f"unique directed A→B edges: {stats['n_directed_edges']}")
    lines.append(f"unique undirected pairs {{A,B}}: {stats['n_undirected_pairs']}")
    text = "\n".join(lines) + "\n"
    (OUT / "summary.txt").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
