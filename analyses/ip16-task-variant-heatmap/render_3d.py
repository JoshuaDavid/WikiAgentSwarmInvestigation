#!/usr/bin/env python3
"""Animated 3D scatter of the (ip16 x variant) cells from
`08_ip16_task_variant_heatmap.svg`, one sphere per non-zero cell.

Placement:
  x, y = PCA[0:2] of the /16's log-scaled variant profile
         (so /16s with similar variant fingerprints cluster in x-y).
  z    = variant column index in the same order the heatmap uses
         (family blocks: archive, fast-follow, sec, vocab).

Colour re-uses `family_variant_base` + `cell_color` from
`build_and_plot.py` so the palette matches the heatmap exactly:
hue = task family, shade = variant within family, saturation/lightness
scaled by log(cell revs).

Sphere radius scales with log(cell revs).

Writes:
  outputs/ip16_task_variant_clusters_3d.mp4
  outputs/ip16_task_variant_clusters_3d.gif   (lower-res preview)

Rerun with:
    python3 analyses/ip16-task-variant-heatmap/render_3d.py
"""
from __future__ import annotations

import colorsys
import csv
import math
from collections import OrderedDict, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "outputs"
TSV = OUT_DIR / "ip16_variant.tsv"

# --- palette (must match build_and_plot.py) ----------------------------------

FAMILY_HUE = {
    "archive-item-research-bench": 210,
    "fast-follow-question-bench":   15,
    "sec-regcf-ma-cache":          140,
    "vocab-puzzle-refs":           285,
}
FAMILY_ORDER = [
    "archive-item-research-bench",
    "fast-follow-question-bench",
    "sec-regcf-ma-cache",
    "vocab-puzzle-refs",
]


def family_variant_base(family: str, variant_idx: int, variant_n: int):
    hue = FAMILY_HUE[family]
    if variant_n <= 1:
        return (hue, 0.65, 0.48)
    frac = variant_idx / (variant_n - 1)
    return (hue + (frac - 0.5) * 16.0,
            0.55 + (1 - abs(frac - 0.5) * 2) * 0.20,
            0.30 + frac * 0.42)


def cell_rgb(base, count: int, max_count: int):
    if count <= 0:
        return (0.98, 0.98, 0.98)
    frac = math.log1p(count) / math.log1p(max_count)
    hue, sat, light_saturated = base
    light = 0.94 - (0.94 - light_saturated) * frac
    sat_eff = 0.25 + (sat - 0.25) * frac
    r, g, b = colorsys.hls_to_rgb((hue % 360) / 360.0, light, sat_eff)
    return (r, g, b)


# --- data --------------------------------------------------------------------

def load_cells():
    cells = []
    with TSV.open() as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            cells.append((row["ip16"], row["task"], row["variant"], int(row["revisions"])))
    return cells


def order_variants(cells):
    variant_totals = defaultdict(int)
    for _ip, fam, var, n in cells:
        variant_totals[(fam, var)] += n
    fam_vars: "OrderedDict[str, list[str]]" = OrderedDict()
    for fam in FAMILY_ORDER:
        vs = sorted([v for (f, v) in variant_totals if f == fam],
                    key=lambda v: (-variant_totals[(fam, v)], v))
        if vs:
            fam_vars[fam] = vs
    columns = []                # flat list [(fam, var), ...]
    bounds = []                 # [(fam, start_idx, end_idx), ...]
    for fam, vs in fam_vars.items():
        s = len(columns)
        for v in vs:
            columns.append((fam, v))
        bounds.append((fam, s, len(columns) - 1))
    return fam_vars, columns, bounds


def build_ip_matrix(cells, columns):
    """(n_ip, n_variants) log-scaled matrix, row-ordered by descending total revs."""
    ip_totals = defaultdict(int)
    per_ip = defaultdict(lambda: defaultdict(int))
    for ip, fam, var, n in cells:
        ip_totals[ip] += n
        per_ip[ip][(fam, var)] += n
    ips = sorted(ip_totals, key=lambda k: (-ip_totals[k], k))
    n_var = len(columns)
    X = np.zeros((len(ips), n_var))
    for i, ip in enumerate(ips):
        for j, key in enumerate(columns):
            n = per_ip[ip].get(key, 0)
            if n:
                X[i, j] = math.log1p(n)
    return ips, ip_totals, per_ip, X


def pca_2d(X: np.ndarray) -> np.ndarray:
    Xc = X - X.mean(axis=0, keepdims=True)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    coords = U[:, :2] * S[:2]
    # Percentile-rank per axis so a handful of outlier /16s (e.g. 20.165)
    # don't compress the rest of the points into a tiny blob at the origin.
    out = np.zeros_like(coords)
    n = coords.shape[0]
    for k in range(2):
        order = np.argsort(coords[:, k])
        ranks = np.empty(n)
        ranks[order] = np.linspace(-1.0, 1.0, n)
        out[:, k] = ranks
    return out


# --- render ------------------------------------------------------------------

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cells = load_cells()
    fam_vars, columns, bounds = order_variants(cells)
    ips, ip_totals, per_ip, X = build_ip_matrix(cells, columns)
    ip_coords = pca_2d(X)

    ip_index = {ip: i for i, ip in enumerate(ips)}
    variant_index = {(f, v): j for j, (f, v) in enumerate(columns)}
    n_var = len(columns)

    max_cell = max(n for _, _, _, n in cells)

    # per-family palette lookup for the base colour of each column
    base_hsl = {}
    for fam, vs in fam_vars.items():
        for i, v in enumerate(vs):
            base_hsl[(fam, v)] = family_variant_base(fam, i, len(vs))

    # Build point arrays.
    xs, ys, zs, colours, sizes = [], [], [], [], []
    for ip, fam, var, n in cells:
        i = ip_index[ip]
        j = variant_index[(fam, var)]
        xs.append(float(ip_coords[i, 0]) * 4.5)
        ys.append(float(ip_coords[i, 1]) * 4.5)
        zs.append(j / max(1, n_var - 1) * 5.0)
        colours.append(cell_rgb(base_hsl[(fam, var)], n, max_cell))
        # radius: log(cell revs); larger floor so single-rev cells are visible
        r = 18.0 + 80.0 * math.log1p(n) / math.log1p(max_cell)
        sizes.append(r)

    xs = np.array(xs); ys = np.array(ys); zs = np.array(zs)
    sizes = np.array(sizes)
    colours = np.array(colours)

    # Ghost columns along z at each family band edge to make family layout legible.
    family_bar_x = xs.min() - 1.2
    family_bar_y = ys.max() + 0.8
    fam_bar_lines = []
    for fam, s, e in bounds:
        z0 = s / max(1, n_var - 1) * 5.0
        z1 = e / max(1, n_var - 1) * 5.0
        r, g, b = colorsys.hls_to_rgb(FAMILY_HUE[fam] / 360.0, 0.48, 0.65)
        fam_bar_lines.append((fam, z0, z1, (r, g, b)))

    fig = plt.figure(figsize=(10, 8), dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Shadow projection at z=0 so the cluster shape is legible from any angle.
    shadow_colours = np.concatenate(
        [colours * 0.4 + 0.6, np.full((len(colours), 1), 0.25)], axis=1,
    )
    ax.scatter(xs, ys, np.zeros_like(zs),
               c=shadow_colours, s=sizes * 0.55,
               edgecolors="none", depthshade=False)

    scatter = ax.scatter(
        xs, ys, zs, c=colours, s=sizes,
        edgecolors=(0, 0, 0, 0.35), linewidths=0.5, depthshade=True,
    )

    # Family band stripes floating on the far corner.
    z_bar_x = xs.min() - 0.4
    z_bar_y = ys.max() + 0.4
    fam_short = {
        "archive-item-research-bench": "archive",
        "fast-follow-question-bench":  "fast-follow",
        "sec-regcf-ma-cache":          "sec",
        "vocab-puzzle-refs":           "vocab",
    }
    for fam, z0, z1, rgb in fam_bar_lines:
        ax.plot([z_bar_x, z_bar_x], [z_bar_y, z_bar_y],
                [z0, z1], color=rgb, linewidth=7, solid_capstyle="butt",
                zorder=1)
        ax.text(z_bar_x + 0.1, z_bar_y, (z0 + z1) / 2 + 0.05,
                fam_short[fam], color=rgb, fontsize=7,
                ha="left", va="center", fontweight="bold")

    # Bring axis panes into a soft white so the palette dominates.
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_edgecolor((0.85, 0.85, 0.85))
        pane.set_facecolor((1, 1, 1, 0.7))
    ax.grid(True, linewidth=0.3, alpha=0.4)

    ax.set_xlabel("PCA[0] of /16's variant profile", fontsize=9, labelpad=4)
    ax.set_ylabel("PCA[1] of /16's variant profile", fontsize=9, labelpad=4)
    ax.set_zlabel("variant (heatmap column order)", fontsize=9, labelpad=4)
    ax.tick_params(axis="both", which="major", labelsize=7)

    fig.suptitle(
        f"Top-{len(ips)} /16 subnets clustered by task-variant fingerprint",
        fontsize=13, fontweight="600", y=0.965,
    )
    fig.text(0.5, 0.925,
             "one sphere per (subnet, variant) cell · same palette as heatmap 08 · "
             "size = log(cell revs)",
             ha="center", fontsize=9, color="#555")

    # Legend: one swatch per family.
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

    ax.set_box_aspect((1.1, 1.1, 1.35))
    ax.view_init(elev=22, azim=0)

    n_frames = 120

    def update(frame):
        azim = (frame / n_frames) * 360.0
        # very gentle elevation wobble for depth cueing
        elev = 22 + 5 * math.sin(2 * math.pi * frame / n_frames)
        ax.view_init(elev=elev, azim=azim)
        return (scatter,)

    ani = animation.FuncAnimation(
        fig, update, frames=n_frames, interval=40, blit=False,
    )

    mp4 = OUT_DIR / "ip16_task_variant_clusters_3d.mp4"
    gif = OUT_DIR / "ip16_task_variant_clusters_3d.gif"

    print(f"rendering {mp4} ...")
    writer = animation.FFMpegWriter(fps=25, bitrate=4200, codec="libx264",
                                    extra_args=["-pix_fmt", "yuv420p",
                                                "-movflags", "+faststart"])
    ani.save(str(mp4), writer=writer, dpi=140)
    print(f"wrote {mp4}")

    # Also produce a smaller GIF (Pillow writer, lower dpi).
    print(f"rendering {gif} ...")
    ani2 = animation.FuncAnimation(
        fig, update, frames=n_frames // 2, interval=80, blit=False,
    )
    ani2.save(str(gif), writer=animation.PillowWriter(fps=15), dpi=80)
    print(f"wrote {gif}")


if __name__ == "__main__":
    main()
