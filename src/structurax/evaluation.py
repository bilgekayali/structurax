"""Deterministic rule-family evaluation contracts for v0.2."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from structurax.models import StrictModel

RULE_FAMILY_BY_ID: dict[str, str] = {
    "ARITHMETIC_LINE_TOTAL": "arithmetic",
    "ARITHMETIC_SUBTOTAL": "arithmetic",
    "ARITHMETIC_TAX": "arithmetic",
    "ARITHMETIC_TOTAL": "arithmetic",
    "CURRENCY_MISMATCH": "cross_document",
    "UNIT_PRICE_VARIANCE": "cross_document",
    "INVOICE_EXCEEDS_DELIVERY": "cross_document",
    "BANK_ACCOUNT_CHANGE": "cross_document",
    "DUPLICATE_INVOICE": "duplicate",
    "MISSING_APPROVAL": "approval",
    "EMBEDDED_INSTRUCTION": "embedded_instruction",
}
RULE_FAMILIES: tuple[str, ...] = tuple(sorted(set(RULE_FAMILY_BY_ID.values())))


class RuleEvaluationCase(StrictModel):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,79}$")
    expected_rule_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def canonical_rules(self) -> "RuleEvaluationCase":
        if self.expected_rule_ids != sorted(set(self.expected_rule_ids)):
            raise ValueError("expected_rule_ids must be unique and canonically sorted")
        unknown = sorted(set(self.expected_rule_ids) - RULE_FAMILY_BY_ID.keys())
        if unknown:
            raise ValueError("unknown expected rule IDs: " + ", ".join(unknown))
        return self


class ObservedRuleCase(StrictModel):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,79}$")
    observed_rule_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def canonical_rules(self) -> "ObservedRuleCase":
        if self.observed_rule_ids != sorted(set(self.observed_rule_ids)):
            raise ValueError("observed_rule_ids must be unique and canonically sorted")
        unknown = sorted(set(self.observed_rule_ids) - RULE_FAMILY_BY_ID.keys())
        if unknown:
            raise ValueError("unknown observed rule IDs: " + ", ".join(unknown))
        return self


class RuleFamilyMetric(StrictModel):
    family: str
    true_positive: int = Field(ge=0)
    false_positive: int = Field(ge=0)
    false_negative: int = Field(ge=0)
    precision: float | None = Field(default=None, ge=0, le=1)
    recall: float | None = Field(default=None, ge=0, le=1)


class RuleEvaluationReport(StrictModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    case_count: int = Field(ge=1)
    metrics: list[RuleFamilyMetric]
    macro_precision: float | None = Field(default=None, ge=0, le=1)
    macro_recall: float | None = Field(default=None, ge=0, le=1)
    limitations: list[str]


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def evaluate_rule_families(
    expected_cases: list[RuleEvaluationCase],
    observed_cases: list[ObservedRuleCase],
) -> RuleEvaluationReport:
    if not expected_cases:
        raise ValueError("at least one labeled evaluation case is required")
    expected_by_id = {case.case_id: case for case in expected_cases}
    observed_by_id = {case.case_id: case for case in observed_cases}
    if len(expected_by_id) != len(expected_cases):
        raise ValueError("expected case IDs must be unique")
    if len(observed_by_id) != len(observed_cases):
        raise ValueError("observed case IDs must be unique")
    if set(expected_by_id) != set(observed_by_id):
        missing = sorted(set(expected_by_id) - set(observed_by_id))
        extra = sorted(set(observed_by_id) - set(expected_by_id))
        raise ValueError(f"evaluation case mismatch; missing={missing}, extra={extra}")

    counters = {family: [0, 0, 0] for family in RULE_FAMILIES}
    for case_id, expected_case in expected_by_id.items():
        observed_case = observed_by_id[case_id]
        expected_families = {RULE_FAMILY_BY_ID[rule_id] for rule_id in expected_case.expected_rule_ids}
        observed_families = {RULE_FAMILY_BY_ID[rule_id] for rule_id in observed_case.observed_rule_ids}
        for family in RULE_FAMILIES:
            expected = family in expected_families
            observed = family in observed_families
            if expected and observed:
                counters[family][0] += 1
            elif observed and not expected:
                counters[family][1] += 1
            elif expected and not observed:
                counters[family][2] += 1

    metrics: list[RuleFamilyMetric] = []
    precisions: list[float] = []
    recalls: list[float] = []
    for family in RULE_FAMILIES:
        tp, fp, fn = counters[family]
        precision = _ratio(tp, tp + fp)
        recall = _ratio(tp, tp + fn)
        if precision is not None:
            precisions.append(precision)
        if recall is not None:
            recalls.append(recall)
        metrics.append(
            RuleFamilyMetric(
                family=family,
                true_positive=tp,
                false_positive=fp,
                false_negative=fn,
                precision=precision,
                recall=recall,
            )
        )
    return RuleEvaluationReport(
        case_count=len(expected_cases),
        metrics=metrics,
        macro_precision=(round(sum(precisions) / len(precisions), 6) if precisions else None),
        macro_recall=(round(sum(recalls) / len(recalls), 6) if recalls else None),
        limitations=[
            "Metrics describe the committed synthetic/labeled evaluation cases only.",
            "They are regression evidence, not production fraud-detection accuracy claims.",
        ],
    )
