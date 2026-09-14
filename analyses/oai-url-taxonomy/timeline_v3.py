#!/usr/bin/env python3
"""Corrected timeline with 3 example (url, first_seen_query, crawl_date) tuples per row.

Same detectors as timeline_v2.py. For each technique we pick the earliest 3
matching URLs by crawl-date-any, and show the shortest illustrative sighting
for each.
"""

import json
import re
import sys

PARSED_PATH = "/collusionwiki/analyses/oai-url-taxonomy/outputs/urls.parsed.jsonl"
HISTORY_PATH = "/collusionwiki/analyses/oai-url-taxonomy/outputs/urls_history.jsonl"

# --- load and join ---

hist = {}
with open(HISTORY_PATH) as f:
    for line in f:
        h = json.loads(line)
        hist[h["url"]] = h

rows = []
with open(PARSED_PATH) as f:
    for line in f:
        r = json.loads(line)
        h = hist.get(r["url"], {})
        r["history"] = h
        rows.append(r)


# --- detectors (same as v2) ---

JS_EXEC = {"r.jina.ai", "s.jina.ai", "md.succ.ai", "pure.md", "markdown.new",
           "platform.lemino.ai", "api.microlink.io", "web2md.site",
           "markdown.microlink.io"}

def in_wrappers(name): return lambda r: name in (r["parsed"].get("wrappers") or [])
def in_url(*subs): return lambda r: any(s.lower() in r["url"].lower() for s in subs)
def in_url_or_encoded(*subs):
    import urllib.parse
    def _f(r):
        u = r["url"].lower()
        try:
            dec = urllib.parse.unquote(urllib.parse.unquote(u))
        except Exception:
            dec = u
        return any((s.lower() in u) or (s.lower() in dec) for s in subs)
    return _f
def jq_matches(pat):
    p = re.compile(pat)
    return lambda r: any(x.get("type")=="jq" and p.search(x.get("value") or "")
                          for x in (r["parsed"].get("transforms") or []))
def transform_type(name):
    return lambda r: any(x.get("type")==name for x in (r["parsed"].get("transforms") or []))
def multihop(): return lambda r: len(r["parsed"].get("wrappers") or []) >= 2
def jsexec_wraps_httpbin():
    return lambda r: "httpbin.org" in r["url"] and any(
        w in JS_EXEC for w in (r["parsed"].get("wrappers") or []))

import base64 as _b64
def in_decoded_httpbin_base64(*subs):
    def _f(r):
        u = r["url"]
        m = re.search(r"httpbin\.org/base64/([^?&#\s]+)", u)
        if not m: return False
        payload = m.group(1)
        if "[...]" in payload: payload = payload.split("[...]")[0]
        for dec in (_b64.urlsafe_b64decode, _b64.b64decode):
            for pad in ("", "=", "==", "==="):
                try:
                    out = dec(payload + pad).decode("utf-8", errors="replace")
                    return any(s.lower() in out.lower() for s in subs)
                except Exception: pass
        for trim in range(1, 8):
            for dec in (_b64.urlsafe_b64decode, _b64.b64decode):
                for pad in ("", "=", "==", "==="):
                    try:
                        out = dec(payload[:-trim] + pad).decode("utf-8", errors="replace")
                        return any(s.lower() in out.lower() for s in subs)
                    except Exception: pass
        return False
    return _f


TECHNIQUES = [
    ("compositional: multi-hop chain ≥2", multihop()),
    ("encoding: %25 double-encoding",     in_url("https%253A")),
    ("yourls admin: sort_by=timestamp",   in_url("sort_by=timestamp")),
    ("wrapper: allorigins.hexlet.app",    in_wrappers("allorigins.hexlet.app")),
    ("wrapper: cors.bwa.workers.dev",     in_wrappers("cors.bwa.workers.dev")),
    ("wrapper: proxymule.com",            in_wrappers("proxymule.com")),
    ("payload: httpbin.org/base64/",      in_url("httpbin.org/base64/")),
    ("target: investor.gov/files/county.json", in_url_or_encoded("investor.gov/files/county.json")),
    ("target: finance.yahoo.com/quote",   in_url("finance.yahoo.com/quote")),
    ("wrapper: s.jina.ai",                in_wrappers("s.jina.ai")),
    ("shortcode: agiq",                   in_url("agiq47", "agiq")),
    ("shortcode: OAIJAN/OAIAUG",          in_url("OAIJAN", "OAIAUG")),
    ("wrapper: everyorigin.deno.dev",     in_wrappers("everyorigin.deno.dev")),
    ("compositional: js-exec wraps httpbin", jsexec_wraps_httpbin()),
    ("shortcode: ag0ref in b64",          in_decoded_httpbin_base64("ag0ref")),
    ("transform: jq= filter",             transform_type("jq")),
    ("jq: regCF_county_2021",             jq_matches(r"regCF_county_2021")),
    ("jq: MA geo-selector",               jq_matches(r'(us-ma-|code\[3:5\]\s*==\s*"ma")')),
    ("target: nomisweb NM_",              lambda r: bool(re.search(r"nomisweb\.co\.uk/api/v01/dataset/NM_", r["url"]))),
    ("target: api.datausa.io tesseract",  in_url("api.datausa.io/tesseract")),
    ("wrapper: api.microlink.io",         in_wrappers("api.microlink.io")),
    ("wrapper: api.codetabs.com",         in_wrappers("api.codetabs.com")),
    ("wrapper: platform.lemino.ai",       in_wrappers("platform.lemino.ai")),
    ("wrapper: proxy.cors.sh",            in_wrappers("proxy.cors.sh")),
    ("jq: regCF_county_2019",             jq_matches(r"regCF_county_2019")),
    ("shortcode: SECcountyM",             in_url("SECcountyM", "seccountym")),
    ("target: code.highcharts.com us-ma", lambda r: "code.highcharts.com" in r["url"] and "us-ma" in r["url"]),
    ("payload: httpbin.org/redirect-to",  in_url("httpbin.org/redirect-to")),
    ("jq: regCF_county_2020",             jq_matches(r"regCF_county_2020")),
    ("jq: cents-to-dollars .usd/10",      jq_matches(r"\.usd\s*/\s*10")),
    ("encoding: double-slash //",         in_url("//files//", "sec.gov//")),
    ("transform: data.markdown.attr",     transform_type("data.markdown.attr")),
    ("wrapper: translate.goog mangle",    in_url(".translate.goog")),
    ("encoding: %2525 triple-encoding",   in_url("%25253A")),
    ("cache-bust: ?fresh=",               in_url("?fresh=", "&fresh=")),
    ("encoding: %2E-for-dot",             in_url("county%2Ejson", "%2Ejson")),
    ("shortcode: OpenAIRegCFTest",        in_url("OpenAIRegCFTest")),
    ("shortcode: agwpc2018/2020",         in_url("agwpc2018", "agwpc2020")),
    ("shortcode: SEC regCF data blob in b64", in_decoded_httpbin_base64("SEC regCF", "SEC county.json regCF")),
    ("cache-bust: ?forcefreshmethod=",    in_url("forcefreshmethod")),
    ("cache-bust: ?refok=1",              in_url("refok=1")),
    ("shortcode: agtstsum",               in_url("agtstsum")),
    ("target: data.nysed.gov/comparison", in_url_or_encoded("data.nysed.gov/comparison", "data.nysed.gov%2Fcomparison")),
    ("target: data.nysed.gov/enrollment", in_url_or_encoded("data.nysed.gov/enrollment", "data.nysed.gov%2Fenrollment")),
    ("shortcode: SECjqpsliceMASS in b64", in_decoded_httpbin_base64("SECJQPSLICEMASS")),
]


def truncate(s, n):
    if not s: return ""
    return s if len(s) <= n else s[:n-1] + "…"


def pick_earliest_examples(matches, k=3):
    """Return k earliest examples across all sightings.
    Prefer non-researcher sightings; fall back to any."""
    # Flatten to (crawl_date, url, sighting)
    triples = []
    for r in matches:
        for s in r.get("history", {}).get("sightings", []):
            if not s.get("crawl"): continue
            triples.append((s["crawl"], s.get("is_researcher_page", False),
                            r["url"], s))
    # Sort by (researcher last, crawl date), dedupe by URL
    triples.sort(key=lambda t: (t[1], t[0]))
    seen = set()
    picked = []
    for crawl, is_r, url, s in triples:
        if url in seen: continue
        seen.add(url)
        picked.append((crawl, is_r, url, s))
        if len(picked) >= k: break
    return picked


def main():
    for name, pred in TECHNIQUES:
        matches = [r for r in rows if pred(r)]
        n = len(matches)
        if n == 0:
            print(f"\n### {name}   (n=0)  — no matches")
            continue

        e_nr_dates = [r["history"].get("earliest_crawl_nonresearcher")
                      for r in matches
                      if r.get("history", {}).get("earliest_crawl_nonresearcher")]
        min_nr = min(e_nr_dates) if e_nr_dates else "researcher-only"

        print(f"\n### {name}   (n={n}, earliest_nonresearcher={min_nr})")
        for crawl, is_r, url, s in pick_earliest_examples(matches, 3):
            tag = " [via researcher]" if is_r else ""
            print(f"  · crawl={crawl}{tag}   fsq={s.get('fsq','')!r}")
            print(f"    url: {truncate(url, 200)}")
            print(f"    first_page: {truncate(s.get('first_page_url',''), 140)}")


if __name__ == "__main__":
    main()
