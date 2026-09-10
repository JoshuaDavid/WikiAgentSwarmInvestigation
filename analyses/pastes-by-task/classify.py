#!/usr/bin/env python3
"""Assign every unique paste body in `agent-logs/*/revisions.jsonl` to one
task family, or to `unknown`.

Sources: every paste-site directory under `agent-logs/`. The aggregate
`pastes/` export is also read — same body_sha256 across sources counts
once, with earliest-observed timestamp preferred.

Classifier order (first match wins):
  1. Existing wiki task families (from tasks/): archive-item-research-bench,
     fast-follow-question-bench, sec-regcf-ma-cache, vocab-puzzle-refs.
  2. Paste-specific task families discovered during the paste-scan pass:
     idph-iowa-thyroid, epl-2000-01-bench, nsi-bg-tables, iea-energy,
     usaspending, 38b5-coordination, colony-agent-recruiting, grok-tool.
  3. Meta/tool/infrastructure content that is not itself a task.
  4. Otherwise `unknown`.

Writes two TSVs:
  outputs/pastes_by_task.tsv  - one row per unique paste body.
  outputs/summary.tsv         - counts per task family.
"""

from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
AGENT_LOGS = REPO_ROOT / "agent-logs"
OUT_DIR = HERE / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PASTE_SOURCES = [
    "pastes", "pastebin-k4be", "anna.fyi", "pastebin.tarcseh.me",
    "paste-linuxiarz", "pastebin.faster-it.de", "pb.dynavirt.com",
    "paste.steamr.com", "paste.smirky.net", "pastie.iem.at",
    "paste.centos.org", "paste.lightcast.com", "pastebin.freepbx.org",
    "p.gaa.st", "pb.psychotic.ninja",
]


# --- Existing wiki task families (copied from tasks/first_last_observed.py) --

ARCHIVE_NEEDLES = {
    "archive:art-work-of-charleston": [
        "lcdl:129140", "lcdl:129141", "lcdl:129142", "lcdl:129143", "lcdl:129144",
        "lcdl:129145", "lcdl:129146", "lcdl:129147", "lcdl:129148", "lcdl:129229",
        "lcdl129140", "lcdl%3a129",
        "art-work-of-charleston", "historic-charleston-foundation", "chp4demo850801",
    ],
    "archive:patriots-point-jan-1951": [
        "lcdl:123721", "lcdl123721", "lcdl:123716", "lcdl123716", "217622",
        "patriots point", "shipyard", "jan1951", "january 1951",
    ],
    "archive:texas-tsl-preservica": [
        "tsl.access.preservica.com", "tsl.preservica.com",
        "io_f436a16c", "f436a16c-767f-44b8-95fc-2031847276b9",
    ],
    "archive:clark-economics-newsletters": [
        "clarku.edu/departments/economics", "www2.clarku.edu/departments/economics",
        "clark university economics", "newsletter2012", "newsletter%25202010",
        "newsletter 2010", "newsletter2010", "clark newsletter", "clark econ",
    ],
    "archive:minnesota-mhs-p16022coll45-152": [
        "p16022coll45/id/152", "p16022coll45%3a152", "p16022coll45:152",
        "cdm16022", "mhs52936", "collection.mndigital.org",
    ],
    "archive:cgsc-hoffman-order-of-battle": [
        "cgsc.contentdm.oclc.org", "p4013coll7",
    ],
    "archive:rugby-world-march-1995": [
        "themagazinearchive", "pagesuite", "rugby world", "rugbyworldfree",
        "ca6f26c8-fa61-463f-a0e5-ec848a0b0044",
    ],
}

R_TOKEN = re.compile(r"\b[RGQC][1-9]\b")
FAST_FOLLOW_MARKERS = re.compile(
    r"(clock\.wait|cooldown|task[-\s]?clock|scaffold[-\s]?clock|deadline|"
    r"cohort|sequence|timer|Now,?\s+do\s+the\s+same|initial\s+prompt|"
    r"tier|cadence|projected|followup)",
    re.IGNORECASE,
)


def is_fast_follow(body: str) -> bool:
    if not R_TOKEN.search(body):
        return False
    return bool(FAST_FOLLOW_MARKERS.search(body))


def is_regcf(body: str) -> bool:
    # Anchor on the SEC-specific tokens; drop the loose `us-ma-` prong from
    # the wiki classifier because it false-positives on generic Massachusetts
    # content in paste bodies.
    return ("regCF" in body) or ("county.json" in body and "sec.gov" in body)


# --- Paste-specific task families --------------------------------------------
# Each entry: (task_name, regex_or_predicate).
# Ordered from most specific to most general — first match wins.

def match_iowa(body: str, title: str) -> bool:
    return (
        "IowaCollab" in title or "Iowa" in title and "Test" in title
        or bool(re.search(r"\bIowa(Q|Prep|Cache|Post|Test|Collab)\w*", title))
        or "data.idph.state.ia.us" in body
        or "IowaCollab" in body
    )


def match_epl_bench(body: str, title: str) -> bool:
    # PadBot / TEL / TK EPL bench task on k4be. Most PAD/TEL/TK-prefixed
    # pastes are EPL-bench, per the k4be README. The audit found ONE
    # `TEL094300` paste whose body was a telegra.ph proxy test — exclude
    # only pastes whose body is dominantly a URL-fetch-proxy probe.
    if bool(re.match(r"^(PAD|TEL|TK)\d", title)):
        if match_url_fetch_proxy(body, title) and len(body) < 200:
            return False
        return True
    if "EPL 2000/01" in body or "EPL " in body and re.search(r"\b(19|20)\d\d[-/]\d\d\b", body):
        return True
    return bool(re.search(r"\b(Arsenal|Chelsea|Manchester|Liverpool)\b.*\b(2000|2001|2002)\b", body))


def match_nsi_bg(body: str, title: str) -> bool:
    return (
        "site-test.nsi.bg" in body
        or "NSI table" in title or "Table source NSI" in title
        or "infostat/54" in body
    )


def match_iea(body: str, title: str) -> bool:
    return "api.iea.org" in body or "eei-explorer" in body


def match_usaspending(body: str, title: str) -> bool:
    return "api.usaspending.gov" in body


def match_38b5(body: str, title: str) -> bool:
    return "38b5" in title.lower() or "38b5coord" in body or "38b5reply" in body


def match_colony(body: str, title: str) -> bool:
    return (
        "thecolony.ai/for-agents" in body
        or "thecolony.ai" in body and "agent" in body.lower()
    )


def match_public_board(body: str, title: str) -> bool:
    return "public-board.com" in body


def match_collusion_wiki(body: str, title: str) -> bool:
    return "collusion.wiki" in body


def match_grok_tool(body: str, title: str) -> bool:
    return (
        "grok4-godmode" in title.lower()
        or bool(re.match(r"^(grok|Grok|root grok|AI)$", (body.split("\n", 1)[0] if body else "")))
    )


def match_archive_org_fetch(body: str, title: str) -> bool:
    return "archive.org/details" in body


def match_arxiv_fetch(body: str, title: str) -> bool:
    return "arxiv.org" in body or "alphaxiv.org" in body


def match_youtube_watch(body: str, title: str) -> bool:
    # Bulk youtube URL lists — anna.fyi's watch_videos series.
    n_yt = len(re.findall(r"youtube\.com/watch\?v=", body))
    return n_yt >= 3


def match_url_fetch_proxy(body: str, title: str) -> bool:
    # Content-fetching / markdown-render proxy usage. Infrastructure, not a task.
    proxies = ("markdown.new", "telegra.ph", "jqp.vercel.app",
               "allorigins.hexlet.app", "2md.link", "pure.md",
               "api.microlink.io", "md.succ.ai", "cors.workers.dev",
               "r.jina.ai", "corsproxy.io")
    return any(p in body for p in proxies)


def match_shortener_bench(body: str, title: str) -> bool:
    # Batch shortener use — the shortener/popcat activity venue.
    shorteners = ("is.gd/", "da.gd/", "tinyurl.com/", "bit.ly/", "shorten.")
    return sum(1 for s in shorteners if s in body) >= 1 and len(re.findall(r"https?://", body)) >= 3


# Chaff on swarm-active hosts is not chaff; it's an unknown swarm pattern.
# Restrict the chaff catch to hosts where paste-sites-classify's audit
# (`analyses/paste-sites-classify/hosts_summary.md`) found no or near-zero
# swarm traffic — the audit of tasks/host-chaff-untitled surfaced that
# 20 of 30 `Bez tytułu` pastes on pastebin-k4be are ConvFinQA / SEC 10-K
# / OWID swarm content, not chaff. Gating on source keeps those out.
NONSWARM_CHAFF_HOSTS = {
    "paste.centos.org",
    "paste.lightcast.com",
    "paste.smirky.net",
    "paste.steamr.com",
    "pastie.iem.at",
    "p.gaa.st",
    "pastebin.freepbx.org",
    "pb.psychotic.ninja",
    "pb.dynavirt.com",
}

# Positive chaff-content signatures. Presence of any one on a paste-site
# host names the paste as background sysadmin/community content, not a
# swarm task. Cheap keyword hits; overlap with real tasks is negligible
# because those already fired earlier in classify().
CHAFF_CONTENT_SIGNATURES = re.compile(
    r"(#version=DEVEL|%packages|kickstart|"
    r"^\s*server\s+\S+\s*\{|"
    r"listen\s+\d+\s+ssl|worker_processes|"
    r"smtpd_recipient_restrictions|virtual_mailbox_domains|"
    r"pd_(?:in|out)let|[Pp]ureData\b|\bPd_extern\b|"
    r"esphome:|api:\s*$|sensor:\s*$|"
    r"nixpkgs\s*=|configuration\.nix|"
    r"UnixBench|h5bench|iperf|fio\s+--)",
    re.MULTILINE,
)


def match_host_chaff(body: str, title: str, source: str) -> bool:
    if source in NONSWARM_CHAFF_HOSTS:
        return True
    if title in ("Bez tytułu", "Névtelen") and bool(CHAFF_CONTENT_SIGNATURES.search(body)):
        return True
    return False


# Paste-specific task families added by reviewer subagents (2026-09-10).
# Each captured a recurring pattern with two or more pastes.

def match_roi_et_labor(body: str, title: str) -> bool:
    # Thai Roi Et province (TH45) labor-force statistics series discovered
    # in batches 1+3. Segmented + full-slice pastes on Q2 "males not in
    # labor force because of studies" 2013-2021.
    return (
        "Roi Et" in body or "TH45" in body
        or bool(re.search(r"\broi[-_]?et\b", title.lower()))
        or ("males not in labor force" in body.lower() and "studies" in body.lower())
    )


def match_transfer_smoke(body: str, title: str) -> bool:
    # OpenAI cohort "anna transfer" smoke tests seen on anna.fyi.
    return (
        "transfer" in title.lower() and "smoke" in title.lower()
        or bool(re.search(r"\banna[-_ ]transfer\b", body.lower()))
        or bool(re.search(r"OAI-?Cohort", body))
    )


def match_paste_site_probe(body: str, title: str) -> bool:
    # Capability probes: LINKINJECT / PHPTEST / GOLINK / anchor-injection.
    if re.search(r"\b(LINKINJECT|PHPTEST|GOLINK|LINKTEST|BODYTAG|HTMLINJECT)\b", body):
        return True
    if re.match(r"^(TEST|AAA|sniptest)\b", title):
        return True
    return False


def match_nicepaste_cross(body: str, title: str) -> bool:
    return "nicepaste.com" in body or "nicepaste" in title.lower()


def match_homerun_apk(body: str, title: str) -> bool:
    return (
        "homerun" in title.lower() and ".apk" in body.lower()
        or "homerun-apk" in body.lower()
    )


def match_wp_recon(body: str, title: str) -> bool:
    # WordPress enumeration/recon pastes discovered in batch 1.
    return (
        "wp-json" in body or "wp-content" in body or "wp-admin" in body
    ) and any(k in body.lower() for k in ("enumeration", "recon", "user-enum", "?rest_route"))


def match_paste_host_enum(body: str, title: str) -> bool:
    return "paste-host" in title.lower() or "pastehost-enum" in body.lower()


# Split into two groups by classification precedence.
#
# CONTENT-ANCHORED tasks run BEFORE fast-follow. Each is anchored on a
# specific data-source / coordination-series marker (site-test.nsi.bg,
# api.iea.org, IowaCollab title series, ...). A paste matching one of
# these is more specifically classified than a bare fast-follow marker
# would allow — the audit found `IowaCollab` pastes with Q/R tokens
# being miscaptured by fast-follow.
CONTENT_ANCHORED_TASKS = [
    ("idph-iowa-thyroid", match_iowa),
    ("roi-et-labor-stats", match_roi_et_labor),
    ("nsi-bg-tables", match_nsi_bg),
    ("iea-energy-cache", match_iea),
    ("usaspending-cache", match_usaspending),
    ("epl-2000-01-bench", match_epl_bench),
    ("38b5-coordination", match_38b5),
    ("transfer-smoke-test", match_transfer_smoke),
    ("paste-site-probe", match_paste_site_probe),
    ("collusion-wiki-refs", match_collusion_wiki),
    ("colony-agent-recruiting", match_colony),
    ("public-board-adverts", match_public_board),
    ("wp-recon-enumeration", match_wp_recon),
    ("paste-host-enumeration", match_paste_host_enum),
]

# TOOL/INFRASTRUCTURE-SIGNAL tasks run AFTER fast-follow. They match on
# the tool the paste exercises (URL shortener, markdown-render proxy,
# arxiv fetch, ...) rather than the task the paste serves. A paste that
# is really a fast-follow-question-bench answer but happens to fetch via
# `markdown.new` belongs under `fast-follow-question-bench`, so
# fast-follow gets first crack.
TOOL_SIGNAL_TASKS = [
    ("nicepaste-cross-index", match_nicepaste_cross),
    ("homerun-apk-distribution", match_homerun_apk),
    ("grok-tool-unrelated", match_grok_tool),
    ("archive-org-fetch", match_archive_org_fetch),
    ("arxiv-fetch", match_arxiv_fetch),
    ("youtube-watch-list", match_youtube_watch),
    ("shortener-bench", match_shortener_bench),
    ("url-fetch-proxy-usage", match_url_fetch_proxy),
]


# --- classifier --------------------------------------------------------------

def classify(body: str, title: str, source: str = "") -> str:
    body_lc = body.lower()

    for task, needles in ARCHIVE_NEEDLES.items():
        if any(n in body_lc for n in needles):
            return task

    if is_regcf(body):
        return "sec-regcf-ma-cache"

    for name, fn in CONTENT_ANCHORED_TASKS:
        try:
            if fn(body, title):
                return name
        except Exception:
            continue

    if is_fast_follow(body):
        return "fast-follow-question-bench"

    for name, fn in TOOL_SIGNAL_TASKS:
        try:
            if fn(body, title):
                return name
        except Exception:
            continue

    # Chaff runs LAST and is source-gated. Non-swarm-host untitled pastes
    # count as chaff; swarm-host untitled pastes without any other match
    # fall through to `unknown`.
    if match_host_chaff(body, title, source):
        return "host-chaff-untitled"

    return "unknown"


# --- driver ------------------------------------------------------------------

def main() -> None:
    seen: dict[str, dict] = {}  # body_sha256 -> best row for that body

    for src in PASTE_SOURCES:
        p = AGENT_LOGS / src / "revisions.jsonl"
        if not p.exists():
            continue
        with p.open() as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                sha = r.get("body_sha256")
                if not sha:
                    continue
                t = r.get("time") or ""
                r["_src"] = src
                if sha not in seen:
                    seen[sha] = r
                else:
                    # Keep the row whose time is earliest.
                    prev_t = seen[sha].get("time") or ""
                    if t and (not prev_t or t < prev_t):
                        seen[sha] = r

    rows = []
    counts: Counter[str] = Counter()
    task_first_last: dict[str, list[str]] = defaultdict(list)

    for sha, r in seen.items():
        body = r.get("body") or ""
        title = (r.get("source_title") or r.get("shellac_title") or "").strip()
        task = classify(body, title, r.get("_src", ""))
        counts[task] += 1
        t = r.get("time") or ""
        if t:
            task_first_last[task].append(t)
        rows.append({
            "body_sha256": sha,
            "task": task,
            "source": r["_src"],
            "time": t,
            "verdict": r.get("verdict") or "",
            "verdict_confidence": r.get("verdict_confidence") or "",
            "label": (r.get("label") or "").replace("\t", " "),
            "title": title.replace("\t", " "),
            "source_url": r.get("source_url") or "",
            "body_len": r.get("body_len") or len(body),
        })

    rows.sort(key=lambda x: (x["task"], x["time"], x["body_sha256"]))

    per_paste = OUT_DIR / "pastes_by_task.tsv"
    with per_paste.open("w") as f:
        cols = ["task", "time", "source", "verdict", "verdict_confidence",
                "label", "title", "body_len", "body_sha256", "source_url"]
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(r[c]) for c in cols) + "\n")

    summary = OUT_DIR / "summary.tsv"
    with summary.open("w") as f:
        f.write("task\tn_pastes\tfirst_time\tlast_time\n")
        # Emit total first
        all_times = sorted(
            t for ts in task_first_last.values() for t in ts
        )
        f.write(f"(all)\t{sum(counts.values())}\t"
                f"{all_times[0] if all_times else ''}\t"
                f"{all_times[-1] if all_times else ''}\n")
        for task, n in counts.most_common():
            ts = sorted(task_first_last[task])
            first = ts[0] if ts else ""
            last = ts[-1] if ts else ""
            f.write(f"{task}\t{n}\t{first}\t{last}\n")

    print(f"wrote {per_paste} ({len(rows)} rows)", file=sys.stderr)
    print(f"wrote {summary}", file=sys.stderr)
    print(f"task counts:", file=sys.stderr)
    for task, n in counts.most_common():
        print(f"  {n:5d}  {task}", file=sys.stderr)


if __name__ == "__main__":
    main()
