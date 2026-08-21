"""Assess observable repository governance without claiming unobservable controls."""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_policy(path: str | Path = "configs/repository_governance_policy.json") -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return json.loads(candidate.read_text(encoding="utf-8"))


def assess_snapshot(snapshot: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    active = policy or load_policy()
    protected = snapshot.get("protected") is True
    protection = snapshot.get("protection") or {}
    required = protection.get("required_status_checks") or {}
    contexts = sorted(set(required.get("contexts") or []))
    expected = sorted(set(active["required_status_checks"]))
    missing = sorted(set(expected) - set(contexts))

    blockers: list[str] = []
    if active["require_protected"] and not protected:
        blockers.append("main_branch_not_protected")
    if missing:
        blockers.append("required_status_checks_missing")

    return {
        "policy_version": active["policy_version"],
        "branch": active["branch"],
        "protected": protected,
        "observed_status_checks": contexts,
        "required_status_checks": expected,
        "missing_status_checks": missing,
        "observable_governance_eligible": not blockers,
        "blockers": blockers,
        "manual_controls_expected": active["manual_controls_expected"],
        "manual_controls_verified": False,
        "production_readiness_claimed": False,
    }


def fetch_branch_snapshot(repository: str, branch: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repository}/branches/{branch}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "structurax-governance-assessment",
        "X-GitHub-Api-Version": "2026-03-10",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository")
    parser.add_argument("--branch")
    parser.add_argument("--snapshot")
    parser.add_argument("--output")
    args = parser.parse_args()

    policy = load_policy()
    branch = args.branch or policy["branch"]
    if args.snapshot:
        snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    else:
        repository = args.repository or os.environ.get("GITHUB_REPOSITORY")
        if not repository:
            raise SystemExit("repository is required for live governance assessment")
        snapshot = fetch_branch_snapshot(repository, branch)

    result = assess_snapshot(snapshot, policy)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
