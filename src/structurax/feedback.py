"""Side-effect-free human-review feedback contracts for v0.2."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum

from pydantic import Field, model_validator

from structurax.models import StrictModel


class ReviewOutcome(str, Enum):
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    UNCERTAIN = "uncertain"


class HumanReviewFeedback(StrictModel):
    schema_version: str = "0.2.0"
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,79}$")
    finding_rule_id: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,79}$")
    source_report_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    outcome: ReviewOutcome
    reviewer_role: str = Field(min_length=1, max_length=80)
    rationale_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,79}$")
    notes: str | None = Field(default=None, max_length=500)
    recorded_at: datetime
    operational_side_effects_performed: bool = False

    @model_validator(mode="after")
    def reject_side_effect_claims(self) -> "HumanReviewFeedback":
        if self.operational_side_effects_performed:
            raise ValueError("feedback records must not claim operational side effects")
        return self


def feedback_digest(feedback: HumanReviewFeedback) -> str:
    canonical = json.dumps(
        feedback.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
