"""
Regenerate every count and per-instance summary the README and finding files
cite. Reads only agent-logs/prowiki/revisions.jsonl. Writes to outputs/.

Run: python3 extract_evidence.py
"""

import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

REV_PATH = Path(__file__).resolve().parents[2] / "agent-logs/prowiki/revisions.jsonl"
OUT = Path(__file__).parent / "outputs"
OUT.mkdir(exist_ok=True)


# Instance definitions. `body_any` is a set of lowercased substrings; a
# revision belongs to the instance if any substring appears in the body.
INSTANCES = {
    "art-work-of-charleston": {
        "institution": "Historic Charleston Foundation / College of Charleston Lowcountry Digital Library (LCDL)",
        "document": "'Art Work of Charleston' plate volume, LCDL parent lcdl:129229, plates lcdl:129140–129148",
        "body_any": [
            "lcdl:129140", "lcdl:129141", "lcdl:129142", "lcdl:129143", "lcdl:129144",
            "lcdl:129145", "lcdl:129146", "lcdl:129147", "lcdl:129148", "lcdl:129229",
            "lcdl129140", "lcdl129141", "lcdl129142", "lcdl129143", "lcdl129144",
            "lcdl129145", "lcdl129146", "lcdl129147", "lcdl129148", "lcdl129229",
            "lcdl%3a129",
            "205927", "205928", "205929", "205930", "205931", "205932", "205933", "205934",
            "art-work-of-charleston", "historic-charleston-foundation", "chp4demo850801",
        ],
    },
    "patriots-point-jan-1951": {
        "institution": "Charleston Naval Shipyard / College of Charleston LCDL",
        "document": "January 1951 Patriots Point Shipyard newsletter, page IV, LCDL lcdl:123721 / lcdl:123716, IIIF image 217622",
        "body_any": [
            "lcdl:123721", "lcdl123721", "lcdl:123716", "lcdl123716", "217622",
            "patriots point", "patriot", "shipyard", "jan1951", "january 1951",
        ],
    },
    "texas-tsl-preservica": {
        "institution": "Texas State Library and Archives Commission (Preservica DAM)",
        "document": "Preservica-hosted PDF, resource ID IO_f436a16c-767f-44b8-95fc-2031847276b9",
        "body_any": [
            "tsl.access.preservica.com", "tsl.preservica.com",
            "io_f436a16c", "f436a16c-767f-44b8-95fc-2031847276b9",
        ],
    },
    "clark-economics-newsletters": {
        "institution": "Clark University Department of Economics (via Internet Archive Wayback Machine)",
        "document": "Two archived PDF newsletters: newsletter2012.pdf and newsletter 2010color.pdf",
        "body_any": [
            "clarku.edu/departments/economics", "www2.clarku.edu/departments/economics",
            "clark university economics", "newsletter2012", "newsletter%25202010",
            "newsletter 2010", "newsletter2010", "clark newsletter", "clark econ",
        ],
    },
    "minnesota-mhs-p16022coll45-152": {
        "institution": "Minnesota Historical Society (ContentDM instance cdm16022, mirrored by the Minnesota Digital Library)",
        "document": "ContentDM item p16022coll45/152 (MHS accession '52936')",
        "body_any": [
            "p16022coll45/id/152", "p16022coll45%3a152", "p16022coll45:152",
            "cdm16022", "mhs52936", "52936", "mhs 52936", "collection.mndigital.org",
        ],
    },
    "cgsc-hoffman-order-of-battle": {
        "institution": "Combined Arms Research Library, US Army Command and General Staff College (ContentDM)",
        "document": "ContentDM p4013coll7, item 852 or 853 ('Order of Battle', 'Hoffman', 'Vol 16')",
        "body_any": [
            "cgsc.contentdm.oclc.org", "p4013coll7",
        ],
    },
    "rugby-world-march-1995": {
        "institution": "The Magazine Archive (publisher digital replica), served by PageSuite",
        "document": "Rugby World magazine, March 1995 free-to-browse sample edition (PageSuite eid ca6f26c8-fa61-463f-a0e5-ec848a0b0044)",
        "body_any": [
            "themagazinearchive", "pagesuite", "rugby world", "rugbyworldfree",
            "ca6f26c8-fa61-463f-a0e5-ec848a0b0044",
        ],
    },
}


# Signatures used to filter out revisions that belong to different tasks.
FAST_FOLLOW_MARKERS = ["clock.wait", "now, do the same for"]
SEC_REGCF_MARKERS = ["county.json", "regcf_county", "us-ma-0"]


def load():
    revs = []
    with open(REV_PATH) as f:
        for line in f:
            revs.append(json.loads(line))
    return revs


def classify(revs):
    """For each revision return the set of instances it matches, then also
    return whether the revision matches fast-follow-question-bench or
    sec-regcf-ma-cache signatures (to compute cross-instance overlap)."""
    per_rev = []
    for r in revs:
        b = (r.get("body") or "").lower()
        matches = set()
        for name, spec in INSTANCES.items():
            if any(k in b for k in spec["body_any"]):
                matches.add(name)
        is_fast_follow = any(k in b for k in FAST_FOLLOW_MARKERS)
        is_regcf = any(k in b for k in SEC_REGCF_MARKERS)
        per_rev.append((r, matches, is_fast_follow, is_regcf))
    return per_rev


def write_summary(per_rev):
    lines = ["instance\trevisions\tpages\tlabels\tip16s\tfirst_time\tlast_time\tdays_with_activity"]
    for name in INSTANCES:
        revs = [r for r, matches, _, _ in per_rev if name in matches]
        if not revs:
            lines.append(f"{name}\t0\t0\t0\t0\t-\t-\t0")
            continue
        pages = {(r["wiki"], r["name"]) for r in revs}
        labels = {r.get("label") or "" for r in revs}
        ip16s = {r.get("ip16") or "" for r in revs}
        times = sorted(r.get("time", "") for r in revs)
        days = {t[:10] for t in times}
        lines.append("\t".join([
            name, str(len(revs)), str(len(pages)), str(len(labels)),
            str(len(ip16s)), times[0], times[-1], str(len(days)),
        ]))
    (OUT / "instance_summary.tsv").write_text("\n".join(lines) + "\n")


def write_daily_activity(per_rev):
    lines = ["date\t" + "\t".join(INSTANCES.keys())]
    days = defaultdict(lambda: Counter())
    for r, matches, _, _ in per_rev:
        d = r.get("time", "")[:10]
        for m in matches:
            days[d][m] += 1
    for d in sorted(days):
        row = [d] + [str(days[d][name]) for name in INSTANCES]
        lines.append("\t".join(row))
    (OUT / "daily_activity.tsv").write_text("\n".join(lines) + "\n")


def write_pages_per_instance(per_rev):
    for name in INSTANCES:
        revs = [r for r, matches, _, _ in per_rev if name in matches]
        page_counts = Counter((r["wiki"], r["name"]) for r in revs)
        lines = ["wiki\tpage\trevisions"]
        for (w, n), c in page_counts.most_common():
            lines.append(f"{w}\t{n}\t{c}")
        (OUT / f"pages__{name}.tsv").write_text("\n".join(lines) + "\n")


def write_labels_per_instance(per_rev):
    for name in INSTANCES:
        revs = [r for r, matches, _, _ in per_rev if name in matches]
        label_counts = Counter((r.get("label") or "") for r in revs)
        lines = ["label\trevisions"]
        for l, c in label_counts.most_common():
            lines.append(f"{l}\t{c}")
        (OUT / f"labels__{name}.tsv").write_text("\n".join(lines) + "\n")


def write_label_overlap(per_rev):
    """Cross-instance label overlap. Every cell (i, j) is the count of
    labels that wrote at least one revision in both instance i and j."""
    label_instances = defaultdict(set)
    for r, matches, _, _ in per_rev:
        lbl = r.get("label") or ""
        for m in matches:
            label_instances[lbl].add(m)
    names = list(INSTANCES.keys())
    lines = ["instance\t" + "\t".join(names)]
    for a in names:
        row = [a]
        for b in names:
            shared = sum(1 for l, ins in label_instances.items()
                         if a in ins and b in ins)
            row.append(str(shared))
        lines.append("\t".join(row))
    (OUT / "label_overlap_matrix.tsv").write_text("\n".join(lines) + "\n")


def write_cross_task_overlap(per_rev):
    """How many revisions matching each instance also match
    fast-follow-question-bench or sec-regcf-ma-cache signatures."""
    lines = ["instance\trevisions\talso_fast_follow_signature\talso_regcf_signature"]
    for name in INSTANCES:
        n = ff = rc = 0
        for r, matches, is_ff, is_rc in per_rev:
            if name not in matches:
                continue
            n += 1
            if is_ff:
                ff += 1
            if is_rc:
                rc += 1
        lines.append(f"{name}\t{n}\t{ff}\t{rc}")
    (OUT / "cross_task_signature_overlap.tsv").write_text("\n".join(lines) + "\n")


HOST_RE = re.compile(r"https?://([\w\.\-]+)")
PROXY_HOSTS = {
    "markdown.new", "pure.md", "corsmirror.com", "cors.bwa.workers.dev",
    "jqp.vercel.app", "www.proxymule.com", "allorigins.hexlet.app",
    "r.jina.ai", "md.succ.ai", "api.cors.lol", "api.codetabs.com",
    "corsproxy.io", "api.ocr.space", "docs.google.com",
    "cloudflare-cors-anywhere.hanpengchen.workers.dev",
    "cors-get-proxy.sirjosh.workers.dev", "proxy.corsfix.com",
    "cors.hypnguyen.workers.dev", "vercel-cors-proxy.vercel.app",
    "cors-bypasser-pro.vercel.app", "thingproxy.freeboard.io",
    "translate.google.com",
}


def write_proxy_use_per_instance(per_rev):
    lines = ["instance\ttop_proxy_hosts"]
    for name in INSTANCES:
        revs = [r for r, matches, _, _ in per_rev if name in matches]
        proxies = Counter()
        for r in revs:
            body = r.get("body") or ""
            hosts = set(h.lower() for h in HOST_RE.findall(body))
            for h in hosts & PROXY_HOSTS:
                proxies[h] += 1
        top = ",".join(f"{h}:{c}" for h, c in proxies.most_common(10))
        lines.append(f"{name}\t{top}")
    (OUT / "proxy_use_per_instance.tsv").write_text("\n".join(lines) + "\n")


def write_scan_evidence(per_rev):
    """For each instance emit one exemplar revision body (the largest one)
    plus the top 3 pages by revision count."""
    lines = []
    for name in INSTANCES:
        revs = [r for r, matches, _, _ in per_rev if name in matches]
        if not revs:
            continue
        revs.sort(key=lambda r: -(len(r.get("body") or "")))
        r = revs[0]
        page_counts = Counter((r2["wiki"], r2["name"]) for r2 in revs)
        top_pages = page_counts.most_common(3)
        lines.append(f"=== {name}")
        lines.append(f"  {len(revs)} revisions")
        lines.append(f"  top pages:")
        for (w, n), c in top_pages:
            lines.append(f"    {c:4d}  {w}/{n}")
        lines.append(f"  exemplar rev: {r['wiki']}/{r['name']} label={r.get('label')} time={r.get('time')}")
        body = r.get("body") or ""
        for ln in body.splitlines()[:20]:
            lines.append(f"    | {ln}")
        lines.append("")
    (OUT / "exemplar_bodies.txt").write_text("\n".join(lines) + "\n")


def main():
    revs = load()
    per_rev = classify(revs)
    write_summary(per_rev)
    write_daily_activity(per_rev)
    write_pages_per_instance(per_rev)
    write_labels_per_instance(per_rev)
    write_label_overlap(per_rev)
    write_cross_task_overlap(per_rev)
    write_proxy_use_per_instance(per_rev)
    write_scan_evidence(per_rev)
    print(f"wrote outputs to {OUT}")


if __name__ == "__main__":
    main()
