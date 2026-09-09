#!/usr/bin/env python3
"""Same node set + edge set as `render_labels_coedit_2d.py`, but the
layout comes from a force-directed spring embedding on the
co-editorship graph itself, not from PCA on the page-profile matrix.

Why: the PCA layout optimises "labels with similar page profiles are
close" — but two labels can share 2 pages (thus have an edge) while
having very different total page vectors (thus placed far apart).
Result: edges of hugely varying length. Force-directed makes
edge-connected nodes attract, so edge lengths become interpretable.

Layout: Fruchterman-Reingold with weighted attraction; PCA(x, y) is
used as the initial position so the family split from row 12 remains a
visible tendency even after relaxation.

Writes:
  outputs/labels_coedit_2d_spring.png
  outputs/labels_coedit_2d_spring.svg
"""
from __future__ import annotations

import colorsys
import math
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_and_plot import (  # noqa: E402
    FAMILY_HUE, FAMILY_ORDER, load_page_family, family_variant_base,
)
from render_labels_coedit_3d import (  # noqa: E402
    MIN_LABEL_REVS, MAX_LABELS_PER_PAGE, MIN_EDGE_WEIGHT,
    cell_rgb, collect, order_columns, rank_scale, load_page_label_counts,
)

REPO_ROOT = HERE.parent.parent
OUT_DIR = HERE / "outputs"


def spring_layout(N, edges, iterations=400, seed_pos=None, rng_seed=1,
                  k_scale=4.0, gravity=0.03):
    """Vectorised Fruchterman-Reingold in pure numpy.

    Bounded by a mild central gravitational term rather than a hard
    frame clip.  Hard clipping puts a line of nodes along the frame
    edge; gravity lets weakly-connected nodes sit close to the boundary
    but without a visible wall.

    `edges` = [(i, j, weight)]; attraction is weight-scaled.
    """
    rng = np.random.default_rng(rng_seed)
    if seed_pos is None:
        pos = rng.normal(scale=0.3, size=(N, 2))
    else:
        pos = seed_pos.astype(float).copy()
        pos += rng.normal(scale=1e-3, size=pos.shape)

    if edges:
        edge_i = np.array([i for i, _, _ in edges])
        edge_j = np.array([j for _, j, _ in edges])
        edge_w = np.array([w for _, _, w in edges], dtype=float)
    else:
        edge_i = np.array([], dtype=int)
        edge_j = np.array([], dtype=int)
        edge_w = np.array([], dtype=float)

    k = k_scale * math.sqrt(1.0 / max(N, 1))
    t_start = 0.15

    for it in range(iterations):
        t = t_start * (1.0 - it / iterations) ** 1.5

        diff = pos[:, None, :] - pos[None, :, :]
        dist2 = (diff ** 2).sum(-1) + 1e-9
        np.fill_diagonal(dist2, np.inf)
        rep_mag = (k * k) / dist2
        rep = (rep_mag[..., None] * diff).sum(axis=1)

        att = np.zeros_like(pos)
        if edge_i.size:
            d_ij = pos[edge_i] - pos[edge_j]
            d = np.sqrt((d_ij ** 2).sum(-1)) + 1e-9
            att_mag = (d * d) / k * edge_w
            att_vec = (att_mag / d)[:, None] * d_ij
            np.add.at(att, edge_i, -att_vec)
            np.add.at(att, edge_j, att_vec)

        # Central gravity — bounds the layout without a hard wall.
        grav = -gravity * pos

        force = rep + att + grav
        fmag = np.sqrt((force ** 2).sum(-1)) + 1e-9
        step = np.minimum(t, fmag)[:, None] * (force / fmag[:, None])
        pos += step

    # Recenter and normalise so the widest axis fills [-1, 1].
    pos = pos - pos.mean(axis=0, keepdims=True)
    span = np.max(np.abs(pos)) or 1.0
    pos = pos / span
    return pos


def spring_layout_3d(N, edges, iterations=400, seed_pos_2d=None,
                     z_target=None, time_weight=0.6,
                     rng_seed=1, k_scale=4.0, gravity=0.03):
    """Same Fruchterman-Reingold but in 3D, with an optional per-node
    z-anchor that pulls each node toward `z_target[i]` on the z axis.

    Setting `time_weight` above ~1 makes z essentially a fixed axis (like
    row 13's approach).  Values between 0.3 and 0.8 preserve graph
    structure while letting cohort onset stratify the cloud along z.
    """
    rng = np.random.default_rng(rng_seed)
    pos = np.zeros((N, 3))
    if seed_pos_2d is not None:
        pos[:, :2] = seed_pos_2d
    else:
        pos[:, :2] = rng.normal(scale=0.3, size=(N, 2))
    if z_target is not None:
        pos[:, 2] = z_target
    else:
        pos[:, 2] = rng.normal(scale=0.3, size=N)
    pos += rng.normal(scale=1e-3, size=pos.shape)

    if edges:
        edge_i = np.array([i for i, _, _ in edges])
        edge_j = np.array([j for _, j, _ in edges])
        edge_w = np.array([w for _, _, w in edges], dtype=float)
    else:
        edge_i = np.array([], dtype=int)
        edge_j = np.array([], dtype=int)
        edge_w = np.array([], dtype=float)

    k = k_scale * math.sqrt(1.0 / max(N, 1))
    t_start = 0.15

    for it in range(iterations):
        t = t_start * (1.0 - it / iterations) ** 1.5

        diff = pos[:, None, :] - pos[None, :, :]     # (N, N, 3)
        dist2 = (diff ** 2).sum(-1) + 1e-9
        np.fill_diagonal(dist2, np.inf)
        rep_mag = (k * k) / dist2
        rep = (rep_mag[..., None] * diff).sum(axis=1)

        att = np.zeros_like(pos)
        if edge_i.size:
            d_ij = pos[edge_i] - pos[edge_j]
            d = np.sqrt((d_ij ** 2).sum(-1)) + 1e-9
            att_mag = (d * d) / k * edge_w
            att_vec = (att_mag / d)[:, None] * d_ij
            np.add.at(att, edge_i, -att_vec)
            np.add.at(att, edge_j, att_vec)

        grav = -gravity * pos

        force = rep + att + grav
        if z_target is not None:
            force[:, 2] += time_weight * (z_target - pos[:, 2])

        fmag = np.sqrt((force ** 2).sum(-1)) + 1e-9
        step = np.minimum(t, fmag)[:, None] * (force / fmag[:, None])
        pos += step

    pos = pos - pos.mean(axis=0, keepdims=True)
    # Normalise each axis independently. x/y get stretched by graph
    # forces to fill a wide plane; z is held near z_target by the
    # anchor. A global max|pos| would squash z flat; per-axis keeps all
    # three visible.
    span = np.max(np.abs(pos), axis=0)
    span[span < 1e-9] = 1.0
    pos = pos / span
    return pos


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page_family = load_page_family()
    page_n_labels = load_page_label_counts()

    per_label_variant, per_label_pages, per_label_times, label_totals, page_labels = collect(page_family)

    kept = [lab for lab, n in label_totals.items()
            if n >= MIN_LABEL_REVS and per_label_variant.get(lab)]
    kept.sort(key=lambda l: (-label_totals[l], l))
    label_index = {lab: i for i, lab in enumerate(kept)}
    kept_set = set(kept)
    print(f"nodes: {len(kept)}")

    non_hub_pages = [pk for pk, nl in page_n_labels.items() if nl <= MAX_LABELS_PER_PAGE]
    page_index = {pk: j for j, pk in enumerate(non_hub_pages)}

    # PCA seed (same as the old 2D render) so the layout starts from the
    # family split — force-directed then improves edge lengths on top.
    X = np.zeros((len(kept), len(non_hub_pages)))
    for i, lab in enumerate(kept):
        for pk, n in per_label_pages[lab].items():
            j = page_index.get(pk)
            if j is not None:
                X[i, j] = math.log1p(n)
    Xc = X - X.mean(axis=0, keepdims=True)
    U, S, _ = np.linalg.svd(Xc, full_matrices=False)
    seed = np.column_stack([rank_scale(U[:, 0] * S[0]),
                            rank_scale(U[:, 1] * S[1])])

    # Layout attraction uses every co-edit pair with weight >= 2, so the
    # springs express meaningful co-editorship rather than one-shot
    # accidents.  Draw set is the same threshold, so what you see is
    # what pulled.
    all_edge_w: dict[tuple[int, int], int] = defaultdict(int)
    for pk, labs in page_labels.items():
        if page_n_labels.get(pk, 0) > MAX_LABELS_PER_PAGE:
            continue
        labs = [lab for lab in labs if lab in kept_set]
        if len(labs) < 2:
            continue
        labs.sort()
        for a, b in combinations(labs, 2):
            all_edge_w[(label_index[a], label_index[b])] += 1
    layout_edges = [(i, j, w) for (i, j), w in all_edge_w.items()
                    if w >= MIN_EDGE_WEIGHT]
    print(f"layout edges (weight >= {MIN_EDGE_WEIGHT}): {len(layout_edges)}")

    # Restrict to nodes that participate in at least one weight->=2 edge.
    # Singletons make the frame edges ugly without adding graph information.
    connected = set()
    for i, j, _ in layout_edges:
        connected.add(i); connected.add(j)
    old_to_new = {old: new for new, old in enumerate(sorted(connected))}
    print(f"nodes in the graph: {len(connected)} "
          f"(dropped {len(kept) - len(connected)} singletons)")

    kept = [kept[old] for old in sorted(connected)]
    layout_edges = [(old_to_new[i], old_to_new[j], w) for i, j, w in layout_edges]
    seed = seed[sorted(connected)]

    pos = spring_layout(len(kept), layout_edges,
                        iterations=250, seed_pos=seed)

    # After the singleton drop the layout edges *are* the draw edges.
    draw_edges = sorted(layout_edges, key=lambda e: e[2])
    print(f"draw edges (weight >= {MIN_EDGE_WEIGHT}): {len(draw_edges)}")

    # Palette + colours (unchanged).
    fam_vars = order_columns(per_label_variant)
    base_hsl = {}
    for fam, vs in fam_vars.items():
        for i, v in enumerate(vs):
            base_hsl[(fam, v)] = family_variant_base(fam, i, len(vs))
    max_cell = max((n for cells in per_label_variant.values()
                    for n in cells.values()), default=1)

    colours = np.zeros((len(kept), 3))
    for i, lab in enumerate(kept):
        cells = per_label_variant[lab]
        (fam, var), n_dom = max(cells.items(), key=lambda kv: kv[1])
        colours[i] = cell_rgb(base_hsl[(fam, var)], n_dom, max_cell)

    max_total = max(label_totals[lab] for lab in kept)
    sizes = np.array(
        [12.0 + 90.0 * math.log1p(label_totals[lab]) / math.log1p(max_total)
         for lab in kept]
    )

    fig, ax = plt.subplots(figsize=(11, 9.5), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    max_w = max(w for _, _, w in draw_edges) if draw_edges else 1
    segs, seg_colours, seg_widths = [], [], []
    for i, j, w in draw_edges:
        segs.append(((pos[i, 0], pos[i, 1]), (pos[j, 0], pos[j, 1])))
        blend = 0.5 * colours[i] + 0.5 * colours[j]
        alpha = 0.15 + 0.55 * math.log1p(w) / math.log1p(max_w)
        seg_colours.append((*blend, alpha))
        seg_widths.append(0.35 + 0.9 * math.log1p(w) / math.log1p(max_w))
    if segs:
        lc = LineCollection(segs, colors=seg_colours, linewidths=seg_widths,
                            capstyle="round", zorder=1)
        ax.add_collection(lc)

    ax.scatter(pos[:, 0], pos[:, 1], c=colours, s=sizes,
               edgecolors=(0, 0, 0, 0.35), linewidths=0.4, zorder=2)

    ax.set_xlabel("spring layout x", fontsize=10, labelpad=6)
    ax.set_ylabel("spring layout y", fontsize=10, labelpad=6)
    ax.tick_params(axis="both", which="major", labelsize=8)
    ax.grid(True, linewidth=0.3, alpha=0.4)
    ax.set_aspect("equal")
    ax.margins(0.02)

    fig.suptitle(
        f"{len(kept):,} agent labels · co-editorship spring layout · z axis collapsed",
        fontsize=13, fontweight="600", y=0.965,
    )
    fig.text(
        0.5, 0.925,
        f"node = label · colour = dominant (family, variant), palette from heatmap 08 · "
        f"layout = Fruchterman-Reingold on {len(layout_edges):,} co-edit pairs (weight ≥ 1) · "
        f"drawn edges = weight ≥ {MIN_EDGE_WEIGHT} ({len(draw_edges):,} shown)",
        ha="center", fontsize=9, color="#555",
    )

    handles = []
    for fam in FAMILY_ORDER:
        if fam not in fam_vars:
            continue
        r, g, b = colorsys.hls_to_rgb(FAMILY_HUE[fam] / 360.0, 0.48, 0.65)
        handles.append(Line2D([0], [0], marker="o", linestyle="",
                              markerfacecolor=(r, g, b),
                              markeredgecolor="none",
                              markersize=9, label=fam))
    ax.legend(handles=handles, loc="lower center",
              bbox_to_anchor=(0.5, -0.09), ncol=4, fontsize=9,
              frameon=True, facecolor="white", edgecolor="#bbb")

    fig.subplots_adjust(top=0.88, bottom=0.12, left=0.08, right=0.97)

    png = OUT_DIR / "labels_coedit_2d_spring.png"
    svg = OUT_DIR / "labels_coedit_2d_spring.svg"
    fig.savefig(png, dpi=180, facecolor="white")
    fig.savefig(svg, facecolor="white")
    print(f"wrote {png}")
    print(f"wrote {svg}")


if __name__ == "__main__":
    main()
