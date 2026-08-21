"""Strict v0.5 construction-intelligence evidence contracts."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from structurax.models import Severity, StrictModel

CONSTRUCTION_SCHEMA_VERSION = "0.5.0"
MONEY = Decimal("0.01")
QTY = Decimal("0.001")


def qmoney(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def qqty(value: Decimal) -> Decimal:
    return value.quantize(QTY, rounding=ROUND_HALF_UP)


def canonical_digest(payload: object) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class ArtifactType(str, Enum):
    BOQ = "boq"
    CONTRACT = "contract"
    VARIATION_ORDER = "variation_order"
    PURCHASE_ORDER = "purchase_order"
    DELIVERY = "delivery"
    INVOICE = "invoice"


class LineageRelation(str, Enum):
    AUTHORIZES = "authorizes"
    AMENDS = "amends"
    ORDERS_AGAINST = "orders_against"
    FULFILLS = "fulfills"
    INVOICES_AGAINST = "invoices_against"


class VariationStatus(str, Enum):
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"


class MatchStatus(str, Enum):
    MATCHED = "matched"
    REVIEW = "review"
    BLOCK = "block"


class LineageNode(StrictModel):
    artifact_id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9._-]{2,79}$")
    artifact_type: ArtifactType
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class LineageEdge(StrictModel):
    from_artifact_id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9._-]{2,79}$")
    to_artifact_id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9._-]{2,79}$")
    relation: LineageRelation

    @model_validator(mode="after")
    def no_self_edge(self) -> "LineageEdge":
        if self.from_artifact_id == self.to_artifact_id:
            raise ValueError("lineage self-edges are not permitted")
        return self


class BOQLine(StrictModel):
    artifact_id: str
    item_code: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=300)
    unit: str = Field(min_length=1, max_length=30)
    budget_quantity: Decimal = Field(gt=0)
    budget_unit_rate: Decimal = Field(ge=0)
    budget_amount: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def arithmetic(self) -> "BOQLine":
        expected = qmoney(self.budget_quantity * self.budget_unit_rate)
        if qmoney(self.budget_amount) != expected:
            raise ValueError("BOQ budget_amount must equal quantity times unit rate")
        return self


class ContractLine(StrictModel):
    artifact_id: str
    supplier_id: str = Field(min_length=1, max_length=80)
    item_code: str = Field(min_length=1, max_length=80)
    unit: str = Field(min_length=1, max_length=30)
    contracted_quantity: Decimal = Field(gt=0)
    unit_rate: Decimal = Field(ge=0)


class VariationOrderLine(StrictModel):
    artifact_id: str
    variation_id: str = Field(min_length=1, max_length=80)
    supplier_id: str = Field(min_length=1, max_length=80)
    item_code: str = Field(min_length=1, max_length=80)
    status: VariationStatus
    quantity_delta: Decimal
    revised_unit_rate: Decimal | None = Field(default=None, ge=0)
    effective_at: date
    approval_evidence_sha256: str | None = Field(
        default=None,
        pattern=r"^[a-f0-9]{64}$",
    )

    @model_validator(mode="after")
    def approved_requires_evidence(self) -> "VariationOrderLine":
        if self.status == VariationStatus.APPROVED and self.approval_evidence_sha256 is None:
            raise ValueError("approved variation orders require approval evidence")
        if self.status != VariationStatus.APPROVED and self.approval_evidence_sha256 is not None:
            raise ValueError("non-approved variation orders cannot carry approval evidence")
        return self


class PurchaseOrderLine(StrictModel):
    artifact_id: str
    supplier_id: str = Field(min_length=1, max_length=80)
    item_code: str = Field(min_length=1, max_length=80)
    quantity: Decimal = Field(gt=0)
    unit_rate: Decimal = Field(ge=0)


class DeliveryLine(StrictModel):
    artifact_id: str
    supplier_id: str = Field(min_length=1, max_length=80)
    item_code: str = Field(min_length=1, max_length=80)
    quantity: Decimal = Field(gt=0)


class InvoiceLine(StrictModel):
    artifact_id: str
    supplier_id: str = Field(min_length=1, max_length=80)
    item_code: str = Field(min_length=1, max_length=80)
    quantity: Decimal = Field(gt=0)
    unit_rate: Decimal = Field(ge=0)


class SupplierPriceObservation(StrictModel):
    supplier_id: str = Field(min_length=1, max_length=80)
    item_code: str = Field(min_length=1, max_length=80)
    observed_at: date
    unit_rate: Decimal = Field(gt=0)
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class ConstructionPolicy(StrictModel):
    schema_version: Literal["0.5.0"] = CONSTRUCTION_SCHEMA_VERSION
    quantity_tolerance: Decimal = Field(default=Decimal("0.001"), ge=0)
    rate_tolerance_percent: Decimal = Field(default=Decimal("2.5"), ge=0, le=100)
    supplier_anomaly_percent: Decimal = Field(default=Decimal("20"), ge=0, le=1000)
    minimum_supplier_history: int = Field(default=3, ge=3, le=100)
    project_budget_variance_percent: Decimal = Field(default=Decimal("5"), ge=0, le=1000)


class ConstructionIntelligenceCase(StrictModel):
    schema_version: Literal["0.5.0"] = CONSTRUCTION_SCHEMA_VERSION
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    project_id: str = Field(min_length=1, max_length=80)
    generated_at: datetime
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    synthetic_data: Literal[True] = True
    lineage_nodes: list[LineageNode] = Field(min_length=1)
    lineage_edges: list[LineageEdge] = Field(default_factory=list)
    boq_lines: list[BOQLine] = Field(min_length=1)
    contract_lines: list[ContractLine] = Field(min_length=1)
    variation_orders: list[VariationOrderLine] = Field(default_factory=list)
    purchase_orders: list[PurchaseOrderLine] = Field(min_length=1)
    deliveries: list[DeliveryLine] = Field(min_length=1)
    invoices: list[InvoiceLine] = Field(min_length=1)
    supplier_price_history: list[SupplierPriceObservation] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_case(self) -> "ConstructionIntelligenceCase":
        node_ids = [node.artifact_id for node in self.lineage_nodes]
        if node_ids != sorted(set(node_ids)):
            raise ValueError("lineage nodes must be unique and canonically sorted")
        known = set(node_ids)
        node_types = {node.artifact_id: node.artifact_type for node in self.lineage_nodes}
        for edge in self.lineage_edges:
            if edge.from_artifact_id not in known or edge.to_artifact_id not in known:
                raise ValueError("lineage edges must reference known artifacts")
        edge_keys = [
            (edge.from_artifact_id, edge.to_artifact_id, edge.relation.value)
            for edge in self.lineage_edges
        ]
        if edge_keys != sorted(set(edge_keys)):
            raise ValueError("lineage edges must be unique and canonically sorted")
        expected_types = (
            ("boq_lines", self.boq_lines, ArtifactType.BOQ),
            ("contract_lines", self.contract_lines, ArtifactType.CONTRACT),
            ("variation_orders", self.variation_orders, ArtifactType.VARIATION_ORDER),
            ("purchase_orders", self.purchase_orders, ArtifactType.PURCHASE_ORDER),
            ("deliveries", self.deliveries, ArtifactType.DELIVERY),
            ("invoices", self.invoices, ArtifactType.INVOICE),
        )
        for group_name, values, expected_type in expected_types:
            keys: list[tuple[str, str, str]] = []
            for value in values:
                if value.artifact_id not in known:
                    raise ValueError(f"{group_name} artifact_id must exist in lineage nodes")
                if node_types[value.artifact_id] != expected_type:
                    raise ValueError(
                        f"{group_name} artifact_id must reference a {expected_type.value} lineage node"
                    )
                supplier = getattr(value, "supplier_id", "")
                keys.append((value.artifact_id, supplier, value.item_code))
            if keys != sorted(set(keys)):
                raise ValueError(f"{group_name} lines must be unique and canonically sorted")
        contract_keys = [(line.supplier_id, line.item_code) for line in self.contract_lines]
        if contract_keys != sorted(set(contract_keys)):
            raise ValueError("contract authority must be unique per supplier and item_code")
        boq_keys = [line.item_code for line in self.boq_lines]
        if boq_keys != sorted(set(boq_keys)):
            raise ValueError("BOQ item codes must be unique and canonically sorted")
        return self


class ConstructionEvidenceRef(StrictModel):
    artifact_id: str
    field: str
    observed: str
    expected: str | None = None


class ConstructionFinding(StrictModel):
    rule_id: str
    severity: Severity
    title: str
    description: str
    evidence: list[ConstructionEvidenceRef] = Field(min_length=1)
    recommendation: str
    requires_human_review: Literal[True] = True


class MatchResult(StrictModel):
    invoice_artifact_id: str
    supplier_id: str
    item_code: str
    status: MatchStatus
    three_way_complete: bool
    four_way_complete: bool
    po_quantity_ok: bool
    delivery_quantity_ok: bool
    authorized_quantity_ok: bool
    authorized_rate_ok: bool


class ProjectCostSummary(StrictModel):
    boq_budget_total: Decimal = Field(ge=0)
    authorized_contract_total: Decimal = Field(ge=0)
    invoiced_total: Decimal = Field(ge=0)
    authorized_vs_budget_percent: Decimal
    invoiced_vs_budget_percent: Decimal


class LineageSummary(StrictModel):
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    cycle_detected: bool
    invoice_nodes_without_contract_path: list[str]


class ConstructionIntelligenceReport(StrictModel):
    schema_version: Literal["0.5.0"] = CONSTRUCTION_SCHEMA_VERSION
    engine_version: Literal["0.5.0"] = CONSTRUCTION_SCHEMA_VERSION
    case_id: str
    project_id: str
    input_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    findings: list[ConstructionFinding]
    matches: list[MatchResult]
    cost_summary: ProjectCostSummary
    lineage_summary: LineageSummary
    requires_human_review: bool
    automation_authority: Literal[False] = False
    operational_side_effects_performed: Literal[False] = False
