#!/usr/bin/env python3
"""Redact credential-shaped strings before anything is written to outputs/.

Scanned pages carry third-party credentials in their request URLs: Mapbox
and Mapillary tokens behind Tableau map layers, API keys in query strings,
bearer tokens inside smuggled scripts. None of them belong in a public
repository, and GitHub push protection rejects a push that contains them.
Every writer in this analysis passes its rows through `redact_obj` first.

The replacement keeps the recognisable prefix and drops the secret part, so
`access_token=pk.eyJ1Ij…` becomes `access_token=pk.<redacted:mapbox>`.
"""

from __future__ import annotations

import re

PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("mapbox", re.compile(r"\b([sp]k\.)eyJ[A-Za-z0-9_\-]{10,}(?:\.[A-Za-z0-9_\-]+)*"), r"\1<redacted:mapbox>"),
    ("mapillary", re.compile(r"(MLY(?:%7C|\|)\d+(?:%7C|\|))[0-9a-f]{10,}", re.I), r"\1<redacted:mapillary>"),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}(?:\.[A-Za-z0-9_\-]+)?"), "<redacted:jwt>"),
    ("bearer", re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]{16,}"), r"\1<redacted:bearer>"),
    ("aws", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"), r"\1<redacted:aws>"),
    ("github", re.compile(r"\b(gh[pousr]_)[A-Za-z0-9]{30,}"), r"\1<redacted:github>"),
    ("slack", re.compile(r"\b(xox[abpr]-)[0-9A-Za-z\-]{10,}"), r"\1<redacted:slack>"),
    ("google", re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"), "AIza<redacted:google>"),
    ("openai", re.compile(r"\b(sk-)[A-Za-z0-9]{20,}"), r"\1<redacted:openai>"),
    ("query_token", re.compile(r"((?:access_token|api_?key|apikey|auth_?token|secret|password|passwd|pwd)=)(?!MLY|[sp]k\.)[^&\s\"'<>\\]{6,}", re.I), r"\1<redacted:param>"),
    ("query_key", re.compile(r"([?&;]key=)[A-Za-z0-9_\-]{16,}"), r"\1<redacted:param>"),
]


def redact_text(s: str) -> str:
    for _, pat, repl in PATTERNS:
        s = pat.sub(repl, s)
    return s


def redact_obj(o):
    if isinstance(o, str):
        return redact_text(o)
    if isinstance(o, list):
        return [redact_obj(x) for x in o]
    if isinstance(o, dict):
        return {k: redact_obj(v) for k, v in o.items()}
    return o


def count_hits(s: str) -> dict[str, int]:
    return {name: len(pat.findall(s)) for name, pat, _ in PATTERNS if pat.search(s)}


if __name__ == "__main__":
    import json
    import sys
    # In-place pass over jsonl / tsv files given on the command line.
    for path in sys.argv[1:]:
        text = open(path, encoding="utf-8").read()
        before = count_hits(text)
        if path.endswith(".jsonl"):
            out = "".join(json.dumps(redact_obj(json.loads(l)), ensure_ascii=False) + "\n" for l in text.splitlines() if l.strip())
        else:
            out = redact_text(text)
        open(path, "w", encoding="utf-8").write(out)
        print(f"{path}: {before or 'clean'} -> {count_hits(out) or 'clean'}")
