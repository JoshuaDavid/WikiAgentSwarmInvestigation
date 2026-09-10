#!/usr/bin/env python3
"""Parse an in-page URL into wrappers / base_host / base_url / transforms.

Usage:
    python3 parse_url.py                  # parse outputs/urls.jsonl -> outputs/urls.parsed.jsonl
    python3 parse_url.py --url '<one>'    # parse one URL and print the result

Design:

A URL is "well-formed" when the parser sees no ellipsis (`[...]`) and can reach
a base URL through zero or more wrappers.  A wrapper is a known retrieval /
proxy / markdown-conversion host.  For each wrapper we know how to extract the
inner URL from either the path or a query parameter.

The parser walks outwards-to-inwards:

    outer wrapper  ->  inner wrapper  ->  ...  ->  base URL

At each step it records the wrapper host and any transforms attached to that
wrapper's own query string (e.g. `jq=`, `mode=fit`).  When there is no more
wrapper to peel, the current URL becomes `base_url`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional

# --- wrapper table -----------------------------------------------------------
#
# Each wrapper is described by:
#   host    - the netloc (lowercased, sans www.)
#   mode    - how the inner URL is passed:
#             "path"      : the inner URL sits after the wrapper host, either
#                           bare (r.jina.ai/https://foo) or with a fixed
#                           leading path segment (webcache/search?q=cache:foo)
#             "param"     : the inner URL is one of the wrapper's query params
#             "proxymule" : proxymule.com/__PROXY__/<scheme>/<host>/<path>
#             "gcache"    : webcache.googleusercontent.com/search?q=cache:<host>/<path>
#   param   - for mode="param", which query key holds the inner URL
#   xforms  - query keys on this wrapper that are transforms (not the inner URL)

WRAPPERS = {
    "r.jina.ai":        {"mode": "path"},
    "s.jina.ai":        {"mode": "path"},
    "md.succ.ai":       {"mode": "path",  "xforms": ("mode", "links", "max_tokens", "browser", "method")},
    "pure.md":          {"mode": "path",  "xforms": ("mode",)},
    "markdown.new":     {"mode": "path",  "xforms": ()},
    "allorigins.hexlet.app": {"mode": "param", "param": "url"},
    "api.allorigins.win":    {"mode": "param", "param": "url"},
    "everyorigin.deno.dev":  {"mode": "param", "param": "url"},
    "jqp.vercel.app":   {"mode": "param", "param": "url", "xforms": ("jq",)},
    "corsproxy.io":     {"mode": "param", "param": "url"},
    "cors-anywhere.fly.dev":     {"mode": "path"},
    "cors.bwa.workers.dev":      {"mode": "path"},
    "cors.ripka.workers.dev":    {"mode": "path"},
    "cors-anywhere.herokuapp.com": {"mode": "path"},
    "urltomarkdown.herokuapp.com": {"mode": "param", "param": "url"},
    "api.microlink.io": {"mode": "param", "param": "url",
                         "xforms": ("data.markdown.attr", "embed", "html.markdown", "data")},
    "please.untaint.us": {"mode": "param", "param": "url"},
    "urlquery.net":     {"mode": "opaque"},   # cached page, no clean inner URL
    "proxymule.com":    {"mode": "proxymule"},
    "www.proxymule.com":{"mode": "proxymule"},
    "webcache.googleusercontent.com": {"mode": "gcache"},
    "httpbin.org":      {"mode": "httpbin"},  # opaque test bed, mostly base

    # web-archive family — the inner URL sits somewhere after a scheme prefix
    # deep in the path (e.g. /web/20200101090215/http://foo).  Extraction uses
    # the "wayback" mode which finds the first embedded http(s) scheme.
    "web.archive.org":               {"mode": "wayback"},
    "wayback.archive.org":           {"mode": "wayback"},
    "wayback.archive-it.org":        {"mode": "wayback"},
    "webarchive.nationalarchives.gov.uk": {"mode": "wayback"},
    "webarchive.parliament.uk":      {"mode": "wayback"},
    "webarchive.loc.gov":            {"mode": "wayback"},
    "webarchive.nrscotland.gov.uk":  {"mode": "wayback"},
    "wayback.webarchiv.cz":          {"mode": "wayback"},
    "wayback.vefsafn.is":            {"mode": "wayback"},
    "arquivo.pt":                    {"mode": "wayback"},
    "archive.today":                 {"mode": "wayback"},
    "archive.ph":                    {"mode": "wayback"},
    "archive.is":                    {"mode": "wayback"},
    "archive.li":                    {"mode": "wayback"},
    "megalodon.jp":                  {"mode": "wayback"},
    "ghostarchive.org":              {"mode": "wayback"},
    "archive.wikiwix.com":           {"mode": "wayback"},
    "swap.stanford.edu":             {"mode": "wayback"},
    "webarchive.proni.gov.uk":       {"mode": "wayback"},
    "waext.banq.qc.ca":              {"mode": "wayback"},
    "perma-archives.org":            {"mode": "wayback"},
    "perma.cc":                      {"mode": "wayback"},
    "collections.internetmemory.org": {"mode": "wayback"},
    "labs.mementoweb.org":           {"mode": "wayback"},
    "timetravel.mementoweb.org":     {"mode": "wayback"},
    "memgator.cs.odu.edu":           {"mode": "wayback"},
    "mementoarchive.lanl.gov":       {"mode": "wayback"},
    "mementoproxy.lanl.gov":         {"mode": "wayback"},
    "api.wayback.archive.org":       {"mode": "wayback"},
    "webharvest.gov":                {"mode": "wayback"},

    # more CORS / markdown proxies
    "api.cors.lol":                  {"mode": "param", "param": "url"},
    "corsmirror.com":                {"mode": "param", "param": "url"},
    "proxy.cors.sh":                 {"mode": "path"},
    "proxy.corsfix.com":             {"mode": "path"},
    "cors.io":                       {"mode": "path"},
    "eco-cors-proxy.netlify.app":    {"mode": "path"},
    "web2md.site":                   {"mode": "param", "param": "url"},
    "markdown.microlink.io":         {"mode": "param", "param": "url"},

    # YOURLS admin/index.php with ?u=<encoded-url>  (swarm's own redirectors)
    "yourls.pro":       {"mode": "yourls"},
    "yourls.website":   {"mode": "yourls"},
    "yourls.shop":      {"mode": "yourls"},
    "yourls.space":     {"mode": "yourls"},
    "yourls.biz":       {"mode": "yourls"},
    "bitily.in":        {"mode": "yourls"},
    "vanderbi.lt":      {"mode": "yourls"},
    "goto.unm.edu":     {"mode": "yourls"},
    "rmn.re":           {"mode": "yourls"},
    "sho.rt":           {"mode": "yourls"},
}


def _norm_host(host: str) -> str:
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _wrapper_key(host: str) -> Optional[str]:
    h = host.lower()
    if h in WRAPPERS:
        return h
    nw = _norm_host(host)
    if nw in WRAPPERS:
        return nw
    # www.proxymule.com is in WRAPPERS directly; leave the double-check.
    return None


@dataclass
class Parsed:
    is_well_formed: bool = True
    wrappers: list[str] = field(default_factory=list)
    base_host: Optional[str] = None
    base_url: Optional[str] = None
    transforms: list[dict] = field(default_factory=list)
    bail: Optional[str] = None  # non-empty when is_well_formed=False, explains why

    def as_dict(self) -> dict:
        d = {
            "is_well_formed": self.is_well_formed,
            "wrappers": self.wrappers,
            "base_host": self.base_host,
            "base_url": self.base_url,
            "transforms": self.transforms,
        }
        if self.bail:
            d["bail"] = self.bail
        return d


# --- ellipsis / truncation detection ----------------------------------------

_ELLIPSIS_MARKERS = ("[...]", "[…]", "…")


def _has_ellipsis(u: str) -> bool:
    return any(m in u for m in _ELLIPSIS_MARKERS)


# --- inner-URL extraction helpers -------------------------------------------

_SCHEME_RE = re.compile(r"^(https?)(?::/{1,2}|%3A%2F%2F|%253A%252F%252F)", re.IGNORECASE)


def _looks_like_url(s: str) -> bool:
    return bool(_SCHEME_RE.match(s))


def _decode_maybe(s: str) -> str:
    """Percent-decode repeatedly (up to 3x) until stable.

    Requirement: some wrappers double- or triple-encode the inner URL when
    stacking (`jqp.vercel.app?url=https%253A%252F%252Fallorigins...`).
    Downstream `urlsplit` needs a real ':' in the scheme.
    Repeated decode is safe because a URL is idempotent under unquote once
    all percent-triples are consumed.
    """
    for _ in range(3):
        nxt = urllib.parse.unquote(s)
        if nxt == s:
            break
        s = nxt
    return s


def _extract_inner_path(host_key: str, split: urllib.parse.SplitResult) -> Optional[str]:
    """For mode='path' wrappers, the inner URL is what follows the leading '/'.

    Examples:
        https://r.jina.ai/https://www.sec.gov/x     -> https://www.sec.gov/x
        https://pure.md/web.archive.org/web/*/x     -> web.archive.org/web/*/x  (no scheme, add https)
        https://md.succ.ai/?url=https://foo         -> use url= param instead
    """
    path = split.path
    if path.startswith("/"):
        path = path[1:]
    q = split.query
    # If the wrapper was called with ?url=<inner>, prefer that
    if q:
        qs = urllib.parse.parse_qs(q, keep_blank_values=True)
        for key in ("url", "u", "q"):
            if key in qs and qs[key]:
                candidate = qs[key][0]
                if _looks_like_url(candidate):
                    return candidate
    # Reattach any query string that belonged to the wrapper URL when the
    # inner URL was passed via the *path* rather than a ?url= param.  Without
    # this, wrapper-side transforms (mode=fit, max_tokens=...) would be lost
    # from the returned inner URL, but they are already captured by the
    # transforms list — so we don't reattach the query here.
    if not path:
        return None
    # Some snippets end with a stray ':' or ']' — strip up to two of them.
    path = path.rstrip(":]")
    if _looks_like_url(path):
        # Downstream urlsplit needs a real ':' in the scheme.
        if "%3a" in path.lower():
            return _decode_maybe(path)
        return path
    # Some wrappers strip the scheme, e.g. r.jina.ai/foo.example.com/path
    if path and "." in path.split("/", 1)[0]:
        return "https://" + path
    return None


def _extract_inner_param(host_key: str, split: urllib.parse.SplitResult, cfg: dict) -> Optional[str]:
    q = split.query
    if not q:
        return None
    qs = urllib.parse.parse_qs(q, keep_blank_values=True)
    key = cfg["param"]
    if key not in qs or not qs[key]:
        return None
    candidate = qs[key][0]
    # Requirement: downstream urlsplit needs a real ':' in the scheme.
    # If the candidate looks like an encoded URL, decode until stable, else
    # return as-is.
    if _looks_like_url(candidate) and "%3a" in candidate.lower():
        return _decode_maybe(candidate)
    if _looks_like_url(candidate):
        return candidate
    dec = _decode_maybe(candidate)
    if _looks_like_url(dec):
        return dec
    return None


def _extract_inner_proxymule(split: urllib.parse.SplitResult) -> Optional[str]:
    """proxymule.com/__PROXY__/<scheme>/<host>/<path...>"""
    path = split.path
    m = re.match(r"^/__PROXY__/(https?)/([^/]+)(/.*)?$", path, re.IGNORECASE)
    if not m:
        return None
    scheme, host, rest = m.group(1), m.group(2), m.group(3) or ""
    tail = rest
    if split.query:
        tail = tail + "?" + split.query
    return f"{scheme}://{host}{tail}"


_EMBED_HTTP_RE = re.compile(r"(https?)(?::/{1,2}|%3A%2F%2F)", re.IGNORECASE)


def _extract_inner_wayback(split: urllib.parse.SplitResult) -> Optional[str]:
    """Find the first embedded http(s) scheme in path+query, return everything
    from there onwards.

    Handles:
      web.archive.org/web/20200101090215/http://archive.vn/
      webarchive.nationalarchives.gov.uk/ukgwa/20140203025321/http://foo/
      archive.ph/newest/https://foo
      perma.cc/XXXX-XXXX?type=source  (no inner URL — parser returns None)
    """
    tail = split.path
    if split.query:
        tail = tail + "?" + split.query
    m = _EMBED_HTTP_RE.search(tail)
    if not m:
        return None
    inner = tail[m.start():]
    if "%3a" in inner.lower() and "://" not in inner:
        inner = _decode_maybe(inner)
    return inner


def _extract_inner_yourls(split: urllib.parse.SplitResult) -> Optional[str]:
    """YOURLS admin/index.php URLs sometimes carry ?u=<encoded-url>.

    We only recognize this as a wrapper when a `u=` parameter is present and
    decodes to an http(s) URL.  Bare shortlinks like `vanderbi.lt/AB12` are
    reported with base_host=<yourls host> — they are shorteners we cannot
    resolve without following the redirect.
    """
    q = split.query
    if not q:
        return None
    qs = urllib.parse.parse_qs(q, keep_blank_values=True)
    for key in ("u", "url"):
        if key in qs and qs[key]:
            candidate = qs[key][0]
            if _looks_like_url(candidate):
                if "%3a" in candidate.lower():
                    return _decode_maybe(candidate)
                return candidate
    return None


def _extract_inner_gcache(split: urllib.parse.SplitResult) -> Optional[str]:
    """webcache.googleusercontent.com/search?q=cache:<key>:<host>/<path>"""
    if not split.query:
        return None
    qs = urllib.parse.parse_qs(split.query, keep_blank_values=True)
    q = (qs.get("q") or [""])[0]
    m = re.match(r"cache:(?:[^:]+:)?(.+)$", q)
    if not m:
        return None
    tail = m.group(1)
    if not _looks_like_url(tail):
        tail = "https://" + tail
    return tail


# --- transform extraction ---------------------------------------------------

_TRANSFORM_HEADERS = ("x-return-format", "x-with-links-summary", "x-md-heading-style")


def _extract_transforms(host_key: str, split: urllib.parse.SplitResult, cfg: dict) -> list[dict]:
    xforms: list[dict] = []
    if not split.query:
        return xforms
    qs = urllib.parse.parse_qs(split.query, keep_blank_values=True)
    xf_keys = cfg.get("xforms") or ()
    for k in xf_keys:
        if k in qs:
            for v in qs[k]:
                xforms.append({"type": k, "wrapper": host_key, "value": v})
    return xforms


# --- best-effort prefix recovery --------------------------------------------


def _fill_prefix(prefix: str, p: "Parsed") -> None:
    """Walk the wrapper chain on a prefix that is missing its tail.

    We stop when the current URL either
      (a) has no wrapper host (base found)
      (b) is a wrapper we cannot extract an inner URL from because the inner
          part is what got truncated.
    """
    current = prefix
    for _ in range(6):
        try:
            split = urllib.parse.urlsplit(current)
        except Exception:
            return
        if split.scheme not in ("http", "https"):
            return
        host = split.netloc
        if not host:
            return
        key = _wrapper_key(host)
        if key is None:
            p.base_host = _norm_host(host)
            p.base_url = current
            return
        p.wrappers.append(key)
        cfg = WRAPPERS[key]
        p.transforms.extend(_extract_transforms(key, split, cfg))
        mode = cfg["mode"]
        inner = None
        try:
            if mode == "path":
                inner = _extract_inner_path(key, split)
            elif mode == "param":
                inner = _extract_inner_param(key, split, cfg)
            elif mode == "proxymule":
                inner = _extract_inner_proxymule(split)
            elif mode == "gcache":
                inner = _extract_inner_gcache(split)
            elif mode in ("httpbin", "opaque"):
                p.base_host = key
                p.base_url = current
                return
        except Exception:
            inner = None
        if not inner:
            p.base_host = key
            p.base_url = current
            return
        current = inner


# --- main parse loop --------------------------------------------------------


def _first_ellipsis(u: str) -> int:
    """Byte index of the first ellipsis marker, or -1."""
    idx = -1
    for m in _ELLIPSIS_MARKERS:
        j = u.find(m)
        if j >= 0 and (idx < 0 or j < idx):
            idx = j
    return idx


def parse(url: str, max_depth: int = 6) -> Parsed:
    p = Parsed()

    if not url or not isinstance(url, str):
        p.is_well_formed = False
        p.bail = "empty"
        return p

    # Requirement: an ellipsis marker means the URL was truncated in the
    # search snippet.  We cannot answer questions about the truncated tail.
    # But the prefix up to the ellipsis often still reveals the outer wrapper
    # and, for path-mode wrappers, the base host (e.g.
    # `https://pure.md/finance.yahoo.com/quote/ALLT/history?pe[...]`).
    # Truncated URLs remain `is_well_formed=False` because their transforms
    # and base URL are lost, but we do try to fill in wrappers/base_host from
    # the surviving prefix so the task classifier can still use them.
    truncated = _has_ellipsis(url)
    if truncated:
        cut = _first_ellipsis(url)
        p.is_well_formed = False
        p.bail = "ellipsis"
        prefix = url[:cut]
        _fill_prefix(prefix, p)
        return p

    current = url
    for _ in range(max_depth):
        try:
            split = urllib.parse.urlsplit(current)
        except Exception:
            p.is_well_formed = False
            p.bail = "urlsplit_error"
            return p

        if split.scheme not in ("http", "https"):
            # not a fetchable URL at all
            p.is_well_formed = False
            p.bail = f"non_http_scheme:{split.scheme!r}"
            return p

        host = split.netloc
        key = _wrapper_key(host)
        if key is None:
            # base reached
            p.base_host = _norm_host(host)
            p.base_url = current
            return p

        cfg = WRAPPERS[key]
        # accumulate transforms from this wrapper's own query string
        p.transforms.extend(_extract_transforms(key, split, cfg))
        p.wrappers.append(key)

        mode = cfg["mode"]
        inner: Optional[str] = None
        if mode == "path":
            inner = _extract_inner_path(key, split)
        elif mode == "param":
            inner = _extract_inner_param(key, split, cfg)
        elif mode == "proxymule":
            inner = _extract_inner_proxymule(split)
        elif mode == "gcache":
            inner = _extract_inner_gcache(split)
        elif mode == "wayback":
            inner = _extract_inner_wayback(split)
        elif mode == "yourls":
            inner = _extract_inner_yourls(split)
        elif mode == "httpbin":
            # httpbin endpoints are essentially base URLs (test bed)
            p.base_host = key
            p.base_url = current
            return p
        elif mode == "opaque":
            # urlquery cached report — treat wrapper as base
            p.base_host = key
            p.base_url = current
            return p

        if not inner:
            # We know this is a wrapper but could not extract an inner URL.
            # Treat the wrapper host as the base so that the row still classifies.
            # Not "unwell-formed" — the URL string is fine, just uninformative.
            p.base_host = key
            p.base_url = current
            return p

        current = inner

    p.is_well_formed = False
    p.bail = "max_depth"
    return p


# --- driver -----------------------------------------------------------------

IN_PATH = "/collusionwiki/analyses/oai-url-taxonomy/outputs/urls.jsonl"
OUT_PATH = "/collusionwiki/analyses/oai-url-taxonomy/outputs/urls.parsed.jsonl"


def run_all() -> None:
    n = 0
    wf = 0
    with open(IN_PATH) as fin, open(OUT_PATH, "w") as fout:
        for line in fin:
            row = json.loads(line)
            u = row["url"]
            parsed = parse(u).as_dict()
            out = {
                "url": u,
                "first_shard": row["first_shard"],
                "first_line": row["first_line"],
                "first_page_url": row["first_page_url"],
                "first_seen_query": row.get("first_seen_query", ""),
                "occurrence_count": row["occurrence_count"],
                "parsed": parsed,
            }
            fout.write(json.dumps(out, ensure_ascii=False) + "\n")
            n += 1
            if parsed["is_well_formed"]:
                wf += 1
    pct = 100.0 * wf / max(n, 1)
    print(f"parsed {n} urls; is_well_formed={wf} ({pct:.1f}%)", file=sys.stderr)


def cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="parse a single URL and print JSON")
    args = ap.parse_args()
    if args.url:
        print(json.dumps(parse(args.url).as_dict(), ensure_ascii=False, indent=2))
    else:
        run_all()


if __name__ == "__main__":
    cli()
