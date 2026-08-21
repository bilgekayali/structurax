import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V10ReleaseGateTests(unittest.TestCase):
    def run_json(self, script: str) -> dict:
        result = subprocess.run(
            [sys.executable, script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_schema_contract_gate_passes_but_is_not_final_freeze(self):
        payload = self.run_json("scripts/verify_stable_schemas.py")
        self.assertTrue(payload["compatible"])
        self.assertGreaterEqual(payload["schema_count"], 20)
        self.assertFalse(payload["final_v1_freeze"])
        self.assertFalse(payload["production_readiness_claimed"])

    def test_dependency_closure_sbom_is_deterministic(self):
        first = subprocess.run(
            [sys.executable, "scripts/generate_dependency_sbom.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        second = subprocess.run(
            [sys.executable, "scripts/generate_dependency_sbom.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(first, second)
        payload = json.loads(first)
        names = {component["name"] for component in payload["components"]}
        self.assertIn("structurax", names)
        self.assertIn("pydantic", names)
        self.assertIn("cryptography", names)
        properties = {item["name"]: item["value"] for item in payload["metadata"]["properties"]}
        self.assertEqual(properties["structurax:production-release-sbom"], "false")

    def test_formal_release_gate_fails_closed_by_configuration(self):
        payload = self.run_json("scripts/assess_release_gate.py")
        self.assertFalse(payload["eligible"])
        self.assertFalse(payload["formal_release_declared"])
        self.assertIn("independent_security_review_verified", payload["blockers"])
        self.assertIn("build_provenance_attested", payload["blockers"])
        self.assertIn("package_version_not_1_0_0", payload["blockers"])
        self.assertFalse(payload["production_readiness_claimed"])

    def test_release_gate_cannot_claim_eligible_with_blockers(self):
        from scripts.assess_release_gate import assess_release_gate, load_gate

        gate = load_gate()
        gate["formal_release_eligible"] = True
        with self.assertRaises(SystemExit):
            assess_release_gate(gate)


if __name__ == "__main__":
    unittest.main()
