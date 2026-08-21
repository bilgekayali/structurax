"""Compute the v1.0 release-surface digest across Git-tracked source and policy state.

The digest intentionally canonicalizes only the mechanical release metadata that is allowed
to change during the final human-reviewed promotion transaction. Code, schemas, workflows,
security policy, dependencies and every other tracked byte remain digest-significant.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_EVIDENCE = {
    "security-review/v0.4-review.json",
    "security-review/v1.0-review.json",
    "production-evidence/v1.0-controls.json",
    "release-approval/v1.0-promotion.json",
}

_PROJECT_VERSION = re.compile(rb'(?m)^version = "[^"]+"$')
_PROJECT_STATUS = re.compile(rb'(?m)^  "Development Status :: [0-9] - [^"]+",$')
_PACKAGE_VERSION = re.compile(rb'(?m)^__version__ = "[^"]+"$')


def canonicalize_release_metadata(relative: str, content: bytes) -> bytes:
    """Normalize only promotion-approved metadata fields for release-surface hashing."""
    if relative == "pyproject.toml":
        content, version_count = _PROJECT_VERSION.subn(b'version = "<release-version>"', content)
        content, status_count = _PROJECT_STATUS.subn(
            b'  "Development Status :: <release-status>",', content
        )
        if version_count != 1:
            raise SystemExit("pyproject.toml must contain exactly one project version field")
        if status_count != 1:
            raise SystemExit("pyproject.toml must contain exactly one development-status classifier")
    elif relative == "src/structurax/__init__.py":
        content, count = _PACKAGE_VERSION.subn(b'__version__ = "<release-version>"', content)
        if count != 1:
            raise SystemExit("src/structurax/__init__.py must contain exactly one __version__ field")
    return content


def compute_release_surface_digest(root: str | Path = ROOT) -> str:
    base = Path(root)
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=base)
    paths = sorted(path.decode("utf-8") for path in raw.split(b"\0") if path)
    digest = hashlib.sha256()
    for relative in paths:
        if relative in EXCLUDED_EVIDENCE:
            continue
        path = base / relative
        if not path.is_file():
            continue
        content = canonicalize_release_metadata(relative, path.read_bytes())
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def main() -> None:
    print(compute_release_surface_digest())


if __name__ == "__main__":
    main()
