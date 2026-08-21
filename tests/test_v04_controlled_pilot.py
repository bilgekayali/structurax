import unittest
from datetime import datetime, timezone

from structurax.pilot import (
    AccessControlProfile, DataHandlingProfile, HumanCheckpoint, IncidentResponseProfile,
    PilotDeploymentPlan, RedTeamReport, RedTeamScenarioResult, RollbackPlan, assess_pilot_readiness,
)
from structurax.review_workflow import (
    ActorIdentity, ReviewAction, ReviewCase, ReviewRole, WorkflowPolicy,
    append_audit_event, derive_state, policy_digest, verify_audit_chain, WorkflowState,
    validate_policy_replacement,
)

D = lambda ch: ch * 64
T0 = datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc)


class V04Tests(unittest.TestCase):
    def policy(self):
        return WorkflowPolicy(
            policy_id="pilot-review",
            policy_version="0.4.0",
            authored_by="policy-author",
            approved_by="policy-owner",
            change_ticket_id="CHG-0400",
            effective_at=T0,
            required_approval_roles=[ReviewRole.APPROVER],
            approval_owner_ids=["approver-1"],
        )

    def case(self, policy):
        return ReviewCase(
            case_id="CASE-001",
            subject_artifact_sha256=D("a"),
            policy_sha256=policy_digest(policy),
            created_by="maker-1",
            created_at=T0,
        )

    def actor(self, actor_id, role):
        return ActorIdentity(actor_id=actor_id, roles=[role])

    def test_maker_checker_blocks_self_approval(self):
        p = self.policy(); c = self.case(p); events=[]
        events.append(append_audit_event(c, events, ReviewAction.SUBMIT, self.actor("maker-1", ReviewRole.REQUESTER), T0, {"x":"1"}, p))
        events.append(append_audit_event(c, events, ReviewAction.START_REVIEW, self.actor("reviewer-1", ReviewRole.REVIEWER), T0, {"x":"2"}, p))
        with self.assertRaisesRegex(ValueError, "self-approval"):
            append_audit_event(c, events, ReviewAction.APPROVE, ActorIdentity(actor_id="maker-1", roles=[ReviewRole.APPROVER]), T0, {"x":"3"}, p)

    def test_approval_owner_is_enforced(self):
        p = self.policy(); c = self.case(p); events=[]
        events.append(append_audit_event(c, events, ReviewAction.SUBMIT, self.actor("maker-1", ReviewRole.REQUESTER), T0, {}, p))
        events.append(append_audit_event(c, events, ReviewAction.START_REVIEW, self.actor("reviewer-1", ReviewRole.REVIEWER), T0, {}, p))
        with self.assertRaisesRegex(ValueError, "approval owner"):
            append_audit_event(c, events, ReviewAction.APPROVE, self.actor("approver-2", ReviewRole.APPROVER), T0, {}, p)

    def test_valid_chain_reaches_approved(self):
        p = self.policy(); c = self.case(p); events=[]
        for action, actor in [
            (ReviewAction.SUBMIT, self.actor("maker-1", ReviewRole.REQUESTER)),
            (ReviewAction.START_REVIEW, self.actor("reviewer-1", ReviewRole.REVIEWER)),
            (ReviewAction.APPROVE, self.actor("approver-1", ReviewRole.APPROVER)),
        ]:
            events.append(append_audit_event(c, events, action, actor, T0, {"action":action.value}, p))
        verify_audit_chain(c, events)
        self.assertEqual(derive_state(c, events), WorkflowState.APPROVED)
        self.assertTrue(all(not e.raw_document_content_recorded for e in events))
        self.assertTrue(all(not e.operational_side_effects_performed for e in events))

    def test_tampered_chain_fails(self):
        p = self.policy(); c = self.case(p); events=[]
        events.append(append_audit_event(c, events, ReviewAction.SUBMIT, self.actor("maker-1", ReviewRole.REQUESTER), T0, {}, p))
        payload = events[0].model_dump(mode="json"); payload["payload_sha256"] = D("b")
        tampered = [events[0].__class__.model_validate(payload)]
        with self.assertRaisesRegex(ValueError, "digest"):
            verify_audit_chain(c, tampered)

    def test_policy_replacement_binds_exact_predecessor(self):
        current = self.policy()
        replacement = WorkflowPolicy(
            policy_id=current.policy_id, policy_version="0.4.1", authored_by="author-2", approved_by="owner-2",
            change_ticket_id="CHG-0401", effective_at=datetime(2026,8,22,tzinfo=timezone.utc),
            supersedes_policy_sha256=policy_digest(current), required_approval_roles=[ReviewRole.APPROVER], approval_owner_ids=["approver-1"])
        validate_policy_replacement(current, replacement)
        bad = replacement.model_copy(update={"supersedes_policy_sha256": D("f")})
        with self.assertRaisesRegex(ValueError, "exact current policy digest"):
            validate_policy_replacement(current, bad)

    def plan(self):
        cps=[HumanCheckpoint(checkpoint_id=x, owner_id=f"{x}-owner", evidence_sha256=D(str(i+1)), satisfied=True) for i,x in enumerate([
            "business_owner_approval","privacy_review","security_review","workflow_owner_approval"])]
        return PilotDeploymentPlan(
            plan_id="synthetic-pilot", workflow_policy_sha256=D("a"),
            data_handling=DataHandlingProfile(retention_days=90), access_control=AccessControlProfile(),
            incident_response=IncidentResponseProfile(incident_owner_id="security-owner"),
            rollback=RollbackPlan(rollback_owner_id="release-owner", rollback_test_evidence_sha256=D("e"), max_recovery_minutes=30),
            human_checkpoints=cps)

    def red(self, passed=True):
        return RedTeamReport(exercise_id="v0.4-red-team", synthetic_only=True, performed_at=T0,
            scenarios=[RedTeamScenarioResult(scenario_id="maker-checker", expected_control="self approval blocked", observed_control="self approval blocked", passed=passed)])

    def test_missing_independent_review_blocks_pilot(self):
        assessment=assess_pilot_readiness(self.plan(), self.red())
        self.assertFalse(assessment.eligible)
        self.assertEqual(assessment.reasons,["independent_security_review_missing"])
        self.assertFalse(assessment.deployment_performed)
        self.assertFalse(assessment.automated_action_authority)

    def test_red_team_failure_blocks_pilot(self):
        a=assess_pilot_readiness(self.plan(), self.red(False))
        self.assertEqual(a.reasons,["independent_security_review_missing","red_team_control_failure"])

    def test_policy_author_cannot_self_approve_policy(self):
        with self.assertRaisesRegex(ValueError, "different humans"):
            WorkflowPolicy(
                policy_id="pilot-review", policy_version="0.4.0", authored_by="same-human",
                approved_by="same-human", change_ticket_id="CHG-1", effective_at=T0,
                required_approval_roles=[ReviewRole.APPROVER])

    def test_pilot_plan_cannot_enable_live_or_automated_execution(self):
        payload = self.plan().model_dump(mode="json")
        payload["live_model_calls_permitted"] = True
        with self.assertRaises(Exception):
            PilotDeploymentPlan.model_validate(payload)
        payload = self.plan().model_dump(mode="json")
        payload["automated_approval_permitted"] = True
        with self.assertRaises(Exception):
            PilotDeploymentPlan.model_validate(payload)

    def test_audit_event_cannot_claim_raw_content_or_side_effects(self):
        p = self.policy(); c = self.case(p); events=[]
        event = append_audit_event(c, events, ReviewAction.SUBMIT, self.actor("maker-1", ReviewRole.REQUESTER), T0, {}, p)
        payload = event.model_dump(mode="json"); payload["raw_document_content_recorded"] = True
        with self.assertRaises(Exception):
            event.__class__.model_validate(payload)
        payload = event.model_dump(mode="json"); payload["operational_side_effects_performed"] = True
        with self.assertRaises(Exception):
            event.__class__.model_validate(payload)

    def test_independent_review_must_bind_expected_repository_digest(self):
        from structurax.pilot import IndependentSecurityReview
        review = IndependentSecurityReview(
            reviewed_repository_sha256=D("f"), reviewer_id="synthetic-independent-reviewer",
            reviewer_independence_confirmed=True, review_evidence_sha256=D("e"), completed_at=T0)
        a = assess_pilot_readiness(self.plan(), self.red(), review, expected_repository_sha256=D("d"))
        self.assertFalse(a.eligible)
        self.assertEqual(a.reasons, ["independent_review_repository_digest_mismatch"])

    def test_matching_review_can_open_reference_gate(self):
        from structurax.pilot import IndependentSecurityReview
        review = IndependentSecurityReview(
            reviewed_repository_sha256=D("d"), reviewer_id="synthetic-independent-reviewer",
            reviewer_independence_confirmed=True, review_evidence_sha256=D("e"), completed_at=T0)
        a = assess_pilot_readiness(self.plan(), self.red(), review, expected_repository_sha256=D("d"))
        self.assertTrue(a.eligible)
        self.assertEqual(a.reasons, [])


if __name__ == '__main__': unittest.main()
