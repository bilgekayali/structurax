"""Deterministic v0.5 construction authority and lineage helpers."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from structurax.construction_models import (
    ConstructionIntelligenceCase,
    LineageEdge,
    LineageRelation,
    VariationStatus,
    qmoney,
    qqty,
)


def grouped_quantity(
    values: list[object],
    *,
    supplier_id: str,
    item_code: str,
) -> Decimal:
    total = Decimal("0")
    for value in values:
        if (
            getattr(value, "supplier_id") == supplier_id
            and getattr(value, "item_code") == item_code
        ):
            total += getattr(value, "quantity")
    return qqty(total)


def contract_authority(
    case: ConstructionIntelligenceCase,
    supplier_id: str,
    item_code: str,
) -> tuple[Decimal, Decimal, str] | None:
    contracts = [
        line
        for line in case.contract_lines
        if line.supplier_id == supplier_id and line.item_code == item_code
    ]
    if not contracts:
        return None
    contract = contracts[0]
    quantity = contract.contracted_quantity
    rate = contract.unit_rate
    source = contract.artifact_id
    declared_amendments = {
        (edge.from_artifact_id, edge.to_artifact_id)
        for edge in case.lineage_edges
        if edge.relation == LineageRelation.AMENDS
    }
    approved = sorted(
        [
            vo
            for vo in case.variation_orders
            if vo.supplier_id == supplier_id
            and vo.item_code == item_code
            and vo.status == VariationStatus.APPROVED
            and (contract.artifact_id, vo.artifact_id) in declared_amendments
        ],
        key=lambda vo: (vo.effective_at, vo.variation_id),
    )
    for vo in approved:
        quantity += vo.quantity_delta
        if vo.revised_unit_rate is not None:
            rate = vo.revised_unit_rate
        source = vo.artifact_id
    return qqty(quantity), qmoney(rate), source


def rate_within(actual: Decimal, expected: Decimal, tolerance_percent: Decimal) -> bool:
    if expected == 0:
        return actual == 0
    variance = abs(actual - expected) / expected * Decimal("100")
    return variance <= tolerance_percent


def graph_cycle(nodes: list[str], edges: list[LineageEdge]) -> bool:
    adjacency: dict[str, list[str]] = {node: [] for node in nodes}
    for edge in edges:
        adjacency[edge.from_artifact_id].append(edge.to_artifact_id)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in adjacency[node]:
            if visit(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in nodes if node not in visited)


def has_contract_path(case: ConstructionIntelligenceCase, invoice_id: str) -> bool:
    reverse: dict[str, list[str]] = defaultdict(list)
    for edge in case.lineage_edges:
        reverse[edge.to_artifact_id].append(edge.from_artifact_id)
    types = {node.artifact_id: node.artifact_type.value for node in case.lineage_nodes}
    stack = [invoice_id]
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if types[current] == "contract":
            return True
        stack.extend(reverse[current])
    return False
