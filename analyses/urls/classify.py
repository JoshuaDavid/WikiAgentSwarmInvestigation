#!/usr/bin/env python3
"""Classify extracted URLs by host into functional categories."""

from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "outputs"
URLS_JSONL = OUT_DIR / "urls.jsonl"
HOSTS_TSV = OUT_DIR / "urls-by-host.tsv"
OUT_JSONL = OUT_DIR / "urls-classified.jsonl"
OUT_CATEGORY_TSV = OUT_DIR / "urls-by-category.tsv"
OUT_HOST_TSV = OUT_DIR / "urls-hosts-classified.tsv"

# Category definitions.
#
# Order matters — the first matching rule wins. Each rule is (category, matcher).
# The matcher runs against the *decoded* host (percent-decoded, HTML-entity
# decoded, lowercased, trailing-dot stripped). Rules that need to keep the raw
# host — the obfuscation category, mainly — check the raw string instead.

CATEGORIES: list[tuple[str, str]] = [
    ("wiki_self",                "own-wiki: the ProWiki farm being written to (self-links, sandbox, sister wikis)."),
    ("fetch_proxy_markdown",     "URL→Markdown/HTML fetch services: used to pull remote pages through a third party that returns plain text (bypasses CORS and, in some cases, robots/CF blocks)."),
    ("cors_proxy",               "Generic CORS-bypass HTTP proxies (`?url=...` fetchers, workers.dev relays, allorigins clones)."),
    ("jq_json_relay",            "Hosted `jq` / JSON-transform playgrounds that accept `?url=...` and run arbitrary expressions on the response — used as a computation + fetch relay."),
    ("google_translate_proxy",   "Google Translate used as an HTTP proxy (`*.translate.goog` mirrors the target host with query rewriting)."),
    ("archive_wayback",          "Wayback / archive services used to retrieve blocked pages via historical snapshots."),
    ("url_shortener",            "URL shorteners — obscure the destination in the wiki text."),
    ("counter_signalling",       "Public hit-counter APIs — usable as low-bandwidth cross-agent coordination channels."),
    ("cloud_storage_dropbox",    "Cloud object storage and ad-hoc tunnels (Azure blob, Google user-content, pinggy tunnels, serveo user content). Typically dumping ground / drop-box."),
    ("google_docs",              "Google Docs / Drive / Search — either data sources or shared scratch space."),
    ("data_source_datausa",      "DataUSA endpoints (all subdomain variants)."),
    ("data_source_sec_investor", "SEC / investor.gov — target of many benchmark tasks."),
    ("data_source_health",       "Health-data sources: AIHW (Australia), IHME (Global), OECD, Our World in Data, UNCTAD stats."),
    ("data_source_us_gov",       "Other US government sources: usaspending, census, MAX.gov, OMB."),
    ("data_source_finance",      "Financial-market sources: Yahoo Finance regional mirrors, Apple iTunes proxy."),
    ("data_source_library",      "Library/archive/CMS sources: contentdm, preservica, ArcGIS, Tableau, Power BI, ContentDM, university library repositories."),
    ("data_source_publishing",   "News/publisher archives: pagesuite, magazinearchive, patriotspoint, infogram."),
    ("data_source_other",        "Miscellaneous public data endpoints and reference sites (Common Crawl index, github APIs used as data source, dp.la, wordfinder, tigerweb)."),
    ("test_placeholder",         "Test/placeholder hosts: example.com, httpbin, jsonplaceholder, jokeapi."),
    ("obfuscated_or_malformed",  "Deliberately mangled host strings: percent-encoded letters, HTML-entity dots, appended `_NNNN` pseudo-ports, host-in-path smashing. All point at the same underlying targets — used to bypass filters/blocklists."),
    ("unclassified",             "Everything else."),
]

CATEGORY_DESCRIPTIONS = dict(CATEGORIES)

# Rules for the "decoded host" branch.
def category_from_decoded(host: str, raw_host: str) -> str:
    # --- obfuscation detection runs first on the RAW host ---
    if re.search(r"%[0-9a-fA-F]{2}", raw_host):
        return "obfuscated_or_malformed"
    if "&#" in raw_host:
        return "obfuscated_or_malformed"
    if re.search(r"_\d{3,}$", raw_host):
        return "obfuscated_or_malformed"
    if raw_host.endswith("."):
        return "obfuscated_or_malformed"
    if raw_host.endswith("="):
        return "obfuscated_or_malformed"
    if raw_host in {"www.sec&", "...", "...html"}:
        return "obfuscated_or_malformed"

    # --- self / farm ---
    if host.endswith("wikiservice.at") or host.endswith("wikiservice.com") or host.endswith("wikiservice.org"):
        return "wiki_self"
    if host.endswith("prowiki.org"):
        return "wiki_self"

    # --- Markdown/HTML fetch proxies ---
    md_hosts = {
        "r.jina.ai", "jina.ai", "r.jina-ai.workers.dev",
        "md.succ.ai", "md.dhr.wtf", "pure.md", "markdown.new",
        "markdown.microlink.io", "magic-html-api.vercel.app",
        "urltomarkdown.herokuapp.com", "api.microlink.io",
        "viewpagesource.online", "www.pageshot.site",
        "image.thum.io", "api.shotapi.io", "images.weserv.nl",
        "api.ocr.space",
    }
    if host in md_hosts:
        return "fetch_proxy_markdown"

    # --- CORS proxies / relays ---
    if host.endswith(".workers.dev") and ("cors" in host or "jina" in host or "test" in host or "findme" in host or "sirjosh" in host or "hanpengchen" in host or "hypnguyen" in host or "bwa" in host):
        return "cors_proxy"
    cors_hosts = {
        "allorigins.hexlet.app", "allorigins.win", "api.allorigins.win",
        "corsmirror.com", "api.cors.lol", "cors-anywhere.com",
        "cors-anywhere.herokuapp.com", "corsproxy.io",
        "thingproxy.freeboard.io", "cors.eu.org", "proxy.cors.sh",
        "proxy.corsfix.com", "cors.isomorphic-git.org",
        "vercel-cors-proxy.vercel.app", "vercel-cors-proxy-lokal.vercel.app",
        "cors-bypasser-pro.vercel.app", "proxy-mu-seven-70.vercel.app",
        "api.codetabs.com", "thenacken-python-cors-proxy.hf.space",
        "jsonp.afeld.me", "www.proxymule.com", "proxymule.com",
        "webcrawlerapi.com",
    }
    if host in cors_hosts:
        return "cors_proxy"

    # --- jq / JSON transformation relay ---
    if host in {
        "jqp.vercel.app", "jqp-git-main-sighrobot.vercel.app",
        "jsonhero.io", "jsonformatter.curiousconcept.com",
        "codebeautify.org",
    }:
        return "jq_json_relay"

    # --- Google Translate as proxy ---
    if host.endswith(".translate.goog"):
        return "google_translate_proxy"
    if host in {"translate.google.com", "translate-pa.googleapis.com"}:
        return "google_translate_proxy"

    # --- archive / wayback ---
    if host in {
        "web.archive.org", "archive.org",
        "wayback.archive.org", "wayback.archive-it.org", "archive-it.org",
        "memgator.cs.odu.edu",
        "index.commoncrawl.org",
    } or host == "sec.govwayback.com":  # typosquat wayback
        return "archive_wayback"

    # --- URL shorteners ---
    shorteners = {
        "is.gd", "v.gd", "da.gd", "tinyurl.com", "ctxr.me",
        "bitily.in", "app.bitily.in", "2dd.pl", "1word.ws",
        "word.tips",
    }
    if host in shorteners:
        return "url_shortener"

    # --- Counter APIs (signalling) ---
    if host in {"api.counterapi.dev", "countapi.mileshilliard.com"}:
        return "counter_signalling"

    # --- Cloud storage & tunnels ---
    if host.endswith(".blob.core.windows.net"):
        return "cloud_storage_dropbox"
    if host.endswith(".serveousercontent.com") or host.endswith(".run.pinggy-free.link"):
        return "cloud_storage_dropbox"
    if host.endswith(".googleusercontent.com"):
        return "cloud_storage_dropbox"
    if host in {"www.datalumos.org"}:
        return "cloud_storage_dropbox"

    # --- Google docs / drive / search ---
    if host in {"docs.google.com", "drive.google.com", "www.google.com"}:
        return "google_docs"

    # --- Data source: DataUSA ---
    if host.endswith("datausa.io"):
        return "data_source_datausa"

    # --- Data source: SEC / investor.gov ---
    if host in {"www.sec.gov", "sec.gov", "data.sec.gov", "www.investor.gov", "investor.gov"}:
        return "data_source_sec_investor"

    # --- Data source: Health / policy ---
    if host in {
        "www.aihw.gov.au", "viz.aihw.gov.au", "vizprod.aihw.gov.au",
        "vizhub.healthdata.org",
        "www.oecd.org",
        "api.ourworldindata.org",
        "unctadstat.unctad.org", "unctadstat-api.unctad.org",
    }:
        return "data_source_health"

    # --- Data source: US Gov (non-SEC/DataUSA) ---
    if host in {
        "api.usaspending.gov", "files.usaspending.gov",
        "api.census.gov", "tigerweb.geo.census.gov",
        "portal.max.gov", "piv.max.gov", "login.max.gov", "max.omb.gov",
    }:
        return "data_source_us_gov"

    # --- Finance ---
    if host in {
        "finance.yahoo.com", "ca.finance.yahoo.com", "finance.yahoo.co.jp",
        "query1.finance.yahoo.com", "query2.finance.yahoo.com",
        "proxy-itunes.apple.com",
    }:
        return "data_source_finance"

    # --- Library / archive / GIS / dashboards ---
    if host in {
        "hub.catalogit.app", "api.catalogit.app",
        "rspace.library.cofc.edu", "lcdl.library.cofc.edu", "iiif.library.cofc.edu",
        "cdm16022.contentdm.oclc.org", "www.cdm16022.contentdm.oclc.org",
        "localhost.cdm16022.contentdm.oclc.org",
        "cgsc.contentdm.oclc.org", "server16022.contentdm.oclc.org",
        "collection.mndigital.org", "reflections.mndigital.org",
        "metl.lib.umn.edu", "vanderbi.lt",
        "tsl.preservica.com", "tsl.access.preservica.com",
        "services3.arcgis.com",
        "app.powerbi.com", "public.tableau.com",
        "platform.lemino.ai",
    }:
        return "data_source_library"

    # --- Publishing / news archives ---
    if host in {
        "pages.pagesuite.com", "editions.pagesuite.com",
        "www.themagazinearchive.com", "editions.themagazinearchive.org",
        "www.patriotspoint.org",
        "e.infogram.com", "infogram.com",
    }:
        return "data_source_publishing"

    # --- Other data endpoints ---
    if host in {
        "api.github.com", "raw.githubusercontent.com", "raw.githack.com",
        "api.dp.la", "dp.la",
        "fly.wordfinderapi.com",
        "housingdata.org", "code.highcharts.com",
    }:
        return "data_source_other"

    # --- Test / placeholder ---
    if host in {
        "example.com", "example.org", "example.net", "www.example.com",
        "httpbin.org", "eu.httpbin.org",
        "jsonplaceholder.typicode.com",
        "v2.jokeapi.dev",
    }:
        return "test_placeholder"

    # --- Suspicious infra ---
    if host in {
        "ir.intrusion.com", "urlquery.net",
    }:
        return "cloud_storage_dropbox"  # fold in as infra

    return "unclassified"


def decode_host(raw: str) -> str:
    import urllib.parse as up
    h = raw
    try:
        h = up.unquote(h)
        h = up.unquote(h)  # double decode common case
    except Exception:
        pass
    h = h.replace("&#46;", ".")
    return h.lower().rstrip(".")


def main() -> None:
    # Classify all hosts.
    host_to_category: dict[str, str] = {}
    with HOSTS_TSV.open("r", encoding="utf-8") as hf:
        next(hf)  # header
        for line in hf:
            host, _count = line.rstrip("\n").split("\t")
            decoded = decode_host(host)
            host_to_category[host] = category_from_decoded(decoded, host)

    # Emit per-URL classified stream (rewriting urls.jsonl with an extra field).
    per_category = Counter()
    per_category_hosts: dict[str, set[str]] = defaultdict(set)
    per_wiki_category = defaultdict(Counter)

    with URLS_JSONL.open("r", encoding="utf-8") as rf, OUT_JSONL.open("w", encoding="utf-8") as wf:
        for line in rf:
            rec = json.loads(line)
            host = rec["host"]
            cat = host_to_category.get(host, "unclassified")
            rec["category"] = cat
            wf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            per_category[cat] += 1
            per_category_hosts[cat].add(host)
            per_wiki_category[rec.get("wiki") or "?"][cat] += 1

    # Category totals.
    with OUT_CATEGORY_TSV.open("w", encoding="utf-8") as cf:
        cf.write("category\turl_occurrences\tdistinct_hosts\tdescription\n")
        for cat, _desc in CATEGORIES:
            cf.write(f"{cat}\t{per_category[cat]}\t{len(per_category_hosts[cat])}\t{CATEGORY_DESCRIPTIONS[cat]}\n")

    # Per-host + category.
    host_count = {}
    with HOSTS_TSV.open("r", encoding="utf-8") as hf:
        next(hf)
        for line in hf:
            host, count = line.rstrip("\n").split("\t")
            host_count[host] = int(count)
    with OUT_HOST_TSV.open("w", encoding="utf-8") as hf:
        hf.write("category\thost\turl_occurrences\n")
        rows = sorted(host_count.items(), key=lambda kv: (host_to_category[kv[0]], -kv[1]))
        for host, count in rows:
            hf.write(f"{host_to_category[host]}\t{host}\t{count}\n")

    total = sum(per_category.values())
    print(f"total URL occurrences: {total}", file=sys.stderr)
    for cat, _ in CATEGORIES:
        print(f"  {cat:32s} {per_category[cat]:8d}   ({len(per_category_hosts[cat])} hosts)", file=sys.stderr)
    print(f"wrote {OUT_JSONL}", file=sys.stderr)
    print(f"wrote {OUT_CATEGORY_TSV}", file=sys.stderr)
    print(f"wrote {OUT_HOST_TSV}", file=sys.stderr)


if __name__ == "__main__":
    main()
