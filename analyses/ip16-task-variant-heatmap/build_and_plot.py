#!/usr/bin/env python3
"""Heatmap: top-N /16 subnets (rows) × task variants (columns), grouped
into task-family blocks. Cell fill uses the same task-family/variant
palette as analyses/agent-activity-by-date/ — hue = task family, shade
within family = variant — and cell opacity is log-scaled by revisions on
that (subnet, variant).

Reads:
  agent-logs/prowiki/revisions.jsonl
  agent-logs/prowiki/pages.jsonl

Writes:
  outputs/ip16_variant.tsv               ip16, task, variant, revisions
  outputs/ip16_task_variant_heatmap.svg  the heatmap

Pure stdlib. Rerun with:
    python3 analyses/ip16-task-variant-heatmap/build_and_plot.py
"""
from __future__ import annotations
import colorsys
import json
import math
import re
import sys
from collections import defaultdict, OrderedDict
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
REV_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"
PAGES_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "pages.jsonl"
OUT_DIR = HERE / "outputs"

TOP_N = 60

# --- task classifiers (same as analyses/agent-activity-by-date/) -------------

ARCHIVE_INSTANCES: dict[str, list[str]] = {
    "art-work-of-charleston": [
        "lcdl:129140", "lcdl:129141", "lcdl:129142", "lcdl:129143", "lcdl:129144",
        "lcdl:129145", "lcdl:129146", "lcdl:129147", "lcdl:129148", "lcdl:129229",
        "lcdl129140", "lcdl129141", "lcdl129142", "lcdl129143", "lcdl129144",
        "lcdl129145", "lcdl129146", "lcdl129147", "lcdl129148", "lcdl129229",
        "lcdl%3a129",
        "205927", "205928", "205929", "205930", "205931", "205932", "205933", "205934",
        "art-work-of-charleston", "historic-charleston-foundation", "chp4demo850801",
    ],
    "patriots-point-jan-1951": [
        "lcdl:123721", "lcdl123721", "lcdl:123716", "lcdl123716", "217622",
        "patriots point", "patriot", "shipyard", "jan1951", "january 1951",
    ],
    "texas-tsl-preservica": [
        "tsl.access.preservica.com", "tsl.preservica.com",
        "io_f436a16c", "f436a16c-767f-44b8-95fc-2031847276b9",
    ],
    "clark-economics-newsletters": [
        "clarku.edu/departments/economics", "www2.clarku.edu/departments/economics",
        "clark university economics", "newsletter2012", "newsletter%25202010",
        "newsletter 2010", "newsletter2010", "clark newsletter", "clark econ",
    ],
    "minnesota-mhs-p16022coll45-152": [
        "p16022coll45/id/152", "p16022coll45%3a152", "p16022coll45:152",
        "cdm16022", "mhs52936", "52936", "mhs 52936", "collection.mndigital.org",
    ],
    "cgsc-hoffman-order-of-battle": [
        "cgsc.contentdm.oclc.org", "p4013coll7",
    ],
    "rugby-world-march-1995": [
        "themagazinearchive", "pagesuite", "rugby world", "rugbyworldfree",
        "ca6f26c8-fa61-463f-a0e5-ec848a0b0044",
    ],
}
R_TOKEN = re.compile(r"\b[RGQC][1-9]\b")
FAST_FOLLOW_MARKERS = re.compile(
    r"(clock\.wait|cooldown|task[-\s]?clock|scaffold[-\s]?clock|deadline|"
    r"cohort|sequence|timer|Now,?\s+do\s+the\s+same|initial\s+prompt|"
    r"tier|cadence|projected|followup)",
    re.IGNORECASE,
)
HUB_FAMILIES = {
    "relay-coordination", "off_store_unclassified", "mixed-task", "unknown",
    "probe-test", "source-cache-url-list", "source-or-unclassified",
}
FAST_FOLLOW_FAMILIES = [
    "oecd-equity", "datausa-clothing-workforce", "datausa-cashiers-masters",
    "datausa-construction-workforce", "datausa-grocery-workforce",
    "ihme-cvd-deaths", "datausa-language-french", "datausa-poverty-county",
    "datausa-maids-wage", "datausa-police-wage-age",
    "datausa-transport-production", "datausa-sector61-state",
    "ihme-family-planning", "datausa-occupation-salary-61-62",
    "datausa-finance-gender-gap", "oecd-regional-co2", "uefa-pass-accuracy",
    "nyc-veterans", "datausa-enrollment-asian", "datausa-poverty-state",
    "datausa-production-share", "vermont-rent", "datausa-cashiers-bachelors",
    "datausa-ivy-tuition", "fuel-poverty-ni", "ihme-mcv2", "ihme-smoking",
    "sdg-index-score", "dataafrica-rainfed-crops", "datausa-slp-ethnicity",
    "oecd-household-income", "datausa-construction-wage",
    "datausa-cashier-skills", "alaska-climate", "datausa-elpaso-foreign-born",
    "aihw-pbs", "dataafrica-health-stunting", "ihme-lymphatic-filariasis",
    "world-poverty-clock",
]
VOCAB_PAGE_ID = "dse/AgentVocabPuzzleRefsJun20"

# Same family palette as analyses/agent-activity-by-date/.
FAMILY_HUE = {
    "archive-item-research-bench": 210,   # blue
    "fast-follow-question-bench":   15,   # red-orange
    "sec-regcf-ma-cache":          140,   # green
    "vocab-puzzle-refs":           285,   # violet
}
FAMILY_ORDER = [
    "archive-item-research-bench",
    "fast-follow-question-bench",
    "sec-regcf-ma-cache",
    "vocab-puzzle-refs",
]


def hsl_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def family_variant_base(family: str, variant_idx: int, variant_n: int) -> tuple[float, float, float]:
    """Return (hue, saturation, lightness) for the *fully-saturated* colour of
    a variant. Cell rendering then modulates lightness by log(count)."""
    hue = FAMILY_HUE[family]
    if variant_n <= 1:
        return (hue, 0.65, 0.48)
    frac = variant_idx / (variant_n - 1)
    return (hue + (frac - 0.5) * 16.0,
            0.55 + (1 - abs(frac - 0.5) * 2) * 0.20,
            0.30 + frac * 0.42)


def cell_color(base: tuple[float, float, float], count: int, max_count: int) -> str:
    if count <= 0:
        return "#fafafa"
    frac = math.log1p(count) / math.log1p(max_count)
    hue, sat, light_saturated = base
    # Interpolate from very light (94) to the variant's saturated lightness.
    light = 0.94 - (0.94 - light_saturated) * frac
    sat_eff = 0.25 + (sat - 0.25) * frac
    return hsl_hex(hue, sat_eff, light)


# --- data --------------------------------------------------------------------

def load_page_family() -> dict[str, str]:
    m: dict[str, str] = {}
    with PAGES_PATH.open() as f:
        for line in f:
            p = json.loads(line)
            m[p["page_key"]] = p.get("page_family", "") or ""
    return m


def match_archive_instances(body_lc: str) -> set[str]:
    return {name for name, needles in ARCHIVE_INSTANCES.items()
            if any(k in body_lc for k in needles)}


def collect(page_family: dict[str, str]):
    """Return (ip_totals, cell) where cell[(ip16, task, variant)] = revs."""
    ip_totals: dict[str, int] = defaultdict(int)
    cell: dict[tuple[str, str, str], int] = defaultdict(int)
    with REV_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            body = r.get("body") or ""
            body_lc = body.lower()
            ip = r.get("ip16") or "(none)"
            ip_totals[ip] += 1

            for inst in match_archive_instances(body_lc):
                cell[(ip, "archive-item-research-bench", inst)] += 1

            if R_TOKEN.search(body) and FAST_FOLLOW_MARKERS.search(body):
                fam = page_family.get(r.get("page_key", ""), "") or "unknown"
                if fam in FAST_FOLLOW_FAMILIES:
                    variant = fam
                elif fam in HUB_FAMILIES:
                    variant = f"(hub:{fam})"
                else:
                    variant = f"(other:{fam})"
                cell[(ip, "fast-follow-question-bench", variant)] += 1

            if ("regCF" in body) or ("us-ma-" in body) or ("county.json" in body):
                cell[(ip, "sec-regcf-ma-cache", "(no variants)")] += 1

            if r.get("page_id") == VOCAB_PAGE_ID:
                cell[(ip, "vocab-puzzle-refs", "(no variants)")] += 1

    return ip_totals, cell


# --- render ------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page_family = load_page_family()
    ip_totals, cell = collect(page_family)

    top_ips = [ip for ip, _ in
               sorted(ip_totals.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_N]]

    # Discover variants per family, ordered by total revisions descending.
    variant_totals: dict[tuple[str, str], int] = defaultdict(int)
    for (ip, fam, var), n in cell.items():
        variant_totals[(fam, var)] += n
    family_variants: "OrderedDict[str, list[str]]" = OrderedDict()
    for fam in FAMILY_ORDER:
        variants = sorted(
            [v for (f, v) in variant_totals if f == fam],
            key=lambda v: (-variant_totals[(fam, v)], v),
        )
        if variants:
            family_variants[fam] = variants

    # Flat column list plus family boundaries.
    columns: list[tuple[str, str]] = []
    family_bounds: list[tuple[str, int, int]] = []
    for fam, variants in family_variants.items():
        start = len(columns)
        for v in variants:
            columns.append((fam, v))
        family_bounds.append((fam, start, len(columns) - 1))

    # Palette bases per (fam, variant).
    base_hsl: dict[tuple[str, str], tuple[float, float, float]] = {}
    for fam, variants in family_variants.items():
        for i, v in enumerate(variants):
            base_hsl[(fam, v)] = family_variant_base(fam, i, len(variants))

    max_cell = max((cell.get((ip, f, v), 0) for ip in top_ips
                    for (f, v) in columns), default=1) or 1

    # Emit TSV.
    with (OUT_DIR / "ip16_variant.tsv").open("w") as f:
        f.write("ip16\ttask\tvariant\trevisions\n")
        for ip in top_ips:
            for (fam, var) in columns:
                n = cell.get((ip, fam, var), 0)
                if n:
                    f.write(f"{ip}\t{fam}\t{var}\t{n}\n")

    # Layout.
    W = max(1200, 240 + 12 * len(columns) + 280)
    CELL_W = 12
    CELL_H = 12
    MARGIN_L, MARGIN_R = 170, 260
    MARGIN_T, MARGIN_B = 240, 30    # big top margin for rotated variant labels
    plot_w = CELL_W * len(columns)
    plot_h = CELL_H * len(top_ips)
    W = MARGIN_L + plot_w + MARGIN_R
    H = MARGIN_T + plot_h + MARGIN_B

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="11">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
        f'<text x="{MARGIN_L + plot_w/2:.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">Top {TOP_N} source '
        f'/16 subnets × task variants</text>',
        f'<text x="{MARGIN_L + plot_w/2:.0f}" y="46" text-anchor="middle" '
        f'fill="#555">Rows = /16 subnets by total revs. Columns = task '
        f'variants, grouped by family (same palette as agent-activity-by-date). '
        f'Cell shade = log(revs on that (subnet, variant)).</text>',
    ]

    # Family header bars above the columns.
    header_bar_y = MARGIN_T - 34
    for fam, start_i, end_i in family_bounds:
        x0 = MARGIN_L + start_i * CELL_W
        w = (end_i - start_i + 1) * CELL_W
        # Solid family colour bar.
        h_hue = FAMILY_HUE[fam]
        parts.append(
            f'<rect x="{x0:.1f}" y="{header_bar_y}" width="{w:.1f}" '
            f'height="10" fill="{hsl_hex(h_hue, 0.65, 0.48)}"/>'
        )
        parts.append(
            f'<text x="{x0 + w/2:.1f}" y="{header_bar_y - 4}" '
            f'text-anchor="middle" font-weight="600" fill="#111" '
            f'font-size="11">{escape(fam)} '
            f'<tspan fill="#666" font-weight="400">'
            f'· {end_i - start_i + 1} col{"" if end_i == start_i else "s"}'
            f'</tspan></text>'
        )

    # Column (variant) labels rotated -60°.
    for j, (fam, var) in enumerate(columns):
        x = MARGIN_L + j * CELL_W + CELL_W / 2
        y = MARGIN_T - 12
        parts.append(
            f'<text x="{x:.1f}" y="{y}" text-anchor="start" fill="#333" '
            f'font-size="10" transform="rotate(-60 {x:.1f} {y})">'
            f'{escape(var)}</text>'
        )

    # Row labels (IP) and row bands.
    for i, ip in enumerate(top_ips):
        y_row = MARGIN_T + i * CELL_H
        parts.append(
            f'<text x="{MARGIN_L - 8}" y="{y_row + CELL_H - 3}" '
            f'text-anchor="end" fill="#111" font-size="10">'
            f'{escape(ip)}</text>'
        )
        parts.append(
            f'<text x="{MARGIN_L - 64}" y="{y_row + CELL_H - 3}" '
            f'text-anchor="end" fill="#666" font-size="10">'
            f'{ip_totals[ip]:,}</text>'
        )
        # Row background.
        parts.append(
            f'<rect x="{MARGIN_L}" y="{y_row}" width="{plot_w:.1f}" '
            f'height="{CELL_H}" fill="#fbfbfb" stroke="none"/>'
        )
        for j, (fam, var) in enumerate(columns):
            n = cell.get((ip, fam, var), 0)
            if n <= 0:
                continue
            x = MARGIN_L + j * CELL_W
            parts.append(
                f'<rect x="{x:.1f}" y="{y_row + 0.5}" width="{CELL_W - 0.5}" '
                f'height="{CELL_H - 1}" fill="{cell_color(base_hsl[(fam, var)], n, max_cell)}" '
                f'stroke="none"><title>{escape(ip)} · {escape(fam)} / '
                f'{escape(var)}: {n:,}</title></rect>'
            )

    # Vertical family dividers.
    for fam, start_i, end_i in family_bounds:
        x = MARGIN_L + (end_i + 1) * CELL_W
        parts.append(
            f'<line x1="{x:.1f}" y1="{MARGIN_T}" x2="{x:.1f}" '
            f'y2="{MARGIN_T + plot_h}" stroke="#bbb" stroke-width="0.8"/>'
        )

    # Legend at right.
    lx = MARGIN_L + plot_w + 20
    ly = MARGIN_T
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'legend</text>'
    )
    ly += 14
    parts.append(
        f'<text x="{lx}" y="{ly}" fill="#111" font-size="11">'
        f'hue = task family</text>'
    )
    ly += 14
    parts.append(
        f'<text x="{lx}" y="{ly}" fill="#111" font-size="11">'
        f'shade within col = variant</text>'
    )
    ly += 14
    parts.append(
        f'<text x="{lx}" y="{ly}" fill="#111" font-size="11">'
        f'opacity = log(revs)</text>'
    )
    ly += 20
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'family palettes</text>'
    )
    ly += 14
    for fam, variants in family_variants.items():
        parts.append(
            f'<text x="{lx}" y="{ly + 10}" fill="#111" font-size="11" '
            f'font-weight="600">{escape(fam)}</text>'
        )
        ly += 14
        strip_w = 200
        cell_w2 = strip_w / max(1, len(variants))
        for i, v in enumerate(variants):
            base = family_variant_base(fam, i, len(variants))
            parts.append(
                f'<rect x="{lx + i * cell_w2:.1f}" y="{ly}" '
                f'width="{cell_w2:.1f}" height="10" '
                f'fill="{cell_color(base, max_cell, max_cell)}">'
                f'<title>{escape(v)}: {variant_totals[(fam, v)]:,}</title>'
                f'</rect>'
            )
        ly += 16
    ly += 8

    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'opacity ramp</text>'
    )
    ly += 14
    # Use the fast-follow palette anchor for the ramp; it's the tallest column.
    ramp_base = family_variant_base("fast-follow-question-bench", 0, 1)
    ramp_w = 200
    steps = 100
    for i in range(steps):
        frac = i / (steps - 1)
        n = int(round(math.expm1(frac * math.log1p(max_cell))))
        parts.append(
            f'<rect x="{lx + i * ramp_w / steps:.2f}" y="{ly}" '
            f'width="{ramp_w / steps + 0.5:.2f}" height="12" '
            f'fill="{cell_color(ramp_base, max(1, n), max_cell)}" '
            f'stroke="none"/>'
        )
    parts.append(
        f'<rect x="{lx}" y="{ly}" width="{ramp_w}" height="12" '
        f'fill="none" stroke="#333" stroke-width="0.4"/>'
    )
    for t in sorted({1, 10, 100, max_cell}):
        frac = math.log1p(t) / math.log1p(max_cell)
        x = lx + frac * ramp_w
        parts.append(
            f'<text x="{x:.1f}" y="{ly + 24}" text-anchor="middle" '
            f'fill="#333" font-size="10">{t:,}</text>'
        )
    ly += 40

    total_all = sum(ip_totals.values())
    total_top = sum(ip_totals[ip] for ip in top_ips)
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'notes</text>'
    )
    ly += 14
    for line in [
        f"top {TOP_N} /16s: {total_top:,} /",
        f"  {total_all:,} revs "
        f"({100 * total_top / total_all:.0f}%)",
        f"{len(columns)} variants, "
        f"{len(family_variants)} families",
        f"peak cell: {max_cell:,}",
    ]:
        parts.append(f'<text x="{lx}" y="{ly}" fill="#333">{line}</text>')
        ly += 14

    parts.append("</svg>")
    (OUT_DIR / "ip16_task_variant_heatmap.svg").write_text("\n".join(parts))
    print(f"wrote {OUT_DIR / 'ip16_variant.tsv'}", file=sys.stderr)
    print(f"wrote {OUT_DIR / 'ip16_task_variant_heatmap.svg'}", file=sys.stderr)


if __name__ == "__main__":
    main()
