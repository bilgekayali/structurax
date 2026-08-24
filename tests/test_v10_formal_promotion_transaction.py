import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_formal_promotion_plan import build_formal_promotion_plan, load_policy
from scripts.release_surface_digest import compute_release_surface_digest

ROOT = Path(__file__).resolve().parents[1]


class V10FormalPromotionTransactionTests(unittest.TestCase):
    def _tracked_repo(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "src/structurax").mkdir(parents=True)
        (root / "release-approval").mkdir(parents=True)
        (root / "pyproject.toml").write_text(
            '[project]\nname = "structurax"\nversion = "1.0.0"\nclassifiers = [\n'
            '  "Development Status :: 3 - Alpha",\n]\n',
            encoding="utf-8",
        )
        (root / "src/structurax/__init__.py").write_text(
            '__version__ = "1.0.0"\n', encoding="utf-8"
        )
        (root / "src/structurax/core.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "release-approval/v1.0-promotion.json").write_text(
            '{"approved": false}\n', encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        return temp, root

    def _ready_report(self, digest: str) -> dict:
        gate = json.loads((ROOT / "configs/release_candidate_gate.json").read_text(encoding="utf-8"))
        return {
            "repository_sha256": digest,
            "package_version": "1.0.0",
            "candidate_checks": {name: True for name in gate["checks"]},
            "blockers": [],
            "ready_for_human_promotion": True,
            "human_promotion_required": True,
            "formal_gate_mutation_authorized": False,
            "production_readiness_claimed": False,
        }

    def test_stable_classifier_promotion_preserves_release_surface_digest(self):
        temp, root = self._tracked_repo()
        try:
            before = compute_release_surface_digest(root)
            pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
            pyproject = pyproject.replace(
                "Development Status :: 3 - Alpha",
                "Development Status :: 5 - Production/Stable",
            )
            (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
            after = compute_release_surface_digest(root)
            self.assertEqual(before, after)
        finally:
            temp.cleanup()

    def test_source_change_changes_release_surface_digest(self):
        temp, root = self._tracked_repo()
        try:
            before = compute_release_surface_digest(root)
            (root / "src/structurax/core.py").write_text("VALUE = 2\n", encoding="utf-8")
            after = compute_release_surface_digest(root)
            self.assertNotEqual(before, after)
        finally:
            temp.cleanup()

    def test_human_approval_record_is_excluded_from_release_surface_digest(self):
        temp, root = self._tracked_repo()
        try:
            before = compute_release_surface_digest(root)
            (root / "release-approval/v1.0-promotion.json").write_text(
                '{"approved": true, "ticket": "REL-100"}\n', encoding="utf-8"
            )
            after = compute_release_surface_digest(root)
            self.assertEqual(before, after)
        finally:
            temp.cleanup()

    def test_all_checks_can_produce_a_human_only_stable_promotion_plan(self):
        digest = "a" * 64
        plan = build_formal_promotion_plan(
            self._ready_report(digest),
            "b" * 40,
            release_surface_sha256=digest,
        )
        self.assertTrue(plan["promotion_plan_eligible"])
        self.assertEqual(plan["package_baseline_version"], "1.0.0")
        self.assertEqual(plan["target_version"], "1.0.0")
        self.assertEqual(plan["target_tag"], "v1.0.0")
        self.assertEqual(len(plan["metadata_mutations"]), 1)
        self.assertEqual(
            plan["metadata_mutations"][0]["field"],
            "project.classifiers.development_status",
        )
        self.assertFalse(plan["automatic_metadata_mutation_allowed"])
        self.assertFalse(plan["automatic_tag_creation_allowed"])
        self.assertFalse(plan["automatic_publish_allowed"])
        self.assertTrue(plan["human_approval_required"])

    def test_non_version_blocker_prevents_stable_promotion_plan(self):
        digest = "c" * 64
        report = self._ready_report(digest)
        report["candidate_checks"]["independent_security_review_verified"] = False
        report["blockers"] = ["independent_security_review_verified"]
        report["ready_for_human_promotion"] = False
        plan = build_formal_promotion_plan(report, "d" * 40, release_surface_sha256=digest)
        self.assertFalse(plan["promotion_plan_eligible"])
        self.assertEqual(plan["metadata_mutations"], [])
        self.assertIn("independent_security_review_verified", plan["blockers"])
        self.assertIn("promotion_readiness_has_blockers", plan["blockers"])
        self.assertIn("promotion_readiness_not_ready", plan["blockers"])

    def test_package_baseline_mismatch_prevents_stable_promotion_plan(self):
        digest = "1" * 64
        report = self._ready_report(digest)
        report["package_version"] = "0.5.0"
        plan = build_formal_promotion_plan(report, "2" * 40, release_surface_sha256=digest)
        self.assertFalse(plan["promotion_plan_eligible"])
        self.assertIn("package_baseline_version_mismatch", plan["blockers"])

    def test_promotion_plan_rejects_different_release_surface_digest(self):
        with self.assertRaisesRegex(SystemExit, "different v1.0 release-surface digest"):
            build_formal_promotion_plan(
                self._ready_report("e" * 64),
                "f" * 40,
                release_surface_sha256="0" * 64,
            )

    def test_policies_use_release_surface_digest_and_required_check(self):
        promotion = json.loads(
            (ROOT / "configs/promotion_readiness_policy.json").read_text(encoding="utf-8")
        )
        production = json.loads(
            (ROOT / "configs/production_evidence_policy.json").read_text(encoding="utf-8")
        )
        governance = json.loads(
            (ROOT / "configs/repository_governance_policy.json").read_text(encoding="utf-8")
        )
        self.assertEqual(promotion["release_surface_digest_algorithm"], "sha256-release-surface-v1")
        self.assertEqual(production["repository_digest_algorithm"], "sha256-release-surface-v1")
        self.assertIn("formal-promotion-transaction", governance["required_status_checks"])

    def test_package_is_1_0_0_without_false_stable_claim(self):
        gate = json.loads((ROOT / "configs/release_candidate_gate.json").read_text(encoding="utf-8"))
        policy = load_policy()
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        package_init = (ROOT / "src/structurax/__init__.py").read_text(encoding="utf-8")
        self.assertFalse(gate["formal_release_eligible"])
        self.assertEqual(policy["package_baseline_version"], "1.0.0")
        self.assertEqual(policy["target_version"], "1.0.0")
        self.assertIn('version = "1.0.0"', pyproject)
        self.assertIn('Development Status :: 3 - Alpha', pyproject)
        self.assertIn('__version__ = "1.0.0"', package_init)
        self.assertFalse(policy["production_readiness_claimed"])


if __name__ == "__main__":
    unittest.main()
