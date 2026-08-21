# Changelog

All notable changes to StructuraX are documented here.

## [0.3.0] - 2026-08-21

### Added

- Provider-neutral, fail-closed AI extraction adapter contract bound to exact source and
  v0.2 ingestion provenance.
- Offline recorded-response adapter with no live model, network, tool, subprocess or
  filesystem-write execution in the built-in path.
- Pre-invocation untrusted-instruction detection that prevents adapter invocation and
  selects a deterministic fallback artifact.
- Confidence-based abstention for low overall confidence, low required-field confidence
  and missing required fields.
- Machine contracts that preserve human review, prohibit automation authority and record
  zero operational side effects.
- Synthetic two-adapter comparison covering exact field accuracy, evidence fidelity,
  recorded latency, recorded cost, invocation count and fallback count.
- New CLI commands, JSON Schemas, reproducible synthetic AI fixtures, evaluation report,
  v0.3 tests and AI-boundary documentation.

### Security boundary

- v0.3 does not ship a credentialed live AI provider integration and does not claim that
  lexical prompt-injection indicators are an exhaustive injection defense.
- AI-selected outputs remain review evidence only; they do not approve, pay, mutate ERP
  state or establish document authenticity, legal truth or engineering correctness.

## [0.2.0] - 2026-08-20

### Added

- Fail-closed PDF preflight and a closed ingestion-adapter contract with exact source,
  adapter and extraction provenance.
- Network-free, digest-bound recorded extraction adapter for synthetic PDF fixtures.
- Adversarial/truncated PDF boundary fixtures protected by an Ed25519-signed manifest.
- Deterministic English and Turkish reviewer explanations for all current rule IDs.
- Rule-family false-positive/false-negative, precision and recall regression evidence.
- Side-effect-free human-review feedback contract and stable feedback digest.
- Six v0.2 JSON Schemas, fixture data-lineage documentation and expanded CI across Python
  3.11, 3.12 and 3.13.

### Security boundary

- v0.2 does not perform live OCR/model calls and does not claim kernel/container sandbox
  enforcement. Real parser/OCR workers remain a future separately isolated boundary.

## [0.1.0] - 2026-08-05

### Added

- Strict Pydantic contracts for synthetic construction document packs.
- Deterministic arithmetic, cross-document, approval, duplicate, and embedded-instruction controls.
- Field-level evidence, reproducible input hashes, and `allow`, `review`, or `block` dispositions.
- Command-line validation and analysis with JSON and Markdown reports.
- Clean and deliberately risky synthetic reference scenarios.
- Credential-free Gradio and Docker demo paths.
- Generated JSON Schema, reference reports, unit tests, CI, architecture notes, and threat model.
