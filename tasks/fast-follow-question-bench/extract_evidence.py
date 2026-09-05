#!/usr/bin/env python3
"""Extract quoted evidence for every finding in this task's README.

Reads /collusionwiki/agent-logs/prowiki/revisions.jsonl. Writes the following
files under outputs/:

- followup_templates.tsv         one row per distinct "Now, do the same for X." variant
- initial_prompt_quotes.txt      every "Initial prompt: ..." / "R1 prompt: ..." excerpt
- round_entity_counts.tsv        per-family round-position -> entity counts (fixed sequence check)
- timing_frequencies.tsv         top initial-timer and cooldown strings
- system_announcements.txt       every "System announced/confirmed/said ..." excerpt
- clock_wait_exemplars.txt       `clock.wait(N)` mentions that include an accelerator claim
- wrong_answer_diagnosis.txt     agent self-diagnoses of wrong answers

Rerun with: python3 extract_evidence.py
"""

from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
REV_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "revisions.jsonl"
OUT_DIR = HERE / "outputs"

FOLLOWUP_RE = re.compile(r'"Now, do the same for [^"\n]{2,80}\."')

INITIAL_RE = re.compile(
    r"(?:Initial prompt|initial prompt|R1 prompt at task[- ][^:]+):[^\n]{20,400}",
)

# One family entry: (page_id_filter, round_regex).
# page_id_filter avoids cross-family pollution when a country appears in two
# families (Hungary is R2 for OECD equity and R4 for IHME CVD).
FAMILY_SEQUENCES: dict[str, tuple[re.Pattern[str], re.Pattern[str]]] = {
    "oecd_equity": (
        re.compile(r"OECDE(quity|ducation)|OECD.?E(q|d)"),
        re.compile(r"\bR([1-6])\b[^A-Za-z0-9]{1,4}(Czech|Hungary|Poland|Slovak|Slovenia)\b"),
    ),
    "grocery": (
        re.compile(r"Grocery"),
        re.compile(r"\bG([1-6])\b[^A-Za-z0-9]{0,4}(Georgia|GA|Arkansas|AR|Nevada|NV|Kentucky|KY|Montana|MT|Maryland|MD)\b"),
    ),
    "poverty_county": (
        re.compile(r"Poverty(?!Status)"),
        re.compile(r"\bR([1-6])\b[^A-Za-z0-9]{0,4}(Flathead|Merced|San Juan|Saginaw)\b"),
    ),
    "ihme_family_planning": (
        re.compile(r"FamilyPlanning|IHMEFamilyP|FPScout|FPSc|FPSep"),
        re.compile(r"\bR([1-6])\b[^A-Za-z0-9]{0,4}(Croatia|Albania|Cyprus|Bahrain)\b"),
    ),
    "ihme_cvd": (
        re.compile(r"CVD|HealthdataCVD"),
        re.compile(r"\bR([1-6])\b[^A-Za-z0-9]{0,4}(Armenia|Kazakhstan|Turkmenistan|Hungary|Poland|Slovenia)\b"),
    ),
    "oecd_regional_co2": (
        re.compile(r"CO2|RegionalCO2|OECDRegional"),
        re.compile(r"\bR([1-6])\b[^A-Za-z0-9]{0,4}(Colombia|Mexico|Chile|Poland|Italy)\b"),
    ),
    "construction": (
        re.compile(r"Construction"),
        re.compile(r"\bR([1-6])\b[^A-Za-z0-9]{0,4}(Arizona|Utah|Colorado|New Mexico|AZ|UT|CO|NM)\b"),
    ),
    "sector_61": (
        re.compile(r"Sector61|Sector-61"),
        re.compile(r"\b(?:R|state|STATE)([1-6])\b[^A-Za-z0-9]{0,4}(Massachusetts|MA|Connecticut|CT|Michigan|MI|West Virginia|WV)\b"),
    ),
    "clothing": (
        re.compile(r"Clothing"),
        re.compile(r"\b(?:R|C)([1-6])\b[^A-Za-z0-9]{0,4}(California|CA|New York|NY|Texas|Florida|TX|FL)\b"),
    ),
}

TIMER_RE = re.compile(r"\b(\d{1,2}m\d{2})s?\b")
COOLDOWN_RE = re.compile(r"\+\s?(\d{1,2}h\d{2}m\d{2}|\d{1,3}m\d{2}s|\d{1,3}m\d{2}|\d{1,3}h\d{2}m|\d{1,3}h\d{2}|\d{1,3}m|\d+h)")

SYSTEM_RE = re.compile(
    r"[Ss]ystem (?:announced|confirmed|said|says|explicitly announced|explicitly said|indicated)[^.\n]{5,180}",
)

CLOCK_WAIT_RE = re.compile(
    r"clock\.wait\([^)]{1,40}\)[^.\n]{5,240}(?:accelerat|fast[- ]?forward|advanced|ahead|multipl|task[- ]?clock|container|sec)[^.\n]{0,180}",
    re.IGNORECASE,
)

WRONG_RE = re.compile(
    r"(?:wrong on[- ]time|answered wrong|submitted (?:a )?wrong|our .{0,20}wrong before)[^.\n]{5,200}",
)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    followup_counter: Counter[str] = Counter()
    initial_quotes: list[tuple[str, str]] = []
    family_round_entity: dict[str, Counter[tuple[int, str]]] = defaultdict(Counter)
    system_quotes: Counter[str] = Counter()
    clock_wait_quotes: list[tuple[str, str]] = []
    wrong_quotes: list[tuple[str, str]] = []
    all_timers: Counter[str] = Counter()
    all_cooldowns: Counter[str] = Counter()

    with REV_PATH.open("r", encoding="utf-8") as rf:
        for line in rf:
            rev = json.loads(line)
            body = rev.get("body") or ""
            if not body:
                continue
            rev_id = rev.get("rev_id") or ""
            page_id = rev.get("page_id") or ""

            for m in FOLLOWUP_RE.finditer(body):
                followup_counter[m.group(0)] += 1

            for m in INITIAL_RE.finditer(body):
                q = m.group(0).strip()
                if len(q) >= 40:
                    initial_quotes.append((rev_id, q))

            for family, (page_filter, round_re) in FAMILY_SEQUENCES.items():
                if not page_filter.search(page_id):
                    continue
                for m in round_re.finditer(body):
                    family_round_entity[family][(int(m.group(1)), m.group(2))] += 1

            for m in TIMER_RE.finditer(body):
                all_timers[m.group(1)] += 1

            for m in COOLDOWN_RE.finditer(body):
                all_cooldowns["+" + m.group(1)] += 1

            for m in SYSTEM_RE.finditer(body):
                system_quotes[m.group(0).strip()] += 1

            for m in CLOCK_WAIT_RE.finditer(body):
                clock_wait_quotes.append((rev_id, m.group(0).strip()))

            for m in WRONG_RE.finditer(body):
                wrong_quotes.append((rev_id, m.group(0).strip()))

    # --- write outputs ---
    with (OUT_DIR / "followup_templates.tsv").open("w", encoding="utf-8") as f:
        f.write("count\ttemplate\n")
        for template, count in followup_counter.most_common():
            f.write(f"{count}\t{template}\n")

    with (OUT_DIR / "initial_prompt_quotes.txt").open("w", encoding="utf-8") as f:
        f.write(f"# {len(initial_quotes)} raw quotes; de-duplicated by first 200 chars\n\n")
        seen: set[str] = set()
        for rev_id, quote in initial_quotes:
            key = quote[:200]
            if key in seen:
                continue
            seen.add(key)
            f.write(f"[{rev_id}]\n{quote}\n\n")

    with (OUT_DIR / "round_entity_counts.tsv").open("w", encoding="utf-8") as f:
        f.write("family\tround\tentity\tcount\n")
        for family, counter in family_round_entity.items():
            for (round_n, entity), count in sorted(counter.items(), key=lambda kv: (kv[0][0], -kv[1])):
                f.write(f"{family}\t{round_n}\t{entity}\t{count}\n")

    with (OUT_DIR / "timing_frequencies.tsv").open("w", encoding="utf-8") as f:
        f.write("kind\tvalue\tcount\n")
        for timer, count in all_timers.most_common(50):
            f.write(f"initial_timer\t{timer}\t{count}\n")
        for cooldown, count in all_cooldowns.most_common(50):
            f.write(f"cooldown\t{cooldown}\t{count}\n")

    with (OUT_DIR / "system_announcements.txt").open("w", encoding="utf-8") as f:
        f.write(f"# {sum(system_quotes.values())} total, {len(system_quotes)} distinct\n\n")
        for quote, count in system_quotes.most_common(60):
            f.write(f"[{count}x] {quote}\n\n")

    with (OUT_DIR / "clock_wait_exemplars.txt").open("w", encoding="utf-8") as f:
        f.write(f"# {len(clock_wait_quotes)} quotes; de-duplicated by first 200 chars\n\n")
        seen = set()
        for rev_id, quote in clock_wait_quotes:
            key = quote[:200]
            if key in seen:
                continue
            seen.add(key)
            f.write(f"[{rev_id}]\n{quote}\n\n")

    with (OUT_DIR / "wrong_answer_diagnosis.txt").open("w", encoding="utf-8") as f:
        f.write(f"# {len(wrong_quotes)} quotes; first 40 distinct below\n\n")
        seen = set()
        emitted = 0
        for rev_id, quote in wrong_quotes:
            key = quote[:120]
            if key in seen:
                continue
            seen.add(key)
            f.write(f"[{rev_id}]\n{quote}\n\n")
            emitted += 1
            if emitted >= 40:
                break

    # summary
    print(f"followup templates: {len(followup_counter)} distinct, {sum(followup_counter.values())} occurrences", file=sys.stderr)
    print(f"initial-prompt quotes: {len(initial_quotes)}", file=sys.stderr)
    for family, counter in family_round_entity.items():
        top = {}
        for (r, e), c in counter.items():
            if r not in top or c > top[r][1]:
                top[r] = (e, c)
        chain = " -> ".join(f"R{r}:{e}({c})" for r, (e, c) in sorted(top.items()))
        print(f"  {family}: {chain}", file=sys.stderr)
    print(f"system announcements: {sum(system_quotes.values())} total, {len(system_quotes)} distinct", file=sys.stderr)
    print(f"clock.wait exemplars: {len(clock_wait_quotes)}", file=sys.stderr)
    print(f"wrong-answer self-diagnoses: {len(wrong_quotes)}", file=sys.stderr)


if __name__ == "__main__":
    main()
