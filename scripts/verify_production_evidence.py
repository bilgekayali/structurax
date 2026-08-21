"""Verify signed, digest-bound production-control evidence without auto-promoting v1.0."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.repository_review_digest import compute_repository_digest  # noqa: E402

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,159}$")
_DISALLOWED_PRODUCTION_MARKERS = ("synthetic", "demo", "test", "reference", "example")


def canonical_statement(statement: dict[str, Any]) -> bytes:
    return json.dumps(statement, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return payload


def load_policy(path: str | Path = "configs/production_evidence_policy.json") -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return _load_json(candidate)


def _require_exact_keys(payload: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise SystemExit(f"{label} keys mismatch; missing={missing}; extra={extra}")


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise SystemExit(f"{label} must be a lowercase SHA-256 hex digest")
    return value


def _require_opaque_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or _OPAQUE_ID.fullmatch(value) is None:
        raise SystemExit(f"{label} must be an opaque identifier")
    lowered = value.lower()
    if any(marker in lowered for marker in _DISALLOWED_PRODUCTION_MARKERS):
        raise SystemExit(f"{label} uses a non-production marker")
    return value


def _parse_timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise SystemExit(f"{label} must be an RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"{label} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SystemExit(f"{label} must include a timezone offset")
    return parsed


def _load_trusted_public_key(path: Path) -> tuple[Ed25519PublicKey, str]:
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise SystemExit("trusted production-evidence key must be Ed25519")
    raw = key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return key, hashlib.sha256(raw).hexdigest()


def missing_evidence_assessment(policy: dict[str, Any]) -> dict[str, Any]:
    checks = {name: False for name in sorted(policy["required_controls"])}
    return {
        "available": False,
        "contract_verified": False,
        "cryptographic_signature_verified": False,
        "repository_digest_verified": False,
        "candidate_checks": checks,
        "blockers": ["production_evidence_missing"],
        "formal_gate_mutation_authorized": False,
        "production_readiness_claimed": False,
    }


def verify_production_evidence(
    evidence_path: str | Path | None = None,
    trusted_public_key_path: str | Path | None = None,
    *,
    policy: dict[str, Any] | None = None,
    repository_digest: str | None = None,
) -> dict[str, Any]:
    active_policy = policy or load_policy()
    configured = Path(evidence_path or active_policy["evidence_path"])
    if not configured.is_absolute():
        configured = ROOT / configured
    if not configured.exists():
        return missing_evidence_assessment(active_policy)

    if trusted_public_key_path is None:
        raise SystemExit("signed production evidence exists but no trusted Ed25519 public key was supplied")
    key_path = Path(trusted_public_key_path)
    if not key_path.is_absolute():
        key_path = ROOT / key_path

    envelope = _load_json(configured)
    _require_exact_keys(envelope, {"schema_version", "statement", "signature"}, "production evidence envelope")
    if envelope["schema_version"] != "1.0.0":
        raise SystemExit("unsupported production evidence schema_version")

    statement = envelope["statement"]
    signature = envelope["signature"]
    if not isinstance(statement, dict) or not isinstance(signature, dict):
        raise SystemExit("statement and signature must be objects")

    _require_exact_keys(
        statement,
        {
            "reviewed_repository_sha256",
            "environment_id",
            "completed_at",
            "production_environment_confirmed",
            "raw_endpoint_metadata_present",
            "raw_secret_material_present",
            "controls",
        },
        "production evidence statement",
    )
    if statement["production_environment_confirmed"] is not True:
        raise SystemExit("production_environment_confirmed must be true")
    if statement["raw_endpoint_metadata_present"] is not False:
        raise SystemExit("raw endpoint metadata is forbidden in committed production evidence")
    if statement["raw_secret_material_present"] is not False:
        raise SystemExit("raw secret material is forbidden in committed production evidence")

    expected_repository_digest = repository_digest or compute_repository_digest(ROOT)
    reviewed_digest = _require_sha256(statement["reviewed_repository_sha256"], "reviewed_repository_sha256")
    if reviewed_digest != expected_repository_digest:
        raise SystemExit(
            "production evidence is bound to a different repository digest: "
            f"expected={expected_repository_digest}; actual={reviewed_digest}"
        )

    _require_opaque_id(statement["environment_id"], "environment_id")
    statement_completed = _parse_timestamp(statement["completed_at"], "statement.completed_at")

    controls = statement["controls"]
    if not isinstance(controls, list):
        raise SystemExit("controls must be an array")
    required_controls = active_policy["required_controls"]
    if not isinstance(required_controls, dict) or not required_controls:
        raise SystemExit("production evidence policy required_controls is invalid")
    if len(controls) != len(required_controls):
        raise SystemExit("production evidence must contain exactly the required control set")

    seen: set[str] = set()
    evidence_digests: set[str] = set()
    control_completed: list[datetime] = []
    for index, control in enumerate(controls):
        if not isinstance(control, dict):
            raise SystemExit(f"controls[{index}] must be an object")
        _require_exact_keys(
            control,
            {
                "control_id",
                "evidence_kind",
                "result",
                "validator_id",
                "evidence_sha256",
                "completed_at",
                "negative_path_tested",
            },
            f"controls[{index}]",
        )
        control_id = control["control_id"]
        if control_id not in required_controls:
            raise SystemExit(f"unexpected production control: {control_id}")
        if control_id in seen:
            raise SystemExit(f"duplicate production control: {control_id}")
        seen.add(control_id)
        if control["evidence_kind"] != required_controls[control_id]:
            raise SystemExit(f"evidence_kind mismatch for {control_id}")
        if control["result"] != "passed":
            raise SystemExit(f"production control did not pass: {control_id}")
        if active_policy.get("require_negative_path_tested", True) and control["negative_path_tested"] is not True:
            raise SystemExit(f"negative path was not tested for {control_id}")
        _require_opaque_id(control["validator_id"], f"{control_id}.validator_id")
        evidence_sha = _require_sha256(control["evidence_sha256"], f"{control_id}.evidence_sha256")
        if evidence_sha in evidence_digests:
            raise SystemExit("each production control must bind a distinct evidence artifact digest")
        evidence_digests.add(evidence_sha)
        control_completed.append(_parse_timestamp(control["completed_at"], f"{control_id}.completed_at"))

    if seen != set(required_controls):
        raise SystemExit("production evidence control set is incomplete")
    if any(timestamp > statement_completed for timestamp in control_completed):
        raise SystemExit("statement.completed_at cannot precede a control validation timestamp")

    _require_exact_keys(signature, {"algorithm", "key_id", "signature_b64"}, "production evidence signature")
    if signature["algorithm"] != active_policy["signature_algorithm"] or signature["algorithm"] != "Ed25519":
        raise SystemExit("production evidence signature algorithm must be Ed25519")
    trusted_key, trusted_key_id = _load_trusted_public_key(key_path)
    supplied_key_id = _require_sha256(signature["key_id"], "signature.key_id")
    if supplied_key_id != trusted_key_id:
        raise SystemExit("production evidence key_id does not match the supplied trusted public key")
    try:
        signed = base64.b64decode(signature["signature_b64"], validate=True)
    except Exception as exc:  # binascii.Error is intentionally normalized to one fail-closed message.
        raise SystemExit("production evidence signature_b64 is invalid") from exc
    try:
        trusted_key.verify(signed, canonical_statement(statement))
    except InvalidSignature as exc:
        raise SystemExit("production evidence signature verification failed") from exc

    checks = {name: True for name in sorted(required_controls)}
    return {
        "available": True,
        "contract_verified": True,
        "cryptographic_signature_verified": True,
        "repository_digest_verified": True,
        "reviewed_repository_sha256": reviewed_digest,
        "environment_id": statement["environment_id"],
        "validator_key_id": trusted_key_id,
        "candidate_checks": checks,
        "blockers": [],
        "formal_gate_mutation_authorized": False,
        "production_readiness_claimed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence")
    parser.add_argument("--trusted-public-key")
    args = parser.parse_args()
    result = verify_production_evidence(args.evidence, args.trusted_public_key)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
