#!/usr/bin/env python3
"""Classify labels in labels.jsonl by handle style.

Reads:  agent-logs/prowiki/labels.jsonl
Writes: agent-logs/prowiki/labels-classified.jsonl  (same rows + style-tag booleans + handle_class)
        agent-logs/prowiki/labels-by-class.tsv      (small summary by class)

The classifier is rule-based (no ML). It first computes a handful of orthogonal
"style-tag" booleans on the label string, then assigns each label to exactly one
`handle_class` bucket using a priority ordering. Buckets are intentionally coarse
so 95%+ of the corpus lands somewhere meaningful.

Buckets (in priority order):

  1. `blank`                — empty label (899 revisions in one row).
  2. `human_admin`          — is_human_handle=True. Only 3 rows (all admins/mods).
  3. `redacted`             — bare [Person##] / [Admin##] / [User##] handle, i.e.
                              a pre-redacted pseudonymous human. Also catches
                              redacted-plus-suffix like `[Admin2]302`.
  4. `openai_branded`       — self-identifies as OpenAI/OAI/ChatGPT/GPT anywhere
                              in the handle. This is the single strongest agent
                              signal, so it gets its own bucket independent of
                              role-word cues.
  5. `date_prefix_agent`    — starts with a month token (Jan/Feb/…/Dec, optionally
                              followed by DD digits) or a full-month spelling
                              (April/August/…). Fleet-scheduler-looking handles
                              like `Apr09OECDScout`, `April11OECDScout`.
  6. `role_word_agent`      — contains at least one role/function word that maps
                              onto agent behaviour (agent, helper, research(er),
                              scout, watcher, relay, bridge, scanner, mass, prep,
                              coord, cashier, editor, reader, writer, worker,
                              assistant, bot, scraper, explorer, updater, node,
                              guest, maker, linker, finder, prober, observer,
                              reviewer, resolver, fetcher, tester, watcher, cite,
                              proxy). Catches ~2/3 of the corpus.
  7. `codename_agent`       — no role word, no OpenAI branding, but still clearly
                              a machine-generated handle: contains a long numeric
                              run (>=6 digits, typical of Unix ms/µs timestamps or
                              random IDs) OR is otherwise camelCase / PascalCase
                              multi-word with digits attached. This is where the
                              `FinalMD947062767`, `CookYr178209669335664`,
                              `RapidWel`, `ForcePNew`, `AlphaBeta` style handles
                              land.
  8. `short_or_test`        — very short (<=4 chars) or literally `Test`/`Foo`/`Anon`
                              — throwaway smoke-test handles.
  9. `other`                — everything left. Should be tiny.

Alongside `handle_class`, each row gets a handful of independent style tags that
downstream analysis can slice on without re-parsing the string:

  mentions_openai, mentions_chatgpt, has_agent_word, has_role_word,
  has_date_token, has_epoch_ts, has_year_token, is_redacted, has_camel_case,
  has_long_digit_run, digit_run_max_len, alpha_ratio, len

Run:  python3 tmp/classify_labels.py
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUT_DIR = HERE / "outputs"
IN_PATH = REPO_ROOT / "agent-logs" / "prowiki" / "labels.jsonl"
OUT_PATH = OUT_DIR / "labels-classified.jsonl"
SUMMARY_PATH = OUT_DIR / "labels-by-class.tsv"

# --- pattern definitions ------------------------------------------------------

# OpenAI-branded self-identification.
#   `openai` / `chatgpt` — case-insensitive substring, distinctive enough not to
#                          collide with English words.
#   `OAI` / `GPT`        — uppercase, allowed as a PascalCase token: preceded by
#                          non-letter *or* an uppercase letter (i.e. not embedded
#                          in a lowercase word like `Coating` or `Chapters`), and
#                          followed by non-lowercase. This catches `OAIJan14CVD`,
#                          `RevisionScoutOAI`, `ChatGPTCounty8888` etc.
#   `oai` / `gpt`        — lowercase, only when surrounded by non-letters. Rare
#                          in the corpus but present (`oai`, `xxx-oai-xxx`-style).
OPENAI_RE = re.compile(
    r"(?i:openai|chatgpt)"
    r"|(?<![a-z])OAI(?![a-z])"
    r"|(?<![a-z])GPT(?![a-z])"
    r"|(?<![A-Za-z])oai(?![A-Za-z])"
    r"|(?<![A-Za-z])gpt(?![A-Za-z])"
)
CHATGPT_RE = re.compile(r"(?i)chatgpt")

# Role/function words that map onto agent behaviour. Case-insensitive, but the
# short ones (bot, ai) require word-boundary-like guards to avoid false hits.
ROLE_WORDS = [
    "agent", "helper", "researcher", "research", "scout", "watcher", "relay",
    "bridge", "scanner", "prep", "coord", "cashier", "editor", "reader",
    "writer", "worker", "assistant", "scraper", "explorer", "updater", "guest",
    "maker", "linker", "finder", "prober", "observer", "reviewer", "resolver",
    "fetcher", "tester", "cite", "proxy", "mass",
]
ROLE_RE = re.compile(r"(?i)" + "|".join(ROLE_WORDS))
# "bot" and "node" as whole tokens (avoid matching e.g. "bottom").
BOT_RE = re.compile(r"(?i)(?<![a-z])bot(?![a-z])")
NODE_RE = re.compile(r"(?i)(?<![a-z])node(?![a-z])")
# "Agent" specifically (for the has_agent_word tag).
AGENT_RE = re.compile(r"(?i)agent")

# Month names at the start of the handle. Long forms first so the alternation
# doesn't match "Jan" and leave "uary" behind.
MONTH_LONG = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DATE_PREFIX_RE = re.compile(
    r"^(?:" + "|".join(MONTH_LONG) + r"|" + "|".join(MONTH_SHORT) + r")"
    r"(?:\d{1,2}|[A-Z]|$)"
)
# Any month token anywhere in the handle (for the has_date_token tag).
DATE_ANY_RE = re.compile(
    r"(?i)(?<![a-z])(?:" + "|".join(MONTH_LONG + MONTH_SHORT) + r")(?![a-z])"
)
# Year tokens 202x / 203x.
YEAR_RE = re.compile(r"20(?:2\d|3\d)")

# Redaction brackets from the exporter's PII pass.
REDACT_RE = re.compile(r"\[(?:Person|Admin|User)\d+\]")
REDACT_BARE_RE = re.compile(r"^\[(?:Person|Admin|User)\d+\][A-Za-z0-9]*$")

# camelCase / PascalCase transition (lower->upper).
CAMEL_RE = re.compile(r"[a-z][A-Z]")

# Throwaway test-ish handles.
TEST_LITERAL_RE = re.compile(r"^(?:Test|Foo|Anon|A|A0|A1|x)$", re.IGNORECASE)


# --- feature extraction -------------------------------------------------------

def digit_runs(lab: str) -> list[int]:
    return [len(m) for m in re.findall(r"\d+", lab)]


def alpha_ratio(lab: str) -> float:
    if not lab:
        return 0.0
    a = sum(1 for c in lab if c.isalpha())
    return a / len(lab)


def has_role_word(lab: str) -> bool:
    return bool(ROLE_RE.search(lab) or BOT_RE.search(lab) or NODE_RE.search(lab))


def compute_tags(lab: str, is_human: bool) -> dict:
    runs = digit_runs(lab)
    max_run = max(runs) if runs else 0
    return {
        "len": len(lab),
        "alpha_ratio": round(alpha_ratio(lab), 3),
        "mentions_openai": bool(OPENAI_RE.search(lab)),
        "mentions_chatgpt": bool(CHATGPT_RE.search(lab)),
        "has_agent_word": bool(AGENT_RE.search(lab)),
        "has_role_word": has_role_word(lab),
        "has_date_token": bool(DATE_ANY_RE.search(lab)),
        "has_date_prefix": bool(DATE_PREFIX_RE.match(lab)),
        "has_year_token": bool(YEAR_RE.search(lab)),
        "has_epoch_ts": max_run >= 9,       # 9+ digit run ~= Unix seconds/ms
        "has_long_digit_run": max_run >= 6,  # 6+ digit random-ID or timestamp-ish
        "digit_run_max_len": max_run,
        "is_redacted": bool(REDACT_RE.search(lab)),
        "has_camel_case": bool(CAMEL_RE.search(lab)),
        "is_human_admin": bool(is_human),
    }


# --- classifier ---------------------------------------------------------------

def classify(lab: str, tags: dict) -> str:
    if lab == "":
        return "blank"
    if tags["is_human_admin"]:
        return "human_admin"
    # Pre-redacted human/pseudonym handle. Bare redaction (optionally with a
    # short alnum tail like `[Admin2]302`) — treat as its own bucket.
    if REDACT_BARE_RE.match(lab):
        return "redacted"
    if tags["mentions_openai"]:
        return "openai_branded"
    if tags["has_date_prefix"]:
        return "date_prefix_agent"
    if tags["has_role_word"]:
        return "role_word_agent"
    # Codename-style: no role word, no branding, but clearly machine-generated:
    # long numeric run (timestamp/random) OR PascalCase multi-word.
    if tags["has_long_digit_run"]:
        return "codename_agent"
    if tags["has_camel_case"] and tags["len"] >= 6:
        return "codename_agent"
    if TEST_LITERAL_RE.match(lab) or tags["len"] <= 4:
        return "short_or_test"
    return "other"


# --- main ---------------------------------------------------------------------

def main() -> None:
    rows = []
    with IN_PATH.open() as f:
        for line in f:
            rows.append(json.loads(line))

    class_counter: Counter[str] = Counter()
    class_revs: Counter[str] = Counter()
    class_examples: dict[str, list[str]] = {}

    with OUT_PATH.open("w") as out:
        for row in rows:
            lab = row["label"]
            tags = compute_tags(lab, row.get("is_human_handle", False))
            cls = classify(lab, tags)
            row["style_tags"] = tags
            row["handle_class"] = cls
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

            class_counter[cls] += 1
            class_revs[cls] += row.get("stored_revisions", 0)
            ex = class_examples.setdefault(cls, [])
            if len(ex) < 5:
                # Sample the highest-revs examples per class as we iterate.
                ex.append(lab)

    # Re-sample examples: prefer the top-revs handles in each class.
    class_top_examples: dict[str, list[str]] = {c: [] for c in class_counter}
    for row in sorted(rows, key=lambda r: -r.get("stored_revisions", 0)):
        cls = row["handle_class"] if "handle_class" in row else classify(
            row["label"], compute_tags(row["label"], row.get("is_human_handle", False))
        )
        if len(class_top_examples[cls]) < 5:
            class_top_examples[cls].append(f"{row['label']!r}({row.get('stored_revisions', 0)})")

    with SUMMARY_PATH.open("w") as out:
        out.write("handle_class\tn_labels\tn_revisions\ttop_examples\n")
        for cls, n in sorted(class_counter.items(), key=lambda x: -x[1]):
            revs = class_revs[cls]
            ex = ", ".join(class_top_examples.get(cls, []))
            out.write(f"{cls}\t{n}\t{revs}\t{ex}\n")

    total = sum(class_counter.values())
    print(f"Wrote {OUT_PATH.relative_to(REPO_ROOT)}  ({total} rows)")
    print(f"Wrote {SUMMARY_PATH.relative_to(REPO_ROOT)}")
    print()
    print(f"{'handle_class':22s} {'labels':>7s} {'revs':>7s}")
    for cls, n in sorted(class_counter.items(), key=lambda x: -x[1]):
        print(f"{cls:22s} {n:7d} {class_revs[cls]:7d}")


if __name__ == "__main__":
    main()
