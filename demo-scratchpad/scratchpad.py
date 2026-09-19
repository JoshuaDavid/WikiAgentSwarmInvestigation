"""Tiny path-addressed HTTP scratchpad backed by SQLite.

Run: python3 scratchpad.py [--host 127.0.0.1] [--port 8000] [--db scratchpad.db]

Routes:
  GET /                              -> homepage (fixed HTML)
  GET /<path>                        -> return stored value for <path>
  GET /<path>?set-html=<value>       -> replace value at <path>, return new value

Unknown query params are ignored for rendering, so /foo?uniq=A and /foo?uniq=B
return the same current value.
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

SET_PARAM = "set-html"

HOMEPAGE = (
    "<h1>Scratchpad Test</h1>\n"
    "<code>GET:/foo?set-html=My%20%3Cblink%3Edemo%3C%2Fblink%3E%20html</code> to store<br>\n"
    "<code>GET:/foo to retrieve</code><br>\n"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS scratchpads (
    path       TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    method        TEXT NOT NULL,
    path          TEXT NOT NULL,
    query         TEXT NOT NULL,
    url           TEXT NOT NULL,
    value_before  TEXT,
    value_after   TEXT,
    response_hash TEXT NOT NULL,
    user_agent    TEXT,
    source_ip     TEXT,
    xff           TEXT,
    headers_json  TEXT
);
"""


class Store:
    def __init__(self, db_path: str) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)

    def get(self, path: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM scratchpads WHERE path = ?", (path,)
            ).fetchone()
        return row[0] if row else None

    def set(self, path: str, value: str, now: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO scratchpads(path, value, updated_at) VALUES(?, ?, ?) "
                "ON CONFLICT(path) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (path, value, now),
            )

    def log(
        self,
        *,
        ts: str,
        method: str,
        path: str,
        query: str,
        url: str,
        value_before: str | None,
        value_after: str | None,
        response_hash: str,
        user_agent: str | None,
        source_ip: str | None,
        xff: str | None = None,
        headers_json: str | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO requests(ts, method, path, query, url, value_before, value_after, "
                "response_hash, user_agent, source_ip, xff, headers_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    ts, method, path, query, url,
                    value_before, value_after, response_hash, user_agent, source_ip,
                    xff, headers_json,
                ),
            )


def sha256_hex(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def make_handler(store: Store) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "Scratchpad/1.0"

        def log_message(self, format: str, *args) -> None:  # quieter default logging
            sys.stderr.write("%s - - [%s] %s\n" % (
                self.address_string(), self.log_date_time_string(), format % args,
            ))

        def _respond(self, body: bytes, content_type: str = "text/html; charset=utf-8",
                     status: int = 200, extra_headers: list[tuple[str, str]] | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra_headers or []):
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
            split = urlsplit(self.path)
            path = split.path
            query = split.query
            params = parse_qs(query, keep_blank_values=True)
            now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
            user_agent = self.headers.get("User-Agent")
            source_ip = self.client_address[0] if self.client_address else None
            xff = self.headers.get("X-Forwarded-For")
            import json as _json
            headers_json = _json.dumps({k: v for k, v in self.headers.items()})

            if path == "/" or path == "":
                body = HOMEPAGE.encode("utf-8")
                self._respond(body)
                store.log(
                    ts=now, method="GET", path=path, query=query, url=self.path,
                    value_before=None, value_after=None,
                    response_hash=sha256_hex(body),
                    user_agent=user_agent, source_ip=source_ip,
                    xff=xff, headers_json=headers_json,
                )
                return

            value_before = store.get(path)
            value_after = value_before

            if SET_PARAM in params:
                new_value = params[SET_PARAM][-1]
                store.set(path, new_value, now)
                value_after = new_value

            # Optional response overrides. These are for probe use;
            # they DO NOT affect the stored value at `path`.
            status_override = 200
            extra_headers: list[tuple[str, str]] = []
            if "respond-status" in params:
                try:
                    status_override = int(params["respond-status"][-1])
                except ValueError:
                    pass
            if "respond-redirect" in params:
                # Overrides everything; return 302 with Location header.
                target = params["respond-redirect"][-1]
                body = b""
                self._respond(body, status=302, extra_headers=[("Location", target)])
                store.log(
                    ts=now, method="GET", path=path, query=query, url=self.path,
                    value_before=value_before, value_after=value_after,
                    response_hash=sha256_hex(body),
                    user_agent=user_agent, source_ip=source_ip,
                    xff=xff, headers_json=headers_json,
                )
                return

            body = (value_after or "").encode("utf-8")
            self._respond(body, status=status_override, extra_headers=extra_headers)
            store.log(
                ts=now, method="GET", path=path, query=query, url=self.path,
                value_before=value_before, value_after=value_after,
                response_hash=sha256_hex(body),
                user_agent=user_agent, source_ip=source_ip,
                xff=xff, headers_json=headers_json,
            )

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="scratchpad.db")
    args = parser.parse_args(argv)

    store = Store(args.db)
    handler = make_handler(store)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"scratchpad listening on http://{args.host}:{args.port} (db={args.db})", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
