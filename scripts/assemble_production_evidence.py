"""Assemble secret-free production-control receipts into an unsigned v1.0 evidence statement."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.release_surface_digest import compute_release_surface_digest  # noqa: E402
from scripts.verify_production_evidence import load_policy  # noqa: E402

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,159}$")
_DISALLOWED_MARKERS = ("synthetic", "demo", "test", "reference", "example")
_RECEIPT_KEYS = {
    "schema_version",
    "release_surface_sha256",
    "environment_id",
    "control_id",
    "evidence_kind",
    "result",
    "validator_id",
    "evidence_artifact_id",
    "evidence_sha256",
    "completed_at",
    "negative_path_tested",
    "raw_endpoint_metadata_present",
    "raw_secret_material_present",
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return payload


def load_collection_policy(path: str | Path = "configs/production_evidence_collection_policy.json") -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return _load_json(candidate)


def _opaque(value: Any, label: str) -> str:
    if not isinstance(value, str) or _OPAQUE_ID.fullmatch(value) is None:
        raise SystemExit(f"{label} must be an opaque identifier")
    lowered = value.lower()
    if any(marker in lowered for marker in _DISALLOWED_MARKERS):
        raise SystemExit(f"{label} uses a non-production marker")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise SystemExit(f"{label} must be a lowercase SHA-256 hex digest")
    return value


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise SystemExit(f"{label} must be an RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"{label} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SystemExit(f"{label} must include a timezone offset")
    return parsed


def validate_receipt(
    receipt: dict[str, Any],
    *,
    expected_digest: str,
    required_controls: dict[str, str],
    collection_policy: dict[str, Any],
) -> tuple[str, str, str, str, datetime, dict[str, Any]]:
    if set(receipt) != _RECEIPT_KEYS:
        raise SystemExit("production control receipt keys mismatch")
    if receipt["schema_version"] != collection_policy["receipt_schema_version"]:
        raise SystemExit("unsupported production control receipt schema_version")
    digest = _sha256(receipt["release_surface_sha256"], "release_surface_sha256")
    if digest != expected_digest:
        raise SystemExit("production control receipt is bound to a different release surface")
    environment_id = _opaque(receipt["environment_id"], "environment_id")
    control_id = receipt["control_id"]
    if control_id not in required_controls:
        raise SystemExit(f"unexpected production control receipt: {control_id}")
    if receipt["evidence_kind"] != required_controls[control_id]:
        raise SystemExit(f"evidence_kind mismatch for {control_id}")
    if receipt["result"] != "passed":
        raise SystemExit(f"production control did not pass: {control_id}")
    if collection_policy["require_negative_path_tested"] and receipt["negative_path_tested"] is not True:
        raise SystemExit(f"negative path was not tested for {control_id}")
    if receipt["raw_endpoint_metadata_present"] is not False:
        raise SystemExit("raw endpoint metadata is forbidden in production control receipts")
    if receipt["raw_secret_material_present"] is not False:
        raise SystemExit("raw secret material is forbidden in production control receipts")
    validator_id = _opaque(receipt["validator_id"], f"{control_id}.validator_id")
    artifact_id = _opaque(receipt["evidence_artifact_id"], f"{control_id}.evidence_artifact_id")
    evidence_sha = _sha256(receipt["evidence_sha256"], f"{control_id}.evidence_sha256")
    completed = _timestamp(receipt["completed_at"], f"{control_id}.completed_at")
    final_control = {
        "control_id": control_id,
        "evidence_kind": receipt["evidence_kind"],
        "result": "passed",
        "validator_id": validator_id,
        "evidence_sha256": evidence_sha,
        "completed_at": receipt["completed_at"],
        "negative_path_tested": True,
    }
    return environment_id, control_id, artifact_id, evidence_sha, completed, final_control


def assemble_production_statement(
    receipt_paths: list[str | Path],
    *,
    repository_digest: str | None = None,
    final_policy: dict[str, Any] | None = None,
    collection_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_final = final_policy or load_policy()
    active_collection = collection_policy or load_collection_policy()
    required_controls = active_final["required_controls"]
    expected_ids = list(active_collection["required_control_ids"])
    if set(expected_ids) != set(required_controls):
        raise SystemExit("collection policy and final evidence policy disagree on required controls")
    if len(receipt_paths) != len(required_controls):
        raise SystemExit("exactly one receipt for every required production control is required")
    digest = repository_digest or compute_release_surface_digest(ROOT)

    environments: set[str] = set()
    seen_controls: set[str] = set()
    artifact_ids: set[str] = set()
    evidence_digests: set[str] = set()
    completed: list[datetime] = []
    controls: list[dict[str, Any]] = []
    for raw_path in receipt_paths:
        path = Path(raw_path)
        receipt = _load_json(path)
        environment_id, control_id, artifact_id, evidence_sha, finished, final_control = validate_receipt(
            receipt,
            expected_digest=digest,
            required_controls=required_controls,
            collection_policy=active_collection,
        )
        if control_id in seen_controls:
            raise SystemExit(f"duplicate production control receipt: {control_id}")
        seen_controls.add(control_id)
        if active_collection["require_distinct_external_evidence"]:
            if artifact_id in artifact_ids:
                raise SystemExit("each production control must bind a distinct external evidence artifact id")
            if evidence_sha in evidence_digests:
                raise SystemExit("each production control must bind a distinct external evidence digest")
        artifact_ids.add(artifact_id)
        evidence_digests.add(evidence_sha)
        environments.add(environment_id)
        completed.append(finished)
        controls.append(final_control)

    if seen_controls != set(required_controls):
        raise SystemExit("production control receipt set is incomplete")
    if len(environments) != 1:
        raise SystemExit("all production control receipts must refer to the same environment_id")

    order = {control_id: index for index, control_id in enumerate(expected_ids)}
    controls.sort(key=lambda item: order[item["control_id"]])
    statement_completed = max(completed).isoformat()
    return {
        "reviewed_repository_sha256": digest,
        "environment_id": next(iter(environments)),
        "completed_at": statement_completed,
        "production_environment_confirmed": True,
        "raw_endpoint_metadata_present": False,
        "raw_secret_material_present": False,
        "controls": controls,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    statement = assemble_production_statement(args.receipt)
    Path(args.output).write_text(json.dumps(statement, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": args.output,
        "release_surface_sha256": statement["reviewed_repository_sha256"],
        "control_count": len(statement["controls"]),
        "signed": False,
        "private_key_handled": False,
        "formal_gate_mutation_authorized": False,
        "production_readiness_claimed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
