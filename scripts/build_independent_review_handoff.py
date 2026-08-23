"""Build a non-authoritative handoff manifest for a genuine independent v1.0 security review."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from scripts.release_surface_digest import compute_release_surface_digest
except ModuleNotFoundError:  # direct script execution
    from release_surface_digest import compute_release_surface_digest


ROOT = Path(__file__).resolve().parents[1]
SHA40 = re.compile(r"^[a-f0-9]{40}$")


def _load_policy(path: str | Path = "configs/independent_security_review_policy.json") -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("independent security review policy must be a JSON object")
    return payload


def _git_head(root: Path = ROOT) -> str:
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
    ).strip()
    if SHA40.fullmatch(head) is None:
        raise SystemExit("git HEAD is not a canonical 40-character SHA")
    return head


def build_independent_review_handoff(
    *,
    root: str | Path = ROOT,
    repository: str = "bilgekayali/structurax",
    commit_sha: str | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = Path(root)
    active_policy = policy or _load_policy()
    digest = compute_release_surface_digest(base)
    head = commit_sha or _git_head(base)
    if SHA40.fullmatch(head) is None:
        raise SystemExit("commit_sha must be a canonical 40-character SHA")

    review_path = active_policy["evidence_envelope_path"]
    required_schema = active_policy["required_schema_version"]
    return {
        "policy_version": active_policy["policy_version"],
        "repository": repository,
        "source_commit_sha": head,
        "release_surface_sha256": digest,
        "release_surface_digest_algorithm": active_policy["release_surface_digest_algorithm"],
        "required_schema_version": required_schema,
        "evidence_schema_path": active_policy["schema_path"],
        "expected_review_envelope_path": review_path,
        "required_review_areas": active_policy["required_review_areas"],
        "acceptance": {
            "review_outcome": "passed",
            "max_open_critical_findings": active_policy["max_open_critical_findings"],
            "max_open_high_findings": active_policy["max_open_high_findings"],
            "max_open_release_blocking_findings": active_policy[
                "max_open_release_blocking_findings"
            ],
            "risk_acceptance_required": active_policy["risk_acceptance_required"],
            "raw_secret_material_present": active_policy["allow_raw_secret_material"],
        },
        "external_report": {
            "required": active_policy["external_report_required"] is True,
            "must_remain_outside_repository": (
                active_policy["external_report_must_remain_outside_repository"] is True
            ),
            "sha256_must_match_envelope": True,
        },
        "reviewer_authority": {
            "reviewer_must_be_independent": active_policy["reviewer_must_be_independent"] is True,
            "repository_owner_or_implementation_author_may_self_attest": False,
            "ci_may_create_review_evidence": False,
        },
        "verification_command_template": (
            "python scripts/verify_independent_review.py "
            f"--review {review_path} "
            "--evidence-file /secure/path/to/external-review-report "
            f"--expected-repository-sha256 {digest} "
            f"--required-schema-version {required_schema}"
        ),
        "automatic_gate_mutation_allowed": False,
        "production_readiness_claimed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default="bilgekayali/structurax")
    parser.add_argument("--commit-sha")
    parser.add_argument("--policy", default="configs/independent_security_review_policy.json")
    parser.add_argument("--output")
    args = parser.parse_args()
    policy = _load_policy(args.policy)
    manifest = build_independent_review_handoff(
        repository=args.repository,
        commit_sha=args.commit_sha,
        policy=policy,
    )
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
