# Production Evidence Harness

StructuraX keeps production validation separate from reference validation. This harness defines a machine-verifiable envelope for real production-control evidence without pretending that CI has access to, or has validated, a production environment.

## Purpose

The harness covers the four production-only controls that remain false in `configs/release_candidate_gate.json`:

- PostgreSQL tenant isolation.
- External identity boundary.
- Evidence encryption and key management.
- Observability and deployment controls.

A production validation statement must be bound to the canonical v1.0 release-surface digest and signed with an out-of-band trusted Ed25519 validator key. The committed envelope contains only opaque identifiers and SHA-256 evidence digests. Raw endpoints, credentials, secrets, connection strings, tokens, key material and production document content are forbidden.

## Evidence shape

`release-evidence-schemas/production-control-evidence.schema.json` defines the release-evidence schema. It intentionally lives outside `schemas/` so the already-frozen application schema surface remains unchanged.

Each control must:

1. be present exactly once;
2. have result `passed`;
3. bind a distinct external evidence artifact by SHA-256;
4. identify an opaque validator;
5. record a timezone-aware completion timestamp; and
6. confirm that a negative path was tested.

The top-level statement must confirm that the validation occurred against a production environment while explicitly declaring that raw endpoint metadata and raw secret material are absent from the committed evidence.

## Signature and release-surface binding

`scripts/assess_promotion_readiness.py` supplies `sha256-release-surface-v1` to the production-evidence verifier. `scripts/release_surface_digest.py` hashes Git-tracked source and policy state while canonicalizing only the explicit mechanical release metadata permitted by the final promotion transaction. This lets genuine production evidence remain valid across the final version/classifier-only promotion commit without making source, schema, workflow, dependency or security-policy changes invisible.

`production-evidence/v1.0-controls.json` is excluded from the release-surface digest, just like independent-review and human release-approval evidence, so signed evidence can bind the reviewed source/configuration state without a circular hash dependency.

The signature key identifier is the SHA-256 digest of the trusted raw Ed25519 public key. Merely committing a self-generated public key together with an evidence envelope is not sufficient evidence of validator trust. The trusted key must be supplied through the release governance process.

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
