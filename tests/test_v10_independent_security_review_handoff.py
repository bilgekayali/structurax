import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_independent_review_handoff import build_independent_review_handoff
from scripts.verify_independent_review import verify_independent_review


ROOT = Path(__file__).resolve().parents[1]


class V10IndependentSecurityReviewHandoffTests(unittest.TestCase):
    def _policy(self) -> dict:
        return json.loads(
            (ROOT / "configs/independent_security_review_policy.json").read_text(
                encoding="utf-8"
            )
        )

    def _v1_review(self, report: Path, digest: str) -> dict:
        policy = self._policy()
        return {
            "schema_version": "1.0.0",
            "release_surface_sha256": digest,
            "reviewer_id": "external-security-firm-2026",
            "reviewer_independence_confirmed": True,
            "review_outcome": "passed",
            "review_areas": policy["required_review_areas"],
            "external_report_artifact_id": "SEC-REVIEW-2026-001",
            "review_evidence_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            "open_findings": {
                "critical": 0,
                "high": 0,
                "medium": 1,
                "low": 2,
                "informational": 3,
            },
            "open_release_blocking_findings": 0,
            "risk_acceptance_required": False,
            "completed_at": "2026-08-23T12:00:00Z",
            "raw_secret_material_present": False,
            "production_readiness_claimed": False,
        }

    def test_v1_review_verifies_external_report_digest_and_release_surface(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "external-review.pdf"
            report.write_bytes(b"independent external security review bytes")
            digest = "a" * 64
            review_path = Path(temp) / "review.json"
            review_path.write_text(
                json.dumps(self._v1_review(report, digest)),
                encoding="utf-8",
            )
            result = verify_independent_review(
                review_path,
                digest,
                evidence_path=report,
                required_schema_version="1.0.0",
            )
            self.assertTrue(result["verified"])
            self.assertTrue(result["review_evidence_verified"])
            self.assertTrue(result["independent_security_review_verified"])
            self.assertEqual(result["review_outcome"], "passed")
            self.assertFalse(result["production_readiness_claimed"])

    def test_tampered_external_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "external-review.pdf"
            report.write_bytes(b"original report")
            digest = "b" * 64
            review_path = Path(temp) / "review.json"
            review_path.write_text(
                json.dumps(self._v1_review(report, digest)),
                encoding="utf-8",
            )
            report.write_bytes(b"tampered report")
            with self.assertRaisesRegex(SystemExit, "evidence digest mismatch"):
                verify_independent_review(
                    review_path,
                    digest,
                    evidence_path=report,
                    required_schema_version="1.0.0",
                )

    def test_open_high_finding_blocks_v1_review(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "external-review.pdf"
            report.write_bytes(b"review report")
            digest = "c" * 64
            payload = self._v1_review(report, digest)
            payload["open_findings"]["high"] = 1
            review_path = Path(temp) / "review.json"
            review_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "open high findings"):
                verify_independent_review(
                    review_path,
                    digest,
                    evidence_path=report,
                    required_schema_version="1.0.0",
                )

    def test_exact_review_area_coverage_is_required(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "external-review.pdf"
            report.write_bytes(b"review report")
            digest = "d" * 64
            payload = self._v1_review(report, digest)
            payload["review_areas"] = payload["review_areas"][:-1]
            review_path = Path(temp) / "review.json"
            review_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "exact required review areas"):
                verify_independent_review(
                    review_path,
                    digest,
                    evidence_path=report,
                    required_schema_version="1.0.0",
                )

    def test_v1_review_requires_external_report_file(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "external-review.pdf"
            report.write_bytes(b"review report")
            digest = "e" * 64
            review_path = Path(temp) / "review.json"
            review_path.write_text(
                json.dumps(self._v1_review(report, digest)),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SystemExit, "requires the external review evidence file"):
                verify_independent_review(
                    review_path,
                    digest,
                    required_schema_version="1.0.0",
                )

    def test_placeholder_reviewer_identity_is_rejected_for_v1(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "external-review.pdf"
            report.write_bytes(b"review report")
            digest = "f" * 64
            payload = self._v1_review(report, digest)
            payload["reviewer_id"] = "independent-reviewer"
            review_path = Path(temp) / "review.json"
            review_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "placeholder identity"):
                verify_independent_review(
                    review_path,
                    digest,
                    evidence_path=report,
                    required_schema_version="1.0.0",
                )

    def test_handoff_manifest_is_non_authoritative_and_digest_bound(self):
        manifest = build_independent_review_handoff()
        policy = self._policy()
        self.assertEqual(
            manifest["release_surface_digest_algorithm"],
            "sha256-release-surface-v1",
        )
        self.assertEqual(
            manifest["required_review_areas"],
            policy["required_review_areas"],
        )
        self.assertEqual(len(manifest["release_surface_sha256"]), 64)
        self.assertEqual(len(manifest["source_commit_sha"]), 40)
        self.assertTrue(manifest["external_report"]["required"])
        self.assertTrue(manifest["external_report"]["must_remain_outside_repository"])
        self.assertFalse(manifest["automatic_gate_mutation_allowed"])
        self.assertFalse(manifest["production_readiness_claimed"])

    def test_v1_schema_is_release_evidence_not_frozen_application_schema(self):
        policy = self._policy()
        self.assertTrue(policy["schema_path"].startswith("release-evidence-schemas/"))
        self.assertFalse(policy["schema_path"].startswith("schemas/"))
        self.assertTrue((ROOT / policy["schema_path"]).is_file())

    def test_runbook_requires_report_hash_verification(self):
        runbook = (ROOT / "docs/V1_RELEASE_PROMOTION_RUNBOOK.md").read_text(
            encoding="utf-8"
        )
        handoff = (ROOT / "docs/INDEPENDENT_SECURITY_REVIEW_HANDOFF.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("--independent-review-evidence", runbook)
        self.assertIn("--evidence-file", handoff)
        self.assertIn("genuine independent", handoff.lower())
        self.assertIn("must not self-attest", handoff.lower())


if __name__ == "__main__":
    unittest.main()
