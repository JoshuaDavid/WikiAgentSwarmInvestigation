"""Per-class fraction of wiki-access-log hits that are the 10th-or-later
hit on the same URL within a trailing 25-minute window.

For each (class, url) group we sort hits by timestamp, then for each hit
at index k (0-indexed) mark it a "burst hit" if k >= 9 and
ts[k] - ts[k-9] <= 25*60. That is: the current hit plus the 9 preceding
hits on the same URL from IPs in the same class all fit in a 25-minute
window ending at the current hit.

Restriction: only pre-disclosure rows (ts <= 2026-09-04 23:59:59 UTC).
The post-disclosure activity is admin cleanup + researcher probes and is
tagged out by memory `project_post_disclosure_activity`.

Class assignment: `truth_class` column from
`analyses/hour-bayesian/outputs/ip_classification.tsv`. IPs without a
classification row are skipped (they carry no cluster identity).

Reads:
- /collusionwiki/tmp/wiki-access-logs/all.db (17.7M rows)
- analyses/hour-bayesian/outputs/ip_classification.tsv (IP → class)

Writes:
- outputs/repeat_hits_by_class.tsv
- outputs/repeat_hits_top_urls.tsv  (per-class top URLs by burst count)

Strategy: attach classified-IPs as a temp table, JOIN, ORDER BY
(class, url, ts) so hits stream in per-group order. Process each group
in memory as it flushes. Avoids loading 17.7M rows into a Python dict.
"""
from __future__ import annotations
import csv
import heapq
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ACCESS_DB = REPO / "tmp" / "wiki-access-logs" / "all.db"
CLASS_TSV = REPO / "analyses" / "hour-bayesian" / "outputs" / "ip_classification.tsv"
OUT_DIR = Path(__file__).resolve().parent / "outputs"

CUTOFF_TS = 1788479999   # 2026-09-04 23:59:59 UTC — pre-disclosure only
WINDOW_S = 25 * 60       # 25-minute trailing window
K = 10                   # count hit if it's the K-th or later in the window
TOP_URLS_PER_CLASS = 20


def flush(cls, url, ts_list, class_total, class_burst, class_url_burst,
          class_urls_with_burst, class_urls):
    n = len(ts_list)
    class_total[cls] += n
    class_urls[cls] += 1
    if n < K:
        return
    ts_list.sort()
    n_burst = 0
    for k in range(K - 1, n):
        if ts_list[k] - ts_list[k - (K - 1)] <= WINDOW_S:
            n_burst += 1
    if n_burst:
        class_burst[cls] += n_burst
        class_urls_with_burst[cls] += 1
        heap = class_url_burst[cls]
        item = (n_burst, url)
        if len(heap) < TOP_URLS_PER_CLASS:
            heapq.heappush(heap, item)
        elif item > heap[0]:
            heapq.heapreplace(heap, item)


def main() -> None:
    print("loading ip→class …", flush=True)
    ip_class: dict[str, str] = {}
    with CLASS_TSV.open() as fh:
        r = csv.DictReader(fh, delimiter="\t")
        for row in r:
            ip_class[row["ip"]] = row["truth_class"]
    print(f"  {len(ip_class):,} classified IPs", flush=True)

    print("scanning + streaming access log …", flush=True)
    cx = sqlite3.connect(ACCESS_DB)
    cx.execute("CREATE TEMP TABLE ipcls (ip TEXT PRIMARY KEY, cls TEXT NOT NULL)")
    cx.executemany(
        "INSERT INTO ipcls(ip, cls) VALUES (?, ?)",
        ip_class.items(),
    )
    cx.commit()
    print(f"  loaded {len(ip_class):,} rows into TEMP ipcls", flush=True)

    class_total = Counter()
    class_burst = Counter()
    class_urls = Counter()
    class_urls_with_burst = Counter()
    class_url_burst: dict[str, list[tuple[int, str]]] = defaultdict(list)

    cur_cls = cur_url = None
    ts_list: list[int] = []
    n_processed = 0

    query = """
        SELECT c.cls AS cls, a.action AS url, a.ts AS ts
          FROM access a
          JOIN ipcls c ON a.ip = c.ip
         WHERE a.ts <= ?
           AND a.action IS NOT NULL
         ORDER BY c.cls, a.action, a.ts
    """
    for cls, url, ts in cx.execute(query, (CUTOFF_TS,)):
        if cls != cur_cls or url != cur_url:
            if cur_cls is not None:
                flush(
                    cur_cls, cur_url, ts_list,
                    class_total, class_burst, class_url_burst,
                    class_urls_with_burst, class_urls,
                )
            cur_cls, cur_url = cls, url
            ts_list = []
        ts_list.append(ts)
        n_processed += 1
        if n_processed % 500_000 == 0:
            print(f"  {n_processed:>10,} rows processed  (class={cur_cls})",
                  flush=True)
    if cur_cls is not None:
        flush(
            cur_cls, cur_url, ts_list,
            class_total, class_burst, class_url_burst,
            class_urls_with_burst, class_urls,
        )
    print(f"  done. {n_processed:,} rows", flush=True)

    OUT_DIR.mkdir(exist_ok=True, parents=True)
    with (OUT_DIR / "repeat_hits_by_class.tsv").open("w") as fh:
        fh.write(
            "class\ttotal_hits\tburst_hits\tfrac_burst"
            "\turls_with_burst\turls_total\tmean_burst_per_url\n"
        )
        for cls in sorted(class_total, key=lambda c: -class_total[c]):
            tot = class_total[cls]
            b = class_burst[cls]
            n_urls = class_urls[cls]
            n_urls_b = class_urls_with_burst[cls]
            mean_b = (b / n_urls_b) if n_urls_b else 0.0
            fh.write(
                f"{cls}\t{tot}\t{b}\t{b/tot if tot else 0:.6f}"
                f"\t{n_urls_b}\t{n_urls}\t{mean_b:.2f}\n"
            )
        tot_all = sum(class_total.values())
        burst_all = sum(class_burst.values())
        fh.write(
            f"__ALL__\t{tot_all}\t{burst_all}"
            f"\t{burst_all/tot_all if tot_all else 0:.6f}"
            f"\t{sum(class_urls_with_burst.values())}"
            f"\t{sum(class_urls.values())}"
            f"\t{burst_all/max(sum(class_urls_with_burst.values()),1):.2f}\n"
        )

    with (OUT_DIR / "repeat_hits_top_urls.tsv").open("w") as fh:
        fh.write("class\tburst_hits\turl\n")
        for cls in sorted(class_url_burst):
            top = sorted(class_url_burst[cls], reverse=True)
            for n_b, url in top:
                fh.write(f"{cls}\t{n_b}\t{url}\n")

    print(f"wrote {OUT_DIR/'repeat_hits_by_class.tsv'}")
    print(f"wrote {OUT_DIR/'repeat_hits_top_urls.tsv'}")


if __name__ == "__main__":
    main()
