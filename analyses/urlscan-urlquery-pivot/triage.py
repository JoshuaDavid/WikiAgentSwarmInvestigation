#!/usr/bin/env python3
"""Triage harvested urlscan.io and urlquery.net rows for swarm tells.

Reads:
  outputs/urlscan/hits.jsonl, outputs/urlquery/hits.jsonl
  ../oai-spider-url-triage/predicates.py      the 50-tell predicate library
  ../oai-url-taxonomy/parse_url.py            wrapper peeling -> base host
  ../urls/outputs/urls.jsonl                  every URL in agent-logs bodies
  ../oai-url-taxonomy/outputs/urls.jsonl      every URL the Google scan saw
  scrape/outputs/swarm.termina.digital/pub/   venue, venue_link, lead tables

Writes:
  outputs/rows.jsonl        every harvested row with tier, tells, base host,
                            and the three dedup flags
  outputs/tier_a.jsonl      tier A rows only
  outputs/new_hosts.tsv     hosts in tier A rows unknown to termina and to
                            this repo's corpus
  outputs/summary.md        the tables the README quotes

Tiers:
  A  the URL carries at least one shape tell (a predicate other than plain
     host membership), or its base host is a known benchmark data target
  B  the URL only sits on a swarm-used host; shape is not distinctive
  C  no tell
"""

from __future__ import annotations

import collections
import csv
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "analyses", "oai-spider-url-triage"))
sys.path.insert(0, os.path.join(REPO, "analyses", "oai-url-taxonomy"))
sys.path.insert(0, HERE)
import predicates  # noqa: E402
import parse_url  # noqa: E402
from targets import TARGETS, INCIDENT_WINDOW_START  # noqa: E402
from redact import redact_obj, redact_text  # noqa: E402

OUT = os.path.join(HERE, "outputs")
TERMINA = os.path.join(REPO, "scrape", "outputs", "swarm.termina.digital", "pub")
CORE_START, CORE_END = "2026-05-11", "2026-06-22"

HOST_ONLY_TELLS = {"wrapper_host", "swarm_yourls_host", "swarm_wiki_host", "testbed_host"}
# Tells that fire on ordinary use of a path-mode wrapper. ``r.jina.ai/https://x``
# is how every r.jina.ai user writes a URL, and the ``//`` it contains is not
# a malformation. These do not make a row tier A on their own.
WEAK_TELLS = HOST_ONLY_TELLS | {"double_slash_in_path", "r_jina_prefix"}

# Path-mode wrappers the shared parser does not know. Peeled before parsing.
EXTRA_PATH_WRAPPERS = ("text.microlink.io", "html.microlink.io", "markdown.microlink.io",
                       "pdf.microlink.io", "deelay.me")

# Rows on a swarm-used host whose base host is hit in a burst are promoted to
# tier A. A burst is BURST_MIN rows on one base host inside BURST_DAYS days.
BURST_MIN, BURST_DAYS = 10, 3

# Benchmark data targets. A URL whose innermost host is one of these is a
# tier A hit even when its shape carries no other tell.
DATA_TARGET_HOSTS = {
    "sec.gov", "investor.gov", "api.datausa.io", "api-la.datausa.io",
    "la.datausa.io", "datausa.io", "api.usaspending.gov", "portal.max.gov",
    "piv.max.gov", "api.dataafrica.io", "api.worldpoverty.io", "ons.gov.uk",
    "api.beta.ons.gov.uk", "site-test.nsi.bg", "px.hagstofa.is",
    "data.idph.state.ia.us", "viz.aihw.gov.au", "vizhub.healthdata.org",
    "rspace.library.cofc.edu", "lcdl.library.cofc.edu", "iiif.library.cofc.edu",
    "railroadtreasures.com", "finance.yahoo.co.jp", "code.highcharts.com",
    "preservica.com", "api.ourworldindata.org", "hub.catalogit.app",
    "search.projectarclight.org", "labaspreces.eu", "datasets.cbs.nl",
}


def _norm_host(h: str) -> str:
    h = (h or "").lower().strip().rstrip(".")
    return h[4:] if h.startswith("www.") else h


def _host_of(url: str) -> str:
    try:
        return _norm_host(urllib.parse.urlsplit(url).netloc.split("@")[-1].split(":")[0])
    except Exception:
        return ""


def _norm_url(u: str) -> str:
    u = (u or "").strip()
    for p in ("https://", "http://"):
        if u.lower().startswith(p):
            u = u[len(p):]
    if u.lower().startswith("www."):
        u = u[4:]
    return u.rstrip("/")


def _with_scheme(u: str) -> str:
    return u if u.lower().startswith(("http://", "https://")) else "https://" + u


def _apex_match(host: str, known: set[str]) -> bool:
    parts = host.split(".")
    return any(".".join(parts[i:]) in known for i in range(len(parts) - 1))


def load_termina() -> tuple[set[str], dict[str, str]]:
    hosts: set[str] = set()
    status: dict[str, str] = {}
    for name in ("venue.jsonl", "venue_link.jsonl", "lead.jsonl"):
        path = os.path.join(TERMINA, name)
        if not os.path.exists(path):
            continue
        for line in open(path):
            d = json.loads(line)
            for key in ("host", "url"):
                v = d.get(key)
                if not v or not isinstance(v, str):
                    continue
                h = _host_of(_with_scheme(v)) if "/" in v or "." in v else ""
                if h and "." in h and " " not in h:
                    hosts.add(h.lstrip("."))
                    if name == "venue.jsonl":
                        status[h] = d.get("status") or ""
    return hosts, status


def load_url_sets() -> tuple[set[str], set[str], set[str]]:
    corpus_urls, corpus_hosts, scan_urls = set(), set(), set()
    p = os.path.join(REPO, "analyses", "urls", "outputs", "urls.jsonl")
    for line in open(p):
        d = json.loads(line)
        u = d.get("url") or ""
        corpus_urls.add(_norm_url(u))
        corpus_hosts.add(_host_of(u))
    p = os.path.join(REPO, "analyses", "oai-url-taxonomy", "outputs", "urls.jsonl")
    for line in open(p):
        d = json.loads(line)
        scan_urls.add(_norm_url(d.get("url") or ""))
    corpus_hosts.discard("")
    return corpus_urls, corpus_hosts, scan_urls


DOUBLE_SCHEME_RE = re.compile(r"(?i)https?:/{1,2}https?(?::|%3A)/{0,2}")


def _peel_double_scheme(u: str) -> str:
    """Strip a leading doubled scheme like ``http://https://host``."""
    for _ in range(3):
        m = re.match(r"(?i)^https?:/{1,2}(https?(?::|%3A)(?:/|%2F){0,2}.*)$", u)
        if not m:
            return u
        u = urllib.parse.unquote(m.group(1)) if "%3A" in m.group(1)[:8].upper() else m.group(1)
    return u


def _peel_extra(url: str) -> tuple[list[str], str]:
    """Peel path-mode wrappers the shared parser lacks. Returns (wrappers, inner)."""
    peeled: list[str] = []
    for _ in range(4):
        sp = urllib.parse.urlsplit(url)
        host = _norm_host(sp.netloc)
        if host not in EXTRA_PATH_WRAPPERS:
            break
        path = sp.path.lstrip("/")
        if host == "deelay.me":
            path = re.sub(r"^\d+/", "", path)
        inner = path + (("?" + sp.query) if sp.query else "")
        if not inner:
            break
        peeled.append(host)
        url = _with_scheme(urllib.parse.unquote(inner) if inner.lower().startswith("https%3a") else inner)
    return peeled, url


def analyse(url: str) -> dict:
    url = _with_scheme(url)
    tells = predicates.classify(url)
    extra_wrappers, inner = _peel_extra(url)
    if extra_wrappers:
        tells = sorted(set(tells) | set(predicates.classify(inner)) | {"wrapper_host"})
        url = inner
    # Local tell: a wrapper path that carries two schemes in a row. Ordinary
    # clients never emit ``r.jina.ai/http://https://host``; the swarm's URL
    # assembly does.
    if DOUBLE_SCHEME_RE.search(url):
        tells = sorted(set(tells) | {"double_scheme"})
    try:
        parsed = parse_url.parse(url)
        wrappers = extra_wrappers + list(getattr(parsed, "wrappers", []) or [])
        base_host = _norm_host(getattr(parsed, "base_host", "") or "")
        base_url = getattr(parsed, "base_url", "") or ""
        if base_host in ("http:", "https:", "http", "https") or DOUBLE_SCHEME_RE.match(base_url or ""):
            base_url = _peel_double_scheme(base_url)
            base_host = _host_of(base_url)
    except Exception:
        wrappers, base_host, base_url = list(extra_wrappers), "", ""
    shape = [t for t in tells if t not in WEAK_TELLS]
    data_target = base_host in DATA_TARGET_HOSTS or _apex_match(base_host, DATA_TARGET_HOSTS)
    if shape or data_target:
        tier = "A"
    elif tells:
        tier = "B"
    else:
        tier = "C"
    return {"tells": tells, "wrappers": wrappers, "base_host": base_host,
            "base_url": base_url, "data_target": data_target, "tier": tier}


def main() -> None:
    termina_hosts, termina_status = load_termina()
    corpus_urls, corpus_hosts, scan_urls = load_url_sets()
    target_source = {t: s for t, s, _ in TARGETS}

    import glob
    rows = []
    files = [("urlscan", p) for p in sorted(glob.glob(os.path.join(OUT, "urlscan", "hits*.jsonl")))]
    files += [("urlquery", p) for p in sorted(glob.glob(os.path.join(OUT, "urlquery", "hits*.jsonl")))]
    files += [("wayback", p) for p in sorted(glob.glob(os.path.join(OUT, "wayback", "hits*.jsonl")))]
    for src, p in files:
        for line in open(p):
            h = json.loads(line)
            if src == "wayback":
                ts = h.get("timestamp") or ""
                h = {"target": h.get("target"), "target_source": "wayback", "url": h.get("url"),
                     "date": f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:14]}",
                     "report_id": f"{ts}/{h.get('digest')}",
                     "report_url": f"https://web.archive.org/web/{ts}id_/{h.get('url')}",
                     "detections": h.get("status"), "ip": None, "asn": None, "asnname": None}
                src_eff = "urlquery_like"
            if src == "urlscan":
                primary = h.get("task_url") or h.get("page_url") or ""
                alt = h.get("page_url") or ""
                when = (h.get("time") or "")[:19].replace("T", " ")
                ident = h.get("scan_id")
                link = "https://urlscan.io/result/%s/" % ident
            else:
                primary = h.get("url") or ""
                alt = ""
                when = h.get("date") or ""
                ident = h.get("report_id")
                link = h.get("report_url")
            a = analyse(primary)
            if alt and alt != primary:
                a2 = analyse(alt)
                a["tells"] = sorted(set(a["tells"]) | set(a2["tells"]))
                if a2["tier"] < a["tier"]:
                    a["tier"] = a2["tier"]
            page_host = _host_of(_with_scheme(primary))
            hosts_here = {page_host, a["base_host"], *[_norm_host(w) for w in a["wrappers"]]} - {""}
            row = {
                "source": src,
                "id": ident,
                "link": link,
                "time": when,
                "target": h.get("target"),
                "target_source": h.get("target_source") or target_source.get(h.get("target")),
                "url": primary,
                "page_host": page_host,
                "in_window": when[:10] >= INCIDENT_WINDOW_START,
                "in_core": CORE_START <= when[:10] <= CORE_END,
                "any_host_known_termina": any(x in termina_hosts or _apex_match(x, termina_hosts) for x in hosts_here),
                "any_host_in_corpus": any(x in corpus_hosts for x in hosts_here),
                "base_host_known_termina": bool(a["base_host"]) and (a["base_host"] in termina_hosts or _apex_match(a["base_host"], termina_hosts)),
                "base_host_in_corpus": a["base_host"] in corpus_hosts,
                "url_in_corpus": _norm_url(primary) in corpus_urls,
                "url_in_google_scan": _norm_url(primary) in scan_urls,
                "ip": h.get("page_ip") or h.get("ip"),
                "asn": h.get("page_asn") or h.get("asn"),
                "asnname": h.get("page_asnname") or h.get("asnname"),
                "visibility": h.get("visibility"),
                "method": h.get("method"),
                "detections": h.get("detections"),
                **a,
            }
            rows.append(row)

    # one row per (source, id): a scan can be found by several targets
    best: dict[tuple, dict] = {}
    for r in rows:
        k = (r["source"], r["id"])
        if k not in best or r["tier"] < best[k]["tier"]:
            if k in best:
                r["found_by"] = sorted(set(best[k]["found_by"]) | {r["target"]})
            else:
                r["found_by"] = [r["target"]]
            best[k] = r
        else:
            best[k]["found_by"] = sorted(set(best[k]["found_by"]) | {r["target"]})
    rows = sorted(best.values(), key=lambda r: (r["source"], r["time"], r["id"] or ""))

    # Burst promotion: tier B rows in the incident window whose base host
    # collects BURST_MIN rows (any tier) within BURST_DAYS days.
    import datetime as _dt
    by_host: dict[str, list] = collections.defaultdict(list)
    for r in rows:
        if r["in_window"] and r["base_host"]:
            try:
                by_host[r["base_host"]].append(_dt.date.fromisoformat(r["time"][:10]))
            except ValueError:
                pass
    bursty: set[str] = set()
    for h, ds in by_host.items():
        ds.sort()
        for i in range(len(ds)):
            if i + BURST_MIN - 1 < len(ds) and (ds[i + BURST_MIN - 1] - ds[i]).days < BURST_DAYS:
                bursty.add(h)
                break
    for r in rows:
        if r["tier"] == "B" and r["in_window"] and r["base_host"] in bursty:
            r["tier"] = "A"
            r["tells"] = sorted(set(r["tells"]) | {"burst_cluster"})
    # Direct-target promotion: a tier C row is a bare submission of a data
    # URL with no wrapper and no shape tell. When the same base host carries
    # tier A rows on the same or an adjacent day, the bare submission is
    # the same activity reaching the target without a relay.
    def _endpoint(u: str) -> str:
        sp = urllib.parse.urlsplit(_with_scheme(u))
        return "/".join(sp.path.split("/")[:3])

    a_days: dict[str, set] = collections.defaultdict(set)
    a_paths: dict[str, set] = collections.defaultdict(set)
    a_count: collections.Counter = collections.Counter()
    for r in rows:
        if r["tier"] == "A" and r["in_window"] and r["base_host"] and "burst_cluster" not in r["tells"]:
            a_count[r["base_host"]] += 1
            a_paths[r["base_host"]].add(_endpoint(r["base_url"] or r["url"]))
            try:
                a_days[r["base_host"]].add(_dt.date.fromisoformat(r["time"][:10]))
            except ValueError:
                pass
    for r in rows:
        h = r["base_host"]
        if r["tier"] != "C" or not r["in_window"] or a_count[h] < BURST_MIN or r["wrappers"]:
            continue
        if _endpoint(r["url"]) not in a_paths[h]:
            continue
        try:
            d = _dt.date.fromisoformat(r["time"][:10])
        except ValueError:
            continue
        if any(abs((d - x).days) <= 1 for x in a_days[h]):
            r["tier"] = "A"
            r["tells"] = sorted(set(r["tells"]) | {"direct_target_burst"})
    for r in rows:
        r["bursty_host"] = r["base_host"] in bursty

    rows = [redact_obj(r) for r in rows]
    with open(os.path.join(OUT, "rows.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tier_a = [r for r in rows if r["tier"] == "A"]
    with open(os.path.join(OUT, "tier_a.jsonl"), "w") as f:
        for r in tier_a:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # --- new hosts ------------------------------------------------------
    new_hosts: dict[str, dict] = {}
    for r in tier_a:
        for role, hval in (("page", r["page_host"]), ("base", r["base_host"]), *[("wrapper", _norm_host(w)) for w in r["wrappers"]]):
            if not hval:
                continue
            if hval in termina_hosts or _apex_match(hval, termina_hosts) or hval in corpus_hosts:
                continue
            e = new_hosts.setdefault(hval, {"host": hval, "roles": set(), "n": 0, "first": r["time"], "last": r["time"], "sample": r["url"], "sources": set()})
            e["roles"].add(role); e["n"] += 1; e["sources"].add(r["source"])
            e["first"] = min(e["first"], r["time"]); e["last"] = max(e["last"], r["time"])
    with open(os.path.join(OUT, "new_hosts.tsv"), "w") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["host", "roles", "tier_a_rows", "first", "last", "sources", "sample_url"])
        for e in sorted(new_hosts.values(), key=lambda e: (-e["n"], e["host"])):
            w.writerow([e["host"], ",".join(sorted(e["roles"])), e["n"], e["first"], e["last"], ",".join(sorted(e["sources"])), redact_text(e["sample"][:200])])

    # --- clusters -------------------------------------------------------
    # One row per base host with >= BURST_MIN tier A rows in the incident
    # window. This is the table an investigator reads first.
    cl: dict[str, dict] = {}
    for r in tier_a:
        if not r["in_window"] or not r["base_host"]:
            continue
        e = cl.setdefault(r["base_host"], {"base_host": r["base_host"], "rows": 0, "urls": set(), "days": set(),
                                           "wrappers": collections.Counter(), "sources": set(), "first": r["time"], "last": r["time"],
                                           "known_termina": r["base_host_known_termina"], "known_corpus": r["base_host_in_corpus"],
                                           "url_in_corpus": 0, "sample": r["url"]})
        e["rows"] += 1; e["urls"].add(_norm_url(r["url"])); e["days"].add(r["time"][:10])
        e["wrappers"][" > ".join(r["wrappers"]) or "(none)"] += 1; e["sources"].add(r["source"])
        e["first"] = min(e["first"], r["time"]); e["last"] = max(e["last"], r["time"])
        e["url_in_corpus"] += int(r["url_in_corpus"])
    clusters = sorted([e for e in cl.values() if e["rows"] >= BURST_MIN], key=lambda e: -e["rows"])
    with open(os.path.join(OUT, "clusters.tsv"), "w") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["base_host", "tier_a_rows", "distinct_urls", "active_days", "first", "last", "top_wrappers",
                    "base_host_in_corpus", "base_host_known_to_termina", "urls_already_in_corpus", "sample_url"])
        for e in clusters:
            w.writerow([e["base_host"], e["rows"], len(e["urls"]), len(e["days"]), e["first"][:16], e["last"][:16],
                        "; ".join(f"{k} ({n})" for k, n in e["wrappers"].most_common(3)),
                        "yes" if e["known_corpus"] else "no", "yes" if e["known_termina"] else "no",
                        e["url_in_corpus"], redact_text(e["sample"][:220])])

    # --- summary --------------------------------------------------------
    L = []
    L.append("# urlscan / urlquery pivot — summary\n")
    L.append("Generated by `triage.py`.\n")
    by_src = collections.Counter(r["source"] for r in rows)
    L.append("## Rows\n")
    L.append("| source | rows | tier A | tier B | tier C | tier A in core window (%s..%s) |" % (CORE_START, CORE_END))
    L.append("|---|---:|---:|---:|---:|---:|")
    for s in ("urlscan", "urlquery", "wayback"):
        rs = [r for r in rows if r["source"] == s]
        L.append("| %s | %d | %d | %d | %d | %d |" % (
            s, len(rs), sum(r["tier"] == "A" for r in rs), sum(r["tier"] == "B" for r in rs),
            sum(r["tier"] == "C" for r in rs), sum(r["tier"] == "A" and r["in_core"] for r in rs)))
    L.append("")
    L.append("## Per target\n")
    L.append("| target | source list | urlscan rows | urlquery rows | wayback rows | tier A | tier A in core |")
    L.append("|---|---|---:|---:|---:|---:|---:|")
    per = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        for t in r["found_by"]:
            per[t]["us" if r["source"] == "urlscan" else ("wb" if r["source"] == "wayback" else "uq")] += 1
            if r["tier"] == "A":
                per[t]["A"] += 1
                if r["in_core"]:
                    per[t]["Acore"] += 1
    extra = [(t, "wayback", "host") for t in sorted(per) if t not in {x[0] for x in TARGETS}]
    for t, s, _ in list(TARGETS) + extra:
        c = per[t]
        if sum(c.values()) == 0:
            continue
        L.append("| %s | %s | %d | %d | %d | %d | %d |" % (t, s, c["us"], c["uq"], c["wb"], c["A"], c["Acore"]))
    L.append("")
    L.append("## Tier A by UTC day\n")
    L.append("| day | urlscan | urlquery | wayback |")
    L.append("|---|---:|---:|---:|")
    days = collections.defaultdict(collections.Counter)
    for r in tier_a:
        days[r["time"][:10]][r["source"]] += 1
    for d in sorted(days):
        L.append("| %s | %d | %d | %d |" % (d, days[d]["urlscan"], days[d]["urlquery"], days[d]["wayback"]))
    L.append("")
    L.append("## Clusters: base hosts with %d+ tier A rows in the incident window\n" % BURST_MIN)
    L.append("| base host | rows | distinct URLs | days | first | last | base host in corpus | base host known to termina | top wrapper |")
    L.append("|---|---:|---:|---:|---|---|---|---|---|")
    for e in clusters:
        L.append("| %s | %d | %d | %d | %s | %s | %s | %s | %s |" % (
            e["base_host"], e["rows"], len(e["urls"]), len(e["days"]), e["first"][:10], e["last"][:10],
            "yes" if e["known_corpus"] else "no", "yes" if e["known_termina"] else "no",
            e["wrappers"].most_common(1)[0][0]))
    L.append("")
    L.append("## Tier A innermost hosts (top 40)\n")
    L.append("| base host | rows | first | last |")
    L.append("|---|---:|---|---|")
    bh = collections.defaultdict(list)
    for r in tier_a:
        bh[r["base_host"] or r["page_host"]].append(r["time"])
    for h, ts in sorted(bh.items(), key=lambda kv: -len(kv[1]))[:40]:
        L.append("| %s | %d | %s | %s |" % (h, len(ts), min(ts), max(ts)))
    L.append("")
    L.append("## Tier A wrapper stacks (top 25)\n")
    L.append("| wrappers (outer → inner) | rows |")
    L.append("|---|---:|")
    ws = collections.Counter(" → ".join(r["wrappers"]) or "(none)" for r in tier_a)
    for k, n in ws.most_common(25):
        L.append("| %s | %d |" % (k, n))
    L.append("")
    L.append("## Tier A tells (top 30)\n")
    L.append("| tell | rows |")
    L.append("|---|---:|")
    tc = collections.Counter(t for r in tier_a for t in r["tells"])
    for k, n in tc.most_common(30):
        L.append("| %s | %d |" % (k, n))
    L.append("")
    L.append("## Novelty of tier A rows\n")
    L.append("| check | rows |")
    L.append("|---|---:|")
    L.append("| tier A total | %d |" % len(tier_a))
    L.append("| exact URL already in agent-logs bodies | %d |" % sum(r["url_in_corpus"] for r in tier_a))
    L.append("| exact URL already in the Google-scan URL set | %d |" % sum(r["url_in_google_scan"] for r in tier_a))
    L.append("| exact URL in neither | %d |" % sum((not r["url_in_corpus"]) and (not r["url_in_google_scan"]) for r in tier_a))
    L.append("| base host known to termina | %d |" % sum(r["base_host_known_termina"] for r in tier_a))
    L.append("| base host in this repository's corpus | %d |" % sum(r["base_host_in_corpus"] for r in tier_a))
    L.append("| base host known to neither | %d |" % sum((not r["base_host_known_termina"]) and (not r["base_host_in_corpus"]) for r in tier_a))
    L.append("| distinct new hosts (see new_hosts.tsv) | %d |" % len(new_hosts))
    L.append("")
    L.append("## urlscan submission metadata for tier A rows\n")
    L.append("| visibility / method | rows |")
    L.append("|---|---:|")
    vm = collections.Counter("%s / %s" % (r["visibility"], r["method"]) for r in tier_a if r["source"] == "urlscan")
    for k, n in vm.most_common():
        L.append("| %s | %d |" % (k, n))
    L.append("")
    with open(os.path.join(OUT, "summary.md"), "w") as f:
        f.write("\n".join(L))
    print("\n".join(L[:12]))
    print("... rows=%d tier_a=%d new_hosts=%d" % (len(rows), len(tier_a), len(new_hosts)))


if __name__ == "__main__":
    main()
