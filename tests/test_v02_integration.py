"""v0.2 sandboxed-ingestion, evaluation and review-contract tests."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from structurax.evaluation import ObservedRuleCase, RuleEvaluationCase, evaluate_rule_families
from structurax.explanations import ReviewerExplanation, reviewer_explanation, supported_explanation_rule_ids
from structurax.feedback import HumanReviewFeedback, ReviewOutcome, feedback_digest
from structurax.fixture_signing import verify_fixture_manifest
from structurax.ingestion import RecordedExtractionAdapter, SandboxProfile, ingest_pdf_path, inspect_pdf_bytes

ROOT = Path(__file__).resolve().parents[1]
INGESTION = ROOT / "datasets" / "ingestion"
EVALUATION = ROOT / "datasets" / "evaluation" / "rule_cases.json"


class V02IntegrationTests(unittest.TestCase):
    def test_signed_fixture_manifest_verifies_exact_files(self) -> None:
        manifest = verify_fixture_manifest(
            ROOT,
            INGESTION / "manifest.json",
            INGESTION / "manifest.sig",
            INGESTION / "manifest.pub",
        )
        self.assertEqual(manifest.fixture_set_id, "structurax-v0.2-ingestion")
        self.assertEqual(len(manifest.entries), 5)

    def test_manifest_verification_detects_fixture_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(INGESTION, temp_root / "datasets" / "ingestion")
            target = temp_root / "datasets" / "ingestion" / "clean-invoice.pdf"
            target.write_bytes(target.read_bytes() + b"tamper")
            with self.assertRaises(ValueError):
                verify_fixture_manifest(
                    temp_root,
                    temp_root / "datasets" / "ingestion" / "manifest.json",
                    temp_root / "datasets" / "ingestion" / "manifest.sig",
                    temp_root / "datasets" / "ingestion" / "manifest.pub",
                )

    def test_recorded_adapter_ingests_only_digest_bound_safe_fixtures(self) -> None:
        adapter = RecordedExtractionAdapter.from_path(INGESTION / "recorded_extractions.json")
        clean = ingest_pdf_path(INGESTION / "clean-invoice.pdf", adapter)
        injected = ingest_pdf_path(INGESTION / "embedded-instruction.pdf", adapter)
        self.assertFalse(clean.external_execution_performed)
        self.assertIn("Synthetic invoice INV-001", clean.pages[0].text)
        self.assertIn("Ignore prior instructions", injected.pages[0].text)
        self.assertTrue(injected.requires_human_review)

    def test_active_content_and_truncation_fail_closed_before_extraction(self) -> None:
        with self.assertRaises(ValueError):
            inspect_pdf_bytes((INGESTION / "active-content.pdf").read_bytes())
        with self.assertRaises(ValueError):
            inspect_pdf_bytes((INGESTION / "truncated.pdf").read_bytes())

    def test_rule_family_metrics_measure_false_positive_and_false_negative(self) -> None:
        expected = [
            RuleEvaluationCase(case_id="case-a", expected_rule_ids=["ARITHMETIC_TOTAL"]),
            RuleEvaluationCase(case_id="case-b", expected_rule_ids=["BANK_ACCOUNT_CHANGE"]),
        ]
        observed = [
            ObservedRuleCase(case_id="case-a", observed_rule_ids=[]),
            ObservedRuleCase(
                case_id="case-b",
                observed_rule_ids=["BANK_ACCOUNT_CHANGE", "DUPLICATE_INVOICE"],
            ),
        ]
        report = evaluate_rule_families(expected, observed)
        metrics = {metric.family: metric for metric in report.metrics}
        self.assertEqual(metrics["arithmetic"].false_negative, 1)
        self.assertEqual(metrics["duplicate"].false_positive, 1)
        self.assertEqual(metrics["cross_document"].true_positive, 1)

    def test_committed_evaluation_cases_are_canonical(self) -> None:
        payload = json.loads(EVALUATION.read_text(encoding="utf-8"))
        for case in payload["cases"]:
            RuleEvaluationCase(
                case_id=case["case_id"],
                expected_rule_ids=case["expected_rule_ids"],
            )

    def test_feedback_is_side_effect_free_and_digest_stable(self) -> None:
        feedback = HumanReviewFeedback(
            case_id="risky-pack",
            finding_rule_id="BANK_ACCOUNT_CHANGE",
            source_report_sha256="a" * 64,
            outcome=ReviewOutcome.CONFIRMED,
            reviewer_role="finance_reviewer",
            rationale_code="SOURCE_VERIFIED",
            recorded_at=datetime(2026, 8, 20, tzinfo=UTC),
        )
        self.assertFalse(feedback.operational_side_effects_performed)
        self.assertEqual(feedback_digest(feedback), feedback_digest(feedback))

    def test_all_current_rules_have_bilingual_reviewer_explanations(self) -> None:
        self.assertEqual(len(supported_explanation_rule_ids()), 11)
        for rule_id in supported_explanation_rule_ids():
            self.assertTrue(reviewer_explanation(rule_id, "en").review_action)
            self.assertTrue(reviewer_explanation(rule_id, "tr").review_action)

    def test_machine_contracts_reject_authority_and_side_effect_claims(self) -> None:
        with self.assertRaises(Exception):
            SandboxProfile(network_access=True)
        with self.assertRaises(Exception):
            ReviewerExplanation(
                rule_id="BANK_ACCOUNT_CHANGE",
                language="en",
                summary="review",
                review_action="review",
                automation_authority=True,
            )
        with self.assertRaises(Exception):
            HumanReviewFeedback(
                case_id="risky-pack",
                finding_rule_id="BANK_ACCOUNT_CHANGE",
                source_report_sha256="a" * 64,
                outcome=ReviewOutcome.CONFIRMED,
                reviewer_role="finance_reviewer",
                rationale_code="SOURCE_VERIFIED",
                recorded_at=datetime(2026, 8, 20, tzinfo=UTC),
                operational_side_effects_performed=True,
            )

    def test_machine_contract_schemas_encode_fail_closed_consts(self) -> None:
        sandbox_schema = SandboxProfile.model_json_schema()["properties"]
        self.assertIs(sandbox_schema["network_access"]["const"], False)
        self.assertIs(sandbox_schema["external_model_access"]["const"], False)
        explanation_schema = ReviewerExplanation.model_json_schema()["properties"]
        self.assertIs(explanation_schema["automation_authority"]["const"], False)
        self.assertEqual(explanation_schema["schema_version"]["const"], "0.2.0")
        feedback_schema = HumanReviewFeedback.model_json_schema()["properties"]
        self.assertIs(feedback_schema["operational_side_effects_performed"]["const"], False)
        self.assertEqual(feedback_schema["schema_version"]["const"], "0.2.0")


if __name__ == "__main__":
    unittest.main()
