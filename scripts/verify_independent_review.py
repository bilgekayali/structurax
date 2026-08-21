"""Verify an independent security-review evidence envelope against the exact repository digest."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts.repository_review_digest import compute_repository_digest
except ModuleNotFoundError:  # direct script execution
    from repository_review_digest import compute_repository_digest


ROOT = Path(__file__).resolve().parents[1]
HEX64 = re.compile(r"^[a-f0-9]{64}$")


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("completed_at must include timezone information")
    return parsed


def verify_independent_review(
    review_path: str | Path,
    expected_repository_sha256: str | None = None,
) -> dict[str, Any]:
    path = Path(review_path)
    if not path.is_absolute():
        path = ROOT / path
    review = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "reviewed_repository_sha256",
        "reviewer_id",
        "reviewer_independence_confirmed",
        "review_evidence_sha256",
        "completed_at",
    }
    if set(review) != required:
        raise SystemExit(f"independent review keys must be exact: {sorted(required)}")
    if review["schema_version"] != "0.4.0":
        raise SystemExit("independent review must use the frozen evidence-envelope schema version 0.4.0")
    if review["reviewer_independence_confirmed"] is not True:
        raise SystemExit("reviewer independence must be explicitly confirmed")
    reviewer = review["reviewer_id"]
    if not isinstance(reviewer, str) or not (3 <= len(reviewer) <= 160):
        raise SystemExit("reviewer_id length is invalid")
    evidence_digest = review["review_evidence_sha256"]
    if not isinstance(evidence_digest, str) or not HEX64.fullmatch(evidence_digest):
        raise SystemExit("review evidence digest must be lowercase sha256")
    if evidence_digest == "0" * 64:
        raise SystemExit("review evidence digest cannot be an all-zero placeholder")
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
        "reviewed_repository_sha256": expected,
        "reviewer_id": reviewer,
        "review_evidence_sha256": evidence_digest,
        "independent_security_review_verified": True,
        "formal_release_gate_updated": False,
        "production_readiness_claimed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", default="security-review/v1.0-review.json")
    parser.add_argument("--expected-repository-sha256")
    args = parser.parse_args()
    print(
        json.dumps(
            verify_independent_review(args.review, args.expected_repository_sha256),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
