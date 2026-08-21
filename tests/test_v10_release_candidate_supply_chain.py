import json
import tempfile
import unittest
from pathlib import Path

import structurax

from scripts.build_release_evidence_manifest import build_release_evidence_manifest
from scripts.repository_review_digest import EXCLUDED
from scripts.verify_independent_review import verify_independent_review
from scripts.verify_release_evidence_manifest import verify_release_evidence_manifest


ROOT = Path(__file__).resolve().parents[1]


class V10ReleaseCandidateSupplyChainTests(unittest.TestCase):
    def make_dist(self, root: Path) -> Path:
        dist = root / "dist"
        dist.mkdir()
        version = structurax.__version__
        (dist / f"structurax-{version}-py3-none-any.whl").write_bytes(b"synthetic-wheel")
        (dist / "structurax-dependency-sbom.cdx.json").write_text(
            json.dumps(
                {
                    "bomFormat": "CycloneDX",
                    "specVersion": "1.5",
                    "metadata": {"component": {"name": "structurax", "version": version}},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        (dist / "structurax-source-provenance.json").write_text(
            json.dumps(
                {
                    "package": "structurax",
                    "package_version": version,
                    "build_attestation": False,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        (dist / "structurax-release-gate.json").write_text(
            json.dumps({"package_version": version, "eligible": False}, sort_keys=True),
            encoding="utf-8",
        )
        return dist

    def test_release_evidence_manifest_binds_exact_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            dist = self.make_dist(Path(temp))
            manifest = build_release_evidence_manifest(dist)
            path = dist / "structurax-release-evidence-manifest.json"
            path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            verified = verify_release_evidence_manifest(path, dist)
            self.assertTrue(verified["verified"])
            self.assertEqual(
                verified["artifact_roles"],
                ["wheel", "dependency_sbom", "source_provenance", "release_gate"],
            )
            self.assertFalse(verified["formal_release_evidence_complete"])
            self.assertFalse(verified["production_readiness_claimed"])

    def test_release_evidence_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            dist = self.make_dist(Path(temp))
            manifest = build_release_evidence_manifest(dist)
            path = dist / "structurax-release-evidence-manifest.json"
            path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
            (dist / "structurax-source-provenance.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(SystemExit):
                verify_release_evidence_manifest(path, dist)

    def test_independent_review_binds_exact_repository_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            expected = "a" * 64
            review_path = Path(temp) / "review.json"
            review_path.write_text(
                json.dumps(
                    {
                        "schema_version": "0.4.0",
                        "reviewed_repository_sha256": expected,
                        "reviewer_id": "independent-reviewer",
                        "reviewer_independence_confirmed": True,
                        "review_evidence_sha256": "b" * 64,
                        "completed_at": "2026-08-21T15:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            result = verify_independent_review(review_path, expected)
            self.assertTrue(result["independent_security_review_verified"])
            self.assertFalse(result["formal_release_gate_updated"])
            self.assertFalse(result["production_readiness_claimed"])

    def test_independent_review_for_other_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            review_path = Path(temp) / "review.json"
            review_path.write_text(
                json.dumps(
                    {
                        "schema_version": "0.4.0",
                        "reviewed_repository_sha256": "a" * 64,
                        "reviewer_id": "independent-reviewer",
                        "reviewer_independence_confirmed": True,
                        "review_evidence_sha256": "b" * 64,
                        "completed_at": "2026-08-21T15:00:00+00:00",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                verify_independent_review(review_path, "c" * 64)

    def test_review_evidence_file_is_excluded_from_review_digest(self):
        self.assertIn("security-review/v1.0-review.json", EXCLUDED)

    def test_attestation_workflow_verifies_manifest_before_attesting(self):
        workflow = (ROOT / ".github/workflows/release-evidence-attestation.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("python scripts/build_release_evidence_manifest.py", workflow)
        self.assertLess(
            workflow.index("python scripts/verify_release_evidence_manifest.py"),
            workflow.index("uses: actions/attest@v4"),
        )

    def test_governance_policy_requires_release_evidence_validation(self):
        policy = json.loads((ROOT / "configs/repository_governance_policy.json").read_text(encoding="utf-8"))
        self.assertIn("release-evidence-validation", policy["required_status_checks"])

    def test_formal_release_gate_remains_closed_for_external_evidence(self):
        gate = json.loads((ROOT / "configs/release_candidate_gate.json").read_text(encoding="utf-8"))
        checks = gate["checks"]
        self.assertFalse(checks["complete_release_sbom_attached"])
        self.assertFalse(checks["build_provenance_attested"])
        self.assertFalse(checks["independent_security_review_verified"])
        self.assertFalse(gate["formal_release_eligible"])


if __name__ == "__main__":
    unittest.main()
