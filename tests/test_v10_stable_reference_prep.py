import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from structurax.stable_reference import (
    ObservabilityEvent,
    StableReferenceProfile,
    TenantContext,
    TenantEvidenceEnvelope,
    require_same_tenant,
    stable_reference_profile,
)

ROOT = Path(__file__).resolve().parents[1]
D = "a" * 64


class V10StableReferencePrepTests(unittest.TestCase):
    def context(self, tenant: str = "tenant-a") -> TenantContext:
        return TenantContext(
            tenant_id=tenant,
            principal_id="reviewer-01",
            issuer="https://identity.example/reference",
            subject="reviewer-01",
            roles=("reviewer",),
            authenticated_at=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
            mfa_verified=True,
        )

    def envelope(self, tenant: str = "tenant-a") -> TenantEvidenceEnvelope:
        return TenantEvidenceEnvelope(
            tenant_id=tenant,
            artifact_id="INV-001",
            ciphertext_sha256=D,
            source_sha256="b" * 64,
            encryption_algorithm="AES-256-GCM",
            key_reference="kms://reference/tenant-a/evidence",
            key_version="1",
            ciphertext_bytes=1024,
        )

    def test_cross_tenant_evidence_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "tenant boundary mismatch"):
            require_same_tenant(self.context("tenant-a"), self.envelope("tenant-b"))

    def test_same_tenant_reference_is_accepted(self):
        require_same_tenant(self.context(), self.envelope())

    def test_roles_must_be_canonical(self):
        payload = self.context().model_dump()
        payload["roles"] = ("reviewer", "reviewer")
        with self.assertRaisesRegex(ValidationError, "sorted, unique"):
            TenantContext.model_validate(payload)

    def test_key_reference_cannot_embed_secret_material(self):
        payload = self.envelope().model_dump()
        payload["key_reference"] = "kms://reference?token=secret"
        with self.assertRaisesRegex(ValidationError, "opaque reference"):
            TenantEvidenceEnvelope.model_validate(payload)

    def test_observability_forbids_raw_content(self):
        with self.assertRaises(ValidationError):
            ObservabilityEvent(
                tenant_id="tenant-a",
                trace_id="trace-01",
                event_type="analysis",
                artifact_sha256=D,
                occurred_at=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
                outcome="review",
                raw_document_content="invoice body",
            )

    def test_stable_profile_cannot_claim_production_readiness(self):
        profile = stable_reference_profile()
        self.assertFalse(profile.production_readiness_claimed)
        payload = profile.model_dump()
        payload["production_readiness_claimed"] = True
        with self.assertRaises(ValidationError):
            StableReferenceProfile.model_validate(payload)

    def test_postgres_reference_forces_rls_and_scopes_tenant(self):
        sql = (ROOT / "sql/001_tenant_rls_reference.sql").read_text(encoding="utf-8")
        self.assertIn("FORCE ROW LEVEL SECURITY", sql)
        self.assertGreaterEqual(sql.count("current_setting('app.tenant_id', true)"), 4)
        self.assertIn("reference-only", sql.lower())

    def test_public_api_contract_checker_passes(self):
        result = subprocess.run(
            [sys.executable, "scripts/verify_stable_api.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["compatible"])
        self.assertFalse(payload["production_readiness_claimed"])

    def test_release_provenance_is_deterministic_and_explicitly_incomplete(self):
        command = [sys.executable, "scripts/build_release_provenance.py"]
        first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        second = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertEqual(first.stdout, second.stdout)
        payload = json.loads(first.stdout)
        self.assertEqual(len(payload["source_tree_sha256"]), 64)
        self.assertFalse(payload["resolved_dependency_sbom"])
        self.assertFalse(payload["build_attestation"])
        self.assertFalse(payload["production_readiness_claimed"])


if __name__ == "__main__":
    unittest.main()
