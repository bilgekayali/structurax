import json
import unittest
from pathlib import Path

from scripts.assess_repository_governance import assess_snapshot, load_policy


ROOT = Path(__file__).resolve().parents[1]


class V10RepositoryGovernanceTests(unittest.TestCase):
    def test_unprotected_branch_fails_observable_governance(self):
        report = assess_snapshot({"protected": False, "protection": {}})
        self.assertFalse(report["observable_governance_eligible"])
        self.assertIn("main_branch_not_protected", report["blockers"])
        self.assertFalse(report["production_readiness_claimed"])

    def test_missing_required_checks_are_reported(self):
        policy = load_policy()
        snapshot = {
            "protected": True,
            "protection": {
                "required_status_checks": {
                    "contexts": ["CodeQL (python)"]
                }
            },
        }
        report = assess_snapshot(snapshot, policy)
        self.assertFalse(report["observable_governance_eligible"])
        self.assertIn("required_status_checks_missing", report["blockers"])
        self.assertGreaterEqual(len(report["missing_status_checks"]), 1)

    def test_protected_branch_with_all_required_checks_is_observably_eligible_only(self):
        policy = load_policy()
        snapshot = {
            "protected": True,
            "protection": {
                "required_status_checks": {
                    "contexts": list(policy["required_status_checks"])
                }
            },
        }
        report = assess_snapshot(snapshot, policy)
        self.assertTrue(report["observable_governance_eligible"])
        self.assertEqual(report["blockers"], [])
        self.assertFalse(report["manual_controls_verified"])
        self.assertFalse(report["production_readiness_claimed"])

    def test_policy_requires_ci_release_gate_and_codeql_checks(self):
        required = set(load_policy()["required_status_checks"])
        self.assertIn("deterministic-validation (3.11)", required)
        self.assertIn("deterministic-validation (3.12)", required)
        self.assertIn("deterministic-validation (3.13)", required)
        self.assertIn("v1-prep-release-gates", required)
        self.assertIn("CodeQL (python)", required)

    def test_formal_release_gate_includes_repository_governance_blockers(self):
        gate = json.loads((ROOT / "configs/release_candidate_gate.json").read_text(encoding="utf-8"))
        self.assertFalse(gate["checks"]["main_branch_protection_verified"])
        self.assertFalse(gate["checks"]["required_status_checks_verified"])
        self.assertFalse(gate["formal_release_eligible"])

    def test_attestation_workflow_is_manual_and_uses_consolidated_action(self):
        workflow = (ROOT / ".github/workflows/release-evidence-attestation.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("actions/attest@v4", workflow)
        self.assertIn("sbom-path:", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("attestations: write", workflow)
        self.assertNotIn("pull_request:", workflow)


if __name__ == "__main__":
    unittest.main()
