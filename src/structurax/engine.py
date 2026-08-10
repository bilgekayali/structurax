"""Analysis orchestration and deterministic report metadata."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from structurax.models import (
    AnalysisReport,
    AnalysisSummary,
    Disposition,
    DocumentPack,
    Policy,
    Severity,
)
from structurax.rules import evaluate_rules


ENGINE_VERSION = "0.1.0"


def _input_hash(pack: DocumentPack) -> str:
    canonical = json.dumps(
        pack.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def analyze_pack(
    pack: DocumentPack,
    policy: Policy | None = None,
    *,
    generated_at: datetime | None = None,
) -> AnalysisReport:
    active_policy = policy or Policy()
    findings = evaluate_rules(pack, active_policy)
    severity_counts = {severity.value: 0 for severity in Severity}
    for finding in findings:
        severity_counts[finding.severity.value] += 1
    if severity_counts[Severity.CRITICAL.value]:
        disposition = Disposition.BLOCK
    elif findings:
        disposition = Disposition.REVIEW
    else:
        disposition = Disposition.ALLOW
    return AnalysisReport(
        engine_version=ENGINE_VERSION,
        pack_id=pack.pack_id,
        generated_at=generated_at or datetime.now(UTC),
        input_sha256=_input_hash(pack),
        policy_version=active_policy.policy_version,
        summary=AnalysisSummary(
            finding_count=len(findings),
            severity_counts=severity_counts,
            disposition=disposition,
            requires_human_review=bool(findings),
        ),
        findings=findings,
    )
