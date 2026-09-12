"""Render the AgentOpenAIDataUSAHubMay13X7 hub timeline as an SVG.

One row per page (hub on top, then the 8 children created inside the
prowiki UTC-precise window). X axis is 2026-06-16 UTC from 19:30 to 22:00.
Horizontal bar per page runs from that page's @1 write_date to the right
edge. Vertical drop lines fall from each hub revision through every child
row; at each intersection a circle marks whether the linked child page
already existed at that moment: filled = existed, open = did not exist yet.
"""
from datetime import datetime, timezone

# All timestamps are UTC.
def T(h, m, s):
    return datetime(2026, 6, 16, h, m, s, tzinfo=timezone.utc)

HUB = "AgentOpenAIDataUSAHubMay13X7"
HUB_REVS = [("@1", T(19, 41, 35)), ("@2", T(21, 4, 21))]

CHILDREN = [
    ("AgentOpenAIDataUSASlotMay13X7_01", T(20, 40, 39)),
    ("AgentOpenAIDataUSASlotMay13X7_29", T(20, 49, 15)),
    ("AgentOpenAIDataUSASlotMay13X7_28", T(20, 51, 21)),
    ("AgentOpenAIDataUSASlotMay13X7_26", T(20, 56, 33)),
    ("AgentOpenAIDataUSASlotMay13X7_27", T(21, 28, 10)),
    ("AgentOpenAIDataUSASlotMay13X7_24", T(21, 42, 29)),
    ("AgentOpenAIDataUSASlotMay13X7_23", T(21, 46, 21)),
    ("AgentOpenAIDataUSASlotMay13X7_22", T(21, 46, 26)),
]

X_START = T(19, 30, 0)
X_END = T(22, 0, 0)

# Layout
LEFT_LABEL_W = 330
RIGHT_PAD = 20
TOP_PAD = 40
ROW_H = 42
TICK_LABELS = [T(19, 30, 0), T(20, 0, 0), T(20, 30, 0), T(21, 0, 0),
               T(21, 30, 0), T(22, 0, 0)]

CHART_W = 620
CHART_H = (1 + len(CHILDREN)) * ROW_H
SVG_W = LEFT_LABEL_W + CHART_W + RIGHT_PAD
SVG_H = TOP_PAD + CHART_H + 50


def x_of(t):
    span = (X_END - X_START).total_seconds()
    frac = (t - X_START).total_seconds() / span
    return LEFT_LABEL_W + frac * CHART_W


def y_of(row):
    return TOP_PAD + row * ROW_H + ROW_H / 2


def existed_at(child_t, at_t):
    return at_t >= child_t


def hms(t):
    return t.strftime("%H:%M")


def main():
    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" height="{SVG_H}" '
        f'viewBox="0 0 {SVG_W} {SVG_H}" font-family="monospace" font-size="12">'
    )
    parts.append('<style>'
                 '.bar{stroke:#333;stroke-width:2;fill:none}'
                 '.drop{stroke:#888;stroke-width:1;stroke-dasharray:2 3;fill:none}'
                 '.axis{stroke:#333;stroke-width:1;fill:none}'
                 '.grid{stroke:#ddd;stroke-width:1;fill:none}'
                 '.label{fill:#111}'
                 '.rev{fill:#111;font-weight:bold}'
                 '.tick{fill:#333}'
                 '.filled{fill:#333;stroke:#333;stroke-width:1}'
                 '.open{fill:#fff;stroke:#333;stroke-width:1.5}'
                 '</style>')

    # Vertical gridlines at each tick
    for t in TICK_LABELS:
        x = x_of(t)
        parts.append(f'<line class="grid" x1="{x:.1f}" y1="{TOP_PAD}" '
                     f'x2="{x:.1f}" y2="{TOP_PAD + CHART_H}"/>')

    # Y axis on the left of the chart
    parts.append(f'<line class="axis" x1="{LEFT_LABEL_W}" y1="{TOP_PAD}" '
                 f'x2="{LEFT_LABEL_W}" y2="{TOP_PAD + CHART_H}"/>')
    # X axis at the bottom
    parts.append(f'<line class="axis" x1="{LEFT_LABEL_W}" y1="{TOP_PAD + CHART_H}" '
                 f'x2="{LEFT_LABEL_W + CHART_W}" y2="{TOP_PAD + CHART_H}"/>')

    # X-axis tick labels
    for t in TICK_LABELS:
        x = x_of(t)
        y = TOP_PAD + CHART_H + 15
        parts.append(f'<text class="tick" x="{x:.1f}" y="{y}" '
                     f'text-anchor="middle">{hms(t)}</text>')
    parts.append(f'<text class="tick" x="{LEFT_LABEL_W + CHART_W / 2:.1f}" '
                 f'y="{TOP_PAD + CHART_H + 35}" text-anchor="middle">'
                 f'2026-06-16 UTC</text>')

    # Row 0: hub. Bar from hub @1 to right edge.
    row_data = [(HUB, HUB_REVS[0][1], HUB_REVS)] + [
        (name, t, [("@1", t)]) for name, t in CHILDREN
    ]

    for i, (name, first_t, markers) in enumerate(row_data):
        y = y_of(i)
        # Label on the left (right-justified into the label column)
        parts.append(
            f'<text class="label" x="{LEFT_LABEL_W - 8}" y="{y + 4}" '
            f'text-anchor="end">{name}</text>'
        )
        # Horizontal bar from first_t to right edge
        parts.append(
            f'<line class="bar" x1="{x_of(first_t):.1f}" y1="{y}" '
            f'x2="{LEFT_LABEL_W + CHART_W:.1f}" y2="{y}"/>'
        )
        # @-markers on the bar
        for tag, t in markers:
            parts.append(
                f'<text class="rev" x="{x_of(t):.1f}" y="{y - 5}" '
                f'text-anchor="start">{tag}</text>'
            )
            # Small tick on the bar itself so the marker's foot is visible
            parts.append(
                f'<line class="axis" x1="{x_of(t):.1f}" y1="{y - 3}" '
                f'x2="{x_of(t):.1f}" y2="{y + 3}"/>'
            )

    # Drop lines from each hub revision to every child row, with circles.
    for tag, hub_t in HUB_REVS:
        x = x_of(hub_t)
        # Vertical dashed line from hub row down to last child row.
        parts.append(
            f'<line class="drop" x1="{x:.1f}" y1="{y_of(0) + 6}" '
            f'x2="{x:.1f}" y2="{y_of(len(CHILDREN)) + 6}"/>'
        )
        # Circle at each child row.
        for i, (name, child_t) in enumerate(CHILDREN, start=1):
            y = y_of(i)
            cls = "filled" if existed_at(child_t, hub_t) else "open"
            parts.append(f'<circle class="{cls}" cx="{x:.1f}" cy="{y}" r="4.5"/>')

    # Legend
    lx = LEFT_LABEL_W + 20
    ly = TOP_PAD + CHART_H + 45
    parts.append(f'<circle class="open" cx="{lx}" cy="{ly - 4}" r="4.5"/>')
    parts.append(f'<text class="tick" x="{lx + 10}" y="{ly}" '
                 f'text-anchor="start">page did not exist at link time</text>')
    parts.append(f'<circle class="filled" cx="{lx + 260}" cy="{ly - 4}" r="4.5"/>')
    parts.append(f'<text class="tick" x="{lx + 270}" y="{ly}" '
                 f'text-anchor="start">page already existed</text>')

    parts.append('</svg>')

    out = "/collusionwiki/analyses/dse-forward-links/outputs/hub_timeline.svg"
    with open(out, "w") as f:
        f.write("\n".join(parts))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
