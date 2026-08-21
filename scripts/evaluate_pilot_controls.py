"""Run deterministic synthetic v0.4 red-team controls and pilot readiness gate."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from structurax.pilot import (
    PilotDeploymentPlan,
    RedTeamReport,
    RedTeamScenarioResult,
    assess_pilot_readiness,
)
from structurax.review_workflow import (
    ActorIdentity,
    AuditEvent,
    ReviewAction,
    ReviewCase,
    ReviewRole,
    WorkflowPolicy,
    append_audit_event,
    event_digest,
    validate_policy_replacement,
    verify_audit_chain,
    verify_audit_history,
)

ROOT = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 8, 21, 9, 0, tzinfo=timezone.utc)


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _result(
    scenario_id: str,
    expected: str,
    observed: str,
    passed: bool,
) -> RedTeamScenarioResult:
    return RedTeamScenarioResult(
        scenario_id=scenario_id,
        expected_control=expected,
        observed_control=observed,
        passed=passed,
    )


def run_exercise() -> RedTeamReport:
    policy = WorkflowPolicy.model_validate(
        _load(ROOT / "configs" / "pilot_policy.json")
    )
    case = ReviewCase.model_validate(
        _load(ROOT / "datasets" / "workflow" / "reference_case.json")
    )
    events = [
        AuditEvent.model_validate(item)
        for item in _load(
            ROOT / "datasets" / "workflow" / "reference_events.json"
        )
    ]
    verify_audit_history(case, events, policy)
    scenarios: list[RedTeamScenarioResult] = []

    tampered_payload = events[0].model_dump(mode="json")
    tampered_payload["payload_sha256"] = "f" * 64
    tampered = AuditEvent.model_validate(tampered_payload)
    try:
        verify_audit_chain(case, [tampered])
        tamper_blocked = False
    except ValueError:
        tamper_blocked = True
    scenarios.append(
        _result(
            "audit-chain-tampering",
            "tampered audit event rejected",
            (
                "tampered audit event rejected"
                if tamper_blocked
                else "tamper accepted"
            ),
            tamper_blocked,
        )
    )

    forged = events[2].model_copy(
        update={
            "actor": ActorIdentity(
                actor_id="synthetic-unowned-approver",
                roles=[ReviewRole.APPROVER],
            ),
            "event_sha256": "0" * 64,
        }
    )
    forged = forged.model_copy(
        update={"event_sha256": event_digest(forged)}
    )
    rehashed_history = [events[0], events[1], forged]
    try:
        verify_audit_chain(case, rehashed_history)
        structurally_valid = True
    except ValueError:
        structurally_valid = False
    try:
        verify_audit_history(case, rehashed_history, policy)
        semantic_blocked = False
    except ValueError:
        semantic_blocked = True
    semantic_replay_passed = structurally_valid and semantic_blocked
    scenarios.append(
        _result(
            "audit-semantic-replay-bypass",
            "rehashed history cannot bypass RBAC and approval ownership",
            (
                "rehash structurally valid but semantic replay rejected"
                if semantic_replay_passed
                else "semantic replay bypass not blocked"
            ),
            semantic_replay_passed,
        )
    )

    fresh_events = events[:2]
    try:
        append_audit_event(
            case,
            fresh_events,
            ReviewAction.APPROVE,
            ActorIdentity(
                actor_id=case.created_by,
                roles=[ReviewRole.APPROVER],
            ),
            T0,
            {"attempt": "self-approval"},
            policy,
        )
        self_blocked = False
    except ValueError:
        self_blocked = True
    scenarios.append(
        _result(
            "maker-checker-self-approval",
            "case creator cannot approve",
            "self approval blocked" if self_blocked else "self approval accepted",
            self_blocked,
        )
    )

    try:
        append_audit_event(
            case,
            fresh_events,
            ReviewAction.APPROVE,
            ActorIdentity(
                actor_id="synthetic-unowned-approver",
                roles=[ReviewRole.APPROVER],
            ),
            T0,
            {"attempt": "unowned-approval"},
            policy,
        )
        owner_blocked = False
    except ValueError:
        owner_blocked = True
    scenarios.append(
        _result(
            "unauthorized-approval-owner",
            "non-owner approver rejected",
            (
                "non-owner approver rejected"
                if owner_blocked
                else "non-owner approver accepted"
            ),
            owner_blocked,
        )
    )

    replacement_payload = policy.model_dump(mode="json")
    replacement_payload.update(
        {
            "policy_version": "0.4.1",
            "authored_by": "synthetic-policy-author-2",
            "approved_by": "synthetic-policy-owner-2",
            "change_ticket_id": "SYNTHETIC-CHG-0401",
            "effective_at": "2026-08-22T08:00:00Z",
            "supersedes_policy_sha256": "0" * 64,
        }
    )
    replacement = WorkflowPolicy.model_validate(replacement_payload)
    try:
        validate_policy_replacement(policy, replacement)
        stale_blocked = False
    except ValueError:
        stale_blocked = True
    scenarios.append(
        _result(
            "policy-substitution",
            "replacement must bind exact predecessor policy digest",
            (
                "stale policy substitution rejected"
                if stale_blocked
                else "stale policy accepted"
            ),
            stale_blocked,
        )
    )

    plan = PilotDeploymentPlan.model_validate(
        _load(ROOT / "configs" / "pilot_plan.json")
    )
    provisional = RedTeamReport(
        exercise_id="v0.4-independent-review-gate-probe",
        performed_at=T0,
        scenarios=[
            _result(
                "gate-probe",
                "gate remains closed",
                "gate remains closed",
                True,
            )
        ],
    )
    assessment = assess_pilot_readiness(plan, provisional)
    review_blocked = (
        not assessment.eligible
        and "independent_security_review_missing" in assessment.reasons
    )
    scenarios.append(
        _result(
            "independent-review-gate",
            "missing independent review blocks pilot eligibility",
            (
                "pilot eligibility blocked"
                if review_blocked
                else "pilot eligibility opened"
            ),
            review_blocked,
        )
    )

    return RedTeamReport(
        exercise_id="structurax-v0.4-synthetic-red-team",
        performed_at=T0,
        scenarios=sorted(scenarios, key=lambda item: item.scenario_id),
    )


def main() -> None:
    report = run_exercise()
    plan = PilotDeploymentPlan.model_validate(
        _load(ROOT / "configs" / "pilot_plan.json")
    )
    assessment = assess_pilot_readiness(plan, report)
    target = ROOT / "reports" / "evaluation" / "v0.4-red-team.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {target.relative_to(ROOT)}")
    readiness = (
        ROOT / "reports" / "evaluation" / "v0.4-pilot-readiness.json"
    )
    readiness.write_text(
        json.dumps(
            assessment.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {readiness.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
