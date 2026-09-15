"""Render a chain of specific new-link creation events as an SVG.

Input is a list of (src_page, src_seq, dst_page) triples, ordered along
the chain. Each row is a page (union of src and dst names, in first-seen
order). A colored drop falls at the src rev's write_date from the src bar
down to the dst row, ending on an open circle (target didn't exist yet at
that moment; the caller only supplies at-creation-time forward-link
events). A downward triangle marks the drop's origin on the src bar.

Every rev of a page that appears in the triple list contributes an @N tick
and label on that page's bar so the reader can see which specific rev
introduced the link.

Style is monochrome, matching the other chain SVGs in this analysis.
"""
import json
import re
import sys
from datetime import datetime, timedelta

PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"

BAR_COLOR = "#222"
DROP_COLOR = "#777"
GRID_COLOR = "#f0f0f0"
AXIS_COLOR = "#333"

# The specific link events to plot.
EVENTS = [
    ("AgentMassDataNext774411",  1, "AgentMassThird889922"),
    ("AgentMassThird889922",      1, "AgentMassFourth990033"),
    ("AgentMassFourth990033",     1, "AgentMassFifth551199"),
    ("AgentMassFifth551199",      2, "AgentMassSixth113377"),
    ("AgentMassSixth113377",      1, "AgentMassSeventh991113"),
]


def parse(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def load_revs(names):
    revs = {n: [] for n in names}
    first_t = {}
    with open(PROWIKI) as f:
        for line in f:
            r = json.loads(line)
            if r.get("wiki") != "dse":
                continue
            name = r["name"]
            t = r.get("write_date")
            if not t:
                continue
            t = parse(t)
            if name in revs:
                revs[name].append({"seq": r["seq"], "t": t})
            if name not in first_t or t < first_t[name]:
                first_t[name] = t
    for n in revs:
        revs[n].sort(key=lambda r: r["t"])
    return revs, first_t


def main(out_path):
    # Row order: first appearance of each page as we walk the event list.
    order = []
    for src, _, dst in EVENTS:
        for n in (src, dst):
            if n not in order:
                order.append(n)
    revs, first_t = load_revs(order)

    # For each row, which revisions do we mark as @N ticks? All revisions of
    # that page whose seq appears as the src of some event, plus that page's
    # @1 (its own creation). Duplicates de-duped.
    row_marks = {n: {1} for n in order}
    for src, seq, _ in EVENTS:
        row_marks[src].add(seq)

    # Look up (page, seq) -> time.
    def rev_time(page, seq):
        for r in revs[page]:
            if r["seq"] == seq:
                return r["t"]
        raise KeyError(f"{page}@{seq}")

    # X-axis: from earliest tick to latest.
    times = []
    for n in order:
        for seq in row_marks[n]:
            times.append(rev_time(n, seq))
    lo, hi = min(times), max(times)
    span = hi - lo
    pad = timedelta(seconds=max(180, span.total_seconds() * 0.06))
    x_start, x_end = lo - pad, hi + pad

    LEFT_LABEL_W = 340
    RIGHT_PAD = 30
    TOP_PAD = 30
    ROW_H = 40
    CHART_W = 800
    n_rows = len(order)
    CHART_H = n_rows * ROW_H
    SVG_W = LEFT_LABEL_W + CHART_W + RIGHT_PAD
    SVG_H = TOP_PAD + CHART_H + 90

    def x_of(t):
        s = (x_end - x_start).total_seconds()
        return LEFT_LABEL_W + (t - x_start).total_seconds() / s * CHART_W

    def y_of(i):
        return TOP_PAD + i * ROW_H + ROW_H / 2

    span_s = (x_end - x_start).total_seconds()
    for step_s in [180, 300, 600, 900, 1800]:
        if span_s / step_s <= 8:
            tick_step = step_s
            break
    else:
        tick_step = 3600
    epoch_s = int(x_start.timestamp())
    first_tick = ((epoch_s // tick_step) + 1) * tick_step
    tick_times = []
    ts = first_tick
    while ts <= x_end.timestamp():
        tick_times.append(datetime.fromtimestamp(ts, tz=x_start.tzinfo))
        ts += tick_step

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" '
        f'height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}" '
        f'font-family="monospace" font-size="12">'
    )
    parts.append(f'<rect x="0" y="0" width="{SVG_W}" height="{SVG_H}" fill="#fff"/>')

    for t in tick_times:
        x = x_of(t)
        parts.append(
            f'<line x1="{x:.1f}" y1="{TOP_PAD}" x2="{x:.1f}" '
            f'y2="{TOP_PAD + CHART_H}" stroke="{GRID_COLOR}" stroke-width="1"/>'
        )

    # Drops under bars.
    row_of = {n: i for i, n in enumerate(order)}
    drop_events = []
    for src, seq, dst in EVENTS:
        x = x_of(rev_time(src, seq))
        y_src = y_of(row_of[src])
        y_dst = y_of(row_of[dst])
        drop_events.append((x, y_src, y_dst))
        parts.append(
            f'<line x1="{x:.1f}" y1="{y_src + 5:.1f}" '
            f'x2="{x:.1f}" y2="{y_dst:.1f}" '
            f'stroke="{DROP_COLOR}" stroke-width="1.2" '
            f'stroke-dasharray="4 3" fill="none"/>'
        )

    # Bars + @N markers.
    for i, name in enumerate(order):
        y = y_of(i)
        first_t_row = first_t[name]
        parts.append(
            f'<text x="{LEFT_LABEL_W - 8}" y="{y + 4}" text-anchor="end" '
            f'fill="{BAR_COLOR}" font-weight="bold">{name}</text>'
        )
        parts.append(
            f'<line x1="{x_of(first_t_row):.1f}" y1="{y}" '
            f'x2="{LEFT_LABEL_W + CHART_W:.1f}" y2="{y}" '
            f'stroke="{BAR_COLOR}" stroke-width="2.5"/>'
        )
        for seq in sorted(row_marks[name]):
            x = x_of(rev_time(name, seq))
            parts.append(
                f'<line x1="{x:.1f}" y1="{y - 5}" x2="{x:.1f}" y2="{y + 5}" '
                f'stroke="{BAR_COLOR}" stroke-width="2"/>'
            )
            parts.append(
                f'<text x="{x + 3:.1f}" y="{y - 7}" text-anchor="start" '
                f'fill="{BAR_COLOR}" font-weight="bold">@{seq}</text>'
            )

    # Bottom triangles at each drop's source, and open circles at each dst.
    for x, y_src, y_dst in drop_events:
        parts.append(
            f'<polygon points="{x-4:.1f},{y_src + 2:.1f} '
            f'{x+4:.1f},{y_src + 2:.1f} {x:.1f},{y_src + 9:.1f}" '
            f'fill="{BAR_COLOR}" stroke="{BAR_COLOR}"/>'
        )
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y_dst:.1f}" r="4.5" fill="#fff" '
            f'stroke="{BAR_COLOR}" stroke-width="1.8"/>'
        )

    # Axes.
    parts.append(
        f'<line x1="{LEFT_LABEL_W}" y1="{TOP_PAD}" x2="{LEFT_LABEL_W}" '
        f'y2="{TOP_PAD + CHART_H}" stroke="{AXIS_COLOR}" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{LEFT_LABEL_W}" y1="{TOP_PAD + CHART_H}" '
        f'x2="{LEFT_LABEL_W + CHART_W}" y2="{TOP_PAD + CHART_H}" '
        f'stroke="{AXIS_COLOR}" stroke-width="1"/>'
    )
    for t in tick_times:
        x = x_of(t)
        parts.append(
            f'<text x="{x:.1f}" y="{TOP_PAD + CHART_H + 15}" '
            f'text-anchor="middle" fill="{AXIS_COLOR}">'
            f'{t.strftime("%H:%M")}</text>'
        )
    parts.append(
        f'<text x="{LEFT_LABEL_W + CHART_W / 2:.1f}" '
        f'y="{TOP_PAD + CHART_H + 35}" text-anchor="middle" '
        f'fill="{AXIS_COLOR}">{x_start.strftime("%Y-%m-%d")} UTC</text>'
    )

    # Legend.
    lx = LEFT_LABEL_W + 10
    ly1 = TOP_PAD + CHART_H + 55
    ly2 = ly1 + 18
    parts.append(
        f'<polygon points="{lx-4:.1f},{ly1 - 8:.1f} {lx+4:.1f},{ly1 - 8:.1f} '
        f'{lx:.1f},{ly1 - 1:.1f}" fill="{BAR_COLOR}" stroke="{BAR_COLOR}"/>'
    )
    parts.append(
        f'<text x="{lx + 10}" y="{ly1}" fill="{AXIS_COLOR}" font-size="11">'
        f'link created at this rev</text>'
    )
    parts.append(
        f'<circle cx="{lx}" cy="{ly2 - 4}" r="4.5" fill="#fff" '
        f'stroke="{BAR_COLOR}" stroke-width="1.8"/>'
    )
    parts.append(
        f'<text x="{lx + 10}" y="{ly2}" fill="{AXIS_COLOR}" font-size="11">'
        f'target did not yet exist</text>'
    )

    parts.append('</svg>')
    with open(out_path, "w") as f:
        f.write("\n".join(parts))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    out = (sys.argv[1] if len(sys.argv) > 1
           else "/collusionwiki/analyses/dse-forward-links/outputs/"
                "chain_events_mass_seventh.svg")
    main(out)
