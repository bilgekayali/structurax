from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.repository_review_digest import EXCLUDED
from scripts.verify_production_evidence import canonical_statement, load_policy, verify_production_evidence


ROOT = Path(__file__).resolve().parents[1]


def _statement(repository_digest: str = "a" * 64) -> dict[str, object]:
    control_ids = list(load_policy()["required_controls"])
    controls = []
    for index, control_id in enumerate(control_ids, start=1):
        controls.append(
            {
                "control_id": control_id,
                "evidence_kind": load_policy()["required_controls"][control_id],
                "result": "passed",
                "validator_id": f"validator:ops-{index}",
                "evidence_sha256": hashlib.sha256(control_id.encode("utf-8")).hexdigest(),
                "completed_at": "2026-08-21T14:00:00+00:00",
                "negative_path_tested": True,
            }
        )
    return {
        "reviewed_repository_sha256": repository_digest,
        "environment_id": "prod:opaque-env-01",
        "completed_at": "2026-08-21T14:30:00+00:00",
        "production_environment_confirmed": True,
        "raw_endpoint_metadata_present": False,
        "raw_secret_material_present": False,
        "controls": controls,
    }


def _signed_envelope(statement: dict[str, object], key: Ed25519PrivateKey) -> dict[str, object]:
    public = key.public_key()
    raw = public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    signature = key.sign(canonical_statement(statement))
    return {
        "schema_version": "1.0.0",
        "statement": statement,
        "signature": {
            "algorithm": "Ed25519",
            "key_id": hashlib.sha256(raw).hexdigest(),
            "signature_b64": base64.b64encode(signature).decode("ascii"),
        },
    }


def _write_key(path: Path, key: Ed25519PrivateKey) -> None:
    path.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


class V10ProductionEvidenceHarnessTests(unittest.TestCase):
    def test_missing_production_evidence_remains_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = verify_production_evidence(
                Path(tmp) / "missing.json",
                policy=load_policy(),
                repository_digest="a" * 64,
            )
        self.assertFalse(result["available"])
        self.assertFalse(result["contract_verified"])
        self.assertFalse(result["formal_gate_mutation_authorized"])
        self.assertEqual(result["blockers"], ["production_evidence_missing"])
        self.assertTrue(all(value is False for value in result["candidate_checks"].values()))

    def test_valid_signed_production_evidence_is_digest_bound_but_does_not_auto_promote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = Ed25519PrivateKey.generate()
            statement = _statement()
            evidence = root / "evidence.json"
            trusted_key = root / "trusted.pem"
            evidence.write_text(json.dumps(_signed_envelope(statement, key)), encoding="utf-8")
            _write_key(trusted_key, key)
            result = verify_production_evidence(
                evidence,
                trusted_key,
                policy=load_policy(),
                repository_digest="a" * 64,
            )
        self.assertTrue(result["contract_verified"])
        self.assertTrue(result["cryptographic_signature_verified"])
        self.assertTrue(result["repository_digest_verified"])
        self.assertTrue(all(result["candidate_checks"].values()))
        self.assertFalse(result["formal_gate_mutation_authorized"])
        self.assertFalse(result["production_readiness_claimed"])

    def test_production_evidence_for_other_repository_digest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = Ed25519PrivateKey.generate()
            evidence = root / "evidence.json"
            trusted_key = root / "trusted.pem"
            evidence.write_text(json.dumps(_signed_envelope(_statement("b" * 64), key)), encoding="utf-8")
            _write_key(trusted_key, key)
            with self.assertRaises(SystemExit):
                verify_production_evidence(
                    evidence,
                    trusted_key,
                    policy=load_policy(),
                    repository_digest="a" * 64,
                )

    def test_tampering_after_signature_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = Ed25519PrivateKey.generate()
            envelope = _signed_envelope(_statement(), key)
            envelope["statement"]["environment_id"] = "prod:opaque-env-02"  # type: ignore[index]
            evidence = root / "evidence.json"
            trusted_key = root / "trusted.pem"
            evidence.write_text(json.dumps(envelope), encoding="utf-8")
            _write_key(trusted_key, key)
            with self.assertRaises(SystemExit):
                verify_production_evidence(
                    evidence,
                    trusted_key,
                    policy=load_policy(),
                    repository_digest="a" * 64,
                )

    def test_raw_secret_or_endpoint_metadata_is_rejected(self) -> None:
        for field in ("raw_secret_material_present", "raw_endpoint_metadata_present"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                key = Ed25519PrivateKey.generate()
                statement = _statement()
                statement[field] = True
                evidence = root / "evidence.json"
                trusted_key = root / "trusted.pem"
                evidence.write_text(json.dumps(_signed_envelope(statement, key)), encoding="utf-8")
                _write_key(trusted_key, key)
                with self.assertRaises(SystemExit):
                    verify_production_evidence(
                        evidence,
                        trusted_key,
                        policy=load_policy(),
                        repository_digest="a" * 64,
                    )

    def test_nonproduction_markers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = Ed25519PrivateKey.generate()
            statement = _statement()
            statement["environment_id"] = "synthetic-env-01"
            evidence = root / "evidence.json"
            trusted_key = root / "trusted.pem"
            evidence.write_text(json.dumps(_signed_envelope(statement, key)), encoding="utf-8")
            _write_key(trusted_key, key)
            with self.assertRaises(SystemExit):
                verify_production_evidence(
                    evidence,
                    trusted_key,
                    policy=load_policy(),
                    repository_digest="a" * 64,
                )

    def test_each_control_requires_distinct_evidence_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = Ed25519PrivateKey.generate()
            statement = _statement()
            controls = statement["controls"]  # type: ignore[assignment]
            controls[1]["evidence_sha256"] = controls[0]["evidence_sha256"]  # type: ignore[index]
            evidence = root / "evidence.json"
            trusted_key = root / "trusted.pem"
            evidence.write_text(json.dumps(_signed_envelope(statement, key)), encoding="utf-8")
            _write_key(trusted_key, key)
            with self.assertRaises(SystemExit):
                verify_production_evidence(
                    evidence,
                    trusted_key,
                    policy=load_policy(),
                    repository_digest="a" * 64,
                )

    def test_production_evidence_file_is_excluded_from_repository_digest(self) -> None:
        self.assertIn("production-evidence/v1.0-controls.json", EXCLUDED)

    def test_governance_policy_requires_production_evidence_harness(self) -> None:
        policy = json.loads((ROOT / "configs/repository_governance_policy.json").read_text(encoding="utf-8"))
        self.assertIn("production-evidence-harness", policy["required_status_checks"])

    def test_formal_release_gate_remains_closed_for_production_controls(self) -> None:
        gate = json.loads((ROOT / "configs/release_candidate_gate.json").read_text(encoding="utf-8"))
        for control in load_policy()["required_controls"]:
            self.assertFalse(gate["checks"][control])
        self.assertFalse(gate["formal_release_eligible"])


if __name__ == "__main__":
    unittest.main()
