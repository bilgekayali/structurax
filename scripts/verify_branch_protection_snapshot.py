"""Verify a GitHub branch-protection response against StructuraX governance policy."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.assess_repository_governance import load_policy
except ModuleNotFoundError:  # direct script execution
    from assess_repository_governance import load_policy


def _enabled(value: Any) -> bool:
    if isinstance(value, dict):
        return value.get("enabled") is True
    return value is True


def verify_branch_protection_snapshot(
    snapshot: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active = policy or load_policy()
    manual = active["manual_controls_expected"]
    blockers: list[str] = []

    status = snapshot.get("required_status_checks")
    if not isinstance(status, dict):
        blockers.append("required_status_checks_missing")
        observed_contexts: list[str] = []
        strict = False
    else:
        observed_contexts = sorted(set(status.get("contexts") or []))
        strict = status.get("strict") is True

    expected_contexts = sorted(set(active["required_status_checks"]))
    missing = sorted(set(expected_contexts) - set(observed_contexts))
    unexpected = sorted(set(observed_contexts) - set(expected_contexts))
    if missing:
        blockers.append("required_status_checks_missing")
    if unexpected:
        blockers.append("unexpected_required_status_checks")
    if strict != (manual["strict_status_checks"] is True):
        blockers.append("strict_status_checks_mismatch")

    reviews = snapshot.get("required_pull_request_reviews")
    if manual["pull_request_required"] is True and not isinstance(reviews, dict):
        blockers.append("pull_request_reviews_missing")
        reviews = {}
    elif not isinstance(reviews, dict):
        reviews = {}

    review_expectations = {
        "dismiss_stale_reviews": manual["dismiss_stale_reviews"] is True,
        "require_code_owner_reviews": manual["require_code_owner_reviews"] is True,
        "require_last_push_approval": manual["require_last_push_approval"] is True,
        "required_approving_review_count": int(manual["required_approving_reviews"]),
    }
    for key, expected in review_expectations.items():
        if reviews.get(key) != expected:
            blockers.append(f"{key}_mismatch")

    observed_enforce_admins = _enabled(snapshot.get("enforce_admins"))
    if observed_enforce_admins != (manual["enforce_admins"] is True):
        blockers.append("enforce_admins_mismatch")

    boolean_controls = {
        "required_conversation_resolution": manual["conversation_resolution_required"] is True,
        "allow_force_pushes": manual["force_pushes_allowed"] is True,
        "allow_deletions": manual["branch_deletion_allowed"] is True,
        "required_linear_history": manual["required_linear_history"] is True,
    }
    for field, expected in boolean_controls.items():
        if _enabled(snapshot.get(field)) != expected:
            blockers.append(f"{field}_mismatch")

    required_checks_verified = (
        not missing
        and not unexpected
        and strict == (manual["strict_status_checks"] is True)
    )
    codeql_enforced = required_checks_verified and "CodeQL (python)" in observed_contexts
    protection_verified = not blockers

    return {
        "policy_version": active["policy_version"],
        "branch": active["branch"],
        "branch_protection_verified": protection_verified,
        "main_branch_protection_verified": protection_verified,
        "required_status_checks_verified": required_checks_verified,
        "codeql_release_gate_enforced": codeql_enforced,
        "manual_controls_verified": protection_verified,
        "observed_status_checks": observed_contexts,
        "required_status_checks": expected_contexts,
        "missing_status_checks": missing,
        "unexpected_status_checks": unexpected,
        "blockers": sorted(set(blockers)),
        "formal_gate_mutation_authorized": False,
        "production_readiness_claimed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    args = parser.parse_args()
    path = Path(args.snapshot)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict):
        raise SystemExit("branch protection snapshot must be a JSON object")
    print(json.dumps(verify_branch_protection_snapshot(snapshot), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
