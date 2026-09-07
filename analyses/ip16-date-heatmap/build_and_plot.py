#!/usr/bin/env python3
"""Top-N source /16 subnets, one row each, plotted as a per-day activity
heatmap.

  rows = /16 subnets, ordered by total revisions descending
  cols = UTC calendar days across the export
  cell = navy log-shade of revisions on that (subnet, day)

Reads:
  agent-logs/prowiki/revisions.jsonl

Writes:
  outputs/ip16_daily.tsv        ip16, date, revisions
  outputs/ip16_date_heatmap.svg the heatmap

Pure stdlib. Rerun with:
    python3 analyses/ip16-date-heatmap/build_and_plot.py
"""
from __future__ import annotations
import colorsys
import json
import math
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
REV_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"
OUT_DIR = HERE / "outputs"

TOP_N = 60


def hsl_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def cell_color(count: int, max_count: int) -> str:
    if count <= 0:
        return "#f7f7f7"
    frac = math.log1p(count) / math.log1p(max_count)
    hue = 215
    sat = 0.30 + 0.55 * frac
    light = 0.94 - 0.72 * frac
    return hsl_hex(hue, sat, light)


def slash8_color(prefix: str) -> str:
    """Deterministic swatch colour for a /8 prefix — hash → hue."""
    h = 0
    for ch in prefix:
        h = (h * 131 + ord(ch)) & 0xFFFFFFF
    hue = (h * 137) % 360
    return hsl_hex(hue, 0.55, 0.55)


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
    totals: dict[str, int] = defaultdict(int)
    with REV_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            t = r.get("time") or ""
            if len(t) < 10:
                continue
            ip = r.get("ip16") or "(none)"
            per_day[(ip, t[:10])] += 1
            totals[ip] += 1
    return totals, per_day


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    totals, per_day = collect()

    top = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_N]
    top_ips = [ip for ip, _ in top]

    dates_present = sorted({d for (_, d) in per_day})
    dates = date_range(dates_present[0], dates_present[-1])

    with (OUT_DIR / "ip16_daily.tsv").open("w") as f:
        f.write("ip16\tdate\trevisions\n")
        for ip in top_ips:
            for d in dates:
                n = per_day.get((ip, d), 0)
                if n:
                    f.write(f"{ip}\t{d}\t{n}\n")

    max_cell = max((per_day.get((ip, d), 0) for ip in top_ips for d in dates),
                   default=1) or 1

    # Layout.
    W = 1500
    ROW_H = 12
    MARGIN_L, MARGIN_R = 200, 220
    MARGIN_T, MARGIN_B = 74, 90
    plot_w = W - MARGIN_L - MARGIN_R
    plot_h = TOP_N * ROW_H
    H = MARGIN_T + plot_h + MARGIN_B
    cell_w = plot_w / len(dates)

    total_all = sum(totals.values())
    total_top = sum(totals[ip] for ip in top_ips)
    n_slash8 = len({ip.split(".")[0] for ip in totals})
    n_slash16 = len(totals)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="11">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">Top {TOP_N} source '
        f'/16 subnets: daily revision heatmap</text>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="46" text-anchor="middle" '
        f'fill="#555">Rows ordered by total revisions. Shade = log(revs on '
        f'that day). Peak cell: {max_cell:,} revs. Swatch = /8 prefix.</text>',
    ]

    # Rows.
    for i, ip in enumerate(top_ips):
        y_row = MARGIN_T + i * ROW_H
        slash8 = ip.split(".")[0]
        # /8 swatch.
        parts.append(
            f'<rect x="6" y="{y_row + 1}" width="10" height="{ROW_H - 2}" '
            f'fill="{slash8_color(slash8)}"><title>{escape(slash8)}.*'
            f'</title></rect>'
        )
        parts.append(
            f'<text x="24" y="{y_row + ROW_H - 3}" fill="#111">'
            f'{escape(ip)}</text>'
        )
        parts.append(
            f'<text x="{MARGIN_L - 8}" y="{y_row + ROW_H - 3}" '
            f'text-anchor="end" fill="#666">{totals[ip]:,}</text>'
        )
        # Background band.
        parts.append(
            f'<rect x="{MARGIN_L}" y="{y_row}" width="{plot_w:.1f}" '
            f'height="{ROW_H}" fill="#fbfbfb" stroke="none"/>'
        )
        for j, d in enumerate(dates):
            n = per_day.get((ip, d), 0)
            if n <= 0:
                continue
            x = MARGIN_L + j * cell_w
            parts.append(
                f'<rect x="{x:.2f}" y="{y_row + 0.5}" width="{cell_w:.2f}" '
                f'height="{ROW_H - 1}" fill="{cell_color(n, max_cell)}" '
                f'stroke="none"><title>{escape(ip)} · {d} · {n:,}'
                f'</title></rect>'
            )

    # X-axis labels.
    step = max(1, len(dates) // 20)
    y0 = MARGIN_T + plot_h
    for j, d in enumerate(dates):
        if j % step != 0 and j != len(dates) - 1:
            continue
        x = MARGIN_L + j * cell_w + cell_w / 2
        parts.append(
            f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y0 + 4}" '
            f'stroke="#666" stroke-width="0.5"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y0 + 18}" text-anchor="end" fill="#333" '
            f'transform="rotate(-60 {x:.1f} {y0 + 18})">{d[5:]}</text>'
        )
    parts.append(
        f'<line x1="{MARGIN_L}" y1="{y0}" x2="{MARGIN_L + plot_w}" '
        f'y2="{y0}" stroke="#333" stroke-width="0.5"/>'
    )
    parts.append(
        f'<line x1="{MARGIN_L}" y1="{MARGIN_T}" x2="{MARGIN_L}" '
        f'y2="{y0}" stroke="#333" stroke-width="0.5"/>'
    )

    # Legend.
    lx = MARGIN_L + plot_w + 20
    ly = MARGIN_T
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'revs on a (subnet, day) cell</text>'
    )
    ly += 14
    ramp_w = 180
    ramp_h = 14
    steps = 100
    for i in range(steps):
        frac = i / (steps - 1)
        n = int(round(math.expm1(frac * math.log1p(max_cell))))
        parts.append(
            f'<rect x="{lx + i * ramp_w / steps:.2f}" y="{ly}" '
            f'width="{ramp_w / steps + 0.5:.2f}" height="{ramp_h}" '
            f'fill="{cell_color(max(1, n), max_cell)}" stroke="none"/>'
        )
    parts.append(
        f'<rect x="{lx}" y="{ly}" width="{ramp_w}" height="{ramp_h}" '
        f'fill="none" stroke="#333" stroke-width="0.5"/>'
    )
    ticks = sorted({1, 10, 100, 1000, max_cell})
    for t in ticks:
        frac = math.log1p(t) / math.log1p(max_cell)
        x = lx + frac * ramp_w
        parts.append(
            f'<line x1="{x:.1f}" y1="{ly + ramp_h}" x2="{x:.1f}" '
            f'y2="{ly + ramp_h + 3}" stroke="#333" stroke-width="0.5"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{ly + ramp_h + 14}" '
            f'text-anchor="middle" font-size="10" fill="#333">{t:,}</text>'
        )

    # Top /8 groupings among the top-N rows.
    ly += ramp_h + 40
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'/8 groups in top {TOP_N}</text>'
    )
    ly += 14
    slash8_counts: dict[str, int] = defaultdict(int)
    slash8_ips: dict[str, int] = defaultdict(int)
    for ip in top_ips:
        s8 = ip.split(".")[0]
        slash8_counts[s8] += totals[ip]
        slash8_ips[s8] += 1
    for s8, n in sorted(slash8_counts.items(), key=lambda kv: -kv[1])[:12]:
        parts.append(
            f'<rect x="{lx}" y="{ly}" width="12" height="12" '
            f'fill="{slash8_color(s8)}"/>'
        )
        parts.append(
            f'<text x="{lx + 18}" y="{ly + 10}" fill="#111">{s8}.*'
            f' <tspan fill="#666">· {slash8_ips[s8]} /16s · '
            f'{n:,} revs</tspan></text>'
        )
        ly += 15

    ly += 10
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">notes</text>'
    )
    ly += 14
    for line in [
        f"top {TOP_N} /16s cover",
        f"  {total_top:,} of {total_all:,} revs "
        f"({100 * total_top / total_all:.0f}%)",
        f"across {n_slash16} /16s in",
        f"{n_slash8} /8 prefixes",
    ]:
        parts.append(f'<text x="{lx}" y="{ly}" fill="#333">{line}</text>')
        ly += 14

    parts.append("</svg>")
    (OUT_DIR / "ip16_date_heatmap.svg").write_text("\n".join(parts))
    print(f"wrote {OUT_DIR / 'ip16_daily.tsv'}", file=sys.stderr)
    print(f"wrote {OUT_DIR / 'ip16_date_heatmap.svg'}", file=sys.stderr)


if __name__ == "__main__":
    main()
