#!/usr/bin/env python3
"""Sample N well-formed and N unclassified rows from urls.parsed.jsonl.

Used to spot-check parser and classifier passes.
"""

import argparse
import json
import random
import sys
from typing import Iterable

DEFAULT_IN = "/collusionwiki/analyses/oai-url-taxonomy/outputs/urls.parsed.jsonl"


def load_pred(path: str, pred) -> list[dict]:
    out = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if pred(r):
                out.append(r)
    return out


def _fmt(r: dict, show_first_page: bool = False) -> str:
    p = r.get("parsed", {})
    lines = [
        f"URL: {r['url'][:280]}",
        f"  well_formed={p.get('is_well_formed')}"
        f"  wrappers={p.get('wrappers')}"
        f"  base_host={p.get('base_host')}"
        f"  bail={p.get('bail')}",
        f"  base_url={ (p.get('base_url') or '')[:220] }",
    ]
    if p.get("transforms"):
        lines.append(f"  transforms={p['transforms']}")
    if show_first_page:
        lines.append(f"  first_page_url={r.get('first_page_url','')[:200]}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=DEFAULT_IN)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--n-wf", type=int, default=10, help="how many well-formed to sample")
    ap.add_argument("--n-un", type=int, default=10, help="how many unclassified to sample")
    ap.add_argument("--pool", choices=("all", "no-wrap", "with-wrap"), default="all",
                    help="restrict well-formed pool")
    ap.add_argument("--first-page", action="store_true")
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    def wf_pred(r):
        p = r.get("parsed", {})
        if not p.get("is_well_formed"):
            return False
        if args.pool == "no-wrap":
            return not p.get("wrappers")
        if args.pool == "with-wrap":
            return bool(p.get("wrappers"))
        return True

    def un_pred(r):
        return not r.get("parsed", {}).get("is_well_formed", False)

    wf = load_pred(args.inp, wf_pred)
    un = load_pred(args.inp, un_pred)
    print(f"pool: well_formed({args.pool})={len(wf)}  unclassified={len(un)}", file=sys.stderr)

    sample_wf = random.sample(wf, min(args.n_wf, len(wf)))
    sample_un = random.sample(un, min(args.n_un, len(un)))

    print("=" * 20, "WELL-FORMED SAMPLE", "=" * 20)
    for r in sample_wf:
        print(_fmt(r, args.first_page))
        print()

    print("=" * 20, "UNCLASSIFIED SAMPLE", "=" * 20)
    for r in sample_un:
        print(_fmt(r, args.first_page))
        print()


if __name__ == "__main__":
    main()
