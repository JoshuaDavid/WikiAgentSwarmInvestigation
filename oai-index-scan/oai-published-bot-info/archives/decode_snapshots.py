"""Decode any brotli- or gzip-compressed snapshot files in place so every
archived file is plain JSON, matching the shape of the non-archived files
at `../<bot>-scraper-*.json`.

Archive.org serves the raw stored bytes when the URL uses the `id_` rewrite,
so if `openai.com` responded with `Content-Encoding: br` or `gzip` the
snapshot on disk is the compressed body. Loading that as JSON fails, so this
script sniffs the first bytes, decompresses, verifies the result parses as
JSON, and writes it back.

Files that already contain plain JSON are left unchanged.
"""
import gzip
import json
from pathlib import Path

try:
    import brotli
    HAVE_BROTLI = True
except ImportError:
    HAVE_BROTLI = False

ROOT = Path(__file__).parent
BOTS = ["gptbot", "searchbot", "chatgpt-user"]

def try_decode(data):
    """Return (plaintext, encoding) or (None, reason)."""
    if data[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(data).decode("utf-8"), "gzip"
        except Exception as e:
            return None, f"gzip-fail:{e}"
    try:
        text = data.decode("utf-8")
        json.loads(text)
        return text, "plain"
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    if HAVE_BROTLI:
        try:
            return brotli.decompress(data).decode("utf-8"), "brotli"
        except Exception as e:
            return None, f"brotli-fail:{e}"
    return None, "unknown-encoding"

def main():
    for bot in BOTS:
        d = ROOT / bot
        counts = {"plain": 0, "gzip": 0, "brotli": 0, "failed": 0}
        failures = []
        for f in sorted(d.iterdir()):
            data = f.read_bytes()
            if not data:
                counts["failed"] += 1
                failures.append((f.name, "empty")); continue
            text, enc = try_decode(data)
            if text is None:
                counts["failed"] += 1
                failures.append((f.name, enc)); continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as e:
                counts["failed"] += 1
                failures.append((f.name, f"post-decode json-fail:{e}")); continue
            counts[enc] += 1
            if enc != "plain":
                f.write_text(text)
        print(f"{bot}: {counts}")
        for name, why in failures[:5]:
            print(f"  fail: {name}  reason={why}")

if __name__ == "__main__":
    main()
