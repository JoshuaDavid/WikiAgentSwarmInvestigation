"""Render a per-hub timeline SVG with all internal and external link events.

For a chosen hub page:
- Top row is the hub. Every hub revision is a tick + `@N` label on that bar.
- Rows below are every distinct wiki page the hub ever links to (union of
  wiki.cgi?id= targets across all hub revisions), ordered by their own
  first-write time. Pages never observed as their own revision get a row
  label with no bar.
- Below the hub bar, at each revision that creates a new internal link
  (wiki.cgi?id= target absent from all prior hub revisions), a downward
  triangle marks the moment. A dashed drop falls from that point to each
  new target's row and lands on a circle: open = target didn't exist at
  that moment, filled = it did.
- Above the hub bar, at each revision that creates a new external link
  (URL not on wikiservice.at, absent from prior hub revisions), an upward
  triangle marks the moment. A dashed line rises to a stack of host labels
  listing every new host at that revision.

Style is monochrome: dark bars, gray dashed drops, open/filled circles.

Usage:
    python render_hub_v2.py <HubName> [out.svg]
"""
import json
import re
import sys
from datetime import datetime, timedelta
from urllib.parse import urlparse

PROWIKI = "/collusionwiki/agent-logs/prowiki/revisions.jsonl"
WIKI_CGI_ID = re.compile(
    r'wikiservice\.at/dse/wiki\.cgi\?[^\s\]"\)]*?\bid=([A-Za-z0-9_/\-]+)'
)
URL_RE = re.compile(r'https?://[^\s\]"\)]+')

BAR_COLOR = "#222"
DROP_COLOR = "#777"
TRI_COLOR = "#222"
HOST_LABEL_COLOR = "#333"
GRID_COLOR = "#f0f0f0"
AXIS_COLOR = "#333"


def parse(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def load_all():
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
                                    "label": r.get("label"),
                                    "seq": r.get("seq")}
    return first_rev


def load_hub_revs(hub_name):
    revs = []
    with open(PROWIKI) as f:
        for line in f:
            r = json.loads(line)
            if r.get("wiki") != "dse" or r.get("name") != hub_name:
                continue
            t = r.get("write_date")
            if not t:
                continue
            body = r.get("body") or ""
            revs.append({
                "t": parse(t),
                "seq": r["seq"],
                "body": body,
                "internals": set(WIKI_CGI_ID.findall(body)) - {hub_name},
                "external_urls": {u for u in URL_RE.findall(body)
                                    if "wikiservice.at" not in u},
                "label": r.get("label"),
            })
    revs.sort(key=lambda r: r["t"])
    prev_int, prev_ext = set(), set()
    for r in revs:
        r["new_internals"] = sorted(r["internals"] - prev_int)
        new_ext = r["external_urls"] - prev_ext
        r["new_external_urls"] = new_ext
        r["new_hosts"] = sorted({urlparse(u).hostname for u in new_ext
                                    if urlparse(u).hostname})
        prev_int |= r["internals"]
        prev_ext |= r["external_urls"]
    return revs


def build(hub_name, out_path):
    first_rev = load_all()
    hub_revs = load_hub_revs(hub_name)
    if not hub_revs:
        raise SystemExit(f"No hub revisions for {hub_name}")

    # Union of all internal targets ever linked from this hub.
    all_internals = set()
    for r in hub_revs:
        all_internals |= r["internals"]

    # Row order for children: by first_write time if known, else after all.
    def sort_key(name):
        if name in first_rev:
            return (0, first_rev[name]["t"])
        return (1, name)
    children = sorted(all_internals, key=sort_key)

    # X range covers the hub's earliest rev to the latest between hub revs
    # and children's first-write.
    times = [r["t"] for r in hub_revs]
    for c in children:
        if c in first_rev:
            times.append(first_rev[c]["t"])
    lo, hi = min(times), max(times)
    span = hi - lo
    pad = timedelta(seconds=max(300, span.total_seconds() * 0.06))
    x_start = lo - pad
    x_end = hi + pad

    # Reserve top space for external host labels. Compute how much room we
    # need: the tallest stack of new_hosts across revisions.
    max_hosts = max((len(r["new_hosts"]) for r in hub_revs), default=0)
    HOST_LINE_H = 12
    TOP_LABEL_BLOCK = 12 + max_hosts * HOST_LINE_H + 12  # padding + lines + gap

    LEFT_LABEL_W = 340
    RIGHT_PAD = 20
    TOP_PAD = 20 + TOP_LABEL_BLOCK
    ROW_H = 32
    CHART_W = 780
    n_rows = 1 + len(children)
    CHART_H = n_rows * ROW_H
    SVG_W = LEFT_LABEL_W + CHART_W + RIGHT_PAD
    SVG_H = TOP_PAD + CHART_H + 70

    def x_of(t):
        s = (x_end - x_start).total_seconds()
        return LEFT_LABEL_W + (t - x_start).total_seconds() / s * CHART_W

    def y_of(row):
        return TOP_PAD + row * ROW_H + ROW_H / 2

    # X tick step: 5-8 ticks target.
    span_s = (x_end - x_start).total_seconds()
    for step_s in [300, 600, 900, 1800, 3600, 7200, 14400]:
        if span_s / step_s <= 8:
            tick_step_s = step_s
            break
    else:
        tick_step_s = 43200
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

    # Grid
    for t in tick_times:
        x = x_of(t)
        parts.append(
            f'<line x1="{x:.1f}" y1="{TOP_PAD}" x2="{x:.1f}" '
            f'y2="{TOP_PAD + CHART_H}" stroke="{GRID_COLOR}" '
            f'stroke-width="1"/>'
        )

    # --- Drops (drawn first so bars cover them) ---
    hub_y = y_of(0)
    for r in hub_revs:
        if not r["new_internals"]:
            continue
        x = x_of(r["t"])
        for target in r["new_internals"]:
            if target not in [None] + children:  # noop; sanity
                pass
            try:
                child_row = 1 + children.index(target)
            except ValueError:
                continue
            y_target = y_of(child_row)
            parts.append(
                f'<line x1="{x:.1f}" y1="{hub_y + 5:.1f}" '
                f'x2="{x:.1f}" y2="{y_target:.1f}" '
                f'stroke="{DROP_COLOR}" stroke-width="1.2" '
                f'stroke-dasharray="4 3" fill="none"/>'
            )

    # --- Bars ---
    # Hub bar spans from first hub rev to right edge.
    parts.append(
        f'<text x="{LEFT_LABEL_W - 8}" y="{hub_y + 4}" text-anchor="end" '
        f'fill="{BAR_COLOR}" font-weight="bold">{hub_name}</text>'
    )
    parts.append(
        f'<line x1="{x_of(hub_revs[0]["t"]):.1f}" y1="{hub_y}" '
        f'x2="{LEFT_LABEL_W + CHART_W:.1f}" y2="{hub_y}" '
        f'stroke="{BAR_COLOR}" stroke-width="3"/>'
    )
    # Child bars.
    for i, name in enumerate(children, start=1):
        y = y_of(i)
        parts.append(
            f'<text x="{LEFT_LABEL_W - 8}" y="{y + 4}" text-anchor="end" '
            f'fill="{BAR_COLOR}">{name}</text>'
        )
        if name in first_rev:
            x1 = x_of(first_rev[name]["t"])
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y}" '
                f'x2="{LEFT_LABEL_W + CHART_W:.1f}" y2="{y}" '
                f'stroke="{BAR_COLOR}" stroke-width="2.5"/>'
            )
            # @1 marker.
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y - 4}" x2="{x1:.1f}" '
                f'y2="{y + 4}" stroke="{BAR_COLOR}" stroke-width="2"/>'
            )
            parts.append(
                f'<text x="{x1 + 3:.1f}" y="{y - 6}" text-anchor="start" '
                f'fill="{BAR_COLOR}" font-weight="bold">@1</text>'
            )

    # --- @N markers on hub bar (above the line) ---
    for r in hub_revs:
        x = x_of(r["t"])
        parts.append(
            f'<line x1="{x:.1f}" y1="{hub_y - 5}" x2="{x:.1f}" '
            f'y2="{hub_y + 5}" stroke="{BAR_COLOR}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{x + 3:.1f}" y="{hub_y - 7}" text-anchor="start" '
            f'fill="{BAR_COLOR}" font-weight="bold">@{r["seq"]}</text>'
        )

    # --- Bottom triangles: revs with new internal links ---
    def down_triangle(x, y_top):
        # Apex points down; base sits on the bar.
        return (f'<polygon points="{x-4:.1f},{y_top:.1f} '
                f'{x+4:.1f},{y_top:.1f} {x:.1f},{y_top + 7:.1f}" '
                f'fill="{TRI_COLOR}" stroke="{TRI_COLOR}"/>')

    for r in hub_revs:
        if r["new_internals"]:
            parts.append(down_triangle(x_of(r["t"]), hub_y + 2))

    # --- Top triangles + dashed up-lines + host labels ---
    def up_triangle(x, y_bot):
        # Apex points up; base sits on the bar.
        return (f'<polygon points="{x-4:.1f},{y_bot:.1f} '
                f'{x+4:.1f},{y_bot:.1f} {x:.1f},{y_bot - 7:.1f}" '
                f'fill="{TRI_COLOR}" stroke="{TRI_COLOR}"/>')

    for r in hub_revs:
        if not r["new_hosts"]:
            continue
        x = x_of(r["t"])
        # Triangle apex is at (x, hub_y - 9). Dashed line goes up from apex
        # to the top of the label block.
        apex_y = hub_y - 9
        # Compute label block: stack hosts from top down; place lowest label
        # just above the dashed line.
        n = len(r["new_hosts"])
        label_bottom_y = hub_y - 18  # a few px above the triangle apex
        label_top_y = label_bottom_y - (n - 1) * HOST_LINE_H
        # Dashed line
        parts.append(
            f'<line x1="{x:.1f}" y1="{apex_y - 1:.1f}" '
            f'x2="{x:.1f}" y2="{label_bottom_y + 2:.1f}" '
            f'stroke="{HOST_LABEL_COLOR}" stroke-width="1" '
            f'stroke-dasharray="3 2"/>'
        )
        # Labels stacked
        for i, host in enumerate(r["new_hosts"]):
            y = label_top_y + i * HOST_LINE_H
            parts.append(
                f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
                f'fill="{HOST_LABEL_COLOR}" font-size="10">{host}</text>'
            )
        # Triangle
        parts.append(up_triangle(x, hub_y - 2))

    # --- Circles at each internal-link creation ---
    for r in hub_revs:
        x = x_of(r["t"])
        for target in r["new_internals"]:
            try:
                child_row = 1 + children.index(target)
            except ValueError:
                continue
            y = y_of(child_row)
            existed = (target in first_rev
                       and first_rev[target]["t"] <= r["t"])
            if existed:
                parts.append(
                    f'<circle cx="{x:.1f}" cy="{y}" r="4.5" '
                    f'fill="{BAR_COLOR}" stroke="{BAR_COLOR}" '
                    f'stroke-width="1"/>'
                )
            else:
                parts.append(
                    f'<circle cx="{x:.1f}" cy="{y}" r="4.5" '
                    f'fill="#fff" stroke="{BAR_COLOR}" stroke-width="1.8"/>'
                )

    # --- Axes and tick labels ---
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
    date_span = f"{x_start.strftime('%Y-%m-%d')} UTC"
    if x_start.date() != x_end.date():
        date_span = (f"{x_start.strftime('%Y-%m-%d')} -> "
                     f"{x_end.strftime('%Y-%m-%d')} UTC")
    parts.append(
        f'<text x="{LEFT_LABEL_W + CHART_W / 2:.1f}" '
        f'y="{TOP_PAD + CHART_H + 35}" text-anchor="middle" '
        f'fill="{AXIS_COLOR}">{date_span}</text>'
    )

    # Legend
    lx = LEFT_LABEL_W + 20
    ly = TOP_PAD + CHART_H + 55
    parts.append(down_triangle(lx, ly - 4))
    parts.append(
        f'<text x="{lx + 10}" y="{ly}" fill="{AXIS_COLOR}" font-size="11">'
        f'new internal link at this rev</text>'
    )
    parts.append(up_triangle(lx + 240, ly + 3))
    parts.append(
        f'<text x="{lx + 250}" y="{ly}" fill="{AXIS_COLOR}" font-size="11">'
        f'new external link (host labeled above)</text>'
    )
    parts.append(
        f'<circle cx="{lx + 520}" cy="{ly - 4}" r="4.5" fill="#fff" '
        f'stroke="{BAR_COLOR}" stroke-width="1.8"/>'
    )
    parts.append(
        f'<text x="{lx + 530}" y="{ly}" fill="{AXIS_COLOR}" font-size="11">'
        f'target didn\'t exist yet</text>'
    )
    parts.append(
        f'<circle cx="{lx + 680}" cy="{ly - 4}" r="4.5" fill="{BAR_COLOR}" '
        f'stroke="{BAR_COLOR}"/>'
    )
    parts.append(
        f'<text x="{lx + 690}" y="{ly}" fill="{AXIS_COLOR}" font-size="11">'
        f'target existed</text>'
    )

    parts.append('</svg>')
    with open(out_path, "w") as f:
        f.write("\n".join(parts))
    print(f"wrote {out_path}  ({len(children)} internal targets, "
          f"{len(hub_revs)} hub revs)")


if __name__ == "__main__":
    hub = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else (
        f"/collusionwiki/analyses/dse-forward-links/outputs/hub_v2_{hub}.svg"
    )
    build(hub, out)
