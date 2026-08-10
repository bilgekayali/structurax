"""Deterministic document-risk rules with field-level evidence."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from structurax.models import (
    ApprovalStatus,
    Document,
    DocumentPack,
    DocumentType,
    EvidenceRef,
    Finding,
    Policy,
    Severity,
)


MONEY_QUANTUM = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM)


def _differs(left: Decimal, right: Decimal, tolerance: Decimal) -> bool:
    return abs(_money(left) - _money(right)) > tolerance


def _evidence(
    document: Document,
    field: str,
    observed: object,
    expected: object | None = None,
) -> EvidenceRef:
    return EvidenceRef(
        document_id=document.document_id,
        field=field,
        observed=str(observed),
        expected=None if expected is None else str(expected),
    )


def _related_document(
    document: Document,
    documents: dict[str, Document],
    document_type: DocumentType,
) -> Document | None:
    for related_id in document.related_document_ids:
        related = documents[related_id]
        if related.document_type == document_type:
            return related
    return next(
        (
            candidate
            for candidate in documents.values()
            if candidate.document_type == document_type
        ),
        None,
    )


def _arithmetic_findings(pack: DocumentPack, policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    for document in pack.documents:
        expected_subtotal = sum(
            (_money(item.quantity * item.unit_price) for item in document.line_items),
            start=Decimal("0"),
        )
        for item in document.line_items:
            expected_line_total = _money(item.quantity * item.unit_price)
            if _differs(
                item.line_total, expected_line_total, policy.amount_tolerance
            ):
                findings.append(
                    Finding(
                        rule_id="ARITHMETIC_LINE_TOTAL",
                        severity=Severity.HIGH,
                        title="Line total does not match quantity × unit price",
                        description=(
                            f"{document.document_id} contains an inconsistent total "
                            f"for line {item.item_code}."
                        ),
                        evidence=[
                            _evidence(
                                document,
                                f"line_items.{item.item_code}.line_total",
                                _money(item.line_total),
                                expected_line_total,
                            )
                        ],
                        recommendation=(
                            "Stop approval and reconcile the source document with "
                            "the supplier or document owner."
                        ),
                    )
                )
        expected_tax = _money(
            expected_subtotal * document.tax_rate_percent / Decimal("100")
        )
        expected_total = _money(expected_subtotal + expected_tax)
        for rule_id, title, field, observed, expected in (
            (
                "ARITHMETIC_SUBTOTAL",
                "Document subtotal is inconsistent",
                "subtotal",
                document.subtotal,
                expected_subtotal,
            ),
            (
                "ARITHMETIC_TAX",
                "Document tax amount is inconsistent",
                "tax_amount",
                document.tax_amount,
                expected_tax,
            ),
            (
                "ARITHMETIC_TOTAL",
                "Document total is inconsistent",
                "total",
                document.total,
                expected_total,
            ),
        ):
            if _differs(observed, expected, policy.amount_tolerance):
                findings.append(
                    Finding(
                        rule_id=rule_id,
                        severity=Severity.HIGH,
                        title=title,
                        description=(
                            f"{document.document_id} does not reconcile to its "
                            "line items and tax calculation."
                        ),
                        evidence=[
                            _evidence(
                                document,
                                field,
                                _money(observed),
                                _money(expected),
                            )
                        ],
                        recommendation=(
                            "Block automated approval and reconcile the arithmetic "
                            "against the original source."
                        ),
                    )
                )
    return findings


def _cross_document_findings(
    pack: DocumentPack, policy: Policy
) -> list[Finding]:
    findings: list[Finding] = []
    documents = {document.document_id: document for document in pack.documents}
    invoices = [
        document
        for document in pack.documents
        if document.document_type == DocumentType.INVOICE
    ]
    for invoice in invoices:
        purchase_order = _related_document(
            invoice, documents, DocumentType.PURCHASE_ORDER
        )
        delivery_note = _related_document(
            invoice, documents, DocumentType.DELIVERY_NOTE
        )
        if purchase_order is None:
            continue
        if invoice.currency != purchase_order.currency:
            findings.append(
                Finding(
                    rule_id="CURRENCY_MISMATCH",
                    severity=Severity.HIGH,
                    title="Invoice and purchase-order currencies differ",
                    description=(
                        f"{invoice.document_id} does not use the currency authorized "
                        f"by {purchase_order.document_id}."
                    ),
                    evidence=[
                        _evidence(
                            invoice,
                            "currency",
                            invoice.currency,
                            purchase_order.currency,
                        )
                    ],
                    recommendation=(
                        "Obtain a corrected invoice or an approved contract change "
                        "before payment review."
                    ),
                )
            )
        order_items = {
            item.item_code: item for item in purchase_order.line_items
        }
        delivery_items = (
            {item.item_code: item for item in delivery_note.line_items}
            if delivery_note
            else {}
        )
        for invoice_item in invoice.line_items:
            order_item = order_items.get(invoice_item.item_code)
            if order_item and order_item.unit_price > 0:
                variance = _money(
                    abs(invoice_item.unit_price - order_item.unit_price)
                    / order_item.unit_price
                    * Decimal("100")
                )
                if variance > policy.price_variance_percent:
                    findings.append(
                        Finding(
                            rule_id="UNIT_PRICE_VARIANCE",
                            severity=Severity.HIGH,
                            title="Invoice unit price exceeds policy tolerance",
                            description=(
                                f"Line {invoice_item.item_code} in "
                                f"{invoice.document_id} differs from the purchase "
                                "order price."
                            ),
                            evidence=[
                                _evidence(
                                    invoice,
                                    (
                                        "line_items."
                                        f"{invoice_item.item_code}.unit_price"
                                    ),
                                    _money(invoice_item.unit_price),
                                    _money(order_item.unit_price),
                                ),
                                _evidence(
                                    purchase_order,
                                    (
                                        "line_items."
                                        f"{order_item.item_code}.unit_price"
                                    ),
                                    _money(order_item.unit_price),
                                ),
                            ],
                            recommendation=(
                                "Require an approved change order or corrected "
                                "invoice before payment."
                            ),
                        )
                    )
            delivered_item = delivery_items.get(invoice_item.item_code)
            if delivered_item and invoice_item.quantity > delivered_item.quantity:
                findings.append(
                    Finding(
                        rule_id="INVOICE_EXCEEDS_DELIVERY",
                        severity=Severity.HIGH,
                        title="Invoice quantity exceeds recorded delivery",
                        description=(
                            f"{invoice.document_id} bills more "
                            f"{invoice_item.item_code} than the delivery note records."
                        ),
                        evidence=[
                            _evidence(
                                invoice,
                                f"line_items.{invoice_item.item_code}.quantity",
                                invoice_item.quantity,
                                delivered_item.quantity,
                            ),
                            _evidence(
                                delivery_note,
                                f"line_items.{delivered_item.item_code}.quantity",
                                delivered_item.quantity,
                            ),
                        ],
                        recommendation=(
                            "Hold the affected line and verify receipt with the site "
                            "and commercial teams."
                        ),
                    )
                )
        baseline_account = purchase_order.bank_account
        if (
            baseline_account
            and invoice.bank_account
            and invoice.bank_account != baseline_account
        ):
            findings.append(
                Finding(
                    rule_id="BANK_ACCOUNT_CHANGE",
                    severity=Severity.CRITICAL,
                    title="Supplier bank account changed",
                    description=(
                        f"{invoice.document_id} requests payment to an account that "
                        f"differs from {purchase_order.document_id}."
                    ),
                    evidence=[
                        _evidence(
                            invoice,
                            "bank_account",
                            invoice.bank_account,
                            baseline_account,
                        ),
                        _evidence(
                            purchase_order,
                            "bank_account",
                            baseline_account,
                        ),
                    ],
                    recommendation=(
                        "Block payment and verify the change through an independent, "
                        "pre-established supplier contact channel."
                    ),
                )
            )
    return findings


def _duplicate_invoice_findings(pack: DocumentPack) -> list[Finding]:
    groups: dict[tuple[str, str, str, Decimal], list[Document]] = defaultdict(list)
    for document in pack.documents:
        if document.document_type == DocumentType.INVOICE:
            key = (
                document.supplier_id,
                document.external_reference,
                document.currency,
                _money(document.total),
            )
            groups[key].append(document)
    findings: list[Finding] = []
    for duplicates in groups.values():
        if len(duplicates) < 2:
            continue
        findings.append(
            Finding(
                rule_id="DUPLICATE_INVOICE",
                severity=Severity.CRITICAL,
                title="Possible duplicate invoice",
                description=(
                    "Multiple invoices share supplier, external reference, currency, "
                    "and total."
                ),
                evidence=[
                    _evidence(
                        document,
                        "external_reference",
                        document.external_reference,
                    )
                    for document in duplicates
                ],
                recommendation=(
                    "Block payment and have Accounts Payable verify invoice lineage "
                    "and prior payment status."
                ),
            )
        )
    return findings


def _approval_findings(pack: DocumentPack, policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    required_roles = {role.casefold() for role in policy.required_approval_roles}
    governed_types = {DocumentType.PURCHASE_ORDER, DocumentType.INVOICE}
    for document in pack.documents:
        if (
            document.document_type not in governed_types
            or document.total < policy.high_value_threshold
        ):
            continue
        approved_roles = {
            approval.role.casefold()
            for approval in document.approvals
            if approval.status == ApprovalStatus.APPROVED
        }
        missing = sorted(required_roles - approved_roles)
        if missing:
            findings.append(
                Finding(
                    rule_id="MISSING_APPROVAL",
                    severity=Severity.HIGH,
                    title="Required high-value approval is missing",
                    description=(
                        f"{document.document_id} lacks approved roles required by "
                        "the active policy."
                    ),
                    evidence=[
                        _evidence(
                            document,
                            "approvals",
                            ", ".join(sorted(approved_roles)) or "none",
                            ", ".join(sorted(required_roles)),
                        )
                    ],
                    recommendation=(
                        "Route the document to the missing approval roles before "
                        "any payment or commitment."
                    ),
                )
            )
    return findings


def _embedded_instruction_findings(
    pack: DocumentPack, policy: Policy
) -> list[Finding]:
    findings: list[Finding] = []
    indicators = [indicator.casefold() for indicator in policy.prompt_injection_indicators]
    for document in pack.documents:
        normalized = document.extracted_text.casefold()
        matched = sorted(
            {indicator for indicator in indicators if indicator in normalized}
        )
        if not matched:
            continue
        findings.append(
            Finding(
                rule_id="EMBEDDED_INSTRUCTION",
                severity=Severity.CRITICAL,
                title="Document contains an embedded control-bypass instruction",
                description=(
                    f"Extracted text in {document.document_id} contains content that "
                    "must be treated as untrusted data, not an instruction."
                ),
                evidence=[
                    _evidence(
                        document,
                        "extracted_text",
                        ", ".join(matched),
                        "no control-bypass indicators",
                    )
                ],
                recommendation=(
                    "Quarantine the document for human review and do not execute "
                    "instructions found inside document content."
                ),
            )
        )
    return findings


def evaluate_rules(pack: DocumentPack, policy: Policy) -> list[Finding]:
    findings = [
        *_arithmetic_findings(pack, policy),
        *_cross_document_findings(pack, policy),
        *_duplicate_invoice_findings(pack),
        *_approval_findings(pack, policy),
        *_embedded_instruction_findings(pack, policy),
    ]
    severity_rank = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
    }
    return sorted(
        findings,
        key=lambda finding: (
            severity_rank[finding.severity],
            finding.rule_id,
            finding.evidence[0].document_id,
        ),
    )
