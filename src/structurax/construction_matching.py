"""Deterministic v0.5 invoice, supplier, and three-/four-way matching."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from statistics import median

from structurax.construction_lineage import contract_authority, grouped_quantity, has_contract_path, rate_within
from structurax.construction_models import (
    ConstructionEvidenceRef, ConstructionFinding, ConstructionIntelligenceCase, ConstructionPolicy,
    MatchResult, MatchStatus, qmoney,
)
from structurax.models import Severity


def _evidence(artifact_id: str, field: str, observed: object, expected: object | None = None) -> ConstructionEvidenceRef:
    return ConstructionEvidenceRef(
        artifact_id=artifact_id, field=field, observed=str(observed),
        expected=None if expected is None else str(expected),
    )


def evaluate_invoice_matching(
    case: ConstructionIntelligenceCase,
    policy: ConstructionPolicy,
) -> tuple[list[ConstructionFinding], list[MatchResult]]:
    active = policy
    findings: list[ConstructionFinding] = []
    matches: list[MatchResult] = []
    history: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
    for observation in case.supplier_price_history:
        history[(observation.supplier_id, observation.item_code)].append(
            observation.unit_rate
        )

    for invoice in sorted(
        case.invoices,
        key=lambda item: (item.artifact_id, item.item_code, item.supplier_id),
    ):
        authority = contract_authority(case, invoice.supplier_id, invoice.item_code)
        relevant_pos = [
            po
            for po in case.purchase_orders
            if po.supplier_id == invoice.supplier_id
            and po.item_code == invoice.item_code
        ]
        po_qty = grouped_quantity(
            case.purchase_orders,
            supplier_id=invoice.supplier_id,
            item_code=invoice.item_code,
        )
        delivered_qty = grouped_quantity(
            case.deliveries,
            supplier_id=invoice.supplier_id,
            item_code=invoice.item_code,
        )
        invoiced_qty = grouped_quantity(
            case.invoices,
            supplier_id=invoice.supplier_id,
            item_code=invoice.item_code,
        )
        po_exists = po_qty > 0
        delivery_exists = delivered_qty > 0
        authority_exists = authority is not None
        po_ok = po_exists and invoiced_qty <= po_qty + active.quantity_tolerance
        delivery_ok = (
            delivery_exists
            and invoiced_qty <= delivered_qty + active.quantity_tolerance
        )
        auth_qty_ok = False
        auth_rate_ok = False
        if authority:
            auth_qty, auth_rate, auth_source = authority
            auth_qty_ok = invoiced_qty <= auth_qty + active.quantity_tolerance
            invoice_rate_ok = rate_within(
                invoice.unit_rate,
                auth_rate,
                active.rate_tolerance_percent,
            )
            po_rate_ok = all(
                rate_within(po.unit_rate, auth_rate, active.rate_tolerance_percent)
                for po in relevant_pos
            )
            auth_rate_ok = invoice_rate_ok and po_rate_ok
            if not auth_qty_ok:
                findings.append(
                    ConstructionFinding(
                        rule_id="INVOICE_EXCEEDS_AUTHORIZED_QUANTITY",
                        severity=Severity.CRITICAL,
                        title="Cumulative invoice quantity exceeds contract authority",
                        description=(
                            f"{invoice.artifact_id} bills {invoice.item_code} above the "
                            "contract plus approved variation quantity."
                        ),
                        evidence=[
                            _evidence(
                                invoice.artifact_id,
                                "quantity.cumulative_invoiced",
                                invoiced_qty,
                                auth_qty,
                            ),
                            _evidence(auth_source, "authorized_quantity", auth_qty),
                        ],
                        recommendation=(
                            "Block the affected payment line and obtain an approved "
                            "variation or corrected invoice before further processing."
                        ),
                    )
                )
            if not invoice_rate_ok:
                findings.append(
                    ConstructionFinding(
                        rule_id="UNIT_RATE_EXCEEDS_AUTHORIZED",
                        severity=Severity.CRITICAL,
                        title="Invoice unit rate is outside authorized contract tolerance",
                        description=(
                            f"{invoice.artifact_id} uses a unit rate not supported by "
                            "the contract or latest approved variation."
                        ),
                        evidence=[
                            _evidence(
                                invoice.artifact_id,
                                "unit_rate",
                                qmoney(invoice.unit_rate),
                                auth_rate,
                            ),
                            _evidence(auth_source, "authorized_unit_rate", auth_rate),
                        ],
                        recommendation=(
                            "Hold the line and verify the governing contract or approved "
                            "variation order."
                        ),
                    )
                )
            for po in relevant_pos:
                if not rate_within(
                    po.unit_rate,
                    auth_rate,
                    active.rate_tolerance_percent,
                ):
                    findings.append(
                        ConstructionFinding(
                            rule_id="PO_UNIT_RATE_EXCEEDS_AUTHORIZED",
                            severity=Severity.HIGH,
                            title="Purchase-order unit rate is outside contract authority",
                            description=(
                                f"{po.artifact_id} uses a unit rate not supported by "
                                "the contract or latest approved variation."
                            ),
                            evidence=[
                                _evidence(
                                    po.artifact_id,
                                    "unit_rate",
                                    qmoney(po.unit_rate),
                                    auth_rate,
                                ),
                                _evidence(auth_source, "authorized_unit_rate", auth_rate),
                            ],
                            recommendation=(
                                "Review the purchase order against the governing contract "
                                "and approved variation evidence."
                            ),
                        )
                    )
        else:
            findings.append(
                ConstructionFinding(
                    rule_id="MISSING_CONTRACT_AUTHORITY",
                    severity=Severity.CRITICAL,
                    title="Invoice line has no contract authority",
                    description=(
                        f"No contract line authorizes supplier {invoice.supplier_id} "
                        f"item {invoice.item_code}."
                    ),
                    evidence=[
                        _evidence(
                            invoice.artifact_id,
                            "item_code",
                            invoice.item_code,
                            "contracted item",
                        )
                    ],
                    recommendation=(
                        "Block approval until contract authority is established and linked."
                    ),
                )
            )
        if not po_ok:
            findings.append(
                ConstructionFinding(
                    rule_id="THREE_WAY_PO_MISMATCH",
                    severity=Severity.HIGH,
                    title="Invoice quantity does not reconcile to purchase orders",
                    description=(
                        f"Cumulative invoice quantity for {invoice.item_code} exceeds "
                        "or lacks purchase-order quantity."
                    ),
                    evidence=[
                        _evidence(
                            invoice.artifact_id,
                            "quantity.cumulative_invoiced",
                            invoiced_qty,
                            po_qty,
                        )
                    ],
                    recommendation=(
                        "Reconcile invoice quantity to an authorized purchase order "
                        "before payment review."
                    ),
                )
            )
        if not delivery_ok:
            findings.append(
                ConstructionFinding(
                    rule_id="THREE_WAY_DELIVERY_MISMATCH",
                    severity=Severity.HIGH,
                    title="Invoice quantity does not reconcile to recorded delivery",
                    description=(
                        f"Cumulative invoice quantity for {invoice.item_code} exceeds "
                        "or lacks delivery evidence."
                    ),
                    evidence=[
                        _evidence(
                            invoice.artifact_id,
                            "quantity.cumulative_invoiced",
                            invoiced_qty,
                            delivered_qty,
                        )
                    ],
                    recommendation=(
                        "Verify receipt with site records and hold the unmatched quantity."
                    ),
                )
            )

        prices = history[(invoice.supplier_id, invoice.item_code)]
        if len(prices) >= active.minimum_supplier_history:
            baseline = Decimal(str(median(prices)))
            deviation = (
                Decimal("0")
                if baseline == 0
                else abs(invoice.unit_rate - baseline)
                / baseline
                * Decimal("100")
            )
            if deviation > active.supplier_anomaly_percent:
                findings.append(
                    ConstructionFinding(
                        rule_id="SUPPLIER_UNIT_RATE_ANOMALY",
                        severity=Severity.MEDIUM,
                        title=(
                            "Supplier unit rate deviates from deterministic historical median"
                        ),
                        description=(
                            f"{invoice.artifact_id} is outside the configured supplier "
                            f"price-history threshold for {invoice.item_code}."
                        ),
                        evidence=[
                            _evidence(
                                invoice.artifact_id,
                                "unit_rate",
                                qmoney(invoice.unit_rate),
                                qmoney(baseline),
                            )
                        ],
                        recommendation=(
                            "Review supplier price history and commercial justification; "
                            "this signal is not proof of fraud or overcharging."
                        ),
                    )
                )

        three_way_complete = po_exists and delivery_exists
        contract_path_ok = has_contract_path(case, invoice.artifact_id)
        four_way_complete = (
            three_way_complete and authority_exists and contract_path_ok
        )
        if not four_way_complete:
            status = (
                MatchStatus.BLOCK
                if (not authority_exists or not contract_path_ok)
                else MatchStatus.REVIEW
            )
        elif po_ok and delivery_ok and auth_qty_ok and auth_rate_ok:
            status = MatchStatus.MATCHED
        elif not auth_qty_ok or not auth_rate_ok:
            status = MatchStatus.BLOCK
        else:
            status = MatchStatus.REVIEW
        matches.append(
            MatchResult(
                invoice_artifact_id=invoice.artifact_id,
                supplier_id=invoice.supplier_id,
                item_code=invoice.item_code,
                status=status,
                three_way_complete=three_way_complete,
                four_way_complete=four_way_complete,
                po_quantity_ok=po_ok,
                delivery_quantity_ok=delivery_ok,
                authorized_quantity_ok=auth_qty_ok,
                authorized_rate_ok=auth_rate_ok,
            )
        )

    return findings, matches
