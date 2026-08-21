"""Build deterministic synthetic v0.4 workflow and pilot-reference fixtures."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from structurax.pilot import (
    AccessControlProfile,
    DataHandlingProfile,
    HumanCheckpoint,
    IncidentResponseProfile,
    PilotDeploymentPlan,
    RollbackPlan,
)
from structurax.review_workflow import (
    ActorIdentity,
    ReviewAction,
    ReviewCase,
    ReviewRole,
    WorkflowPolicy,
    append_audit_event,
    canonical_digest,
    policy_digest,
)

ROOT = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc)


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT)}")


def build_reference() -> tuple[WorkflowPolicy, ReviewCase, list, PilotDeploymentPlan]:
    policy = WorkflowPolicy(
        policy_id="controlled-pilot-review",
        policy_version="0.4.0",
        authored_by="synthetic-policy-author",
        approved_by="synthetic-policy-owner",
        change_ticket_id="SYNTHETIC-CHG-0400",
        effective_at=T0,
        required_approval_roles=[ReviewRole.APPROVER],
        approval_owner_ids=["synthetic-approver"],
    )
    case = ReviewCase(
        case_id="PILOT-CASE-001",
        subject_artifact_sha256=canonical_digest({"synthetic_artifact": "v0.3-ai-resolution"}),
        policy_sha256=policy_digest(policy),
        created_by="synthetic-maker",
        created_at=T0,
    )
    events = []
    actors = [
        (ReviewAction.SUBMIT, ActorIdentity(actor_id="synthetic-maker", roles=[ReviewRole.REQUESTER])),
        (ReviewAction.START_REVIEW, ActorIdentity(actor_id="synthetic-reviewer", roles=[ReviewRole.REVIEWER])),
        (ReviewAction.APPROVE, ActorIdentity(actor_id="synthetic-approver", roles=[ReviewRole.APPROVER])),
    ]
    for offset, (action, actor) in enumerate(actors, start=1):
        events.append(
            append_audit_event(
                case,
                events,
                action,
                actor,
                datetime(2026, 8, 21, 8, offset, tzinfo=timezone.utc),
                {"synthetic_action": action.value},
                policy,
            )
        )
    checkpoints = [
        HumanCheckpoint(
            checkpoint_id=checkpoint,
            owner_id=f"synthetic-{checkpoint}-owner",
            evidence_sha256=canonical_digest({"checkpoint": checkpoint, "synthetic": True}),
            satisfied=True,
        )
        for checkpoint in [
            "business_owner_approval",
            "privacy_review",
            "security_review",
            "workflow_owner_approval",
        ]
    ]
    plan = PilotDeploymentPlan(
        plan_id="synthetic-controlled-pilot",
        workflow_policy_sha256=policy_digest(policy),
        data_handling=DataHandlingProfile(retention_days=90),
        access_control=AccessControlProfile(),
        incident_response=IncidentResponseProfile(incident_owner_id="synthetic-security-owner"),
        rollback=RollbackPlan(
            rollback_owner_id="synthetic-release-owner",
            rollback_test_evidence_sha256=canonical_digest({"rollback": "synthetic-reference-test"}),
            max_recovery_minutes=30,
        ),
        human_checkpoints=checkpoints,
    )
    return policy, case, events, plan


def main() -> None:
    policy, case, events, plan = build_reference()
    _write(ROOT / "configs" / "pilot_policy.json", policy.model_dump(mode="json"))
    _write(ROOT / "configs" / "pilot_plan.json", plan.model_dump(mode="json"))
    _write(ROOT / "datasets" / "workflow" / "reference_case.json", case.model_dump(mode="json"))
    _write(ROOT / "datasets" / "workflow" / "reference_events.json", [event.model_dump(mode="json") for event in events])


if __name__ == "__main__":
    main()
