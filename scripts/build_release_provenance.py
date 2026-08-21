"""Build deterministic source/dependency provenance for v1.0 preparation."""
from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files(patterns: Iterable[str]) -> list[Path]:
    found: set[Path] = set()
    for pattern in patterns:
        found.update(path for path in ROOT.glob(pattern) if path.is_file())
    return sorted(found, key=lambda path: path.as_posix())


def build_manifest() -> dict[str, object]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    tracked = _files(
        (
            "src/structurax/*.py",
            "configs/*.json",
            "schemas/*.json",
            "scripts/*.py",
            "sql/*.sql",
        )
    )
    files = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in tracked
    ]
    manifest = {
        "format": "structurax-release-provenance/v1",
        "package": project["name"],
        "package_version": project["version"],
        "python_requires": project["requires-python"],
        "declared_dependencies": sorted(project.get("dependencies", [])),
        "files": files,
        "source_tree_sha256": hashlib.sha256(
            "\n".join(f"{item['path']}:{item['sha256']}" for item in files).encode("utf-8")
        ).hexdigest(),
        "resolved_dependency_sbom": False,
        "build_attestation": False,
        "production_readiness_claimed": False,
    }
    return manifest


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
