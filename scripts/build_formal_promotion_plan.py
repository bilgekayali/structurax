"""Build a fail-closed two-phase v1.0 formal-promotion plan without mutating the repository."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.release_surface_digest import compute_release_surface_digest
except ModuleNotFoundError:  # direct script execution
    from release_surface_digest import compute_release_surface_digest

ROOT = Path(__file__).resolve().parents[1]
_SHA40 = re.compile(r"^[a-f0-9]{40}$")


def load_policy(path: str | Path = "configs/formal_promotion_policy.json") -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("formal promotion policy must be a JSON object")
    return payload


def _load_json(path: str | Path) -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected JSON object: {candidate}")
    return payload


def build_formal_promotion_plan(
    readiness: dict[str, Any],
    expected_head_sha: str,
    *,
    policy: dict[str, Any] | None = None,
    release_surface_sha256: str | None = None,
) -> dict[str, Any]:
    active = policy or load_policy()
    if _SHA40.fullmatch(expected_head_sha) is None:
        raise SystemExit("expected_head_sha must be an exact lowercase 40-character Git SHA")

    surface_digest = release_surface_sha256 or compute_release_surface_digest(ROOT)
    if readiness.get("repository_sha256") != surface_digest:
        raise SystemExit("promotion readiness is bound to a different v1.0 release-surface digest")
    if readiness.get("human_promotion_required") is not True:
        raise SystemExit("promotion readiness must require human promotion")
    if readiness.get("formal_gate_mutation_authorized") is not False:
        raise SystemExit("promotion readiness cannot authorize automatic formal-gate mutation")
    if readiness.get("production_readiness_claimed") is not False:
        raise SystemExit("promotion readiness cannot pre-claim production readiness")

    checks = readiness.get("candidate_checks")
    if not isinstance(checks, dict) or not checks:
        raise SystemExit("promotion readiness candidate_checks are missing")
    failed_checks = sorted(name for name, passed in checks.items() if passed is not True)

    observed_version = readiness.get("package_version")
    baseline_version = active["package_baseline_version"]
    target_version = active["target_version"]
    blockers = list(failed_checks)
    if baseline_version != target_version:
        blockers.append("package_baseline_target_mismatch")
    if observed_version != baseline_version:
        blockers.append("package_baseline_version_mismatch")

    readiness_blockers = readiness.get("blockers", [])
    if not isinstance(readiness_blockers, list):
        raise SystemExit("promotion readiness blockers must be a list")
    if readiness_blockers:
        blockers.append("promotion_readiness_has_blockers")
    if readiness.get("ready_for_human_promotion") is not True:
        blockers.append("promotion_readiness_not_ready")

    blockers = sorted(set(blockers))
    eligible = not blockers
    return {
        "policy_version": active["policy_version"],
        "release_surface_sha256": surface_digest,
        "expected_head_sha": expected_head_sha,
        "observed_version": observed_version,
        "package_baseline_version": baseline_version,
        "target_version": target_version,
        "target_tag": active["target_tag"],
        "promotion_plan_eligible": eligible,
        "blockers": blockers,
        "metadata_mutations": active["allowed_metadata_mutations"] if eligible else [],
        "required_post_mutation_checks": active["required_post_mutation_checks"],
        "human_approval_required": active["human_approval_required"] is True,
        "automatic_metadata_mutation_allowed": False,
        "automatic_tag_creation_allowed": False,
        "automatic_publish_allowed": False,
        "formal_gate_mutation_authorized": False,
        "production_readiness_claimed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness", required=True)
    parser.add_argument("--expected-head-sha", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = build_formal_promotion_plan(_load_json(args.readiness), args.expected_head_sha)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
