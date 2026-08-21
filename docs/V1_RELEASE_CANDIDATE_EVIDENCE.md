# v1.0 Release-Candidate Evidence

StructuraX now has a bounded release-evidence pipeline for the v1.0 release-candidate process. It is designed to bind the package subject, dependency SBOM, source provenance and formal release-gate output before any GitHub attestation is created.

## Digest-bound bundle

`scripts/build_release_evidence_manifest.py` requires exactly one wheel in `dist/` and binds four roles:

- `wheel`
- `dependency_sbom`
- `source_provenance`
- `release_gate`

Every artifact is recorded with its filename, byte count and SHA-256 digest. The manifest also carries the wheel subject digest and a deterministic bundle digest over the canonical evidence structure.

`scripts/verify_release_evidence_manifest.py` recomputes those values and fails closed on missing artifacts, digest drift, size drift, package/version mismatch, role-order drift or any preview artifact that claims formal release readiness.

## Independent security review

The existing frozen `IndependentSecurityReview` evidence envelope remains the compatibility contract. `scripts/verify_independent_review.py` adds release-candidate semantics without changing that frozen schema. It requires:

- an exact repository review digest,
- an identified reviewer,
- explicit reviewer-independence confirmation,
- a non-placeholder SHA-256 digest for the review evidence,
- and a timezone-aware completion timestamp.

`security-review/v1.0-review.json` is excluded from the canonical repository digest to avoid a circular hash dependency. A review for any other digest fails verification.

A verified review envelope does **not** automatically mutate the formal release gate. Promotion of `independent_security_review_verified` remains an explicit human-reviewed release action.

## GitHub workflows

`Release Evidence Validation` runs on pull requests and `main` and verifies the non-attested preview bundle. `Release Evidence Attestation` remains manual. It now verifies the digest-bound bundle before calling GitHub attestation actions and validates an independent review if one is present.

The manual workflow is still a preview while the formal release gate is blocked. Running it does not by itself establish production readiness or satisfy the final v1.0 release conditions.

## Remaining external blockers

This work does not enable `main` branch protection, configure required checks in repository settings, prove production PostgreSQL/identity/KMS/observability controls, promote the package to `1.0.0`, or create the genuine independent security review. Formal release remains fail-closed until those controls are separately evidenced and approved.
