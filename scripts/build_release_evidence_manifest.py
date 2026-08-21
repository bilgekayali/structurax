"""Build a digest-bound release-evidence preview manifest for StructuraX."""
from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROLE_FILES = {
    "dependency_sbom": "structurax-dependency-sbom.cdx.json",
    "source_provenance": "structurax-source-provenance.json",
    "release_gate": "structurax-release-gate.json",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _artifact(role: str, path: Path) -> dict[str, Any]:
    return {
        "role": role,
        "path": path.name,
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def build_release_evidence_manifest(dist_dir: str | Path = "dist") -> dict[str, Any]:
    dist = Path(dist_dir)
    if not dist.is_absolute():
        dist = ROOT / dist
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    package = project["name"]
    version = project["version"]

    wheels = sorted(dist.glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"release evidence requires exactly one wheel; found {len(wheels)}")
    wheel = wheels[0]
    expected_prefix = f"{package.replace('-', '_')}-{version}-"
    if not wheel.name.startswith(expected_prefix):
        raise SystemExit(
            f"wheel identity does not match package/version: expected prefix {expected_prefix!r}, got {wheel.name!r}"
        )

    evidence_paths: dict[str, Path] = {"wheel": wheel}
    for role, filename in ROLE_FILES.items():
        path = dist / filename
        if not path.is_file():
            raise SystemExit(f"release evidence artifact missing for role {role}: {filename}")
        evidence_paths[role] = path

    sbom = _load_json(evidence_paths["dependency_sbom"])
    sbom_component = sbom.get("metadata", {}).get("component", {})
    if sbom_component.get("name") != package or sbom_component.get("version") != version:
        raise SystemExit("dependency SBOM root component does not match package/version")

    provenance = _load_json(evidence_paths["source_provenance"])
    if provenance.get("package") != package or provenance.get("package_version") != version:
        raise SystemExit("source provenance does not match package/version")
    if provenance.get("build_attestation") is not False:
        raise SystemExit("preview source provenance must not claim build attestation")

    release_gate = _load_json(evidence_paths["release_gate"])
    if release_gate.get("package_version") != version:
        raise SystemExit("release-gate evidence does not match package version")
    if release_gate.get("eligible") is not False:
        raise SystemExit("preview bundle must not claim formal release eligibility")

    ordered_roles = ("wheel", "dependency_sbom", "source_provenance", "release_gate")
    artifacts = [_artifact(role, evidence_paths[role]) for role in ordered_roles]
    subject = artifacts[0]
    core = {
        "format": "structurax-release-evidence/v1",
        "package": package,
        "package_version": version,
        "subject": {
            "path": subject["path"],
            "sha256": subject["sha256"],
        },
        "artifacts": artifacts,
    }
    return {
        **core,
        "bundle_sha256": _canonical_sha256(core),
        "formal_release_evidence_complete": False,
        "attestation_performed": False,
        "independent_security_review_verified": False,
        "production_readiness_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(build_release_evidence_manifest(), indent=2, sort_keys=True))
