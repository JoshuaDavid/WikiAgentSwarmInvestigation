#!/usr/bin/env python3
"""Run one iteration of the sample-and-check loop.

For a given seed:

  1. Classify every URL with the current predicate library.
  2. Sample up to 20 URLs that at least one predicate flagged.  Show them.
  3. Sample 100 URLs that no predicate flagged.  Show them.

The user (or a follow-up commit) can inspect and add predicates.
"""

import json
import random
import sys

sys.path.insert(0, "/collusionwiki/analyses/oai-spider-url-triage")

import predicates  # type: ignore

URLS_JSONL = "/collusionwiki/analyses/oai-spider-url-triage/outputs/urls.jsonl"


def main() -> None:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    n_match = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    n_miss = int(sys.argv[3]) if len(sys.argv) > 3 else 100

    rows = [json.loads(l) for l in open(URLS_JSONL)]
    matched = []
    unmatched = []
    for r in rows:
        hits = predicates.classify(r["url"])
        r["hits"] = hits
        (matched if hits else unmatched).append(r)

    print(f"pool: matched={len(matched)}  unmatched={len(unmatched)}", file=sys.stderr)
    random.seed(seed)
    ms = random.sample(matched, min(n_match, len(matched)))
    us = random.sample(unmatched, min(n_miss, len(unmatched)))

    print(f"\n===== MATCHED SAMPLE ({len(ms)}) =====")
    for r in ms:
        print(f"[{','.join(r['hits'])[:70]}]")
        print(f"  {r['url']}")

    print(f"\n===== UNMATCHED SAMPLE ({len(us)}) =====")
    for r in us:
        print(f"  {r['url'][:230]}")


if __name__ == "__main__":
    main()
