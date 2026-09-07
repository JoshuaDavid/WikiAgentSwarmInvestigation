#!/usr/bin/env python3
"""Stacked bar chart of paste-site revisions per UTC day, one segment per
paste-hosting site.

Reads:
  agent-logs/pastes/revisions.jsonl

Writes:
  outputs/pastes_daily_by_site.tsv  date, site, revisions
  outputs/pastes_stacked_by_site.svg

Pure stdlib. Rerun with:
    python3 analyses/pastes-by-date-and-site/build_and_plot.py
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
REV_PATH = REPO_ROOT / "agent-logs" / "pastes" / "revisions.jsonl"
OUT_DIR = HERE / "outputs"

# X-axis window: the pastes file has scattered pre-2026 rows (37 of 458 revs
# spread across 2020-2025). Bucket those into a single "(pre-2026)" note and
# plot the 2026 range in full daily resolution.
X_START = "2026-03-01"


def hsl_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def site_color(idx: int, n: int) -> str:
    """Deterministic distinct-hue palette. Even hue spacing over the wheel."""
    hue = (idx * 360.0 / n + 15) % 360
    # Alternating saturation/lightness so adjacent sites contrast.
    if idx % 2 == 0:
        return hsl_hex(hue, 0.60, 0.45)
    return hsl_hex(hue, 0.70, 0.58)


def date_range(start: str, end: str) -> list[str]:
    y1, m1, d1 = (int(x) for x in start.split("-"))
    y2, m2, d2 = (int(x) for x in end.split("-"))
    a, b = date(y1, m1, d1), date(y2, m2, d2)
    out, cur = [], a
    while cur <= b:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def collect():
    per_day: dict[tuple[str, str], int] = defaultdict(int)
    site_totals: dict[str, int] = defaultdict(int)
    pre_window: dict[str, int] = defaultdict(int)   # site -> count pre-X_START
    with REV_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            t = r.get("time") or ""
            if len(t) < 10:
                continue
            d = t[:10]
            site = r.get("name", "").split("/", 1)[0] or "(unknown)"
            site_totals[site] += 1
            if d < X_START:
                pre_window[site] += 1
                continue
            per_day[(d, site)] += 1
    return per_day, site_totals, pre_window


def nice_ymax(v: int) -> int:
    if v <= 0:
        return 1
    for step in [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]:
        for mult in range(1, 11):
            if step * mult >= v:
                return step * mult
    return v


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    per_day, site_totals, pre_window = collect()

    # Site stack order: largest total at bottom of stack.
    sites = sorted(site_totals, key=lambda s: (-site_totals[s], s))
    color = {s: site_color(i, len(sites)) for i, s in enumerate(sites)}

    # X-axis dates: X_START -> max date present.
    dates_present = sorted({d for (d, _) in per_day})
    end = dates_present[-1] if dates_present else X_START
    dates = date_range(X_START, end)

    with (OUT_DIR / "pastes_daily_by_site.tsv").open("w") as f:
        f.write("date\tsite\trevisions\n")
        for (d, s), n in sorted(per_day.items()):
            f.write(f"{d}\t{s}\t{n}\n")

    # Per-day totals for y-scale.
    day_total = defaultdict(int)
    for (d, s), n in per_day.items():
        day_total[d] += n
    y_max = nice_ymax(max(day_total.values()) if day_total else 1)

    W, H = 1500, 640
    MARGIN_L, MARGIN_R = 80, 340
    MARGIN_T, MARGIN_B = 70, 100
    plot_w = W - MARGIN_L - MARGIN_R
    plot_h = H - MARGIN_T - MARGIN_B
    bar_w = plot_w / len(dates)
    x0, y0 = MARGIN_L, MARGIN_T + plot_h

    total_all = sum(site_totals.values())
    total_in_window = sum(per_day.values())
    total_pre = sum(pre_window.values())

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="12">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">Paste-site revisions '
        f'per UTC day, stacked by site</text>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="46" text-anchor="middle" '
        f'fill="#555">{total_in_window:,} revs from {X_START} → {end} '
        f'({total_pre} additional revs 2020-01 → 2026-02 not shown). '
        f'{len(sites)} sites.</text>',
    ]

    # Y grid + labels.
    for k in range(6):
        v = int(round(y_max * k / 5))
        y = y0 - plot_h * v / y_max
        parts.append(
            f'<line x1="{x0}" y1="{y:.1f}" x2="{x0 + plot_w}" y2="{y:.1f}" '
            f'stroke="#eee" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x0 - 6}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="#333">{v:,}</text>'
        )
    parts.append(
        f'<line x1="{x0}" y1="{MARGIN_T}" x2="{x0}" y2="{y0}" '
        f'stroke="#333" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{x0}" y1="{y0}" x2="{x0 + plot_w}" y2="{y0}" '
        f'stroke="#333" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{MARGIN_L - 60}" y="{MARGIN_T + plot_h/2:.0f}" '
        f'transform="rotate(-90 {MARGIN_L - 60} {MARGIN_T + plot_h/2:.0f})" '
        f'text-anchor="middle" fill="#333">revisions</text>'
    )

    # Bars.
    for i, d in enumerate(dates):
        cursor = y0
        for s in sites:   # bottom-up in stack order
            n = per_day.get((d, s), 0)
            if n <= 0:
                continue
            seg_h = plot_h * n / y_max
            x = x0 + i * bar_w
            parts.append(
                f'<rect x="{x + 0.3:.1f}" y="{cursor - seg_h:.1f}" '
                f'width="{max(0.5, bar_w - 0.6):.1f}" height="{seg_h:.1f}" '
                f'fill="{color[s]}" stroke="none">'
                f'<title>{d} · {escape(s)}: {n:,}</title></rect>'
            )
            cursor -= seg_h

    # X labels every ~7 days.
    step = max(1, len(dates) // 25)
    for i, d in enumerate(dates):
        if i % step != 0 and i != len(dates) - 1:
            continue
        x = x0 + i * bar_w + bar_w / 2
        parts.append(
            f'<text x="{x:.1f}" y="{y0 + 14}" text-anchor="end" fill="#333" '
            f'transform="rotate(-60 {x:.1f} {y0 + 14})">{d[5:]}</text>'
        )

    # Legend.
    lx = MARGIN_L + plot_w + 20
    ly = MARGIN_T
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'sites (stack order top → bottom)</text>'
    )
    ly += 14
    # Reverse so top-of-stack shows first in legend.
    for s in reversed(sites):
        n = site_totals[s]
        n_in = n - pre_window.get(s, 0)
        pre = pre_window.get(s, 0)
        pre_note = f" · +{pre} pre-window" if pre else ""
        parts.append(
            f'<rect x="{lx}" y="{ly}" width="14" height="12" '
            f'fill="{color[s]}"/>'
        )
        parts.append(
            f'<text x="{lx + 20}" y="{ly + 10}" fill="#111" '
            f'font-size="11">{escape(s)} <tspan fill="#666">· {n_in:,} rev'
            f'{"" if n_in == 1 else "s"}{pre_note}</tspan></text>'
        )
        ly += 16

    ly += 8
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">notes</text>'
    )
    ly += 14
    peak_day = max(day_total, key=day_total.get) if day_total else "n/a"
    for line in [
        f"total in window: {total_in_window:,}",
        f"pre-window (excluded): {total_pre:,}",
        f"peak day: {peak_day}"
        f" ({day_total.get(peak_day, 0):,} revs)",
        f"corpus grand total: {total_all:,}",
    ]:
        parts.append(f'<text x="{lx}" y="{ly}" fill="#333">{line}</text>')
        ly += 14

    parts.append("</svg>")
    (OUT_DIR / "pastes_stacked_by_site.svg").write_text("\n".join(parts))
    print(f"wrote {OUT_DIR / 'pastes_daily_by_site.tsv'}", file=sys.stderr)
    print(f"wrote {OUT_DIR / 'pastes_stacked_by_site.svg'}", file=sys.stderr)


if __name__ == "__main__":
    main()
