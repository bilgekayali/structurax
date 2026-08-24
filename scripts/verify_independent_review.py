"""Verify independent security-review evidence against the exact reviewed source surface."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts.release_surface_digest import compute_release_surface_digest
    from scripts.repository_review_digest import compute_repository_digest
except ModuleNotFoundError:  # direct script execution
    from release_surface_digest import compute_release_surface_digest
    from repository_review_digest import compute_repository_digest


ROOT = Path(__file__).resolve().parents[1]
HEX64 = re.compile(r"^[a-f0-9]{64}$")
OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,159}$")
LEGACY_KEYS = {
    "schema_version",
    "reviewed_repository_sha256",
    "reviewer_id",
    "reviewer_independence_confirmed",
    "review_evidence_sha256",
    "completed_at",
}
V1_KEYS = {
    "schema_version",
    "release_surface_sha256",
    "reviewer_id",
    "reviewer_independence_confirmed",
    "review_outcome",
    "review_areas",
    "external_report_artifact_id",
    "review_evidence_sha256",
    "open_findings",
    "open_release_blocking_findings",
    "risk_acceptance_required",
    "completed_at",
    "raw_secret_material_present",
    "production_readiness_claimed",
}
FINDING_KEYS = {"critical", "high", "medium", "low", "informational"}
PLACEHOLDER_REVIEWER_IDS = {
    "independent-reviewer",
    "reviewer",
    "example-reviewer",
    "test-reviewer",
    "demo-reviewer",
}


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("completed_at must include timezone information")
    return parsed


def _load_policy(path: str | Path = "configs/independent_security_review_policy.json") -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("independent security review policy must be a JSON object")
    return payload


def _reviewer_id(value: Any, *, reject_placeholders: bool) -> str:
    if not isinstance(value, str) or not (3 <= len(value) <= 160):
        raise SystemExit("reviewer_id length is invalid")
    if reject_placeholders and value.strip().lower() in PLACEHOLDER_REVIEWER_IDS:
        raise SystemExit("reviewer_id cannot use a placeholder identity")
    return value


def _evidence_digest(value: Any) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise SystemExit("review evidence digest must be lowercase sha256")
    if value == "0" * 64:
        raise SystemExit("review evidence digest cannot be an all-zero placeholder")
    return value


def _verify_evidence_file(evidence_path: str | Path | None, expected_sha256: str) -> str:
    if evidence_path is None:
        raise SystemExit("v1.0 independent review requires the external review evidence file")
    path = Path(evidence_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise SystemExit(f"independent review evidence file not found: {path}")
    observed = hashlib.sha256(path.read_bytes()).hexdigest()
    if observed != expected_sha256:
        raise SystemExit(
            "independent review evidence digest mismatch: "
            f"expected {expected_sha256}, got {observed}"
        )
    return observed


def _verify_legacy_review(
    review: dict[str, Any],
    expected_repository_sha256: str | None,
) -> dict[str, Any]:
    if set(review) != LEGACY_KEYS:
        raise SystemExit(f"independent review keys must be exact: {sorted(LEGACY_KEYS)}")
    if review["schema_version"] != "0.4.0":
        raise SystemExit("legacy independent review must use schema version 0.4.0")
    if review["reviewer_independence_confirmed"] is not True:
        raise SystemExit("reviewer independence must be explicitly confirmed")
    reviewer = _reviewer_id(review["reviewer_id"], reject_placeholders=False)
    evidence_digest = _evidence_digest(review["review_evidence_sha256"])
    try:
        _timestamp(review["completed_at"])
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"invalid completed_at: {exc}") from exc

    expected = expected_repository_sha256 or compute_repository_digest()
    if not HEX64.fullmatch(expected):
        raise SystemExit("expected repository digest is invalid")
    if review["reviewed_repository_sha256"] != expected:
        raise SystemExit(
            "independent review is not bound to the exact repository digest: "
            f"expected {expected}, got {review['reviewed_repository_sha256']}"
        )

    return {
        "verified": True,
        "schema_version": "0.4.0",
        "reviewed_repository_sha256": expected,
        "repository_digest_algorithm": "sha256-git-tracked-excluding-evidence",
        "reviewer_id": reviewer,
        "review_evidence_sha256": evidence_digest,
        "review_evidence_verified": False,
        "independent_security_review_verified": True,
        "formal_release_gate_updated": False,
        "production_readiness_claimed": False,
    }


def _verify_v1_review(
    review: dict[str, Any],
    expected_repository_sha256: str | None,
    evidence_path: str | Path | None,
    policy_path: str | Path,
) -> dict[str, Any]:
    if set(review) != V1_KEYS:
        raise SystemExit(f"v1.0 independent review keys must be exact: {sorted(V1_KEYS)}")
    if review["schema_version"] != "1.0.0":
        raise SystemExit("v1.0 independent review must use schema version 1.0.0")
    if review["reviewer_independence_confirmed"] is not True:
        raise SystemExit("reviewer independence must be explicitly confirmed")
    if review["review_outcome"] != "passed":
        raise SystemExit("independent review outcome must be passed")
    if review["raw_secret_material_present"] is not False:
        raise SystemExit("independent review envelope cannot declare raw secret material")
    if review["production_readiness_claimed"] is not False:
        raise SystemExit("independent review cannot claim production readiness")

    policy = _load_policy(policy_path)
    required_areas = policy["required_review_areas"]
    if review["review_areas"] != required_areas:
        raise SystemExit("independent review must cover the exact required review areas")

    reviewer = _reviewer_id(review["reviewer_id"], reject_placeholders=True)
    artifact_id = review["external_report_artifact_id"]
    if not isinstance(artifact_id, str) or OPAQUE_ID.fullmatch(artifact_id) is None:
        raise SystemExit("external_report_artifact_id must be an opaque identifier")

    evidence_digest = _evidence_digest(review["review_evidence_sha256"])
    observed_evidence_digest = _verify_evidence_file(evidence_path, evidence_digest)

    findings = review["open_findings"]
    if not isinstance(findings, dict) or set(findings) != FINDING_KEYS:
        raise SystemExit(f"open_findings keys must be exact: {sorted(FINDING_KEYS)}")
    for severity in FINDING_KEYS:
        value = findings[severity]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SystemExit(f"open_findings.{severity} must be a non-negative integer")
    if findings["critical"] != policy["max_open_critical_findings"]:
        raise SystemExit("open critical findings exceed the release policy")
    if findings["high"] != policy["max_open_high_findings"]:
        raise SystemExit("open high findings exceed the release policy")
    if review["open_release_blocking_findings"] != policy["max_open_release_blocking_findings"]:
        raise SystemExit("open release-blocking findings exceed the release policy")
    if review["risk_acceptance_required"] is not policy["risk_acceptance_required"]:
        raise SystemExit("independent review still requires risk acceptance")

    try:
        _timestamp(review["completed_at"])
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"invalid completed_at: {exc}") from exc

    expected = expected_repository_sha256 or compute_release_surface_digest()
    if not isinstance(expected, str) or not HEX64.fullmatch(expected):
        raise SystemExit("expected release-surface digest is invalid")
    if review["release_surface_sha256"] != expected:
        raise SystemExit(
            "independent review is not bound to the exact v1.0 release-surface digest: "
            f"expected {expected}, got {review['release_surface_sha256']}"
        )

    return {
        "verified": True,
        "schema_version": "1.0.0",
        "reviewed_repository_sha256": expected,
        "repository_digest_algorithm": policy["release_surface_digest_algorithm"],
        "reviewer_id": reviewer,
        "review_outcome": "passed",
        "review_areas": required_areas,
        "external_report_artifact_id": artifact_id,
        "review_evidence_sha256": evidence_digest,
        "review_evidence_verified": observed_evidence_digest == evidence_digest,
        "open_findings": findings,
        "open_release_blocking_findings": 0,
        "risk_acceptance_required": False,
        "independent_security_review_verified": True,
        "formal_release_gate_updated": False,
        "production_readiness_claimed": False,
    }


def verify_independent_review(
    review_path: str | Path,
    expected_repository_sha256: str | None = None,
    evidence_path: str | Path | None = None,
    required_schema_version: str | None = None,
    policy_path: str | Path = "configs/independent_security_review_policy.json",
) -> dict[str, Any]:
    path = Path(review_path)
    if not path.is_absolute():
        path = ROOT / path
    review = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(review, dict):
        raise SystemExit("independent review must be a JSON object")
    schema_version = review.get("schema_version")
    if required_schema_version is not None and schema_version != required_schema_version:
        raise SystemExit(
            f"independent review must use required schema version {required_schema_version}"
        )
    if schema_version == "0.4.0":
        return _verify_legacy_review(review, expected_repository_sha256)
    if schema_version == "1.0.0":
        return _verify_v1_review(
            review,
            expected_repository_sha256,
            evidence_path,
            policy_path,
        )
    raise SystemExit(f"unsupported independent review schema version: {schema_version!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", default="security-review/v1.0-review.json")
    parser.add_argument("--evidence-file")
    parser.add_argument("--expected-repository-sha256")
    parser.add_argument("--required-schema-version")
    parser.add_argument("--policy", default="configs/independent_security_review_policy.json")
    args = parser.parse_args()
    required_schema_version = args.required_schema_version
    if required_schema_version is None and Path(args.review).name == "v1.0-review.json":
        required_schema_version = "1.0.0"
    print(
        json.dumps(
            verify_independent_review(
                args.review,
                args.expected_repository_sha256,
                args.evidence_file,
                required_schema_version,
                args.policy,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
