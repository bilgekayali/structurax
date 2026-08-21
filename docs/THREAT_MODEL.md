# Threat Model

## Objective

StructuraX v0.3 demonstrates how untrusted synthetic PDF inputs can cross a bounded,
provenance-preserving ingestion boundary and an optional fail-closed probabilistic
extraction boundary before deterministic construction-document controls and human review.
It is an alpha reference implementation, not a complete PDF sandbox, malware scanner,
prompt-injection detector, fraud detector, accounting control, legal opinion or
engineering control.

## Assets

- Integrity and provenance of source bytes and extracted text.
- Integrity of probabilistic request/response/evidence bindings.
- Integrity of confidence/abstention and deterministic fallback decisions.
- Integrity of document amounts, quantities, currencies and payment details.
- Traceability from findings to source fields and rule families.
- Integrity of human-review feedback evidence.
- Reproducibility of fixtures, reports and evaluation metrics.

## Trust boundaries

| Boundary | Established in v0.3 | Not established by v0.3 |
|---|---|---|
| PDF preflight | Header/EOF, size bounds, selected active-content rejection | Complete PDF safety or malware absence |
| v0.2 built-in adapter | Digest-bound recorded replay; no network/subprocess/model code path | OS/container sandbox proof for a future live parser/OCR adapter |
| v0.3 built-in AI adapter | Exact request-digest replay; closed declared execution profile | Proof that an arbitrary third-party adapter cannot violate its declaration |
| AI request | Exact source/extraction digests, bounded pages and requested fields | Authenticity or truth of the underlying document |
| AI evidence | Requested-field check, cited-page bounds, recomputed page-text digest, response digest | Model factuality, semantic correctness or exhaustive evidence attribution |
| Prompt-injection precheck | Bounded lexical indicators block invocation and force fallback | Detection of all indirect/direct prompt-injection techniques |
| Confidence policy | Explicit overall/field thresholds and missing-field fallback | Calibrated production confidence or business-risk acceptance |
| AI resolution | Human review required; automation authority and side effects false | Authorization to pay, approve, notify or modify systems |
| Fixture integrity | v0.2 signed fixture chain; v0.3 deterministic generated synthetic fixtures | Organizational production trust anchor or real provider evidence |
| Deterministic rules | Reproducible selected risk signals | Exhaustive fraud or contractual-truth determination |

## Covered threat examples

- Truncated/non-PDF input is rejected before extraction.
- Selected PDF active/opaque content markers fail closed.
- Source substitution changes SHA-256 and breaks recorded extraction/request binding.
- Unrequested AI fields fail closed.
- AI evidence hashes that do not match cited page text fail closed.
- Recorded AI responses whose canonical digest is altered fail closed.
- Known control-bypass phrases are detected before adapter invocation and force fallback.
- Low confidence or missing required fields force deterministic fallback.
- AI-selected outputs cannot claim automation authority or operational side effects.
- Synthetic adapter accuracy/evidence/latency/cost tradeoffs are measured without live calls.

## Residual risks and out of scope

- PDF parser vulnerabilities, decompression bombs and sandbox escapes are not fully solved by
  byte-marker preflight.
- The built-in replay adapters are not live OCR or live AI engines and establish no
  production OCR/model accuracy.
- A malicious document can use PDF constructs or prompt-injection language not covered by
  current bounded checks.
- Confidence values are provider-supplied evidence inputs; v0.3 applies thresholds but does
  not prove statistical calibration.
- A custom adapter could lie about a closed execution profile; production enforcement must
  exist outside this reference core.
- Signatures, stamps, handwriting/image manipulation and digital-signature validation remain
  out of scope.
- Authentication, tenancy, retention, privacy, incident response and live-system connectors
  remain out of scope until later milestones.
- Clean or AI-selected results are not approval, authenticity, compliance or safety
  guarantees.

## Safe deployment principle

Do not connect the v0.3 reference path directly to production documents or consequential
actions. A future live parser/OCR/model integration must be separately isolated,
least-privileged, auditable and denied network/tool capabilities unless explicitly reviewed
for that deployment. A qualified human remains responsible for source authenticity, policy
applicability, model/provider suitability and every consequential next step.
