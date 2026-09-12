"""Render a chain of at-creation forward links as an SVG.

Each row is a page. Each page's @1 revision contains a wiki.cgi?id= link to
the next page in the chain; the next page's own @1 is later in time.

For every page in a chain, a colored dashed drop falls at that page's @1
timestamp down to the next page's row, ending in an open circle (the
target does not exist yet). Drop color matches the source row.

Multiple chains stack vertically in one SVG so different runs can be
compared on a shared X-axis.
"""
import json
import re
import sys
from datetime import datetime, timedelta

PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"
WIKI_CGI_ID = re.compile(
    r"wikiservice\.at/dse/wiki\.cgi\?[^\s\]]*?\bid=([A-Za-z0-9_/\-]+)"
)

PALETTE = [
    "#1f77b4", "#2ca02c", "#ff7f0e", "#d62728",
    "#9467bd", "#17becf", "#e377c2", "#8c564b",
    "#bcbd22", "#393b79", "#637939", "#843c39",
]

CHAINS = [
    ["AgentMassDataNext774411", "AgentMassThird889922",
     "AgentMassFourth990033", "AgentMassFifth551199"],
    ["AgentMassSixth113377", "AgentMassSeventh991113",
     "AgentMassEighth224466", "AgentMassNinth778899"],
]


def parse(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def load_first_revs():
    first_rev = {}
    with open(PROWIKI) as f:
        for line in f:
            r = json.loads(line)
            if r.get("wiki") != "dse":
                continue
            t = r.get("write_date")
            if not t:
                continue
            t = parse(t)
            name = r["name"]
            if name not in first_rev or t < first_rev[name]["t"]:
                first_rev[name] = {"t": t, "body": r.get("body") or "",
                                    "label": r.get("label")}
    return first_rev


def build_svg(chains, out_path, gap_rows=1):
    first_rev = load_first_revs()

    # Flatten to a row order with visual gaps between chains.
    rows = []  # list of (name | None, color_idx or None)
    color_idx = 0
    for ci, chain in enumerate(chains):
        if ci > 0:
            for _ in range(gap_rows):
                rows.append((None, None))
        for name in chain:
            rows.append((name, color_idx))
            color_idx += 1

    # X-axis range from earliest @1 to latest @1 plus a bit of padding.
    times = [first_rev[n]["t"] for name_row, _ in rows if name_row
             for n in [name_row]]
    lo, hi = min(times), max(times)
    span = hi - lo
    pad = timedelta(seconds=max(300, span.total_seconds() * 0.08))
    x_start = lo - pad
    x_end = hi + pad

    LEFT_LABEL_W = 340
    RIGHT_PAD = 20
    TOP_PAD = 30
    ROW_H = 40
    CHART_W = 720
    CHART_H = len(rows) * ROW_H
    SVG_W = LEFT_LABEL_W + CHART_W + RIGHT_PAD
    SVG_H = TOP_PAD + CHART_H + 60

    def x_of(t):
        s = (x_end - x_start).total_seconds()
        return LEFT_LABEL_W + (t - x_start).total_seconds() / s * CHART_W

    def y_of(row):
        return TOP_PAD + row * ROW_H + ROW_H / 2

    # Tick step: aim for 5-8 ticks.
    span_s = (x_end - x_start).total_seconds()
    for step_s in [300, 600, 900, 1800, 3600, 7200]:
        if span_s / step_s <= 8:
            tick_step_s = step_s
            break
    else:
        tick_step_s = 14400
    epoch_s = int(x_start.timestamp())
    first_tick_s = ((epoch_s // tick_step_s) + 1) * tick_step_s
    tick_times = []
    ts = first_tick_s
    while ts <= x_end.timestamp():
        tick_times.append(datetime.fromtimestamp(ts, tz=x_start.tzinfo))
        ts += tick_step_s

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" '
        f'height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}" '
        f'font-family="monospace" font-size="12">'
    )
    parts.append(
        f'<rect x="0" y="0" width="{SVG_W}" height="{SVG_H}" fill="#ffffff"/>'
    )
    parts.append(
        '<style>'
        '.axis{stroke:#333;stroke-width:1;fill:none}'
        '.grid{stroke:#f5f5f5;stroke-width:1;fill:none}'
        '.tick{fill:#333}'
        '</style>'
    )

    # Grid
    for t in tick_times:
        x = x_of(t)
        parts.append(
            f'<line class="grid" x1="{x:.1f}" y1="{TOP_PAD}" '
            f'x2="{x:.1f}" y2="{TOP_PAD + CHART_H}"/>'
        )

    # Compute drops: for each chain, each page (except last) drops to the next.
    # Drops sit UNDER bars, so emit them first.
    drops = []  # (x, y1, y2, color, target_y)
    row_index_of = {}
    for i, (name, cidx) in enumerate(rows):
        if name:
            row_index_of[name] = i
    for chain in chains:
        for src, tgt in zip(chain, chain[1:]):
            i_src = row_index_of[src]
            i_tgt = row_index_of[tgt]
            color = PALETTE[rows[i_src][1] % len(PALETTE)]
            x = x_of(first_rev[src]["t"])
            drops.append((x, y_of(i_src), y_of(i_tgt), color))

    for x, y1, y2, color in drops:
        parts.append(
            f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="1.5" '
            f'stroke-dasharray="4 3" fill="none"/>'
        )

    # Bars.
    for i, (name, cidx) in enumerate(rows):
        if name is None:
            continue
        color = PALETTE[cidx % len(PALETTE)]
        y = y_of(i)
        first_t = first_rev[name]["t"]
        parts.append(
            f'<text x="{LEFT_LABEL_W - 8}" y="{y + 4}" '
            f'text-anchor="end" fill="{color}" font-weight="bold">{name}</text>'
        )
        parts.append(
            f'<line x1="{x_of(first_t):.1f}" y1="{y}" '
            f'x2="{LEFT_LABEL_W + CHART_W:.1f}" y2="{y}" '
            f'stroke="{color}" stroke-width="3" fill="none"/>'
        )
        # @1 marker.
        x = x_of(first_t)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y - 5}" x2="{x:.1f}" y2="{y + 5}" '
            f'stroke="{color}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{x + 3:.1f}" y="{y - 7}" text-anchor="start" '
            f'fill="{color}" font-weight="bold">@1</text>'
        )

    # Dots at each drop's target row (all forward, so all open).
    for x, y1, y2, color in drops:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y2:.1f}" r="5" fill="#fff" '
            f'stroke="{color}" stroke-width="2"/>'
        )

    # Axis + tick labels.
    parts.append(
        f'<line class="axis" x1="{LEFT_LABEL_W}" y1="{TOP_PAD}" '
        f'x2="{LEFT_LABEL_W}" y2="{TOP_PAD + CHART_H}"/>'
    )
    parts.append(
        f'<line class="axis" x1="{LEFT_LABEL_W}" y1="{TOP_PAD + CHART_H}" '
        f'x2="{LEFT_LABEL_W + CHART_W}" y2="{TOP_PAD + CHART_H}"/>'
    )
    for t in tick_times:
        x = x_of(t)
        parts.append(
            f'<text class="tick" x="{x:.1f}" y="{TOP_PAD + CHART_H + 15}" '
            f'text-anchor="middle">{t.strftime("%H:%M")}</text>'
        )
    parts.append(
        f'<text class="tick" x="{LEFT_LABEL_W + CHART_W / 2:.1f}" '
        f'y="{TOP_PAD + CHART_H + 35}" text-anchor="middle">'
        f'{x_start.strftime("%Y-%m-%d")} UTC</text>'
    )

    # Legend.
    lx = LEFT_LABEL_W + 20
    ly = TOP_PAD + CHART_H + 55
    parts.append(
        f'<circle cx="{lx}" cy="{ly - 4}" r="5" fill="#fff" '
        f'stroke="#333" stroke-width="2"/>'
    )
    parts.append(
        f'<text class="tick" x="{lx + 10}" y="{ly}" text-anchor="start">'
        f'link created at parent @1; target did not yet exist</text>'
    )

    parts.append('</svg>')
    with open(out_path, "w") as f:
        f.write("\n".join(parts))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    out = (sys.argv[1] if len(sys.argv) > 1
           else "/collusionwiki/analyses/dse-forward-links/outputs/"
                "chain_timeline_mass.svg")
    build_svg(CHAINS, out)
