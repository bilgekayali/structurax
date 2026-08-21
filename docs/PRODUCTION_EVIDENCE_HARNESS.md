# Production Evidence Harness

StructuraX keeps production validation separate from reference validation. This harness defines a machine-verifiable envelope for real production-control evidence without pretending that CI has access to, or has validated, a production environment.

## Purpose

The harness covers the four production-only controls that remain false in `configs/release_candidate_gate.json`:

- PostgreSQL tenant isolation.
- External identity boundary.
- Evidence encryption and key management.
- Observability and deployment controls.

A production validation statement must be bound to the exact canonical `sha256-release-surface-v1` digest and signed with an out-of-band trusted Ed25519 validator key. The committed envelope contains only opaque identifiers and SHA-256 evidence digests. Raw endpoints, credentials, secrets, connection strings, tokens, key material and production document content are forbidden.

## Evidence shape

`release-evidence-schemas/production-control-evidence.schema.json` defines the final release-evidence schema. It intentionally lives outside `schemas/` so the frozen application schema surface remains unchanged.

Each control must:

1. be present exactly once;
2. have result `passed`;
3. bind a distinct external evidence artifact by SHA-256;
4. identify an opaque validator;
5. record a timezone-aware completion timestamp; and
6. confirm that a negative path was tested.

The top-level statement must confirm that validation occurred against a production environment while explicitly declaring that raw endpoint metadata and raw secret material are absent from committed evidence.

## Release-surface binding

`scripts/release_surface_digest.py` computes the v1.0 evidence-binding digest. It canonicalizes only the explicitly allowlisted final release metadata fields, so the mechanical `0.5.0` to `1.0.0` promotion can preserve evidence binding while any source, schema, workflow, dependency, security-policy or other tracked-byte change invalidates prior production evidence.

`production-evidence/v1.0-controls.json` is excluded from the release-surface digest to avoid a circular hash dependency.

## Collection and signing handoff

`docs/PRODUCTION_EVIDENCE_COLLECTION.md` defines the operational collection flow. Secret-free per-control receipts are assembled into an unsigned statement, then converted into the canonical Ed25519 payload. The repository never handles a validator private key. An external trusted signer produces the signature, and the repository only attaches and verifies the signature with the separately supplied trusted public key.

The signature key identifier is the SHA-256 digest of the trusted raw Ed25519 public key. Merely supplying a public key and a valid signature does not establish organizational trust in that key; the trust anchor must be established through the release-governance process.

## Fail-closed behavior

The repository does not contain `production-evidence/v1.0-controls.json`. Normal CI therefore verifies that production evidence is absent and that the formal release gate remains closed.

Even a cryptographically valid production evidence envelope returns `formal_gate_mutation_authorized=false`. Evidence verification is an input to a human-reviewed promotion; it never changes `formal_release_eligible` or production-control booleans by itself.

## Non-claims

This harness does not:

- deploy PostgreSQL, an IdP, KMS/HSM, telemetry infrastructure or a runtime environment;
- inspect a production environment from ordinary CI;
- prove that an external evidence artifact is trustworthy merely because its digest is recorded;
- establish the organizational trust anchor for a validator key;
- enable GitHub branch protection or required checks;
- create final release attestations; or
- replace the genuine independent security review required before formal v1.0.
