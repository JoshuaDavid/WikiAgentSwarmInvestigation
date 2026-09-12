"""Render the AgentOpenAIDataUSAHubMay13X7 hub timeline as an SVG.

One row per page, each in its own color. Vertical dashed drop lines fall
from each hub revision and inherit the hub's color; dots on those drop
lines also inherit the hub's color. A dot lands on a child row only if
that hub revision created a link to that child (new_links = links in this
rev minus links in the previous rev of the same page). Fill state on a
dot: open = target did not yet exist at drop time, filled = target already
existed.

Render order: drops first, then horizontal bars, so bars visibly cover
drop segments where they cross without a dot.
"""
from datetime import datetime, timezone

def T(h, m, s):
    return datetime(2026, 6, 16, h, m, s, tzinfo=timezone.utc)

HUB = "AgentOpenAIDataUSAHubMay13X7"

_SLOTS = [f"AgentOpenAIDataUSASlotMay13X7_{i:02d}" for i in range(1, 31)]
HUB_REVS = [
    {"tag": "@1", "t": T(19, 41, 35), "new_links": set(_SLOTS)},
    {"tag": "@2", "t": T(21, 4, 21), "new_links": set()},
]

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

HUB_COLOR = "#d62728"
CHILD_COLORS = [
    "#1f77b4",  # _01 blue
    "#2ca02c",  # _29 green
    "#ff7f0e",  # _28 orange
    "#9467bd",  # _26 purple
    "#17becf",  # _27 cyan
    "#e377c2",  # _24 pink
    "#bcbd22",  # _23 olive
    "#8c564b",  # _22 brown
]

X_START = T(19, 30, 0)
X_END = T(22, 0, 0)

LEFT_LABEL_W = 330
RIGHT_PAD = 20
TOP_PAD = 40
ROW_H = 42
CHART_W = 620
CHART_H = (1 + len(CHILDREN)) * ROW_H
SVG_W = LEFT_LABEL_W + CHART_W + RIGHT_PAD
SVG_H = TOP_PAD + CHART_H + 60

TICK_LABELS = [T(19, 30, 0), T(20, 0, 0), T(20, 30, 0), T(21, 0, 0),
               T(21, 30, 0), T(22, 0, 0)]


def x_of(t):
    span = (X_END - X_START).total_seconds()
    frac = (t - X_START).total_seconds() / span
    return LEFT_LABEL_W + frac * CHART_W


def y_of(row):
    return TOP_PAD + row * ROW_H + ROW_H / 2


def hms(t):
    return t.strftime("%H:%M")


def main():
    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" '
        f'height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}" '
        f'font-family="monospace" font-size="12">'
    )
    parts.append(
        '<style>'
        '.axis{stroke:#333;stroke-width:1;fill:none}'
        '.grid{stroke:#eee;stroke-width:1;fill:none}'
        '.tick{fill:#333}'
        '</style>'
    )

    # --- Layer 1: grid ---
    for t in TICK_LABELS:
        x = x_of(t)
        parts.append(
            f'<line class="grid" x1="{x:.1f}" y1="{TOP_PAD}" '
            f'x2="{x:.1f}" y2="{TOP_PAD + CHART_H}"/>'
        )

    # --- Layer 2: drop lines (under bars). All drops from the hub, so all
    # inherit the hub's color. ---
    drop_y_top = y_of(0)
    drop_y_bot = y_of(len(CHILDREN)) + 6
    for rev in HUB_REVS:
        x = x_of(rev["t"])
        parts.append(
            f'<line x1="{x:.1f}" y1="{drop_y_top:.1f}" '
            f'x2="{x:.1f}" y2="{drop_y_bot:.1f}" '
            f'stroke="{HUB_COLOR}" stroke-width="1" '
            f'stroke-dasharray="2 3" fill="none"/>'
        )

    # --- Layer 3: horizontal bars (on top of drops) ---
    rows = [(HUB, HUB_REVS[0]["t"], [(r["tag"], r["t"]) for r in HUB_REVS], HUB_COLOR)]
    for (name, t), color in zip(CHILDREN, CHILD_COLORS):
        rows.append((name, t, [("@1", t)], color))

    for i, (name, first_t, markers, color) in enumerate(rows):
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

    # --- Layer 4: @-markers on bars, in row color ---
    for i, (name, first_t, markers, color) in enumerate(rows):
        y = y_of(i)
        for tag, t in markers:
            parts.append(
                f'<line x1="{x_of(t):.1f}" y1="{y - 5}" '
                f'x2="{x_of(t):.1f}" y2="{y + 5}" '
                f'stroke="{color}" stroke-width="2"/>'
            )
            parts.append(
                f'<text x="{x_of(t) + 3:.1f}" y="{y - 7}" '
                f'text-anchor="start" fill="{color}" '
                f'font-weight="bold">{tag}</text>'
            )

    # --- Layer 5: dots (hub color) ---
    for rev in HUB_REVS:
        x = x_of(rev["t"])
        for i, (child_name, child_t) in enumerate(CHILDREN, start=1):
            if child_name not in rev["new_links"]:
                continue
            y = y_of(i)
            filled = rev["t"] >= child_t
            if filled:
                parts.append(
                    f'<circle cx="{x:.1f}" cy="{y}" r="5" '
                    f'fill="{HUB_COLOR}" stroke="{HUB_COLOR}" '
                    f'stroke-width="1"/>'
                )
            else:
                parts.append(
                    f'<circle cx="{x:.1f}" cy="{y}" r="5" '
                    f'fill="#fff" stroke="{HUB_COLOR}" '
                    f'stroke-width="2"/>'
                )

    # --- Layer 6: axes and tick labels ---
    parts.append(
        f'<line class="axis" x1="{LEFT_LABEL_W}" y1="{TOP_PAD}" '
        f'x2="{LEFT_LABEL_W}" y2="{TOP_PAD + CHART_H}"/>'
    )
    parts.append(
        f'<line class="axis" x1="{LEFT_LABEL_W}" y1="{TOP_PAD + CHART_H}" '
        f'x2="{LEFT_LABEL_W + CHART_W}" y2="{TOP_PAD + CHART_H}"/>'
    )
    for t in TICK_LABELS:
        x = x_of(t)
        parts.append(
            f'<text class="tick" x="{x:.1f}" y="{TOP_PAD + CHART_H + 15}" '
            f'text-anchor="middle">{hms(t)}</text>'
        )
    parts.append(
        f'<text class="tick" x="{LEFT_LABEL_W + CHART_W / 2:.1f}" '
        f'y="{TOP_PAD + CHART_H + 35}" text-anchor="middle">'
        f'2026-06-16 UTC</text>'
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
    parts.append(
        f'<circle cx="{lx + 280}" cy="{ly - 4}" r="5" fill="{HUB_COLOR}" '
        f'stroke="{HUB_COLOR}"/>'
    )
    parts.append(
        f'<text class="tick" x="{lx + 290}" y="{ly}" text-anchor="start">'
        f'link created; target already existed</text>'
    )

    parts.append('</svg>')

    out = "/collusionwiki/analyses/dse-forward-links/outputs/hub_timeline.svg"
    with open(out, "w") as f:
        f.write("\n".join(parts))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
