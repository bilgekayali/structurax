import json
import unittest
from pathlib import Path

from scripts.assess_promotion_readiness import assess_promotion_readiness, load_policy as load_promotion_policy
from scripts.assess_release_gate import load_gate
from scripts.build_branch_protection_payload import build_branch_protection_payload
from scripts.verify_branch_protection_snapshot import verify_branch_protection_snapshot


ROOT = Path(__file__).resolve().parents[1]


def compliant_protection_snapshot():
    policy = json.loads((ROOT / "configs/repository_governance_policy.json").read_text(encoding="utf-8"))
    manual = policy["manual_controls_expected"]
    return {
        "required_status_checks": {
            "strict": manual["strict_status_checks"],
            "contexts": list(policy["required_status_checks"]),
        },
        "enforce_admins": {"enabled": manual["enforce_admins"]},
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": manual["dismiss_stale_reviews"],
            "require_code_owner_reviews": manual["require_code_owner_reviews"],
            "required_approving_review_count": manual["required_approving_reviews"],
            "require_last_push_approval": manual["require_last_push_approval"],
        },
        "required_conversation_resolution": {"enabled": manual["conversation_resolution_required"]},
        "allow_force_pushes": {"enabled": manual["force_pushes_allowed"]},
        "allow_deletions": {"enabled": manual["branch_deletion_allowed"]},
        "required_linear_history": {"enabled": manual["required_linear_history"]},
    }


class V10PromotionHandoffTests(unittest.TestCase):
    def test_branch_protection_payload_matches_governance_policy(self):
        policy = json.loads((ROOT / "configs/repository_governance_policy.json").read_text(encoding="utf-8"))
        payload = build_branch_protection_payload(policy)
        self.assertTrue(payload["required_status_checks"]["strict"])
        self.assertEqual(payload["required_status_checks"]["contexts"], policy["required_status_checks"])
        self.assertTrue(payload["enforce_admins"])
        self.assertTrue(payload["required_pull_request_reviews"]["require_last_push_approval"])
        self.assertEqual(payload["required_pull_request_reviews"]["required_approving_review_count"], 1)
        self.assertFalse(payload["allow_force_pushes"])
        self.assertFalse(payload["allow_deletions"])
        self.assertTrue(payload["required_conversation_resolution"])

    def test_exact_protection_snapshot_is_verified_without_auto_promotion(self):
        report = verify_branch_protection_snapshot(compliant_protection_snapshot())
        self.assertTrue(report["branch_protection_verified"])
        self.assertTrue(report["required_status_checks_verified"])
        self.assertTrue(report["codeql_release_gate_enforced"])
        self.assertFalse(report["formal_gate_mutation_authorized"])
        self.assertFalse(report["production_readiness_claimed"])

    def test_protection_snapshot_fails_closed_on_review_or_codeql_drift(self):
        snapshot = compliant_protection_snapshot()
        snapshot["required_pull_request_reviews"]["require_last_push_approval"] = False
        snapshot["required_status_checks"]["contexts"].remove("CodeQL (python)")
        report = verify_branch_protection_snapshot(snapshot)
        self.assertFalse(report["branch_protection_verified"])
        self.assertFalse(report["required_status_checks_verified"])
        self.assertIn("require_last_push_approval_mismatch", report["blockers"])
        self.assertIn("required_status_checks_missing", report["blockers"])

    def test_promotion_readiness_remains_blocked_without_external_evidence(self):
        report = assess_promotion_readiness(
            gate=load_gate(),
            policy=load_promotion_policy(),
            branch_snapshot={
                "protected": True,
                "protection": {
                    "required_status_checks": {
                        "contexts": json.loads(
                            (ROOT / "configs/repository_governance_policy.json").read_text(encoding="utf-8")
                        )["required_status_checks"]
                    }
                },
            },
            protection_snapshot=compliant_protection_snapshot(),
            package_version="0.5.0",
            repository_digest="a" * 64,
        )
        self.assertFalse(report["ready_for_human_promotion"])
        self.assertTrue(report["candidate_checks"]["main_branch_protection_verified"])
        self.assertTrue(report["candidate_checks"]["required_status_checks_verified"])
        self.assertTrue(report["candidate_checks"]["codeql_release_gate_enforced"])
        self.assertIn("postgresql_tenant_isolation_validated", report["blockers"])
        self.assertIn("complete_release_sbom_attached", report["blockers"])
        self.assertIn("independent_security_review_verified", report["blockers"])
        self.assertIn("package_version_not_1_0_0", report["blockers"])
        self.assertFalse(report["formal_gate_mutation_authorized"])

    def test_current_formal_gate_is_not_mutated_by_promotion_assessment(self):
        before = load_gate()
        assess_promotion_readiness(
            gate=before,
            branch_snapshot={"protected": False, "protection": {}},
            repository_digest="b" * 64,
        )
        after = load_gate()
        self.assertEqual(before, after)
        self.assertFalse(after["formal_release_eligible"])

    def test_governance_policy_requires_promotion_readiness_check(self):
        policy = json.loads((ROOT / "configs/repository_governance_policy.json").read_text(encoding="utf-8"))
        self.assertIn("promotion-readiness", policy["required_status_checks"])

    def test_promotion_workflow_and_runbook_are_fail_closed(self):
        workflow = (ROOT / ".github/workflows/promotion-readiness.yml").read_text(encoding="utf-8")
        runbook = (ROOT / "docs/V1_RELEASE_PROMOTION_RUNBOOK.md").read_text(encoding="utf-8")
        self.assertIn("promotion-readiness:", workflow)
        self.assertIn('"ready_for_human_promotion": false', workflow)
        self.assertIn('"formal_gate_mutation_authorized": false', workflow)
        self.assertIn("/branches/main/protection", runbook)
        self.assertIn("2026-03-10", runbook)
        self.assertIn("Do not", runbook)
        self.assertIn("formal_release_eligible", runbook)


if __name__ == "__main__":
    unittest.main()
