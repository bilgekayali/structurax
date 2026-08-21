"""Fail-closed v0.2 ingestion boundary for untrusted synthetic PDF fixtures.

The core never performs OCR, network access, subprocess execution, or model calls.
Adapters must declare a closed sandbox profile and return bounded, typed extraction
artifacts with deterministic provenance.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from pydantic import Field, model_validator

from structurax.models import StrictModel

MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_PAGES = 200
MAX_PAGE_TEXT = 10_000
MAX_TOTAL_TEXT = 100_000
PDF_MEDIA_TYPE = "application/pdf"
FORBIDDEN_PDF_MARKERS: tuple[bytes, ...] = (
    b"/JavaScript",
    b"/JS",
    b"/Launch",
    b"/EmbeddedFile",
    b"/OpenAction",
    b"/AA",
    b"/RichMedia",
    b"/XFA",
    b"/Encrypt",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_digest(payload: object) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(raw)


class SandboxProfile(StrictModel):
    network_access: Literal[False] = False
    subprocess_access: Literal[False] = False
    filesystem_write_access: Literal[False] = False
    external_model_access: Literal[False] = False

    @model_validator(mode="after")
    def require_closed_profile(self) -> "SandboxProfile":
        if any(
            (
                self.network_access,
                self.subprocess_access,
                self.filesystem_write_access,
                self.external_model_access,
            )
        ):
            raise ValueError("v0.2 ingestion adapters must declare a closed sandbox profile")
        return self


class AdapterIdentity(StrictModel):
    adapter_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,79}$")
    adapter_version: str = Field(min_length=1, max_length=40)
    sandbox: SandboxProfile = Field(default_factory=SandboxProfile)


class ExtractedPage(StrictModel):
    page_number: int = Field(ge=1, le=MAX_PAGES)
    text: str = Field(max_length=MAX_PAGE_TEXT)
    ocr_used: bool = False


class AdapterExtraction(StrictModel):
    pages: list[ExtractedPage] = Field(min_length=1, max_length=MAX_PAGES)
    warnings: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_page_sequence_and_size(self) -> "AdapterExtraction":
        page_numbers = [page.page_number for page in self.pages]
        if page_numbers != list(range(1, len(self.pages) + 1)):
            raise ValueError("extracted pages must be contiguous and start at page 1")
        total = sum(len(page.text) for page in self.pages)
        if total > MAX_TOTAL_TEXT:
            raise ValueError("extracted text exceeds the v0.2 bounded text limit")
        return self


class IngestionProvenance(StrictModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_size_bytes: int = Field(ge=1, le=MAX_SOURCE_BYTES)
    source_media_type: Literal["application/pdf"] = PDF_MEDIA_TYPE
    adapter_id: str
    adapter_version: str
    adapter_config_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    extraction_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class IngestionArtifact(StrictModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    source_name: str = Field(min_length=1, max_length=200)
    pages: list[ExtractedPage] = Field(min_length=1, max_length=MAX_PAGES)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    provenance: IngestionProvenance
    external_execution_performed: Literal[False] = False
    requires_human_review: Literal[True] = True

    @model_validator(mode="after")
    def preserve_non_execution_boundary(self) -> "IngestionArtifact":
        if self.external_execution_performed:
            raise ValueError("v0.2 ingestion must not claim external execution")
        return self


class RecordedExtractionCatalog(StrictModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    adapter: AdapterIdentity
    extractions: dict[str, AdapterExtraction]

    @model_validator(mode="after")
    def validate_digest_keys(self) -> "RecordedExtractionCatalog":
        for digest in self.extractions:
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("recorded extraction keys must be lowercase SHA-256 digests")
        return self


@runtime_checkable
class DocumentIngestionAdapter(Protocol):
    @property
    def identity(self) -> AdapterIdentity: ...

    def extract(self, source_bytes: bytes, source_name: str) -> AdapterExtraction: ...


class RecordedExtractionAdapter:
    """Network-free adapter that replays committed synthetic extraction fixtures."""

    def __init__(self, catalog: RecordedExtractionCatalog) -> None:
        self._catalog = catalog

    @property
    def identity(self) -> AdapterIdentity:
        return self._catalog.adapter

    def extract(self, source_bytes: bytes, source_name: str) -> AdapterExtraction:
        digest = _sha256(source_bytes)
        try:
            return self._catalog.extractions[digest]
        except KeyError as exc:
            raise ValueError(
                f"no recorded extraction exists for source digest {digest} ({source_name})"
            ) from exc

    @classmethod
    def from_path(cls, path: str | Path) -> "RecordedExtractionAdapter":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(RecordedExtractionCatalog.model_validate(payload))


def inspect_pdf_bytes(source_bytes: bytes) -> None:
    if not source_bytes:
        raise ValueError("empty PDF input is rejected")
    if len(source_bytes) > MAX_SOURCE_BYTES:
        raise ValueError("PDF exceeds the v0.2 source-size limit")
    if not source_bytes.startswith(b"%PDF-"):
        raise ValueError("source does not have a PDF header")
    if not source_bytes.rstrip().endswith(b"%%EOF"):
        raise ValueError("PDF is truncated or has an invalid terminal marker")
    for marker in FORBIDDEN_PDF_MARKERS:
        if marker in source_bytes:
            raise ValueError(
                f"PDF contains unsupported active or opaque content marker {marker.decode('ascii')}"
            )


def ingest_pdf_bytes(
    source_bytes: bytes,
    source_name: str,
    adapter: DocumentIngestionAdapter,
) -> IngestionArtifact:
    """Preflight a PDF and bind adapter output to exact source/config provenance."""

    inspect_pdf_bytes(source_bytes)
    identity = AdapterIdentity.model_validate(adapter.identity.model_dump(mode="json"))
    extraction = adapter.extract(source_bytes, source_name)
    extraction = AdapterExtraction.model_validate(extraction.model_dump(mode="json"))
    source_digest = _sha256(source_bytes)
    adapter_digest = _canonical_digest(identity.model_dump(mode="json"))
    extraction_digest = _canonical_digest(extraction.model_dump(mode="json"))
    return IngestionArtifact(
        source_name=source_name,
        pages=extraction.pages,
        warnings=extraction.warnings,
        provenance=IngestionProvenance(
            source_sha256=source_digest,
            source_size_bytes=len(source_bytes),
            adapter_id=identity.adapter_id,
            adapter_version=identity.adapter_version,
            adapter_config_sha256=adapter_digest,
            extraction_sha256=extraction_digest,
        ),
    )


def ingest_pdf_path(
    source_path: str | Path,
    adapter: DocumentIngestionAdapter,
) -> IngestionArtifact:
    source = Path(source_path)
    return ingest_pdf_bytes(source.read_bytes(), source.name, adapter)
