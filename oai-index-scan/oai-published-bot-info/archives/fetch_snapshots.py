"""Fetch every archive.org snapshot of the three OpenAI-published bot IP
range files and drop each snapshot into an archives/<bot>/<timestamp>.json
path.

For each bot, hit the CDX index at
`http://web.archive.org/cdx/search/cdx?url=openai.com/<name>.json&output=json`,
then GET each snapshot's raw body via the `id_` (identity) rewrite so we get
the original bytes IA stored.

A 3-second sleep runs between every archive.org request, per the user's
instructions. Existing local files are skipped so re-running the script only
fetches new snapshots.
"""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BOTS = {
    "gptbot":       "openai.com/gptbot.json",
    "searchbot":    "openai.com/searchbot.json",
    "chatgpt-user": "openai.com/chatgpt-user.json",
}

ROOT = Path(__file__).parent
SLEEP_SECS = 3

def http_get(url, timeout=60, max_retries=5):
    """archive.org returns 503 semi-frequently; retry with backoff."""
    req = urllib.request.Request(url, headers={"User-Agent": "collusionwiki-oai-snapshot-fetcher/1.0"})
    last_err = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read(), resp.status, dict(resp.headers)
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code not in (429, 502, 503, 504):
                raise
            backoff = SLEEP_SECS + 2 * (2 ** attempt)
            print(f"    HTTP {e.code} on {url} (attempt {attempt+1}/{max_retries}); sleep {backoff}s")
            time.sleep(backoff)
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            backoff = SLEEP_SECS + 2 * (2 ** attempt)
            print(f"    {e!r} on {url} (attempt {attempt+1}/{max_retries}); sleep {backoff}s")
            time.sleep(backoff)
    raise last_err

def cdx_rows(target):
    url = f"http://web.archive.org/cdx/search/cdx?url={target}&output=json"
    body, status, _ = http_get(url)
    data = json.loads(body.decode("utf-8"))
    if not data:
        return []
    header, *rows = data
    return [dict(zip(header, r)) for r in rows]

def fetch_bot(bot_name, target):
    out_dir = ROOT / bot_name
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {bot_name}  ({target}) ===")
    rows = cdx_rows(target)
    print(f"  CDX returned {len(rows)} snapshots")
    time.sleep(SLEEP_SECS)

    for i, r in enumerate(rows, 1):
        ts = r["timestamp"]
        original = r["original"]
        status = r.get("statuscode")
        mime = r.get("mimetype", "")
        out_path = out_dir / f"{ts}.json"
        if out_path.exists():
            print(f"  [{i:>3}/{len(rows)}]  {ts}  status={status}  already have, skip")
            continue

        snap_url = f"http://web.archive.org/web/{ts}id_/{original}"
        try:
            body, http_status, _ = http_get(snap_url)
        except urllib.error.HTTPError as e:
            print(f"  [{i:>3}/{len(rows)}]  {ts}  HTTP {e.code}  giving up on {snap_url}")
            time.sleep(SLEEP_SECS)
            continue
        except Exception as e:
            print(f"  [{i:>3}/{len(rows)}]  {ts}  ERR {e!r}")
            time.sleep(SLEEP_SECS)
            continue

        out_path.write_bytes(body)
        print(f"  [{i:>3}/{len(rows)}]  {ts}  {len(body):>6} B  status={status}  mime={mime}")
        time.sleep(SLEEP_SECS)

def main():
    for bot, target in BOTS.items():
        try:
            fetch_bot(bot, target)
        except Exception as e:
            print(f"\n!! failed on {bot}: {e!r}")

if __name__ == "__main__":
    main()
