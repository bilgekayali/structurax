# Threat Model

## Objective

StructuraX v0.2 demonstrates how untrusted synthetic PDF inputs can cross a bounded,
provenance-preserving ingestion boundary before deterministic construction-document
controls and human review. It is an alpha reference implementation, not a complete PDF
sandbox, malware scanner, fraud detector, accounting control, legal opinion or engineering
control.

## Assets

- Integrity and provenance of source bytes and extracted text.
- Integrity of document amounts, quantities, currencies and payment details.
- Traceability from findings to source fields and rule families.
- Integrity of human-review feedback evidence.
- Reproducibility of fixtures, reports and evaluation metrics.

## Trust boundaries

| Boundary | Established in v0.2 | Not established by v0.2 |
|---|---|---|
| PDF preflight | Header/EOF, size bounds, selected active-content rejection | Complete PDF safety or malware absence |
| Built-in adapter | Digest-bound recorded replay; no network/subprocess/model code path | OS/container sandbox proof for a future live adapter |
| Fixture integrity | Ed25519 signature + exact SHA-256 file binding | Organizational signer identity or production trust anchor |
| Normalized pack | Strict synthetic JSON validation | Authenticity of a real supplier/source document |
| Deterministic rules | Reproducible selected risk signals | Exhaustive fraud or contractual-truth determination |
| Reviewer feedback | Typed, digestable, side-effect-free evidence | Authorization to pay, approve, notify or modify systems |

## Covered threat examples

- Truncated/non-PDF input is rejected before extraction.
- Selected PDF active/opaque content markers fail closed.
- Source substitution changes SHA-256 and breaks recorded extraction/manifest binding.
- Adapter configuration/output substitution changes provenance digests.
- Embedded control-bypass language remains untrusted document data.
- False positives and false negatives can be measured explicitly by rule family.

## Residual risks and out of scope

- PDF parser vulnerabilities, decompression bombs and sandbox escapes are not fully solved by
  byte-marker preflight.
- The built-in replay adapter is not a live OCR engine and does not establish OCR accuracy.
- A malicious PDF can use constructs not covered by the selected marker list.
- Signatures/stamps/handwriting/image manipulation and digital-signature validation remain
  out of scope.
- Authentication, tenancy, retention, privacy, incident response and live-system connectors
  remain out of scope.
- Clean results are not approval, authenticity, compliance or safety guarantees.

## Safe deployment principle

Do not connect the v0.2 reference to production documents or consequential actions. A
future live parser/OCR integration must be separately sandboxed, least-privileged,
auditable and network-disabled by default. A qualified human remains responsible for
source authenticity, policy applicability and every consequential next step.
