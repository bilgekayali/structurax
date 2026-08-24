# Changelog

All notable changes to StructuraX are documented here.

## [1.0.0] - 2026-08-24

### Changed

- Promoted package metadata and `structurax.__version__` to `1.0.0` as the v1 package baseline.
- Updated formal-promotion policy so `1.0.0` is the package baseline while the `Production/Stable` classifier remains a separate, gated human-approved release action.
- Kept release-surface hashing tolerant only of the approved release metadata fields; source, policy, workflow, dependency and schema changes remain digest-significant.
- Updated citation metadata and release diagnostics to the `1.0.0` package baseline.

### Security boundary

- The `1.0.0` package-version baseline does **not** assert formal release eligibility or production readiness.
- Genuine independent security review, signed production-control evidence, authenticated repository-governance verification, complete release SBOM/provenance attestation and human release approval remain required before the `Production/Stable` classifier, release tag or publication can be treated as formally promoted.
- `formal_release_eligible` and `production_readiness_claimed` remain fail-closed until those controls are verified.

## [0.5.0] - 2026-08-21

### Added

- Strict synthetic construction-intelligence contracts for BOQ, contract, variation-order, purchase-order, delivery, invoice and supplier price-history evidence.
- Deterministic three-way and four-way matching with cumulative quantity and authorized-rate checks.
- Contract authority derived only from approved, evidence-backed, explicitly linked and currently effective variation orders.
- Typed document-lineage graph with canonical edges, relation-type validation, contract-path checks and cycle defense.
- BOQ quantity, authorized project-cost and realized invoiced-cost variance evidence.
- Supplier unit-rate anomaly review signal based on a minimum deterministic historical median; future observations are rejected.
- Clean and deliberately risky synthetic construction cases, deterministic evaluation reports and compact JSON Schemas.
- `structurax construction-analyze` CLI command and CI coverage across Python 3.11, 3.12 and 3.13.

### Security boundary

- v0.5 remains deterministic and reference-only; it performs no live OCR/model call, payment, ERP mutation, deployment, procurement commitment or external notification.
- `matched`, `review` and `block` are evidence classifications only and do not carry automation authority.
- Supplier anomalies and cost variances are review signals, not proof of fraud, overcharging, contractual entitlement, legal liability or engineering correctness.

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
