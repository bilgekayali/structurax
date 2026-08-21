# Changelog

All notable changes to StructuraX are documented here.

## [0.4.0] - 2026-08-21

### Added

- Role-based human review workflow with maker-checker separation and explicit approval ownership.
- Tamper-evident, hash-linked audit-event evidence bound to exact review-case and policy digests.
- Semantic audit-history replay that revalidates RBAC, maker-checker and approval-owner rules even when an attacker recomputes event hashes.
- Policy versioning and change-governance contract requiring separate author/approver humans and exact predecessor binding.
- Reference-only data handling, default-deny access, incident response, human checkpoint and rollback contracts.
- Deterministic synthetic workflow fixtures and v0.4 red-team scenarios for audit tampering, rehashed unauthorized history, self-approval, approval-owner bypass, policy substitution and missing independent review.
- Fail-closed pilot-readiness assessment that cannot become eligible without a genuine independent review bound to the expected repository digest.
- Deterministic Git-tracked repository review-digest utility and independent security review schema/handoff guidance.
- Seven new v0.4 JSON Schemas, pilot governance/security/deployment documentation and CI coverage.

### Security boundary

- The hash-linked audit chain is tamper-evident evidence, not proof of immutable/WORM storage; production immutability requires separately enforced append-only storage and IAM controls.
- v0.4 remains reference-only: no live model/OCR call, deployment, autonomous approval, payment, ERP mutation or external notification is performed.
- The implementation milestone does not fabricate independent review evidence. The committed pilot-readiness report remains ineligible until a real independent review exists.

## [0.3.0] - 2026-08-21

### Added

- Provider-neutral, fail-closed AI extraction adapter contract bound to exact source and v0.2 ingestion provenance.
- Offline recorded-response adapter with no live model, network, tool, subprocess or filesystem-write execution in the built-in path.
- Pre-invocation untrusted-instruction detection, confidence abstention and deterministic fallback.
- Cited-page evidence digest and canonical provider-response digest verification.
- Synthetic two-adapter comparison covering field accuracy, evidence fidelity, recorded latency and cost.

### Security boundary

- v0.3 does not ship a credentialed live AI provider integration or autonomous action authority.

## [0.2.0] - 2026-08-20

### Added

- Fail-closed PDF preflight and a closed ingestion-adapter contract with exact source, adapter and extraction provenance.
- Network-free, digest-bound recorded extraction adapter for synthetic PDF fixtures.
- Adversarial/truncated PDF boundary fixtures protected by an Ed25519-signed manifest.
- Deterministic English and Turkish reviewer explanations and rule-family regression evidence.
- Side-effect-free human-review feedback contract.

## [0.1.0] - 2026-08-05

### Added

- Strict Pydantic contracts for synthetic construction document packs.
- Deterministic arithmetic, cross-document, approval, duplicate, and embedded-instruction controls.
- Field-level evidence, reproducible input hashes, and `allow`, `review`, or `block` dispositions.
- Command-line validation and analysis with JSON and Markdown reports.
- Clean and deliberately risky synthetic reference scenarios.
- Credential-free Gradio and Docker demo paths.
