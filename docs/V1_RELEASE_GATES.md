# v1.0 Release Gates — Preparation Slice

This slice hardens the path toward a stable StructuraX release while deliberately keeping
formal v1.0 eligibility **false**.

## Draft schema compatibility gate

`configs/stable_schema_contract.json` defines the minimum committed schema surface and
critical schema files that must remain present during preparation. `scripts/verify_stable_schemas.py`
requires every committed `*.schema.json` file to be valid JSON with a unique title and an
object root.

This is not yet the final backward-compatibility freeze. The final release candidate must
replace the preparation contract with an explicitly reviewed compatibility policy and
versioned baseline.

## Installed dependency-closure SBOM

`scripts/generate_dependency_sbom.py` walks the installed Python distribution dependency
closure from `structurax` and emits deterministic CycloneDX 1.5-shaped JSON for the active
CI environment. It is evidence that dependency-closure generation works; it is **not** yet
the signed/attested release SBOM for a production artifact.

## Formal release gate

`configs/release_candidate_gate.json` records the controls that must be true before a formal
v1.0 promotion. `scripts/assess_release_gate.py` fails closed if the configuration attempts
to declare formal eligibility while any blocker remains. It also requires package version
`1.0.0`.

The preparation configuration intentionally keeps these controls false, including real
PostgreSQL tenant-isolation validation, external identity validation, evidence encryption
and key-management validation, observability/deployment validation, complete release SBOM,
build provenance attestation, enforced CodeQL release gating and genuine independent
security review.

## CI

`.github/workflows/release-gates.yml` verifies the draft API/schema contracts, generates and
checks the dependency-closure SBOM, asserts the formal release gate remains blocked, and
runs the focused release-gate tests. Existing deterministic CI and CodeQL remain separate
required evidence sources; repository branch-protection enforcement is still future work.
