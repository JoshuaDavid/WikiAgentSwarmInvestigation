#!/usr/bin/env python3
"""Read analyses/urls/outputs/urls-classified.jsonl. For every URL
occurrence, bucket by (UTC date, category). Write:

  outputs/urls_by_date.tsv        date, category, occurrences
  outputs/urls_stacked_area.svg   stacked area chart (20 categories × 40 days)

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

# Category groups: like categories share a hue, individual categories vary in
# lightness. Order within a group is reflected in the stack order.
CATEGORY_GROUPS = [
    ("own wiki",              215, ["wiki_self"]),
    ("proxies / relays",       15, ["jq_json_relay", "fetch_proxy_markdown",
                                    "cors_proxy", "google_translate_proxy"]),
    ("data sources",          140, ["data_source_sec_investor",
                                    "data_source_datausa",
                                    "data_source_us_gov",
                                    "data_source_library",
                                    "data_source_other",
                                    "data_source_health",
                                    "data_source_publishing",
                                    "data_source_finance"]),
    ("archive / storage",     195, ["archive_wayback", "cloud_storage_dropbox",
                                    "google_docs"]),
    ("obfuscation / test",    285, ["url_shortener", "counter_signalling",
                                    "test_placeholder",
                                    "obfuscated_or_malformed"]),
]


def hsl_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def category_color(group_hue: int, idx: int, n: int) -> str:
    if n == 1:
        return hsl_hex(group_hue, 0.55, 0.48)
    frac = idx / (n - 1)
    hue = group_hue + (frac - 0.5) * 20
    sat = 0.45 + 0.30 * (1 - abs(frac - 0.5) * 2)
    light = 0.32 + frac * 0.42
    return hsl_hex(hue, sat, light)


def date_range(start: str, end: str) -> list[str]:
    y1, m1, d1 = (int(x) for x in start.split("-"))
    y2, m2, d2 = (int(x) for x in end.split("-"))
    a, b = date(y1, m1, d1), date(y2, m2, d2)
    out, cur = [], a
    while cur <= b:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def collect() -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    with URL_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            t = r.get("time") or ""
            if len(t) < 10:
                continue
            cat = r.get("category") or "unknown"
            counts[(t[:10], cat)] += 1
    return counts


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    counts = collect()
    if not counts:
        raise RuntimeError("no URLs found")

    dates_present = sorted({d for (d, _) in counts})
    dates = date_range(dates_present[0], dates_present[-1])

    # Flatten to stack order.
    stack_categories: list[tuple[str, str, str]] = []  # (group, cat, color)
    for group_name, hue, cats in CATEGORY_GROUPS:
        for i, c in enumerate(cats):
            stack_categories.append((group_name, c, category_color(hue, i, len(cats))))

    # Include any category the data has that we didn't map (should be none).
    known = {c for _, _, cats in [(g, h, cs) for g, h, cs in CATEGORY_GROUPS] for c in cats}
    unknown = sorted({c for (_, c) in counts if c not in known})
    for c in unknown:
        stack_categories.append(("(other)", c, "#999"))

    with (OUT_DIR / "urls_by_date.tsv").open("w") as f:
        f.write("date\tcategory\toccurrences\n")
        for (d, c), n in sorted(counts.items()):
            f.write(f"{d}\t{c}\t{n}\n")

    # Compute stack heights.
    day_total: dict[str, int] = defaultdict(int)
    for (d, c), n in counts.items():
        day_total[d] += n
    y_max = max(day_total.values()) if day_total else 1

    # Layout.
    W, H = 1500, 720
    MARGIN_L, MARGIN_R = 80, 380
    MARGIN_T, MARGIN_B = 74, 100
    plot_w = W - MARGIN_L - MARGIN_R
    plot_h = H - MARGIN_T - MARGIN_B

    def x_at(i: int) -> float:
        # Sample points at the centre of each day column.
        return MARGIN_L + (i + 0.5) * (plot_w / len(dates))

    def y_at(v: float) -> float:
        return MARGIN_T + plot_h - plot_h * v / y_max

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="12">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">URL occurrences per '
        f'day, stacked by category</text>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="46" text-anchor="middle" '
        f'fill="#555">Categories share a hue by functional group (own-wiki, '
        f'proxies, data sources, archive/storage, obfuscation/test).</text>',
    ]

    # Y-axis grid.
    def nice_ymax(v: int) -> int:
        if v <= 0:
            return 1
        for step in [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000,
                     2000, 5000, 10000, 20000]:
            for mult in range(1, 11):
                if step * mult >= v:
                    return step * mult
        return v
    y_max_r = nice_ymax(y_max)
    for k in range(6):
        v = int(round(y_max_r * k / 5))
        y = MARGIN_T + plot_h - plot_h * v / y_max_r
        parts.append(
            f'<line x1="{MARGIN_L}" y1="{y:.1f}" x2="{MARGIN_L + plot_w}" '
            f'y2="{y:.1f}" stroke="#eee" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{MARGIN_L - 6}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="#333">{v:,}</text>'
        )
    # Adjust y_at to use rounded max.
    def y_at_r(v: float) -> float:
        return MARGIN_T + plot_h - plot_h * v / y_max_r

    # Stack polygons.
    stack_bottom = [0.0] * len(dates)
    for group, cat, color in stack_categories:
        top = list(stack_bottom)
        for i, d in enumerate(dates):
            top[i] = stack_bottom[i] + counts.get((d, cat), 0)
        # Build polygon points: forward along top, back along bottom.
        pts_top = [(x_at(i), y_at_r(top[i])) for i in range(len(dates))]
        pts_bot = [(x_at(i), y_at_r(stack_bottom[i])) for i in range(len(dates))]
        pts = pts_top + list(reversed(pts_bot))
        d_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        total = sum(counts.get((d, cat), 0) for d in dates)
        parts.append(
            f'<polygon points="{d_attr}" fill="{color}" stroke="#fff" '
            f'stroke-width="0.3"><title>{escape(cat)} '
            f'({escape(group)}): {total:,} occurrences</title></polygon>'
        )
        stack_bottom = top

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

    # X-axis labels every ~3 days.
    step = max(1, len(dates) // 20)
    y_axis = MARGIN_T + plot_h
    for i, d in enumerate(dates):
        if i % step != 0 and i != len(dates) - 1:
            continue
        x = x_at(i)
        parts.append(
            f'<text x="{x:.1f}" y="{y_axis + 14}" text-anchor="end" '
            f'fill="#333" transform="rotate(-60 {x:.1f} {y_axis + 14})">'
            f'{d[5:]}</text>'
        )

    # Legend by group.
    lx = MARGIN_L + plot_w + 20
    ly = MARGIN_T
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'categories (stack order top → bottom)</text>'
    )
    ly += 14
    # Group by group_name preserving order.
    by_group: dict[str, list[tuple[str, str]]] = defaultdict(list)
    order: list[str] = []
    for group, cat, color in stack_categories:
        if group not in by_group:
            order.append(group)
        by_group[group].append((cat, color))
    # Reverse stack order in legend so top-of-stack shows first (matches image).
    for group in order:
        entries = list(reversed(by_group[group]))  # top of stack first
        group_total = sum(sum(counts.get((d, c), 0) for d in dates)
                          for (c, _) in entries)
        ly += 8
        parts.append(
            f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
            f'{escape(group)}<tspan fill="#666" font-weight="400">'
            f'  · {group_total:,}</tspan></text>'
        )
        ly += 6
        for cat, color in entries:
            n = sum(counts.get((d, cat), 0) for d in dates)
            parts.append(
                f'<rect x="{lx}" y="{ly}" width="14" height="12" '
                f'fill="{color}"/>'
            )
            parts.append(
                f'<text x="{lx + 20}" y="{ly + 10}" fill="#111" '
                f'font-size="11">{escape(cat)}'
                f' <tspan fill="#666">· {n:,}</tspan></text>'
            )
            ly += 15
        ly += 2

    parts.append("</svg>")
    (OUT_DIR / "urls_stacked_area.svg").write_text("\n".join(parts))
    print(f"wrote {OUT_DIR / 'urls_by_date.tsv'} ({len(counts)} rows)",
          file=sys.stderr)
    print(f"wrote {OUT_DIR / 'urls_stacked_area.svg'}", file=sys.stderr)


if __name__ == "__main__":
    main()
