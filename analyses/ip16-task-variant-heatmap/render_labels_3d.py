#!/usr/bin/env python3
"""Animated 3D cluster render of agent labels (handles), colour-coded with
the same task-family x variant palette as heatmap 08.

Motivation: the /16-subnet variant of this render (`render_3d.py`) reuses
a beautiful palette but /16 traffic is spread pretty evenly and the
clusters aren't informative. Swapping the row axis from /16 subnets to
agent labels puts the palette on the axis where cohort structure
actually lives — date-prefix cohorts, OpenAI-branded scouts, and
role-word helpers separate visibly in PCA space.

Placement:
  Feature vector per label = log(1 + revisions on (family, variant)) for
  every (family, variant) column the heatmap classifier discovers.
  x, y, z = PCA[0:3] of that matrix, percentile-rank-scaled so a few
  hyper-active handles don't compress the rest of the cloud.

Sphere colour = the (family, variant) each label has the most revisions
on, run through the same `family_variant_base` + `cell_color` as
`build_and_plot.py`.

Sphere radius scales with log(total revs).

Writes:
  outputs/labels_task_variant_clusters_3d.mp4
  outputs/labels_task_variant_clusters_3d.gif
"""
from __future__ import annotations

import colorsys
import json
import math
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_and_plot import (  # noqa: E402
    ARCHIVE_INSTANCES, R_TOKEN, FAST_FOLLOW_MARKERS, HUB_FAMILIES,
    FAST_FOLLOW_FAMILIES, FAMILY_HUE, FAMILY_ORDER, VOCAB_PAGE_ID,
    load_page_family, match_archive_instances, family_variant_base,
)

REPO_ROOT = HERE.parent.parent
REV_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"
OUT_DIR = HERE / "outputs"

MIN_LABEL_REVS = 2  # drop the 1,332 singleton labels — no clustering signal


def cell_rgb(base, count: int, max_count: int):
    if count <= 0:
        return (0.98, 0.98, 0.98)
    frac = math.log1p(count) / math.log1p(max_count)
    hue, sat, light_saturated = base
    light = 0.94 - (0.94 - light_saturated) * frac
    sat_eff = 0.25 + (sat - 0.25) * frac
    r, g, b = colorsys.hls_to_rgb((hue % 360) / 360.0, light, sat_eff)
    return (r, g, b)


def collect_by_label(page_family: dict[str, str]):
    """Return per_label[(fam, var)] -> revs, plus per_label totals."""
    per_label: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    label_totals: dict[str, int] = defaultdict(int)

    with REV_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            label = r.get("label") or ""
            if not label:
                continue
            label_totals[label] += 1

            body = r.get("body") or ""
            body_lc = body.lower()

            for inst in match_archive_instances(body_lc):
                per_label[label][("archive-item-research-bench", inst)] += 1

            if R_TOKEN.search(body) and FAST_FOLLOW_MARKERS.search(body):
                fam = page_family.get(r.get("page_key", ""), "") or "unknown"
                if fam in FAST_FOLLOW_FAMILIES:
                    variant = fam
                elif fam in HUB_FAMILIES:
                    variant = f"(hub:{fam})"
                else:
                    variant = f"(other:{fam})"
                per_label[label][("fast-follow-question-bench", variant)] += 1

            if ("regCF" in body) or ("us-ma-" in body) or ("county.json" in body):
                per_label[label][("sec-regcf-ma-cache", "(no variants)")] += 1

            if r.get("page_id") == VOCAB_PAGE_ID:
                per_label[label][("vocab-puzzle-refs", "(no variants)")] += 1

    return per_label, label_totals


def order_columns(per_label):
    """Same family-block order as heatmap 08."""
    variant_totals = defaultdict(int)
    for label_cells in per_label.values():
        for (fam, var), n in label_cells.items():
            variant_totals[(fam, var)] += n

    fam_vars: "OrderedDict[str, list[str]]" = OrderedDict()
    for fam in FAMILY_ORDER:
        vs = sorted([v for (f, v) in variant_totals if f == fam],
                    key=lambda v: (-variant_totals[(fam, v)], v))
        if vs:
            fam_vars[fam] = vs
    columns: list[tuple[str, str]] = []
    for fam, vs in fam_vars.items():
        for v in vs:
            columns.append((fam, v))
    return fam_vars, columns


def pca_3d(X: np.ndarray) -> np.ndarray:
    Xc = X - X.mean(axis=0, keepdims=True)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    coords = U[:, :3] * S[:3]
    n = coords.shape[0]
    out = np.zeros_like(coords)
    for k in range(3):
        order = np.argsort(coords[:, k])
        ranks = np.empty(n)
        ranks[order] = np.linspace(-1.0, 1.0, n)
        out[:, k] = ranks
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page_family = load_page_family()
    per_label, label_totals = collect_by_label(page_family)

    # Keep labels with enough activity to have a fingerprint at all.
    labels = [lab for lab, n in label_totals.items() if n >= MIN_LABEL_REVS]
    labels = [lab for lab in labels if per_label[lab]]  # drop revs w/o cells
    labels.sort(key=lambda l: (-label_totals[l], l))
    print(f"labels kept: {len(labels)} of {len(label_totals)} "
          f"(threshold {MIN_LABEL_REVS} revs and >=1 classified cell)")

    fam_vars, columns = order_columns(per_label)
    print(f"columns discovered: {len(columns)} "
          f"across {len(fam_vars)} families")

    n_var = len(columns)
    X = np.zeros((len(labels), n_var))
    for i, lab in enumerate(labels):
        cells = per_label[lab]
        for j, key in enumerate(columns):
            n = cells.get(key, 0)
            if n:
                X[i, j] = math.log1p(n)

    coords = pca_3d(X)

    # Per-label dominant (fam, variant) + count -> palette colour.
    base_hsl = {}
    for fam, vs in fam_vars.items():
        for i, v in enumerate(vs):
            base_hsl[(fam, v)] = family_variant_base(fam, i, len(vs))
    max_cell = max((n for cells in per_label.values() for n in cells.values()), default=1)

    xs, ys, zs, colours, sizes, dom_fams = [], [], [], [], [], []
    max_total = max(label_totals[lab] for lab in labels)
    for i, lab in enumerate(labels):
        cells = per_label[lab]
        (fam, var), n_dom = max(cells.items(), key=lambda kv: kv[1])
        colours.append(cell_rgb(base_hsl[(fam, var)], n_dom, max_cell))
        dom_fams.append(fam)
        xs.append(coords[i, 0] * 4.5)
        ys.append(coords[i, 1] * 4.5)
        zs.append(coords[i, 2] * 4.5)
        r = 10.0 + 90.0 * math.log1p(label_totals[lab]) / math.log1p(max_total)
        sizes.append(r)

    xs = np.array(xs); ys = np.array(ys); zs = np.array(zs)
    sizes = np.array(sizes)
    colours = np.array(colours)

    fig = plt.figure(figsize=(10, 8), dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Family halo groups (draw darker family cores under lighter cells).
    order_by_family = sorted(range(len(labels)),
                             key=lambda i: FAMILY_ORDER.index(dom_fams[i]))
    xs_o = xs[order_by_family]
    ys_o = ys[order_by_family]
    zs_o = zs[order_by_family]
    cs_o = colours[order_by_family]
    ss_o = sizes[order_by_family]

    # Shadow (semi-transparent, projected on z = min).
    z_floor = zs_o.min() - 0.2
    shadow_c = np.concatenate(
        [cs_o * 0.4 + 0.6, np.full((len(cs_o), 1), 0.20)], axis=1,
    )
    ax.scatter(xs_o, ys_o, np.full_like(zs_o, z_floor),
               c=shadow_c, s=ss_o * 0.55,
               edgecolors="none", depthshade=False)

    scatter = ax.scatter(
        xs_o, ys_o, zs_o, c=cs_o, s=ss_o,
        edgecolors=(0, 0, 0, 0.32), linewidths=0.4, depthshade=True,
    )

    # Bring axis panes into a soft white so the palette dominates.
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_edgecolor((0.85, 0.85, 0.85))
        pane.set_facecolor((1, 1, 1, 0.7))
    ax.grid(True, linewidth=0.3, alpha=0.4)

    ax.set_xlabel("PCA[0] of label's variant profile", fontsize=9, labelpad=4)
    ax.set_ylabel("PCA[1] of label's variant profile", fontsize=9, labelpad=4)
    ax.set_zlabel("PCA[2] of label's variant profile", fontsize=9, labelpad=4)
    ax.tick_params(axis="both", which="major", labelsize=7)

    fig.suptitle(
        f"{len(labels):,} agent labels clustered by task-variant fingerprint",
        fontsize=13, fontweight="600", y=0.965,
    )
    fig.text(0.5, 0.925,
             "one sphere per handle (>= 2 stored revs) · palette = heatmap 08 "
             "(hue = family, shade = dominant variant) · size = log(total revs)",
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
              bbox_to_anchor=(0.5, -0.06), ncol=4, fontsize=8,
              frameon=True, facecolor="white", edgecolor="#bbb")

    ax.set_box_aspect((1.2, 1.2, 1.2))
    ax.view_init(elev=20, azim=0)

    n_frames = 120

    def update(frame):
        azim = (frame / n_frames) * 360.0
        elev = 20 + 6 * math.sin(2 * math.pi * frame / n_frames)
        ax.view_init(elev=elev, azim=azim)
        return (scatter,)

    ani = animation.FuncAnimation(
        fig, update, frames=n_frames, interval=40, blit=False,
    )

    mp4 = OUT_DIR / "labels_task_variant_clusters_3d.mp4"
    gif = OUT_DIR / "labels_task_variant_clusters_3d.gif"

    print(f"rendering {mp4} ...")
    writer = animation.FFMpegWriter(fps=25, bitrate=4200, codec="libx264",
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
