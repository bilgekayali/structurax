"""Fail-closed contracts for StructuraX v1.0 stable-reference preparation."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,127}$"


class TenantContext(BaseModel):
    """Reference identity context; it does not authenticate a principal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str = Field(pattern=_ID_PATTERN)
    principal_id: str = Field(pattern=_ID_PATTERN)
    issuer: str = Field(min_length=3, max_length=512)
    subject: str = Field(min_length=1, max_length=512)
    roles: tuple[str, ...] = Field(min_length=1)
    authenticated_at: datetime
    mfa_verified: bool
    synthetic_reference: Literal[True] = True

    @field_validator("roles")
    @classmethod
    def canonical_roles(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(sorted({role.strip() for role in value if role.strip()}))
        if not normalized:
            raise ValueError("at least one non-empty role is required")
        if normalized != value:
            raise ValueError("roles must be sorted, unique, and non-empty")
        return value


class TenantEvidenceEnvelope(BaseModel):
    """Metadata-only encrypted-evidence reference; plaintext is intentionally excluded."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str = Field(pattern=_ID_PATTERN)
    artifact_id: str = Field(pattern=_ID_PATTERN)
    ciphertext_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_sha256: str = Field(pattern=_SHA256_PATTERN)
    encryption_algorithm: Literal["AES-256-GCM"]
    key_reference: str = Field(min_length=3, max_length=512)
    key_version: str = Field(min_length=1, max_length=128)
    ciphertext_bytes: int = Field(gt=0)
    plaintext_present: Literal[False] = False
    secrets_present: Literal[False] = False
    production_write_performed: Literal[False] = False

    @field_validator("key_reference")
    @classmethod
    def reference_must_not_embed_secret(cls, value: str) -> str:
        lowered = value.lower()
        forbidden = ("secret=", "password=", "private_key=", "token=")
        if any(marker in lowered for marker in forbidden):
            raise ValueError("key_reference must be an opaque reference, not secret material")
        return value


class ObservabilityEvent(BaseModel):
    """Tenant-scoped telemetry contract that forbids document payloads."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0-prep"] = "1.0-prep"
    tenant_id: str = Field(pattern=_ID_PATTERN)
    trace_id: str = Field(pattern=_ID_PATTERN)
    event_type: Literal[
        "ingestion",
        "analysis",
        "review",
        "policy",
        "security",
        "release_gate",
    ]
    artifact_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    occurred_at: datetime
    outcome: Literal["success", "review", "block", "error"]
    raw_document_content: Literal[None] = None
    prompt_content: Literal[None] = None
    secret_content: Literal[None] = None


class StableReferenceProfile(BaseModel):
    """Machine-readable posture for v1.0 preparation, not a production-readiness claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0-prep"] = "1.0-prep"
    tenant_isolation_mode: Literal["postgresql-rls-reference"]
    identity_boundary: Literal["external-oidc-reference"]
    evidence_encryption_required: Literal[True] = True
    observability_raw_content_allowed: Literal[False] = False
    autonomous_authority: Literal[False] = False
    production_execution_performed: Literal[False] = False
    production_readiness_claimed: Literal[False] = False
    independent_security_review_verified: Literal[False] = False


def require_same_tenant(context: TenantContext, evidence: TenantEvidenceEnvelope) -> None:
    """Fail closed when evidence is not bound to the caller's tenant."""

    if context.tenant_id != evidence.tenant_id:
        raise ValueError("tenant boundary mismatch")


def stable_reference_profile() -> StableReferenceProfile:
    return StableReferenceProfile(
        tenant_isolation_mode="postgresql-rls-reference",
        identity_boundary="external-oidc-reference",
    )
