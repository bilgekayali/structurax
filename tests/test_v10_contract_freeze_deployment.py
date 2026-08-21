import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from scripts.verify_stable_api import load_contract as load_api_contract, verify_contract
from scripts.verify_stable_schemas import load_contract as load_schema_contract, verify_schema_contract
from structurax.deployment_reference import DeploymentReferenceProfile, build_observability_record
from structurax.stable_reference import ObservabilityEvent


ROOT = Path(__file__).resolve().parents[1]


class V10ContractFreezeDeploymentTests(unittest.TestCase):
    def test_api_contract_is_exact_frozen_release_candidate(self):
        report = verify_contract()
        self.assertTrue(report["compatible"])
        self.assertTrue(report["final_v1_freeze"])
        self.assertEqual(report["status"], "frozen-release-candidate")
        self.assertFalse(report["production_readiness_claimed"])

    def test_api_contract_rejects_additive_surface_drift(self):
        contract = copy.deepcopy(load_api_contract())
        contract["exact_public_exports"].append("future_unreviewed_export")
        with self.assertRaises(SystemExit):
            verify_contract(contract)

    def test_schema_contract_pins_exact_content_surface(self):
        report = verify_schema_contract()
        self.assertTrue(report["compatible"])
        self.assertTrue(report["final_v1_freeze"])
        self.assertEqual(report["schema_count"], 23)
        self.assertEqual(len(report["pinned_schema_blobs"]), 23)

    def test_schema_contract_rejects_content_identity_mismatch(self):
        contract = copy.deepcopy(load_schema_contract())
        path = sorted(contract["schema_git_blobs"])[0]
        contract["schema_git_blobs"][path] = "0" * 40
        with self.assertRaises(SystemExit):
            verify_schema_contract(contract)

    def test_deployment_profile_fails_closed_on_privileged_runtime(self):
        payload = json.loads((ROOT / "configs/deployment_reference.json").read_text(encoding="utf-8"))
        payload["privileged"] = True
        with self.assertRaises(ValidationError):
            DeploymentReferenceProfile.model_validate(payload)

    def test_deployment_profile_requires_external_secret_reference(self):
        payload = json.loads((ROOT / "configs/deployment_reference.json").read_text(encoding="utf-8"))
        payload["secrets_delivery"] = "environment-plaintext"
        with self.assertRaises(ValidationError):
            DeploymentReferenceProfile.model_validate(payload)

    def test_observability_record_is_metadata_only_and_deterministic(self):
        event = ObservabilityEvent(
            tenant_id="tenant-a",
            trace_id="trace-01",
            event_type="analysis",
            artifact_sha256="a" * 64,
            occurred_at=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
            outcome="review",
        )
        first = build_observability_record(event)
        second = build_observability_record(event)
        self.assertEqual(first, second)
        self.assertEqual(len(first["event_sha256"]), 64)
        self.assertFalse(first["raw_content_exported"])
        self.assertFalse(first["production_export_performed"])
        self.assertNotIn("raw_document_content", first["event"])
        self.assertNotIn("prompt_content", first["event"])
        self.assertNotIn("secret_content", first["event"])

    def test_formal_gate_only_marks_contract_freeze_complete(self):
        gate = json.loads((ROOT / "configs/release_candidate_gate.json").read_text(encoding="utf-8"))
        self.assertTrue(gate["checks"]["stable_api_contract_frozen"])
        self.assertTrue(gate["checks"]["stable_schema_contract_frozen"])
        self.assertFalse(gate["checks"]["observability_and_deployment_controls_validated"])
        self.assertFalse(gate["formal_release_eligible"])

    def test_governance_policy_requires_deployment_reference_check(self):
        policy = json.loads((ROOT / "configs/repository_governance_policy.json").read_text(encoding="utf-8"))
        self.assertIn("deployment-reference-validation", policy["required_status_checks"])


if __name__ == "__main__":
    unittest.main()
