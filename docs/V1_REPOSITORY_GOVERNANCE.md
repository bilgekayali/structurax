# v1.0 Repository Governance and Attestation Preparation

This slice makes repository governance and release-evidence provenance explicit without
claiming that GitHub repository settings or production controls have been configured.

## Observable branch-governance policy

`configs/repository_governance_policy.json` defines the expected `main`-branch status-check
surface. `scripts/assess_repository_governance.py` can inspect the public GitHub branch
summary and report whether the branch is protected and whether the expected check contexts
are present.

The observable required checks are:

- `deterministic-validation (3.11)`
- `deterministic-validation (3.12)`
- `deterministic-validation (3.13)`
- `v1-prep-release-gates`
- `CodeQL (python)`

GitHub's branch summary does not prove every protection detail. Strict/up-to-date status
checks, review counts, stale-review dismissal, conversation resolution, force-push policy,
and deletion policy remain explicit manual controls until they are independently inspected.
The assessment therefore never marks those controls as verified.

## Release-evidence attestation workflow

`.github/workflows/release-evidence-attestation.yml` is intentionally manual. It builds the
currently selected repository revision, generates the dependency-closure SBOM, source
provenance and formal-release gate report, and then uses GitHub artifact attestations to
create signed provenance and SBOM attestations for the built wheel.

The workflow uses `actions/attest@v4`, the current consolidated GitHub attestation action.
Creating this workflow does not set `build_provenance_attested=true`; the formal release gate
must remain closed until an exact release candidate has been built, attested and verified.

## Required repository settings before formal v1.0

Repository administrators must still configure and independently verify protection for
`main`, including required pull requests, the expected status checks, strict/up-to-date
checking, at least one approving review, stale-review dismissal, conversation resolution,
and disabled force pushes / branch deletion.

These settings are repository state, not source code. They must not be represented as
complete merely because the policy or workflow files exist.
