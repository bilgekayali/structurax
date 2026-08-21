# Production Evidence Harness

StructuraX keeps production validation separate from reference validation. This harness defines a machine-verifiable envelope for real production-control evidence without pretending that CI has access to, or has validated, a production environment.

## Purpose

The harness covers the four production-only controls that remain false in `configs/release_candidate_gate.json`:

- PostgreSQL tenant isolation.
- External identity boundary.
- Evidence encryption and key management.
- Observability and deployment controls.

A production validation statement must be bound to the exact canonical repository digest and signed with an out-of-band trusted Ed25519 validator key. The committed envelope contains only opaque identifiers and SHA-256 evidence digests. Raw endpoints, credentials, secrets, connection strings, tokens, key material and production document content are forbidden.

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

## Signature and repository binding

`scripts/verify_production_evidence.py` canonicalizes only the statement, verifies an Ed25519 signature using a separately supplied trusted public key and requires `reviewed_repository_sha256` to match `scripts/repository_review_digest.py`.

`production-evidence/v1.0-controls.json` is excluded from the canonical repository digest, just like independent-review evidence, so the signed statement can bind the code/configuration state without a circular hash dependency.

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
