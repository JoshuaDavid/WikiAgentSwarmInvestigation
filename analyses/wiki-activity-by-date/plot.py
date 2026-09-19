#!/usr/bin/env python3
"""Render a stacked bar chart from outputs/daily_by_wiki.tsv.

  outputs/daily_stacked_by_wiki.svg

x = calendar date (UTC), height = total requests, stack colour = wiki.
Pure stdlib.
"""
from __future__ import annotations
import colorsys
import sys
from collections import defaultdict, OrderedDict
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
TSV = HERE / "outputs" / "daily_by_wiki.tsv"
SVG = HERE / "outputs" / "daily_stacked_by_wiki.svg"


def hsl_hex(h_deg: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h_deg / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def wiki_color(i: int, n: int) -> str:
    # Evenly spaced hues, avoiding hue collisions on the standard 12 slots.
    hue = (i * 360.0 / max(1, n)) % 360
    return hsl_hex(hue, 0.60, 0.48)


def load() -> tuple[dict[tuple[str, str], int], dict[str, int]]:
    cells: dict[tuple[str, str], int] = {}
    wiki_total: dict[str, int] = defaultdict(int)
    with TSV.open() as f:
        next(f)
        for line in f:
            d, wiki, n = line.rstrip("\n").split("\t")
            cells[(d, wiki)] = int(n)
            wiki_total[wiki] += int(n)
    return cells, wiki_total


def date_range(a_iso: str, b_iso: str) -> list[str]:
    y1, m1, d1 = (int(x) for x in a_iso.split("-"))
    y2, m2, d2 = (int(x) for x in b_iso.split("-"))
    a, b = date(y1, m1, d1), date(y2, m2, d2)
    out, cur = [], a
    while cur <= b:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def nice_y_max(v: int) -> int:
    if v <= 0:
        return 1
    for step in [1, 2, 5, 10, 20, 50, 100, 200, 500,
                 1_000, 2_000, 5_000, 10_000,
                 20_000, 50_000, 100_000, 200_000, 500_000,
                 1_000_000, 2_000_000, 5_000_000]:
        for mult in range(1, 11):
            if step * mult >= v:
                return step * mult
    return v


def y_ticks(y_max: int, n: int = 5) -> list[int]:
    return [int(round(y_max * i / n)) for i in range(n + 1)]


def fmt_thousands(n: int) -> str:
    return f"{n:,}"


def render() -> None:
    cells, wiki_total = load()
    dates = date_range(min(d for d, _ in cells), max(d for d, _ in cells))
    # Draw order (bottom → top): largest wikis on the bottom so their strata
    # form a stable base and the smaller ones sit on top where the eye lands.
    wikis_ordered = [w for w, _ in sorted(wiki_total.items(), key=lambda kv: (-kv[1], kv[0]))]
    # Drop wikis with zero requests from the stack — they can't be seen anyway
    # — but keep them in the legend so the reader knows they were parsed.
    stack_wikis = [w for w in wikis_ordered if wiki_total[w] > 0]

    colors = OrderedDict()
    for i, w in enumerate(wikis_ordered):
        colors[w] = wiki_color(i, len(wikis_ordered))

    day_total: dict[str, int] = defaultdict(int)
    for (d, w), n in cells.items():
        day_total[d] += n
    y_max = nice_y_max(max(day_total.values()))

    # Layout.
    W, H = 1600, 780
    MARGIN_L, MARGIN_R = 90, 300
    MARGIN_T, MARGIN_B = 70, 110
    plot_w = W - MARGIN_L - MARGIN_R
    plot_h = H - MARGIN_T - MARGIN_B
    bar_w = plot_w / len(dates)
    x0, y0 = MARGIN_L, MARGIN_T + plot_h

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="12">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
    ]
    total = sum(day_total.values())
    parts.append(
        f'<text x="{MARGIN_L + plot_w/2:.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">Wiki access activity by date '
        f'(stacked by wiki)</text>'
    )
    parts.append(
        f'<text x="{MARGIN_L + plot_w/2:.0f}" y="46" text-anchor="middle" '
        f'fill="#555">{total:,} requests across {len(dates)} days '
        f'({dates[0]} → {dates[-1]}), {len(stack_wikis)} wikis with traffic'
        f'</text>'
    )

    # Y grid + ticks.
    for tick in y_ticks(y_max):
        y = y0 - int(round(plot_h * tick / y_max))
        parts.append(
            f'<line x1="{x0}" y1="{y}" x2="{x0 + plot_w}" y2="{y}" '
            f'stroke="#eee" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x0 - 8}" y="{y + 4}" text-anchor="end" fill="#333">'
            f'{fmt_thousands(tick)}</text>'
        )
    # Axes.
    parts.append(
        f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0 - plot_h}" '
        f'stroke="#333" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{x0}" y1="{y0}" x2="{x0 + plot_w}" y2="{y0}" '
        f'stroke="#333" stroke-width="1"/>'
    )

    # Stacked bars.
    for i, d in enumerate(dates):
        cursor_y = y0
        for w in stack_wikis:
            n = cells.get((d, w), 0)
            if n <= 0:
                continue
            seg_h = plot_h * n / y_max
            x = x0 + i * bar_w
            parts.append(
                f'<rect x="{x:.2f}" y="{cursor_y - seg_h:.2f}" '
                f'width="{max(0.4, bar_w - 0.4):.2f}" height="{seg_h:.2f}" '
                f'fill="{colors[w]}" stroke="none">'
                f'<title>{d}  {w}: {n:,}</title></rect>'
            )
            cursor_y -= seg_h

    # X labels: show every ~7th date to avoid overlap on 204 bars.
    step = max(1, len(dates) // 28)
    for i, d in enumerate(dates):
        if i % step != 0 and i != len(dates) - 1:
            continue
        x = x0 + i * bar_w + bar_w / 2
        parts.append(
            f'<text x="{x:.1f}" y="{y0 + 14}" text-anchor="end" fill="#333" '
            f'transform="rotate(-60 {x:.1f} {y0 + 14})">{d}</text>'
        )
    parts.append(
        f'<text x="{MARGIN_L - 66}" y="{MARGIN_T + plot_h/2:.0f}" '
        f'transform="rotate(-90 {MARGIN_L - 66} {MARGIN_T + plot_h/2:.0f})" '
        f'text-anchor="middle" fill="#333">requests</text>'
    )

    # Legend: draw order matches stack order (largest at top-left of stack).
    lx = W - MARGIN_R + 20
    ly = MARGIN_T + 4
    parts.append(f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">wiki</text>')
    parts.append(
        f'<text x="{lx + 170}" y="{ly}" font-weight="600" fill="#111" '
        f'text-anchor="end">requests</text>'
    )
    ly += 6
    for w in wikis_ordered:
        ly += 18
        swatch_fill = colors[w] if wiki_total[w] > 0 else "#dcdcdc"
        parts.append(
            f'<rect x="{lx}" y="{ly - 10}" width="14" height="12" '
            f'fill="{swatch_fill}" stroke="#888" stroke-width="0.5"/>'
        )
        label = escape(w) + ("" if wiki_total[w] > 0 else "  (no log data)")
        parts.append(
            f'<text x="{lx + 20}" y="{ly}" fill="#111">{label}</text>'
        )
        parts.append(
            f'<text x="{lx + 190}" y="{ly}" text-anchor="end" fill="#333">'
            f'{fmt_thousands(wiki_total[w])}</text>'
        )

    parts.append("</svg>")
    SVG.write_text("\n".join(parts))
    print(f"wrote {SVG}", file=sys.stderr)


if __name__ == "__main__":
    render()
