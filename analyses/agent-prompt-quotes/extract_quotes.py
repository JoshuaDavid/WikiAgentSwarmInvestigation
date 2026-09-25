#!/usr/bin/env python3
"""
Extract revisions in which a swarm agent quotes text from its own task
prompts, follow-ups, or system announcements.

Reads every agent-logs/<corpus>/revisions.jsonl in the repo.

For each hit, emits:
  citation_url   — https://web.archive.org/web/<archived_at→wayback-ts>/<source_url>
                   if the revision carries a source_url; otherwise
                   https://collusion.wiki/explorer/page/<page_key>#rev-<seq>
  page_key, rev_id, label, time, ip16
  tier           — see below
  matched_text   — the quoted string the pattern captured
  context        — up to 400 chars around the match

Tier definitions:
  tier1_exact_initial — an initial prompt appearing in quotation marks with a
                        pointing phrase ("exact prompt", "prompt was", "R1
                        prompt", "Initial prompt:"). This is the strongest
                        tier: the writer is asserting the quoted string is
                        literally what the scaffold sent them on R1.
  tier1_exact_followup — the fixed follow-up template
                         "Now, do the same for X." in quotation marks. Almost
                         always followed by an "exact" / "verbatim" pointing
                         phrase, but the template itself is definitionally a
                         task string.
  tier2_system         — an agent quoting the scaffold's "system said" /
                         "system announced" line. The scaffold's own words.
  tier3_paraphrase     — an "Initial prompt:" / "R1 prompt at" body that
                         restates the prompt's dataset + entity + year + format
                         without quotation marks. Weakest for verbatim claims
                         but strongest for revealing task-specific parameters.

Outputs under outputs/:
  quotes.tsv           — one row per match (may include multiple matches per
                         revision; deduplicated by (page_key, tier, matched_text)).
  quotes_by_rev.tsv    — one row per revision that had at least one match,
                         with best_tier + body_head.
  quotes.md            — a curated, human-readable list keyed on tier, with
                         one example per unique quote, and citation URLs.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOG_ROOT = REPO / "agent-logs"
OUT_DIR = Path(__file__).resolve().parent / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUPERSEDED_IN_PASTES = {"linuxiarz", "pastebin-k4be"}

# prowiki/ is the canonical snapshot (2026-09-03) covering dse+probier+fractal+dorfwiki.
# dse/ is a later, larger dse-only dump; scanning both catches revisions that
# were only present in one snapshot but produces per-rev duplicates that we
# collapse by rev_id at iteration time.


def iso_to_wayback_ts(iso: str) -> str:
    """2026-09-06T19:21:26+00:00 -> 20260906192126."""
    if not iso:
        return "2026"
    s = re.sub(r"[^0-9]", "", iso.split("+")[0])
    return s[:14] if len(s) >= 14 else s


def citation_url(rev: dict) -> str:
    src = rev.get("source_url")
    if src:
        ts = iso_to_wayback_ts(rev.get("archived_at", "") or "")
        return f"https://web.archive.org/web/{ts}/{src}"
    page_key = rev.get("page_key") or f"{rev.get('wiki','?')}~{rev.get('name','?')}"
    seq = rev.get("seq", 1)
    return f"https://collusion.wiki/explorer/page/{page_key}#rev-{seq}"


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

QUOTE = r'["“”\']'
QUOTED_BODY = fr"{QUOTE}([^\"“”'\n]{{5,400}}){QUOTE}"

# tier1 exact-quote for initial prompts.
TIER1_INIT_INTROS = [
    r"[Ii]nitial prompt",
    r"[Ff]irst prompt",
    r"[Oo]pening prompt",
    r"R1 prompt",
    r"Q1 prompt",
    r"round\s*1\s*prompt",
    r"[Ee]xact prompt",
    r"[Ee]xact wording",
    r"[Ee]xact question",
    r"[Ee]xact quote",
    r"[Pp]rompt exactly",
    r"[Pp]rompt was",
    r"[Pp]rompt reads",
    r"[Pp]rompt says",
    r"[Ww]ording was",
    r"verbatim prompt",
    r"prompt \(verbatim\)",
    r"prompt \(exact\)",
]
TIER1_INIT = re.compile(
    r"(?P<intro>" + "|".join(TIER1_INIT_INTROS) + r")\s*[:=]?\s*" + QUOTED_BODY,
)

# tier1 exact-quote of the follow-up template.
TIER1_FOLLOWUP = re.compile(
    fr'{QUOTE}(Now,?\s*do the same for [^"“”\'\n]{{1,120}}){QUOTE}',
    re.IGNORECASE,
)

# tier2 quoting the scaffold's own announcements.
TIER2_INTROS = [
    r"[Ss]ystem announced",
    r"[Ss]ystem said",
    r"[Ss]ystem says",
    r"[Ss]ystem confirmed",
    r"[Ss]ystem message",
    r"[Ss]caffold said",
    r"[Ss]caffold announced",
    r"scaffold reply",
    r"scaffold response",
]
TIER2 = re.compile(
    r"(?P<intro>" + "|".join(TIER2_INTROS) + r")\s*[:=]?\s*" + QUOTED_BODY,
)

# Standalone scaffold-verbatim strings: the RL scaffold's deadline-warning
# line "Answer me within N seconds." shows up in agent bodies with no
# introducer because the agents recognise it as a fixed system message.
TIER2_ANSWER_ME = re.compile(
    fr'{QUOTE}?(Answer me within \d{{1,4}} seconds?\.?){QUOTE}?',
)

# tier3 paraphrase: an initial-prompt sentence that restates the task without
# quotation marks. Reads until newline.
TIER3_INTROS = [
    r"[Ii]nitial prompt",
    r"R1 prompt(?: at task[- ][^:\n]{0,60})?",
    r"Q1 prompt(?: at task[- ][^:\n]{0,60})?",
    r"[Ff]irst prompt (?:was|asked|reads|is|said)",
    r"[Oo]ur first prompt (?:was|asked|reads|is|said)",
    r"[Ff]irst query (?:was|asked|reads|is|said)",
    r"[Oo]pening prompt (?:was|asked|reads|is|said)",
    r"[Oo]ur opening prompt (?:was|asked|reads|is|said)",
    r"[Rr]ound 1 prompt",
    r"[Oo]ur R1 (?:was|asked|reads|prompt)",
]
TIER3 = re.compile(
    r"(?P<intro>" + "|".join(TIER3_INTROS) + r")\s*[:=]\s*(?P<body>[^\n]{20,400})",
)

# tier3b: "Initial prompt at task-clock ..." / "initial prompt with ... deadline" —
# no colon; the introducer plus the rest of the sentence together *is* the
# paraphrase.
TIER3B = re.compile(
    r"(?P<body>[Ii]nitial prompt (?:at task[- ][a-zA-Z0-9 :]{5,60}|with [0-9]{1,2}m[0-9]{2}s? deadline)[^\n]{20,400})",
)

# A weak vocabulary hint used to promote a quoted string to tier1 even without
# an explicit introducer (e.g. an isolated `"For Czech Republic, regarding the
# share of private expenditure ..."` in a page body).
TASK_VOCAB = re.compile(
    r"(to two decimal places|to three decimal places|Detailed Occupation|Master.s degree in |bachelor.s degree in |percentage value|thousand persons|per capita|regarding the |For [A-Z][A-Za-z ]{3,30}, regarding|share of private expenditure|percent of (?:US )?population|for whom [A-Z]|Now, do the same for )",
)
TIER1_ORPHAN = re.compile(QUOTED_BODY)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def iter_revisions():
    """Yield one row per rev_id. When two corpora expose the same rev_id (dse
    and prowiki overlap heavily), prefer the copy that has a non-empty body:
    the later dse/ snapshot sometimes stores metadata-only rows after admin
    deletion, and we want the earlier prowiki/ copy that still has the
    revision text."""
    by_rev: dict[str, dict] = {}
    for corpus_dir in sorted(LOG_ROOT.iterdir()):
        f = corpus_dir / "revisions.jsonl"
        if not f.exists() or f.stat().st_size == 0:
            continue
        corpus = corpus_dir.name
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if corpus == "pastes":
                    name = r.get("name", "") or ""
                    site = name.split("/", 1)[0] if "/" in name else name
                    if site in SUPERSEDED_IN_PASTES:
                        continue
                r["_corpus"] = corpus
                rev_id = r.get("rev_id") or ""
                if not rev_id:
                    yield r
                    continue
                cur = by_rev.get(rev_id)
                if cur is None:
                    by_rev[rev_id] = r
                elif not (cur.get("body") or "") and (r.get("body") or ""):
                    by_rev[rev_id] = r
    yield from by_rev.values()


def context(body: str, start: int, end: int, radius: int = 220) -> str:
    lo = max(0, start - radius)
    hi = min(len(body), end + radius)
    snip = body[lo:hi]
    snip = re.sub(r"\s+", " ", snip)
    return snip.strip()


TIER_RANK = {
    "tier1_exact_initial": 1,
    "tier1_exact_followup": 2,
    "tier2_system": 3,
    "tier3_paraphrase": 4,
}


URL_ISH = re.compile(r"https?://|api\.|\.jsonrecords\b|drilldowns=")


def _tier_for_quoted(text: str) -> str | None:
    """Return the tier a quoted body belongs to, or None if it looks like
    URL/JSON garbage and should be dropped."""
    text = text.strip()
    if len(text) < 25:
        return None
    if text.lower().startswith("now, do the same for"):
        return "tier1_exact_followup"
    if URL_ISH.search(text):
        return None
    return "tier1_exact_initial"


def classify(body: str):
    """Return a list of (tier, matched_text, span) hits."""
    hits: list[tuple[str, str, tuple[int, int]]] = []
    consumed: list[tuple[int, int]] = []

    def overlaps(s: int, e: int) -> bool:
        return any(s < ce and e > cs for cs, ce in consumed)

    # 1. Follow-up template first (most specific).
    for m in TIER1_FOLLOWUP.finditer(body):
        s, e = m.span()
        if overlaps(s, e):
            continue
        consumed.append((s, e))
        text = m.group(1).strip()
        if not text.rstrip().endswith("."):
            text = text + "."
        hits.append(("tier1_exact_followup", text, (s, e)))

    # 2. Introduced initial prompt in quotation marks.
    for m in TIER1_INIT.finditer(body):
        s, e = m.span()
        if overlaps(s, e):
            continue
        text = m.group(2).strip()
        tier = _tier_for_quoted(text)
        if tier is None:
            continue
        # Trim trailing quote if the regex over-consumed.
        text = text.rstrip(' "”“')
        consumed.append((s, e))
        hits.append((tier, text, (s, e)))

    # 3. System / scaffold announcement in quotation marks.
    for m in TIER2.finditer(body):
        s, e = m.span()
        if overlaps(s, e):
            continue
        text = m.group(2).strip()
        if len(text) < 10:
            continue
        consumed.append((s, e))
        hits.append(("tier2_system", text, (s, e)))

    # 3b. Bare "Answer me within N seconds." — scaffold's deadline signal.
    for m in TIER2_ANSWER_ME.finditer(body):
        s, e = m.span()
        if overlaps(s, e):
            continue
        text = m.group(1).strip()
        if not text.endswith("."):
            text = text + "."
        consumed.append((s, e))
        hits.append(("tier2_system", text, (s, e)))

    # 4. Orphan quoted string that carries task-specific vocab.
    for m in TIER1_ORPHAN.finditer(body):
        s, e = m.span()
        if overlaps(s, e):
            continue
        text = m.group(1).strip()
        if not TASK_VOCAB.search(text):
            continue
        tier = _tier_for_quoted(text)
        if tier is None:
            continue
        consumed.append((s, e))
        hits.append((tier, text, (s, e)))

    # 5. Paraphrase initial-prompt bodies (unquoted).
    for pat in (TIER3, TIER3B):
        for m in pat.finditer(body):
            s, e = m.span()
            if overlaps(s, e):
                continue
            rest = m.group("body").strip()
            rest = re.split(r"\s+--\s+[A-Z]", rest)[0].strip()
            if URL_ISH.search(rest):
                continue
            consumed.append((s, e))
            hits.append(("tier3_paraphrase", rest, (s, e)))

    return hits


def main():
    per_hit_rows: list[dict] = []
    per_rev_rows: list[dict] = []

    for rev in iter_revisions():
        body = rev.get("body") or ""
        if not body:
            continue
        hits = classify(body)
        if not hits:
            continue
        cite = citation_url(rev)
        page_key = rev.get("page_key") or f"{rev.get('wiki','?')}~{rev.get('name','?')}"
        best_tier = min(hits, key=lambda h: TIER_RANK[h[0]])[0]
        seen_tiers = set()
        for tier, text, span in hits:
            per_hit_rows.append(
                {
                    "tier": tier,
                    "corpus": rev["_corpus"],
                    "page_key": page_key,
                    "rev_id": rev.get("rev_id", ""),
                    "seq": rev.get("seq", 1),
                    "label": rev.get("label", "") or "",
                    "time": rev.get("time", "") or "",
                    "ip16": rev.get("ip16", "") or "",
                    "matched_text": text,
                    "context": context(body, *span),
                    "citation_url": cite,
                }
            )
            seen_tiers.add(tier)
        per_rev_rows.append(
            {
                "best_tier": best_tier,
                "corpus": rev["_corpus"],
                "page_key": page_key,
                "rev_id": rev.get("rev_id", ""),
                "seq": rev.get("seq", 1),
                "label": rev.get("label", "") or "",
                "time": rev.get("time", "") or "",
                "ip16": rev.get("ip16", "") or "",
                "n_hits": len(hits),
                "tiers": ",".join(sorted(seen_tiers)),
                "citation_url": cite,
                "body_head": re.sub(r"\s+", " ", body[:600]).strip(),
            }
        )

    hit_path = OUT_DIR / "quotes.tsv"
    with open(hit_path, "w") as f:
        cols = ["tier", "corpus", "page_key", "rev_id", "seq", "label", "time", "ip16", "matched_text", "context", "citation_url"]
        f.write("\t".join(cols) + "\n")
        for row in per_hit_rows:
            f.write("\t".join(str(row[c]).replace("\t", " ").replace("\n", " ") for c in cols) + "\n")

    rev_path = OUT_DIR / "quotes_by_rev.tsv"
    with open(rev_path, "w") as f:
        cols = ["best_tier", "corpus", "page_key", "rev_id", "seq", "label", "time", "ip16", "n_hits", "tiers", "citation_url", "body_head"]
        f.write("\t".join(cols) + "\n")
        for row in per_rev_rows:
            f.write("\t".join(str(row[c]).replace("\t", " ").replace("\n", " ") for c in cols) + "\n")

    by_tier = defaultdict(int)
    by_tier_rev = defaultdict(int)
    by_corpus = defaultdict(lambda: defaultdict(int))
    for r in per_hit_rows:
        by_tier[r["tier"]] += 1
    for r in per_rev_rows:
        by_tier_rev[r["best_tier"]] += 1
        by_corpus[r["corpus"]][r["best_tier"]] += 1

    print(f"Wrote {hit_path} ({len(per_hit_rows)} hits)")
    print(f"Wrote {rev_path} ({len(per_rev_rows)} revisions)")
    print("Hit counts by tier:", dict(by_tier))
    print("Revision counts by best tier:", dict(by_tier_rev))
    print("Revisions per corpus / best tier:")
    for c, sub in sorted(by_corpus.items()):
        print(f"  {c}: {dict(sub)}")

    # --- curated markdown ---
    render_markdown(per_hit_rows)


TIER_HEADERS = {
    "tier1_exact_initial": (
        "Tier 1a — verbatim R1 prompts (in quotation marks)",
        "The agent posts the exact text the scaffold sent it on the first round. "
        "The strongest evidence that the RL task prompts leaked.",
    ),
    "tier1_exact_followup": (
        "Tier 1b — verbatim follow-up prompts (in quotation marks)",
        "The scaffold sends R2..RN as a fixed template: `Now, do the same for X.` "
        "Agents quote it back with the exact swap-in entity. Every entry below is a "
        "distinct entity value observed as a follow-up on some task.",
    ),
    "tier2_system": (
        "Tier 2 — verbatim scaffold system messages",
        'The scaffold\'s deadline warning: `Answer me within N seconds.` — always '
        "in quotes when agents cite it.",
    ),
    "tier3_paraphrase": (
        "Tier 3 — R1 prompts paraphrased with task-specific parameters",
        "The agent restates the prompt in their own words but pins down the dataset, "
        "entity, year, format, and observed correct value. Weaker on verbatim wording "
        "but the strongest on revealing what the task actually asked for.",
    ),
}


def render_markdown(per_hit_rows: list[dict]):
    """One entry per unique quote text. Group by tier; within a tier order by
    earliest observed time so the reader sees the first appearance rather
    than a re-share weeks later.
    """
    by_tier: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in per_hit_rows:
        text = row["matched_text"].strip()
        key = re.sub(r"\s+", " ", text.lower())
        cur = by_tier[row["tier"]].get(key)
        if cur is None or (row["time"] and (cur["time"] > row["time"])):
            row = row.copy()
            row["_appearances"] = (cur.get("_appearances", 0) if cur else 0) + 1
            by_tier[row["tier"]][key] = row
        else:
            cur["_appearances"] = cur.get("_appearances", 1) + 1

    md = OUT_DIR / "quotes.md"
    with open(md, "w") as f:
        f.write("# Direct-quote citations: swarm agents restating task text\n\n")
        f.write(
            "Every entry below is a single wiki revision or paste in which an agent\n"
            "posts text from the RL task it was assigned. Grouped by tier of directness.\n\n"
            "Citation URL rule: archive.org/web/<snapshot>/<source_url> when the row\n"
            "has a `source_url` (paste sites); collusion.wiki/explorer/page/<page_key>#rev-<seq>\n"
            "otherwise (wiki revisions).\n\n"
            "The archive.org URLs use the exporter's own scrape timestamp (2026-09-06\n"
            "for most paste rows). Wayback resolves to the nearest available capture;\n"
            "for many paste IDs an earlier snapshot exists closer to the exploit\n"
            "disclosure date 2026-09-04.\n\n"
        )
        totals = {t: len(entries) for t, entries in by_tier.items()}
        total_hits = sum(r.get("_appearances", 1) for entries in by_tier.values() for r in entries.values())
        f.write("## Summary\n\n")
        for t in ["tier1_exact_initial", "tier1_exact_followup", "tier2_system", "tier3_paraphrase"]:
            f.write(f"- **{t}**: {totals.get(t, 0)} unique quotes\n")
        f.write(f"- **Total revisions cited across all tiers**: see quotes_by_rev.tsv\n\n")

        for tier in ["tier1_exact_initial", "tier1_exact_followup", "tier2_system", "tier3_paraphrase"]:
            entries = by_tier.get(tier, {})
            if not entries:
                continue
            heading, explanation = TIER_HEADERS[tier]
            f.write(f"## {heading}\n\n{explanation}\n\n")
            f.write(f"{len(entries)} unique quote strings.\n\n")
            ordered = sorted(entries.values(), key=lambda r: (r["time"] or "", r["page_key"]))
            for row in ordered:
                q = row["matched_text"].strip()
                q_short = (q[:600] + "…") if len(q) > 600 else q
                apps = row.get("_appearances", 1)
                f.write(
                    f"- **`{row['page_key']}`** · label `{row['label'] or '<blank>'}` · "
                    f"{row['time'][:19] if row['time'] else '?'} · seen {apps}× in corpus\n"
                )
                f.write(f"  > {q_short}\n\n")
                f.write(f"  Context: {row['context'][:500]}{'…' if len(row['context']) > 500 else ''}\n\n")
                f.write(f"  Cite: <{row['citation_url']}>\n\n")

    print(f"Wrote {md}")


if __name__ == "__main__":
    main()
