"""Verify the frozen StructuraX v1.0 release-candidate public API surface."""
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

import structurax


ROOT = Path(__file__).resolve().parents[1]


def load_contract(path: str | Path = "configs/stable_api_contract.json") -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return json.loads(candidate.read_text(encoding="utf-8"))


def _surface_digest(exports: list[str]) -> str:
    payload = "\n".join(sorted(exports)) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _symbol_kind(value: object) -> str:
    if inspect.isclass(value):
        return "class"
    if inspect.isfunction(value):
        return "function"
    return type(value).__name__


def verify_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    active = contract or load_contract()
    if active.get("status") != "frozen-release-candidate":
        raise SystemExit("stable API contract is not frozen for the release candidate")
    if active.get("allow_additive_exports") is not False:
        raise SystemExit("stable API contract must fail closed on additive exports")

    expected = list(active["exact_public_exports"])
    observed = list(structurax.__all__)
    expected_set = set(expected)
    observed_set = set(observed)
    missing = sorted(expected_set - observed_set)
    unexpected = sorted(observed_set - expected_set)
    if missing or unexpected or len(expected) != len(expected_set) or len(observed) != len(observed_set):
        raise SystemExit(
            "stable API compatibility violation; "
            f"missing={missing}, unexpected={unexpected}, duplicate_contract_entries={len(expected) != len(expected_set)}, "
            f"duplicate_runtime_entries={len(observed) != len(observed_set)}"
        )

    digest = _surface_digest(observed)
    if digest != active["public_surface_sha256"]:
        raise SystemExit(
            "stable API surface digest mismatch; expected "
            f"{active['public_surface_sha256']}, observed {digest}"
        )

    module_mismatches: dict[str, dict[str, str]] = {}
    kind_mismatches: dict[str, dict[str, str]] = {}
    for name in expected:
        value = getattr(structurax, name)
        expected_module = active["public_symbol_modules"][name]
        observed_module = getattr(value, "__module__", "")
        if observed_module != expected_module:
            module_mismatches[name] = {"expected": expected_module, "observed": observed_module}
        expected_kind = active["public_symbol_kinds"][name]
        observed_kind = _symbol_kind(value)
        if observed_kind != expected_kind:
            kind_mismatches[name] = {"expected": expected_kind, "observed": observed_kind}

    if module_mismatches or kind_mismatches:
        raise SystemExit(
            "stable API symbol identity mismatch; "
            f"modules={module_mismatches}, kinds={kind_mismatches}"
        )

    return {
        "contract_version": active["contract_version"],
        "status": active["status"],
        "baseline_package_version": active["baseline_package_version"],
        "intended_release_version": active["intended_release_version"],
        "runtime_package_version": structurax.__version__,
        "public_surface_sha256": digest,
        "public_exports": sorted(observed),
        "compatible": True,
        "final_v1_freeze": True,
        "production_readiness_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify_contract(), indent=2, sort_keys=True))
