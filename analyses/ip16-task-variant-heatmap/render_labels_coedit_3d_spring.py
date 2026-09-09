#!/usr/bin/env python3
"""Row 12 reborn on the spring layout: same 514-node co-editorship
graph as `render_labels_coedit_2d_spring.py`, with the time axis
brought back on z.

  x, y = Fruchterman-Reingold on the (co-edited >= 2 non-hub pages)
         graph, seeded from PCA and bounded by mild central gravity
  z    = percentile-rank of the label's mean UTC write time, tick
         labels showing the corresponding calendar dates
  edges= the same 1,315 co-editorship pairs, drawn as 3D lines
  size = log(total revs)
  hue  = family, shade = dominant variant, palette from heatmap 08

Writes:
  outputs/labels_coedit_3d_spring.mp4
  outputs/labels_coedit_3d_spring.gif
"""
from __future__ import annotations

import colorsys
import datetime as dt
import math
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Line3DCollection

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_and_plot import (  # noqa: E402
    FAMILY_HUE, FAMILY_ORDER, load_page_family, family_variant_base,
)
from render_labels_coedit_3d import (  # noqa: E402
    MIN_LABEL_REVS, MAX_LABELS_PER_PAGE, MIN_EDGE_WEIGHT,
    cell_rgb, collect, order_columns, rank_scale, load_page_label_counts,
)
from render_labels_coedit_2d_spring import spring_layout  # noqa: E402

REPO_ROOT = HERE.parent.parent
OUT_DIR = HERE / "outputs"


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

    non_hub_pages = [pk for pk, nl in page_n_labels.items() if nl <= MAX_LABELS_PER_PAGE]
    page_index = {pk: j for j, pk in enumerate(non_hub_pages)}

    # PCA seed for spring layout.
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

    edge_w: dict[tuple[int, int], int] = defaultdict(int)
    for pk, labs in page_labels.items():
        if page_n_labels.get(pk, 0) > MAX_LABELS_PER_PAGE:
            continue
        labs = [lab for lab in labs if lab in kept_set]
        if len(labs) < 2:
            continue
        labs.sort()
        for a, b in combinations(labs, 2):
            edge_w[(label_index[a], label_index[b])] += 1
    layout_edges = [(i, j, w) for (i, j), w in edge_w.items() if w >= MIN_EDGE_WEIGHT]

    connected = sorted({i for i, _, _ in layout_edges} | {j for _, j, _ in layout_edges})
    old_to_new = {old: new for new, old in enumerate(connected)}
    kept = [kept[old] for old in connected]
    layout_edges = [(old_to_new[i], old_to_new[j], w) for i, j, w in layout_edges]
    seed = seed[connected]
    print(f"nodes: {len(kept)}  edges (weight >= {MIN_EDGE_WEIGHT}): {len(layout_edges)}")

    pos = spring_layout(len(kept), layout_edges,
                        iterations=400, seed_pos=seed)
    # After spring_layout, pos is normalised so max|pos| == 1. Give it
    # roughly the same span as z so neither axis dominates the box.
    pos = pos * 2.5

    mean_times = np.array([np.mean(per_label_times[lab]) for lab in kept])
    # z centred on 0 with a span comparable to x, y.
    z = rank_scale(mean_times) * 2.5

    # Colours + sizes.
    fam_vars = order_columns(per_label_variant)
    base_hsl = {}
    for fam, vs in fam_vars.items():
        for i, v in enumerate(vs):
            base_hsl[(fam, v)] = family_variant_base(fam, i, len(vs))
    max_cell = max((n for cells in per_label_variant.values()
                    for n in cells.values()), default=1)

    colours = np.zeros((len(kept), 3))
    dom_fam = []
    for i, lab in enumerate(kept):
        cells = per_label_variant[lab]
        (fam, var), n_dom = max(cells.items(), key=lambda kv: kv[1])
        colours[i] = cell_rgb(base_hsl[(fam, var)], n_dom, max_cell)
        dom_fam.append(fam)

    max_total = max(label_totals[lab] for lab in kept)
    sizes = np.array(
        [14.0 + 100.0 * math.log1p(label_totals[lab]) / math.log1p(max_total)
         for lab in kept]
    )

    x = pos[:, 0]
    y = pos[:, 1]

    fig = plt.figure(figsize=(11, 8.5), dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Edges as 3D line segments.
    max_w = max(w for _, _, w in layout_edges) if layout_edges else 1
    segs, seg_colours, seg_widths = [], [], []
    for i, j, w in sorted(layout_edges, key=lambda e: e[2]):
        segs.append(((x[i], y[i], z[i]), (x[j], y[j], z[j])))
        blend = 0.5 * colours[i] + 0.5 * colours[j]
        alpha = 0.18 + 0.55 * math.log1p(w) / math.log1p(max_w)
        seg_colours.append((*blend, alpha))
        seg_widths.append(0.4 + 1.0 * math.log1p(w) / math.log1p(max_w))
    if segs:
        lc = Line3DCollection(segs, colors=seg_colours, linewidths=seg_widths)
        ax.add_collection3d(lc)

    z_floor = z.min() - 0.15
    shadow_c = np.concatenate(
        [colours * 0.4 + 0.6, np.full((len(colours), 1), 0.20)], axis=1,
    )
    ax.scatter(x, y, np.full_like(z, z_floor),
               c=shadow_c, s=sizes * 0.55,
               edgecolors="none", depthshade=False)

    scatter = ax.scatter(
        x, y, z, c=colours, s=sizes,
        edgecolors=(0, 0, 0, 0.35), linewidths=0.4, depthshade=True,
    )

    # z-axis tick labels in real UTC dates via percentile inverse.
    sorted_t = np.sort(mean_times)
    z_ticks = np.linspace(-2.4, 2.4, 5)
    tick_dates = []
    for zt in z_ticks:
        frac = (zt + 2.5) / 5.0
        idx = min(len(sorted_t) - 1, max(0, int(round(frac * (len(sorted_t) - 1)))))
        d = dt.datetime.utcfromtimestamp(sorted_t[idx])
        tick_dates.append(d.strftime("%b %d"))
    ax.set_zticks(z_ticks)
    ax.set_zticklabels(tick_dates)

    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_edgecolor((0.85, 0.85, 0.85))
        pane.set_facecolor((1, 1, 1, 0.7))
    ax.grid(True, linewidth=0.3, alpha=0.4)

    ax.set_xlabel("spring layout x", fontsize=9, labelpad=4)
    ax.set_ylabel("spring layout y", fontsize=9, labelpad=4)
    ax.set_zlabel("mean write time (percentile rank)", fontsize=9, labelpad=4)
    ax.tick_params(axis="both", which="major", labelsize=7)

    fig.suptitle(
        f"{len(kept):,} labels · co-editorship spring layout · z = mean write time",
        fontsize=13, fontweight="600", y=0.965,
    )
    fig.text(
        0.5, 0.925,
        f"node = label · colour = dominant (family, variant), palette from heatmap 08 · "
        f"layout = Fruchterman-Reingold on {len(layout_edges):,} co-edit pairs (weight ≥ 2)",
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
              bbox_to_anchor=(0.5, -0.06), ncol=4, fontsize=8,
              frameon=True, facecolor="white", edgecolor="#bbb")

    ax.set_box_aspect((1.2, 1.2, 1.2))
    ax.view_init(elev=18, azim=0)

    n_frames = 120

    def update(frame):
        azim = (frame / n_frames) * 360.0
        elev = 18 + 6 * math.sin(2 * math.pi * frame / n_frames)
        ax.view_init(elev=elev, azim=azim)
        return (scatter,)

    ani = animation.FuncAnimation(
        fig, update, frames=n_frames, interval=40, blit=False,
    )

    mp4 = OUT_DIR / "labels_coedit_3d_spring.mp4"
    gif = OUT_DIR / "labels_coedit_3d_spring.gif"

    print(f"rendering {mp4} ...")
    writer = animation.FFMpegWriter(fps=25, bitrate=4400, codec="libx264",
                                    extra_args=["-pix_fmt", "yuv420p",
                                                "-movflags", "+faststart"])
    ani.save(str(mp4), writer=writer, dpi=140)
    print(f"wrote {mp4}")

    print(f"rendering {gif} ...")
    ani2 = animation.FuncAnimation(
        fig, update, frames=n_frames // 2, interval=80, blit=False,
    )
    ani2.save(str(gif), writer=animation.PillowWriter(fps=15), dpi=80)
    print(f"wrote {gif}")


if __name__ == "__main__":
    main()
