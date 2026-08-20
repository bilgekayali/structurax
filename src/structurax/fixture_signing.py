"""Ed25519 verification for committed v0.2 synthetic fixture manifests."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import Field, model_validator

from structurax.models import StrictModel


class FixtureEntry(StrictModel):
    path: str = Field(pattern=r"^datasets/ingestion/[a-zA-Z0-9._/-]+$")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    media_type: Literal["application/pdf", "application/json"]
    expected_outcome: Literal["accept", "reject"]
    expected_reason: str | None = Field(default=None, max_length=160)


class FixtureManifest(StrictModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    fixture_set_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,79}$")
    entries: list[FixtureEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def canonical_entries(self) -> "FixtureManifest":
        paths = [entry.path for entry in self.entries]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise ValueError("fixture entries must have unique canonically sorted paths")
        return self


def verify_manifest_signature(
    manifest_bytes: bytes,
    signature_b64: str,
    public_key_b64: str,
) -> None:
    try:
        signature = base64.b64decode(signature_b64.strip(), validate=True)
        public_key_bytes = base64.b64decode(public_key_b64.strip(), validate=True)
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(signature, manifest_bytes)
    except (ValueError, InvalidSignature) as exc:
        raise ValueError("fixture manifest Ed25519 signature verification failed") from exc


def verify_fixture_manifest(
    root: str | Path,
    manifest_path: str | Path,
    signature_path: str | Path,
    public_key_path: str | Path,
) -> FixtureManifest:
    root_path = Path(root).resolve()
    manifest_bytes = Path(manifest_path).read_bytes()
    verify_manifest_signature(
        manifest_bytes,
        Path(signature_path).read_text(encoding="ascii"),
        Path(public_key_path).read_text(encoding="ascii"),
    )
    manifest = FixtureManifest.model_validate(json.loads(manifest_bytes))
    for entry in manifest.entries:
        candidate = (root_path / entry.path).resolve()
        try:
            candidate.relative_to(root_path)
        except ValueError as exc:
            raise ValueError(f"fixture path escapes repository root: {entry.path}") from exc
        if not candidate.is_file():
            raise ValueError(f"fixture file is missing: {entry.path}")
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if digest != entry.sha256:
            raise ValueError(f"fixture digest mismatch: {entry.path}")
    return manifest
