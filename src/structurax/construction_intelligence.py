"""Deterministic v0.5 construction intelligence analysis."""
from __future__ import annotations

from decimal import Decimal

from structurax.construction_lineage import contract_authority, graph_cycle, has_contract_path
from structurax.construction_matching import evaluate_invoice_matching
from structurax.construction_models import (
    ConstructionEvidenceRef, ConstructionFinding, ConstructionIntelligenceCase, ConstructionIntelligenceReport,
    ConstructionPolicy, LineageRelation, LineageSummary, ProjectCostSummary, VariationStatus,
    canonical_digest, qmoney, qqty,
)
from structurax.models import Severity


def _evidence(artifact_id: str, field: str, observed: object, expected: object | None = None) -> ConstructionEvidenceRef:
    return ConstructionEvidenceRef(
        artifact_id=artifact_id, field=field, observed=str(observed),
        expected=None if expected is None else str(expected),
    )


def analyze_construction_case(
    case: ConstructionIntelligenceCase,
    policy: ConstructionPolicy | None = None,
) -> ConstructionIntelligenceReport:
    active = policy or ConstructionPolicy()
    findings, matches = evaluate_invoice_matching(case, active)
    boq_by_item = {line.item_code: line for line in case.boq_lines}
    declared_edges = {
        (edge.from_artifact_id, edge.to_artifact_id, edge.relation)
        for edge in case.lineage_edges
    }
    contract_by_key = {
        (line.supplier_id, line.item_code): line for line in case.contract_lines
    }
    for variation in case.variation_orders:
        if variation.status != VariationStatus.APPROVED:
            continue
        contract = contract_by_key.get((variation.supplier_id, variation.item_code))
        if contract is None:
            continue
        if (
            contract.artifact_id,
            variation.artifact_id,
            LineageRelation.AMENDS,
        ) not in declared_edges:
            findings.append(
                ConstructionFinding(
                    rule_id="APPROVED_VARIATION_UNLINKED",
                    severity=Severity.HIGH,
                    title=(
                        "Approved variation order is not linked to its governing contract"
                    ),
                    description=(
                        f"{variation.artifact_id} affects {variation.item_code} but "
                        "lacks an explicit contract-to-variation lineage edge."
                    ),
                    evidence=[
                        _evidence(
                            variation.artifact_id,
                            "lineage.contract_amendment",
                            "missing",
                            contract.artifact_id,
                        )
                    ],
                    recommendation=(
                        "Establish and verify the contract amendment lineage before "
                        "using the variation as commercial authority."
                    ),
                )
            )

    boq_budget = qmoney(
        sum((line.budget_amount for line in case.boq_lines), Decimal("0"))
    )
    authorized_total = Decimal("0")
    for contract in case.contract_lines:
        authority = contract_authority(case, contract.supplier_id, contract.item_code)
        if not authority:
            continue
        quantity, rate, source = authority
        authorized_total += quantity * rate
        boq = boq_by_item.get(contract.item_code)
        if boq is None:
            findings.append(
                ConstructionFinding(
                    rule_id="CONTRACT_ITEM_NOT_IN_BOQ",
                    severity=Severity.HIGH,
                    title="Contract item has no BOQ baseline",
                    description=(
                        f"Contract authority for {contract.item_code} cannot be "
                        "reconciled to a BOQ item."
                    ),
                    evidence=[
                        _evidence(
                            contract.artifact_id,
                            "item_code",
                            contract.item_code,
                            "BOQ item",
                        )
                    ],
                    recommendation=(
                        "Confirm scope authorization and establish the BOQ/change-control "
                        "baseline before relying on the contract line."
                    ),
                )
            )
        if boq and quantity > boq.budget_quantity + active.quantity_tolerance:
            findings.append(
                ConstructionFinding(
                    rule_id="BOQ_QUANTITY_VARIANCE",
                    severity=Severity.MEDIUM,
                    title="Authorized contract quantity exceeds BOQ quantity",
                    description=(
                        f"Approved contract/variation scope for {contract.item_code} "
                        "exceeds the BOQ baseline."
                    ),
                    evidence=[
                        _evidence(
                            source,
                            "authorized_quantity",
                            quantity,
                            qqty(boq.budget_quantity),
                        ),
                        _evidence(
                            boq.artifact_id,
                            "budget_quantity",
                            qqty(boq.budget_quantity),
                        ),
                    ],
                    recommendation=(
                        "Review the approved scope change against budget, forecast, "
                        "and change-control evidence."
                    ),
                )
            )
    authorized_total = qmoney(authorized_total)
    invoiced_total = qmoney(
        sum(
            (line.quantity * line.unit_rate for line in case.invoices),
            Decimal("0"),
        )
    )
    auth_variance = (
        Decimal("0")
        if boq_budget == 0
        else (authorized_total - boq_budget) / boq_budget * Decimal("100")
    )
    invoice_variance = (
        Decimal("0")
        if boq_budget == 0
        else (invoiced_total - boq_budget) / boq_budget * Decimal("100")
    )
    if auth_variance > active.project_budget_variance_percent:
        findings.append(
            ConstructionFinding(
                rule_id="PROJECT_AUTHORIZED_COST_OVERRUN",
                severity=Severity.HIGH,
                title="Authorized contract cost exceeds BOQ budget threshold",
                description=(
                    "Contract plus approved variation authority exceeds the configured "
                    "project budget variance threshold."
                ),
                evidence=[
                    ConstructionEvidenceRef(
                        artifact_id=case.boq_lines[0].artifact_id,
                        field="project_authorized_vs_boq",
                        observed=str(qmoney(authorized_total)),
                        expected=str(boq_budget),
                    )
                ],
                recommendation=(
                    "Escalate to commercial/project controls for forecast and "
                    "approved-budget reconciliation."
                ),
            )
        )

    node_ids = [node.artifact_id for node in case.lineage_nodes]
    cycle = graph_cycle(node_ids, case.lineage_edges)
    if cycle:
        findings.append(
            ConstructionFinding(
                rule_id="LINEAGE_CYCLE",
                severity=Severity.HIGH,
                title="Document lineage graph contains a cycle",
                description=(
                    "The declared construction-document lineage is not a directed "
                    "acyclic evidence chain."
                ),
                evidence=[
                    ConstructionEvidenceRef(
                        artifact_id=node_ids[0],
                        field="lineage",
                        observed="cycle_detected",
                        expected="acyclic",
                    )
                ],
                recommendation=(
                    "Review lineage references and correct circular document "
                    "relationships before relying on provenance."
                ),
            )
        )
    invoice_nodes = sorted({line.artifact_id for line in case.invoices})
    orphans = sorted(
        invoice_id
        for invoice_id in invoice_nodes
        if not has_contract_path(case, invoice_id)
    )
    for invoice_id in orphans:
        findings.append(
            ConstructionFinding(
                rule_id="LINEAGE_MISSING_CONTRACT_PATH",
                severity=Severity.HIGH,
                title="Invoice lineage does not reach a contract",
                description=(
                    f"{invoice_id} has no declared lineage path to a contract artifact."
                ),
                evidence=[
                    _evidence(
                        invoice_id,
                        "lineage.contract_path",
                        "missing",
                        "present",
                    )
                ],
                recommendation=(
                    "Establish and verify invoice-to-PO/delivery/contract lineage "
                    "before approval."
                ),
            )
        )

    rank = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
    }
    findings = sorted(
        findings,
        key=lambda finding: (
            rank[finding.severity],
            finding.rule_id,
            finding.evidence[0].artifact_id,
        ),
    )
    return ConstructionIntelligenceReport(
        case_id=case.case_id,
        project_id=case.project_id,
        input_sha256=canonical_digest(case.model_dump(mode="json")),
        findings=findings,
        matches=matches,
        cost_summary=ProjectCostSummary(
            boq_budget_total=boq_budget,
            authorized_contract_total=authorized_total,
            invoiced_total=invoiced_total,
            authorized_vs_budget_percent=qmoney(auth_variance),
            invoiced_vs_budget_percent=qmoney(invoice_variance),
        ),
        lineage_summary=LineageSummary(
            node_count=len(case.lineage_nodes),
            edge_count=len(case.lineage_edges),
            cycle_detected=cycle,
            invoice_nodes_without_contract_path=orphans,
        ),
        requires_human_review=bool(findings),
    )
