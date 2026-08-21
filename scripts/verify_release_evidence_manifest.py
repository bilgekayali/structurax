"""Verify a StructuraX release-evidence preview manifest against local artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.build_release_evidence_manifest import build_release_evidence_manifest
except ModuleNotFoundError:  # direct script execution
    from build_release_evidence_manifest import build_release_evidence_manifest


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_policy(path: str | Path = "configs/release_evidence_policy.json") -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return json.loads(candidate.read_text(encoding="utf-8"))


def verify_release_evidence_manifest(
    manifest_path: str | Path = "dist/structurax-release-evidence-manifest.json",
    dist_dir: str | Path = "dist",
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    if not manifest_file.is_absolute():
        manifest_file = ROOT / manifest_file
    dist = Path(dist_dir)
    if not dist.is_absolute():
        dist = ROOT / dist
    active = policy or load_policy()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    if manifest.get("format") != active["bundle_format"]:
        raise SystemExit("release evidence bundle format mismatch")
    roles = [item.get("role") for item in manifest.get("artifacts", [])]
    if roles != active["required_artifact_roles"]:
        raise SystemExit(f"release evidence role set/order mismatch: {roles}")

    for item in manifest["artifacts"]:
        path = dist / item["path"]
        if not path.is_file():
            raise SystemExit(f"release evidence artifact missing: {item['path']}")
        if _sha256(path) != item["sha256"]:
            raise SystemExit(f"release evidence digest mismatch: {item['path']}")
        if path.stat().st_size != item["bytes"]:
            raise SystemExit(f"release evidence size mismatch: {item['path']}")

    expected = build_release_evidence_manifest(dist)
    for key in (
        "format",
        "package",
        "package_version",
        "subject",
        "artifacts",
        "bundle_sha256",
    ):
        if manifest.get(key) != expected.get(key):
            raise SystemExit(f"release evidence manifest mismatch for {key}")

    for flag in (
        "formal_release_evidence_complete",
        "attestation_performed",
        "independent_security_review_verified",
        "production_readiness_claimed",
    ):
        if manifest.get(flag) is not False:
            raise SystemExit(f"preview release evidence must keep {flag}=false")

    return {
        "verified": True,
        "package": manifest["package"],
        "package_version": manifest["package_version"],
        "subject_sha256": manifest["subject"]["sha256"],
        "bundle_sha256": manifest["bundle_sha256"],
        "artifact_roles": roles,
        "formal_release_evidence_complete": False,
        "production_readiness_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify_release_evidence_manifest(), indent=2, sort_keys=True))
