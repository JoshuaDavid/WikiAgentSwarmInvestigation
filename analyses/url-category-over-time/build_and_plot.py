#!/usr/bin/env python3
"""Read analyses/urls/outputs/urls-classified.jsonl (prowiki + pastes + gems).
For every URL occurrence, bucket by (UTC date, host). Write:

  outputs/urls_by_date_host.tsv       date, category, host, occurrences
  outputs/urls_stacked_bar_by_host.svg  stacked bar per date, segments = hosts,
                                        colored by the host's category.

Pure stdlib. Rerun with:
    python3 analyses/url-category-over-time/build_and_plot.py
"""
from __future__ import annotations
import colorsys
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
URL_PATH = REPO_ROOT / "analyses" / "urls" / "outputs" / "urls-classified.jsonl"
OUT_DIR = HERE / "outputs"

# Categories, in stack order (top of stack = first in this list).
# Each has (label, group_hue). Group hues are shared with hand-picked bundles
# so related categories read as one color family in the chart.
CATEGORIES: list[tuple[str, int]] = [
    ("wiki_self",                215),
    ("jq_json_relay",             10),
    ("fetch_proxy_markdown",      25),
    ("cors_proxy",                40),
    ("google_translate_proxy",     0),
    ("data_source_sec_investor", 130),
    ("data_source_datausa",      145),
    ("data_source_us_gov",       160),
    ("data_source_health",       115),
    ("data_source_finance",      100),
    ("data_source_library",       85),
    ("data_source_publishing",   175),
    ("data_source_other",         70),
    ("archive_wayback",          195),
    ("cloud_storage_dropbox",    210),
    ("google_docs",              230),
    ("url_shortener",            290),
    ("counter_signalling",       310),
    ("test_placeholder",         330),
    ("obfuscated_or_malformed",  350),
    ("unclassified",              -1),
]


def hsl_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def category_color(hue: int) -> str:
    if hue < 0:
        return "#888888"
    return hsl_hex(hue, 0.55, 0.48)


def host_color(hue: int, rank: int, count: int) -> str:
    """Within-category variation: shift lightness (and mildly hue) so multiple
    featured hosts in the same category can be told apart in a stacked bar."""
    if hue < 0:
        return "#888888"
    if count == 1:
        return hsl_hex(hue, 0.55, 0.48)
    frac = rank / (count - 1)  # 0 for first (largest), 1 for last
    hue_j = hue + (frac - 0.5) * 24
    sat = 0.50 + 0.20 * (1 - abs(frac - 0.5) * 2)
    light = 0.34 + frac * 0.34
    return hsl_hex(hue_j, sat, light)


OTHER_COLOR = "#bbbbbb"


def date_range(start: str, end: str) -> list[str]:
    y1, m1, d1 = (int(x) for x in start.split("-"))
    y2, m2, d2 = (int(x) for x in end.split("-"))
    a, b = date(y1, m1, d1), date(y2, m2, d2)
    out, cur = [], a
    while cur <= b:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


# Window: 2026-01-01 onwards. The chart auto-starts at the earliest in-window
# date (currently 2026-02-26 from an anna.fyi paste). Anything older — a
# handful of scattered rows from 2018–2025, mostly ludism — is aggregated
# into the legend's "pre-window" counts.
WINDOW_START = "2026-01-01"


def collect() -> tuple[
    dict[tuple[str, str, str], int],   # (date, cat, host) -> count
    dict[tuple[str, str], int],        # (cat, host) -> pre-window count
    dict[str, str],                    # host -> category
]:
    in_window: dict[tuple[str, str, str], int] = defaultdict(int)
    pre_window: dict[tuple[str, str], int] = defaultdict(int)
    host_cat: dict[str, str] = {}
    with URL_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            host = r.get("host") or ""
            cat = r.get("category") or "unclassified"
            host_cat[host] = cat
            t = r.get("time") or ""
            d = t[:10] if len(t) >= 10 else ""
            if d and d >= WINDOW_START:
                in_window[(d, cat, host)] += 1
            else:
                pre_window[(cat, host)] += 1
    return in_window, pre_window, host_cat


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    in_win, pre_win, host_cat = collect()
    if not in_win:
        raise RuntimeError("no in-window URLs found")

    dates_present = sorted({d for (d, _, _) in in_win})
    dates = date_range(dates_present[0], dates_present[-1])
    n_days = len(dates)

    cat_hue = dict(CATEGORIES)
    cat_order = [c for c, _ in CATEGORIES]
    cat_rank = {c: i for i, c in enumerate(cat_order)}

    # Per-category totals across the window (in-window only).
    cat_total_win: dict[str, int] = defaultdict(int)
    cat_hosts_win: dict[str, set[str]] = defaultdict(set)
    host_total_win: dict[str, int] = defaultdict(int)
    host_cat: dict[str, str] = {}
    for (d, c, h), n in in_win.items():
        cat_total_win[c] += n
        cat_hosts_win[c].add(h)
        host_total_win[h] += n
        host_cat[h] = c

    # Per-category pre-window totals (undated + pre 2026-05-01).
    cat_total_pre: dict[str, int] = defaultdict(int)
    for (c, h), n in pre_win.items():
        cat_total_pre[c] += n

    # Featured hosts: the smallest set whose in-window URL counts sum to
    # >= 90% of the total. Everything else goes into a single grey "other"
    # segment (per day).
    hosts_ranked = sorted(host_total_win.items(), key=lambda kv: -kv[1])
    total_win = sum(host_total_win.values())
    cutoff = 0.90 * total_win
    featured: list[str] = []
    cum = 0
    for host, n in hosts_ranked:
        featured.append(host)
        cum += n
        if cum >= cutoff:
            break
    featured_set = set(featured)

    # Per-host color: category hue + within-category shading. Featured hosts
    # within a category are ranked by in-window count (largest = rank 0).
    per_cat_featured: dict[str, list[str]] = defaultdict(list)
    for host in featured:
        per_cat_featured[host_cat[host]].append(host)
    host_to_color: dict[str, str] = {}
    for cat, hosts in per_cat_featured.items():
        hue = cat_hue.get(cat, -1)
        for i, host in enumerate(hosts):
            host_to_color[host] = host_color(hue, i, len(hosts))

    # TSV output.
    with (OUT_DIR / "urls_by_date_host.tsv").open("w") as f:
        f.write("date\tcategory\thost\toccurrences\tfeatured\n")
        for (d, c, h), n in sorted(
            in_win.items(),
            key=lambda kv: (kv[0][0], cat_rank.get(kv[0][1], 999), -kv[1]),
        ):
            f.write(f"{d}\t{c}\t{h}\t{n}\t{1 if h in featured_set else 0}\n")

    # Stack order within each bar: category rank asc, then host total desc.
    # We render bottom-up, so the first entries end up at the bottom.
    def stack_key(item: tuple[str, str]) -> tuple[int, int]:
        cat, host = item
        return (cat_rank.get(cat, 999), -host_total_win[host])

    # Per-day totals for y-axis scaling.
    day_total: dict[str, int] = defaultdict(int)
    for (d, _, _), n in in_win.items():
        day_total[d] += n
    y_max = max(day_total.values()) if day_total else 1

    # Layout.
    W, H = 1600, 780
    MARGIN_L, MARGIN_R = 80, 420
    MARGIN_T, MARGIN_B = 74, 110
    plot_w = W - MARGIN_L - MARGIN_R
    plot_h = H - MARGIN_T - MARGIN_B
    bar_pitch = plot_w / n_days
    bar_w = max(2.0, bar_pitch * 0.85)

    def x_left(i: int) -> float:
        return MARGIN_L + i * bar_pitch + (bar_pitch - bar_w) / 2

    # Log-scale y-axis. The chart is a stacked bar in log space: each
    # segment's cumulative bottom and top are mapped through log10, and the
    # visible height of a segment is log(cum_top) - log(cum_bot). Segments
    # near the bottom of the stack take most of the visible height; segments
    # further up compress. The single-URL floor is Y_MIN = 1 (log10 = 0).
    import math
    Y_MIN = 1.0
    Y_MAX = 10.0 ** math.ceil(math.log10(max(y_max, 10)))  # next power of 10
    LOG_MIN = math.log10(Y_MIN)
    LOG_MAX = math.log10(Y_MAX)

    def y_at(v: float) -> float:
        # Clamp values below Y_MIN to the baseline.
        v = v if v > Y_MIN else Y_MIN
        frac = (math.log10(v) - LOG_MIN) / (LOG_MAX - LOG_MIN)
        return MARGIN_T + plot_h - plot_h * frac

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="12">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">URL occurrences per '
        f'day — stacked bar; top hosts colored individually, long tail in '
        f'grey "other"</text>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="46" text-anchor="middle" '
        f'fill="#555">Sources: prowiki + apchem + wiki4d + ludism + milkwiki + '
        f'texteditors + pastes + gems + popcat-wayback + per-site paste scrapes. '
        f'Y-axis is log10; hosts in the same category share a hue.</text>',
    ]

    # Y grid — one line per power of 10, plus minor lines at 2/5 of each
    # decade so the reader can eyeball intermediate values.
    n_decades = int(round(LOG_MAX - LOG_MIN))
    for k in range(n_decades + 1):
        v = 10 ** (int(LOG_MIN) + k)
        y = y_at(v)
        parts.append(
            f'<line x1="{MARGIN_L}" y1="{y:.1f}" x2="{MARGIN_L + plot_w}" '
            f'y2="{y:.1f}" stroke="#ccc" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{MARGIN_L - 6}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="#333">{v:,}</text>'
        )
        # Minor decade ticks at 2× and 5× within each decade.
        if k < n_decades:
            for m in (2, 5):
                y = y_at(v * m)
                parts.append(
                    f'<line x1="{MARGIN_L}" y1="{y:.1f}" '
                    f'x2="{MARGIN_L + plot_w}" y2="{y:.1f}" '
                    f'stroke="#eee" stroke-width="1"/>'
                )

    # Bars: for each day, stack featured hosts bottom-up in (category, host
    # size) order, then a single grey "other" segment at the top covering
    # every non-featured host for that day.
    per_day: dict[str, dict[tuple[str, str], int]] = defaultdict(dict)
    per_day_other: dict[str, tuple[int, int]] = {}  # day -> (urls, host_count)
    for (d, c, h), n in in_win.items():
        if h in featured_set:
            per_day[d][(c, h)] = n
    for d in dates:
        other_urls = 0
        other_hosts: set[str] = set()
        for (dd, c, h), n in in_win.items():
            if dd == d and h not in featured_set:
                other_urls += n
                other_hosts.add(h)
        if other_urls:
            per_day_other[d] = (other_urls, len(other_hosts))

    for i, d in enumerate(dates):
        segs = per_day.get(d, {})
        if not segs and d not in per_day_other:
            continue
        ordered = sorted(segs.items(), key=lambda kv: stack_key(kv[0]))
        x = x_left(i)
        base = 0.0
        for (cat, host), n in ordered:
            color = host_to_color.get(host, category_color(cat_hue.get(cat, -1)))
            top = base + n
            y0 = y_at(top)
            y1 = y_at(base)
            h_px = max(0.6, y1 - y0)
            parts.append(
                f'<rect x="{x:.1f}" y="{y0:.1f}" width="{bar_w:.2f}" '
                f'height="{h_px:.2f}" fill="{color}">'
                f'<title>{escape(d)} · {escape(host)} ({escape(cat)}): '
                f'{n:,} URL occurrences</title></rect>'
            )
            base = top
        # "other" segment sits on top.
        if d in per_day_other:
            other_urls, other_hosts_n = per_day_other[d]
            top = base + other_urls
            y0 = y_at(top)
            y1 = y_at(base)
            h_px = max(0.6, y1 - y0)
            parts.append(
                f'<rect x="{x:.1f}" y="{y0:.1f}" width="{bar_w:.2f}" '
                f'height="{h_px:.2f}" fill="{OTHER_COLOR}">'
                f'<title>{escape(d)} · other ({other_hosts_n} hosts): '
                f'{other_urls:,} URL occurrences</title></rect>'
            )

    # Axes.
    parts.append(
        f'<line x1="{MARGIN_L}" y1="{MARGIN_T}" x2="{MARGIN_L}" '
        f'y2="{MARGIN_T + plot_h}" stroke="#333" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{MARGIN_L}" y1="{MARGIN_T + plot_h}" '
        f'x2="{MARGIN_L + plot_w}" y2="{MARGIN_T + plot_h}" '
        f'stroke="#333" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{MARGIN_L - 60}" y="{MARGIN_T + plot_h/2:.0f}" '
        f'transform="rotate(-90 {MARGIN_L - 60} {MARGIN_T + plot_h/2:.0f})" '
        f'text-anchor="middle" fill="#333">URL occurrences (log scale)</text>'
    )

    # X labels every ~step days.
    step = max(1, n_days // 22)
    y_axis = MARGIN_T + plot_h
    for i, d in enumerate(dates):
        if i % step != 0 and i != n_days - 1:
            continue
        cx = x_left(i) + bar_w / 2
        parts.append(
            f'<text x="{cx:.1f}" y="{y_axis + 16}" text-anchor="end" '
            f'fill="#333" transform="rotate(-60 {cx:.1f} {y_axis + 16})">'
            f'{d}</text>'
        )

    # Legend: featured hosts (top 90% by URL volume), each with its own color;
    # grey "other" row covers the long tail.
    lx = MARGIN_L + plot_w + 24
    ly = MARGIN_T
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'top hosts (~90% of window URLs)</text>'
    )
    ly += 14
    parts.append(
        f'<text x="{lx}" y="{ly}" fill="#666" font-size="11">'
        f'colored by host; hosts in the same category share a hue with '
        f'lightness variation.</text>'
    )
    ly += 18

    remainder_hosts = hosts_ranked[len(featured):]
    remainder_urls = total_win - cum
    remainder_host_count = len(remainder_hosts)

    # Group featured hosts in the legend by category (matches stack order in
    # the chart) so like-colored hosts sit next to each other.
    for cat in cat_order:
        for host in per_cat_featured.get(cat, []):
            n = host_total_win[host]
            color = host_to_color[host]
            parts.append(
                f'<rect x="{lx}" y="{ly - 10}" width="16" height="12" '
                f'fill="{color}"/>'
            )
            parts.append(
                f'<text x="{lx + 22}" y="{ly}" fill="#111" font-size="12">'
                f'{escape(host)}'
                f'<tspan fill="#666"> · {n:,} · {escape(cat)}</tspan></text>'
            )
            ly += 16

    if remainder_hosts:
        parts.append(
            f'<rect x="{lx}" y="{ly - 10}" width="16" height="12" '
            f'fill="{OTHER_COLOR}"/>'
        )
        parts.append(
            f'<text x="{lx + 22}" y="{ly}" fill="#111" font-size="12">'
            f'other'
            f'<tspan fill="#666"> · {remainder_urls:,} URLs · '
            f'{remainder_host_count:,} hosts</tspan></text>'
        )
        ly += 16

    ly += 16
    total_pre = sum(cat_total_pre.values())
    n_hosts_all = sum(len(v) for v in cat_hosts_win.values())
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'window: {dates[0]} → {dates[-1]}</text>'
    )
    ly += 16
    parts.append(
        f'<text x="{lx}" y="{ly}" fill="#333">'
        f'{total_win:,} URL occurrences · {n_hosts_all} distinct hosts</text>'
    )
    ly += 16
    parts.append(
        f'<text x="{lx}" y="{ly}" fill="#333">'
        f'pre-window (undated or before {WINDOW_START}): {total_pre:,}</text>'
    )

    parts.append("</svg>")
    (OUT_DIR / "urls_stacked_bar_by_host.svg").write_text("\n".join(parts))
    print(f"wrote {OUT_DIR / 'urls_by_date_host.tsv'} "
          f"({len(in_win):,} rows)", file=sys.stderr)
    print(f"wrote {OUT_DIR / 'urls_stacked_bar_by_host.svg'}", file=sys.stderr)


if __name__ == "__main__":
    main()
