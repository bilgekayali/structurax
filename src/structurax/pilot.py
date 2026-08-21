"""v0.4 controlled-pilot reference contracts and fail-closed readiness assessment."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from structurax.models import StrictModel

PILOT_SCHEMA_VERSION = "0.4.0"
REQUIRED_CHECKPOINTS = [
    "business_owner_approval",
    "privacy_review",
    "security_review",
    "workflow_owner_approval",
]


class DataHandlingProfile(StrictModel):
    schema_version: Literal["0.4.0"] = PILOT_SCHEMA_VERSION
    classification: Literal["pilot_restricted"] = "pilot_restricted"
    retention_days: int = Field(ge=1, le=3650)
    raw_document_text_in_audit: Literal[False] = False
    secrets_in_evidence: Literal[False] = False
    least_privilege_required: Literal[True] = True
    deletion_requires_authorized_human: Literal[True] = True


class AccessControlProfile(StrictModel):
    schema_version: Literal["0.4.0"] = PILOT_SCHEMA_VERSION
    default_deny: Literal[True] = True
    mfa_required_for_humans: Literal[True] = True
    service_accounts_no_human_login: Literal[True] = True
    tenant_boundary_required: Literal[True] = True
    break_glass_review_required: Literal[True] = True


class IncidentResponseProfile(StrictModel):
    schema_version: Literal["0.4.0"] = PILOT_SCHEMA_VERSION
    incident_owner_id: str = Field(min_length=3, max_length=120)
    security_incident_process_defined: Literal[True] = True
    privacy_incident_process_defined: Literal[True] = True
    ai_control_failure_process_defined: Literal[True] = True
    human_notification_required: Literal[True] = True
    automatic_external_notification_permitted: Literal[False] = False


class RollbackPlan(StrictModel):
    schema_version: Literal["0.4.0"] = PILOT_SCHEMA_VERSION
    rollback_owner_id: str = Field(min_length=3, max_length=120)
    backup_required: Literal[True] = True
    rollback_test_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    max_recovery_minutes: int = Field(ge=1, le=1440)
    automatic_rollback_without_human: Literal[False] = False


class HumanCheckpoint(StrictModel):
    checkpoint_id: str = Field(min_length=3, max_length=120)
    owner_id: str = Field(min_length=3, max_length=120)
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence_kind: Literal["synthetic_reference"] = "synthetic_reference"
    satisfied: bool


class PilotDeploymentPlan(StrictModel):
    schema_version: Literal["0.4.0"] = PILOT_SCHEMA_VERSION
    plan_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,79}$")
    workflow_policy_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    data_handling: DataHandlingProfile
    access_control: AccessControlProfile
    incident_response: IncidentResponseProfile
    rollback: RollbackPlan
    human_checkpoints: list[HumanCheckpoint] = Field(min_length=4, max_length=20)
    live_model_calls_permitted: Literal[False] = False
    automated_approval_permitted: Literal[False] = False
    deployment_performed: Literal[False] = False
    reference_only: Literal[True] = True

    @model_validator(mode="after")
    def validate_checkpoints(self) -> "PilotDeploymentPlan":
        ids = [item.checkpoint_id for item in self.human_checkpoints]
        if ids != sorted(set(ids)):
            raise ValueError("human checkpoints must be unique and canonically sorted")
        if ids != REQUIRED_CHECKPOINTS:
            raise ValueError("pilot plan must contain the exact required human checkpoints")
        return self


class RedTeamScenarioResult(StrictModel):
    scenario_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,119}$")
    expected_control: str = Field(min_length=3, max_length=300)
    observed_control: str = Field(min_length=3, max_length=300)
    passed: bool


class RedTeamReport(StrictModel):
    schema_version: Literal["0.4.0"] = PILOT_SCHEMA_VERSION
    exercise_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,79}$")
    synthetic_only: Literal[True] = True
    performed_at: datetime
    scenarios: list[RedTeamScenarioResult] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def canonical_scenarios(self) -> "RedTeamReport":
        ids = [item.scenario_id for item in self.scenarios]
        if ids != sorted(set(ids)):
            raise ValueError("red-team scenarios must be unique and canonically sorted")
        return self

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.scenarios)


class IndependentSecurityReview(StrictModel):
    schema_version: Literal["0.4.0"] = PILOT_SCHEMA_VERSION
    reviewed_repository_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewer_id: str = Field(min_length=3, max_length=160)
    reviewer_independence_confirmed: Literal[True] = True
    review_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    completed_at: datetime


class PilotReadinessAssessment(StrictModel):
    schema_version: Literal["0.4.0"] = PILOT_SCHEMA_VERSION
    plan_id: str
    eligible: bool
    reasons: list[str]
    red_team_passed: bool
    independent_security_review_present: bool
    all_human_checkpoints_satisfied: bool
    deployment_performed: Literal[False] = False
    automated_action_authority: Literal[False] = False
    reference_only: Literal[True] = True

    @model_validator(mode="after")
    def canonical_reasons(self) -> "PilotReadinessAssessment":
        if self.reasons != sorted(set(self.reasons)):
            raise ValueError("assessment reasons must be unique and canonically sorted")
        if self.eligible and self.reasons:
            raise ValueError("eligible assessment cannot contain blocking reasons")
        return self


def assess_pilot_readiness(
    plan: PilotDeploymentPlan,
    red_team: RedTeamReport,
    independent_review: IndependentSecurityReview | None = None,
    expected_repository_sha256: str | None = None,
) -> PilotReadinessAssessment:
    reasons: list[str] = []
    all_checkpoints = all(item.satisfied for item in plan.human_checkpoints)
    if not all_checkpoints:
        reasons.append("human_checkpoint_incomplete")
    if not red_team.passed:
        reasons.append("red_team_control_failure")
    if independent_review is None:
        reasons.append("independent_security_review_missing")
    elif expected_repository_sha256 is None:
        reasons.append("repository_digest_not_verified")
    elif independent_review.reviewed_repository_sha256 != expected_repository_sha256:
        reasons.append("independent_review_repository_digest_mismatch")
    return PilotReadinessAssessment(
        plan_id=plan.plan_id,
        eligible=not reasons,
        reasons=sorted(reasons),
        red_team_passed=red_team.passed,
        independent_security_review_present=independent_review is not None,
        all_human_checkpoints_satisfied=all_checkpoints,
    )
