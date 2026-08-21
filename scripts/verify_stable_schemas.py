"""Verify the exact frozen StructuraX v1.0 release-candidate schema surface."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_contract(path: str | Path = "configs/stable_schema_contract.json") -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return json.loads(candidate.read_text(encoding="utf-8"))


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def verify_schema_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    active = contract or load_contract()
    if active.get("status") != "frozen-release-candidate":
        raise SystemExit("stable schema contract is not frozen for the release candidate")

    schema_files = sorted((ROOT / "schemas").glob("*.schema.json"))
    observed = {path.relative_to(ROOT).as_posix(): path for path in schema_files}
    expected_blobs = dict(active["schema_git_blobs"])
    expected_paths = set(expected_blobs)
    observed_paths = set(observed)

    missing = sorted(expected_paths - observed_paths)
    unexpected = sorted(observed_paths - expected_paths)
    if missing or unexpected:
        raise SystemExit(
            f"stable schema surface violation; missing={missing}, unexpected={unexpected}"
        )

    expected_count = int(active["exact_schema_count"])
    if len(schema_files) != expected_count or expected_count != len(expected_paths):
        raise SystemExit(
            "stable schema count violation; "
            f"contract={expected_count}, pinned={len(expected_paths)}, observed={len(schema_files)}"
        )

    content_mismatches: dict[str, dict[str, str]] = {}
    invalid: list[str] = []
    titles: set[str] = set()
    required_keys = tuple(active["required_top_level_keys"])
    for relative, path in observed.items():
        observed_blob = _git_blob_sha1(path)
        if observed_blob != expected_blobs[relative]:
            content_mismatches[relative] = {
                "expected": expected_blobs[relative],
                "observed": observed_blob,
            }
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

    if content_mismatches:
        raise SystemExit(f"stable schema content mismatch: {content_mismatches}")
    if invalid:
        raise SystemExit(f"stable schema contract violation; invalid schemas: {sorted(invalid)}")

    return {
        "contract_version": active["contract_version"],
        "status": active["status"],
        "schema_count": len(schema_files),
        "pinned_schema_blobs": dict(sorted(expected_blobs.items())),
        "compatible": True,
        "final_v1_freeze": True,
        "production_readiness_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify_schema_contract(), indent=2, sort_keys=True))
