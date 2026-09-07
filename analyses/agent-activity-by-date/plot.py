#!/usr/bin/env python3
"""Render two SVG bar charts from outputs/daily_totals.tsv and
outputs/daily_by_variant.tsv:

  outputs/daily_totals.svg           plain bars, one per calendar day
  outputs/daily_stacked_by_task.svg  stacked bars, grouped by task family
                                     and coloured by variant within family

Pure stdlib. Rerun with:
    python3 analyses/agent-activity-by-date/plot.py
"""
from __future__ import annotations
import colorsys
import sys
from collections import defaultdict, OrderedDict
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "outputs"

TOTALS_TSV = OUT_DIR / "daily_totals.tsv"
VARIANT_TSV = OUT_DIR / "daily_by_variant.tsv"
TOTALS_SVG = OUT_DIR / "daily_totals.svg"
STACKED_SVG = OUT_DIR / "daily_stacked_by_task.svg"

# Very-different family hues (degrees on the colour wheel).
FAMILY_HUE = {
    "archive-item-research-bench": 210,   # blue
    "fast-follow-question-bench":   15,   # red-orange
    "sec-regcf-ma-cache":          140,   # green
    "vocab-puzzle-refs":           285,   # violet
    "unclassified":                  0,   # grey (saturation is set to 0 below)
}
# Draw order (bottom → top). Unclassified on top so it does not visually bury
# the task-attributed strata.
FAMILY_STACK_ORDER = [
    "archive-item-research-bench",
    "fast-follow-question-bench",
    "sec-regcf-ma-cache",
    "vocab-puzzle-refs",
    "unclassified",
]


def hsl_to_hex(h_deg: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h_deg / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def family_variant_color(family: str, variant_idx: int, variant_n: int) -> str:
    """A shade within the family palette.

    Same base hue for every variant of a task family. A small hue rotation
    (±8°) and a lightness sweep from 0.30 to 0.72 makes the variants
    distinguishable without breaking the family's visual identity.
    """
    hue = FAMILY_HUE[family]
    if family == "unclassified":
        # Grey ramp only.
        l = 0.55 if variant_n <= 1 else 0.30 + 0.42 * (variant_idx / max(1, variant_n - 1))
        return hsl_to_hex(0, 0.0, l)
    if variant_n <= 1:
        return hsl_to_hex(hue, 0.65, 0.48)
    frac = variant_idx / (variant_n - 1)
    hue_local = hue + (frac - 0.5) * 16.0
    lightness = 0.30 + frac * 0.42
    saturation = 0.55 + (1 - abs(frac - 0.5) * 2) * 0.20
    return hsl_to_hex(hue_local, saturation, lightness)


# --- I/O ---------------------------------------------------------------------

def load_totals() -> dict[str, int]:
    m: dict[str, int] = {}
    with TOTALS_TSV.open() as f:
        next(f)
        for line in f:
            d, n = line.rstrip("\n").split("\t")
            m[d] = int(n)
    return m


def load_by_variant() -> dict[tuple[str, str, str], int]:
    m: dict[tuple[str, str, str], int] = {}
    with VARIANT_TSV.open() as f:
        next(f)
        for line in f:
            d, task, variant, n = line.rstrip("\n").split("\t")
            m[(task, variant, d)] = int(n)
    return m


# --- geometry ----------------------------------------------------------------

def date_range(start_iso: str, end_iso: str) -> list[str]:
    y1, m1, d1 = (int(x) for x in start_iso.split("-"))
    y2, m2, d2 = (int(x) for x in end_iso.split("-"))
    a, b = date(y1, m1, d1), date(y2, m2, d2)
    out, cur = [], a
    while cur <= b:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def nice_y_max(v_max: int) -> int:
    if v_max <= 0:
        return 1
    for step in [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]:
        for mult in range(1, 11):
            if step * mult >= v_max:
                return step * mult
    return v_max


def y_ticks(y_max: int, n: int = 5) -> list[int]:
    return [int(round(y_max * i / n)) for i in range(n + 1)]


# --- SVG helpers -------------------------------------------------------------

def svg_open(w: int, h: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="12">',
        f'<rect x="0" y="0" width="{w}" height="{h}" fill="white"/>',
    ]


def svg_close() -> str:
    return "</svg>"


def axis_lines(x0: int, y0: int, w: int, h: int) -> list[str]:
    return [
        f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0 - h}" '
        f'stroke="#333" stroke-width="1"/>',
        f'<line x1="{x0}" y1="{y0}" x2="{x0 + w}" y2="{y0}" '
        f'stroke="#333" stroke-width="1"/>',
    ]


def y_grid_and_labels(x0: int, y0: int, w: int, h: int, y_max: int) -> list[str]:
    out = []
    for tick in y_ticks(y_max):
        y = y0 - int(round(h * tick / y_max))
        out.append(
            f'<line x1="{x0}" y1="{y}" x2="{x0 + w}" y2="{y}" '
            f'stroke="#eee" stroke-width="1"/>'
        )
        out.append(
            f'<text x="{x0 - 6}" y="{y + 4}" text-anchor="end" '
            f'fill="#333">{tick:,}</text>'
        )
    return out


def x_date_labels(x0: int, y0: int, dates: list[str], bar_w: int) -> list[str]:
    out = []
    for i, d in enumerate(dates):
        x = x0 + i * bar_w + bar_w / 2
        label = d[5:]  # MM-DD
        out.append(
            f'<text x="{x:.1f}" y="{y0 + 14}" text-anchor="end" fill="#333" '
            f'transform="rotate(-60 {x:.1f} {y0 + 14})">{label}</text>'
        )
    return out


# --- Chart 1: totals ---------------------------------------------------------

def render_totals(totals: dict[str, int]) -> None:
    dates = date_range(min(totals), max(totals))
    W, H = 1200, 620
    MARGIN_L, MARGIN_R = 80, 40
    MARGIN_T, MARGIN_B = 60, 90
    plot_w = W - MARGIN_L - MARGIN_R
    plot_h = H - MARGIN_T - MARGIN_B
    bar_w = plot_w / len(dates)
    y_max = nice_y_max(max(totals.values()))
    x0, y0 = MARGIN_L, MARGIN_T + plot_h

    total_revs = sum(totals.values())
    parts = svg_open(W, H)
    parts.append(
        f'<text x="{W/2:.0f}" y="24" text-anchor="middle" font-size="18" '
        f'font-weight="600" fill="#111">Agent activity by date '
        f'(prowiki revisions)</text>'
    )
    parts.append(
        f'<text x="{W/2:.0f}" y="44" text-anchor="middle" fill="#555">'
        f'{total_revs:,} revisions across {len(dates)} calendar days '
        f'({dates[0]} → {dates[-1]}); peak {max(totals.values()):,} on '
        f'{max(totals, key=totals.get)}</text>'
    )
    parts += y_grid_and_labels(x0, y0, plot_w, plot_h, y_max)
    parts += axis_lines(x0, y0, plot_w, plot_h)

    for i, d in enumerate(dates):
        n = totals.get(d, 0)
        if n <= 0:
            continue
        bar_h = plot_h * n / y_max
        x = x0 + i * bar_w
        parts.append(
            f'<rect x="{x + 1:.1f}" y="{y0 - bar_h:.1f}" '
            f'width="{bar_w - 2:.1f}" height="{bar_h:.1f}" '
            f'fill="#2a6db0"><title>{d}: {n:,} revs</title></rect>'
        )

    parts += x_date_labels(x0, y0, dates, bar_w)
    parts.append(
        f'<text x="{MARGIN_L - 60}" y="{MARGIN_T + plot_h/2:.0f}" '
        f'transform="rotate(-90 {MARGIN_L - 60} {MARGIN_T + plot_h/2:.0f})" '
        f'text-anchor="middle" fill="#333">revisions</text>'
    )
    parts.append(svg_close())
    TOTALS_SVG.write_text("\n".join(parts))
    print(f"wrote {TOTALS_SVG}", file=sys.stderr)


# --- Chart 2: stacked --------------------------------------------------------

def render_stacked(by_variant: dict[tuple[str, str, str], int]) -> None:
    # Collect: dates, family→ordered variants (by total desc within family),
    # per-cell counts.
    dates_set: set[str] = set()
    family_variant_total: dict[tuple[str, str], int] = defaultdict(int)
    cells: dict[tuple[str, str, str], int] = defaultdict(int)
    for (task, variant, d), n in by_variant.items():
        cells[(task, variant, d)] += n
        family_variant_total[(task, variant)] += n
        dates_set.add(d)
    dates = date_range(min(dates_set), max(dates_set))

    # Order variants within each family by descending total → deterministic
    # colour assignment and stack order.
    family_variants: "OrderedDict[str, list[str]]" = OrderedDict()
    for fam in FAMILY_STACK_ORDER:
        variants = sorted(
            [v for (f, v) in family_variant_total if f == fam],
            key=lambda v: (-family_variant_total[(fam, v)], v),
        )
        if variants:
            family_variants[fam] = variants

    # Colour lookup.
    color: dict[tuple[str, str], str] = {}
    for fam, variants in family_variants.items():
        for i, v in enumerate(variants):
            color[(fam, v)] = family_variant_color(fam, i, len(variants))

    # Layout.
    W, H = 1400, 780
    MARGIN_L, MARGIN_R = 80, 340   # extra right margin for the legend
    MARGIN_T, MARGIN_B = 70, 110
    plot_w = W - MARGIN_L - MARGIN_R
    plot_h = H - MARGIN_T - MARGIN_B
    bar_w = plot_w / len(dates)
    x0, y0 = MARGIN_L, MARGIN_T + plot_h

    # Compute per-date stack totals (== raw daily total, up to a small
    # overcount from archive multi-matches; see README).
    day_total: dict[str, int] = defaultdict(int)
    for (fam, var, d), n in cells.items():
        day_total[d] += n
    y_max = nice_y_max(max(day_total.values()))

    parts = svg_open(W, H)
    parts.append(
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">Agent activity by date, '
        f'stacked by task family and variant</text>'
    )
    parts.append(
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="46" text-anchor="middle" '
        f'fill="#555">Hue = task family (very different). Shade = variant '
        f'within family. Grey = unclassified.</text>'
    )
    parts += y_grid_and_labels(x0, y0, plot_w, plot_h, y_max)
    parts += axis_lines(x0, y0, plot_w, plot_h)

    for i, d in enumerate(dates):
        cursor_y = y0
        for fam, variants in family_variants.items():
            for v in variants:
                n = cells.get((fam, v, d), 0)
                if n <= 0:
                    continue
                seg_h = plot_h * n / y_max
                x = x0 + i * bar_w
                parts.append(
                    f'<rect x="{x + 0.5:.1f}" y="{cursor_y - seg_h:.1f}" '
                    f'width="{bar_w - 1:.1f}" height="{seg_h:.1f}" '
                    f'fill="{color[(fam, v)]}" stroke="none">'
                    f'<title>{d}  {fam} / {escape(v)}: {n:,}</title></rect>'
                )
                cursor_y -= seg_h

    parts += x_date_labels(x0, y0, dates, bar_w)
    parts.append(
        f'<text x="{MARGIN_L - 60}" y="{MARGIN_T + plot_h/2:.0f}" '
        f'transform="rotate(-90 {MARGIN_L - 60} {MARGIN_T + plot_h/2:.0f})" '
        f'text-anchor="middle" fill="#333">revisions</text>'
    )

    # Legend.
    lx = W - MARGIN_R + 20
    ly = MARGIN_T
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">Legend</text>'
    )
    ly += 14
    for fam, variants in family_variants.items():
        fam_total = sum(family_variant_total[(fam, v)] for v in variants)
        ly += 10
        parts.append(
            f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">{fam}'
            f' <tspan fill="#666" font-weight="400">'
            f'· {fam_total:,} revs · {len(variants)} variant'
            f'{"" if len(variants) == 1 else "s"}</tspan></text>'
        )
        ly += 6
        # Swatch strip: one cell per variant.
        strip_w = 300
        cell_w = strip_w / max(1, len(variants))
        for i, v in enumerate(variants):
            parts.append(
                f'<rect x="{lx + i * cell_w:.1f}" y="{ly}" '
                f'width="{cell_w:.1f}" height="12" fill="{color[(fam, v)]}">'
                f'<title>{escape(v)}: '
                f'{family_variant_total[(fam, v)]:,}</title></rect>'
            )
        ly += 14
        # Top-3 variant names for orientation.
        top = variants[:3]
        parts.append(
            f'<text x="{lx}" y="{ly + 10}" fill="#333" font-size="11">'
            f'top: {escape(", ".join(top))}'
            f'{"" if len(variants) <= 3 else f" (+{len(variants) - 3} more)"}'
            f'</text>'
        )
        ly += 20

    parts.append(svg_close())
    STACKED_SVG.write_text("\n".join(parts))
    print(f"wrote {STACKED_SVG}", file=sys.stderr)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render_totals(load_totals())
    render_stacked(load_by_variant())


if __name__ == "__main__":
    main()
