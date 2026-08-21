"""Generate committed JSON Schemas for StructuraX public evidence contracts."""

from __future__ import annotations

import json
from pathlib import Path

from structurax.evaluation import RuleEvaluationReport
from structurax.explanations import ReviewerExplanation
from structurax.feedback import HumanReviewFeedback
from structurax.fixture_signing import FixtureManifest
from structurax.ingestion import IngestionArtifact, RecordedExtractionCatalog
from structurax.models import DocumentPack

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "document-pack.schema.json": DocumentPack,
    "fixture-manifest.schema.json": FixtureManifest,
    "human-review-feedback.schema.json": HumanReviewFeedback,
    "ingestion-artifact.schema.json": IngestionArtifact,
    "recorded-extraction-catalog.schema.json": RecordedExtractionCatalog,
    "reviewer-explanation.schema.json": ReviewerExplanation,
    "rule-evaluation-report.schema.json": RuleEvaluationReport,
}


def main() -> None:
    target_dir = ROOT / "schemas"
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMAS.items():
        target = target_dir / filename
        target.write_text(
            json.dumps(
                model.model_json_schema(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
