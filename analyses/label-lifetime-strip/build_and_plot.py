#!/usr/bin/env python3
"""Top-N agent handles (by stored revisions) plotted as a heatmap:

  rows = handles, ordered by first appearance (top = earliest)
  cols = UTC calendar days across the export
  cell = shade of the handle's class hue, log-scaled by (label, date) revs

Reads:
  agent-logs/prowiki/revisions.jsonl
  analyses/labels/outputs/labels-classified.jsonl

Writes:
  outputs/top_labels_daily.tsv        label, date, revisions
  outputs/label_lifetime_strip.svg    the heatmap

Pure stdlib. Rerun with:
    python3 analyses/label-lifetime-strip/build_and_plot.py
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
LABELS_CLASSIFIED = REPO_ROOT / "analyses" / "labels" / "outputs" / "labels-classified.jsonl"
OUT_DIR = HERE / "outputs"

TOP_N = 80

# Handle-class → base hue. Chosen so classes are easy to tell apart at low
# saturation (long bars of pale colour must still be distinguishable).
CLASS_HUE = {
    "role_word_agent":    215,   # blue
    "openai_branded":      15,   # red-orange
    "codename_agent":     140,   # green
    "date_prefix_agent":  285,   # violet
    "redacted":            45,   # amber
    "short_or_test":      325,   # magenta
    "human_admin":         85,   # olive
    "other":              200,   # cyan
    "blank":                0,   # grey (sat=0 below)
}
CLASS_ORDER = [
    "role_word_agent", "openai_branded", "codename_agent", "date_prefix_agent",
    "short_or_test", "redacted", "other", "human_admin", "blank",
]


def load_label_class() -> dict[str, dict]:
    m: dict[str, dict] = {}
    with LABELS_CLASSIFIED.open() as f:
        for line in f:
            r = json.loads(line)
            m[r["label"]] = {
                "handle_class": r.get("handle_class", "other"),
                "first_write": r.get("first_write", ""),
                "last_write": r.get("last_write", ""),
                "stored_revisions": r.get("stored_revisions", 0),
            }
    return m


def collect_daily() -> tuple[dict[str, int], dict[tuple[str, str], int]]:
    """Return (label_total, (label, date) -> count) — all labels."""
    totals: dict[str, int] = defaultdict(int)
    per_day: dict[tuple[str, str], int] = defaultdict(int)
    with REV_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            t = r.get("time") or ""
            if len(t) < 10:
                continue
            label = r.get("label", "")
            totals[label] += 1
            per_day[(label, t[:10])] += 1
    return totals, per_day


def date_range(start: str, end: str) -> list[str]:
    y1, m1, d1 = (int(x) for x in start.split("-"))
    y2, m2, d2 = (int(x) for x in end.split("-"))
    a, b = date(y1, m1, d1), date(y2, m2, d2)
    out, cur = [], a
    while cur <= b:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def hsl_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def cell_color(handle_class: str, count: int, max_count: int) -> str:
    if count <= 0:
        return "#fafafa"
    hue = CLASS_HUE.get(handle_class, 200)
    if handle_class == "blank":
        # Pure grey ramp.
        frac = math.log1p(count) / math.log1p(max_count)
        return hsl_hex(0, 0.0, 0.92 - 0.70 * frac)
    frac = math.log1p(count) / math.log1p(max_count)
    sat = 0.35 + 0.55 * frac
    light = 0.92 - 0.60 * frac
    return hsl_hex(hue, sat, light)


def solid_class_color(handle_class: str) -> str:
    return hsl_hex(CLASS_HUE.get(handle_class, 200), 0.65, 0.48) \
        if handle_class != "blank" else hsl_hex(0, 0.0, 0.45)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    label_info = load_label_class()
    totals, per_day = collect_daily()

    # Top-N by stored revisions.
    top = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_N]
    top_labels = [lbl for lbl, _ in top]

    # Row order: by first-write ascending (top = earliest).
    def first_seen(lbl: str) -> str:
        info = label_info.get(lbl, {})
        return info.get("first_write") or "9999-99-99"
    row_labels = sorted(top_labels, key=first_seen)

    # Date range: full export.
    all_dates_present = {d for (_, d) in per_day}
    dates = date_range(min(all_dates_present), max(all_dates_present))

    # Emit TSV.
    with (OUT_DIR / "top_labels_daily.tsv").open("w") as f:
        f.write("label\tdate\trevisions\n")
        for lbl in row_labels:
            for d in dates:
                n = per_day.get((lbl, d), 0)
                if n:
                    f.write(f"{lbl}\t{d}\t{n}\n")

    # Max cell for shade scaling — only across the top-N cells.
    max_cell = max(per_day.get((l, d), 0) for l in row_labels for d in dates) or 1

    # Layout.
    W = 1600
    ROW_H = 12
    N_ROWS = len(row_labels)
    MARGIN_L, MARGIN_R = 300, 220   # left for handle labels, right for legend
    MARGIN_T, MARGIN_B = 74, 90
    plot_w = W - MARGIN_L - MARGIN_R
    plot_h = N_ROWS * ROW_H
    H = MARGIN_T + plot_h + MARGIN_B
    cell_w = plot_w / len(dates)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="11">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">Top {TOP_N} agent handles: '
        f'daily activity heatmap</text>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="46" text-anchor="middle" '
        f'fill="#555">Rows ordered by first observed edit. Hue = handle-class. '
        f'Shade = log(revisions on that day). Peak cell: {max_cell:,} revs.</text>',
    ]

    # Cells + row backgrounds.
    for i, lbl in enumerate(row_labels):
        cls = label_info.get(lbl, {}).get("handle_class", "other")
        y_row = MARGIN_T + i * ROW_H
        parts.append(
            f'<rect x="{MARGIN_L}" y="{y_row}" width="{plot_w:.1f}" '
            f'height="{ROW_H}" fill="#fbfbfb" stroke="none"/>'
        )
        for j, d in enumerate(dates):
            n = per_day.get((lbl, d), 0)
            if n <= 0:
                continue
            x = MARGIN_L + j * cell_w
            parts.append(
                f'<rect x="{x:.2f}" y="{y_row + 0.5}" width="{cell_w:.2f}" '
                f'height="{ROW_H - 1}" fill="{cell_color(cls, n, max_cell)}" '
                f'stroke="none"><title>{escape(lbl)} · {d} · {n:,}'
                f'</title></rect>'
            )

        # Handle label (left).
        total = totals.get(lbl, 0)
        disp_lbl = lbl if lbl else "(blank)"
        if len(disp_lbl) > 32:
            disp_lbl = disp_lbl[:30] + "…"
        parts.append(
            f'<text x="{MARGIN_L - 60}" y="{y_row + ROW_H - 3}" '
            f'text-anchor="end" fill="#111" font-size="10">'
            f'{escape(disp_lbl)}</text>'
        )
        parts.append(
            f'<text x="{MARGIN_L - 8}" y="{y_row + ROW_H - 3}" '
            f'text-anchor="end" fill="#666" font-size="10">'
            f'{total:,}</text>'
        )
        # Class swatch to the very left.
        parts.append(
            f'<rect x="6" y="{y_row + 1}" width="10" height="{ROW_H - 2}" '
            f'fill="{solid_class_color(cls)}"><title>{cls}</title></rect>'
        )

    # X-axis: date labels every ~3 days.
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
        f'<line x1="{MARGIN_L}" y1="{MARGIN_T}" x2="{MARGIN_L}" '
        f'y2="{y0}" stroke="#333" stroke-width="0.5"/>'
    )
    parts.append(
        f'<line x1="{MARGIN_L}" y1="{y0}" x2="{MARGIN_L + plot_w}" '
        f'y2="{y0}" stroke="#333" stroke-width="0.5"/>'
    )

    # Legend: class swatch + count of top-N handles in that class + hue ramp.
    lx = MARGIN_L + plot_w + 20
    ly = MARGIN_T
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'handle-class</text>'
    )
    ly += 14
    class_top_counts: dict[str, int] = defaultdict(int)
    for lbl in row_labels:
        cls = label_info.get(lbl, {}).get("handle_class", "other")
        class_top_counts[cls] += 1

    for cls in CLASS_ORDER:
        n_in_top = class_top_counts.get(cls, 0)
        if n_in_top == 0:
            continue
        # Ramp of 6 shades for this class.
        ramp_w = 90
        seg_w = ramp_w / 6
        for k in range(6):
            n_syn = int(round(math.expm1((k + 1) / 6 * math.log1p(max_cell))))
            parts.append(
                f'<rect x="{lx + k * seg_w:.1f}" y="{ly}" '
                f'width="{seg_w:.1f}" height="12" '
                f'fill="{cell_color(cls, max(1, n_syn), max_cell)}"/>'
            )
        parts.append(
            f'<text x="{lx + ramp_w + 8}" y="{ly + 10}" fill="#111" '
            f'font-size="11">{cls} <tspan fill="#666">· {n_in_top} of top '
            f'{TOP_N}</tspan></text>'
        )
        ly += 18

    ly += 8
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">notes</text>'
    )
    ly += 14
    all_revs = sum(totals.values())
    top_revs = sum(totals[l] for l in row_labels)
    for line in [
        f"top {TOP_N} handles account for",
        f"  {top_revs:,} / {all_revs:,} revs "
        f"({100 * top_revs / all_revs:.0f}%)",
        f"of {len(totals):,} distinct labels total",
        f"date range: {dates[0]} → {dates[-1]}",
    ]:
        parts.append(f'<text x="{lx}" y="{ly}" fill="#333">{line}</text>')
        ly += 14

    parts.append("</svg>")
    (OUT_DIR / "label_lifetime_strip.svg").write_text("\n".join(parts))
    print(f"wrote {OUT_DIR / 'top_labels_daily.tsv'}", file=sys.stderr)
    print(f"wrote {OUT_DIR / 'label_lifetime_strip.svg'} "
          f"({len(row_labels)} handles × {len(dates)} days)", file=sys.stderr)


if __name__ == "__main__":
    main()
