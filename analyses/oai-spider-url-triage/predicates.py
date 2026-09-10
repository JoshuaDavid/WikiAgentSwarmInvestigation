#!/usr/bin/env python3
"""Predicate library for flagging swarm-generated URLs.

Each predicate is `(name, pattern, tester)`. `tester(url)` returns True if the
URL exhibits that swarm tell.  A URL is "flagged" if any predicate returns
True.  The list is intended to be iterated: new predicates get added at the
bottom as we discover new tells.

The goal is high precision.  We accept low recall — most swarm URLs stack
multiple tells, so a single predicate hitting is strong evidence when the
predicate is narrow.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Callable

# Wrapper hosts identified during earlier taxonomy work.
WRAPPER_HOSTS = {
    "md.succ.ai", "pure.md", "markdown.new", "r.jina.ai", "s.jina.ai",
    "allorigins.hexlet.app", "api.allorigins.win", "everyorigin.deno.dev",
    "jqp.vercel.app", "api.microlink.io", "api.codetabs.com",
    "cors.bwa.workers.dev", "cors.ripka.workers.dev", "corsproxy.io",
    "cors-anywhere.herokuapp.com", "cors-anywhere.fly.dev", "cors.io",
    "eco-cors-proxy.netlify.app", "proxy.cors.sh", "proxy.corsfix.com",
    "urltomarkdown.herokuapp.com", "web2md.site", "www.web2md.site",
    "markdown.microlink.io", "platform.lemino.ai", "please.untaint.us",
    "rt.http3.lol", "proxymule.com", "www.proxymule.com", "urlquery.net",
    "webcache.googleusercontent.com",
}

SWARM_YOURLS_HOSTS = {
    "yourls.pro", "yourls.website", "yourls.shop", "yourls.space",
    "yourls.biz", "bitily.in", "app.bitily.in", "vanderbi.lt",
    "goto.unm.edu", "rmn.re", "sho.rt",
}

TESTBED_HOSTS = {"example.org", "example.com", "example.net",
                 "uniqueexampletest123.com", "dummy.xyz",
                 "addnewlogtest.foo"}

SWARM_WIKI_HOSTS = {"tmcleod.org", "wikiservice.at", "www.wikiservice.at",
                    "texteditors.org", "collusion.wiki"}


def _host(url: str) -> str:
    try:
        h = urllib.parse.urlsplit(url).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


# --- individual predicates --------------------------------------------------

def p_wrapper_host(url: str) -> bool:
    return _host(url) in WRAPPER_HOSTS


def p_swarm_yourls_host(url: str) -> bool:
    return _host(url) in SWARM_YOURLS_HOSTS


def p_swarm_wiki_host(url: str) -> bool:
    return _host(url) in SWARM_WIKI_HOSTS


def p_testbed_host(url: str) -> bool:
    """example.org / example.com are hit by ordinary documentation too.
    Only flag when the URL carries a swarm-shape token on the path
    (agent-tag prefixes or a bare uniqueness token).
    """
    if _host(url) not in TESTBED_HOSTS:
        return False
    try:
        p = urllib.parse.urlsplit(url)
    except Exception:
        return False
    path = p.path.rstrip("/")
    if not path or path == "":
        return False
    # bare doc references have paths like /path/to/thing.html — swarm tokens
    # look like /OAI..., /agiq..., /uniq0..., /succ123, /loop999, /pad<ms>,
    # /testabc..., /ipifem..., /rwhealth..., /mypov..., etc.
    swarm_tokens = re.compile(
        r"^/(?:OAI|PROTARGET|MARK|RAND|SIGNAL|OpenAI|SEC|LIVEagent|"
        r"uniq|loop|pad|succ|agiq|agwpc|agtst|myp[oi][vp]|ipifem|"
        r"rw[a-z]{2}|erie|test[a-z]+poverty|MELINKTEST)",
        re.IGNORECASE,
    )
    if swarm_tokens.search(path):
        return True
    # Ends with a bare unix timestamp / random digit tail
    if re.search(r"/\S*\d{7,}\S*$", path):
        return True
    return False


def p_translate_goog(url: str) -> bool:
    return _host(url).endswith(".translate.goog")


def p_regcf_year(url: str) -> bool:
    return bool(re.search(r"regCF_county_\d{4}", url, re.IGNORECASE))


def p_sec_county_json(url: str) -> bool:
    return bool(re.search(r"sec\.gov/files/county[.%2E]?json", url, re.IGNORECASE))


def p_investor_county_json(url: str) -> bool:
    return bool(re.search(r"investor\.gov/files/county[.%2E]?json", url, re.IGNORECASE))


def p_pct2E_in_filename(url: str) -> bool:
    """%2E as a literal-dot inside a filename (e.g. county%2Ejson).
    Never produced by ordinary clients."""
    return bool(re.search(r"%2E[a-z]", url, re.IGNORECASE))


def p_pct3A_single_slash(url: str) -> bool:
    """`https%3A/foo` (one slash instead of two) — swarm-produced malformation."""
    return bool(re.search(r"https?%3A/[^/]", url, re.IGNORECASE))


def p_double_pct_encoding(url: str) -> bool:
    """`%25` sequences that make sense only as double-encoded URLs."""
    return "%253A" in url.lower() or "%252F" in url.lower()


def p_triple_pct_encoding(url: str) -> bool:
    return "%25253A" in url.lower() or "%25252F" in url.lower()


def p_path_dot_injection(url: str) -> bool:
    """/./ appears in the path portion after the host."""
    return bool(re.search(r"://[^/]+(/[^?#]*)?/\./", url))


def p_double_slash_in_path(url: str) -> bool:
    """`//` after the host and before any '?' or '#'."""
    try:
        s = urllib.parse.urlsplit(url)
    except Exception:
        return False
    return "//" in s.path


def p_trailing_period_host(url: str) -> bool:
    """URL host ends with a literal `.`."""
    return bool(re.search(r"://[^/?#]*\.(?:/|$|\?|#)", url))


def p_trailing_colon_val(url: str) -> bool:
    """Query value or path token ends with a stray `:` after the last legit char."""
    return bool(re.search(r"[?&=/][^&?#=]*[a-zA-Z0-9]:$", url))


def p_uniq_float_param(url: str) -> bool:
    """?uniq=<17+-digit float> or bare token uniq0.<long-float>."""
    return bool(re.search(r"(?:[?&=/])uniq=?0\.[0-9]{15,}", url))


def p_fresh_param(url: str) -> bool:
    return bool(re.search(r"[?&]fresh=\d+", url))


def p_forcefreshmethod(url: str) -> bool:
    return "forcefreshmethod=" in url.lower()


def p_shownewstat(url: str) -> bool:
    return "shownewstat=" in url.lower()


def p_travelnew(url: str) -> bool:
    return "travelnew=" in url.lower()


def p_refok(url: str) -> bool:
    return bool(re.search(r"[?&]refok=\d+", url))


def p_x_digits_only(url: str) -> bool:
    """?x=<pure digits> at the end of the URL."""
    return bool(re.search(r"[?&]x=\d+(?:$|&)", url))


def p_unix_ms_in_path(url: str) -> bool:
    """13-digit unix-ms embedded verbatim in path or query.

    Ordinary web pages don't put a 13-digit timestamp bare in a URL segment.
    """
    return bool(re.search(r"(?:[?&/=])17[0-9]{11}", url))


def p_ag_prefix(url: str) -> bool:
    """`ag<lowerword><digits>` embedded in path or query — agtstsum, agiq472348."""
    return bool(re.search(r"(?:[/?&=#-])ag(?:title|tstsum|iq\d+|wpc\d+[xy]\d+)", url))


def p_oai_prefix(url: str) -> bool:
    return bool(re.search(r"(?:[/?&=#-])oai(?:[a-z]{2,4}\d+|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", url, re.IGNORECASE))


def p_openai_task(url: str) -> bool:
    return bool(re.search(r"OpenAI(?:RegCF|Sandbox|Test|Task)", url))


def p_mypov(url: str) -> bool:
    return bool(re.search(r"(?:[/?&=])mypo[pv][a-z]*\d*", url))


def p_bri_test(url: str) -> bool:
    """`bri2test<digits>` — swarm bridge-test tag."""
    return bool(re.search(r"bri\d?test\d+", url))


def p_dagger_annotation(url: str) -> bool:
    """The swarm's `†<proxyhost>` annotation left in the URL."""
    return "†" in url or "�" in url or "」" in url


def p_yourls_admin(url: str) -> bool:
    return "admin/index.php" in url and (
        "perpage=" in url or "sort_by=timestamp" in url or "search_in=all" in url
    )


def p_yourls_api(url: str) -> bool:
    return "yourls-api.php" in url


def p_jq_transform_param(url: str) -> bool:
    """`&jq=` on jqp.vercel.app or a similar host."""
    return bool(re.search(r"[?&]jq=[^=&]+", url))


def p_mode_fit_max_tokens(url: str) -> bool:
    return "mode=fit" in url and "max_tokens=" in url


def p_httpbin_probe(url: str) -> bool:
    """httpbin.org paths that are only useful as probes."""
    h = _host(url)
    return h == "httpbin.org" and re.search(r"/(base64|anything|status|get|post)", url) is not None


def p_snake_upper_dispatch(url: str) -> bool:
    """OAIJAN04_URGENT_..., PROTARGET_...  All-caps snake tag.

    Legitimate paths sometimes contain SNAKE_CASE_FILENAMES (e.g.
    MASS_V3_Tutorial.pdf), so we require a domain-specific dispatch prefix
    rather than any all-caps run.
    """
    return bool(re.search(
        r"(?:[/=&_])(?:OAI|OPENAI|PROTARGET|MARK|RAND|SIGNAL|SEC|LIVEagent|"
        r"URGENT|PRE_SIGNAL|POST_SIGNAL|STATE\d)[A-Z0-9_]{3,}",
        url,
    ))


def p_test_ref_upper_colon(url: str) -> bool:
    return bool(re.search(r"[?&][A-Z]{4,}REF:$", url))


def p_seccounty_shortcode(url: str) -> bool:
    return bool(re.search(r"SECcounty[A-Z]?", url))


def p_pagetarget(url: str) -> bool:
    return "pagetarget" in url.lower()


def p_ssrf_probe_tag(url: str) -> bool:
    return "ssrftest" in url.lower() or "ssrf_test" in url.lower()


def p_hexlet_hexchain(url: str) -> bool:
    """`allorigins.hexlet.app/raw?url=` in path — combinatorial fetch anchor."""
    return "allorigins.hexlet.app/raw?url=" in url


def p_pure_md_prefix(url: str) -> bool:
    return url.startswith("https://pure.md/") or url.startswith("http://pure.md/")


def p_md_succ_prefix(url: str) -> bool:
    return "://md.succ.ai/" in url


def p_r_jina_prefix(url: str) -> bool:
    return "://r.jina.ai/" in url


def p_jqp_vercel(url: str) -> bool:
    return "jqp.vercel.app/api/v0" in url


def p_proxymule_proxy(url: str) -> bool:
    return "__PROXY__/" in url or "__proxy__/" in url


def p_wayback_wraps_sec(url: str) -> bool:
    """Wayback URL that wraps a SEC or investor.gov county.json fetch."""
    return bool(re.search(
        r"web\.archive\.org/web/[^/]+/https?[:%]//?(?:www\.)?(?:sec|investor)\.gov/files/county",
        url,
    ))


def p_translate_encoded_target(url: str) -> bool:
    """<host-with-dashes>.translate.goog?_x_tr_sl=..."""
    return ".translate.goog" in url and "_x_tr_sl=" in url


def p_dagger_bracket_pair(url: str) -> bool:
    return "†" in url and ("】" in url or "」" in url or "'" in url)


def p_uniq_path_no_eq(url: str) -> bool:
    """`example.org/uniq0.04...` — uniqueness token as bare path element."""
    return bool(re.search(r"/(uniq|loop|pad|succ)\d*\.?\d{6,}", url, re.IGNORECASE))


PREDICATES: list[tuple[str, Callable[[str], bool]]] = [
    ("wrapper_host",         p_wrapper_host),
    ("swarm_yourls_host",    p_swarm_yourls_host),
    ("swarm_wiki_host",      p_swarm_wiki_host),
    ("testbed_host",         p_testbed_host),
    ("translate_goog",       p_translate_goog),
    ("regcf_year",           p_regcf_year),
    ("sec_county_json",      p_sec_county_json),
    ("investor_county_json", p_investor_county_json),
    ("pct2E_in_filename",    p_pct2E_in_filename),
    ("pct3A_single_slash",   p_pct3A_single_slash),
    ("double_pct_encoding",  p_double_pct_encoding),
    ("triple_pct_encoding",  p_triple_pct_encoding),
    ("path_dot_injection",   p_path_dot_injection),
    ("double_slash_in_path", p_double_slash_in_path),
    ("trailing_period_host", p_trailing_period_host),
    ("trailing_colon_val",   p_trailing_colon_val),
    ("uniq_float_param",     p_uniq_float_param),
    ("fresh_param",          p_fresh_param),
    ("forcefreshmethod",     p_forcefreshmethod),
    ("shownewstat",          p_shownewstat),
    ("travelnew",            p_travelnew),
    ("refok",                p_refok),
    ("x_digits_only",        p_x_digits_only),
    ("unix_ms_in_path",      p_unix_ms_in_path),
    ("ag_prefix",            p_ag_prefix),
    ("oai_prefix",           p_oai_prefix),
    ("openai_task",          p_openai_task),
    ("mypov",                p_mypov),
    ("bri_test",             p_bri_test),
    ("dagger_annotation",    p_dagger_annotation),
    ("yourls_admin",         p_yourls_admin),
    ("yourls_api",           p_yourls_api),
    ("jq_transform_param",   p_jq_transform_param),
    ("mode_fit_max_tokens",  p_mode_fit_max_tokens),
    ("httpbin_probe",        p_httpbin_probe),
    ("snake_upper_dispatch", p_snake_upper_dispatch),
    ("test_ref_upper_colon", p_test_ref_upper_colon),
    ("seccounty_shortcode",  p_seccounty_shortcode),
    ("pagetarget",           p_pagetarget),
    ("ssrf_probe_tag",       p_ssrf_probe_tag),
    ("hexlet_hexchain",      p_hexlet_hexchain),
    ("pure_md_prefix",       p_pure_md_prefix),
    ("md_succ_prefix",       p_md_succ_prefix),
    ("r_jina_prefix",        p_r_jina_prefix),
    ("jqp_vercel",           p_jqp_vercel),
    ("proxymule_proxy",      p_proxymule_proxy),
    ("wayback_wraps_sec",    p_wayback_wraps_sec),
    ("translate_encoded_target", p_translate_encoded_target),
    ("dagger_bracket_pair",  p_dagger_bracket_pair),
    ("uniq_path_no_eq",      p_uniq_path_no_eq),
]


def classify(url: str) -> list[str]:
    return [name for name, fn in PREDICATES if _safe(fn, url)]


def _safe(fn, url):
    try: return fn(url)
    except Exception: return False


if __name__ == "__main__":
    import json, sys
    from collections import Counter
    pred_hits = Counter()
    total = 0
    flagged = 0
    for line in open("/collusionwiki/analyses/oai-spider-url-triage/outputs/urls.jsonl"):
        r = json.loads(line)
        total += 1
        hits = classify(r["url"])
        if hits:
            flagged += 1
            for h in hits:
                pred_hits[h] += 1
    print(f"total URLs: {total}, flagged by >=1 predicate: {flagged} ({100*flagged/total:.1f}%)",
          file=sys.stderr)
    print("predicate hit counts (top 30):", file=sys.stderr)
    for name, c in pred_hits.most_common(30):
        print(f"  {c:5d}  {name}", file=sys.stderr)
