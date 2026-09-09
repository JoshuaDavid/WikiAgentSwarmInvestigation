#!/usr/bin/env python3
"""Flat 2D projection of the row-12 co-editorship render (z-axis
collapsed). Same node set, same palette, same edge set, same (x, y)
positions from percentile-rank PCA on the (label x non-hub-page)
log-scaled matrix.

Writes:
  outputs/labels_coedit_2d.png    high-res raster
  outputs/labels_coedit_2d.svg    same figure as vector
"""
from __future__ import annotations

import colorsys
import math
import sys
from collections import OrderedDict, defaultdict
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
    R_TOKEN, FAST_FOLLOW_MARKERS, HUB_FAMILIES, FAST_FOLLOW_FAMILIES,
    FAMILY_HUE, FAMILY_ORDER, VOCAB_PAGE_ID,
    load_page_family, match_archive_instances, family_variant_base,
)
from render_labels_coedit_3d import (  # noqa: E402
    MIN_LABEL_REVS, MAX_LABELS_PER_PAGE, MIN_EDGE_WEIGHT,
    cell_rgb, collect, order_columns, rank_scale, load_page_label_counts,
)

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
    print(f"nodes: {len(kept)}")

    non_hub_pages = [pk for pk, nl in page_n_labels.items() if nl <= MAX_LABELS_PER_PAGE]
    page_index = {pk: j for j, pk in enumerate(non_hub_pages)}

    X = np.zeros((len(kept), len(non_hub_pages)))
    for i, lab in enumerate(kept):
        for pk, n in per_label_pages[lab].items():
            j = page_index.get(pk)
            if j is not None:
                X[i, j] = math.log1p(n)

    Xc = X - X.mean(axis=0, keepdims=True)
    U, S, _ = np.linalg.svd(Xc, full_matrices=False)
    coords2 = U[:, :2] * S[:2]
    x = rank_scale(coords2[:, 0])
    y = rank_scale(coords2[:, 1])

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
    edges = [(i, j, w) for (i, j), w in edge_w.items() if w >= MIN_EDGE_WEIGHT]
    edges.sort(key=lambda e: e[2])
    print(f"edges: {len(edges)}")

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
        [12.0 + 90.0 * math.log1p(label_totals[lab]) / math.log1p(max_total)
         for lab in kept]
    )

    fig, ax = plt.subplots(figsize=(11, 9.5), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    max_w = max(w for _, _, w in edges) if edges else 1
    segs = []
    seg_colours = []
    seg_widths = []
    for i, j, w in edges:
        segs.append(((x[i], y[i]), (x[j], y[j])))
        blend = 0.5 * colours[i] + 0.5 * colours[j]
        alpha = 0.10 + 0.55 * math.log1p(w) / math.log1p(max_w)
        seg_colours.append((*blend, alpha))
        seg_widths.append(0.35 + 0.9 * math.log1p(w) / math.log1p(max_w))
    if segs:
        lc = LineCollection(segs, colors=seg_colours, linewidths=seg_widths,
                            capstyle="round", zorder=1)
        ax.add_collection(lc)

    ax.scatter(x, y, c=colours, s=sizes,
               edgecolors=(0, 0, 0, 0.35), linewidths=0.4, zorder=2)

    ax.set_xlabel("PCA[0] of label's page profile (percentile rank)",
                  fontsize=10, labelpad=6)
    ax.set_ylabel("PCA[1] of label's page profile (percentile rank)",
                  fontsize=10, labelpad=6)
    ax.tick_params(axis="both", which="major", labelsize=8)
    ax.grid(True, linewidth=0.3, alpha=0.5)
    ax.set_aspect("equal")
    ax.margins(0.02)

    fig.suptitle(
        f"{len(kept):,} agent labels · flattened co-editorship (z axis collapsed)",
        fontsize=13, fontweight="600", y=0.965,
    )
    fig.text(0.5, 0.925,
             f"node = label · colour = dominant (family, variant), palette from heatmap 08 · "
             f"edge = co-edited ≥ {MIN_EDGE_WEIGHT} non-hub pages ({len(edges):,} edges)",
             ha="center", fontsize=9, color="#555")

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

    fig.subplots_adjust(top=0.88, bottom=0.12, left=0.10, right=0.96)

    png = OUT_DIR / "labels_coedit_2d.png"
    svg = OUT_DIR / "labels_coedit_2d.svg"
    fig.savefig(png, dpi=180, facecolor="white")
    fig.savefig(svg, facecolor="white")
    print(f"wrote {png}")
    print(f"wrote {svg}")


if __name__ == "__main__":
    main()
