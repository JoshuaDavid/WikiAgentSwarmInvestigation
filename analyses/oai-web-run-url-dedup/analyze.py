"""Summarise probe results into a table."""

from __future__ import annotations

import json
from pathlib import Path

RAW = Path(__file__).parent / "outputs" / "raw"
OUT = Path(__file__).parent / "outputs"


def summarise(p: dict) -> list[dict]:
    """Extract per-fetch rows from a probe result."""
    name = p["name"]
    desc = p.get("description", "")
    rows: list[dict] = []
    fetches = [s for s in p["steps"] if s["kind"] == "fetch"]
    for i, s in enumerate(fetches):
        call0 = (s["extracted"]["calls"] or [{}])[0]
        rows.append({
            "probe": name,
            "step_i": i,
            "label": s["label"],
            "asked_url": s["url"],
            "canonical_url": call0.get("action_url", ""),
            "external": s.get("external", True),
            "server_hits": len(s["server_hits"]),
            "elapsed_s": s.get("elapsed_s"),
            "crawled_stamp": call0.get("crawled"),
            "returned_content": s["extracted"]["message_text"][:60].replace("\n", " "),
            "probe_desc": desc,
        })
    return rows


def main() -> None:
    all_rows: list[dict] = []
    for f in sorted(RAW.glob("*.json")):
        try:
            p = json.loads(f.read_text())
        except Exception as e:
            print(f"skip {f.name}: {e}")
            continue
        all_rows.extend(summarise(p))

    (OUT / "summary.jsonl").write_text("\n".join(json.dumps(r) for r in all_rows) + "\n")

    # Compact table
    lines: list[str] = []
    lines.append(f"{'probe':<48} {'label':<24} {'hits':>4} {'crawled':<10} canonical_url")
    lines.append("-" * 200)
    last_probe = None
    for r in all_rows:
        if last_probe and r["probe"] != last_probe:
            lines.append("")
        canonical = r["canonical_url"] or "(none)"
        # trim ngrok prefix for readability
        pfx = "https://oai-scratchpad-cache-versioning-demo.ngrok.io"
        if canonical.startswith(pfx):
            canonical_short = "…" + canonical[len(pfx):]
        else:
            canonical_short = canonical
        lines.append(
            f"{r['probe']:<48} {r['label']:<24} {r['server_hits']:>4} "
            f"{(r['crawled_stamp'] or '-'):<10} {canonical_short}"
        )
        last_probe = r["probe"]
    (OUT / "summary.txt").write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT / 'summary.txt'} ({len(all_rows)} rows)")


if __name__ == "__main__":
    main()
