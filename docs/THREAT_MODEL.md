# Threat Model

## Objective

StructuraX v0.1 demonstrates how a deterministic trust layer can surface selected risks in normalized, synthetic construction documents while preserving human authority.

It is an alpha reference implementation, not a complete security, fraud, accounting, legal, or engineering control.

## Assets

- Integrity of document amounts, quantities, currencies, and payment details.
- Traceability from every finding to its source field.
- Integrity of approval requirements and review dispositions.
- Reproducibility of reports for the same pack and policy.
- Safety of the demonstration environment.

## Trust boundaries

| Boundary | Trusted in v0.1 | Not established by v0.1 |
|---|---|---|
| Input | Schema-valid synthetic JSON | Authenticity of a real source document |
| Identity | Synthetic IDs are internally consistent | Supplier, approver, signer, or user identity |
| Policy | Committed policy file is the selected policy | Whether it matches a specific contract or jurisdiction |
| Execution | Local deterministic Python code | External OCR, model, database, payment, or approval systems |
| Output | Evidence-backed signals and disposition | Proof of fraud, contractual truth, or permission to act |

## Covered threat examples

| Threat | v0.1 signal | Primary mitigation path |
|---|---|---|
| Arithmetic manipulation | Totals do not reconcile | Stop automated flow and reconcile source values |
| Price or currency drift | Invoice differs from purchase order | Require corrected evidence or authorized change |
| Overbilling against delivery | Invoiced quantity exceeds delivery note | Verify receipt with site and commercial teams |
| Payment diversion | Bank account differs from baseline | Block and verify through an independent known channel |
| Duplicate payment risk | Invoice identity tuple repeats | Hold and reconcile duplicate candidates |
| Approval bypass | Required role is not approved | Route to the missing authorized reviewer |
| Prompt/control injection in document text | Bypass-oriented instruction is embedded | Treat document content as untrusted data and block |

## Abuse and failure cases

- A malicious author may phrase an instruction in a way not covered by the configured indicators.
- A carefully chosen amount may remain inside a configured tolerance.
- Incorrect but internally consistent documents can evade arithmetic checks.
- Missing or false relationships can produce misleading comparisons.
- Duplicate detection can generate false positives when identifiers are reused legitimately.
- A clean result can be misinterpreted as approval or authenticity.

Controls therefore produce review signals with evidence; they do not claim exhaustive detection.

## Out of scope

- PDF malware, file-format exploits, macros, and sandbox escape.
- OCR accuracy, handwriting, stamps, signatures, and image manipulation.
- Authentication, digital-signature validation, and identity proofing.
- Contract interpretation, legal or regulatory conclusions, and jurisdiction mapping.
- Engineering design review, quantity surveying, or site acceptance.
- Complete fraud detection or production-grade anomaly detection.
- Storage, retention, access control, tenancy, privacy, and incident response for real documents.
- Operational actions such as payment, approval, notification, or ERP mutation.

## Safe deployment principle

Do not connect the v0.1 demo to production data or live actions. Future integrations should be sandboxed, least-privileged, auditable, and disabled by default. A qualified human must verify source authenticity, policy applicability, and any consequential next step.

