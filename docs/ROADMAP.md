# Roadmap

The roadmap keeps deterministic controls and human authority ahead of model capability.

## v0.1 — Deterministic foundation

- [x] Strict synthetic document-pack schema.
- [x] Arithmetic and cross-document reconciliation.
- [x] Duplicate, approval, bank-account, and embedded-instruction signals.
- [x] Field-level evidence and explicit dispositions.
- [x] Reproducible JSON and Markdown reports.
- [x] Credential-free local demo, tests, CI, architecture, and threat model.

## v0.2 — Sandboxed ingestion and evaluation

- [x] Isolated PDF/OCR adapter interface with exact source and adapter provenance.
- [x] Strict PDF preflight with bounded size/content and fail-closed active-content rejection.
- [x] Network-free digest-bound recorded extraction adapter for synthetic fixtures.
- [x] Adversarial and corrupted-document evaluation set.
- [x] English and Turkish reviewer-facing explanations for every current rule ID.
- [x] False-positive and false-negative measurement by rule family.
- [x] Human-review feedback format without production side effects.
- [x] Ed25519-signed fixture manifest and documented data lineage.

## v0.3 — Optional AI adapters

- [x] Provider-neutral extraction adapter contract.
- [x] Recorded-response replay so tests do not require model calls.
- [x] Synthetic model comparison by accuracy, evidence fidelity, latency, and cost.
- [x] Prompt-injection resistance tests at the untrusted-content boundary.
- [x] Confidence abstention and deterministic fallback behavior.
- [x] Network and tool access disabled by default in the accepted core adapter profile.

## v0.4 — Controlled pilot readiness

- [x] Role-based review workflow with tamper-evident hash-linked audit events and semantic policy replay.
- [x] Maker-checker separation, approval ownership, and default-deny role enforcement.
- [x] Policy versioning, exact predecessor binding, approval ownership, and change governance.
- [x] Privacy, retention, access-control, incident-response, and rollback reference contracts.
- [x] Synthetic red-team exercise covering workflow and release-readiness bypass attempts.
- [x] Deployment reference with explicit human checkpoints and no autonomous action authority.
- [x] Exact repository-review digest utility and independent-review machine contract.
- [ ] Genuine independent security review of the exact v0.4 source state.

The hash-linked audit chain is tamper-evident evidence; it is not a claim of append-only or
WORM storage. Production immutability requires separately enforced storage and IAM controls.

The implementation milestone may merge without fabricating independent review evidence. A
pilot-ready claim remains fail-closed until a genuine independent reviewer supplies a
schema-valid review bound to the exact repository digest and all gates are re-run.

## v0.5 — Construction intelligence

- [x] BOQ and quantity reconciliation.
- [x] Contract and approved variation-order linkage with as-of chronology.
- [x] Supplier historical-median and project-cost anomaly evidence.
- [x] Three-way/four-way matching and typed document lineage graph.
- [x] Fail-closed lineage relation semantics and temporal leakage tests.
- [x] Synthetic clean/risky fixtures, deterministic reports, schemas, CLI and CI coverage.

## v1.0 — Stable production reference

- [x] Stable API/schema compatibility contract.
- [ ] PostgreSQL tenant isolation and production identity boundary.
- [x] Encrypted evidence, observability and deployment reference.
- [ ] SBOM/provenance, CodeQL and release gates.
- [ ] Genuine independent security review before formal stable release.

The API/schema surface is frozen for the release candidate with exact public-export and schema
content identities. Security, encryption, PostgreSQL, identity, observability and deployment
reference controls are executable and fail closed, but reference validation is not a claim that
a production environment enforces those controls.

A production-evidence harness now defines an Ed25519-signed, exact-repository-digest-bound
contract for real PostgreSQL, identity, KMS/encryption and observability/deployment validation.
Ordinary CI deliberately contains no production evidence and cannot auto-promote those controls;
a trusted validator key and real external evidence remain required before human-reviewed gate
promotion.

Release-candidate supply-chain preparation now binds the wheel, dependency SBOM, source
provenance and release-gate output into a deterministic SHA-256 evidence manifest before any
manual GitHub attestation step. This is preparation only: the SBOM/provenance milestone remains
open until release evidence is attached and attested for the exact accepted candidate and the
repository-level CodeQL/release governance controls are actually enforced.

The roadmap is directional, not a release commitment. Production use requires a separate
risk assessment, governance model, security architecture, legal/privacy assessment, and
validation against the actual organization, document types, contracts, models, providers
and jurisdiction.
