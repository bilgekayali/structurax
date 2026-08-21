"""Verify the committed schema surface for StructuraX v1.0 preparation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_contract(path: str | Path = "configs/stable_schema_contract.json") -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return json.loads(candidate.read_text(encoding="utf-8"))


def verify_schema_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    active = contract or load_contract()
    schema_files = sorted((ROOT / "schemas").glob("*.schema.json"))
    observed = {path.relative_to(ROOT).as_posix(): path for path in schema_files}

    required = set(active["required_schema_files"])
    missing = sorted(required - observed.keys())
    if missing:
        raise SystemExit(f"stable schema contract violation; missing files: {missing}")

    minimum = int(active["minimum_schema_count"])
    if len(schema_files) < minimum:
        raise SystemExit(
            f"stable schema contract violation; expected at least {minimum} schemas, found {len(schema_files)}"
        )

    required_keys = tuple(active["required_top_level_keys"])
    invalid: list[str] = []
    titles: set[str] = set()
    for relative, path in observed.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if any(key not in payload for key in required_keys):
            invalid.append(relative)
            continue
        if payload.get("type") != active["required_root_type"]:
            invalid.append(relative)
            continue
        title = payload.get("title")
        if not isinstance(title, str) or not title.strip() or title in titles:
            invalid.append(relative)
            continue
        titles.add(title)

    if invalid:
        raise SystemExit(f"stable schema contract violation; invalid schemas: {sorted(invalid)}")

    return {
        "contract_version": active["contract_version"],
        "schema_count": len(schema_files),
        "required_schema_files": sorted(required),
        "compatible": True,
        "final_v1_freeze": False,
        "production_readiness_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify_schema_contract(), indent=2, sort_keys=True))
