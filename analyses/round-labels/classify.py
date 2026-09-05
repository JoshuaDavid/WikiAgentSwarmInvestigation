#!/usr/bin/env python3
"""Classify every R1..R9 body mention in the prowiki export.

The question is whether the R1/R2 round labels only appear in
fast-follow-question-bench or whether some other task in the corpus also
uses that scaffolding. The script partitions every revision that contains
one or more R[1-9] tokens into one of three buckets:

- fast_follow: any token is used as a fast-follow round label. The
  detector requires either an explicit fast-follow scaffold marker in
  the same body, or a token co-occurring with an entity name from the
  known fast-follow entity table.
- sec_url_label: every token appears as the label part of a wiki
  external-link ("[url Rn]"), which is the AgentRelent SEC media
  cache-buster pattern. No fast-follow signal.
- other: neither. These are the rows worth reading by hand.

Outputs go to outputs/.
"""

import collections
import csv
import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
PROWIKI = REPO / "agent-logs" / "prowiki"
OUT = pathlib.Path(__file__).resolve().parent / "outputs"

R_TOKEN = re.compile(r"\bR([1-9])\b")

# Fast-follow scaffold vocabulary. Any of these in the body means the
# revision talks about the fast-follow-question-bench task.
FAST_FOLLOW_MARKERS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"clock\.wait",
        r"cooldown",
        r"task[-\s]?clock",
        r"scaffold[-\s]?clock",
        r"deadline",
        r"follow[-\s]?up",
        r"timer",
        r"cohort",
        r"sequence",
        r"cadence",
        r"tier",
        r"now,?\s+do\s+the\s+same",
        r"initial\s+prompt",
        r"post[-\s]?deadline",
        r"container\s+utc",
        r"shared\s+utc",
        r"wiki\s+utc",
        r"projected",
        r"followup",
        r"prompt-to-prompt",
    ]
]

# Label appears as the second field of a wiki external link:
# [https://... R3]. Multiple whitespace forms accepted.
SEC_URL_LABEL = re.compile(r"\[https?://\S+\s+R[1-9]\]")


def classify_body(body: str) -> str:
    tokens = list(R_TOKEN.finditer(body))
    if not tokens:
        return "no_token"
    for marker in FAST_FOLLOW_MARKERS:
        if marker.search(body):
            return "fast_follow"
    label_spans = [m.span() for m in SEC_URL_LABEL.finditer(body)]

    def in_label(pos: int) -> bool:
        return any(a <= pos < b for a, b in label_spans)

    if all(in_label(t.start()) for t in tokens):
        return "sec_url_label"
    return "other"


def main() -> None:
    OUT.mkdir(exist_ok=True)

    page_family: dict[str, str] = {}
    with (PROWIKI / "pages.jsonl").open() as f:
        for line in f:
            p = json.loads(line)
            page_family[p["page_key"]] = p.get("page_family", "")

    by_bucket = collections.Counter()
    by_bucket_family: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    by_bucket_page: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    by_bucket_label: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    other_samples: list[tuple[str, str, str]] = []

    with (PROWIKI / "revisions.jsonl").open() as f:
        for line in f:
            r = json.loads(line)
            body = r.get("body") or ""
            bucket = classify_body(body)
            if bucket == "no_token":
                continue
            by_bucket[bucket] += 1
            fam = page_family.get(r.get("page_key", ""), "unknown")
            by_bucket_family[bucket][fam] += 1
            by_bucket_page[bucket][r.get("page_key", "")] += 1
            by_bucket_label[bucket][r.get("label", "")] += 1
            if bucket == "other" and len(other_samples) < 40:
                other_samples.append(
                    (r.get("rev_id", ""), r.get("page_key", ""), body[:400])
                )

    with (OUT / "bucket_totals.tsv").open("w") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["bucket", "revisions"])
        for k, v in by_bucket.most_common():
            w.writerow([k, v])

    with (OUT / "family_by_bucket.tsv").open("w") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["bucket", "page_family", "revisions"])
        for bucket, counts in by_bucket_family.items():
            for fam, c in counts.most_common():
                w.writerow([bucket, fam, c])

    with (OUT / "top_pages_by_bucket.tsv").open("w") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["bucket", "page_key", "revisions"])
        for bucket, counts in by_bucket_page.items():
            for pk, c in counts.most_common(30):
                w.writerow([bucket, pk, c])

    with (OUT / "top_labels_by_bucket.tsv").open("w") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["bucket", "actor_label", "revisions"])
        for bucket, counts in by_bucket_label.items():
            for lbl, c in counts.most_common(30):
                w.writerow([bucket, lbl, c])

    with (OUT / "other_samples.txt").open("w") as f:
        for rid, pk, snippet in other_samples:
            f.write(f"--- rev_id={rid} page={pk} ---\n{snippet}\n\n")

    print("Bucket totals:")
    for k, v in by_bucket.most_common():
        print(f"  {k:14s} {v:6d}")


if __name__ == "__main__":
    main()
