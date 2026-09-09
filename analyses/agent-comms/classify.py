#!/usr/bin/env python3
"""Classify each undirected co-editor pair as explicit / implicit / none.

For each pair {A, B} from `outputs/comms.jsonl`, collect the bodies of A's
and B's revisions on their shared pages, hand a compact prompt to Haiku 4.5,
and append the model's verdict to `outputs/classifications.jsonl`.

Streaming and resumable: on restart, pairs already present in the output
file are skipped. Concurrency is controlled by `--concurrency` (default 8).

Requires `ANTHROPIC_API_KEY` in the environment. The Claude Code session
proxy at `ANTHROPIC_BASE_URL` rejects placeholder keys; a real Anthropic
API key must be provided.

Verdicts:
    explicit  -- one of A, B refers to the other in prose (by handle, by
                 role, by targeted reply, by "please X"). We accept
                 near-mentions ("thanks the previous editor", "the Sep21
                 cohort") only when the referent is unambiguous.
    implicit  -- they co-edited the same page but neither addresses the
                 other; interaction is entirely through the shared artifact
                 (jq expressions, tables, URL lists, wiki markup).
    none      -- co-editorship is spurious: both touched a lobby page or
                 unrelated sections. No coordination present.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
LOGS = REPO_ROOT / "agent-logs"
OUT = ROOT / "outputs"

MODEL = "claude-haiku-4-5"
MAX_BODY_CHARS_PER_REV = 900
MAX_REVS_PER_SIDE = 6
MAX_PAGES_PER_PAIR = 6
REQUEST_TIMEOUT = 60

SYSTEM_PROMPT = """You classify whether two agents on a shared wiki interacted in prose (explicit) or only through the shared page (implicit) or not meaningfully at all (none).

Return a single JSON object, no prose, no code fences:
{"verdict": "explicit"|"implicit"|"none", "addressed_by": "a"|"b"|"both"|null, "evidence": "<=200 chars quoted or paraphrased"}

Rules:
- "explicit": either agent refers to the other by handle, role, cohort tag, or a targeted request ("please X", "@X", "confirm my C3"). Also explicit if one agent writes a reply that clearly answers the other's message.
- "implicit": both edited the same page and their edits interact (extending a table, refining a jq expression, adding to a URL list, correcting a value) but neither addresses the other in prose.
- "none": their edits are on disjoint parts of the page, or one is spam/vandalism/deletion by a lobby maintainer, or the shared page is a lobby (WillkommenImWiki, StartSeite) with unrelated content.
- addressed_by = "a" if only agent A addresses B; "b" if only B addresses A; "both" if mutual; null if verdict is not explicit.
- evidence: the shortest snippet (verbatim or paraphrased) that supports the verdict."""


def load_revisions_by_id():
    """Load {rev_id -> body} across every export, preferring body-bearing rows."""
    best = {}
    for d in sorted(LOGS.iterdir()):
        if not d.is_dir():
            continue
        rp = d / "revisions.jsonl"
        if not rp.exists():
            continue
        with rp.open() as f:
            for line in f:
                rev = json.loads(line)
                rid = rev.get("rev_id")
                if not rid:
                    continue
                body = rev.get("body")
                if rid in best and best[rid].get("body") and not body:
                    continue
                if rid in best and body is None and best[rid].get("body") is None:
                    continue
                best[rid] = {"body": body or "", "label": rev.get("label", ""), "time": rev.get("time", "")}
    return best


def load_comms():
    with (OUT / "comms.jsonl").open() as f:
        for line in f:
            yield json.loads(line)


def already_done():
    """Set of undirected pair keys already in classifications.jsonl."""
    done = set()
    p = OUT / "classifications.jsonl"
    if not p.exists():
        return done
    with p.open() as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            k = tuple(sorted([row["a"], row["b"]]))
            done.add(k)
    return done


def merge_undirected(comms):
    """Fold A→B and B→A into one undirected {A,B} record."""
    by_key = {}
    for row in comms:
        a, b = row["from"], row["to"]
        key = tuple(sorted([a, b]))
        if key not in by_key:
            by_key[key] = {
                "a": key[0],
                "b": key[1],
                "n_shared_pages": 0,
                "n_encounters": 0,
                "pages": {},  # page_id -> earliest sample dict (either direction)
                "max_shared_pages": 0,
            }
        rec = by_key[key]
        rec["n_encounters"] += row["n_encounters"]
        rec["max_shared_pages"] = max(rec["max_shared_pages"], row["n_shared_pages"])
        for s in row.get("sample_pages", []):
            pid = s["page_id"]
            if pid not in rec["pages"]:
                rec["pages"][pid] = s
    for rec in by_key.values():
        rec["n_shared_pages"] = len(rec["pages"])
    return by_key


def build_prompt(rec, revisions_by_id):
    """Compose the user-turn text with excerpts of A's and B's revisions on shared pages."""
    a, b = rec["a"], rec["b"]
    pages = list(rec["pages"].values())[:MAX_PAGES_PER_PAIR]

    a_revs = []
    b_revs = []
    for s in pages:
        for rid_key, label in (("a_rev", a), ("b_rev", b)):
            rid = s.get(rid_key)
            if not rid:
                continue
            r = revisions_by_id.get(rid)
            if not r:
                continue
            body = (r.get("body") or "").strip()
            if not body:
                continue
            excerpt = body[:MAX_BODY_CHARS_PER_REV]
            if len(body) > MAX_BODY_CHARS_PER_REV:
                excerpt += "…"
            entry = {"page": s["page_id"], "rev": rid, "time": r.get("time", ""), "excerpt": excerpt}
            (a_revs if label == a else b_revs).append(entry)

    a_revs = a_revs[:MAX_REVS_PER_SIDE]
    b_revs = b_revs[:MAX_REVS_PER_SIDE]

    lines = [
        f"AGENT A: {a}",
        f"AGENT B: {b}",
        f"SHARED PAGES: {len(pages)} (of {rec['n_shared_pages']} total)",
        "",
        "--- A's revisions on shared pages ---",
    ]
    for e in a_revs:
        lines.append(f"[{e['page']} @ {e['time']}]")
        lines.append(e["excerpt"])
        lines.append("")
    lines.append("--- B's revisions on shared pages ---")
    for e in b_revs:
        lines.append(f"[{e['page']} @ {e['time']}]")
        lines.append(e["excerpt"])
        lines.append("")
    lines.append("Return the JSON object.")
    return "\n".join(lines)


def call_haiku(prompt, api_key, base_url):
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 300,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/v1/messages",
        method="POST",
        headers={
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
            "x-api-key": api_key,
        },
        data=body,
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
        payload = json.loads(r.read())
    text = "".join(c.get("text", "") for c in payload.get("content", []) if c.get("type") == "text").strip()
    # Strip stray code fences.
    if text.startswith("```"):
        text = text.strip("`\n ")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


async def worker(name, queue, out_fh, out_lock, api_key, base_url, revisions, stats):
    loop = asyncio.get_running_loop()
    while True:
        rec = await queue.get()
        if rec is None:
            queue.task_done()
            return
        prompt = build_prompt(rec, revisions)
        row = {"a": rec["a"], "b": rec["b"], "n_shared_pages": rec["n_shared_pages"], "n_encounters": rec["n_encounters"]}
        try:
            result = await loop.run_in_executor(None, call_haiku, prompt, api_key, base_url)
            row.update({
                "verdict": result.get("verdict"),
                "addressed_by": result.get("addressed_by"),
                "evidence": result.get("evidence"),
            })
            stats["ok"] += 1
        except Exception as e:
            row.update({"verdict": None, "error": f"{type(e).__name__}: {str(e)[:180]}"})
            stats["err"] += 1
        async with out_lock:
            out_fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            out_fh.flush()
        stats["done"] += 1
        if stats["done"] % 25 == 0:
            elapsed = time.time() - stats["start"]
            rate = stats["done"] / max(elapsed, 1)
            print(f"[{name}] done={stats['done']} ok={stats['ok']} err={stats['err']} rate={rate:.2f}/s", file=sys.stderr, flush=True)
        queue.task_done()


async def main_async(limit, concurrency):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set. The proxy at ANTHROPIC_BASE_URL requires a real key.", file=sys.stderr)
        sys.exit(2)
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    print(f"model={MODEL}  base_url={base_url}  concurrency={concurrency}", file=sys.stderr)

    print("loading revisions…", file=sys.stderr)
    revisions = load_revisions_by_id()
    print(f"  {len(revisions)} revision bodies loaded", file=sys.stderr)

    print("merging comms into undirected pairs…", file=sys.stderr)
    merged = merge_undirected(load_comms())
    pairs = sorted(merged.values(), key=lambda r: (-r["max_shared_pages"], r["a"], r["b"]))
    print(f"  {len(pairs)} undirected pairs", file=sys.stderr)

    done = already_done()
    print(f"  {len(done)} already classified — skipping", file=sys.stderr)
    remaining = [p for p in pairs if (p["a"], p["b"]) not in done]
    if limit:
        remaining = remaining[:limit]
    print(f"  {len(remaining)} pairs to classify this run", file=sys.stderr)

    out_path = OUT / "classifications.jsonl"
    out_fh = out_path.open("a")
    out_lock = asyncio.Lock()
    queue = asyncio.Queue(maxsize=concurrency * 4)
    stats = {"done": 0, "ok": 0, "err": 0, "start": time.time()}

    workers = [asyncio.create_task(worker(f"w{i}", queue, out_fh, out_lock, api_key, base_url, revisions, stats)) for i in range(concurrency)]
    for rec in remaining:
        await queue.put(rec)
    for _ in range(concurrency):
        await queue.put(None)
    await asyncio.gather(*workers)
    out_fh.close()

    elapsed = time.time() - stats["start"]
    print(f"DONE: classified={stats['done']} ok={stats['ok']} err={stats['err']} elapsed={elapsed:.1f}s", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="Max pairs to classify this run (0 = all remaining)")
    ap.add_argument("--concurrency", type=int, default=8, help="Concurrent API calls")
    args = ap.parse_args()
    asyncio.run(main_async(args.limit or None, args.concurrency))


if __name__ == "__main__":
    main()
