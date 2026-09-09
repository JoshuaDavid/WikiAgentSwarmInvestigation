#!/usr/bin/env python3
"""Animated 3D co-editorship render.

  node   = agent label (handle) with >= 3 stored revisions
  colour = the label's dominant (family, variant), same palette as heatmap 08
  size   = log(total revs)
  x, y   = percentile-rank PCA[0:2] on the (label × page) log-scaled
           matrix, restricted to *non-hub* pages (pages with <= 40
           distinct label editors) so a single wiki front page like
           `WillkommenImWiki` doesn't pull every cohort into the origin
  z      = mean UTC write time of the label's revisions, mapped to [0, 5]
  edges  = one line per pair of labels that co-edited at least 2
           non-hub pages; alpha and width scale with pair weight

The (x, y) embedding places labels that touched the same task pages near
each other; z separates cohorts that were only active in different
weeks.  Rotating the camera makes both the horizontal cohort clumps and
the vertical (temporal) stratification legible.

Writes:
  outputs/labels_coedit_3d.mp4
  outputs/labels_coedit_3d.gif
"""
from __future__ import annotations

import colorsys
import datetime as dt
import json
import math
import sys
from collections import OrderedDict, defaultdict
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
    ARCHIVE_INSTANCES, R_TOKEN, FAST_FOLLOW_MARKERS, HUB_FAMILIES,
    FAST_FOLLOW_FAMILIES, FAMILY_HUE, FAMILY_ORDER, VOCAB_PAGE_ID,
    load_page_family, match_archive_instances, family_variant_base,
)

REPO_ROOT = HERE.parent.parent
REV_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"
PAGES_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "pages.jsonl"
OUT_DIR = HERE / "outputs"

MIN_LABEL_REVS = 3          # 1,244 labels
MAX_LABELS_PER_PAGE = 40    # anything above this is a coordination hub
MIN_EDGE_WEIGHT = 2         # keep pairs that co-edited >= 2 non-hub pages


def cell_rgb(base, count: int, max_count: int):
    if count <= 0:
        return (0.98, 0.98, 0.98)
    frac = math.log1p(count) / math.log1p(max_count)
    hue, sat, light_saturated = base
    light = 0.94 - (0.94 - light_saturated) * frac
    sat_eff = 0.25 + (sat - 0.25) * frac
    r, g, b = colorsys.hls_to_rgb((hue % 360) / 360.0, light, sat_eff)
    return (r, g, b)


def parse_iso(s: str) -> float:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def load_page_label_counts():
    """page_key -> n_labels (from pages.jsonl, so we know hubs cheaply)."""
    m: dict[str, int] = {}
    with PAGES_PATH.open() as f:
        for line in f:
            p = json.loads(line)
            m[p["page_key"]] = p.get("n_labels", 0)
    return m


def collect(page_family):
    """Walk revisions.jsonl once; return everything we need per label."""
    per_label_variant: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    per_label_pages: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    per_label_times: dict[str, list] = defaultdict(list)
    label_totals: dict[str, int] = defaultdict(int)
    page_labels: dict[str, set] = defaultdict(set)

    with REV_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            label = r.get("label") or ""
            if not label:
                continue
            pk = r["page_key"]
            label_totals[label] += 1
            per_label_pages[label][pk] += 1
            per_label_times[label].append(parse_iso(r["time"]))
            page_labels[pk].add(label)

            body = r.get("body") or ""
            body_lc = body.lower()

            for inst in match_archive_instances(body_lc):
                per_label_variant[label][("archive-item-research-bench", inst)] += 1

            if R_TOKEN.search(body) and FAST_FOLLOW_MARKERS.search(body):
                fam = page_family.get(pk, "") or "unknown"
                if fam in FAST_FOLLOW_FAMILIES:
                    variant = fam
                elif fam in HUB_FAMILIES:
                    variant = f"(hub:{fam})"
                else:
                    variant = f"(other:{fam})"
                per_label_variant[label][("fast-follow-question-bench", variant)] += 1

            if ("regCF" in body) or ("us-ma-" in body) or ("county.json" in body):
                per_label_variant[label][("sec-regcf-ma-cache", "(no variants)")] += 1

            if r.get("page_id") == VOCAB_PAGE_ID:
                per_label_variant[label][("vocab-puzzle-refs", "(no variants)")] += 1

    return per_label_variant, per_label_pages, per_label_times, label_totals, page_labels


def order_columns(per_label_variant):
    variant_totals = defaultdict(int)
    for cells in per_label_variant.values():
        for k, n in cells.items():
            variant_totals[k] += n
    fam_vars: "OrderedDict[str, list[str]]" = OrderedDict()
    for fam in FAMILY_ORDER:
        vs = sorted([v for (f, v) in variant_totals if f == fam],
                    key=lambda v: (-variant_totals[(fam, v)], v))
        if vs:
            fam_vars[fam] = vs
    return fam_vars


def rank_scale(v: np.ndarray) -> np.ndarray:
    order = np.argsort(v)
    ranks = np.empty_like(v, dtype=float)
    ranks[order] = np.linspace(-1.0, 1.0, len(v))
    return ranks


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page_family = load_page_family()
    page_n_labels = load_page_label_counts()

    per_label_variant, per_label_pages, per_label_times, label_totals, page_labels = collect(page_family)

    # Keep labels with enough revisions AND with at least one classified cell.
    kept = [lab for lab, n in label_totals.items()
            if n >= MIN_LABEL_REVS and per_label_variant.get(lab)]
    kept.sort(key=lambda l: (-label_totals[l], l))
    print(f"nodes (labels): {len(kept)} of {len(label_totals)} "
          f"(threshold {MIN_LABEL_REVS} revs, must classify)")

    label_index = {lab: i for i, lab in enumerate(kept)}
    kept_set = set(kept)

    # Non-hub pages for the embedding matrix and the edge graph.
    non_hub_pages = [pk for pk, nl in page_n_labels.items() if nl <= MAX_LABELS_PER_PAGE]
    page_index = {pk: j for j, pk in enumerate(non_hub_pages)}
    print(f"non-hub pages: {len(non_hub_pages)} "
          f"(<= {MAX_LABELS_PER_PAGE} distinct editors)")

    # (label x page) log-scaled matrix. Sparse-ish but 1244 x ~4500 fits.
    X = np.zeros((len(kept), len(non_hub_pages)))
    for i, lab in enumerate(kept):
        for pk, n in per_label_pages[lab].items():
            j = page_index.get(pk)
            if j is not None:
                X[i, j] = math.log1p(n)
    print(f"embedding matrix: {X.shape}")

    # PCA -> (x, y). Percentile-rank-scale so outliers don't compress the cloud.
    Xc = X - X.mean(axis=0, keepdims=True)
    U, S, _ = np.linalg.svd(Xc, full_matrices=False)
    coords2 = U[:, :2] * S[:2]
    x = rank_scale(coords2[:, 0]) * 4.5
    y = rank_scale(coords2[:, 1]) * 4.5

    # z = mean write time -> percentile-rank -> [0, 5]. Percentile-rank avoids
    # the mid-June activity spike compressing everything to a single slab.
    mean_times = np.array([np.mean(per_label_times[lab]) for lab in kept])
    z = (rank_scale(mean_times) + 1) / 2 * 5.0

    # Edges: for each non-hub page, all label pairs among its editors.
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
    edges.sort(key=lambda e: e[2])   # low weight first, high weight on top
    print(f"edges (weight >= {MIN_EDGE_WEIGHT}): {len(edges)}")

    # Palette bases for each (fam, variant).
    fam_vars = order_columns(per_label_variant)
    base_hsl = {}
    for fam, vs in fam_vars.items():
        for i, v in enumerate(vs):
            base_hsl[(fam, v)] = family_variant_base(fam, i, len(vs))
    max_cell = max((n for cells in per_label_variant.values()
                    for n in cells.values()), default=1)

    dom_fam = []
    colours = np.zeros((len(kept), 3))
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

    # --- render --------------------------------------------------------------

    fig = plt.figure(figsize=(11, 8.5), dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Draw edges first so nodes sit on top.
    segs = []
    seg_colours = []
    seg_widths = []
    max_w = max(w for _, _, w in edges) if edges else 1
    for i, j, w in edges:
        segs.append(((x[i], y[i], z[i]), (x[j], y[j], z[j])))
        # Blend endpoint colours so an edge inherits both families' hues.
        blend = 0.5 * colours[i] + 0.5 * colours[j]
        alpha = 0.10 + 0.55 * math.log1p(w) / math.log1p(max_w)
        seg_colours.append((*blend, alpha))
        seg_widths.append(0.35 + 0.9 * math.log1p(w) / math.log1p(max_w))
    if segs:
        lc = Line3DCollection(segs, colors=seg_colours, linewidths=seg_widths)
        ax.add_collection3d(lc)

    # Shadow (semi-transparent, projected on the floor plane).
    z_floor = z.min() - 0.25
    shadow_c = np.concatenate(
        [colours * 0.4 + 0.6, np.full((len(colours), 1), 0.20)], axis=1,
    )
    ax.scatter(x, y, np.full_like(z, z_floor),
               c=shadow_c, s=sizes * 0.55,
               edgecolors="none", depthshade=False)

    # Nodes.
    scatter = ax.scatter(
        x, y, z, c=colours, s=sizes,
        edgecolors=(0, 0, 0, 0.35), linewidths=0.4, depthshade=True,
    )

    # z-axis tick labels showing actual dates.
    t_min, t_max = float(mean_times.min()), float(mean_times.max())
    z_ticks = np.linspace(0.05, 4.95, 5)
    # Map z back to timestamp by percentile-inverse (approx via interpolation).
    sorted_t = np.sort(mean_times)
    tick_dates = []
    for zt in z_ticks:
        # zt is in [0, 5], corresponds to percentile (zt/5) of mean_times.
        idx = min(len(sorted_t) - 1, max(0, int(round((zt / 5.0) * (len(sorted_t) - 1)))))
        d = dt.datetime.utcfromtimestamp(sorted_t[idx])
        tick_dates.append(d.strftime("%b %d"))
    ax.set_zticks(z_ticks)
    ax.set_zticklabels(tick_dates)

    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_edgecolor((0.85, 0.85, 0.85))
        pane.set_facecolor((1, 1, 1, 0.7))
    ax.grid(True, linewidth=0.3, alpha=0.4)

    ax.set_xlabel("PCA[0] of label's page profile", fontsize=9, labelpad=4)
    ax.set_ylabel("PCA[1] of label's page profile", fontsize=9, labelpad=4)
    ax.set_zlabel("mean write time (percentile rank)", fontsize=9, labelpad=4)
    ax.tick_params(axis="both", which="major", labelsize=7)

    fig.suptitle(
        f"{len(kept):,} agent labels · co-editorship of non-hub pages · "
        f"z = mean write time",
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

    mp4 = OUT_DIR / "labels_coedit_3d.mp4"
    gif = OUT_DIR / "labels_coedit_3d.gif"

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
