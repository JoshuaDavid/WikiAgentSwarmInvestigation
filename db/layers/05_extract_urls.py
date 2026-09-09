"""URL extraction over every post body. Emits url_reference rows citing the
url_extraction analysis_run.

Regex mirrors analyses/urls/extract.py so results agree byte-for-byte."""
from __future__ import annotations
import re
import sqlite3
import urllib.parse
from urllib.parse import unquote

URL_RE = re.compile(r"https?://[^\s<>\]\"'`|{}\\]+", re.IGNORECASE)
TRAILING_STRIP = ".,;:!?'\")"


def _normalize(url: str) -> str:
    while url and url[-1] in TRAILING_STRIP:
        url = url[:-1]
    return url


def _host(url: str) -> str:
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _scheme(url: str) -> str:
    lo = url.lower()
    if lo.startswith("https://"):
        return "https"
    if lo.startswith("http://"):
        return "http"
    return "?"


def _decoded_host(raw: str) -> str:
    h = raw
    try:
        h = unquote(h)
        h = unquote(h)
    except Exception:
        pass
    h = h.replace("&#46;", ".")
    return h.lower().rstrip(".")


def _upsert_host(conn: sqlite3.Connection, name: str,
                 host_cache: dict[str, int]) -> int:
    if name in host_cache:
        return host_cache[name]
    row = conn.execute("SELECT id FROM host WHERE name = ?", (name,)).fetchone()
    if row:
        host_cache[name] = row[0]
        return row[0]
    cur = conn.execute(
        "INSERT INTO host (name, decoded_name) VALUES (?, ?)",
        (name, _decoded_host(name)),
    )
    host_cache[name] = cur.lastrowid
    return cur.lastrowid


def _upsert_web_resource(conn: sqlite3.Connection, host_id: int, url_full: str,
                          wr_cache: dict[str, int]) -> int:
    if url_full in wr_cache:
        return wr_cache[url_full]
    row = conn.execute(
        "SELECT id FROM web_resource WHERE url_full = ?", (url_full,)
    ).fetchone()
    if row:
        wr_cache[url_full] = row[0]
        return row[0]
    cur = conn.execute(
        "INSERT INTO web_resource (host_id, url_full) VALUES (?, ?)",
        (host_id, url_full),
    )
    wr_cache[url_full] = cur.lastrowid
    return cur.lastrowid


def run(conn: sqlite3.Connection, ctx: dict) -> None:
    run_id = ctx["analysis_run_id_by_name"]["url_extraction"]
    host_cache: dict[str, int] = {}
    wr_cache: dict[str, int] = {}

    # Sorted by post.id so extraction order is stable.
    posts = conn.execute(
        "SELECT p.id, b.content_bytes FROM post p "
        "JOIN body b ON b.id = p.body_id ORDER BY p.id"
    ).fetchall()

    n = 0
    for post_id, content_bytes in posts:
        try:
            body = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            body = content_bytes.decode("utf-8", errors="replace")
        if "http" not in body.lower():
            continue
        for m in URL_RE.finditer(body):
            raw = _normalize(m.group(0))
            if not raw or "://" not in raw:
                continue
            host_name = _host(raw)
            if not host_name:
                continue
            host_id = _upsert_host(conn, host_name, host_cache)
            wr_id = _upsert_web_resource(conn, host_id, raw, wr_cache)
            conn.execute(
                "INSERT INTO url_reference "
                "(post_id, web_resource_id, byte_offset, scheme, analysis_run_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (post_id, wr_id, m.start(), _scheme(raw), run_id),
            )
            n += 1
    print(f"  emitted {n} url_reference rows")
