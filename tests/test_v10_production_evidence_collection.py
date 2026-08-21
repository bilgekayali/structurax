from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.assemble_production_evidence import assemble_production_statement, load_collection_policy
from scripts.attach_production_evidence_signature import attach_signature
from scripts.build_production_signing_payload import build_signing_payload
from scripts.release_surface_digest import compute_release_surface_digest
from scripts.verify_production_evidence import load_policy, verify_production_evidence

ROOT = Path(__file__).resolve().parents[1]


def _receipt(control_id: str, index: int, digest: str, *, environment_id: str = "prod:opaque-env-01") -> dict[str, object]:
    final_policy = load_policy()
    return {
        "schema_version": "1.0.0",
        "release_surface_sha256": digest,
        "environment_id": environment_id,
        "control_id": control_id,
        "evidence_kind": final_policy["required_controls"][control_id],
        "result": "passed",
        "validator_id": f"validator:ops-{index}",
        "evidence_artifact_id": f"artifact:prod-{index}",
        "evidence_sha256": hashlib.sha256(f"external-evidence-{index}".encode("utf-8")).hexdigest(),
        "completed_at": f"2026-08-21T15:0{index}:00+00:00",
        "negative_path_tested": True,
        "raw_endpoint_metadata_present": False,
        "raw_secret_material_present": False,
    }


def _write_receipts(root: Path, digest: str) -> list[Path]:
    paths = []
    for index, control_id in enumerate(load_collection_policy()["required_control_ids"], start=1):
        path = root / f"receipt-{index}.json"
        path.write_text(json.dumps(_receipt(control_id, index, digest)), encoding="utf-8")
        paths.append(path)
    return paths


class V10ProductionEvidenceCollectionTests(unittest.TestCase):
    def test_exact_receipt_set_assembles_unsigned_statement(self) -> None:
        digest = compute_release_surface_digest(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            paths = _write_receipts(Path(tmp), digest)
            statement = assemble_production_statement(paths, repository_digest=digest)
        self.assertEqual(statement["reviewed_repository_sha256"], digest)
        self.assertEqual(statement["environment_id"], "prod:opaque-env-01")
        self.assertEqual(len(statement["controls"]), 4)
        self.assertTrue(statement["production_environment_confirmed"])
        self.assertFalse(statement["raw_endpoint_metadata_present"])
        self.assertFalse(statement["raw_secret_material_present"])

    def test_missing_control_receipt_is_rejected(self) -> None:
        digest = compute_release_surface_digest(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            paths = _write_receipts(Path(tmp), digest)
            with self.assertRaises(SystemExit):
                assemble_production_statement(paths[:-1], repository_digest=digest)

    def test_mixed_environment_receipts_are_rejected(self) -> None:
        digest = compute_release_surface_digest(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _write_receipts(root, digest)
            payload = json.loads(paths[-1].read_text(encoding="utf-8"))
            payload["environment_id"] = "prod:opaque-env-02"
            paths[-1].write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(SystemExit):
                assemble_production_statement(paths, repository_digest=digest)

    def test_duplicate_external_evidence_digest_is_rejected(self) -> None:
        digest = compute_release_surface_digest(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _write_receipts(root, digest)
            first = json.loads(paths[0].read_text(encoding="utf-8"))
            second = json.loads(paths[1].read_text(encoding="utf-8"))
            second["evidence_sha256"] = first["evidence_sha256"]
            paths[1].write_text(json.dumps(second), encoding="utf-8")
            with self.assertRaises(SystemExit):
                assemble_production_statement(paths, repository_digest=digest)

    def test_raw_secret_or_endpoint_flags_are_rejected(self) -> None:
        digest = compute_release_surface_digest(ROOT)
        for field in ("raw_secret_material_present", "raw_endpoint_metadata_present"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                paths = _write_receipts(root, digest)
                payload = json.loads(paths[0].read_text(encoding="utf-8"))
                payload[field] = True
                paths[0].write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(SystemExit):
                    assemble_production_statement(paths, repository_digest=digest)

    def test_receipt_for_other_release_surface_is_rejected(self) -> None:
        digest = compute_release_surface_digest(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            paths = _write_receipts(Path(tmp), "a" * 64)
            with self.assertRaises(SystemExit):
                assemble_production_statement(paths, repository_digest=digest)

    def test_signing_payload_is_deterministic_and_private_key_free(self) -> None:
        digest = compute_release_surface_digest(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement = root / "statement.json"
            statement.write_text(json.dumps(assemble_production_statement(_write_receipts(root, digest), repository_digest=digest)), encoding="utf-8")
            first = root / "first.payload"
            second = root / "second.payload"
            one = build_signing_payload(statement, first)
            two = build_signing_payload(statement, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(one["payload_sha256"], two["payload_sha256"])
            self.assertFalse(one["private_key_handled"])

    def test_external_signature_attachment_round_trip(self) -> None:
        digest = compute_release_surface_digest(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement = root / "statement.json"
            statement.write_text(json.dumps(assemble_production_statement(_write_receipts(root, digest), repository_digest=digest)), encoding="utf-8")
            payload_path = root / "signing.payload"
            build_signing_payload(statement, payload_path)
            private_key = Ed25519PrivateKey.generate()
            signature_path = root / "signature.txt"
            signature_path.write_text(base64.b64encode(private_key.sign(payload_path.read_bytes())).decode("ascii"), encoding="utf-8")
            public_key_path = root / "validator.pub.pem"
            public_key_path.write_bytes(private_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
            output = root / "envelope.json"
            result = attach_signature(statement, signature_path, public_key_path, output)
            verified = verify_production_evidence(output, public_key_path, repository_digest=digest)
        self.assertTrue(result["contract_verified"])
        self.assertFalse(result["private_key_handled"])
        self.assertFalse(result["trusted_key_established_by_tool"])
        self.assertTrue(verified["contract_verified"])
        self.assertTrue(all(verified["candidate_checks"].values()))
        self.assertFalse(verified["formal_gate_mutation_authorized"])

    def test_invalid_external_signature_is_rejected(self) -> None:
        digest = compute_release_surface_digest(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement = root / "statement.json"
            statement.write_text(json.dumps(assemble_production_statement(_write_receipts(root, digest), repository_digest=digest)), encoding="utf-8")
            private_key = Ed25519PrivateKey.generate()
            signature_path = root / "signature.txt"
            signature_path.write_text(base64.b64encode(b"not-a-valid-ed25519-signature").decode("ascii"), encoding="utf-8")
            public_key_path = root / "validator.pub.pem"
            public_key_path.write_bytes(private_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
            with self.assertRaises(SystemExit):
                attach_signature(statement, signature_path, public_key_path, root / "envelope.json")

    def test_collection_policy_and_workflow_remain_fail_closed(self) -> None:
        policy = load_collection_policy()
        self.assertFalse(policy["private_key_handling_allowed"])
        self.assertFalse(policy["automatic_signature_allowed"])
        self.assertFalse(policy["automatic_gate_mutation_allowed"])
        governance = json.loads((ROOT / "configs/repository_governance_policy.json").read_text(encoding="utf-8"))
        self.assertIn("production-evidence-collection", governance["required_status_checks"])
        workflow = (ROOT / ".github/workflows/production-evidence-collection.yml").read_text(encoding="utf-8")
        self.assertIn("production-evidence-collection", workflow)
        self.assertIn("private_key_handling_allowed", workflow)
        self.assertNotIn("BEGIN PRIVATE KEY", workflow)

    def test_formal_release_gate_remains_closed(self) -> None:
        gate = json.loads((ROOT / "configs/release_candidate_gate.json").read_text(encoding="utf-8"))
        self.assertFalse(gate["formal_release_eligible"])
        for control in load_policy()["required_controls"]:
            self.assertFalse(gate["checks"][control])


if __name__ == "__main__":
    unittest.main()
