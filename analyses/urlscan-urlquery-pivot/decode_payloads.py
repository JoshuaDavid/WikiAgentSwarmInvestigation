#!/usr/bin/env python3
"""Decode the HTML pages the swarm smuggled through httpbin.org/base64/.

httpbin.org/base64/<b64> answers with the decoded bytes as text/html. A URL
scanner that is asked to scan such a URL renders the page in its browser and
runs any script in it. The swarm used that to run JavaScript inside
urlquery.net's browser. This script reads outputs/rows.jsonl, decodes every
submitted URL of that shape, and writes outputs/httpbin_payloads.jsonl with:
  time, source, id, link, in_core, payload_len, hosts (every host the script
  references), return_channel (how the script reports its result), and the
  decoded HTML.
It prints a summary table to stdout.
"""

from __future__ import annotations

import base64
import collections
import json
import os
import re
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
import sys  # noqa: E402
sys.path.insert(0, HERE)
from redact import redact_obj  # noqa: E402
OUT = os.path.join(HERE, "outputs")
B64_RE = re.compile(r"httpbin(?:go)?\.org/base64/([^?#\s]+)", re.I)
HOST_RE = re.compile(r"https?://([a-z0-9.-]+\.[a-z]{2,})", re.I)

RETURN_MARKERS = [
    ("document.title", r"document\.title\s*="),
    ("dom_text", r"(?:innerText|textContent|append\(|\.innerHTML\s*=|<pre)"),
    ("image_beacon", r"new Image\(\)\.src|\.src\s*=\s*['\"]https?://"),
    ("fetch_beacon", r"fetch\(['\"]https?://(?:ntfy|webhook|pie\.dev|httpbingo|example\.com/(?:exfil|collector))"),
    ("post", r"method:\s*['\"]POST['\"]"),
]


def decode(url: str) -> str | None:
    m = B64_RE.search(url)
    if not m:
        return None
    s = urllib.parse.unquote(m.group(1)).replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    try:
        return base64.b64decode(s).decode("utf-8", "replace")
    except Exception:
        return None


def main() -> None:
    rows = [json.loads(l) for l in open(os.path.join(OUT, "rows.jsonl"))]
    out = []
    for r in rows:
        html = decode(r["url"])
        if html is None or len(html) < 20:
            continue
        hosts = sorted(set(h.lower() for h in HOST_RE.findall(html)))
        channels = [name for name, pat in RETURN_MARKERS if re.search(pat, html)]
        out.append({
            "time": r["time"], "source": r["source"], "id": r["id"], "link": r["link"],
            "in_core": r["in_core"], "payload_len": len(html), "hosts": hosts,
            "return_channel": channels, "html": html,
        })
    out.sort(key=lambda x: x["time"])
    with open(os.path.join(OUT, "httpbin_payloads.jsonl"), "w") as f:
        for x in out:
            f.write(json.dumps(redact_obj(x), ensure_ascii=False) + "\n")

    core = [x for x in out if x["in_core"]]
    print(f"payloads: {len(out)} total, {len(core)} in core window")
    print("by month:", sorted(collections.Counter(x['time'][:7] for x in out).items()))
    print("\nhosts referenced inside core-window payloads:")
    hc = collections.Counter(h for x in core for h in x["hosts"])
    for h, n in hc.most_common(25):
        print(f"  {n:4} {h}")
    print("\nreturn channels (core window):")
    for k, n in collections.Counter(tuple(x["return_channel"]) for x in core).most_common(10):
        print(f"  {n:4} {'+'.join(k) or '(none detected)'}")
    print("\ncore-window payload days:", sorted(collections.Counter(x['time'][:10] for x in core).items()))


if __name__ == "__main__":
    main()
