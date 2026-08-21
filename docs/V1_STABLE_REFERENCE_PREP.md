# v1.0 Stable Reference Preparation

StructuraX v1.0 preparation begins from the accepted v0.5 trust boundaries. This milestone
does **not** declare a stable production release. The roadmap still requires a genuine
independent security review before any formal stable-release claim.

## This preparation slice

This branch adds four fail-closed reference mechanisms:

1. **Draft public API compatibility baseline.** `configs/stable_api_contract.json` records
   the public v0.5 exports that must remain importable while the stable contract is designed.
   `scripts/verify_stable_api.py` fails if a required export disappears.
2. **Tenant / identity reference contracts.** `TenantContext` is metadata supplied by an
   external identity boundary; StructuraX does not authenticate it. `require_same_tenant`
   rejects cross-tenant evidence references.
3. **Encrypted-evidence and telemetry contracts.** The evidence envelope carries digests,
   ciphertext metadata and an opaque key reference only. Observability events structurally
   forbid raw documents, prompts and secrets.
4. **Deterministic release provenance.** `scripts/build_release_provenance.py` hashes bounded
   source/config/schema/script/SQL files and records direct dependency declarations. It
   explicitly does not claim a resolved dependency SBOM or build attestation yet.

## PostgreSQL RLS reference

`sql/001_tenant_rls_reference.sql` demonstrates an intended fail-closed row-level-security
shape using an application tenant setting, `ENABLE ROW LEVEL SECURITY`, and
`FORCE ROW LEVEL SECURITY`. It is deliberately labelled **reference-only**. Real deployment
must separately validate connection-pool tenant context, database roles, owner bypass,
backup/restore isolation, migrations, incident response and operational access.

## Non-claims

This preparation work does not prove production tenant isolation, authenticate identities,
encrypt or persist real evidence, provision keys, deploy PostgreSQL, emit production
telemetry, generate a complete transitive SBOM, create a SLSA attestation, satisfy CodeQL
release gates, or complete the required independent review.

The v1.0 roadmap items therefore remain open until those controls are implemented and
independently validated against the exact release candidate.
