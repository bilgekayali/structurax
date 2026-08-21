import base64
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from structurax.security_reference import (
    decrypt_reference_evidence,
    encrypt_reference_evidence,
    verify_reference_oidc_token,
)


ROOT = Path(__file__).resolve().parents[1]


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _token(private_key: Ed25519PrivateKey, claims: dict, header: dict | None = None) -> str:
    active_header = header or {"alg": "EdDSA", "typ": "JWT", "kid": "synthetic-key-1"}
    encoded_header = _b64url(
        json.dumps(active_header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    encoded_payload = _b64url(
        json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = _b64url(private_key.sign(signing_input))
    return f"{encoded_header}.{encoded_payload}.{signature}"


class V10SecurityReferenceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 21, 15, 0, tzinfo=timezone.utc)
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        now_ts = int(self.now.timestamp())
        self.claims = {
            "iss": "https://identity.example/reference",
            "aud": "structurax",
            "sub": "reviewer-01",
            "principal_id": "reviewer-01",
            "tenant_id": "tenant-a",
            "roles": ["reviewer", "security"],
            "amr": ["pwd", "mfa"],
            "iat": now_ts - 60,
            "auth_time": now_ts - 120,
            "exp": now_ts + 3600,
        }

    def verify(self, token: str):
        return verify_reference_oidc_token(
            token,
            self.public_key,
            expected_issuer="https://identity.example/reference",
            expected_audience="structurax",
            expected_tenant_id="tenant-a",
            now=self.now,
        )

    def test_signed_oidc_reference_token_maps_to_tenant_context(self):
        context = self.verify(_token(self.private_key, self.claims))
        self.assertEqual(context.tenant_id, "tenant-a")
        self.assertEqual(context.roles, ("reviewer", "security"))
        self.assertTrue(context.mfa_verified)

    def test_tampered_oidc_payload_fails_signature(self):
        token = _token(self.private_key, self.claims)
        header, payload, signature = token.split(".")
        tampered_claims = dict(self.claims)
        tampered_claims["tenant_id"] = "tenant-b"
        tampered_payload = _b64url(
            json.dumps(tampered_claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.verify(f"{header}.{tampered_payload}.{signature}")

    def test_wrong_tenant_is_rejected_even_with_valid_signature(self):
        claims = dict(self.claims)
        claims["tenant_id"] = "tenant-b"
        with self.assertRaisesRegex(ValueError, "tenant"):
            self.verify(_token(self.private_key, claims))

    def test_missing_mfa_is_rejected(self):
        claims = dict(self.claims)
        claims["amr"] = ["pwd"]
        with self.assertRaisesRegex(ValueError, "MFA"):
            self.verify(_token(self.private_key, claims))

    def test_expired_token_is_rejected(self):
        claims = dict(self.claims)
        claims["exp"] = int((self.now - timedelta(seconds=1)).timestamp())
        with self.assertRaisesRegex(ValueError, "expired"):
            self.verify(_token(self.private_key, claims))

    def test_unsupported_jwt_algorithm_is_rejected(self):
        token = _token(self.private_key, self.claims, {"alg": "none", "typ": "JWT"})
        with self.assertRaisesRegex(ValueError, "EdDSA"):
            self.verify(token)

    def test_tenant_bound_aes_gcm_round_trip(self):
        plaintext = b"synthetic invoice evidence"
        key = bytes(range(32))
        nonce = bytes(range(12))
        ciphertext, reference = encrypt_reference_evidence(
            plaintext,
            key,
            tenant_id="tenant-a",
            artifact_id="INV-001",
            key_reference="kms://reference/tenant-a/evidence",
            key_version="1",
            nonce=nonce,
        )
        self.assertNotIn(plaintext, ciphertext)
        self.assertFalse(reference.envelope.plaintext_present)
        self.assertFalse(reference.envelope.secrets_present)
        recovered = decrypt_reference_evidence(
            ciphertext, reference, key, tenant_id="tenant-a"
        )
        self.assertEqual(recovered, plaintext)

    def test_cross_tenant_decryption_fails_closed(self):
        ciphertext, reference = encrypt_reference_evidence(
            b"tenant-a evidence",
            b"k" * 32,
            tenant_id="tenant-a",
            artifact_id="INV-002",
            key_reference="kms://reference/tenant-a/evidence",
            key_version="1",
            nonce=b"n" * 12,
        )
        with self.assertRaisesRegex(ValueError, "tenant boundary mismatch"):
            decrypt_reference_evidence(
                ciphertext, reference, b"k" * 32, tenant_id="tenant-b"
            )

    def test_ciphertext_tampering_is_detected_before_decryption(self):
        ciphertext, reference = encrypt_reference_evidence(
            b"tamper-evident evidence",
            b"z" * 32,
            tenant_id="tenant-a",
            artifact_id="INV-003",
            key_reference="kms://reference/tenant-a/evidence",
            key_version="1",
            nonce=b"q" * 12,
        )
        tampered = bytearray(ciphertext)
        tampered[0] ^= 1
        with self.assertRaisesRegex(ValueError, "ciphertext digest mismatch"):
            decrypt_reference_evidence(
                bytes(tampered), reference, b"z" * 32, tenant_id="tenant-a"
            )

    def test_wrong_key_fails_authentication(self):
        ciphertext, reference = encrypt_reference_evidence(
            b"authenticated evidence",
            b"a" * 32,
            tenant_id="tenant-a",
            artifact_id="INV-004",
            key_reference="kms://reference/tenant-a/evidence",
            key_version="1",
            nonce=b"r" * 12,
        )
        with self.assertRaisesRegex(ValueError, "authentication failed"):
            decrypt_reference_evidence(
                ciphertext, reference, b"b" * 32, tenant_id="tenant-a"
            )

    def test_security_validation_is_expected_as_required_status_check(self):
        policy = json.loads(
            (ROOT / "configs/repository_governance_policy.json").read_text(encoding="utf-8")
        )
        self.assertIn("security-reference-validation", policy["required_status_checks"])
        self.assertFalse(policy["production_readiness_claimed"])


if __name__ == "__main__":
    unittest.main()
