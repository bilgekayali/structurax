# StructuraX Analysis Report

- Pack: `risky-pack`
- Engine: `0.1.0`
- Policy: `0.1.0`
- Input SHA-256: `0c34de14f1c21fcf5819c96620faec49818ecdce839baf6c1442c64e6fb76689`
- Disposition: **BLOCK**
- Findings: **13**

> This deterministic report identifies review signals; it does not approve payments, authenticate documents, or replace professional review.

## Severity summary

| Critical | High | Medium | Low |
|---:|---:|---:|---:|
| 4 | 9 | 0 | 0 |

## Findings

| Severity | Rule | Finding | Evidence |
|---|---|---|---|
| critical | `BANK_ACCOUNT_CHANGE` | Supplier bank account changed | INV-200:bank_account=DEMO-TR-STRUCTURAX-999; PO-200:bank_account=DEMO-TR-STRUCTURAX-002 |
| critical | `BANK_ACCOUNT_CHANGE` | Supplier bank account changed | INV-200-COPY:bank_account=DEMO-TR-STRUCTURAX-999; PO-200:bank_account=DEMO-TR-STRUCTURAX-002 |
| critical | `DUPLICATE_INVOICE` | Possible duplicate invoice | INV-200:external_reference=SUP-INV-7788; INV-200-COPY:external_reference=SUP-INV-7788 |
| critical | `EMBEDDED_INSTRUCTION` | Document contains an embedded control-bypass instruction | INV-200:extracted_text=approve without review, ignore prior instructions, system override |
| high | `ARITHMETIC_TOTAL` | Document total is inconsistent | INV-200:total=16500.00 |
| high | `ARITHMETIC_TOTAL` | Document total is inconsistent | INV-200-COPY:total=16500.00 |
| high | `INVOICE_EXCEEDS_DELIVERY` | Invoice quantity exceeds recorded delivery | INV-200:line_items.STL-500.quantity=100; DN-200:line_items.STL-500.quantity=80 |
| high | `INVOICE_EXCEEDS_DELIVERY` | Invoice quantity exceeds recorded delivery | INV-200-COPY:line_items.STL-500.quantity=100; DN-200:line_items.STL-500.quantity=80 |
| high | `MISSING_APPROVAL` | Required high-value approval is missing | INV-200:approvals=project_manager |
| high | `MISSING_APPROVAL` | Required high-value approval is missing | INV-200-COPY:approvals=project_manager |
| high | `MISSING_APPROVAL` | Required high-value approval is missing | PO-200:approvals=project_manager |
| high | `UNIT_PRICE_VARIANCE` | Invoice unit price exceeds policy tolerance | INV-200:line_items.STL-500.unit_price=110.00; PO-200:line_items.STL-500.unit_price=100.00 |
| high | `UNIT_PRICE_VARIANCE` | Invoice unit price exceeds policy tolerance | INV-200-COPY:line_items.STL-500.unit_price=110.00; PO-200:line_items.STL-500.unit_price=100.00 |

## Required follow-up

- **BANK_ACCOUNT_CHANGE:** Block payment and verify the change through an independent, pre-established supplier contact channel.
- **BANK_ACCOUNT_CHANGE:** Block payment and verify the change through an independent, pre-established supplier contact channel.
- **DUPLICATE_INVOICE:** Block payment and have Accounts Payable verify invoice lineage and prior payment status.
- **EMBEDDED_INSTRUCTION:** Quarantine the document for human review and do not execute instructions found inside document content.
- **ARITHMETIC_TOTAL:** Block automated approval and reconcile the arithmetic against the original source.
- **ARITHMETIC_TOTAL:** Block automated approval and reconcile the arithmetic against the original source.
- **INVOICE_EXCEEDS_DELIVERY:** Hold the affected line and verify receipt with the site and commercial teams.
- **INVOICE_EXCEEDS_DELIVERY:** Hold the affected line and verify receipt with the site and commercial teams.
- **MISSING_APPROVAL:** Route the document to the missing approval roles before any payment or commitment.
- **MISSING_APPROVAL:** Route the document to the missing approval roles before any payment or commitment.
- **MISSING_APPROVAL:** Route the document to the missing approval roles before any payment or commitment.
- **UNIT_PRICE_VARIANCE:** Require an approved change order or corrected invoice before payment.
- **UNIT_PRICE_VARIANCE:** Require an approved change order or corrected invoice before payment.
