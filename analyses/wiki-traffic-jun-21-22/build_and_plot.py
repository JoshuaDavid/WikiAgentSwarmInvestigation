#!/usr/bin/env python3
"""Stacked column chart of wiki revisions per UTC minute across
2026-06-21 and 2026-06-22.

X-axis: 2,880 one-minute buckets. Y-axis: revisions in that minute.
Stack segments: one per wiki.

Reads:
  agent-logs/dse/revisions.jsonl
  agent-logs/fractal/revisions.jsonl
  agent-logs/prowiki/revisions.jsonl        (probier + dorfwiki subsets)
  agent-logs/apchem/revisions.jsonl
  agent-logs/ludism/revisions.jsonl
  agent-logs/milkwiki/revisions.jsonl
  agent-logs/texteditors/revisions.jsonl
  agent-logs/wiki4d/revisions.jsonl

Timestamps in the source data carry a variety of TZ offsets. Every row
is normalised to UTC before bucketing.

Writes:
  outputs/wiki_traffic_by_minute.tsv       minute_utc, wiki, revisions
  outputs/wiki_traffic_stacked_by_wiki.svg the chart

Pure stdlib. Rerun with:
    python3 analyses/wiki-traffic-jun-21-22/build_and_plot.py
"""
from __future__ import annotations
import colorsys
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
OUT_DIR = HERE / "outputs"

# (wiki-name, revisions-jsonl-path, filter on wiki-field or None)
SOURCES: list[tuple[str, Path, str | None]] = [
    ("dse",         REPO_ROOT / "agent-logs" / "dse"         / "revisions.jsonl", None),
    ("fractal",     REPO_ROOT / "agent-logs" / "fractal"     / "revisions.jsonl", None),
    ("probier",     REPO_ROOT / "agent-logs" / "prowiki"     / "revisions.jsonl", "probier"),
    ("dorfwiki",    REPO_ROOT / "agent-logs" / "prowiki"     / "revisions.jsonl", "dorfwiki"),
    ("apchem",      REPO_ROOT / "agent-logs" / "apchem"      / "revisions.jsonl", None),
    ("ludism",      REPO_ROOT / "agent-logs" / "ludism"      / "revisions.jsonl", None),
    ("milkwiki",    REPO_ROOT / "agent-logs" / "milkwiki"    / "revisions.jsonl", None),
    ("texteditors", REPO_ROOT / "agent-logs" / "texteditors" / "revisions.jsonl", None),
    ("wiki4d",      REPO_ROOT / "agent-logs" / "wiki4d"      / "revisions.jsonl", None),
]

WINDOW_START = datetime(2026, 6, 21, 0, 0, 0, tzinfo=timezone.utc)
WINDOW_END   = datetime(2026, 6, 23, 0, 0, 0, tzinfo=timezone.utc)   # exclusive

# Fixed per-wiki hues. Ordering matches the eventual stack order (dse at the
# bottom as the largest slice).
WIKI_HUE = {
    "dse":         15,    # red-orange
    "fractal":    285,    # violet
    "probier":    140,    # green
    "wiki4d":     195,    # teal
    "texteditors": 45,    # amber
    "dorfwiki":   330,    # magenta
    "apchem":      75,    # olive
    "ludism":     260,    # blue-violet
    "milkwiki":   180,    # cyan
}


def hsl_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def wiki_color(name: str) -> str:
    return hsl_hex(WIKI_HUE.get(name, 200), 0.60, 0.48)


def parse_utc(iso: str) -> datetime | None:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def collect() -> tuple[dict[tuple[datetime, str], int], dict[str, int]]:
    """Return ((minute, wiki) -> revs) and (wiki -> total)."""
    per_min: dict[tuple[datetime, str], int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)
    for wname, path, want_wiki in SOURCES:
        if not path.exists():
            print(f"skip {wname}: {path} missing", file=sys.stderr)
            continue
        with path.open() as f:
            for line in f:
                r = json.loads(line)
                if want_wiki is not None and r.get("wiki") != want_wiki:
                    continue
                dt = parse_utc(r.get("time") or "")
                if dt is None:
                    continue
                if dt < WINDOW_START or dt >= WINDOW_END:
                    continue
                minute_bucket = dt.replace(second=0, microsecond=0)
                per_min[(minute_bucket, wname)] += 1
                totals[wname] += 1
    return per_min, totals


def minute_range(a: datetime, b: datetime) -> list[datetime]:
    out, cur = [], a
    step = timedelta(minutes=1)
    while cur < b:
        out.append(cur)
        cur += step
    return out


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
    per_min, totals = collect()
    if not per_min:
        raise RuntimeError("no revisions in window")

    active_wikis = [w for w in WIKI_HUE if totals.get(w, 0) > 0]
    # Stack order (bottom → top): largest total at the bottom.
    stack_order = sorted(active_wikis, key=lambda w: (-totals[w], w))

    minutes = minute_range(WINDOW_START, WINDOW_END)

    # TSV.
    with (OUT_DIR / "wiki_traffic_by_minute.tsv").open("w") as f:
        f.write("minute_utc\twiki\trevisions\n")
        for m in minutes:
            for w in stack_order:
                n = per_min.get((m, w), 0)
                if n:
                    f.write(f"{m.strftime('%Y-%m-%dT%H:%M')}Z\t{w}\t{n}\n")

    # Per-minute totals for y-axis.
    minute_totals = [
        sum(per_min.get((m, w), 0) for w in stack_order) for m in minutes
    ]
    y_peak = max(minute_totals)
    y_max = nice_ymax(y_peak)

    # Layout — one pixel wide bars fit comfortably.
    W = 2160
    MARGIN_L, MARGIN_R = 80, 320
    MARGIN_T, MARGIN_B = 78, 90
    plot_w = W - MARGIN_L - MARGIN_R
    bar_w = plot_w / len(minutes)
    plot_h = 480
    H = MARGIN_T + plot_h + MARGIN_B
    x0, y0 = MARGIN_L, MARGIN_T + plot_h

    total_revs = sum(totals.values())
    n_zero_wikis = len([w for w in WIKI_HUE if totals.get(w, 0) == 0])

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="12">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">Wiki revisions per '
        f'UTC minute, 2026-06-21 and 2026-06-22</text>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="46" text-anchor="middle" '
        f'fill="#555">{total_revs:,} revisions across {len(active_wikis)} '
        f'wikis · 2,880 one-minute buckets · peak minute '
        f'{y_peak} rev{"" if y_peak == 1 else "s"}</text>',
    ]

    # Y-grid + labels.
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

    # Vertical grid: mark each hour. Emphasise midnight (day boundary).
    for i, m in enumerate(minutes):
        if m.minute != 0:
            continue
        x = x0 + i * bar_w
        emph = (m.hour == 0)
        parts.append(
            f'<line x1="{x:.2f}" y1="{MARGIN_T}" x2="{x:.2f}" y2="{y0}" '
            f'stroke="{"#bbb" if emph else "#eee"}" '
            f'stroke-width="{1.0 if emph else 0.5}"/>'
        )
        # Hour label every 3 hours (and always the midnight labels).
        if m.hour % 3 == 0:
            parts.append(
                f'<text x="{x:.2f}" y="{y0 + 14}" text-anchor="middle" '
                f'fill="#333" font-size="10">{m.strftime("%H:%M")}</text>'
            )
        if emph:
            parts.append(
                f'<text x="{x + 4:.2f}" y="{MARGIN_T + 12}" '
                f'fill="#666" font-size="11" font-weight="600">'
                f'{m.strftime("%Y-%m-%d")}</text>'
            )

    # Axes.
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
        f'text-anchor="middle" fill="#333">revisions per minute</text>'
    )
    parts.append(
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="{y0 + 42}" '
        f'text-anchor="middle" fill="#333">UTC time</text>'
    )

    # Bars. Skip minutes with zero total.
    for i, m in enumerate(minutes):
        if minute_totals[i] <= 0:
            continue
        cursor = y0
        x = x0 + i * bar_w
        for w in stack_order:
            n = per_min.get((m, w), 0)
            if n <= 0:
                continue
            seg_h = plot_h * n / y_max
            parts.append(
                f'<rect x="{x:.2f}" y="{cursor - seg_h:.2f}" '
                f'width="{max(0.5, bar_w):.2f}" height="{seg_h:.2f}" '
                f'fill="{wiki_color(w)}" stroke="none">'
                f'<title>{m.strftime("%H:%M")} {m.strftime("%m-%d")} · '
                f'{escape(w)}: {n:,}</title></rect>'
            )
            cursor -= seg_h

    # Legend.
    lx = MARGIN_L + plot_w + 20
    ly = MARGIN_T
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'wikis (stack order top → bottom)</text>'
    )
    ly += 14
    for w in reversed(stack_order):
        n = totals[w]
        parts.append(
            f'<rect x="{lx}" y="{ly}" width="14" height="12" '
            f'fill="{wiki_color(w)}"/>'
        )
        parts.append(
            f'<text x="{lx + 20}" y="{ly + 10}" fill="#111" font-size="11">'
            f'{escape(w)} <tspan fill="#666">· {n:,} rev'
            f'{"" if n == 1 else "s"}</tspan></text>'
        )
        ly += 16

    if n_zero_wikis:
        zero_wikis = sorted(w for w in WIKI_HUE if totals.get(w, 0) == 0)
        ly += 6
        parts.append(
            f'<text x="{lx}" y="{ly}" fill="#666" font-size="11">'
            f'{n_zero_wikis} wiki{"" if n_zero_wikis == 1 else "s"} with 0 '
            f'revs in window:</text>'
        )
        ly += 14
        parts.append(
            f'<text x="{lx}" y="{ly}" fill="#666" font-size="11">'
            f'{escape(", ".join(zero_wikis))}</text>'
        )
        ly += 14

    ly += 10
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">notes</text>'
    )
    ly += 14
    for line in [
        f"window: 2026-06-21 00:00 →",
        f"  2026-06-23 00:00 UTC (48 h)",
        f"1-minute buckets → 2,880 bars",
        f"y-axis is linear",
        f"per-minute peak: {y_peak}",
    ]:
        parts.append(f'<text x="{lx}" y="{ly}" fill="#333">{line}</text>')
        ly += 14

    parts.append("</svg>")
    (OUT_DIR / "wiki_traffic_stacked_by_wiki.svg").write_text("\n".join(parts))
    print(f"wrote {OUT_DIR / 'wiki_traffic_by_minute.tsv'}", file=sys.stderr)
    print(f"wrote {OUT_DIR / 'wiki_traffic_stacked_by_wiki.svg'} "
          f"({total_revs:,} revs, {len(active_wikis)} wikis)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
