"""Strict data contracts for synthetic construction document packs."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Reject unknown fields so evidence cannot silently change shape."""

    model_config = ConfigDict(extra="forbid")


class DocumentType(str, Enum):
    QUOTE = "quote"
    PURCHASE_ORDER = "purchase_order"
    DELIVERY_NOTE = "delivery_note"
    INVOICE = "invoice"


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Disposition(str, Enum):
    ALLOW = "allow"
    REVIEW = "review"
    BLOCK = "block"


class LineItem(StrictModel):
    item_code: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=300)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    line_total: Decimal = Field(ge=0)


class Approval(StrictModel):
    role: str = Field(min_length=1, max_length=80)
    status: ApprovalStatus
    recorded_at: datetime | None = None


class Document(StrictModel):
    document_id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9._-]{2,79}$")
    document_type: DocumentType
    external_reference: str = Field(min_length=1, max_length=120)
    issued_at: date
    supplier_id: str = Field(min_length=1, max_length=80)
    buyer_id: str = Field(min_length=1, max_length=80)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    line_items: list[LineItem] = Field(min_length=1)
    subtotal: Decimal = Field(ge=0)
    tax_rate_percent: Decimal = Field(ge=0, le=100)
    tax_amount: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)
    bank_account: str | None = Field(default=None, max_length=120)
    related_document_ids: list[str] = Field(default_factory=list)
    approvals: list[Approval] = Field(default_factory=list)
    extracted_text: str = Field(default="", max_length=20_000)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def item_codes_are_unique(self) -> "Document":
        codes = [item.item_code for item in self.line_items]
        if len(codes) != len(set(codes)):
            raise ValueError("line item codes must be unique within a document")
        return self


class DocumentPack(StrictModel):
    schema_version: str = "0.1.0"
    pack_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    project_id: str = Field(min_length=1, max_length=80)
    generated_at: datetime
    synthetic_data: bool
    documents: list[Document] = Field(min_length=1)

    @model_validator(mode="after")
    def enforce_synthetic_boundary_and_unique_ids(self) -> "DocumentPack":
        if not self.synthetic_data:
            raise ValueError(
                "v0.1 accepts synthetic data only; production documents are rejected"
            )
        document_ids = [document.document_id for document in self.documents]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("document IDs must be unique within a pack")
        known_ids = set(document_ids)
        unknown = sorted(
            {
                related_id
                for document in self.documents
                for related_id in document.related_document_ids
                if related_id not in known_ids
            }
        )
        if unknown:
            raise ValueError(
                "related document IDs must exist in the same pack: "
                + ", ".join(unknown)
            )
        return self


class Policy(StrictModel):
    policy_version: str = "0.1.0"
    amount_tolerance: Decimal = Field(default=Decimal("0.01"), ge=0)
    price_variance_percent: Decimal = Field(default=Decimal("5"), ge=0)
    high_value_threshold: Decimal = Field(default=Decimal("10000"), ge=0)
    required_approval_roles: list[str] = Field(
        default_factory=lambda: ["project_manager", "finance"]
    )
    prompt_injection_indicators: list[str] = Field(
        default_factory=lambda: [
            "ignore previous instructions",
            "ignore prior instructions",
            "system override",
            "approve without review",
            "önceki talimatları yok say",
            "sistem talimatını geçersiz kıl",
            "inceleme olmadan onayla",
        ]
    )


class EvidenceRef(StrictModel):
    document_id: str
    field: str
    observed: str
    expected: str | None = None


class Finding(StrictModel):
    rule_id: str
    severity: Severity
    title: str
    description: str
    evidence: list[EvidenceRef] = Field(min_length=1)
    recommendation: str
    requires_human_review: bool = True


class AnalysisSummary(StrictModel):
    finding_count: int = Field(ge=0)
    severity_counts: dict[str, int]
    disposition: Disposition
    requires_human_review: bool


class AnalysisReport(StrictModel):
    schema_version: str = "0.1.0"
    engine_version: str
    pack_id: str
    generated_at: datetime
    input_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    policy_version: str
    summary: AnalysisSummary
    findings: list[Finding]
