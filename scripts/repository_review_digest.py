"""Compute the canonical Git-tracked repository digest for v0.4 independent review."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {"security-review/v0.4-review.json"}


def main() -> None:
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    paths = sorted(path.decode("utf-8") for path in raw.split(b"\0") if path)
    digest = hashlib.sha256()
    for relative in paths:
        if relative in EXCLUDED:
            continue
        path = ROOT / relative
        if not path.is_file():
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    print(digest.hexdigest())


if __name__ == "__main__":
    main()
