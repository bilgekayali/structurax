"""Fail-closed v0.3 probabilistic extraction boundary.

StructuraX core accepts only closed, offline adapter contracts. The built-in recorded
adapter replays committed synthetic responses and never performs network, tool,
subprocess, filesystem-write, or live model execution.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from pydantic import Field, model_validator

from structurax.models import StrictModel

AI_SCHEMA_VERSION = "0.3.0"
MAX_AI_PAGES = 200
MAX_AI_PAGE_TEXT = 10_000
MAX_AI_TOTAL_TEXT = 100_000
MAX_REQUESTED_FIELDS = 64
MAX_FIELD_VALUE = 5_000


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(payload: object) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(raw)


class AIExecutionProfile(StrictModel):
    network_access: Literal[False] = False
    tool_access: Literal[False] = False
    subprocess_access: Literal[False] = False
    filesystem_write_access: Literal[False] = False

    @model_validator(mode="after")
    def require_closed_profile(self) -> "AIExecutionProfile":
        if any(
            (
                self.network_access,
                self.tool_access,
                self.subprocess_access,
                self.filesystem_write_access,
            )
        ):
            raise ValueError("v0.3 core accepts only closed offline AI adapter profiles")
        return self


class AIAdapterIdentity(StrictModel):
    adapter_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,79}$")
    adapter_version: str = Field(min_length=1, max_length=40)
    provider_label: str = Field(min_length=1, max_length=80)
    model_label: str = Field(min_length=1, max_length=120)
    response_format: str = Field(default="structurax-ai-fields-v1", min_length=1, max_length=80)
    execution_profile: AIExecutionProfile = Field(default_factory=AIExecutionProfile)


class AIPageInput(StrictModel):
    page_number: int = Field(ge=1, le=MAX_AI_PAGES)
    text: str = Field(max_length=MAX_AI_PAGE_TEXT)


class AIExtractionRequest(StrictModel):
    schema_version: Literal["0.3.0"] = AI_SCHEMA_VERSION
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    ingestion_extraction_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    pages: list[AIPageInput] = Field(min_length=1, max_length=MAX_AI_PAGES)
    requested_fields: list[str] = Field(min_length=1, max_length=MAX_REQUESTED_FIELDS)

    @model_validator(mode="after")
    def validate_request(self) -> "AIExtractionRequest":
        page_numbers = [page.page_number for page in self.pages]
        if page_numbers != list(range(1, len(self.pages) + 1)):
            raise ValueError("AI request pages must be contiguous and start at page 1")
        if sum(len(page.text) for page in self.pages) > MAX_AI_TOTAL_TEXT:
            raise ValueError("AI request text exceeds the v0.3 bounded text limit")
        if self.requested_fields != sorted(set(self.requested_fields)):
            raise ValueError("requested_fields must be unique and canonically sorted")
        for field_name in self.requested_fields:
            if not field_name or len(field_name) > 120:
                raise ValueError("requested field names must be 1..120 characters")
        return self


class AIFieldPrediction(StrictModel):
    field_name: str = Field(min_length=1, max_length=120)
    value: str = Field(max_length=MAX_FIELD_VALUE)
    confidence: float = Field(ge=0, le=1)
    evidence_pages: list[int] = Field(min_length=1, max_length=MAX_AI_PAGES)
    evidence_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def canonical_evidence_pages(self) -> "AIFieldPrediction":
        if self.evidence_pages != sorted(set(self.evidence_pages)):
            raise ValueError("evidence_pages must be unique and canonically sorted")
        return self


class AIAdapterResponse(StrictModel):
    fields: list[AIFieldPrediction]
    overall_confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    latency_ms: int = Field(ge=0, le=600_000)
    cost_usd: float = Field(ge=0, le=1000)
    provider_response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def canonical_response(self) -> "AIAdapterResponse":
        names = [field.field_name for field in self.fields]
        if names != sorted(set(names)):
            raise ValueError("AI response fields must be unique and canonically sorted")
        if self.warnings != sorted(set(self.warnings)):
            raise ValueError("AI response warnings must be unique and canonically sorted")
        return self


class AIExtractionArtifact(StrictModel):
    schema_version: Literal["0.3.0"] = AI_SCHEMA_VERSION
    request_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    adapter: AIAdapterIdentity
    fields: list[AIFieldPrediction]
    overall_confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    latency_ms: int = Field(ge=0, le=600_000)
    cost_usd: float = Field(ge=0, le=1000)
    provider_response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    external_execution_performed: Literal[False] = False
    requires_human_review: Literal[True] = True


class RecordedAIResponseCatalog(StrictModel):
    schema_version: Literal["0.3.0"] = AI_SCHEMA_VERSION
    adapter: AIAdapterIdentity
    responses: dict[str, AIAdapterResponse]

    @model_validator(mode="after")
    def validate_digest_keys(self) -> "RecordedAIResponseCatalog":
        for digest in self.responses:
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("recorded AI response keys must be lowercase SHA-256 digests")
        return self


@runtime_checkable
class AIExtractionAdapter(Protocol):
    @property
    def identity(self) -> AIAdapterIdentity: ...

    def extract(self, request: AIExtractionRequest) -> AIAdapterResponse: ...


class RecordedAIAdapter:
    """Offline adapter that replays exact request-digest-bound synthetic responses."""

    def __init__(self, catalog: RecordedAIResponseCatalog) -> None:
        self._catalog = catalog

    @property
    def identity(self) -> AIAdapterIdentity:
        return self._catalog.adapter

    def extract(self, request: AIExtractionRequest) -> AIAdapterResponse:
        digest = canonical_digest(request.model_dump(mode="json"))
        try:
            return self._catalog.responses[digest]
        except KeyError as exc:
            raise ValueError(f"no recorded AI response exists for request digest {digest}") from exc

    @classmethod
    def from_path(cls, path: str | Path) -> "RecordedAIAdapter":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(RecordedAIResponseCatalog.model_validate(payload))


class AITrustPolicy(StrictModel):
    schema_version: Literal["0.3.0"] = AI_SCHEMA_VERSION
    minimum_overall_confidence: float = Field(default=0.80, ge=0, le=1)
    minimum_field_confidence: float = Field(default=0.75, ge=0, le=1)
    required_fields: list[str] = Field(default_factory=list, max_length=MAX_REQUESTED_FIELDS)
    prompt_injection_indicators: list[str] = Field(
        default_factory=lambda: sorted([
            "approve without review",
            "ignore previous instructions",
            "ignore prior instructions",
            "system override",
            "inceleme olmadan onayla",
            "sistem talimatını geçersiz kıl",
            "önceki talimatları yok say",
        ], key=str.casefold)
    )

    @model_validator(mode="after")
    def canonical_policy(self) -> "AITrustPolicy":
        if self.required_fields != sorted(set(self.required_fields)):
            raise ValueError("required_fields must be unique and canonically sorted")
        normalized = [indicator.strip().casefold() for indicator in self.prompt_injection_indicators]
        if any(not indicator for indicator in normalized):
            raise ValueError("prompt injection indicators must be non-empty")
        if normalized != sorted(set(normalized)):
            raise ValueError(
                "prompt injection indicators must be unique and canonically sorted case-insensitively"
            )
        return self


class DeterministicFallbackArtifact(StrictModel):
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    artifact_type: Literal["deterministic_normalized_document"] = "deterministic_normalized_document"


class AIResolution(StrictModel):
    schema_version: Literal["0.3.0"] = AI_SCHEMA_VERSION
    status: Literal["ai_selected", "deterministic_fallback"]
    selected_artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reasons: list[str] = Field(min_length=1)
    adapter_invoked: bool
    ai_artifact: AIExtractionArtifact | None = None
    requires_human_review: Literal[True] = True
    automation_authority: Literal[False] = False
    operational_side_effects_performed: Literal[False] = False

    @model_validator(mode="after")
    def validate_resolution(self) -> "AIResolution":
        if self.status == "ai_selected" and self.ai_artifact is None:
            raise ValueError("ai_selected resolution requires an AI artifact")
        if self.status == "deterministic_fallback" and self.ai_artifact is not None and not self.adapter_invoked:
            raise ValueError("non-invoked fallback cannot contain an AI artifact")
        return self


def request_digest(request: AIExtractionRequest) -> str:
    return canonical_digest(request.model_dump(mode="json"))


def artifact_digest(artifact: AIExtractionArtifact) -> str:
    return canonical_digest(artifact.model_dump(mode="json"))


def _response_payload_digest(response: AIAdapterResponse) -> str:
    payload = response.model_dump(mode="json")
    payload.pop("provider_response_sha256")
    return canonical_digest(payload)


def _validate_response_against_request(
    request: AIExtractionRequest,
    response: AIAdapterResponse,
) -> None:
    requested = set(request.requested_fields)
    page_count = len(request.pages)
    unexpected = sorted({field.field_name for field in response.fields} - requested)
    if unexpected:
        raise ValueError("AI adapter returned unrequested fields: " + ", ".join(unexpected))
    pages = {page.page_number: page.text for page in request.pages}
    for prediction in response.fields:
        if any(page < 1 or page > page_count for page in prediction.evidence_pages):
            raise ValueError(f"AI evidence page is outside request bounds for {prediction.field_name}")
        evidence_text = "\n".join(pages[page] for page in prediction.evidence_pages)
        expected_evidence_digest = _sha256(evidence_text.encode("utf-8"))
        if prediction.evidence_text_sha256 != expected_evidence_digest:
            raise ValueError(f"AI evidence digest does not bind cited pages for {prediction.field_name}")
    if response.provider_response_sha256 != _response_payload_digest(response):
        raise ValueError("AI recorded response digest does not match canonical response payload")


def run_ai_extraction(
    request: AIExtractionRequest,
    adapter: AIExtractionAdapter,
) -> AIExtractionArtifact:
    validated_request = AIExtractionRequest.model_validate(request.model_dump(mode="json"))
    identity = AIAdapterIdentity.model_validate(adapter.identity.model_dump(mode="json"))
    response = adapter.extract(validated_request)
    response = AIAdapterResponse.model_validate(response.model_dump(mode="json"))
    _validate_response_against_request(validated_request, response)
    return AIExtractionArtifact(
        request_sha256=request_digest(validated_request),
        adapter=identity,
        fields=response.fields,
        overall_confidence=response.overall_confidence,
        warnings=response.warnings,
        latency_ms=response.latency_ms,
        cost_usd=response.cost_usd,
        provider_response_sha256=response.provider_response_sha256,
    )


def _untrusted_instruction_matches(request: AIExtractionRequest, policy: AITrustPolicy) -> list[str]:
    text = "\n".join(page.text for page in request.pages).casefold()
    return sorted(
        {
            indicator.casefold()
            for indicator in policy.prompt_injection_indicators
            if indicator.casefold() in text
        }
    )


def resolve_ai_extraction(
    request: AIExtractionRequest,
    adapter: AIExtractionAdapter,
    policy: AITrustPolicy,
    fallback: DeterministicFallbackArtifact,
) -> AIResolution:
    """Select AI evidence only when the closed trust policy passes; otherwise fallback."""

    validated_request = AIExtractionRequest.model_validate(request.model_dump(mode="json"))
    active_policy = AITrustPolicy.model_validate(policy.model_dump(mode="json"))
    matches = _untrusted_instruction_matches(validated_request, active_policy)
    if matches:
        return AIResolution(
            status="deterministic_fallback",
            selected_artifact_sha256=fallback.artifact_sha256,
            reasons=["untrusted_instruction_detected:" + ",".join(matches)],
            adapter_invoked=False,
        )

    artifact = run_ai_extraction(validated_request, adapter)
    reasons: list[str] = []
    if artifact.overall_confidence < active_policy.minimum_overall_confidence:
        reasons.append("overall_confidence_below_threshold")

    predictions = {field.field_name: field for field in artifact.fields}
    required = active_policy.required_fields or validated_request.requested_fields
    missing = sorted(set(required) - predictions.keys())
    if missing:
        reasons.append("missing_required_fields:" + ",".join(missing))
    low_confidence = sorted(
        field_name
        for field_name in required
        if field_name in predictions
        and predictions[field_name].confidence < active_policy.minimum_field_confidence
    )
    if low_confidence:
        reasons.append("field_confidence_below_threshold:" + ",".join(low_confidence))

    if reasons:
        return AIResolution(
            status="deterministic_fallback",
            selected_artifact_sha256=fallback.artifact_sha256,
            reasons=reasons,
            adapter_invoked=True,
            ai_artifact=artifact,
        )

    return AIResolution(
        status="ai_selected",
        selected_artifact_sha256=artifact_digest(artifact),
        reasons=["closed_policy_passed"],
        adapter_invoked=True,
        ai_artifact=artifact,
    )
