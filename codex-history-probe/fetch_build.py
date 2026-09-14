"""Download one official release binary and verify the release API's digest."""

import hashlib
import json
from pathlib import Path
import sys
import tarfile
import urllib.request

base = Path(__file__).resolve().parent
version = sys.argv[1]
tag = "rust-v" + version
metadata_path = base / (version + "-release.json")
if metadata_path.exists():
    release = json.loads(metadata_path.read_text())
else:
    request = urllib.request.Request(
        "https://api.github.com/repos/openai/codex/releases/tags/" + tag,
        headers={"User-Agent": "codex-history-audit"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    metadata_path.write_text(json.dumps(release, indent=2))
assert release["tag_name"] == tag
asset = next(a for a in release["assets"]
             if a["name"] == "codex-aarch64-unknown-linux-musl.tar.gz")
expected_url = "https://github.com/openai/codex/releases/download/" + tag + "/" + asset["name"]
assert asset["browser_download_url"] == expected_url
target = base / version
target.mkdir(exist_ok=True)
archive = target / asset["name"]
if not archive.exists():
    request = urllib.request.Request(expected_url, headers={"User-Agent": "codex-history-audit"})
    with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
with archive.open("rb") as source:
    digest = "sha256:" + hashlib.file_digest(source, "sha256").hexdigest()
if digest != asset["digest"]:
    raise RuntimeError("Release digest mismatch: " + version)
binary = target / "codex"
with tarfile.open(archive) as tar:
    member = next(m for m in tar.getmembers()
                  if m.isfile() and Path(m.name).name == "codex-aarch64-unknown-linux-musl")
    with tar.extractfile(member) as source, binary.open("wb") as output:
        while chunk := source.read(1024 * 1024):
            output.write(chunk)
binary.chmod(0o755)
print(json.dumps({"version": version, "published_at": release["published_at"],
                  "verified_digest": digest, "binary": str(binary)}))
