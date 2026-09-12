"""Render a per-hub forward-link timeline SVG.

One row per page (hub on top, then each child that the hub ever created a
forward link to — i.e. targets where the hub first added the link before
the child page's own first revision). Each row gets its own color;
vertical drop lines and dots inherit the hub's color.

A dot lands on a child row only if that hub revision was the one that
first introduced the link to that child. Fill state: open = target did
not yet exist when the link was added, filled = target already existed.

Render order: drops under bars, so bars visibly cover drop segments where
they cross without a dot.

Usage:
    python render_hub_timeline.py <HubName> <output.svg>
"""
import json
import re
import sys
from datetime import datetime, timedelta
from collections import defaultdict

PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"
WIKI_CGI_ID = re.compile(
    r"wikiservice\.at/dse/wiki\.cgi\?[^\s\]]*?\bid=([A-Za-z0-9_/\-]+)"
)

HUB_COLOR = "#d62728"
# A generous palette; we cycle if a hub has more forward targets than
# distinct colors.
PALETTE = [
    "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#17becf",
    "#e377c2", "#bcbd22", "#8c564b", "#393b79", "#637939",
    "#8c6d31", "#843c39", "#7b4173", "#5254a3", "#8ca252",
    "#bd9e39", "#ad494a", "#a55194", "#6b6ecf", "#b5cf6b",
    "#e7ba52", "#d6616b", "#ce6dbd", "#9c9ede", "#cedb9c",
    "#e7cb94", "#e7969c", "#de9ed6",
]


def parse(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def load(hub_name):
    """Return (hub_revs_sorted, forward_children, x_start, x_end).

    hub_revs_sorted: list of (t, links) for the hub's revisions, ascending.
    forward_children: list of dicts describing each forward-link target.
    x_start, x_end: X-axis range (datetimes).
    """
    hub_revs = []
    first_write = {}
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
            if name not in first_write or t < first_write[name]:
                first_write[name] = t
            if name == hub_name:
                body = r.get("body") or ""
                links = {h for h in WIKI_CGI_ID.findall(body) if h != hub_name}
                hub_revs.append((t, links))
    hub_revs.sort(key=lambda x: x[0])

    # Walk revs, record first-introduction of each outbound target.
    # `introduced_at` records the FIRST time each link appears in a hub
    # revision. Links can be removed and re-added; the earliest introduction
    # is the one relevant to the forward-link question.
    prev = set()
    introduced_at = {}
    for t, links in hub_revs:
        for new_link in links - prev:
            if new_link not in introduced_at:
                introduced_at[new_link] = t
        prev = links

    # Forward = target's first_write is strictly after its introducing rev's time.
    forward = []
    for target, intro_t in introduced_at.items():
        target_first_t = first_write.get(target)
        if target_first_t is None:
            continue
        if intro_t < target_first_t:
            forward.append({
                "name": target,
                "introduced_at": intro_t,
                "target_first_t": target_first_t,
                "gap_s": (target_first_t - intro_t).total_seconds(),
            })
    forward.sort(key=lambda r: r["introduced_at"])

    if not forward:
        raise SystemExit(f"No forward-link children for {hub_name}")

    # X-axis: cover from just before the earliest relevant hub rev to just
    # after the latest child first_write.
    events = [r["introduced_at"] for r in forward] + [
        r["target_first_t"] for r in forward
    ] + [hub_revs[0][0]]
    lo, hi = min(events), max(events)
    span = hi - lo
    pad = timedelta(seconds=max(300, span.total_seconds() * 0.05))
    return hub_revs, forward, lo - pad, hi + pad


def build_svg(hub_name, out_path):
    hub_revs, forward, x_start, x_end = load(hub_name)

    LEFT_LABEL_W = 340
    RIGHT_PAD = 20
    TOP_PAD = 40
    ROW_H = 40
    CHART_W = 720
    n_rows = 1 + len(forward)
    CHART_H = n_rows * ROW_H
    SVG_W = LEFT_LABEL_W + CHART_W + RIGHT_PAD
    SVG_H = TOP_PAD + CHART_H + 60

    def x_of(t):
        span = (x_end - x_start).total_seconds()
        return LEFT_LABEL_W + (t - x_start).total_seconds() / span * CHART_W

    def y_of(row):
        return TOP_PAD + row * ROW_H + ROW_H / 2

    # X ticks: choose a step that gives 5-8 labels across the range.
    span_s = (x_end - x_start).total_seconds()
    for step_s in [600, 900, 1800, 3600, 7200, 14400, 21600, 43200]:
        if span_s / step_s <= 8:
            tick_step_s = step_s
            break
    else:
        tick_step_s = 86400
    # Snap first tick to a multiple of the step above x_start.
    epoch_s = int(x_start.timestamp())
    first_tick_s = ((epoch_s // tick_step_s) + 1) * tick_step_s
    tick_times = []
    t_s = first_tick_s
    while t_s <= x_end.timestamp():
        tick_times.append(datetime.fromtimestamp(t_s, tz=x_start.tzinfo))
        t_s += tick_step_s

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" '
        f'height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}" '
        f'font-family="monospace" font-size="12">'
    )
    parts.append(f'<rect x="0" y="0" width="{SVG_W}" height="{SVG_H}" fill="#ffffff"/>')
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

    # Drops (under bars) — one per introducing hub rev.
    intro_times = sorted({r["introduced_at"] for r in forward})
    drop_y_top = y_of(0)
    drop_y_bot = y_of(len(forward)) + 6
    for t in intro_times:
        x = x_of(t)
        parts.append(
            f'<line x1="{x:.1f}" y1="{drop_y_top:.1f}" '
            f'x2="{x:.1f}" y2="{drop_y_bot:.1f}" '
            f'stroke="{HUB_COLOR}" stroke-width="1.5" '
            f'stroke-dasharray="4 3" fill="none"/>'
        )

    # Bars.
    hub_first_t = hub_revs[0][0]
    rows = [(hub_name, hub_first_t, HUB_COLOR)]
    for i, r in enumerate(forward):
        rows.append((r["name"], r["target_first_t"], PALETTE[i % len(PALETTE)]))
    for i, (name, first_t, color) in enumerate(rows):
        y = y_of(i)
        parts.append(
            f'<text x="{LEFT_LABEL_W - 8}" y="{y + 4}" '
            f'text-anchor="end" fill="{color}" font-weight="bold">{name}</text>'
        )
        parts.append(
            f'<line x1="{x_of(first_t):.1f}" y1="{y}" '
            f'x2="{LEFT_LABEL_W + CHART_W:.1f}" y2="{y}" '
            f'stroke="{color}" stroke-width="3" fill="none"/>'
        )

    # @ markers.
    # Hub row: one small tick per introducing rev (no text label — too many).
    hub_y = y_of(0)
    for t in intro_times:
        parts.append(
            f'<line x1="{x_of(t):.1f}" y1="{hub_y - 6}" '
            f'x2="{x_of(t):.1f}" y2="{hub_y + 6}" '
            f'stroke="{HUB_COLOR}" stroke-width="2"/>'
        )
    # Child rows: @1 marker at each child's first_write.
    for i, r in enumerate(forward, start=1):
        color = PALETTE[(i - 1) % len(PALETTE)]
        y = y_of(i)
        x = x_of(r["target_first_t"])
        parts.append(
            f'<line x1="{x:.1f}" y1="{y - 5}" '
            f'x2="{x:.1f}" y2="{y + 5}" '
            f'stroke="{color}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{x + 3:.1f}" y="{y - 7}" '
            f'text-anchor="start" fill="{color}" font-weight="bold">@1</text>'
        )

    # Dots — one per forward event, on the introducing rev's drop line at the
    # target's row.
    for i, r in enumerate(forward, start=1):
        x = x_of(r["introduced_at"])
        y = y_of(i)
        # Forward by definition -> open circle.
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y}" r="5" '
            f'fill="#fff" stroke="{HUB_COLOR}" stroke-width="2"/>'
        )

    # Axes and labels.
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
    date_span = f"{x_start.strftime('%Y-%m-%d')} UTC"
    if x_start.date() != x_end.date():
        date_span = f"{x_start.strftime('%Y-%m-%d')} -> {x_end.strftime('%Y-%m-%d')} UTC"
    parts.append(
        f'<text class="tick" x="{LEFT_LABEL_W + CHART_W / 2:.1f}" '
        f'y="{TOP_PAD + CHART_H + 35}" text-anchor="middle">{date_span}</text>'
    )

    # Legend
    lx = LEFT_LABEL_W + 20
    ly = TOP_PAD + CHART_H + 55
    parts.append(
        f'<circle cx="{lx}" cy="{ly - 4}" r="5" fill="#fff" '
        f'stroke="{HUB_COLOR}" stroke-width="2"/>'
    )
    parts.append(
        f'<text class="tick" x="{lx + 10}" y="{ly}" text-anchor="start">'
        f'link created; target did not yet exist</text>'
    )

    parts.append('</svg>')
    with open(out_path, "w") as f:
        f.write("\n".join(parts))
    print(f"wrote {out_path}  ({len(forward)} forward children)")


if __name__ == "__main__":
    hub = sys.argv[1] if len(sys.argv) > 1 else "AgentOpenAIDataUSAHubMay13X7"
    out = sys.argv[2] if len(sys.argv) > 2 else (
        f"/collusionwiki/analyses/dse-forward-links/outputs/"
        f"hub_timeline_{hub}.svg"
    )
    build_svg(hub, out)
