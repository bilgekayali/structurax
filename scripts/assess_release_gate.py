"""Fail-closed formal-release gate for StructuraX v1.0 preparation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structurax


ROOT = Path(__file__).resolve().parents[1]


def load_gate(path: str | Path = "configs/release_candidate_gate.json") -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return json.loads(candidate.read_text(encoding="utf-8"))


def assess_release_gate(gate: dict[str, Any] | None = None) -> dict[str, Any]:
    active = gate or load_gate()
    checks = active["checks"]
    blockers = sorted(name for name, passed in checks.items() if passed is not True)
    required_version = active["required_release_version"]
    version_match = structurax.__version__ == required_version
    if not version_match:
        blockers.append("package_version_not_1_0_0")

    eligible = not blockers
    declared = active["formal_release_eligible"] is True
    if declared and not eligible:
        raise SystemExit(
            "formal release gate is inconsistent: formal_release_eligible=true while blockers remain: "
            + ", ".join(blockers)
        )
    if eligible and not declared:
        raise SystemExit(
            "formal release gate requires an explicit human-reviewed promotion to formal_release_eligible=true"
        )

    return {
        "gate_version": active["gate_version"],
        "package_version": structurax.__version__,
        "required_release_version": required_version,
        "blockers": blockers,
        "eligible": False,
        "formal_release_declared": declared,
        "production_readiness_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(assess_release_gate(), indent=2, sort_keys=True))
