"""Generate committed JSON Schemas for StructuraX public evidence contracts."""

from __future__ import annotations

import json
from pathlib import Path

from structurax.ai_adapters import AIExtractionRequest, AIResolution, AITrustPolicy, RecordedAIResponseCatalog
from structurax.ai_evaluation import AIBenchmarkSuite, AIAdapterBenchmarkReport
from structurax.evaluation import RuleEvaluationReport
from structurax.explanations import ReviewerExplanation
from structurax.feedback import HumanReviewFeedback
from structurax.fixture_signing import FixtureManifest
from structurax.ingestion import IngestionArtifact, RecordedExtractionCatalog
from structurax.models import DocumentPack
from structurax.pilot import (
    IndependentSecurityReview,
    PilotDeploymentPlan,
    PilotReadinessAssessment,
    RedTeamReport,
)
from structurax.review_workflow import AuditEvent, ReviewCase, WorkflowPolicy

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "ai-adapter-benchmark-report.schema.json": AIAdapterBenchmarkReport,
    "ai-benchmark-suite.schema.json": AIBenchmarkSuite,
    "ai-extraction-request.schema.json": AIExtractionRequest,
    "ai-resolution.schema.json": AIResolution,
    "ai-trust-policy.schema.json": AITrustPolicy,
    "audit-event.schema.json": AuditEvent,
    "document-pack.schema.json": DocumentPack,
    "fixture-manifest.schema.json": FixtureManifest,
    "human-review-feedback.schema.json": HumanReviewFeedback,
    "independent-security-review.schema.json": IndependentSecurityReview,
    "ingestion-artifact.schema.json": IngestionArtifact,
    "pilot-deployment-plan.schema.json": PilotDeploymentPlan,
    "pilot-readiness-assessment.schema.json": PilotReadinessAssessment,
    "recorded-ai-response-catalog.schema.json": RecordedAIResponseCatalog,
    "recorded-extraction-catalog.schema.json": RecordedExtractionCatalog,
    "red-team-report.schema.json": RedTeamReport,
    "review-case.schema.json": ReviewCase,
    "reviewer-explanation.schema.json": ReviewerExplanation,
    "rule-evaluation-report.schema.json": RuleEvaluationReport,
    "workflow-policy.schema.json": WorkflowPolicy,
}


def main() -> None:
    target_dir = ROOT / "schemas"
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMAS.items():
        target = target_dir / filename
        target.write_text(
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
