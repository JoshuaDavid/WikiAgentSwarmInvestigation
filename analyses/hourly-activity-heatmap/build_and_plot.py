#!/usr/bin/env python3
"""Read agent-logs/prowiki/revisions.jsonl. For every revision, bucket by
(UTC date, hour of day). Write:

  outputs/hourly_counts.tsv   date, hour, revisions
  outputs/hourly_heatmap.svg  date (x) × hour-of-day (y) heatmap
                              cell shade = log-scaled revision count

Pure stdlib. Rerun with:
    python3 analyses/hourly-activity-heatmap/build_and_plot.py
"""
from __future__ import annotations
import colorsys
import json
import math
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
REV_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"
OUT_DIR = HERE / "outputs"


def collect() -> dict[tuple[str, int], int]:
    counts: dict[tuple[str, int], int] = defaultdict(int)
    with REV_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            t = r.get("time") or ""
            if len(t) < 13 or t[10] != "T":
                continue
            d = t[:10]
            try:
                h = int(t[11:13])
            except ValueError:
                continue
            counts[(d, h)] += 1
    return counts


def date_range(start: str, end: str) -> list[str]:
    y1, m1, d1 = (int(x) for x in start.split("-"))
    y2, m2, d2 = (int(x) for x in end.split("-"))
    a, b = date(y1, m1, d1), date(y2, m2, d2)
    out, cur = [], a
    while cur <= b:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def hsl_hex(h_deg: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h_deg / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def cell_color(count: int, max_count: int) -> str:
    """Perceptually-monotone log ramp: white (0) → deep navy (max)."""
    if count <= 0:
        return "#f7f7f7"
    frac = math.log1p(count) / math.log1p(max_count)
    # Ramp from very-light-blue to deep navy.
    hue = 215
    sat = 0.30 + 0.55 * frac
    light = 0.94 - 0.72 * frac
    return hsl_hex(hue, sat, light)


def write_tsv(counts: dict[tuple[str, int], int]) -> None:
    with (OUT_DIR / "hourly_counts.tsv").open("w") as f:
        f.write("date\thour\trevisions\n")
        for (d, h), n in sorted(counts.items()):
            f.write(f"{d}\t{h:02d}\t{n}\n")


def render_svg(counts: dict[tuple[str, int], int]) -> None:
    if not counts:
        raise RuntimeError("no revisions found")
    dates_present = sorted({d for (d, _) in counts})
    all_dates = date_range(dates_present[0], dates_present[-1])
    max_count = max(counts.values())

    W, H = 1400, 640
    MARGIN_L, MARGIN_R = 90, 220
    MARGIN_T, MARGIN_B = 70, 110
    plot_w = W - MARGIN_L - MARGIN_R
    plot_h = H - MARGIN_T - MARGIN_B
    cell_w = plot_w / len(all_dates)
    cell_h = plot_h / 24

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="12">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">Prowiki revisions by '
        f'UTC hour × date</text>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="46" text-anchor="middle" '
        f'fill="#555">One cell = one hour bucket. Shade = log(revisions). '
        f'Peak cell: {max_count:,} revs</text>',
    ]

    # Cells.
    for i, d in enumerate(all_dates):
        for h in range(24):
            n = counts.get((d, h), 0)
            x = MARGIN_L + i * cell_w
            y = MARGIN_T + h * cell_h
            fill = cell_color(n, max_count)
            title = f"{d} {h:02d}:00 UTC — {n:,} revs" if n else \
                    f"{d} {h:02d}:00 UTC — 0"
            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_w:.2f}" '
                f'height="{cell_h:.2f}" fill="{fill}" stroke="#fff" '
                f'stroke-width="0.3"><title>{title}</title></rect>'
            )

    # Y-axis: hour labels every 3 hours.
    for h in range(0, 24, 3):
        y = MARGIN_T + h * cell_h + cell_h / 2 + 4
        parts.append(
            f'<text x="{MARGIN_L - 8}" y="{y:.1f}" text-anchor="end" '
            f'fill="#333">{h:02d}:00</text>'
        )
    parts.append(
        f'<text x="{MARGIN_L - 60}" y="{MARGIN_T + plot_h/2:.0f}" '
        f'transform="rotate(-90 {MARGIN_L - 60} {MARGIN_T + plot_h/2:.0f})" '
        f'text-anchor="middle" fill="#333">hour of day (UTC)</text>'
    )

    # X-axis: date labels every ~3 days.
    step = max(1, len(all_dates) // 20)
    for i, d in enumerate(all_dates):
        if i % step != 0 and i != len(all_dates) - 1:
            continue
        x = MARGIN_L + i * cell_w + cell_w / 2
        parts.append(
            f'<text x="{x:.1f}" y="{MARGIN_T + plot_h + 14}" '
            f'text-anchor="end" fill="#333" transform="rotate(-60 '
            f'{x:.1f} {MARGIN_T + plot_h + 14})">{d[5:]}</text>'
        )

    # Legend: horizontal log-ramp with tick labels at 1, 10, 100, 1000, max.
    lx = W - MARGIN_R + 20
    ly = MARGIN_T
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'revisions per hour</text>'
    )
    ly += 12
    ramp_w = 180
    ramp_h = 14
    steps = 100
    for i in range(steps):
        frac = i / (steps - 1)
        n = int(round(math.expm1(frac * math.log1p(max_count))))
        parts.append(
            f'<rect x="{lx + i * ramp_w / steps:.2f}" y="{ly}" '
            f'width="{ramp_w / steps + 0.5:.2f}" height="{ramp_h}" '
            f'fill="{cell_color(max(1, n), max_count)}" stroke="none"/>'
        )
    # Ramp axis.
    parts.append(
        f'<rect x="{lx}" y="{ly}" width="{ramp_w}" height="{ramp_h}" '
        f'fill="none" stroke="#333" stroke-width="0.5"/>'
    )
    ticks = [1, 10, 100, 1000, max_count]
    ticks = [t for t in ticks if t <= max_count]
    if ticks[-1] != max_count:
        ticks.append(max_count)
    for t in ticks:
        frac = math.log1p(t) / math.log1p(max_count)
        x = lx + frac * ramp_w
        parts.append(
            f'<line x1="{x:.1f}" y1="{ly + ramp_h}" x2="{x:.1f}" '
            f'y2="{ly + ramp_h + 3}" stroke="#333" stroke-width="0.5"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{ly + ramp_h + 14}" '
            f'text-anchor="middle" font-size="10" fill="#333">{t:,}</text>'
        )

    # Legend: total, non-empty cells, quiet-hour band.
    ly += ramp_h + 40
    total = sum(counts.values())
    n_cells = len(all_dates) * 24
    n_active = sum(1 for v in counts.values() if v > 0)
    hourly_totals = defaultdict(int)
    for (d, h), n in counts.items():
        hourly_totals[h] += n
    peak_hour = max(hourly_totals, key=hourly_totals.get)
    quiet_hour = min(hourly_totals, key=hourly_totals.get)
    parts.append(
        f'<text x="{lx}" y="{ly}" fill="#111" font-weight="600">totals</text>'
    )
    ly += 16
    for line in [
        f"{total:,} revisions",
        f"{n_active:,} of {n_cells:,} hour cells non-empty ({100*n_active/n_cells:.0f}%)",
        f"peak hour of day (UTC): {peak_hour:02d}:00  ({hourly_totals[peak_hour]:,})",
        f"quietest hour of day (UTC): {quiet_hour:02d}:00  ({hourly_totals[quiet_hour]:,})",
    ]:
        parts.append(f'<text x="{lx}" y="{ly}" fill="#333">{line}</text>')
        ly += 14

    parts.append("</svg>")
    (OUT_DIR / "hourly_heatmap.svg").write_text("\n".join(parts))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    counts = collect()
    write_tsv(counts)
    render_svg(counts)
    print(f"wrote {OUT_DIR / 'hourly_counts.tsv'} ({len(counts)} cells)",
          file=sys.stderr)
    print(f"wrote {OUT_DIR / 'hourly_heatmap.svg'}", file=sys.stderr)


if __name__ == "__main__":
    main()
