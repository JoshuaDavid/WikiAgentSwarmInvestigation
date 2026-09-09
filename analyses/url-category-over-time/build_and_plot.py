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


def date_range(start: str, end: str) -> list[str]:
    y1, m1, d1 = (int(x) for x in start.split("-"))
    y2, m2, d2 = (int(x) for x in end.split("-"))
    a, b = date(y1, m1, d1), date(y2, m2, d2)
    out, cur = [], a
    while cur <= b:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


WINDOW_START = "2026-05-01"


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
    for (d, c, h), n in in_win.items():
        cat_total_win[c] += n
        cat_hosts_win[c].add(h)
        host_total_win[h] += n

    # Per-category pre-window totals (undated + pre 2026-05-01).
    cat_total_pre: dict[str, int] = defaultdict(int)
    for (c, h), n in pre_win.items():
        cat_total_pre[c] += n

    # TSV output.
    with (OUT_DIR / "urls_by_date_host.tsv").open("w") as f:
        f.write("date\tcategory\thost\toccurrences\n")
        for (d, c, h), n in sorted(
            in_win.items(),
            key=lambda kv: (kv[0][0], cat_rank.get(kv[0][1], 999), -kv[1]),
        ):
            f.write(f"{d}\t{c}\t{h}\t{n}\n")

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

    def nice_ymax(v: int) -> int:
        if v <= 0:
            return 1
        for step in [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000,
                     2000, 5000, 10000, 20000, 50000, 100000]:
            for mult in range(1, 11):
                if step * mult >= v:
                    return step * mult
        return v
    y_max_r = nice_ymax(y_max)

    def y_at(v: float) -> float:
        return MARGIN_T + plot_h - plot_h * v / y_max_r

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="12">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">URL occurrences per '
        f'day — stacked bar, one segment per host, colored by host type</text>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="46" text-anchor="middle" '
        f'fill="#555">Sources: prowiki + pastes + gems. '
        f'Hosts in the same category share a color.</text>',
    ]

    # Y grid.
    for k in range(6):
        v = int(round(y_max_r * k / 5))
        y = y_at(v)
        parts.append(
            f'<line x1="{MARGIN_L}" y1="{y:.1f}" x2="{MARGIN_L + plot_w}" '
            f'y2="{y:.1f}" stroke="#eee" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{MARGIN_L - 6}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="#333">{v:,}</text>'
        )

    # Bars: for each day, stack hosts bottom-up in (category, host size) order.
    per_day: dict[str, dict[tuple[str, str], int]] = defaultdict(dict)
    for (d, c, h), n in in_win.items():
        per_day[d][(c, h)] = n

    for i, d in enumerate(dates):
        segs = per_day.get(d, {})
        if not segs:
            continue
        ordered = sorted(segs.items(), key=lambda kv: stack_key(kv[0]))
        x = x_left(i)
        base = 0.0
        for (cat, host), n in ordered:
            hue = cat_hue.get(cat, -1)
            color = category_color(hue)
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
        f'text-anchor="middle" fill="#333">URL occurrences</text>'
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

    # Legend: categories sorted by in-window total desc.
    lx = MARGIN_L + plot_w + 24
    ly = MARGIN_T
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'category color · in-window · hosts · (pre-window)</text>'
    )
    ly += 22

    sorted_cats = sorted(
        cat_order,
        key=lambda c: (-cat_total_win.get(c, 0), cat_rank.get(c, 999)),
    )
    for cat in sorted_cats:
        n_win = cat_total_win.get(cat, 0)
        if n_win == 0 and cat_total_pre.get(cat, 0) == 0:
            continue
        color = category_color(cat_hue.get(cat, -1))
        n_hosts = len(cat_hosts_win.get(cat, set()))
        pre = cat_total_pre.get(cat, 0)
        parts.append(
            f'<rect x="{lx}" y="{ly - 10}" width="16" height="12" '
            f'fill="{color}"/>'
        )
        pre_str = f'  +{pre:,} pre-window' if pre else ''
        parts.append(
            f'<text x="{lx + 22}" y="{ly}" fill="#111">{escape(cat)}'
            f'<tspan fill="#666"> · {n_win:,} URLs · {n_hosts} hosts'
            f'{escape(pre_str)}</tspan></text>'
        )
        ly += 18

    ly += 12
    total_win = sum(cat_total_win.values())
    total_pre = sum(cat_total_pre.values())
    n_hosts_all = sum(len(v) for v in cat_hosts_win.values())
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'window: {WINDOW_START} → {dates[-1]}</text>'
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
