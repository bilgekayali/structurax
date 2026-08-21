# Production Evidence Collection

StructuraX v1.0 keeps production-control validation external to ordinary CI. This collection layer makes that external process reproducible without giving the repository access to production credentials, endpoints or validator private keys.

## Flow

1. An authorized validator performs the real production checks for PostgreSQL tenant isolation, external identity, evidence encryption/key management, and observability/deployment controls.
2. Each control produces an external evidence artifact in the organization's governed evidence store. The artifact itself is not committed to this repository.
3. The validator creates one secret-free receipt per control using `release-evidence-schemas/production-control-receipt.schema.json`. Each receipt binds the current `sha256-release-surface-v1` digest, one production environment, an opaque validator identifier, an opaque external artifact identifier, the artifact SHA-256 digest, completion time, and confirmation that a negative path was tested.
4. `scripts/assemble_production_evidence.py` requires the exact four-control receipt set, one common environment, distinct artifact ids/digests, no raw endpoints/secrets, and the exact current release-surface digest. It produces an **unsigned** production evidence statement.
5. `scripts/build_production_signing_payload.py` canonicalizes that statement into the exact Ed25519 signing payload. It never loads or generates a private key.
6. A separately governed trusted signer signs the payload outside the repository/CI environment.
7. `scripts/attach_production_evidence_signature.py` combines the statement, externally supplied signature and trusted public key, then runs the normal production-evidence verifier before writing the final envelope.

## Files that must remain transient

The repository ignores `production-evidence/receipts/`, `*.statement.json`, `*.signing-payload` and `*.signature`. These are preparation artifacts and would otherwise perturb the release surface or encourage accidental evidence leakage.

The final `production-evidence/v1.0-controls.json` is intentionally **not** ignored. It may only be added during the explicit human-reviewed release process after the validator trust anchor is established and the external evidence has been independently reviewed.

## Security properties

The collection tooling:

- does not connect to PostgreSQL, an IdP, KMS/HSM, telemetry systems or a production deployment;
- does not accept or store passwords, connection strings, tokens, private keys or raw endpoint metadata;
- does not generate validator keys;
- does not sign evidence;
- does not establish that a supplied public key is organizationally trusted;
- does not mutate formal release-gate booleans;
- does not create tags, publish packages, or claim production readiness.

A cryptographically valid envelope is therefore necessary but not sufficient for formal v1.0 promotion. Repository governance, final release attestations, genuine independent security review and explicit human release approval remain separate gates.
