"""Build the exact GitHub branch-protection payload from StructuraX governance policy."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.assess_repository_governance import load_policy
except ModuleNotFoundError:  # direct script execution
    from assess_repository_governance import load_policy


def build_branch_protection_payload(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    active = policy or load_policy()
    manual = active["manual_controls_expected"]
    required = active["required_status_checks"]
    if not isinstance(required, list) or not required or len(required) != len(set(required)):
        raise SystemExit("required_status_checks must be a non-empty unique list")
    if manual["pull_request_required"] is not True:
        raise SystemExit("stable-release governance requires pull_request_required=true")
    if not 1 <= int(manual["required_approving_reviews"]) <= 6:
        raise SystemExit("required_approving_reviews must be between 1 and 6")

    return {
        "required_status_checks": {
            "strict": manual["strict_status_checks"] is True,
            "contexts": list(required),
        },
        "enforce_admins": manual["enforce_admins"] is True,
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": manual["dismiss_stale_reviews"] is True,
            "require_code_owner_reviews": manual["require_code_owner_reviews"] is True,
            "required_approving_review_count": int(manual["required_approving_reviews"]),
            "require_last_push_approval": manual["require_last_push_approval"] is True,
        },
        "restrictions": None,
        "required_linear_history": manual["required_linear_history"] is True,
        "allow_force_pushes": manual["force_pushes_allowed"] is True,
        "allow_deletions": manual["branch_deletion_allowed"] is True,
        "block_creations": False,
        "required_conversation_resolution": manual["conversation_resolution_required"] is True,
        "lock_branch": False,
        "allow_fork_syncing": False,
    }


def branch_protection_endpoint(repository: str, branch: str) -> str:
    if repository.count("/") != 1 or any(not part for part in repository.split("/")):
        raise SystemExit("repository must be owner/name")
    if not branch or "*" in branch:
        raise SystemExit("branch must be an exact branch name")
    return f"https://api.github.com/repos/{repository}/branches/{branch}/protection"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository")
    parser.add_argument("--branch")
    parser.add_argument("--output")
    args = parser.parse_args()

    policy = load_policy()
    branch = args.branch or policy["branch"]
    payload = {
        "api_version": "2026-03-10",
        "method": "PUT",
        "endpoint": branch_protection_endpoint(args.repository, branch) if args.repository else None,
        "branch": branch,
        "payload": build_branch_protection_payload(policy),
        "production_readiness_claimed": False,
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
