#!/usr/bin/env python3
"""Render a stacked hourly bar chart from an hourly TSV.

  outputs/hourly_stacked_by_wiki_<start>_<end>.svg

x = UTC hour, height = requests, stack = wiki.
Stack order: smallest total at the bottom, largest at the top.
Pure stdlib.
"""
from __future__ import annotations
import argparse
import colorsys
from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape
import sys

OUT_DIR = Path(__file__).resolve().parent / "outputs"


def hsl_hex(h_deg: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h_deg / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def wiki_color(i: int, n: int) -> str:
    hue = (i * 360.0 / max(1, n)) % 360
    return hsl_hex(hue, 0.60, 0.48)


def load(path: Path) -> tuple[dict[tuple[str, str], int], dict[str, int]]:
    cells: dict[tuple[str, str], int] = {}
    wiki_total: dict[str, int] = defaultdict(int)
    with path.open() as f:
        next(f)
        for line in f:
            h, wiki, n = line.rstrip("\n").split("\t")
            cells[(h, wiki)] = int(n)
            wiki_total[wiki] += int(n)
    return cells, wiki_total


def hour_range(start_iso: str, end_iso: str) -> list[str]:
    a = datetime.strptime(start_iso, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    b = datetime.strptime(end_iso, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    b = b + timedelta(hours=23)
    out, cur = [], a
    while cur <= b:
        out.append(cur.strftime("%Y-%m-%d %H"))
        cur += timedelta(hours=1)
    return out


def nice_y_max(v: int) -> int:
    if v <= 0:
        return 1
    for step in [1, 2, 5, 10, 20, 50, 100, 200, 500,
                 1_000, 2_000, 5_000, 10_000,
                 20_000, 50_000, 100_000, 200_000, 500_000, 1_000_000]:
        for mult in range(1, 11):
            if step * mult >= v:
                return step * mult
    return v


def y_ticks(y_max: int, n: int = 5) -> list[int]:
    return [int(round(y_max * i / n)) for i in range(n + 1)]


def render(tsv_path: Path, start_iso: str, end_iso: str) -> Path:
    cells, wiki_total = load(tsv_path)
    hours = hour_range(start_iso, end_iso)

    # Colours: assign in a stable order (large → small) so the biggest wikis
    # always get the same hue across renders and won't drift when the window
    # changes their totals.
    wikis_by_size_desc = [w for w, _ in sorted(wiki_total.items(),
                                               key=lambda kv: (-kv[1], kv[0]))]
    colors = OrderedDict()
    for i, w in enumerate(wikis_by_size_desc):
        colors[w] = wiki_color(i, len(wikis_by_size_desc))

    # Stack order: smallest at the bottom (drawn first), largest on top.
    stack_wikis = [w for w in reversed(wikis_by_size_desc) if wiki_total[w] > 0]

    hour_total: dict[str, int] = defaultdict(int)
    for (h, w), n in cells.items():
        hour_total[h] += n
    y_max = nice_y_max(max(hour_total.values()) if hour_total else 1)

    W, H = 1600, 780
    MARGIN_L, MARGIN_R = 90, 300
    MARGIN_T, MARGIN_B = 70, 120
    plot_w = W - MARGIN_L - MARGIN_R
    plot_h = H - MARGIN_T - MARGIN_B
    bar_w = plot_w / len(hours)
    x0, y0 = MARGIN_L, MARGIN_T + plot_h

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="12">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
    ]
    total = sum(hour_total.values())
    parts.append(
        f'<text x="{MARGIN_L + plot_w/2:.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">Wiki access activity by hour, '
        f'stacked by wiki</text>'
    )
    parts.append(
        f'<text x="{MARGIN_L + plot_w/2:.0f}" y="46" text-anchor="middle" '
        f'fill="#555">{total:,} requests · '
        f'UTC {start_iso} 00:00 → {end_iso} 23:59 · '
        f'{len(hours)} hourly bars · smallest wiki at bottom, largest on top</text>'
    )

    for tick in y_ticks(y_max):
        y = y0 - int(round(plot_h * tick / y_max))
        parts.append(
            f'<line x1="{x0}" y1="{y}" x2="{x0 + plot_w}" y2="{y}" '
            f'stroke="#eee" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x0 - 8}" y="{y + 4}" text-anchor="end" fill="#333">'
            f'{tick:,}</text>'
        )
    parts.append(
        f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0 - plot_h}" '
        f'stroke="#333" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{x0}" y1="{y0}" x2="{x0 + plot_w}" y2="{y0}" '
        f'stroke="#333" stroke-width="1"/>'
    )

    # Vertical day separators.
    for i, h in enumerate(hours):
        if h.endswith(" 00") and i > 0:
            x = x0 + i * bar_w
            parts.append(
                f'<line x1="{x:.1f}" y1="{y0 - plot_h}" x2="{x:.1f}" y2="{y0}" '
                f'stroke="#cfcfcf" stroke-width="1" stroke-dasharray="3 3"/>'
            )

    # Stacked bars: smallest wiki drawn first (at the bottom).
    for i, h in enumerate(hours):
        cursor_y = y0
        for w in stack_wikis:
            n = cells.get((h, w), 0)
            if n <= 0:
                continue
            seg_h = plot_h * n / y_max
            x = x0 + i * bar_w
            parts.append(
                f'<rect x="{x:.2f}" y="{cursor_y - seg_h:.2f}" '
                f'width="{max(0.4, bar_w - 0.4):.2f}" height="{seg_h:.2f}" '
                f'fill="{colors[w]}" stroke="none">'
                f'<title>{h}:00 UTC  {w}: {n:,}</title></rect>'
            )
            cursor_y -= seg_h

    # X labels: one per day at hour 00, plus a light hour tick every 6h.
    for i, h in enumerate(hours):
        hh = h[-2:]
        x = x0 + i * bar_w + bar_w / 2
        if hh == "00":
            parts.append(
                f'<text x="{x:.1f}" y="{y0 + 32}" text-anchor="middle" '
                f'fill="#111" font-weight="600">{h[:10]}</text>'
            )
            parts.append(
                f'<text x="{x:.1f}" y="{y0 + 16}" text-anchor="middle" '
                f'fill="#666">00</text>'
            )
        elif hh in ("06", "12", "18"):
            parts.append(
                f'<text x="{x:.1f}" y="{y0 + 16}" text-anchor="middle" '
                f'fill="#666">{hh}</text>'
            )
    parts.append(
        f'<text x="{MARGIN_L - 66}" y="{MARGIN_T + plot_h/2:.0f}" '
        f'transform="rotate(-90 {MARGIN_L - 66} {MARGIN_T + plot_h/2:.0f})" '
        f'text-anchor="middle" fill="#333">requests / hour</text>'
    )

    # Legend: listed top-of-stack first (i.e. largest wiki first) so the
    # visual reading order top→bottom in the chart matches the legend.
    legend_order = list(reversed(stack_wikis)) + [
        w for w in wikis_by_size_desc if wiki_total[w] == 0
    ]
    lx = W - MARGIN_R + 20
    ly = MARGIN_T + 4
    parts.append(f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">wiki</text>')
    parts.append(
        f'<text x="{lx + 190}" y="{ly}" font-weight="600" fill="#111" '
        f'text-anchor="end">requests</text>'
    )
    ly += 6
    for w in legend_order:
        ly += 18
        swatch = colors[w] if wiki_total[w] > 0 else "#dcdcdc"
        parts.append(
            f'<rect x="{lx}" y="{ly - 10}" width="14" height="12" '
            f'fill="{swatch}" stroke="#888" stroke-width="0.5"/>'
        )
        label = escape(w) + ("" if wiki_total[w] > 0 else "  (no log data)")
        parts.append(
            f'<text x="{lx + 20}" y="{ly}" fill="#111">{label}</text>'
        )
        parts.append(
            f'<text x="{lx + 190}" y="{ly}" text-anchor="end" fill="#333">'
            f'{wiki_total[w]:,}</text>'
        )

    parts.append("</svg>")
    out = OUT_DIR / f"hourly_stacked_by_wiki_{start_iso}_{end_iso}.svg"
    out.write_text("\n".join(parts))
    print(f"wrote {out}", file=sys.stderr)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-06-13")
    ap.add_argument("--end", default="2026-06-20")
    args = ap.parse_args()
    tsv = OUT_DIR / f"hourly_by_wiki_{args.start}_{args.end}.tsv"
    if not tsv.exists():
        print(f"missing {tsv}; run build_hourly.py first", file=sys.stderr)
        sys.exit(1)
    render(tsv, args.start, args.end)


if __name__ == "__main__":
    main()
