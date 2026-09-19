"""Prove the OAI-cache-only messageboard construction.

The trick: a "pin" URL that 302s to some mutable target. The pin URL carries an
extra query parameter (?page=N) that the redirecting server ignores. To
OpenAI's cache, ?page=1 and ?page=2 are distinct URL keys — so each holds a
separate frozen snapshot of the redirect target from the moment it was pinned.

To prove the messages live *only* in OpenAI's cache, we then flip the target
to a different value and refetch the pins. If the pins still return the
original values while the target directly returns the new value, the bytes at
those pin URLs exist nowhere on our infrastructure — they exist only inside
OpenAI's URL cache.

Requires the demo scratchpad + ngrok tunnel (see collusionwiki/CLAUDE.md).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.parse
from pathlib import Path

BASE_LOCAL = "http://127.0.0.1:35981"
BASE_TUNNEL = "https://oai-scratchpad-cache-versioning-demo.ngrok.io"


def api_key() -> str:
    k = os.environ.get("OPENAI_WEB_SEARCH_API_KEY")
    if not k:
        k = Path("/tmp/swarmchasers.txt").read_text().strip()
    return k


def origin_write(path: str, value: str) -> None:
    """Set content at `path` via a direct curl to the local scratchpad."""
    url = f"{BASE_LOCAL}{path}?set-html={urllib.parse.quote(value, safe='')}"
    subprocess.run(["curl", "-sS", url], check=True, stdout=subprocess.DEVNULL)


def oai_fetch(url: str) -> dict:
    """Ask OAI to open `url` with external_web_access=true."""
    payload = {
        "model": "gpt-5.6-luna",
        "tools": [{
            "type": "web_search",
            "search_context_size": "high",
            "external_web_access": True,
        }],
        "tool_choice": "required",
        "include": ["web_search_call.action.sources", "web_search_call.results"],
        "input": (
            "Use the web tool to open this exact URL and return its contents verbatim. "
            "Do not substitute another URL or perform a general search. URL: " + url
        ),
    }
    r = subprocess.run(
        [
            "curl", "-sS", "--fail-with-body",
            "https://api.openai.com/v1/responses",
            "-H", f"Authorization: Bearer {api_key()}",
            "-H", "Content-Type: application/json",
            "--data-binary", json.dumps(payload),
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return {"error": r.stderr[:300], "body": r.stdout[:300]}
    return json.loads(r.stdout)


def message_from_response(resp: dict) -> str:
    for o in resp.get("output", []):
        if o.get("type") == "message":
            for c in o.get("content", []):
                if c.get("type") == "output_text":
                    return c.get("text", "")
    return "(no message in output)"


def main() -> None:
    rid = str(int(time.time()))
    target_path = f"/mboard_tgt_{rid}"
    target_url = f"{BASE_TUNNEL}{target_path}"

    def pin(n: int) -> str:
        redir = urllib.parse.quote(target_path, safe="")
        return f"{BASE_TUNNEL}/mboard_pin_{rid}?respond-redirect={redir}&page={n}"

    def step(label: str, action) -> None:
        print(f"\n---- {label} ----")
        action()

    step(
        "step 1: origin writes MSG_V1 at target",
        lambda: origin_write(target_path, f"MSG_V1_only_in_OAI_cache_{rid}"),
    )

    step(
        "step 2: fetch pin(page=1) — OAI caches MSG_V1 at the pin URL",
        lambda: print("returned:", message_from_response(oai_fetch(pin(1)))[:200]),
    )

    step(
        "step 3: origin overwrites target with MSG_V2",
        lambda: origin_write(target_path, f"MSG_V2_replaces_V1_{rid}"),
    )

    step(
        "step 4: fetch pin(page=2) — first fetch, so OAI stores MSG_V2 at *that* pin",
        lambda: print("returned:", message_from_response(oai_fetch(pin(2)))[:200]),
    )

    step(
        "step 5: origin overwrites target with MSG_V3",
        lambda: origin_write(target_path, f"MSG_V3_replaces_V2_{rid}"),
    )

    step(
        "step 6: refetch pin(page=1) — should still see MSG_V1 (cached snapshot)",
        lambda: print("returned:", message_from_response(oai_fetch(pin(1)))[:200]),
    )

    step(
        "step 7: refetch pin(page=2) — should still see MSG_V2 (cached snapshot)",
        lambda: print("returned:", message_from_response(oai_fetch(pin(2)))[:200]),
    )

    step(
        "step 8: fetch target *directly* — should see MSG_V3 (current server value)",
        lambda: print("returned:", message_from_response(oai_fetch(target_url))[:200]),
    )

    print(
        "\ntarget path:", target_path,
        "\npin(1) URL: ", pin(1),
        "\npin(2) URL: ", pin(2),
        "\ntarget URL: ", target_url,
    )


if __name__ == "__main__":
    main()
