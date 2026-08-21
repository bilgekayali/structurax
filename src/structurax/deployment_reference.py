"""Fail-closed deployment and observability reference controls for v1.0 preparation."""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict

from structurax.stable_reference import ObservabilityEvent


class DeploymentReferenceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0-rc1"] = "1.0-rc1"
    runtime_user: Literal["structurax"]
    run_as_non_root: Literal[True] = True
    read_only_root_filesystem: Literal[True] = True
    privileged: Literal[False] = False
    allow_privilege_escalation: Literal[False] = False
    outbound_network_default: Literal["deny"]
    tls_minimum_version: Literal["TLSv1.3"]
    database_tls_required: Literal[True] = True
    immutable_image_digest_required: Literal[True] = True
    dependency_install_at_runtime: Literal[False] = False
    secrets_delivery: Literal["external-reference-only"]
    evidence_key_material_in_config: Literal[False] = False
    observability_transport: Literal["otlp-https-reference"]
    raw_document_content_export_allowed: Literal[False] = False
    prompt_content_export_allowed: Literal[False] = False
    secret_content_export_allowed: Literal[False] = False
    production_deployment_performed: Literal[False] = False
    production_controls_validated: Literal[False] = False
    production_readiness_claimed: Literal[False] = False


def build_observability_record(event: ObservabilityEvent) -> dict[str, object]:
    """Return deterministic metadata-only telemetry suitable for a reference sink."""

    payload = event.model_dump(mode="json", exclude_none=True)
    forbidden = {"raw_document_content", "prompt_content", "secret_content"}
    if forbidden & payload.keys():
        raise ValueError("observability record contains forbidden raw-content fields")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema": "structurax-observability-reference/v1",
        "event": payload,
        "event_sha256": hashlib.sha256(canonical).hexdigest(),
        "raw_content_exported": False,
        "production_export_performed": False,
    }
