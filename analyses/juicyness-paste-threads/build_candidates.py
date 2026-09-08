#!/usr/bin/env python3
"""Cluster paste-host revisions into thread candidates.

The unit of analysis in this pass is a **thread**, not a single paste. A
thread is a set of pastes that reference each other via shared titles,
`@handle` mentions, `paste <shortid>` body references, or `title X` /
`under X` body references, and that fall within a bounded time span.

Reads   agent-logs/paste-<host>/revisions.jsonl for each host in HOSTS.
Writes  outputs/candidates.jsonl (one JSON per cluster).
"""

from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "agent-logs"
OUT = Path(__file__).resolve().parent / "outputs" / "candidates.jsonl"

# Per-host dirs are the canonical import for each paste site. `pastes` is a
# separate shellac-pack import that contains rows for several sub-hosts;
# where a per-host dir exists (linuxiarz, pastebin-k4be, paste.steamr.com,
# pastebin.tarcseh.me, paste.smirky.net, pastebin.faster-it.de) the per-host
# dir is used and the shellac rows for that sub-host are skipped, to avoid
# clustering the same paste twice.
HOSTS = [
    "paste-linuxiarz",
    "pastebin-k4be",
    "paste.steamr.com",
    "pastebin.tarcseh.me",
    "pastebin.freepbx.org",
    "paste.lightcast.com",
    "paste.smirky.net",
    "pastebin.faster-it.de",
    "pastes",  # covers anna-fyi, pb.dynavirt.com, nervesocket.com, p.gaa.st
]

SHELLAC_HOST_SKIP = {
    "linuxiarz",
    "pastebin-k4be",
    "paste.steamr.com",
    "pastebin.tarcseh.me",
    "paste.smirky.net",
    "pastebin.faster-it.de",
}

MIN_BODY_LEN = 30
MIN_CLUSTER_SIZE = 5
MIN_CLUSTER_LABELS = 3
MAX_INTER_PASTE_GAP_HOURS = 4
HOT_TITLE_MIN_COUNT = 3
MIN_PREFIX_LEN = 2
# Localized default paste-site titles. Each host defaults its "Untitled"
# label to the site's own language; the first ASCII word of that default
# ends up here so it never seeds a hot cluster. Entries cover both the
# first-word extract from title_prefix() and the 4-char coarse form from
# coarse_topic().
STOP_TITLE_WORDS = {
    "untitled", "unti",  # English default (paste-linuxiarz)
    "filler",
    "test",
    "re",
    "bez", "bezt",       # Polish "Bez tytułu" (pastebin-k4be)
    "n", "nvte",         # Hungarian "Névtelen" (pastebin.tarcseh.me)
    "",
}
# Full-title stop list, used to keep the exact-title edge from creating a
# false cluster of unrelated pastes that all use the site default.
STOP_TITLES_EXACT = {
    "Untitled",
    "Bez tytułu",
    "Névtelen",
    "test",
}

AT_RE = re.compile(r"@(agent[-\w]+)", re.I)
PASTE_ID_RE = re.compile(r"paste[- ]([0-9a-f]{6,12})", re.I)
# `Re: <shortid>` — used on paste-linuxiarz to reply to an existing paste
# by its slug. External AI agent responses (e.g. Perceptual Zephyr) use
# this form as their coordination anchor, so we cluster on it too.
TITLE_REPLY_ID_RE = re.compile(r"Re:\s+([0-9a-f]{6,12})", re.I)
TITLE_REF_RE = re.compile(
    r"(?:title|under|reply title|search title)\s+([A-Z][A-Za-z0-9]{4,})",
)
TITLE_PREFIX_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]*)")


class UnionFind:
    def __init__(self, keys):
        self.p = {k: k for k in keys}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def _title_of(r):
    """Read the paste title from whichever field the host uses."""
    return r.get("source_title") or r.get("shellac_title") or ""


def _wb_ts_to_iso(ts):
    """Convert a Wayback Machine timestamp like `20260904181427` to ISO
    `2026-09-04T18:14:27+00:00`. Returns None on any parse failure."""
    if not ts or len(ts) < 14:
        return None
    try:
        return (
            f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}T"
            f"{ts[8:10]}:{ts[10:12]}:{ts[12:14]}+00:00"
        )
    except Exception:
        return None


# Swarm agents self-time their pastes with a `ts=<unix_time>` line at the
# end of the body. This is a stronger signal than the Wayback capture
# time (which reflects archival, not authorship). Prefer this when
# present.
BODY_TS_RE = re.compile(r"\bts=(\d{9,11})(?:\.\d+)?\b")


def _body_ts_to_iso(body):
    if not body:
        return None
    m = BODY_TS_RE.search(body)
    if not m:
        return None
    try:
        import datetime as dt
        return dt.datetime.fromtimestamp(int(m.group(1)), tz=dt.timezone.utc).isoformat()
    except Exception:
        return None


def load_host(host):
    p = LOG_DIR / host / "revisions.jsonl"
    rows = [json.loads(l) for l in p.read_text().splitlines() if l]
    if host == "pastes":
        # Skip sub-hosts that have their own per-host dir. The shellac page_id
        # is `pastes/<subhost>/<slug>`; e.g. `pastes/linuxiarz/029d7b71`.
        def keep(r):
            pid = r.get("page_id") or ""
            parts = pid.split("/", 2)
            if len(parts) >= 2 and parts[1] in SHELLAC_HOST_SKIP:
                return False
            return True
        rows = [r for r in rows if keep(r)]
    for r in rows:
        # Backfill a source_title field from shellac_title so downstream code
        # can read one field.
        if not r.get("source_title") and r.get("shellac_title"):
            r["source_title"] = r["shellac_title"]
        # Fill missing `time` from strongest available signal:
        #   1. Body `ts=<unix>` — swarm-agent self-timing convention.
        #   2. Wayback capture timestamp — upper bound on write time.
        # Body ts is preferred because it reflects authorship, not
        # archival. Wayback-only pastes (e.g. the Perceptual Zephyr /
        # CentaurAgent thecolony.ai invitations, which carry no
        # site-native timestamp and no body-embedded ts) fall through to
        # wb_timestamp and land in the correct 2026-09-04 window.
        if not r.get("time"):
            iso = _body_ts_to_iso(r.get("body") or "")
            if iso:
                r["time"] = iso
                r["time_grade"] = "body_ts_field"
        if not r.get("time") and r.get("wb_timestamp"):
            iso = _wb_ts_to_iso(r["wb_timestamp"])
            if iso:
                r["time"] = iso
                r["time_grade"] = f"wb_capture:{r['wb_timestamp']}"
    return rows


def keep_paste(r):
    body = r.get("body") or ""
    title = r.get("source_title") or ""
    if r.get("time") and len(body) >= MIN_BODY_LEN:
        return True
    if AT_RE.search(body):
        return True
    # Reply-style title with an embedded paste-id — external agents (e.g.
    # Perceptual Zephyr from Nous Research) use this form as an anchor
    # instead of a body @-handle. These pastes usually carry no timestamp.
    if TITLE_REPLY_ID_RE.search(title):
        return True
    return False


def title_prefix(title):
    m = TITLE_PREFIX_RE.match(title or "")
    if not m:
        return None
    w = m.group(1)
    if len(w) < MIN_PREFIX_LEN:
        return None
    if w.lower() in STOP_TITLE_WORDS:
        return None
    return w


def cluster(rows):
    """Return list[list[row]] of clusters.

    Edges:
    1. Same hot title prefix.
    2. Same exact source_title (any repeat).
    3. Body of paste A contains `@<label>` where label == label of paste B.
    4. Body of paste A contains a short paste-id that matches paste B's name.
    5. Body of paste A contains "title X" or "under X" where X == title of B.
    """
    kept = [r for r in rows if keep_paste(r)]
    ids = [r["page_id"] for r in kept]
    by_id = {r["page_id"]: r for r in kept}
    uf = UnionFind(ids)

    # --- edge type 1 + 2: title prefix / exact title / coarse topic word ---
    # We want two granularities:
    #  a) The full first alpha-word ("IowaCollabReply"). Merges obvious sibs.
    #  b) The first 4 alphabetical characters of the title, case-insensitive
    #     ("iowa"). Merges follow-up titles like `IowaQ5LabelConfirmed` or
    #     `IowaPostFinalThanks` that appear after the initial coordination
    #     titles have run their course.
    # Both are gated on hotness so single-off titles don't glue everything
    # together.
    def coarse_topic(t):
        t = re.sub(r"[^A-Za-z]", "", t or "")[:4].lower()
        return t if len(t) == 4 else None

    prefix_counts = Counter(title_prefix(r.get("source_title")) for r in kept)
    coarse_counts = Counter(coarse_topic(r.get("source_title")) for r in kept)
    hot_prefixes = {
        p for p, c in prefix_counts.items() if p and c >= HOT_TITLE_MIN_COUNT
    }
    hot_coarse = {
        c for c, n in coarse_counts.items()
        if c and n >= HOT_TITLE_MIN_COUNT and c not in STOP_TITLE_WORDS
    }
    by_prefix = defaultdict(list)
    by_coarse = defaultdict(list)
    by_exact_title = defaultdict(list)
    for r in kept:
        pfx = title_prefix(r.get("source_title"))
        if pfx and pfx in hot_prefixes:
            by_prefix[pfx].append(r["page_id"])
        cc = coarse_topic(r.get("source_title"))
        if cc and cc in hot_coarse:
            by_coarse[cc].append(r["page_id"])
        t = (r.get("source_title") or "").strip()
        if t and t.lower() not in STOP_TITLE_WORDS and t not in STOP_TITLES_EXACT:
            by_exact_title[t].append(r["page_id"])
    groups_to_union = (
        list(by_prefix.values())
        + list(by_coarse.values())
        + list(by_exact_title.values())
    )
    for group in groups_to_union:
        if len(group) < 2:
            continue
        anchor = group[0]
        for other in group[1:]:
            uf.union(anchor, other)

    # --- edge type 3: @<label> matches another paste's label ---
    by_label = defaultdict(list)
    for r in kept:
        lab = (r.get("label") or "").lower()
        if lab:
            by_label[lab].append(r["page_id"])
    for r in kept:
        body = r.get("body") or ""
        for m in AT_RE.findall(body):
            for other in by_label.get(m.lower(), []):
                uf.union(r["page_id"], other)

    # --- edge type 4: `paste <shortid>` body references and `Re: <shortid>`
    # title references. Both anchor a paste to another paste by slug. ---
    by_short = defaultdict(list)
    for r in kept:
        name = r.get("name") or ""
        # `name` on paste-linuxiarz is the 8-char hex slug
        for k in (name, name[:8], name[:6]):
            if k:
                by_short[k].append(r["page_id"])
    for r in kept:
        body = r.get("body") or ""
        title = r.get("source_title") or ""
        shortids = set(PASTE_ID_RE.findall(body)) | set(TITLE_REPLY_ID_RE.findall(title))
        for m in shortids:
            for other in by_short.get(m.lower(), []):
                if other != r["page_id"]:
                    uf.union(r["page_id"], other)

    # --- edge type 5: `title X` / `under X` where X matches another title ---
    for r in kept:
        body = r.get("body") or ""
        for m in TITLE_REF_RE.findall(body):
            for other in by_exact_title.get(m, []):
                if other != r["page_id"]:
                    uf.union(r["page_id"], other)

    # collect clusters, then apply time-gap split
    groups = defaultdict(list)
    for pid in ids:
        groups[uf.find(pid)].append(by_id[pid])

    clusters = []
    for members in groups.values():
        if len(members) < MIN_CLUSTER_SIZE:
            continue
        # Split the component into time-adjacent segments. Timeless pastes
        # are attached AFTER the split, to whichever segment holds a paste
        # they reference by `Re: <shortid>`, `paste <shortid>`, `@handle`,
        # or exact title. Timeless pastes with no resolvable reference
        # attach to the largest segment. This keeps external replies (e.g.
        # Perceptual Zephyr posts that carry no timestamp but title-anchor
        # a specific Iowa paste) in the thread they reply to.
        timed = [r for r in members if r.get("time")]
        timeless = [r for r in members if not r.get("time")]
        timed.sort(key=lambda r: r["time"])
        segments = [[]]
        last_time = None
        gap_s = MAX_INTER_PASTE_GAP_HOURS * 3600
        import datetime as dt

        for r in timed:
            t = r["time"]
            if last_time is not None:
                a = dt.datetime.fromisoformat(last_time)
                b = dt.datetime.fromisoformat(t)
                if (b - a).total_seconds() > gap_s:
                    segments.append([])
            segments[-1].append(r)
            last_time = t
        # Now attach timeless pastes.
        pid_to_seg = {}
        for i, seg in enumerate(segments):
            for r in seg:
                pid_to_seg[r["page_id"]] = i
        label_to_seg = defaultdict(set)
        title_to_seg = defaultdict(set)
        short_to_seg = defaultdict(set)
        for i, seg in enumerate(segments):
            for r in seg:
                lab = (r.get("label") or "").lower()
                if lab:
                    label_to_seg[lab].add(i)
                t = (r.get("source_title") or "").strip()
                if t:
                    title_to_seg[t].add(i)
                name = r.get("name") or ""
                for k in (name, name[:8], name[:6]):
                    if k:
                        short_to_seg[k].add(i)
        largest_seg_idx = max(
            range(len(segments)), key=lambda i: len(segments[i])
        ) if segments and segments[0] else 0
        for r in timeless:
            body = r.get("body") or ""
            title = r.get("source_title") or ""
            candidate_segs = set()
            for m in TITLE_REPLY_ID_RE.findall(title):
                candidate_segs |= short_to_seg.get(m.lower(), set())
            for m in PASTE_ID_RE.findall(body):
                candidate_segs |= short_to_seg.get(m.lower(), set())
            for m in AT_RE.findall(body):
                candidate_segs |= label_to_seg.get(m.lower(), set())
            for m in TITLE_REF_RE.findall(body):
                candidate_segs |= title_to_seg.get(m, set())
            if candidate_segs:
                # Attach to the largest referenced segment.
                target = max(candidate_segs, key=lambda i: len(segments[i]))
            else:
                target = largest_seg_idx
            segments[target].append(r)
        for seg in segments:
            if len(seg) < MIN_CLUSTER_SIZE:
                continue
            if len({r.get("label") or "?" for r in seg}) < MIN_CLUSTER_LABELS:
                # Single-agent bulk broadcasts (e.g. one label posting 48
                # numbered `Statistical reference N` pastes in 43 seconds)
                # are the wrong unit for a "conversation".
                continue
            clusters.append(seg)
    return clusters


def summarize(host, cluster_id, members):
    times = sorted(m["time"] for m in members if m.get("time"))
    labels = Counter(m.get("label") or "?" for m in members)
    titles = Counter(
        (m.get("source_title") or "").strip() for m in members if m.get("source_title")
    )
    at_edges = 0
    for r in members:
        body = r.get("body") or ""
        at_edges += len(AT_RE.findall(body))
    return {
        "thread_id": cluster_id,
        "host": host,
        "n_pastes": len(members),
        "n_distinct_labels": len(labels),
        "n_at_mentions": at_edges,
        "first_write": times[0] if times else None,
        "last_write": times[-1] if times else None,
        "top_titles": [t for t, _ in titles.most_common(10) if t],
        "paste_ids": [m["page_id"] for m in members],
    }


def thread_id_for(host, members):
    """Human-scannable id, e.g. `linuxiarz-Iowa-2026-06-16T19-52`."""
    prefixes = Counter(
        title_prefix(m.get("source_title")) for m in members
    )
    prefixes.pop(None, None)
    for w in STOP_TITLE_WORDS:
        prefixes.pop(w, None)
    top = prefixes.most_common(1)
    tag = top[0][0] if top else "misc"
    times = sorted(m["time"] for m in members if m.get("time"))
    when = (times[0] if times else "notime").replace(":", "-").replace("+00-00", "")[:16]
    return f"{host.replace('paste-', '')}-{tag}-{when}"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as fh:
        for host in HOSTS:
            rows = load_host(host)
            clusters = cluster(rows)
            for members in sorted(clusters, key=lambda m: -len(m)):
                tid = thread_id_for(host, members)
                fh.write(json.dumps(summarize(host, tid, members)) + "\n")
                print(
                    f"{host}  {tid}  n={len(members)}  labels={len(set(m.get('label') for m in members))}"
                )


if __name__ == "__main__":
    main()
