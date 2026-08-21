"""Synthetic v0.3 evaluation for offline recorded AI adapters."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from structurax.ai_adapters import (
    AIExtractionAdapter,
    AIExtractionRequest,
    AITrustPolicy,
    DeterministicFallbackArtifact,
    resolve_ai_extraction,
)
from structurax.models import StrictModel


class ExpectedAIField(StrictModel):
    field_name: str = Field(min_length=1, max_length=120)
    value: str = Field(max_length=5_000)
    evidence_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class AIBenchmarkCase(StrictModel):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,79}$")
    request: AIExtractionRequest
    expected_fields: list[ExpectedAIField]
    fallback: DeterministicFallbackArtifact

    @model_validator(mode="after")
    def validate_case(self) -> "AIBenchmarkCase":
        names = [field.field_name for field in self.expected_fields]
        if names != sorted(set(names)):
            raise ValueError("expected AI fields must be unique and canonically sorted")
        if not set(names) <= set(self.request.requested_fields):
            raise ValueError("expected AI fields must be a subset of requested_fields")
        return self


class AIBenchmarkSuite(StrictModel):
    schema_version: Literal["0.3.0"] = "0.3.0"
    cases: list[AIBenchmarkCase] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_cases(self) -> "AIBenchmarkSuite":
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("AI benchmark case IDs must be unique")
        return self


class AIAdapterBenchmarkMetric(StrictModel):
    adapter_id: str
    provider_label: str
    model_label: str
    case_count: int = Field(ge=1)
    invocation_count: int = Field(ge=0)
    fallback_count: int = Field(ge=0)
    expected_field_count: int = Field(ge=0)
    exact_field_match_count: int = Field(ge=0)
    evidence_match_count: int = Field(ge=0)
    exact_field_accuracy: float | None = Field(default=None, ge=0, le=1)
    evidence_fidelity: float | None = Field(default=None, ge=0, le=1)
    average_latency_ms: float | None = Field(default=None, ge=0)
    total_cost_usd: float = Field(ge=0)
    average_cost_usd: float | None = Field(default=None, ge=0)


class AIAdapterBenchmarkReport(StrictModel):
    schema_version: Literal["0.3.0"] = "0.3.0"
    metrics: list[AIAdapterBenchmarkMetric] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    live_model_calls_performed: Literal[False] = False


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def evaluate_ai_adapters(
    suite: AIBenchmarkSuite,
    adapters: list[AIExtractionAdapter],
    policy: AITrustPolicy,
) -> AIAdapterBenchmarkReport:
    if not adapters:
        raise ValueError("at least one AI adapter is required")
    adapter_ids = [adapter.identity.adapter_id for adapter in adapters]
    if len(adapter_ids) != len(set(adapter_ids)):
        raise ValueError("AI adapter IDs must be unique in a benchmark run")

    metrics: list[AIAdapterBenchmarkMetric] = []
    for adapter in sorted(adapters, key=lambda item: item.identity.adapter_id):
        expected_count = 0
        exact_count = 0
        evidence_count = 0
        invocation_count = 0
        fallback_count = 0
        latencies: list[int] = []
        costs: list[float] = []

        for case in suite.cases:
            resolution = resolve_ai_extraction(case.request, adapter, policy, case.fallback)
            if resolution.adapter_invoked:
                invocation_count += 1
            if resolution.status == "deterministic_fallback":
                fallback_count += 1
            artifact = resolution.ai_artifact
            if artifact is not None:
                latencies.append(artifact.latency_ms)
                costs.append(artifact.cost_usd)
            predictions = (
                {field.field_name: field for field in artifact.fields}
                if artifact is not None and resolution.status == "ai_selected"
                else {}
            )
            for expected in case.expected_fields:
                expected_count += 1
                prediction = predictions.get(expected.field_name)
                if prediction is not None and prediction.value == expected.value:
                    exact_count += 1
                if (
                    prediction is not None
                    and prediction.evidence_text_sha256 == expected.evidence_text_sha256
                ):
                    evidence_count += 1

        total_cost = round(sum(costs), 6)
        identity = adapter.identity
        metrics.append(
            AIAdapterBenchmarkMetric(
                adapter_id=identity.adapter_id,
                provider_label=identity.provider_label,
                model_label=identity.model_label,
                case_count=len(suite.cases),
                invocation_count=invocation_count,
                fallback_count=fallback_count,
                expected_field_count=expected_count,
                exact_field_match_count=exact_count,
                evidence_match_count=evidence_count,
                exact_field_accuracy=_ratio(exact_count, expected_count),
                evidence_fidelity=_ratio(evidence_count, expected_count),
                average_latency_ms=(round(sum(latencies) / len(latencies), 3) if latencies else None),
                total_cost_usd=total_cost,
                average_cost_usd=(round(total_cost / len(costs), 6) if costs else None),
            )
        )

    return AIAdapterBenchmarkReport(
        metrics=metrics,
        limitations=[
            "Metrics describe committed synthetic recorded responses only.",
            "Provider and model labels are synthetic references, not vendor performance claims.",
            "No live model, network, tool, or production document call is performed by this benchmark.",
        ],
    )
