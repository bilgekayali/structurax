# v1.0 Security Reference Validation

This slice moves selected v1.0 security controls from static contracts into executable
reference validation. It still does **not** declare production readiness.

## PostgreSQL tenant isolation

The `Security Reference Validation` workflow starts an ephemeral PostgreSQL 17 service and
runs `scripts/validate_postgres_rls.py` against `sql/001_tenant_rls_reference.sql`.

The validation proves, in that CI environment, that:

- row-level security is enabled and forced on the evidence table;
- the application role does not have `BYPASSRLS`;
- no evidence rows are visible before a tenant context is established;
- tenant A cannot read or update tenant B rows;
- a tenant A insert using a tenant B identifier is rejected by PostgreSQL RLS;
- same-tenant inserts remain visible; and
- switching the session tenant changes the visible row set as expected.

This is materially stronger than linting the SQL text, but it is not a production-database
validation. Production still requires deployment-specific role ownership, pool/session reset,
connection lifecycle, migration, backup/restore, break-glass access, replica, monitoring and
operational IAM validation.

## Identity reference

`structurax.security_reference.verify_reference_oidc_token` verifies a compact EdDSA JWT
against a pinned Ed25519 public key and fail-closes on unsupported algorithms, invalid
signatures, issuer/audience mismatch, tenant mismatch, expiry/not-before errors, future token
timestamps, missing roles and missing MFA evidence in `amr`.

The function intentionally does not perform live OIDC discovery, JWKS rotation, revocation,
provider availability or organization-specific identity policy enforcement. Those remain
production identity-boundary work.

## Evidence encryption reference

`encrypt_reference_evidence` and `decrypt_reference_evidence` exercise AES-256-GCM using
96-bit nonces and tenant/artifact/source-digest associated data. The reference metadata stores
ciphertext and source digests plus an opaque key reference; it does not store plaintext or key
material. Decryption rejects cross-tenant use, ciphertext tampering, wrong keys and AAD/digest
mismatch.

The test key is synthetic. No production KMS, HSM, envelope-key lifecycle, rotation, deletion,
backup or access policy is claimed.

## Release-gate semantics

The formal release booleans for PostgreSQL tenant isolation, external identity, and evidence
key management remain `false`. Passing this workflow demonstrates bounded reference controls;
it does not silently promote them into production-validation claims.

The new `security-reference-validation` job is added to the expected required-status-check
policy so repository protection can eventually enforce it together with deterministic CI,
Release Gates and CodeQL.
