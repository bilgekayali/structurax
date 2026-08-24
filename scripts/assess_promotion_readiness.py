"""Build a fail-closed v1.0 promotion-readiness matrix without mutating formal release state."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import structurax

try:
    from scripts.assess_release_gate import load_gate
    from scripts.assess_repository_governance import assess_snapshot, fetch_branch_snapshot
    from scripts.release_surface_digest import compute_release_surface_digest
    from scripts.verify_branch_protection_snapshot import verify_branch_protection_snapshot
    from scripts.verify_independent_review import verify_independent_review
    from scripts.verify_production_evidence import verify_production_evidence
except ModuleNotFoundError:  # direct script execution
    from assess_release_gate import load_gate
    from assess_repository_governance import assess_snapshot, fetch_branch_snapshot
    from release_surface_digest import compute_release_surface_digest
    from verify_branch_protection_snapshot import verify_branch_protection_snapshot
    from verify_independent_review import verify_independent_review
    from verify_production_evidence import verify_production_evidence


ROOT = Path(__file__).resolve().parents[1]


def load_policy(path: str | Path = "configs/promotion_readiness_policy.json") -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("promotion readiness policy must be a JSON object")
    return payload


def _load_json(path: str | Path) -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected JSON object: {candidate}")
    return payload


def _missing_protection_assessment() -> dict[str, Any]:
    return {
        "branch_protection_verified": False,
        "main_branch_protection_verified": False,
        "required_status_checks_verified": False,
        "codeql_release_gate_enforced": False,
        "manual_controls_verified": False,
        "blockers": ["branch_protection_snapshot_missing"],
        "formal_gate_mutation_authorized": False,
        "production_readiness_claimed": False,
    }


def _independent_review_assessment(
    review_path: str | Path | None,
    evidence_path: str | Path | None,
    repository_digest: str,
) -> dict[str, Any]:
    configured = Path(review_path or "security-review/v1.0-review.json")
    if not configured.is_absolute():
        configured = ROOT / configured
    if not configured.is_file():
        return {
            "available": False,
            "evidence_available": False,
            "verified": False,
            "independent_security_review_verified": False,
            "blockers": ["independent_security_review_missing"],
            "formal_release_gate_updated": False,
            "production_readiness_claimed": False,
        }

    if evidence_path is None:
        return {
            "available": True,
            "evidence_available": False,
            "verified": False,
            "independent_security_review_verified": False,
            "blockers": ["independent_security_review_evidence_missing"],
            "formal_release_gate_updated": False,
            "production_readiness_claimed": False,
        }

    verified = verify_independent_review(
        configured,
        repository_digest,
        evidence_path=evidence_path,
        required_schema_version="1.0.0",
    )
    return {
        "available": True,
        "evidence_available": True,
        "verified": verified["verified"] is True,
        "independent_security_review_verified": (
            verified["independent_security_review_verified"] is True
        ),
        "schema_version": verified["schema_version"],
        "reviewer_id": verified["reviewer_id"],
        "review_outcome": verified["review_outcome"],
        "review_areas": verified["review_areas"],
        "external_report_artifact_id": verified["external_report_artifact_id"],
        "review_evidence_sha256": verified["review_evidence_sha256"],
        "review_evidence_verified": verified["review_evidence_verified"] is True,
        "open_findings": verified["open_findings"],
        "open_release_blocking_findings": verified["open_release_blocking_findings"],
        "risk_acceptance_required": verified["risk_acceptance_required"],
        "blockers": [],
        "formal_release_gate_updated": False,
        "production_readiness_claimed": False,
    }


def assess_promotion_readiness(
    *,
    gate: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    branch_snapshot: dict[str, Any] | None = None,
    protection_snapshot: dict[str, Any] | None = None,
    production_evidence_path: str | Path | None = None,
    trusted_production_key_path: str | Path | None = None,
    independent_review_path: str | Path | None = None,
    independent_review_evidence_path: str | Path | None = None,
    package_version: str | None = None,
    repository_digest: str | None = None,
) -> dict[str, Any]:
    active_gate = gate or load_gate()
    active_policy = policy or load_policy()
    candidate_checks = dict(active_gate["checks"])
    digest = repository_digest or compute_release_surface_digest(ROOT)

    if branch_snapshot is None:
        branch_report = {
            "protected": False,
            "observable_governance_eligible": False,
            "blockers": ["live_branch_summary_missing"],
            "production_readiness_claimed": False,
        }
    else:
        branch_report = assess_snapshot(branch_snapshot)

    protection_report = (
        verify_branch_protection_snapshot(protection_snapshot)
        if protection_snapshot is not None
        else _missing_protection_assessment()
    )
    live_protected = branch_report.get("protected") is True
    candidate_checks["main_branch_protection_verified"] = bool(
        live_protected and protection_report["main_branch_protection_verified"]
    )
    candidate_checks["required_status_checks_verified"] = bool(
        live_protected and protection_report["required_status_checks_verified"]
    )
    candidate_checks["codeql_release_gate_enforced"] = bool(
        live_protected and protection_report["codeql_release_gate_enforced"]
    )

    production_report = verify_production_evidence(
        production_evidence_path,
        trusted_production_key_path,
        repository_digest=digest,
    )
    for check, passed in production_report["candidate_checks"].items():
        candidate_checks[check] = passed is True

    review_report = _independent_review_assessment(
        independent_review_path,
        independent_review_evidence_path,
        digest,
    )
    candidate_checks["independent_security_review_verified"] = (
        review_report["independent_security_review_verified"] is True
    )

    required_version = active_policy["required_release_version"]
    observed_version = package_version or structurax.__version__
    blockers = sorted(name for name, passed in candidate_checks.items() if passed is not True)
    blockers.extend(review_report.get("blockers", []))
    if observed_version != required_version:
        blockers.append("package_version_not_1_0_0")
    blockers = sorted(set(blockers))

    domains: dict[str, Any] = {}
    for domain, checks in active_policy["gate_check_domains"].items():
        failed = [name for name in checks if candidate_checks.get(name) is not True]
        domains[domain] = {
            "checks": {name: candidate_checks.get(name) is True for name in checks},
            "eligible": not failed,
            "blockers": failed,
        }

    ready_for_human_promotion = not blockers
    return {
        "policy_version": active_policy["policy_version"],
        "gate_version": active_gate["gate_version"],
        "repository_sha256": digest,
        "repository_digest_algorithm": active_policy["release_surface_digest_algorithm"],
        "package_version": observed_version,
        "required_release_version": required_version,
        "candidate_checks": candidate_checks,
        "domains": domains,
        "branch_summary": branch_report,
        "branch_protection": protection_report,
        "production_evidence": production_report,
        "independent_security_review": review_report,
        "blockers": blockers,
        "ready_for_human_promotion": ready_for_human_promotion,
        "human_promotion_required": active_policy["human_promotion_required"] is True,
        "formal_gate_mutation_authorized": False,
        "production_readiness_claimed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--branch-snapshot")
    parser.add_argument("--protection-snapshot")
    parser.add_argument("--production-evidence")
    parser.add_argument("--trusted-production-key")
    parser.add_argument("--independent-review")
    parser.add_argument("--independent-review-evidence")
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.branch_snapshot:
        branch_snapshot = _load_json(args.branch_snapshot)
    else:
        repository = args.repository or os.environ.get("GITHUB_REPOSITORY")
        if not repository:
            raise SystemExit("repository or --branch-snapshot is required")
        branch_snapshot = fetch_branch_snapshot(repository, args.branch)

    protection_snapshot = _load_json(args.protection_snapshot) if args.protection_snapshot else None
    result = assess_promotion_readiness(
        branch_snapshot=branch_snapshot,
        protection_snapshot=protection_snapshot,
        production_evidence_path=args.production_evidence,
        trusted_production_key_path=args.trusted_production_key,
        independent_review_path=args.independent_review,
        independent_review_evidence_path=args.independent_review_evidence,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
