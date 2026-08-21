# StructuraX v1.0 Release Promotion Runbook

This runbook operationalizes the remaining external v1.0 controls. It does not declare StructuraX production-ready and it does not authorize automatic mutation of the formal release gate.

## 1. Preconditions

Start from the exact accepted `main` commit. Confirm the normal CI, release gates, security reference validation, deployment reference validation, release evidence validation, production evidence harness, repository governance, promotion readiness, and CodeQL checks are green for the candidate.

Do not change the package version to `1.0.0` before all external evidence is verified and a human-reviewed promotion change is approved.

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

The connected automation used by this project cannot perform the branch-protection mutation. An administrator with permission to edit repository rules must apply the generated `payload` through GitHub settings or the REST endpoint.

Do not paste a token into repository files, issues, PR comments, CI logs, or committed shell scripts. Use an ephemeral environment variable or the GitHub UI.

Example shape:

```bash
curl -L \
  -X PUT \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_ADMIN_TOKEN" \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  "https://api.github.com/repos/bilgekayali/structurax/branches/main/protection" \
  --data-binary @<(python -c 'import json; print(json.dumps(json.load(open("/tmp/structurax-branch-protection.json"))["payload"]))')
```

Equivalent GitHub UI configuration is acceptable if the resulting state matches the generated policy exactly.

## 4. Capture and verify the resulting protection state

Capture the full branch-protection response outside the repository:

```bash
curl -L \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_ADMIN_TOKEN" \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  "https://api.github.com/repos/bilgekayali/structurax/branches/main/protection" \
  > /tmp/structurax-main-protection.json
```

Verify it:

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

The live branch summary and the full protection snapshot must agree.

## 5. Verify production control evidence

Production evidence must be created by the authorized environment validator and signed with the trusted Ed25519 validator key kept outside the repository.

```bash
python scripts/verify_production_evidence.py \
  --evidence production-evidence/v1.0-controls.json \
  --trusted-public-key /secure/path/production-validator.pub
```

The evidence must bind the exact canonical repository digest and independently pass PostgreSQL tenant isolation, external identity, evidence encryption/key management, and observability/deployment controls. Do not commit raw endpoints, credentials, connection strings, tokens, keys, or production document content.

## 6. Verify the independent security review

A genuine independent reviewer must provide `security-review/v1.0-review.json` bound to the same exact repository digest.

```bash
python scripts/verify_independent_review.py \
  --review security-review/v1.0-review.json
```

The repository owner or implementation assistant must not fabricate this evidence.

## 7. Produce and verify final release supply-chain evidence

Run the manual `Release Evidence Attestation` workflow for the exact accepted candidate only after the independent review and production evidence are available. Verify the generated wheel, dependency SBOM, source provenance, evidence manifest, and GitHub attestations against the same candidate.

The existing preview workflow is not, by itself, proof that `complete_release_sbom_attached` or `build_provenance_attested` may be set to true. Retain the attestation verification output as release evidence.

## 8. Generate the consolidated promotion matrix

After obtaining the full protection snapshot, production evidence, trusted validator key, and independent review:

```bash
python scripts/assess_promotion_readiness.py \
  --repository bilgekayali/structurax \
  --branch main \
  --protection-snapshot /tmp/structurax-main-protection.json \
  --production-evidence production-evidence/v1.0-controls.json \
  --trusted-production-key /secure/path/production-validator.pub \
  --independent-review security-review/v1.0-review.json
```

The report is diagnostic. Even when every candidate check is true, it returns `formal_gate_mutation_authorized: false`.

## 9. Human-reviewed formal promotion

Only after all evidence is independently verified:

1. Prepare a dedicated promotion PR.
2. Update `configs/release_candidate_gate.json` only for controls supported by exact evidence.
3. Change the package version to `1.0.0`.
4. Rebuild the release artifact from that exact promotion commit.
5. Re-run every required status check and final attestation.
6. Require the configured approval and conversation-resolution controls.
7. Merge only if the final promotion matrix has no blockers.

`formal_release_eligible` must remain false until that explicit promotion PR. Do not infer production readiness from reference tests, preview attestations, synthetic validation, or repository documentation alone.
