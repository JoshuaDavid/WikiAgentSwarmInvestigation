#!/usr/bin/env python3
"""Walk oai-index-scan shards in filename order, emit one line per distinct
in-page URL with its earliest-source metadata."""

import json
import glob
import os
import re
import sys
from collections import OrderedDict

SHARD_GLOB = "/collusionwiki/oai-index-scan/results/shards/*.results.jsonl"
OUT_PATH = "/collusionwiki/analyses/oai-url-taxonomy/outputs/urls.jsonl"

# Requirement: the output file is committed to a repo whose remote runs secret
# scanning. Scraped URLs sometimes carry AWS presigned parameters and API-key
# query strings from third-party services.
# The scanner blocks pushes that contain those literal tokens.
# The taxonomy analysis needs the shape of the URL, not the token value.
# Therefore we replace the value of any query parameter whose name matches
# one of the known-credential names below with the literal REDACTED before
# writing the JSONL line.
_CRED_PARAMS = (
    "api_key",
    "apikey",
    "api\\_key",
    "X-Amz-Credential",
    "X-Amz-Signature",
    "X-Amz-Security-Token",
    "AWSAccessKeyId",
    "aws_access_key_id",
    "aws_secret_access_key",
    "signature",
    "access_token",
    "token",
    "auth",
)
_CRED_RE = re.compile(
    r"([?&;]|%26|%3B)(" + "|".join(re.escape(p) for p in _CRED_PARAMS) + r")(=|%3D)([^&;#\s]+)",
    re.IGNORECASE,
)
_AKIA_RE = re.compile(r"AKIA[0-9A-Z]{16}")


def redact(url: str) -> str:
    """Redact query-parameter values whose name looks like a credential.

    The parser downstream only cares about parameter names, base host, and
    transform kinds, so replacing the value with the literal REDACTED keeps
    the URL parseable and shape-preserving.
    """
    def _sub(m: "re.Match") -> str:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}REDACTED"
    url = _CRED_RE.sub(_sub, url)
    url = _AKIA_RE.sub("AKIAREDACTEDREDACT01", url)
    return url


def main() -> None:
    shards = sorted(glob.glob(SHARD_GLOB))
    seen: "OrderedDict[str, dict]" = OrderedDict()

    for shard in shards:
        shard_name = os.path.basename(shard)
        with open(shard) as f:
            for line_no, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                urls = row.get("urls_in_page") or []
                page_url = redact(row.get("page_url", ""))
                page_title = row.get("page_title", "")
                fsq = row.get("first_seen_query", "")
                for u in urls:
                    if not isinstance(u, str):
                        continue
                    u = redact(u)
                    if u in seen:
                        seen[u]["occurrence_count"] += 1
                        continue
                    seen[u] = {
                        "url": u,
                        "first_shard": shard_name,
                        "first_line": line_no,
                        "first_page_url": page_url,
                        "first_page_title": page_title,
                        "first_seen_query": fsq,
                        "occurrence_count": 1,
                    }

    with open(OUT_PATH, "w") as f:
        for row in seen.values():
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(seen)} distinct URLs to {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
