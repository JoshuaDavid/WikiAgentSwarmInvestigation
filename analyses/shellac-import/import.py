#!/usr/bin/env python3
"""Transform the shellac agent-reading pack into agent-logs/-shaped exports.

Input:  ./tmp/shellac_extracted/agent-reading-pack-20260905/agent-text.sqlite
Output: agent-logs/pastes/, agent-logs/shorteners/, agent-logs/gems/,
        agent-logs/apchem/shellac_bodies.jsonl (+ manifest patch, SHA256SUMS refresh)

The shellac pack (from user "shellac") is a deduplicated, weakly-labelled
candidate-agent-text corpus. It does not carry the per-page/per-revision/per-event
schema that scrape/*.py exports for the actual wikis. We adapt the schema:

- Each shellac document becomes one revision.
- source_group becomes the page identity. Groups with multiple documents (mostly
  shortener .body files that changed over time) get multiple ordered revisions.
- One save event per revision. No delete/revert/probe events (shellac's input
  wasn't a wiki request log).
- author (recovered for 408 rows total) becomes label; nulls become "".
- No IP data, no diff hunks, no admin request logs. Fields set to null everywhere.

Attribution note: this data was assembled by shellac and shared as
`agent-reading-pack-20260905.tar.gz` (input_sha256 in manifest).
"""

import base64
import hashlib
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHELLAC_DB = REPO / "tmp/shellac_extracted/agent-reading-pack-20260905/agent-text.sqlite"
SHELLAC_STATS = REPO / "tmp/shellac_extracted/agent-reading-pack-20260905/stats.json"

AGENT_LOGS = REPO / "agent-logs"

GENERATED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "+00:00")

# =============================================================================
# Common
# =============================================================================


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=False))
            f.write("\n")


def refresh_sha256sums(dir_path: Path):
    """Write SHA256SUMS covering every .jsonl and .json in the dir."""
    entries = []
    for p in sorted(dir_path.iterdir()):
        if p.name == "SHA256SUMS" or p.name == "README.md" or p.is_dir():
            continue
        if p.suffix not in {".jsonl", ".json"}:
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        entries.append(f"{h}  {p.name}\n")
    (dir_path / "SHA256SUMS").write_text("".join(entries), encoding="utf-8")


# =============================================================================
# Per-source export
# =============================================================================


def load_shellac_stats():
    return json.loads(SHELLAC_STATS.read_text(encoding="utf-8"))


def sanitize_time(ts: str | None) -> str | None:
    """Shellac dates arrive as ISO strings or None. Return as-is or None."""
    if ts is None or ts == "":
        return None
    return ts


def group_to_name(source_type: str, source_group: str) -> tuple[str, str]:
    """Return (page_name, bucket) - bucket = first char of name, matching prowiki."""
    # For pastes: group like "linuxiarz/abc123" -> keep whole group as name
    # For shorteners: "candidate-sites/vanderbi-lt/iyg1y.body" -> "vanderbi-lt/iyg1y"
    # For gems: "atlas-qa-snapshot-696b16c7-0.0.1" -> gem package (used at page level)
    if source_type == "shortener_candidate":
        s = source_group.removeprefix("candidate-sites/")
        s = s.removesuffix(".body")
        name = s
    else:
        name = source_group
    bucket = name[0] if name else ""
    return name, bucket


def emit_source_dir(
    source_type: str,
    dir_name: str,
    provenance_source: dict,
    limitations: list[str],
    readme_extra: str,
):
    """Emit pages.jsonl, revisions.jsonl, events.jsonl, labels.jsonl, manifest.json, SHA256SUMS.

    For source_types where one page can carry many docs (shorteners), we order
    revisions by (timestamp_utc, id) to get a deterministic seq. When timestamps
    are absent, we fall back to (id) order alone. seq starts at 1.
    """
    conn = sqlite3.connect(SHELLAC_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    rows = c.execute(
        """
        SELECT id, source_type, source_group, title, source_url, author,
               timestamp_utc, timestamp_original, timestamp_basis,
               occurrences, text, text_sha256
        FROM documents
        WHERE source_type = ?
        ORDER BY source_group, COALESCE(timestamp_utc, ''), id
        """,
        (source_type,),
    ).fetchall()

    docs_by_group: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        docs_by_group[r["source_group"]].append(r)

    pages: list[dict] = []
    revisions: list[dict] = []
    events: list[dict] = []
    label_stats: dict[str, dict] = {}

    wiki_name = dir_name

    for source_group, group_rows in docs_by_group.items():
        name, bucket = group_to_name(source_type, source_group)
        page_id = f"{wiki_name}/{name}"
        page_key = f"{wiki_name}~{name}"

        labels_seen: set[str] = set()
        first_time, last_time = None, None
        body_bytes = 0
        for r in group_rows:
            body_bytes += len(r["text"].encode("utf-8"))
            lab = r["author"] or ""
            labels_seen.add(lab)
            t = sanitize_time(r["timestamp_utc"])
            if t:
                first_time = t if first_time is None or t < first_time else first_time
                last_time = t if last_time is None or t > last_time else last_time

        # Emit page row
        pages.append({
            "page_id": page_id,
            "page_key": page_key,
            "wiki": wiki_name,
            "name": name,
            "bucket": bucket,
            "page_family": "off_store_unclassified",
            "page_family_cohort": None,
            "page_family_confidence": None,
            "page_family_method": None,
            "page_family_source": "none",
            "n_revs": len(group_rows),
            "n_revs_before": None,
            "first_write": first_time,
            "last_write": last_time,
            "body_bytes": body_bytes,
            "deleted_live": None,
            "live_body_variant": None,
            "head_differs_from_live": None,
            "n_deletions": 0,
            "n_recreations": 0,
            "labels": sorted(labels_seen),
            "n_labels": len(labels_seen),
            "n_ips": None,
            "n_ip16": None,
            "wiki_head_revision_number": None,
            "source_group": source_group,
            "source_url_example": next((r["source_url"] for r in group_rows if r["source_url"]), None),
        })

        # Emit one revision + one save event per doc, ordered by timestamp
        for seq, r in enumerate(group_rows, start=1):
            rev_id = f"{wiki_name}~{name}@{seq}"
            body = r["text"]
            body_sha = r["text_sha256"]
            label = r["author"] or ""
            t = sanitize_time(r["timestamp_utc"])

            revisions.append({
                "rev_id": rev_id,
                "page_id": page_id,
                "page_key": page_key,
                "wiki": wiki_name,
                "name": name,
                "seq": seq,
                "rcs_rev": None,
                "rcs_path": None,
                "body_len": len(body.encode("utf-8")),
                "body_sha256": body_sha,
                "lines": body.count("\n") + (1 if body and not body.endswith("\n") else 0),
                "diff_base": None,
                "diff_base_reason": "not_captured_by_shellac_pack",
                "hunks": None,
                "label": label,
                "label_source": "shellac_recovered_author" if r["author"] else "unknown",
                "ip16": None,
                "time": t,
                "time_grade": "inherited_source_metadata" if t else "unknown",
                "winning_clock": "shellac_timestamp_utc" if t else None,
                "uncertainty_seconds": None,
                "request_time": None,
                "success_time": None,
                "recent_changes_time": None,
                "write_date": t,
                "archived_at": GENERATED_AT,
                "request_action": None,
                "change_summary": None,
                "related_event_id": None,
                "relation_type": None,
                "round_id": None,
                "body": body,
                "body_encoding": "raw_utf8",
                "wiki_revision_number": None,
                "is_new_page": seq == 1,
                "is_minor_edit": None,
                "body_availability": "full_source",
                "shellac_doc_id": r["id"],
                "shellac_source_type": r["source_type"],
                "shellac_source_group": r["source_group"],
                "shellac_source_url": r["source_url"],
                "shellac_title": r["title"],
                "shellac_occurrences": r["occurrences"],
                "shellac_timestamp_basis": r["timestamp_basis"],
            })

            events.append({
                "event_id": f"save:{rev_id}",
                "event_type": "save",
                "time": t,
                "time_grade": "inherited_source_metadata" if t else "unknown",
                "wiki": wiki_name,
                "revision_ref": rev_id,
            })

            # Aggregate label stats
            ls = label_stats.setdefault(label, {
                "label": label,
                "stored_revisions": 0,
                "first_write": None,
                "last_write": None,
                "stored_revision_ips": None,
                "stored_revision_ip16": None,
                "pages_set": set(),
                "wikis_set": set(),
            })
            ls["stored_revisions"] += 1
            if t:
                ls["first_write"] = t if ls["first_write"] is None or t < ls["first_write"] else ls["first_write"]
                ls["last_write"] = t if ls["last_write"] is None or t > ls["last_write"] else ls["last_write"]
            ls["pages_set"].add(page_id)
            ls["wikis_set"].add(wiki_name)

    labels_out = []
    for lab, ls in sorted(label_stats.items()):
        labels_out.append({
            "label": lab,
            "stored_revisions": ls["stored_revisions"],
            "first_write": ls["first_write"],
            "last_write": ls["last_write"],
            "stored_revision_ips": None,
            "stored_revision_ip16": None,
            "pages": sorted(ls["pages_set"]),
            "stored_revision_pages": len(ls["pages_set"]),
            "wikis": sorted(ls["wikis_set"]),
            "is_human_handle": None,
            "save_requests": None,
            "save_request_ips": None,
            "save_request_ip16": None,
            "save_request_pages": None,
            "save_request_source": "shellac_reading_pack_20260905",
        })

    out_dir = AGENT_LOGS / dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    write_jsonl(out_dir / "pages.jsonl", pages)
    write_jsonl(out_dir / "revisions.jsonl", revisions)
    write_jsonl(out_dir / "events.jsonl", events)
    write_jsonl(out_dir / "labels.jsonl", labels_out)

    manifest = {
        "generated_at": GENERATED_AT,
        "source": provenance_source,
        "cut": {
            "kind": "shellac_reading_pack_extract",
            "shellac_pack": "agent-reading-pack-20260905",
            "shellac_input_sha256": load_shellac_stats().get("input_sha256") or json.loads((REPO / 'tmp/shellac_extracted/agent-reading-pack-20260905/stats.json').read_text())["input_sha256"] if False else "6965c741d0fbe767b84660629ef513b2bc4488f5b4c9ee97519f6749fc26e0af",
            "filter": f"source_type = '{source_type}'",
        },
        "wiki_tz_offset": None,
        "counts": {
            "revisions": {"value": len(revisions)},
            "pages": {"value": len(pages)},
            "labels": {"value": len(labels_out)},
            "events": {"value": len(events)},
        },
        "per_wiki": {
            wiki_name: {
                "revisions": {"value": len(revisions)},
                "pages": {"value": len(pages)},
                "body_bytes": {"value": sum(p["body_bytes"] for p in pages)},
            }
        },
        "limitations": limitations,
        "endpoints_probed": None,
        "attribution": {
            "prepared_by": "shellac",
            "pack": "agent-reading-pack-20260905.tar.gz",
            "note": "Shellac assembled and deduplicated the underlying candidate agent text corpus. This directory is a schema adaptation of that pack into the agent-logs/ layout. Bodies are unchanged.",
        },
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    readme = (
        f"# {dir_name}\n\n"
        f"Adaptation of shellac's `agent-reading-pack-20260905` — the `{source_type}` slice —\n"
        f"into the `agent-logs/` schema used by `prowiki/`, `apchem/` and the other wiki exports.\n\n"
        f"{readme_extra}\n\n"
        "## Schema deviations from `prowiki/`\n\n"
        "- `wiki` field carries the container name (`{dir}`), not a wiki_name.\n"
        "- Bodies live inline in `revisions.jsonl` as `body` (raw UTF-8), not base64 with a `body_encoding` tag. `body_encoding` = `\"raw_utf8\"`.\n"
        "- `ip16` is null everywhere. The upstream corpus does not carry IPs.\n"
        "- `diff_base`/`hunks` are null. Shellac deduplicates by content; there is no revision graph to diff against.\n"
        "- `events.jsonl` contains only `save` rows. No delete/revert/probe request logs are available.\n"
        "- Revision `seq` is assigned by (`timestamp_utc`, `id`) order within a `source_group`. When timestamps are missing, `seq` follows lexicographic `id`.\n"
        "- Every revision row carries `shellac_doc_id`, `shellac_source_group`, `shellac_source_url`, `shellac_title`, `shellac_occurrences`, `shellac_timestamp_basis` for round-tripping to the source pack.\n"
        "- Labels: shellac recovered authors for only 408 of 16,579 documents. Where an author was not recovered, `label` is the empty string.\n\n"
        "## Attribution\n\n"
        "The candidate texts here were collected, deduplicated, and weakly labelled by\n"
        "shellac in `agent-reading-pack-20260905` (input SHA-256 `6965c741…`). The reading\n"
        "pack's README calls out that labels are `\"weak candidate, not actor attribution\"`\n"
        "and that copied source material, researcher imitations, and known false\n"
        "positives are retained. Those caveats carry over to this export unchanged.\n"
    ).replace("{dir}", dir_name)
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    refresh_sha256sums(out_dir)

    return {
        "dir": str(out_dir.relative_to(REPO)),
        "pages": len(pages),
        "revisions": len(revisions),
        "events": len(events),
        "labels": len(labels_out),
    }


# =============================================================================
# apchem supplement
# =============================================================================


def emit_apchem_shellac_supplement():
    """Write agent-logs/apchem/shellac_bodies.jsonl with the 11 extra_wiki_candidate rows,
    plus a `shellac` block in manifest.json, and refresh SHA256SUMS."""

    apchem_dir = AGENT_LOGS / "apchem"
    conn = sqlite3.connect(SHELLAC_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    rows = c.execute(
        """
        SELECT id, source_group, title, text, text_sha256, occurrences
        FROM documents
        WHERE source_type = 'extra_wiki_candidate' AND source_group LIKE 'candidate-sites/tmcleod-apchem/%'
        ORDER BY source_group
        """
    ).fetchall()

    supplement = []
    for r in rows:
        # source_group like candidate-sites/tmcleod-apchem/revisions/OpenAIRegCFTest-r10
        parts = r["source_group"].split("/")
        # last part is Page-rN
        leaf = parts[-1]
        if "-r" in leaf:
            page_name, r_marker = leaf.rsplit("-r", 1)
            try:
                rev_num = int(r_marker)
            except ValueError:
                rev_num = None
        else:
            page_name, rev_num = leaf, None

        page_id = f"apchem/{page_name}"
        # In existing apchem/revisions.jsonl these are numbered @1..@N by seq.
        # Best-guess mapping: shellac r{N} -> apchem seq {N}. Recorded as
        # suggested_rev_ref, not a hard join, because the two scrapes differ.
        suggested_rev_ref = f"apchem~{page_name}@{rev_num}" if rev_num else None

        # Detect UseModWiki's "revision N not available; showing current" fallback.
        # When an older revision has been rotated out of the RCS chain UseModWiki
        # serves the head with a prefix banner. Shellac captured that banner
        # verbatim, so the "revision N" body is not actually revision N's content.
        head200 = r["text"][:200].lower()
        if "not available" in head200 and "showing current revision" in head200:
            body_is_actual_revision = False
            body_kind = "usemodwiki_fallback_to_current_revision"
        elif head200.startswith(f"showing revision {rev_num}") if rev_num else False:
            body_is_actual_revision = True
            body_kind = "usemodwiki_showing_revision_N"
        else:
            body_is_actual_revision = None
            body_kind = "unknown_prefix"

        supplement.append({
            "shellac_doc_id": r["id"],
            "shellac_source_group": r["source_group"],
            "shellac_title": r["title"],
            "shellac_occurrences": r["occurrences"],
            "wiki": "apchem",
            "page_id": page_id,
            "page_name": page_name,
            "shellac_revision_marker": leaf,
            "shellac_revision_number": rev_num,
            "suggested_rev_ref": suggested_rev_ref,
            "suggested_rev_ref_note": "best-effort mapping; shellac and scrape/apchem.py are independent captures. If body_is_actual_revision is false, the body is UseModWiki's fallback to the current head, not revision N's content.",
            "body_kind": body_kind,
            "body_is_actual_revision": body_is_actual_revision,
            "body": r["text"],
            "body_encoding": "raw_utf8",
            "body_len": len(r["text"].encode("utf-8")),
            "body_sha256": r["text_sha256"],
        })

    supplement_path = apchem_dir / "shellac_bodies.jsonl"
    write_jsonl(supplement_path, supplement)

    # Patch manifest.json
    mf_path = apchem_dir / "manifest.json"
    mf = json.loads(mf_path.read_text(encoding="utf-8"))
    mf["shellac_supplement"] = {
        "file": "shellac_bodies.jsonl",
        "rows": len(supplement),
        "source_pack": "agent-reading-pack-20260905",
        "source_pack_input_sha256": "6965c741d0fbe767b84660629ef513b2bc4488f5b4c9ee97519f6749fc26e0af",
        "prepared_by": "shellac",
        "generated_at": GENERATED_AT,
        "note": "Extra body candidates for existing apchem pages OpenAIRegCFTest and SandboxISTIResearchTest. Most rows in revisions.jsonl for these pages are body_availability='metadata_only'; shellac's pack carries the raw source at each revision (r1..r10 and r1 respectively). suggested_rev_ref inside each row is a best-effort join hint, not a proof of identity. Some rows carry UseModWiki's 'Revision N not available (showing current revision instead)' banner — those bodies are the head at capture time, not the actual revision N content; see body_is_actual_revision per row.",
    }
    mf_path.write_text(json.dumps(mf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    refresh_sha256sums(apchem_dir)

    return {"dir": "agent-logs/apchem", "supplement_rows": len(supplement)}


# =============================================================================
# main
# =============================================================================


def main():
    out = []

    out.append(emit_source_dir(
        source_type="paste_candidate",
        dir_name="pastes",
        provenance_source={
            "wiki_name": "pastes",
            "kind": "public_paste_sites",
            "base_urls_observed": [
                "https://linuxiarz.pl", "https://k4be.pl", "https://anna-fyi",
                "https://paste.steamr.com", "https://pastebin.tarcseh.me",
                "https://pb.dynavirt.com", "https://paste.smirky.net",
                "https://pastebin.faster-it.de", "https://nervesocket.com", "https://p.gaa.st",
            ],
            "engine": "n/a (multiple paste engines)",
            "scraper": "shellac agent-reading-pack-20260905 (not our scrape/*.py)",
        },
        limitations=[
            "Weak candidate labels, not forensic attribution (shellac's phrase). Copied source material, researcher imitations, and known false positives are retained.",
            "Deduplication by exact body sha256. Multiple identical bodies at the same paste URL collapse to one row; `shellac_occurrences` records the observed multiplicity.",
            "No IPs (`ip16` = null). Paste sites do not expose them to scrapers.",
            "No revision graph. Each paste is treated as a single revision even where an author later posted an update at a new URL.",
            "Timestamps are inherited paste-site metadata (`timestamp_basis` in the source frontmatter reads 'inherited source metadata; not independently verified'). 421 of 458 rows carry a timestamp.",
            "Authors recovered for 408 rows across the whole reading pack (155 handles); most `label` values here are the empty string.",
            "Content is untrusted (shellac's README explicitly warns of possible prompt injections). Common secret patterns were redacted by shellac (26 redactions across the whole pack).",
        ],
        readme_extra=(
            "458 documents across 10 paste-site hosts. Time span 2020-09 → 2026-09.\n"
            "Host distribution: linuxiarz 219 · pastebin-k4be 126 · anna-fyi 63 ·\n"
            "paste.steamr.com 33 · pastebin.tarcseh.me 6 · pb.dynavirt.com 3 ·\n"
            "paste.smirky.net 3 · pastebin.faster-it.de 2 · nervesocket.com 2 · p.gaa.st 1."
        ),
    ))

    out.append(emit_source_dir(
        source_type="shortener_candidate",
        dir_name="shorteners",
        provenance_source={
            "wiki_name": "shorteners",
            "kind": "public_url_shortener_redirect_bodies",
            "hosts_observed": [
                "vanderbi-lt", "uoft-me", "goto-unm", "popcat", "u-ethz-ch",
            ],
            "engine": "n/a (compromised URL shortener endpoints — see incident write-up)",
            "scraper": "shellac agent-reading-pack-20260905 (not our scrape/*.py)",
        },
        limitations=[
            "Weak candidate labels, not forensic attribution.",
            "Bodies are the shortened URL target strings observed at each redirect endpoint. One page = one .body file at a shortener host. Multiple revisions per page are common (a single vanderbi-lt endpoint carries 2,151 distinct bodies over the capture window).",
            "No timestamps at all (`time` = null everywhere). Revision `seq` is assigned by lexicographic `shellac_doc_id`; do not read it as a chronological order.",
            "No IPs, no author, no request action, no diff base.",
            "The `page_family` classifier was not run — every page is `off_store_unclassified`.",
        ],
        readme_extra=(
            "4,285 documents across 59 shortener bodies. Host distribution:\n"
            "vanderbi-lt 3,043 · uoft-me 527 · goto-unm 468 · popcat 230 · u-ethz-ch 17.\n"
            "The heaviest single body is `vanderbi-lt/iyg1y` with 2,151 revisions."
        ),
    ))

    out.append(emit_source_dir(
        source_type="package_text_candidate",
        dir_name="gems",
        provenance_source={
            "wiki_name": "gems",
            "kind": "rubygems_package_text",
            "packages_observed": [
                "atlas-qa-snapshot-696b16c7-0.0.1",
                "atlas_qa_handoff_20260528230548-0.0.1",
                "sampledocpayload624286-0.0.3",
                "sampledocpayload624286-0.0.5",
                "sampledocpayload624286-0.0.7",
                "sampledocpayload624286-0.0.11",
                "tf_drift_handoff_bundle_20260307t015800z",
            ],
            "engine": "rubygems",
            "scraper": "shellac agent-reading-pack-20260905 (not our scrape/*.py)",
        },
        limitations=[
            "12 rows spanning 7 gem packages. One page = one file inside a gem (README.md, lib/*.rb, exploit.rb, SHA256SUMS.txt).",
            "No timestamps. `time` = null everywhere.",
            "No `wiki` or admin metadata — these are not wiki exports; the shape is a schema adaptation only.",
            "Bodies include Ruby source. Do not eval or `require` them. Shellac's caveat about possible prompt injections applies to package README text as well.",
        ],
        readme_extra=(
            "12 documents across 7 Ruby gem packages published to public gem indexes.\n"
            "Filenames observed include `README.md`, `lib/*.rb`, `payload/README.txt`,\n"
            "`SHA256SUMS.txt`, and three files literally named `exploit.rb`."
        ),
    ))

    out.append(emit_apchem_shellac_supplement())

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
