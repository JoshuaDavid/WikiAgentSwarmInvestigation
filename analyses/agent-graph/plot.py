#!/usr/bin/env python3
"""Render the addressing graph as SVG. Pure stdlib (no matplotlib / networkx).

Layout:
- Fruchterman-Reingold spring embedding on the giant component.
- Repulsion computed only between nodes in the same or adjacent grid cells
  (spatial-hash approximation). This keeps each iteration O(n) for reasonably
  uniform layouts.
- Small components are laid out separately and packed to the right.

Encoding:
- Node radius scales with sqrt(total degree).
- Node color = connected-component id (giant component is one solid color;
  small components each get their own color).
- Edge opacity scales with log(edge weight).
- Top-degree hubs are labelled with their handle.
"""
from __future__ import annotations
import json
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"


def load_graph():
    edges = []
    for line in (OUT / "edges.jsonl").open():
        r = json.loads(line)
        edges.append((r["from"], r["to"], r["count"]))
    nodes = {}
    for line in (OUT / "nodes.jsonl").open():
        r = json.loads(line)
        nodes[r["handle"]] = r["out_degree"] + r["in_degree"]
    comps = json.loads((OUT / "components.json").read_text())
    return nodes, edges, comps


def fr_layout(nodes, edges, width, height, iterations=120, seed=1):
    """Fruchterman-Reingold with grid-cell repulsion approximation."""
    rng = random.Random(seed)
    n = len(nodes)
    if n == 0:
        return {}
    area = width * height
    k = math.sqrt(area / n)
    pos = {v: [rng.uniform(0, width), rng.uniform(0, height)] for v in nodes}
    disp = {v: [0.0, 0.0] for v in nodes}
    t0 = min(width, height) / 4.0
    node_set = set(nodes)
    adj = defaultdict(list)
    for a, b, w in edges:
        if a in node_set and b in node_set:
            adj[a].append((b, w))
            adj[b].append((a, w))

    cell = max(k, 1.0)
    for it in range(iterations):
        for v in nodes:
            disp[v][0] = 0.0
            disp[v][1] = 0.0
        grid = defaultdict(list)
        for v, (x, y) in pos.items():
            grid[(int(x // cell), int(y // cell))].append(v)

        for (cx, cy), members in grid.items():
            neighbors = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    neighbors.extend(grid.get((cx + dx, cy + dy), []))
            for v in members:
                px, py = pos[v]
                for u in neighbors:
                    if u == v:
                        continue
                    ux, uy = pos[u]
                    dx = px - ux
                    dy = py - uy
                    d2 = dx * dx + dy * dy
                    if d2 < 0.01:
                        dx = (rng.random() - 0.5) * 0.1
                        dy = (rng.random() - 0.5) * 0.1
                        d2 = dx * dx + dy * dy + 1e-6
                    d = math.sqrt(d2)
                    force = k * k / d
                    disp[v][0] += dx / d * force
                    disp[v][1] += dy / d * force

        seen = set()
        for v, nbrs in adj.items():
            for u, w in nbrs:
                key = (v, u) if v < u else (u, v)
                if key in seen:
                    continue
                seen.add(key)
                px, py = pos[v]
                ux, uy = pos[u]
                dx = px - ux
                dy = py - uy
                d = math.sqrt(dx * dx + dy * dy) + 1e-6
                weight = 1.0 + math.log1p(w)
                force = (d * d) / k * weight
                fx = dx / d * force
                fy = dy / d * force
                disp[v][0] -= fx
                disp[v][1] -= fy
                disp[u][0] += fx
                disp[u][1] += fy

        t = t0 * (1.0 - it / iterations)
        for v in nodes:
            dx, dy = disp[v]
            dlen = math.sqrt(dx * dx + dy * dy) + 1e-6
            step = min(dlen, t)
            pos[v][0] += dx / dlen * step
            pos[v][1] += dy / dlen * step
            pos[v][0] = min(width - 5, max(5, pos[v][0]))
            pos[v][1] = min(height - 5, max(5, pos[v][1]))
    return {v: (x, y) for v, (x, y) in pos.items()}


def small_component_layout(members, cx, cy, radius):
    n = len(members)
    if n == 1:
        return {members[0]: (cx, cy)}
    return {
        m: (cx + radius * math.cos(2 * math.pi * i / n),
            cy + radius * math.sin(2 * math.pi * i / n))
        for i, m in enumerate(members)
    }


PALETTE = [
    "#2b7ce9",  # giant component
    "#e15759",
    "#f28e2b",
    "#59a14f",
    "#b07aa1",
    "#76b7b2",
    "#edc948",
    "#ff9da7",
    "#9c755f",
    "#bab0ac",
    "#4e79a7",
    "#af7aa1",
    "#d37295",
]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def render(nodes_deg, edges, comps):
    W_TOTAL = 1800
    H = 1200
    GIANT_W = 1400
    SMALL_X = 1420

    comp_color = {}
    for i, c in enumerate(comps):
        color = PALETTE[i % len(PALETTE)]
        for m in c["members"]:
            comp_color[m] = color

    giant = comps[0]["members"]
    giant_set = set(giant)

    pos = fr_layout(giant, edges, GIANT_W, H, iterations=120)

    small_comps = comps[1:]
    slot_h = H / max(len(small_comps), 1)
    slot_r = min(slot_h * 0.35, 55)
    for i, c in enumerate(small_comps):
        cx = SMALL_X + 180
        cy = slot_h * (i + 0.5)
        pos.update(small_component_layout(c["members"], cx, cy, slot_r))

    max_deg = max(nodes_deg.values()) or 1
    max_w = max((w for _, _, w in edges), default=1)

    def node_r(v):
        d = nodes_deg.get(v, 0)
        return 2.0 + 6.0 * math.sqrt(d / max_deg)

    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_TOTAL} {H}" '
                 f'font-family="Helvetica,Arial,sans-serif">')
    parts.append(f'<rect width="{W_TOTAL}" height="{H}" fill="#ffffff"/>')

    parts.append('<text x="20" y="30" font-size="20" font-weight="600" fill="#222">'
                 'Agent-to-agent addressing graph — 15,700 (from,to) pairs across 4 ProWiki wikis'
                 '</text>')
    parts.append(f'<text x="20" y="52" font-size="14" fill="#555">'
                 f'{len(nodes_deg)} handles, {len(edges)} unique directed edges, '
                 f'{len(comps)} connected components. '
                 'Giant component (blue) holds 1,374 of 1,403 handles.'
                 '</text>')

    parts.append(f'<line x1="{GIANT_W}" y1="0" x2="{GIANT_W}" y2="{H}" '
                 f'stroke="#dddddd" stroke-width="1"/>')
    parts.append(f'<text x="{SMALL_X}" y="30" font-size="16" font-weight="600" fill="#333">'
                 'Small components'
                 '</text>')

    for a, b, w in edges:
        if a not in pos or b not in pos:
            continue
        if a in giant_set and b not in giant_set:
            continue
        if b in giant_set and a not in giant_set:
            continue
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        opacity = 0.06 + 0.45 * math.log1p(w) / math.log1p(max_w)
        width_px = 0.4 + 1.2 * math.log1p(w) / math.log1p(max_w)
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="#666" stroke-width="{width_px:.2f}" '
                     f'stroke-opacity="{opacity:.3f}"/>')

    for v, (x, y) in pos.items():
        r = node_r(v)
        color = comp_color.get(v, "#888")
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" '
                     f'fill="{color}" fill-opacity="0.85" '
                     f'stroke="#222" stroke-width="0.3"/>')

    top_hubs = sorted(nodes_deg.items(), key=lambda kv: -kv[1])[:18]
    for v, _ in top_hubs:
        if v not in pos:
            continue
        x, y = pos[v]
        parts.append(
            f'<text x="{x + 6:.1f}" y="{y + 3:.1f}" font-size="10.5" '
            f'fill="#111">{esc(v)}</text>')

    for i, c in enumerate(comps[1:]):
        cx = SMALL_X + 180
        cy = slot_h * (i + 0.5)
        color = PALETTE[(i + 1) % len(PALETTE)]
        parts.append(
            f'<text x="{SMALL_X}" y="{cy - slot_r - 4:.1f}" font-size="11" '
            f'fill="#333" font-weight="600">size {len(c["members"])}</text>')
        for m in c["members"]:
            x, y = pos[m]
            parts.append(
                f'<text x="{x + 5:.1f}" y="{y + 3:.1f}" font-size="9" '
                f'fill="#222">{esc(m)}</text>')

    parts.append('<g transform="translate(20,1120)" font-size="11" fill="#333">')
    parts.append('<text y="0" font-weight="600">Legend</text>')
    parts.append('<circle cx="10" cy="16" r="2" fill="#2b7ce9"/>'
                 '<text x="22" y="19">low degree</text>')
    parts.append('<circle cx="140" cy="16" r="5" fill="#2b7ce9"/>'
                 '<text x="152" y="19">medium degree</text>')
    parts.append('<circle cx="290" cy="16" r="8" fill="#2b7ce9"/>'
                 '<text x="302" y="19">hub (labelled if top-18)</text>')
    parts.append('<line x1="500" y1="16" x2="560" y2="16" stroke="#666" '
                 'stroke-width="0.5" stroke-opacity="0.15"/>'
                 '<text x="568" y="19">1 msg edge</text>')
    parts.append('<line x1="680" y1="16" x2="740" y2="16" stroke="#666" '
                 'stroke-width="1.5" stroke-opacity="0.5"/>'
                 '<text x="748" y="19">many-msg edge</text>')
    parts.append('</g>')

    parts.append('</svg>')
    return "\n".join(parts)


def main():
    nodes, edges, comps = load_graph()
    svg = render(nodes, edges, comps)
    out = OUT / "graph.svg"
    out.write_text(svg)
    print(f"wrote {out} ({len(svg):,} bytes)")


if __name__ == "__main__":
    main()
