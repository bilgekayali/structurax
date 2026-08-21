"""Fail-closed v0.4 human review workflow and immutable audit-chain contracts."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from structurax.models import StrictModel

WORKFLOW_SCHEMA_VERSION = "0.4.0"


def canonical_digest(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class ReviewRole(str, Enum):
    REQUESTER = "requester"
    REVIEWER = "reviewer"
    APPROVER = "approver"
    SECURITY = "security"
    PRIVACY = "privacy"
    RELEASE_MANAGER = "release_manager"


class ReviewAction(str, Enum):
    SUBMIT = "submit"
    START_REVIEW = "start_review"
    REQUEST_CHANGES = "request_changes"
    APPROVE = "approve"
    REJECT = "reject"
    CANCEL = "cancel"


class WorkflowState(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ActorIdentity(StrictModel):
    actor_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._@-]{2,119}$")
    roles: list[ReviewRole] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def canonical_roles(self) -> "ActorIdentity":
        values = [role.value for role in self.roles]
        if values != sorted(set(values)):
            raise ValueError("actor roles must be unique and canonically sorted")
        return self


class WorkflowPolicy(StrictModel):
    schema_version: Literal["0.4.0"] = WORKFLOW_SCHEMA_VERSION
    policy_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,79}$")
    policy_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    authored_by: str = Field(min_length=3, max_length=120)
    approved_by: str = Field(min_length=3, max_length=120)
    change_ticket_id: str = Field(min_length=3, max_length=120)
    effective_at: datetime
    supersedes_policy_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    required_approval_roles: list[ReviewRole] = Field(default_factory=lambda: [ReviewRole.APPROVER])
    approval_owner_ids: list[str] = Field(default_factory=list, max_length=50)
    maker_checker_required: Literal[True] = True
    allow_self_approval: Literal[False] = False
    default_deny: Literal[True] = True

    @model_validator(mode="after")
    def validate_governance(self) -> "WorkflowPolicy":
        if self.authored_by == self.approved_by:
            raise ValueError("policy author and policy approver must be different humans")
        roles = [role.value for role in self.required_approval_roles]
        if roles != sorted(set(roles)):
            raise ValueError("required approval roles must be unique and canonically sorted")
        if self.approval_owner_ids != sorted(set(self.approval_owner_ids)):
            raise ValueError("approval_owner_ids must be unique and canonically sorted")
        return self


def policy_digest(policy: WorkflowPolicy) -> str:
    return canonical_digest(policy.model_dump(mode="json"))


def validate_policy_replacement(current: WorkflowPolicy, replacement: WorkflowPolicy) -> None:
    if replacement.policy_id != current.policy_id:
        raise ValueError("replacement policy_id must match current policy_id")
    if replacement.policy_version == current.policy_version:
        raise ValueError("replacement policy version must change")
    if replacement.supersedes_policy_sha256 != policy_digest(current):
        raise ValueError("replacement policy must bind the exact current policy digest")
    if replacement.effective_at <= current.effective_at:
        raise ValueError("replacement policy must become effective after current policy")


class ReviewCase(StrictModel):
    schema_version: Literal["0.4.0"] = WORKFLOW_SCHEMA_VERSION
    case_id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9._-]{2,79}$")
    subject_artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    policy_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_by: str = Field(min_length=3, max_length=120)
    created_at: datetime
    data_classification: Literal["synthetic", "pilot_restricted"] = "synthetic"
    requires_human_review: Literal[True] = True
    automation_authority: Literal[False] = False


class AuditEvent(StrictModel):
    schema_version: Literal["0.4.0"] = WORKFLOW_SCHEMA_VERSION
    case_id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9._-]{2,79}$")
    sequence: int = Field(ge=1)
    action: ReviewAction
    actor: ActorIdentity
    policy_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    occurred_at: datetime
    prior_event_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    event_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    raw_document_content_recorded: Literal[False] = False
    operational_side_effects_performed: Literal[False] = False


def event_digest(event: AuditEvent) -> str:
    payload = event.model_dump(mode="json")
    payload.pop("event_sha256")
    return canonical_digest(payload)


def verify_audit_chain(case: ReviewCase, events: list[AuditEvent]) -> None:
    previous: str | None = None
    for index, event in enumerate(events, start=1):
        if event.case_id != case.case_id:
            raise ValueError("audit event case_id does not match review case")
        if event.policy_sha256 != case.policy_sha256:
            raise ValueError("audit event policy digest does not match review case")
        if event.sequence != index:
            raise ValueError("audit event sequence must be contiguous and start at 1")
        if event.prior_event_sha256 != previous:
            raise ValueError("audit event prior hash does not match previous event")
        if event.event_sha256 != event_digest(event):
            raise ValueError("audit event digest does not match canonical event payload")
        previous = event.event_sha256


def derive_state(case: ReviewCase, events: list[AuditEvent]) -> WorkflowState:
    verify_audit_chain(case, events)
    state = WorkflowState.DRAFT
    for event in events:
        if event.action == ReviewAction.SUBMIT:
            state = WorkflowState.SUBMITTED
        elif event.action == ReviewAction.START_REVIEW:
            state = WorkflowState.IN_REVIEW
        elif event.action == ReviewAction.REQUEST_CHANGES:
            state = WorkflowState.CHANGES_REQUESTED
        elif event.action == ReviewAction.APPROVE:
            state = WorkflowState.APPROVED
        elif event.action == ReviewAction.REJECT:
            state = WorkflowState.REJECTED
        elif event.action == ReviewAction.CANCEL:
            state = WorkflowState.CANCELLED
    return state


def _require_role(actor: ActorIdentity, allowed: set[ReviewRole]) -> None:
    if not set(actor.roles) & allowed:
        raise ValueError("actor is not authorized for this workflow action")


def _authorize_transition(
    case: ReviewCase,
    state: WorkflowState,
    action: ReviewAction,
    actor: ActorIdentity,
    policy: WorkflowPolicy,
) -> None:
    if state in {WorkflowState.APPROVED, WorkflowState.REJECTED, WorkflowState.CANCELLED}:
        raise ValueError("terminal workflow state cannot transition")
    if action == ReviewAction.SUBMIT:
        if state not in {WorkflowState.DRAFT, WorkflowState.CHANGES_REQUESTED}:
            raise ValueError("submit is only valid from draft or changes_requested")
        _require_role(actor, {ReviewRole.REQUESTER})
        if actor.actor_id != case.created_by:
            raise ValueError("only the case creator may submit or resubmit")
        return
    if action == ReviewAction.START_REVIEW:
        if state != WorkflowState.SUBMITTED:
            raise ValueError("start_review requires submitted state")
        _require_role(actor, {ReviewRole.REVIEWER, ReviewRole.SECURITY, ReviewRole.PRIVACY})
        return
    if action == ReviewAction.REQUEST_CHANGES:
        if state not in {WorkflowState.SUBMITTED, WorkflowState.IN_REVIEW}:
            raise ValueError("request_changes requires submitted or in_review state")
        _require_role(actor, {ReviewRole.REVIEWER, ReviewRole.APPROVER, ReviewRole.SECURITY, ReviewRole.PRIVACY})
        return
    if action in {ReviewAction.APPROVE, ReviewAction.REJECT}:
        if state != WorkflowState.IN_REVIEW:
            raise ValueError("approve/reject requires in_review state")
        _require_role(actor, set(policy.required_approval_roles))
        if actor.actor_id == case.created_by:
            raise ValueError("maker-checker policy prohibits case creator self-approval")
        if policy.approval_owner_ids and actor.actor_id not in policy.approval_owner_ids:
            raise ValueError("actor is not an authorized approval owner")
        return
    if action == ReviewAction.CANCEL:
        if actor.actor_id != case.created_by:
            raise ValueError("only the case creator may cancel")
        _require_role(actor, {ReviewRole.REQUESTER})
        return
    raise ValueError("unsupported workflow action")


def append_audit_event(
    case: ReviewCase,
    events: list[AuditEvent],
    action: ReviewAction,
    actor: ActorIdentity,
    occurred_at: datetime,
    payload: dict[str, str],
    policy: WorkflowPolicy,
) -> AuditEvent:
    if case.policy_sha256 != policy_digest(policy):
        raise ValueError("review case does not bind the supplied workflow policy")
    state = derive_state(case, events)
    _authorize_transition(case, state, action, actor, policy)
    prior = events[-1].event_sha256 if events else None
    provisional = AuditEvent(
        case_id=case.case_id,
        sequence=len(events) + 1,
        action=action,
        actor=actor,
        policy_sha256=case.policy_sha256,
        occurred_at=occurred_at,
        prior_event_sha256=prior,
        payload_sha256=canonical_digest(payload),
        event_sha256="0" * 64,
    )
    return provisional.model_copy(update={"event_sha256": event_digest(provisional)})
