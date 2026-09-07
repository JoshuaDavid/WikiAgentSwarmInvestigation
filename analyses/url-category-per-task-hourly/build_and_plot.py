#!/usr/bin/env python3
"""Per-task-family stacked-area of URL occurrences by hour of the export.

Same category grouping as analyses/url-category-over-time/, but:
- one panel per task family (small multiples), and
- x-axis bucket is 1 hour instead of 1 day.

Task-family classification of a revision uses the same logic as
tasks/first_last_observed.py and analyses/agent-activity-by-date/. A
revision may match more than one family — the URL is then counted in each
matching family's panel. URLs on revisions that match no family go into
the "unclassified" panel.

Reads:
  agent-logs/prowiki/revisions.jsonl
  agent-logs/prowiki/pages.jsonl
  analyses/urls/outputs/urls-classified.jsonl

Writes:
  outputs/urls_by_task_hour.tsv
  outputs/urls_stacked_per_task_hourly.svg

Pure stdlib. Rerun with:
    python3 analyses/url-category-per-task-hourly/build_and_plot.py
"""
from __future__ import annotations
import colorsys
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
REV_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"
PAGES_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "pages.jsonl"
URL_PATH = REPO_ROOT / "analyses" / "urls" / "outputs" / "urls-classified.jsonl"
OUT_DIR = HERE / "outputs"

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
VOCAB_PAGE_ID = "dse/AgentVocabPuzzleRefsJun20"


def classify(body: str, page_id: str) -> set[str]:
    """Return the set of task families this revision belongs to."""
    fams: set[str] = set()
    body_lc = body.lower()
    for needles in ARCHIVE_INSTANCES.values():
        if any(k in body_lc for k in needles):
            fams.add("archive-item-research-bench")
            break
    if R_TOKEN.search(body) and FAST_FOLLOW_MARKERS.search(body):
        fams.add("fast-follow-question-bench")
    if ("regCF" in body) or ("us-ma-" in body) or ("county.json" in body):
        fams.add("sec-regcf-ma-cache")
    if page_id == VOCAB_PAGE_ID:
        fams.add("vocab-puzzle-refs")
    return fams


# --- category grouping (same as analyses/url-category-over-time/) ------------

CATEGORY_GROUPS = [
    ("own wiki",             215, ["wiki_self"]),
    ("proxies / relays",      15, ["jq_json_relay", "fetch_proxy_markdown",
                                   "cors_proxy", "google_translate_proxy"]),
    ("data sources",         140, ["data_source_sec_investor",
                                   "data_source_datausa",
                                   "data_source_us_gov",
                                   "data_source_library",
                                   "data_source_other",
                                   "data_source_health",
                                   "data_source_publishing",
                                   "data_source_finance"]),
    ("archive / storage",    195, ["archive_wayback", "cloud_storage_dropbox",
                                   "google_docs"]),
    ("obfuscation / test",   285, ["url_shortener", "counter_signalling",
                                   "test_placeholder",
                                   "obfuscated_or_malformed"]),
]
PANELS = [
    "archive-item-research-bench",
    "fast-follow-question-bench",
    "sec-regcf-ma-cache",
    "vocab-puzzle-refs",
    "unclassified",
]


def hsl_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def category_color(group_hue: int, idx: int, n: int) -> str:
    if n == 1:
        return hsl_hex(group_hue, 0.55, 0.48)
    frac = idx / (n - 1)
    hue = group_hue + (frac - 0.5) * 20
    sat = 0.45 + 0.30 * (1 - abs(frac - 0.5) * 2)
    light = 0.32 + frac * 0.42
    return hsl_hex(hue, sat, light)


def parse_hour_bucket(iso: str) -> datetime | None:
    """Return the UTC hour-floor of an ISO timestamp, or None."""
    if len(iso) < 13 or iso[10] != "T":
        return None
    try:
        return datetime(int(iso[0:4]), int(iso[5:7]), int(iso[8:10]),
                        int(iso[11:13]), 0, 0, tzinfo=timezone.utc)
    except ValueError:
        return None


def hour_range(a: datetime, b: datetime) -> list[datetime]:
    out, cur = [], a
    step = timedelta(hours=1)
    while cur <= b:
        out.append(cur)
        cur += step
    return out


# --- data ---------------------------------------------------------------

def load_rev_to_families() -> dict[str, set[str]]:
    m: dict[str, set[str]] = {}
    with REV_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            body = r.get("body") or ""
            page_id = r.get("page_id") or ""
            fams = classify(body, page_id)
            m[r["rev_id"]] = fams
    return m


def load_url_hours(rev_to_families: dict[str, set[str]]) -> \
        dict[tuple[str, datetime, str], int]:
    """(task_family, hour_bucket, category) -> count."""
    counts: dict[tuple[str, datetime, str], int] = defaultdict(int)
    with URL_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            hb = parse_hour_bucket(r.get("time") or "")
            if hb is None:
                continue
            cat = r.get("category") or "unknown"
            rev_id = r.get("rev_id") or ""
            fams = rev_to_families.get(rev_id, set())
            if not fams:
                counts[("unclassified", hb, cat)] += 1
            else:
                for fam in fams:
                    counts[(fam, hb, cat)] += 1
    return counts


# --- rendering ---------------------------------------------------------------

def render(counts: dict[tuple[str, datetime, str], int]) -> None:
    all_hours = sorted({h for (_, h, _) in counts})
    if not all_hours:
        raise RuntimeError("no URL hour buckets found")
    hours = hour_range(all_hours[0], all_hours[-1])

    # Order categories for the stack (top-of-stack last so it draws on top).
    stack_categories: list[tuple[str, str, str]] = []
    for group_name, hue, cats in CATEGORY_GROUPS:
        for i, c in enumerate(cats):
            stack_categories.append((group_name, c,
                                    category_color(hue, i, len(cats))))

    # Emit TSV.
    with (OUT_DIR / "urls_by_task_hour.tsv").open("w") as f:
        f.write("task\thour_utc\tcategory\toccurrences\n")
        for (task, hb, cat), n in sorted(counts.items(),
                                          key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
            f.write(f"{task}\t{hb.strftime('%Y-%m-%dT%H:00Z')}\t{cat}\t{n}\n")

    # Layout.
    W = 1600
    MARGIN_L, MARGIN_R = 120, 380
    MARGIN_T, MARGIN_B = 70, 90
    PANEL_H = 140
    PANEL_GAP = 22
    n_panels = len(PANELS)
    plot_w = W - MARGIN_L - MARGIN_R
    total_h = n_panels * PANEL_H + (n_panels - 1) * PANEL_GAP
    H = MARGIN_T + total_h + MARGIN_B

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="12">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="26" text-anchor="middle" '
        f'font-size="18" font-weight="600" fill="#111">URL occurrences per '
        f'hour, split by task family</text>',
        f'<text x="{(MARGIN_L + plot_w/2):.0f}" y="46" text-anchor="middle" '
        f'fill="#555">Small multiples: one stacked-area panel per task '
        f'family. Bucket = 1 UTC hour. Categories share hue by functional group. '
        f'Per-panel y-max.</text>',
    ]

    # Per-panel data.
    def x_at(i: int) -> float:
        return MARGIN_L + (i + 0.5) * (plot_w / len(hours))

    hour_index = {h: i for i, h in enumerate(hours)}

    def y_at(v: float, y_top: float, y_max: float) -> float:
        if y_max <= 0:
            return y_top + PANEL_H
        return y_top + PANEL_H - PANEL_H * v / y_max

    # X-axis date grid — draw once so all panels line up.
    # Mark the start of each day.
    day_ticks: list[tuple[int, str]] = []
    for i, h in enumerate(hours):
        if h.hour == 0:
            day_ticks.append((i, h.strftime("%m-%d")))
    step = max(1, len(day_ticks) // 20)

    for panel_idx, task in enumerate(PANELS):
        y_top = MARGIN_T + panel_idx * (PANEL_H + PANEL_GAP)

        # Extract series for this task.
        series: dict[str, list[int]] = {c: [0] * len(hours)
                                         for (_, c, _) in stack_categories}
        totals_per_hour = [0] * len(hours)
        total = 0
        for (t, hb, cat), n in counts.items():
            if t != task:
                continue
            i = hour_index.get(hb)
            if i is None:
                continue
            if cat in series:
                series[cat][i] += n
                totals_per_hour[i] += n
                total += n
            else:
                # Unmapped category (should not happen with fixed CATEGORY_GROUPS).
                pass

        y_max_raw = max(totals_per_hour) if totals_per_hour else 0
        # Round up for nicer axis labels.
        y_max = 1 if y_max_raw <= 0 else _nice(y_max_raw)

        # Panel background + border.
        parts.append(
            f'<rect x="{MARGIN_L}" y="{y_top}" width="{plot_w}" '
            f'height="{PANEL_H}" fill="#fbfbfb" stroke="#ddd" '
            f'stroke-width="0.5"/>'
        )
        # Vertical day gridlines.
        for (i, _) in day_ticks:
            x = x_at(i) - (plot_w / len(hours)) / 2  # left edge of that day
            parts.append(
                f'<line x1="{x:.1f}" y1="{y_top}" x2="{x:.1f}" '
                f'y2="{y_top + PANEL_H}" stroke="#eee" stroke-width="0.5"/>'
            )

        # Panel title (left of the panel).
        parts.append(
            f'<text x="{MARGIN_L - 12}" y="{y_top + 14}" text-anchor="end" '
            f'font-weight="600" fill="#111">{escape(task)}</text>'
        )
        parts.append(
            f'<text x="{MARGIN_L - 12}" y="{y_top + 30}" text-anchor="end" '
            f'fill="#666" font-size="11">{total:,} URL occurrences</text>'
        )
        parts.append(
            f'<text x="{MARGIN_L - 12}" y="{y_top + 44}" text-anchor="end" '
            f'fill="#666" font-size="11">y-max = {y_max:,} / hr</text>'
        )

        # Y-axis tick at y_max.
        parts.append(
            f'<text x="{MARGIN_L - 4}" y="{y_top + 8}" text-anchor="end" '
            f'fill="#333" font-size="10">{y_max:,}</text>'
        )
        parts.append(
            f'<text x="{MARGIN_L - 4}" y="{y_top + PANEL_H}" text-anchor="end" '
            f'fill="#333" font-size="10">0</text>'
        )

        # Stack polygons.
        stack_bottom = [0.0] * len(hours)
        for group, cat, color in stack_categories:
            row = series.get(cat)
            if row is None or sum(row) == 0:
                continue
            top = [stack_bottom[i] + row[i] for i in range(len(hours))]
            # Skip whole-zero segments to keep the SVG small: but keep endpoints
            # so polygons connect cleanly.
            pts_top = [(x_at(i), y_at(top[i], y_top, y_max))
                       for i in range(len(hours))]
            pts_bot = [(x_at(i), y_at(stack_bottom[i], y_top, y_max))
                       for i in range(len(hours))]
            pts = pts_top + list(reversed(pts_bot))
            d_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            cat_total = sum(row)
            parts.append(
                f'<polygon points="{d_attr}" fill="{color}" stroke="none">'
                f'<title>{escape(task)} · {escape(cat)}: '
                f'{cat_total:,}</title></polygon>'
            )
            stack_bottom = top

        # Bottom border of panel.
        parts.append(
            f'<line x1="{MARGIN_L}" y1="{y_top + PANEL_H}" '
            f'x2="{MARGIN_L + plot_w}" y2="{y_top + PANEL_H}" '
            f'stroke="#333" stroke-width="0.5"/>'
        )

    # Bottom axis: day-tick labels below the last panel.
    y_axis = MARGIN_T + total_h
    for k, (i, label) in enumerate(day_ticks):
        if k % step != 0 and k != len(day_ticks) - 1:
            continue
        x = x_at(i) - (plot_w / len(hours)) / 2
        parts.append(
            f'<text x="{x:.1f}" y="{y_axis + 14}" text-anchor="end" '
            f'fill="#333" transform="rotate(-60 {x:.1f} {y_axis + 14})">'
            f'{label}</text>'
        )

    # Legend at right.
    lx = MARGIN_L + plot_w + 20
    ly = MARGIN_T
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
        f'categories (stack order top → bottom)</text>'
    )
    ly += 14
    for group_name, hue, cats in CATEGORY_GROUPS:
        ly += 8
        # Total across all panels (URLs are counted per-family, so this
        # column-sum exceeds the raw URL total by the multi-family overlap
        # amount).
        group_total = sum(n for (_, _, c), n in counts.items() if c in cats)
        parts.append(
            f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">'
            f'{escape(group_name)}<tspan fill="#666" font-weight="400">'
            f'  · {group_total:,} incl. multi-family</tspan></text>'
        )
        ly += 6
        # Legend order matches stack order shown top → bottom, so reverse.
        for i, cat in enumerate(reversed(cats)):
            color = category_color(hue, len(cats) - 1 - i, len(cats))
            n = sum(v for (_, _, c), v in counts.items() if c == cat)
            parts.append(
                f'<rect x="{lx}" y="{ly}" width="14" height="12" '
                f'fill="{color}"/>'
            )
            parts.append(
                f'<text x="{lx + 20}" y="{ly + 10}" fill="#111" '
                f'font-size="11">{escape(cat)}'
                f' <tspan fill="#666">· {n:,}</tspan></text>'
            )
            ly += 15
        ly += 2

    ly += 10
    total_urls = sum(counts.values())
    parts.append(
        f'<text x="{lx}" y="{ly}" font-weight="600" fill="#111">notes</text>'
    )
    ly += 14
    for line in [
        f"total URL occurrences (with",
        f"  multi-family overlap): {total_urls:,}",
        f"panels use independent y-axis",
        f"so shape is comparable but",
        f"absolute height is not.",
    ]:
        parts.append(f'<text x="{lx}" y="{ly}" fill="#333">{line}</text>')
        ly += 14

    parts.append("</svg>")
    (OUT_DIR / "urls_stacked_per_task_hourly.svg").write_text("\n".join(parts))


def _nice(v: int) -> int:
    if v <= 0:
        return 1
    for step in [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000,
                 2000, 5000, 10000, 20000]:
        for mult in range(1, 11):
            if step * mult >= v:
                return step * mult
    return v


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rev2fams = load_rev_to_families()
    n_classified = sum(1 for f in rev2fams.values() if f)
    print(f"classified {n_classified:,} of {len(rev2fams):,} revisions",
          file=sys.stderr)
    counts = load_url_hours(rev2fams)
    print(f"produced {len(counts):,} (task, hour, category) rows",
          file=sys.stderr)
    render(counts)
    print(f"wrote {OUT_DIR / 'urls_by_task_hour.tsv'}", file=sys.stderr)
    print(f"wrote {OUT_DIR / 'urls_stacked_per_task_hourly.svg'}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
