# StructuraX v1.0 Release Promotion Runbook

This runbook operationalizes the remaining external v1.0 controls. It does not declare StructuraX production-ready and it does not authorize automatic mutation of the formal release gate.

## 1. Preconditions

Start from the exact accepted `main` commit. Confirm the normal CI, release gates, security reference validation, deployment reference validation, release evidence validation, production evidence collection/harness, repository governance, promotion readiness, formal promotion transaction, and CodeQL checks are green for the candidate.

Do not change the package version to `1.0.0` before all external evidence is verified and a human-reviewed promotion change is approved.

All production and v1.0 independent-review evidence must bind `sha256-release-surface-v1`, not the ordinary repository-review digest.

## 2. Generate the exact branch-protection payload

The repository policy is the source of truth for the required contexts and review controls.

```bash
python scripts/build_branch_protection_payload.py \
  --repository bilgekayali/structurax \
  --branch main \
  --output /tmp/structurax-branch-protection.json
cat /tmp/structurax-branch-protection.json
```

The generated document targets:

`PUT https://api.github.com/repos/bilgekayali/structurax/branches/main/protection`

with GitHub REST API version `2026-03-10`.

The payload requires strict status checks, pull-request review, one approval, stale-review dismissal, last-push approval, administrator enforcement, conversation resolution, blocked force pushes, and blocked branch deletion. It also requires every status context listed in `configs/repository_governance_policy.json`.

## 3. Apply branch protection as a repository administrator

The connected automation used by this project cannot perform the branch-protection mutation. An administrator with permission to edit repository rules must apply the generated policy through GitHub settings or the REST endpoint.

Do not paste a token into repository files, issues, PR comments, CI logs, or committed shell scripts. Use an ephemeral environment variable or the GitHub UI.

Equivalent GitHub Ruleset configuration is acceptable if the resulting state matches the repository governance policy exactly.

## 4. Capture and verify the resulting protection state

Capture the full protection/ruleset state through an authenticated administrative session and retain it outside the repository as release evidence.

For classic branch protection, the REST shape may be captured with:

```bash
curl -L \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_ADMIN_TOKEN" \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  "https://api.github.com/repos/bilgekayali/structurax/branches/main/protection" \
  > /tmp/structurax-main-protection.json
```

Verify a compatible protection snapshot:

```bash
python scripts/verify_branch_protection_snapshot.py \
  --snapshot /tmp/structurax-main-protection.json
```

A valid report must show:

- `main_branch_protection_verified: true`
- `required_status_checks_verified: true`
- `codeql_release_gate_enforced: true`
- `manual_controls_verified: true`
- an empty `blockers` array
- `formal_gate_mutation_authorized: false`

Also run the public/live branch assessment:

```bash
python scripts/assess_repository_governance.py \
  --repository bilgekayali/structurax \
  --branch main
```

The live branch summary and the authenticated ruleset/protection evidence must agree.

## 5. Verify production control evidence

Production evidence must be created by the authorized environment validator and signed with the trusted Ed25519 validator key kept outside the repository.

Follow `docs/PRODUCTION_EVIDENCE_COLLECTION.md` to produce the secret-free receipts, unsigned statement, canonical signing payload, external signature, and final envelope.

Then verify:

```bash
python scripts/verify_production_evidence.py \
  --evidence production-evidence/v1.0-controls.json \
  --trusted-public-key /secure/path/production-validator.pub
```

The evidence must bind the exact `sha256-release-surface-v1` digest and independently pass PostgreSQL tenant isolation, external identity, evidence encryption/key management, and observability/deployment controls. Do not commit raw endpoints, credentials, connection strings, tokens, keys, or production document content.

## 6. Obtain and verify the genuine independent security review

Generate the reviewer handoff from the exact accepted candidate:

```bash
python scripts/build_independent_review_handoff.py \
  --repository bilgekayali/structurax \
  --output /tmp/structurax-independent-review-handoff.json
cat /tmp/structurax-independent-review-handoff.json
```

Send the reviewer:

- the exact source commit SHA;
- the generated release-surface digest;
- `docs/INDEPENDENT_SECURITY_REVIEW_HANDOFF.md`;
- `configs/independent_security_review_policy.json`; and
- `release-evidence-schemas/independent-security-review-evidence.schema.json`.

A genuine independent reviewer must return:

1. the detailed review report through the secure evidence channel; and
2. `security-review/v1.0-review.json`, using schema version `1.0.0`.

The detailed report must remain outside the public repository. Its exact bytes are bound by SHA-256 from the envelope.

Verify both the envelope and the external report:

```bash
python scripts/verify_independent_review.py \
  --review security-review/v1.0-review.json \
  --evidence-file /secure/path/to/external-review-report \
  --required-schema-version 1.0.0
```

The repository owner, implementation author, CI system, or implementation assistant must not self-attest. CI/reference tests do not satisfy this gate.

## 7. Produce and verify final release supply-chain evidence

Run the manual `Release Evidence Attestation` workflow for the exact accepted candidate only after the independent review and production evidence are available. Verify the generated wheel, dependency SBOM, source provenance, evidence manifest, and GitHub attestations against the same candidate.

The existing preview workflow is not, by itself, proof that `complete_release_sbom_attached` or `build_provenance_attested` may be set to true. Retain the attestation verification output as release evidence.

## 8. Generate the consolidated promotion matrix

After obtaining the authenticated protection/ruleset evidence, production evidence, trusted validator key, independent review envelope, and external review report:

```bash
python scripts/assess_promotion_readiness.py \
  --repository bilgekayali/structurax \
  --branch main \
  --protection-snapshot /tmp/structurax-main-protection.json \
  --production-evidence production-evidence/v1.0-controls.json \
  --trusted-production-key /secure/path/production-validator.pub \
  --independent-review security-review/v1.0-review.json \
  --independent-review-evidence /secure/path/to/external-review-report
```

The report is diagnostic. Even when every candidate check is true, it returns `formal_gate_mutation_authorized: false`.

In the evidence-complete pre-promotion phase, the only remaining blocker should be `package_version_not_1_0_0`.

## 9. Human-reviewed formal promotion

Only after all evidence is independently verified:

1. Prepare a dedicated promotion PR.
2. Update `configs/release_candidate_gate.json` only for controls supported by exact evidence.
3. Change only the allowlisted release metadata from `0.5.0` to `1.0.0`.
4. Verify the release-surface digest remains unchanged across that metadata-only change.
5. Rebuild the release artifact from that exact promotion commit.
6. Re-run every required status check and final attestation.
7. Require the configured approval and conversation-resolution controls.
8. Merge only if the final promotion matrix has no blockers.
9. Create `v1.0.0` tag/publication only after the accepted promotion commit is fully verified.

`formal_release_eligible` must remain false until that explicit promotion PR. Do not infer production readiness from reference tests, preview attestations, synthetic validation, repository documentation, or an unverified external report digest alone.
