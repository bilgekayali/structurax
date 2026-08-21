"""Verify the draft stable public API baseline without widening authority claims."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structurax


def load_contract(path: str | Path = "configs/stable_api_contract.json") -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    active = contract or load_contract()
    required = set(active["required_public_exports"])
    observed = set(structurax.__all__)
    missing = sorted(required - observed)
    if missing:
        raise SystemExit(f"stable API compatibility violation; missing exports: {missing}")

    forbidden_prefixes = tuple(active["forbidden_public_export_prefixes"])
    forbidden = sorted(name for name in observed if name.startswith(forbidden_prefixes))
    if forbidden:
        raise SystemExit(f"forbidden public export names: {forbidden}")

    return {
        "contract_version": active["contract_version"],
        "package_version": structurax.__version__,
        "required_exports": sorted(required),
        "observed_exports": sorted(observed),
        "missing_exports": [],
        "compatible": True,
        "production_readiness_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify_contract(), indent=2, sort_keys=True))
