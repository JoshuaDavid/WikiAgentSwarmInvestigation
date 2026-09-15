#!/usr/bin/env python3
"""Export this analysis's clusters as records in jombb's collection schema.

jombb is imadreamerboy/just-one-more-bulletin-board, a community evidence
map for the incident. Its data lives in normalised JSONL collections
validated by scripts/validate.py. This script writes, under
outputs/jombb/, one file per collection holding only the rows we add:

  runs.jsonl            one run describing this harvest
  sources.jsonl         the dataset citation plus one representative
                        urlquery.net report locator per cluster
  entities.jsonl        one entity per cluster base host jombb lacks
  claims.jsonl          one bounded claim per cluster, plus one for the
                        smuggled-script mechanism
  relations.jsonl       source–claim–entity links
  urls.jsonl            the representative report locators
  tier_a_report_ids.txt the sorted UUID list of every tier A report
  evidence-set.reference.json
                        an aggregate evidence set over that list, for
                        reference only

jombb's validator pins its receipt inventory (urlquery-receipts.jsonl) and
its evidence-set inventory at fixed V5 contents, so neither receipts nor a
new set are applied; the UUID list and the reference set stand in for them. With --apply <clone>, the rows are appended to a clone of jombb
(skipping IDs that already exist) and jombb's validate.py and generate.py
are run there.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")
DEST = os.path.join(OUT, "jombb")
RUN_ID = "run-collusionwiki-scanner-pivot-20260915"
DATASET_SRC = "src-collusionwiki-scanner-pivot"
RUN_TIME = "2026-09-15T02:00:00Z"
REPO_PATH = "analyses/urlscan-urlquery-pivot/"
CORE_START, CORE_END = "2026-05-11", "2026-06-22"
REPS_PER_CLUSTER = 3

WRAPPER_HOSTS = {"markdown.new", "md.succ.ai", "pure.md", "r.jina.ai", "jqp.vercel.app", "allorigins.hexlet.app",
                 "api.allorigins.win", "api.microlink.io", "markdown.microlink.io", "text.microlink.io",
                 "html.microlink.io", "iad.microlink.io", "pdf.microlink.io", "microlink.io", "proxymule.com",
                 "cors.bwa.workers.dev", "corsmirror.com", "api.cors.lol", "test.cors.workers.dev",
                 "proxy.corsfix.com", "cors.io", "httpbingo.org", "httpbun.com", "deelay.me", "web.archive.org",
                 "arquivo.pt", "webcrawlerapi.com", "md.dhr.wtf", "platform.lemino.ai"}
SINK_HOSTS = {"httpbin.org", "eu.httpbin.org", "example.com", "example.org", "example.net"}
SHORTENER_HOSTS = {"is.gd", "2dd.pl", "vanderbi.lt", "bitily.in", "yourls.pro", "yourls.shop", "yourls.website",
                   "yourls.space", "yourls.biz", "goto.unm.edu", "uoft.me", "u.ethz.ch", "rmn.re", "lnkr.click",
                   "url.popcat.xyz", "t.mdcdev.me", "kodak.love", "zapro.si", "klickhier.at", "da.gd", "tinyurl.com", "v.gd"}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def url_id(u: str) -> str:
    return "url-" + hashlib.sha256(u.encode("utf-8")).hexdigest()[:16]


def rfc3339(t: str) -> tuple[str, str]:
    """'2026-06-18 23:25' -> ('2026-06-18T23:25:00Z', 'minute')."""
    t = t.strip()
    if len(t) >= 19:
        return t[:10] + "T" + t[11:19] + "Z", "second"
    return t[:10] + "T" + t[11:16] + ":00Z", "minute"


def entity_type(host: str) -> str:
    if host in WRAPPER_HOSTS:
        return "retrieval_service"
    if host in SHORTENER_HOSTS:
        return "public_object_service"
    if host in SINK_HOSTS:
        return "other"
    if host.endswith((".gov", ".gov.au", ".gov.uk", ".edu", ".org")) or any(
            k in host for k in ("unctad", "healthdata", "datausa", "sec.gov", "aihw", "acleddata", "statista", "datawrapper", "google.com")):
        return "data_provider"
    return "other"


def load_jombb(clone: str | None) -> dict[str, dict]:
    existing: dict[str, dict] = {"ids": {}, "entity_by_host": {}, "url_ids": set(), "source_tuples": set()}
    if not clone:
        return existing
    for name in ("entities", "sources", "claims", "relations", "urls", "evidence-sets", "runs", "search-events", "urlquery-receipts", "iowa-objects"):
        p = os.path.join(clone, "data", name + ".jsonl")
        if not os.path.exists(p):
            continue
        for line in open(p):
            row = json.loads(line)
            existing["ids"][row["id"]] = name
            if name == "entities":
                existing["entity_by_host"][row["canonical_host"]] = row["id"]
            if name == "urls":
                existing["url_ids"].add(row["id"])
            if name == "sources":
                existing["source_tuples"].add((row.get("source_url"), row.get("source_revision")))
    return existing


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pr-url", required=True)
    ap.add_argument("--commit", required=True, help="commit of this repo the records cite")
    ap.add_argument("--jombb", help="path to a clone of just-one-more-bulletin-board")
    ap.add_argument("--apply", action="store_true", help="append rows to the clone and run its validate/generate")
    args = ap.parse_args()
    os.makedirs(DEST, exist_ok=True)
    existing = load_jombb(args.jombb)

    rows = [json.loads(l) for l in open(os.path.join(OUT, "rows.jsonl"))]
    tier_a = [r for r in rows if r["tier"] == "A" and r["source"] == "urlquery" and r["in_window"] and r["id"]]
    enriched = set()
    p = os.path.join(OUT, "urlquery", "transactions.jsonl")
    if os.path.exists(p):
        enriched = {json.loads(l)["report_id"] for l in open(p)}
    clusters = list(csv.DictReader(open(os.path.join(OUT, "clusters.tsv")), delimiter="\t"))
    payloads = [json.loads(l) for l in open(os.path.join(OUT, "httpbin_payloads.jsonl"))] if os.path.exists(os.path.join(OUT, "httpbin_payloads.jsonl")) else []
    by_host = collections.defaultdict(list)
    for r in tier_a:
        by_host[r["base_host"]].append(r)

    runs = [{
        "id": RUN_ID, "observed_at": RUN_TIME,
        "source_scope": "urlscan.io and urlquery.net public search rows for swarm-related hosts and URL tell strings, plus Wayback CDX capture lists",
        "method": "Search-row harvest by host and tell string, URL-shape predicate triage, wrapper peeling to the innermost host, burst grouping by base host, HTTP transaction readback for a sample of reports",
        "status": "complete",
        "notes": "Scripts, outputs and README are in the collusionwiki repository under %s at commit %s." % (REPO_PATH, args.commit),
    }]
    sources = [{
        "id": DATASET_SRC, "source_url": args.pr_url, "source_revision": args.commit,
        "first_seen_at": RUN_TIME, "first_seen_precision": "date", "canonical_host": "github.com",
        "evidence_type": "research_summary", "publication_status": "public", "risk_tags": ["none"], "safe_to_open": "yes",
        "notes": "Pull request carrying the harvest scripts, redacted search rows, cluster table and decoded smuggled-script payloads.",
    }]
    entities, claims, relations, urls, url_ids_out = [], [], [], [], []
    claim_ids = []
    # Every source_url must also exist as an exact URL row.
    pr_uid = url_id(args.pr_url)
    if pr_uid not in existing["url_ids"]:
        urls.append({"id": pr_uid, "url": args.pr_url, "canonical_host": "github.com",
                     "labels": ["collusionwiki dataset pull request"], "discovered_in": [RUN_ID], "mention_count": 1,
                     "risk_tags": ["none"], "safe_to_open": "yes",
                     "notes": "Pull request carrying the cited scripts and outputs."})

    def add_url(report_url: str, label: str) -> str:
        uid = url_id(report_url)
        if uid not in existing["url_ids"] and uid not in {u["id"] for u in urls}:
            urls.append({"id": uid, "url": report_url, "canonical_host": "urlquery.net", "labels": [label],
                         "discovered_in": [RUN_ID], "mention_count": 1, "risk_tags": ["external_logging"],
                         "safe_to_open": "caution",
                         "notes": "Published as an exact literal; only the report locator is published."})
        return uid

    def entity_for(host: str, role_note: str) -> str:
        if host in existing["entity_by_host"]:
            return existing["entity_by_host"][host]
        eid = "ent-cw-" + slug(host)
        if eid not in {e["id"] for e in entities}:
            entities.append({"id": eid, "name": host, "entity_type": entity_type(host), "canonical_host": host,
                             "notes": role_note})
        return eid

    for c in clusters:
        host = c["base_host"]
        reps = sorted(by_host.get(host, []), key=lambda r: (r["id"] in enriched, r["time"]), reverse=True)[:REPS_PER_CLUSTER]
        if not reps:
            continue
        sl = slug(host)
        wrappers = c["top_wrappers"]
        new_to_corpus = c["base_host_in_corpus"] == "no"
        new_to_termina = c["base_host_known_to_termina"] == "no"
        verified = any(r["id"] in enriched for r in reps)
        # representative source
        rep = reps[0]
        ts, prec = rfc3339(rep["time"])
        src_id = "src-cw-" + sl
        src_tuple = (rep["link"], rep["id"][:8] + " safe public receipt")
        if src_tuple not in existing["source_tuples"]:
            sources.append({"id": src_id, "source_url": rep["link"], "source_revision": src_tuple[1],
                            "first_seen_at": ts, "first_seen_precision": prec, "canonical_host": "urlquery.net",
                            "evidence_type": "indexed_record", "publication_status": "public",
                            "risk_tags": ["external_logging"], "safe_to_open": "caution",
                            "notes": "Representative receipt for the %s cluster; only the report locator is published. Submitted through %s." % (host, rep["page_host"])})
        for r in reps:
            url_ids_out.append(add_url(r["link"], "collusionwiki cluster " + host))
        ent_id = entity_for(host, "Innermost host of a urlquery.net fetch cluster in the collusionwiki scanner harvest.")
        cid = "clm-cw-" + sl
        claim_ids.append(cid)
        claims.append({
            "id": cid, "category": "scanner-relay-fetch",
            "summary": "%s urlquery.net receipts between %s and %s submit %s URLs, mostly through %s, in %s distinct URL spellings." % (
                c["tier_a_rows"], c["first"][:10], c["last"][:10], host, wrappers.split(";")[0].strip(), c["distinct_urls"]),
            "claim_class": "observed_fact",
            "relevance": "high" if new_to_corpus else "medium",
            "attribution_boundary": "urlquery.net does not expose the submitter. Same-submitter grouping rests on URL shape, wrapper choice and burst timing; scans by unrelated submitters on the same host in the same window are not separable.",
            "novelty_vs_original_report": "absent" if new_to_corpus else "partly_known",
            "investigation_status": "new_record" if (new_to_corpus and new_to_termina) else "deeper_analysis",
            "verification_state": "verified_live_readback" if verified else "indexed_only",
            "review_method": "Search-row harvest, predicate triage and wrapper peeling; HTTP transaction readback on a sample." if verified else "Search-row harvest, predicate triage and wrapper peeling.",
            "caveat": "Receipt timestamps are minute-resolution scanner times. The task behind the fetches is inferred from URL shape, not from any prompt.",
            "notes": "Base host %s in the collusionwiki corpus; %s to termina.digital venue tables. Full row set: %soutputs/clusters.tsv." % (
                "absent" if new_to_corpus else "present", "unknown" if new_to_termina else "known", REPO_PATH),
        })
        relations.append({"id": "rel-cw-%s-receipt" % sl, "source_id": src_id if src_tuple not in existing["source_tuples"] else DATASET_SRC,
                          "claim_id": cid, "entity_id": ent_id, "relation_type": "records-relay-fetch",
                          "support_type": "supports", "evidence_strength": "high" if verified else "medium",
                          "notes": "Representative receipt for the cluster."})
        relations.append({"id": "rel-cw-%s-dataset" % sl, "source_id": DATASET_SRC, "claim_id": cid, "entity_id": ent_id,
                          "relation_type": "aggregates-receipts", "support_type": "context", "evidence_strength": "medium",
                          "notes": "Cluster table and per-row tells in the cited dataset."})

    # mechanism claim: smuggled scripts
    core_payloads = [x for x in payloads if x["in_core"] and x["source"] == "urlquery"]
    if core_payloads:
        rep = sorted(core_payloads, key=lambda x: x["time"], reverse=True)[0]
        mech_src = "src-cw-smuggled-script"
        ts, prec = rfc3339(rep["time"])
        sources.append({"id": mech_src, "source_url": rep["link"], "source_revision": rep["id"][:8] + " safe public receipt",
                        "first_seen_at": ts, "first_seen_precision": prec, "canonical_host": "urlquery.net",
                        "evidence_type": "indexed_record", "publication_status": "public",
                        "risk_tags": ["external_logging", "server_side_fetch"], "safe_to_open": "caution",
                        "notes": "Representative httpbin.org/base64 submission; the decoded page runs a script in the scanner's browser. Only the locator is published."})
        url_ids_out.append(add_url(rep["link"], "collusionwiki smuggled-script receipt"))
        ent_id = entity_for("httpbin.org", "Echo service whose /base64/ path serves caller-supplied HTML; used to run scripts inside URL scanners.")
        hosts = collections.Counter(h for x in core_payloads for h in x["hosts"])
        cid = "clm-cw-scanner-remote-browser"
        claim_ids.append(cid)
        claims.append({
            "id": cid, "category": "runtime-harness-probing",
            "summary": "%d core-window urlquery.net receipts submit httpbin.org/base64/ URLs whose decoded HTML runs scripts in the scanner's browser; the scripts most often load %s and %s and write results into the page title or a final navigation URL." % (
                len(core_payloads), hosts.most_common(1)[0][0], hosts.most_common(2)[1][0]),
            "claim_class": "observed_fact", "relevance": "high",
            "attribution_boundary": "The scripts and their targets are observed in the submitted URLs; who submitted them and whether results were consumed is not authenticated.",
            "novelty_vs_original_report": "absent", "investigation_status": "deeper_analysis",
            "verification_state": "verified_live_readback",
            "review_method": "Base64 decoding of every submitted URL of that shape; report-title readback on a sample.",
            "caveat": "Payloads after 2026-06-22 include unrelated scanner tests and are excluded from the count.",
            "notes": "Decoded payloads with referenced hosts: %soutputs/httpbin_payloads.jsonl." % REPO_PATH,
        })
        relations.append({"id": "rel-cw-remote-browser-receipt", "source_id": mech_src, "claim_id": cid, "entity_id": ent_id,
                          "relation_type": "runs-script-in-scanner", "support_type": "supports", "evidence_strength": "high",
                          "notes": "Representative decoded payload."})

    # aggregate evidence set over every tier A urlquery UUID
    ids = sorted({r["id"] for r in tier_a})
    blob = ("\n".join(ids) + "\n").encode("utf-8")
    with open(os.path.join(DEST, "tier_a_report_ids.txt"), "wb") as f:
        f.write(blob)
    h = hashlib.sha256(blob).hexdigest()
    part = collections.Counter(r["base_host"] or "(none)" for r in tier_a)
    top = part.most_common(20)
    partitions = []
    seen_names = set()
    for k, n in top:
        name = slug(k) or "none"
        if name in seen_names:
            name += "-%d" % len(seen_names)
        seen_names.add(name)
        partitions.append({"name": name, "count": n})
    rest = len(tier_a) - sum(n for _, n in top)
    if rest:
        partitions.append({"name": "other-hosts", "count": rest})
    sets = [{
        "id": "set-cw-urlquery-tier-a", "parent_set_id": None, "run_id": RUN_ID, "claim_ids": claim_ids,
        "name": "collusionwiki tier A urlquery.net receipt inventory (aggregate)",
        "set_type": "aggregate", "member_collection": "aggregate",
        "member_count": len(ids), "published_url_count": len(set(url_ids_out)), "withheld_count": len(ids) - len(set(url_ids_out)),
        "manifest_sha256": h, "member_ids_sha256": h, "partitions": partitions,
        "distinct_body_count": None, "epoch_count_reported": None, "epoch_count_receipt_verified": None, "epoch_prefix_rows": None,
        "representative_url_ids": sorted(set(url_ids_out)),
        "notes": "Members are urlquery.net report UUIDs listed in %soutputs/jombb/tier_a_report_ids.txt; the hash is SHA-256 over the sorted list joined by newline with a final newline." % REPO_PATH,
    }]

    # jombb's validator pins its V5 evidence-set inventory, so the aggregate
    # set is written for reference only and not applied to the clone.
    with open(os.path.join(DEST, "evidence-set.reference.json"), "w") as f:
        json.dump(sets[0], f, indent=1)
    files = {"runs.jsonl": runs, "sources.jsonl": sources, "entities.jsonl": entities, "claims.jsonl": claims,
             "relations.jsonl": relations, "urls.jsonl": urls}
    for name, recs in files.items():
        with open(os.path.join(DEST, name), "w") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
        print(f"{name:22} {len(recs)}")

    if args.apply and args.jombb:
        for name, recs in files.items():
            p = os.path.join(args.jombb, "data", name)
            have = {json.loads(l)["id"] for l in open(p)} if os.path.exists(p) else set()
            with open(p, "a") as f:
                for r in recs:
                    if r["id"] not in have:
                        f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
        for script in ("generate.py", "validate.py"):
            res = subprocess.run([sys.executable, os.path.join("scripts", script)], cwd=args.jombb, capture_output=True, text=True)
            print(f"--- jombb {script}: exit {res.returncode}\n{(res.stdout + res.stderr)[-1500:]}")


if __name__ == "__main__":
    main()
