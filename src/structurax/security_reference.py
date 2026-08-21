"""Cryptographic reference controls for StructuraX v1.0 preparation.

These helpers validate bounded security properties with synthetic/reference inputs. They do not
provision an IdP, KMS, database, or production deployment.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .stable_reference import TenantContext, TenantEvidenceEnvelope


_SHA256_PATTERN = r"^[0-9a-f]{64}$"


def _b64url_decode(value: str) -> bytes:
    if not value or any(char.isspace() for char in value):
        raise ValueError("invalid base64url value")
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode((value + padding).encode("ascii"))
    except (UnicodeEncodeError, ValueError) as exc:
        raise ValueError("invalid base64url value") from exc


def _decode_json_segment(value: str, label: str) -> dict[str, Any]:
    try:
        decoded = json.loads(_b64url_decode(value).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid {label} JSON") from exc
    if not isinstance(decoded, dict):
        raise ValueError(f"{label} must be a JSON object")
    return decoded


def _audience_matches(claim: object, expected: str) -> bool:
    if isinstance(claim, str):
        return claim == expected
    if isinstance(claim, list):
        return expected in claim and all(isinstance(item, str) for item in claim)
    return False


class EncryptedEvidenceReference(BaseModel):
    """Metadata required to authenticate tenant-bound ciphertext."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    envelope: TenantEvidenceEnvelope
    nonce_b64url: str = Field(min_length=16, max_length=32)
    aad_sha256: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("nonce_b64url")
    @classmethod
    def nonce_is_96_bits(cls, value: str) -> str:
        if len(_b64url_decode(value)) != 12:
            raise ValueError("AES-GCM nonce must be exactly 96 bits")
        return value


def verify_reference_oidc_token(
    token: str,
    public_key_bytes: bytes,
    *,
    expected_issuer: str,
    expected_audience: str,
    expected_tenant_id: str,
    now: datetime,
) -> TenantContext:
    """Verify a compact EdDSA JWT and map bounded claims into a tenant context.

    This verifies the token signature and a strict claim subset against a pinned public key.
    It does not discover keys, validate a live OIDC provider, or perform token revocation.
    """

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("token must contain exactly three JWT segments")
    encoded_header, encoded_payload, encoded_signature = parts

    header = _decode_json_segment(encoded_header, "JWT header")
    claims = _decode_json_segment(encoded_payload, "JWT payload")
    if header.get("alg") != "EdDSA" or header.get("typ") != "JWT":
        raise ValueError("only EdDSA JWT tokens are accepted")
    if "crit" in header:
        raise ValueError("critical JWT extensions are not supported")

    try:
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(
            _b64url_decode(encoded_signature),
            f"{encoded_header}.{encoded_payload}".encode("ascii"),
        )
    except (ValueError, InvalidSignature) as exc:
        raise ValueError("JWT signature verification failed") from exc

    if claims.get("iss") != expected_issuer:
        raise ValueError("unexpected token issuer")
    if not _audience_matches(claims.get("aud"), expected_audience):
        raise ValueError("unexpected token audience")
    if claims.get("tenant_id") != expected_tenant_id:
        raise ValueError("token tenant does not match requested tenant")

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("token subject is required")

    now_ts = int(now.timestamp())
    exp = claims.get("exp")
    iat = claims.get("iat")
    auth_time = claims.get("auth_time", iat)
    nbf = claims.get("nbf")
    for name, value in (("exp", exp), ("iat", iat), ("auth_time", auth_time)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} must be an integer timestamp")
    if nbf is not None and (not isinstance(nbf, int) or isinstance(nbf, bool)):
        raise ValueError("nbf must be an integer timestamp")
    if exp <= now_ts:
        raise ValueError("token is expired")
    if iat > now_ts or auth_time > now_ts:
        raise ValueError("token timestamps cannot be in the future")
    if nbf is not None and nbf > now_ts:
        raise ValueError("token is not active yet")

    roles_claim = claims.get("roles")
    if not isinstance(roles_claim, list) or not roles_claim or not all(
        isinstance(role, str) and role.strip() for role in roles_claim
    ):
        raise ValueError("token roles must be a non-empty string list")
    roles = tuple(sorted(set(role.strip() for role in roles_claim)))

    amr = claims.get("amr")
    if not isinstance(amr, list) or "mfa" not in amr:
        raise ValueError("token must prove MFA through the amr claim")

    principal_id = claims.get("principal_id", subject)
    if not isinstance(principal_id, str) or not principal_id:
        raise ValueError("principal_id must be a non-empty string")

    return TenantContext(
        tenant_id=expected_tenant_id,
        principal_id=principal_id,
        issuer=expected_issuer,
        subject=subject,
        roles=roles,
        authenticated_at=datetime.fromtimestamp(auth_time, tz=timezone.utc),
        mfa_verified=True,
    )


def _evidence_aad(tenant_id: str, artifact_id: str, source_sha256: str) -> bytes:
    return json.dumps(
        {
            "artifact_id": artifact_id,
            "source_sha256": source_sha256,
            "tenant_id": tenant_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def encrypt_reference_evidence(
    plaintext: bytes,
    key: bytes,
    *,
    tenant_id: str,
    artifact_id: str,
    key_reference: str,
    key_version: str,
    nonce: bytes,
) -> tuple[bytes, EncryptedEvidenceReference]:
    """Encrypt synthetic/reference evidence with tenant-bound AES-256-GCM AAD."""

    if len(key) != 32:
        raise ValueError("AES-256-GCM requires a 32-byte key")
    if len(nonce) != 12:
        raise ValueError("AES-GCM nonce must be exactly 12 bytes")
    if not plaintext:
        raise ValueError("plaintext evidence must not be empty")

    source_sha256 = hashlib.sha256(plaintext).hexdigest()
    aad = _evidence_aad(tenant_id, artifact_id, source_sha256)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    envelope = TenantEvidenceEnvelope(
        tenant_id=tenant_id,
        artifact_id=artifact_id,
        ciphertext_sha256=hashlib.sha256(ciphertext).hexdigest(),
        source_sha256=source_sha256,
        encryption_algorithm="AES-256-GCM",
        key_reference=key_reference,
        key_version=key_version,
        ciphertext_bytes=len(ciphertext),
    )
    reference = EncryptedEvidenceReference(
        envelope=envelope,
        nonce_b64url=base64.urlsafe_b64encode(nonce).rstrip(b"=").decode("ascii"),
        aad_sha256=hashlib.sha256(aad).hexdigest(),
    )
    return ciphertext, reference


def decrypt_reference_evidence(
    ciphertext: bytes,
    reference: EncryptedEvidenceReference,
    key: bytes,
    *,
    tenant_id: str,
) -> bytes:
    """Decrypt only when tenant, ciphertext digest, AAD and source digest all authenticate."""

    if len(key) != 32:
        raise ValueError("AES-256-GCM requires a 32-byte key")
    envelope = reference.envelope
    if envelope.tenant_id != tenant_id:
        raise ValueError("tenant boundary mismatch")
    if len(ciphertext) != envelope.ciphertext_bytes:
        raise ValueError("ciphertext length mismatch")
    if hashlib.sha256(ciphertext).hexdigest() != envelope.ciphertext_sha256:
        raise ValueError("ciphertext digest mismatch")

    aad = _evidence_aad(envelope.tenant_id, envelope.artifact_id, envelope.source_sha256)
    if hashlib.sha256(aad).hexdigest() != reference.aad_sha256:
        raise ValueError("evidence AAD digest mismatch")

    nonce = _b64url_decode(reference.nonce_b64url)
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise ValueError("evidence authentication failed") from exc
    if hashlib.sha256(plaintext).hexdigest() != envelope.source_sha256:
        raise ValueError("decrypted evidence digest mismatch")
    return plaintext
