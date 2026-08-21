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

The built-in v0.2 adapter is a deterministic replay boundary; it does **not** perform live
OCR or claim OS/container sandbox enforcement. A future real parser/OCR worker must be
separately isolated and satisfy the same closed adapter contract.

## v0.3 — Optional AI adapters

- [ ] Provider-neutral extraction adapter contract.
- [ ] Recorded-response replay so tests do not require model calls.
- [ ] Model comparison by accuracy, evidence fidelity, latency, and cost.
- [ ] Prompt-injection resistance tests at the untrusted-content boundary.
- [ ] Confidence abstention and deterministic fallback behavior.
- [ ] Network and tool access disabled by default.

## v0.4 — Controlled pilot readiness

- [ ] Role-based review workflow and immutable audit events.
- [ ] Policy versioning, approval ownership, and change governance.
- [ ] Privacy, retention, access-control, and incident-response design.
- [ ] Red-team exercise and independent security review.
- [ ] Deployment guide with explicit human checkpoints and rollback.

## v0.5 — Construction intelligence

- [ ] BOQ and quantity reconciliation.
- [ ] Contract and variation-order linkage.
- [ ] Supplier and project-cost anomaly evidence.
- [ ] Three-way/four-way matching and document lineage graph.

## v1.0 — Stable production reference

- [ ] Stable API/schema compatibility contract.
- [ ] PostgreSQL tenant isolation and production identity boundary.
- [ ] Encrypted evidence, observability and deployment reference.
- [ ] SBOM/provenance, CodeQL and release gates.
- [ ] Genuine independent security review before formal stable release.

The roadmap is directional, not a release commitment. Production use requires a separate
risk assessment, governance model, security architecture, and validation against the
actual organization, document types, contracts, and jurisdiction.
