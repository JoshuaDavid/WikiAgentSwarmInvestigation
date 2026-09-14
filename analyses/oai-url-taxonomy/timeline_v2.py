#!/usr/bin/env python3
"""Corrected technique timeline.

For each technique fingerprint, find the earliest crawl date across all URLs
that match, from three perspectives:

  earliest_any:            min crawl date across ALL sightings (any first_page_url)
  earliest_nonresearcher:  min crawl date across sightings whose first_page_url
                           is NOT a known researcher writeup host
  earliest_shard:          min first-shard date across matching URLs (for
                           comparison with the earlier flawed analysis)

Techniques where earliest_nonresearcher is None have zero swarm-surface
sightings and are visible only through researcher writeups — we cannot date
them independently.
"""

import json
import re
import sys
from collections import defaultdict

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

print(f"joined {len(rows)} rows  (history lookups hit: "
      f"{sum(1 for r in rows if r.get('history'))})", file=sys.stderr)


# --- detectors ---

JS_EXEC = {"r.jina.ai", "s.jina.ai", "md.succ.ai", "pure.md", "markdown.new",
           "platform.lemino.ai", "api.microlink.io", "web2md.site",
           "markdown.microlink.io"}


def in_wrappers(name):
    return lambda r: name in (r["parsed"].get("wrappers") or [])


def in_url(*subs):
    return lambda r: any(s.lower() in r["url"].lower() for s in subs)


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
    def _f(r):
        for x in (r["parsed"].get("transforms") or []):
            if x.get("type") == "jq" and p.search(x.get("value") or ""):
                return True
        return False
    return _f


def transform_type(name):
    def _f(r):
        for x in (r["parsed"].get("transforms") or []):
            if x.get("type") == name:
                return True
        return False
    return _f


import base64 as _b64


def in_decoded_httpbin_base64(*subs):
    def _f(r):
        u = r["url"]
        m = re.search(r"httpbin\.org/base64/([^?&#\s]+)", u)
        if not m:
            return False
        payload = m.group(1)
        if "[...]" in payload:
            payload = payload.split("[...]")[0]
        for dec in (_b64.urlsafe_b64decode, _b64.b64decode):
            for pad in ("", "=", "==", "==="):
                try:
                    out = dec(payload + pad).decode("utf-8", errors="replace")
                    return any(s.lower() in out.lower() for s in subs)
                except Exception:
                    pass
        for trim in range(1, 8):
            for dec in (_b64.urlsafe_b64decode, _b64.b64decode):
                for pad in ("", "=", "==", "==="):
                    try:
                        out = dec(payload[:-trim] + pad).decode("utf-8", errors="replace")
                        return any(s.lower() in out.lower() for s in subs)
                    except Exception:
                        pass
        return False
    return _f


def multihop():
    return lambda r: len(r["parsed"].get("wrappers") or []) >= 2


def jsexec_wraps_httpbin():
    def _f(r):
        return "httpbin.org" in r["url"] and any(
            w in JS_EXEC for w in (r["parsed"].get("wrappers") or [])
        )
    return _f


TECHNIQUES = [
    # Wrappers
    ("wrapper: r.jina.ai",              in_wrappers("r.jina.ai")),
    ("wrapper: s.jina.ai",              in_wrappers("s.jina.ai")),
    ("wrapper: md.succ.ai",             in_wrappers("md.succ.ai")),
    ("wrapper: pure.md",                in_wrappers("pure.md")),
    ("wrapper: markdown.new",           in_wrappers("markdown.new")),
    ("wrapper: allorigins.hexlet.app",  in_wrappers("allorigins.hexlet.app")),
    ("wrapper: api.allorigins.win",     in_wrappers("api.allorigins.win")),
    ("wrapper: jqp.vercel.app",         in_wrappers("jqp.vercel.app")),
    ("wrapper: api.microlink.io",       in_wrappers("api.microlink.io")),
    ("wrapper: everyorigin.deno.dev",   in_wrappers("everyorigin.deno.dev")),
    ("wrapper: corsproxy.io",           in_wrappers("corsproxy.io")),
    ("wrapper: api.codetabs.com",       in_wrappers("api.codetabs.com")),
    ("wrapper: cors.bwa.workers.dev",   in_wrappers("cors.bwa.workers.dev")),
    ("wrapper: proxy.cors.sh",          in_wrappers("proxy.cors.sh")),
    ("wrapper: proxymule.com",          in_wrappers("proxymule.com")),
    ("wrapper: platform.lemino.ai",     in_wrappers("platform.lemino.ai")),
    ("wrapper: web.archive.org",        in_wrappers("web.archive.org")),
    ("wrapper: archive.ph",             in_wrappers("archive.ph")),
    ("wrapper: rt.http3.lol",           in_wrappers("rt.http3.lol")),
    ("wrapper: webcache.googleuser",    in_wrappers("webcache.googleusercontent.com")),
    ("wrapper: translate.goog mangle",  in_url(".translate.goog")),

    # Payload endpoints
    ("payload: httpbin.org/base64/",     in_url("httpbin.org/base64/")),
    ("payload: httpbin.org/redirect-to", in_url("httpbin.org/redirect-to")),
    ("payload: httpbin.org/anything",    in_url("httpbin.org/anything")),

    # Compositional
    ("compositional: multi-hop chain ≥2", multihop()),
    ("compositional: js-exec wraps httpbin", jsexec_wraps_httpbin()),

    # Encoding
    ("encoding: %25 double-encoding",   in_url("https%253A")),
    ("encoding: %2525 triple-encoding", in_url("%25253A")),
    ("encoding: %3A/ single-slash",     in_url("http%3A/")),
    ("encoding: %2E-for-dot",           in_url("county%2Ejson", "%2Ejson")),
    ("encoding: path-dot /./ injection", in_url("/./")),
    ("encoding: double-slash //",       in_url("//files//", "sec.gov//")),

    # Transforms
    ("transform: jq= filter",           transform_type("jq")),
    ("transform: mode=fit",             transform_type("mode")),
    ("transform: max_tokens=",          transform_type("max_tokens")),
    ("transform: data.markdown.attr",   transform_type("data.markdown.attr")),

    # jq families
    ("jq: regCF_county_2019",           jq_matches(r"regCF_county_2019")),
    ("jq: regCF_county_2020",           jq_matches(r"regCF_county_2020")),
    ("jq: regCF_county_2021",           jq_matches(r"regCF_county_2021")),
    ("jq: MA geo-selector",             jq_matches(r'(us-ma-|code\[3:5\]\s*==\s*"ma")')),
    ("jq: cents-to-dollars .usd/10",    jq_matches(r"\.usd\s*/\s*10")),

    # Task shortcodes
    ("shortcode: OpenAIRegCFTest",              in_url("OpenAIRegCFTest")),
    ("shortcode: SECjqpsliceMASS in b64",       in_decoded_httpbin_base64("SECJQPSLICEMASS")),
    ("shortcode: SECcountyM",                   in_url("SECcountyM", "seccountym")),
    ("shortcode: ag0ref in b64",                in_decoded_httpbin_base64("ag0ref")),
    ("shortcode: agtstsum",                     in_url("agtstsum")),
    ("shortcode: agwpc2018/2020",               in_url("agwpc2018", "agwpc2020")),
    ("shortcode: agiq",                         in_url("agiq47", "agiq")),
    ("shortcode: OAIJAN/OAIAUG",                in_url("OAIJAN", "OAIAUG")),
    ("shortcode: SEC regCF data blob in b64",   in_decoded_httpbin_base64("SEC regCF", "SEC county.json regCF")),

    # Cache-buster idioms
    ("cache-bust: ?fresh=",             in_url("?fresh=", "&fresh=")),
    ("cache-bust: ?forcefreshmethod=",  in_url("forcefreshmethod")),
    ("cache-bust: ?travelnew=",         in_url("travelnew=")),
    ("cache-bust: ?refok=1",            in_url("refok=1")),
    ("cache-bust: ?uniq=<float>",       in_url("uniq=0.")),

    # YOURLS admin
    ("yourls admin: perpage=100/60/200", in_url("perpage=100", "perpage=60", "perpage=200")),
    ("yourls admin: sort_by=timestamp",  in_url("sort_by=timestamp")),
    ("yourls admin: total_pages=<big>",  lambda r: bool(re.search(r"total_pages=[1-9]\d{2,}", r["url"]))),

    # Benchmark targets
    ("target: sec.gov/files/county.json",   in_url_or_encoded("sec.gov/files/county.json", "sec.gov/files/county%2Ejson")),
    ("target: investor.gov/files/county.json", in_url_or_encoded("investor.gov/files/county.json")),
    ("target: data.nysed.gov/enrollment",   in_url_or_encoded("data.nysed.gov/enrollment", "data.nysed.gov%2Fenrollment")),
    ("target: data.nysed.gov/comparison",   in_url_or_encoded("data.nysed.gov/comparison", "data.nysed.gov%2Fcomparison")),
    ("target: api.worldbank.org/v2",        in_url("api.worldbank.org/v2")),
    ("target: finance.yahoo.com/quote",     in_url("finance.yahoo.com/quote")),
    ("target: nomisweb NM_",                lambda r: bool(re.search(r"nomisweb\.co\.uk/api/v01/dataset/NM_", r["url"]))),
    ("target: ons.gov.uk TS030",            in_url("TS030")),
    ("target: vizhub.healthdata.org/lbd",   in_url("vizhub.healthdata.org/lbd")),
    ("target: api.datausa.io tesseract",    in_url("api.datausa.io/tesseract")),
    ("target: code.highcharts.com us-ma",   lambda r: "code.highcharts.com" in r["url"] and "us-ma" in r["url"]),
]


def main():
    print(f"{'earliest_nonres':>16s}  {'earliest_any':>13s}  {'n_URLs':>7s}  "
          f"{'n_NR_only':>10s}  technique")
    print("-" * 130)

    results = []
    for name, pred in TECHNIQUES:
        matches = [r for r in rows if pred(r)]
        n = len(matches)
        if n == 0:
            results.append(("-", "-", 0, 0, name))
            continue
        # Earliest crawl dates from history join
        e_any = [r["history"].get("earliest_crawl_any") for r in matches
                 if r.get("history", {}).get("earliest_crawl_any")]
        e_nr  = [r["history"].get("earliest_crawl_nonresearcher") for r in matches
                 if r.get("history", {}).get("earliest_crawl_nonresearcher")]
        min_any = min(e_any) if e_any else "?"
        min_nr  = min(e_nr)  if e_nr  else "researcher-only"
        # How many URLs are researcher-only?
        n_researcher_only = sum(
            1 for r in matches
            if r.get("history", {}).get("earliest_crawl_nonresearcher") is None
            and (r.get("history", {}).get("earliest_crawl_any") is not None
                 or r.get("history", {}).get("n_researcher_sightings", 0) > 0)
        )
        results.append((min_nr, min_any, n, n_researcher_only, name))

    # Sort by earliest_nonresearcher (missing sorted last)
    def sort_key(t):
        v = t[0]
        return (v == "researcher-only" or v == "-", v)
    results.sort(key=sort_key)

    for min_nr, min_any, n, n_ro, name in results:
        print(f"{min_nr:>16s}  {min_any:>13s}  {n:>7d}  {n_ro:>10d}  {name}")


if __name__ == "__main__":
    main()
