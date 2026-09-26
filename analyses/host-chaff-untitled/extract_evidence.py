#!/usr/bin/env python3
"""Extract the per-paste evidence table for the host-chaff-untitled bucket.

Reads `analyses/pastes-by-task/outputs/pastes_by_task.tsv`, filters to
`task == "host-chaff-untitled"`, joins each row against the underlying
`agent-logs/<source>/revisions.jsonl` body, and adds:

- `host`         parsed netloc of `shellac_source_url` / `source_url`
- `body_len`     recomputed len of the joined body
- `content_kind` heuristic category (see CATEGORY_RULES)
- `first_line`   first non-empty line of the body, truncated to 120 chars
- `k4be_verdict` original subagent verdict from the `pastebin-k4be` scrape
                 (empty for other sources)
- `k4be_verdict_confidence`
- `provenance`   from `analyses/pastes-by-task/outputs/label_provenance.tsv`

Writes `outputs/evidence.tsv`. Sort is deterministic:
`(host, body_sha256)`.

Rerun with: python3 extract_evidence.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
LOGS = REPO_ROOT / "agent-logs"
PASTES_TSV = REPO_ROOT / "analyses" / "pastes-by-task" / "outputs" / "pastes_by_task.tsv"
PROVENANCE_TSV = REPO_ROOT / "analyses" / "pastes-by-task" / "outputs" / "label_provenance.tsv"
OUT_DIR = HERE / "outputs"

TASK_LABEL = "host-chaff-untitled"


# Ordered list of (category, predicate_over_body_and_title).
# First match wins. Categories chosen to describe the sysadmin / hobbyist
# background traffic that dominates this bucket, plus the k4be subgroup
# whose bodies contain swarm-task data.
CATEGORY_RULES = [
    ("puppet-log", lambda b, t: "puppet agent" in b or "puppet:///" in b),
    ("kickstart-config", lambda b, t: "#version=RHEL" in b or "kickstart" in t.lower()),
    ("postfix-config", lambda b, t: "main.cf" in t or "master.cf" in t or "postfix" in b.lower()[:200]),
    ("nginx-config", lambda b, t: "$http_user_agent" in b or "server {" in b and "nginx" in b.lower()),
    ("nixos-config", lambda b, t: "nixos-help" in b or "nix-env" in b),
    ("dhcpd-config", lambda b, t: "dhcpd.conf" in t or "ddns-update-style" in b),
    ("esphome-config", lambda b, t: "esphome:" in b or "sofar" in t.lower()),
    ("modbus-config", lambda b, t: "modbus:" in b[:400] or "message_wait_milliseconds" in b),
    ("foreman-config", lambda b, t: "Foreman" in t or "params.pp" in b),
    ("ansible-facts", lambda b, t: "ansible_facts" in b),
    ("unixbench-output", lambda b, t: "BYTE UNIX Benchmarks" in b or "byte-unixbench" in b),
    ("h5bench-output", lambda b, t: "h5bench" in b or "Configuration file:" in b and "test.h5" in b),
    ("lscpu-output", lambda b, t: "CPU op-mode(s):" in b and "Architecture:" in b),
    ("infiniband-diag", lambda b, t: "ibdiagnet" in b or "perfquery" in b),
    ("system-log", lambda b, t: "auth.log" in b or "sshd[" in b or "systemd-logind" in b),
    ("xen-qemu-build", lambda b, t: "qemu-" in t.lower() or "xen-" in t.lower() or "dpkg-buildpackage" in b),
    ("pd-patch", lambda b, t: b.startswith("#N canvas ")),
    ("react-js", lambda b, t: "React.createElement" in b or "ReactDOM.render" in b),
    ("cpp-code", lambda b, t: "std::lower_bound" in b or "#include <" in b or "// Find " in b[:200]),
    ("avr-c-code", lambda b, t: "#include <avr/io.h>" in b or "PT6524" in b),
    ("http-capture", lambda b, t: "Request URL:" in b and "Response Headers" in b),
    ("jwk-json", lambda b, t: (
        ('"keys":[{' in b and '"kty":"RSA"' in b)
        or ("&quot;keys&quot;" in b and "&quot;kty&quot;" in b)
    )),
    ("gardening-guide", lambda b, t: "EZ Lawn" in b),
    ("ordering-guide", lambda b, t: "grass" in b.lower() and "lawn" in b.lower() and len(b) > 1000),

    # k4be swarm-content sub-cluster: pastes whose title is `Bez tytułu`
    # but whose bodies carry benchmark-task data. See README section
    # "Sub-pattern: k4be misclassifications".
    ("swarm-convfinqa", lambda b, t: (
        "ConvFinQA" in b
        or ("Question:" in b and "Answer:" in b and "Program:" in b)
        or ("quarter ended" in b.lower() and "high" in b.lower())
    )),
    ("swarm-owid-csv", lambda b, t: "OWID" in b or "Entity,Code,Year" in b),
    ("swarm-bullfincher", lambda b, t: "bullfincher.io/sec-proxy" in b or "bullfincher" in b),
    ("swarm-airport-json", lambda b, t: (
        ("'Rank':" in b or "&#039;Rank&#039;:" in b)
        and ("DXB" in b or "LAX" in b)
    )),
    ("swarm-co2-emissions", lambda b, t: (
        "co2emiss" in b or "pcco2" in b or "co2pc" in b
    )),
    ("swarm-nba-stats", lambda b, t: "NBA" in b and "3-Point" in b),
    ("swarm-latin-treatise", lambda b, t: "DE MYSTERIOSO VEHICULO" in b),
    ("swarm-alchemical-meme", lambda b, t: "Alchemical breakdown" in b),
    ("llm-humor-essay", lambda b, t: "SHA-256 hash of absolutely nothing" in b or "Solemn Ceremony of Processing Nothing" in b),
    ("swarm-epl-csv", lambda b, t: "first_name,second_name,web_name" in b),

    ("footer-artifact", lambda b, t: b.strip() in ("pastebin powered by stikked", "Recent added pastes")),
    ("smoke-test", lambda b, t: b.strip().lower() in (
        "hi", "hello test", "test", "hello world", "xx", "hellotest",
        "hello from test", "browserposttest22", "terminal-post",
        "hello paste k4be test",
    )),
]


def open_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def classify_body(body: str, title: str) -> str:
    for name, rule in CATEGORY_RULES:
        try:
            if rule(body, title):
                return name
        except Exception:
            continue
    return "other"


def first_line(body: str) -> str:
    for line in body.splitlines():
        s = line.strip()
        if s:
            return s[:120]
    return ""


def host_of(url: str, source_group: str, wiki: str) -> str:
    if url:
        net = urllib.parse.urlparse(url).netloc
        if net:
            return net
    # Fall back to shellac_source_group prefix like `paste.steamr.com/xxxx`.
    if source_group and "/" in source_group:
        return source_group.split("/", 1)[0]
    # Some directly-scraped hosts (pastie.iem.at) leave URL fields null.
    # The `wiki` field on those exports is the host itself.
    return wiki or ""


def load_target_hashes() -> dict[str, dict]:
    """One row per host-chaff-untitled paste, keyed by body_sha256."""
    out: dict[str, dict] = {}
    with PASTES_TSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row["task"] != TASK_LABEL:
                continue
            out[row["body_sha256"]] = row
    return out


def load_provenance() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with PROVENANCE_TSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            out[row["body_sha256"]] = row
    return out


def join_bodies(targets: dict[str, dict]) -> dict[str, dict]:
    """For each target hash, look up the source rev and attach body + verdict."""
    sources = sorted({row["source"] for row in targets.values()})
    joined: dict[str, dict] = {}
    for src in sources:
        path = LOGS / src / "revisions.jsonl"
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            continue
        for rev in open_jsonl(path):
            h = rev.get("body_sha256")
            if h not in targets:
                continue
            if h in joined:
                continue
            body = rev.get("body") or ""
            url = rev.get("shellac_source_url") or rev.get("source_url") or ""
            group = rev.get("shellac_source_group") or ""
            joined[h] = {
                "body": body,
                "title": rev.get("shellac_title") or rev.get("source_title") or targets[h].get("title") or "",
                "time": rev.get("time") or "",
                "label": rev.get("label") or "",
                "host": host_of(url, group, rev.get("wiki") or src),
                "source_url": url,
                "k4be_verdict": rev.get("verdict") or "",
                "k4be_verdict_confidence": rev.get("verdict_confidence") or "",
            }
    return joined


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = load_target_hashes()
    prov = load_provenance()
    joined = join_bodies(targets)

    out_rows = []
    for sha, tgt in targets.items():
        j = joined.get(sha, {})
        body = j.get("body", "")
        title = j.get("title") or tgt.get("title") or ""
        p = prov.get(sha, {})
        out_rows.append({
            "host": j.get("host", ""),
            "source": tgt["source"],
            "time": j.get("time", ""),
            "label": j.get("label", ""),
            "title": title,
            "content_kind": classify_body(body, title),
            "body_len": len(body),
            "first_line": first_line(body),
            "k4be_verdict": j.get("k4be_verdict", ""),
            "k4be_verdict_confidence": j.get("k4be_verdict_confidence", ""),
            "provenance": p.get("provenance", ""),
            "reviewer_confidence": p.get("reviewer_confidence", ""),
            "reviewer_rationale": p.get("reviewer_rationale", ""),
            "source_url": j.get("source_url", ""),
            "body_sha256": sha,
        })

    out_rows.sort(key=lambda r: (r["host"], r["body_sha256"]))

    fields = [
        "host", "source", "time", "label", "title",
        "content_kind", "body_len", "first_line",
        "k4be_verdict", "k4be_verdict_confidence",
        "provenance", "reviewer_confidence", "reviewer_rationale",
        "source_url", "body_sha256",
    ]
    out_path = OUT_DIR / "evidence.tsv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for row in out_rows:
            w.writerow(row)

    from collections import Counter
    hosts = Counter(r["host"] for r in out_rows)
    kinds = Counter(r["content_kind"] for r in out_rows)
    labels = Counter(r["label"] for r in out_rows)
    times = sorted(r["time"] for r in out_rows if r["time"])
    print(f"pastes:            {len(out_rows)}", file=sys.stderr)
    print(f"distinct hosts:    {len(hosts)}", file=sys.stderr)
    print(f"distinct kinds:    {len(kinds)}", file=sys.stderr)
    print(f"distinct labels:   {len(labels)}", file=sys.stderr)
    if times:
        print(f"time span:         {times[0]} -> {times[-1]}", file=sys.stderr)
    print(f"rows with no time: {sum(1 for r in out_rows if not r['time'])}", file=sys.stderr)
    print(f"wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
