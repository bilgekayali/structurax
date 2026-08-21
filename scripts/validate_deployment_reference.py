"""Validate bounded v1.0 deployment/observability reference controls."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from structurax.deployment_reference import DeploymentReferenceProfile, build_observability_record
from structurax.stable_reference import ObservabilityEvent


ROOT = Path(__file__).resolve().parents[1]


def load_profile(path: str | Path = "configs/deployment_reference.json") -> DeploymentReferenceProfile:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return DeploymentReferenceProfile.model_validate_json(candidate.read_text(encoding="utf-8"))


def validate_reference(profile: DeploymentReferenceProfile | None = None) -> dict[str, Any]:
    active = profile or load_profile()
    event = ObservabilityEvent(
        tenant_id="tenant-reference",
        trace_id="trace-reference",
        event_type="release_gate",
        artifact_sha256="a" * 64,
        occurred_at=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
        outcome="success",
    )
    record = build_observability_record(event)
    event_payload = record["event"]
    forbidden = {"raw_document_content", "prompt_content", "secret_content"}
    if forbidden & set(event_payload):
        raise SystemExit("deployment reference exported forbidden raw-content telemetry")
    if record["raw_content_exported"] is not False or record["production_export_performed"] is not False:
        raise SystemExit("deployment reference violated non-production observability semantics")

    return {
        "reference_validation": "passed",
        "schema_version": active.schema_version,
        "runtime_user": active.runtime_user,
        "run_as_non_root": active.run_as_non_root,
        "read_only_root_filesystem": active.read_only_root_filesystem,
        "outbound_network_default": active.outbound_network_default,
        "tls_minimum_version": active.tls_minimum_version,
        "database_tls_required": active.database_tls_required,
        "immutable_image_digest_required": active.immutable_image_digest_required,
        "secrets_delivery": active.secrets_delivery,
        "observability_event_sha256": record["event_sha256"],
        "raw_content_exported": False,
        "production_deployment_performed": active.production_deployment_performed,
        "production_controls_validated": active.production_controls_validated,
        "production_readiness_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate_reference(), indent=2, sort_keys=True))
