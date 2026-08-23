# StructuraX v1.0 Independent Security Review Handoff

This handoff defines the minimum evidence required for a **genuine independent** security review of the v1.0 release surface. It does not perform the review, select the reviewer, create review evidence, or authorize release promotion.

## Reviewer independence

The reviewer must be organizationally independent from the implementation work being assessed. The repository owner, implementation author, CI system, coding assistant, or any party materially responsible for producing the reviewed changes must not self-attest as the independent reviewer.

The reviewer must explicitly confirm independence in the v1.0 evidence envelope.

## Exact source binding

The review must target one exact Git commit and the corresponding `sha256-release-surface-v1` digest.

After checking out the accepted candidate:

```bash
git rev-parse HEAD
python scripts/release_surface_digest.py
python scripts/build_independent_review_handoff.py \
  --repository bilgekayali/structurax \
  --output /tmp/structurax-independent-review-handoff.json
cat /tmp/structurax-independent-review-handoff.json
```

Do not reuse a review after source, schema, workflow, dependency, security-policy, or other digest-significant content changes. The only normalized fields are the three mechanical release metadata fields defined by the formal promotion transaction.

## Required review areas

The reviewer must cover every area in `configs/independent_security_review_policy.json`:

- application trust boundaries;
- cryptography and evidence integrity;
- dependency and supply chain;
- deployment and observability;
- identity and authorization;
- ingestion and untrusted content;
- release governance;
- tenant isolation; and
- workflow authority and audit.

At minimum, the assessment should combine manual source review, threat-model reasoning, negative-path testing, review of CI/release workflow permissions, dependency/supply-chain inspection, and verification of the repository's fail-closed authority boundaries.

## Acceptance threshold

For v1.0 promotion, the reviewer evidence must state:

- `review_outcome: "passed"`;
- zero open **critical** findings;
- zero open **high** findings;
- zero open release-blocking findings;
- no unresolved risk acceptance requirement;
- exact required review-area coverage;
- no raw secret material in the committed evidence envelope; and
- no production-readiness claim.

Medium, low, and informational findings may be recorded numerically, but any finding the reviewer considers release-blocking must keep the release blocked.

## External report handling

The detailed security report must remain outside the public repository in the organization's governed evidence store. It may contain sensitive attack paths or implementation detail and should be shared through the agreed secure channel.

The reviewer supplies:

1. an opaque external report artifact identifier;
2. the SHA-256 digest of the exact report bytes;
3. the report itself through the secure evidence channel; and
4. `security-review/v1.0-review.json`, conforming to `release-evidence-schemas/independent-security-review-evidence.schema.json`.

The committed JSON envelope contains only non-sensitive metadata and the report digest. The verifier recomputes the SHA-256 of the externally supplied report and rejects any mismatch.

## Verification

When the report and envelope are returned:

```bash
python scripts/verify_independent_review.py \
  --review security-review/v1.0-review.json \
  --evidence-file /secure/path/to/external-review-report \
  --required-schema-version 1.0.0
```

For the final promotion-readiness run:

```bash
python scripts/assess_promotion_readiness.py \
  --repository bilgekayali/structurax \
  --branch main \
  --protection-snapshot /secure/path/structurax-main-protection.json \
  --production-evidence production-evidence/v1.0-controls.json \
  --trusted-production-key /secure/path/production-validator.pub \
  --independent-review security-review/v1.0-review.json \
  --independent-review-evidence /secure/path/to/external-review-report
```

A valid independent-review result is necessary but not sufficient for v1.0. Production evidence, repository governance, final SBOM/provenance attestations, package promotion, and explicit human release approval remain separate gates.

## What does not count

The following do **not** satisfy the independent-review gate:

- normal CI or CodeQL success by itself;
- the repository's synthetic red-team/reference tests;
- an implementation-author self-review;
- a review generated only by the same coding assistant that produced the implementation;
- an envelope whose external report is unavailable for SHA-256 verification;
- a report bound to a different release-surface digest; or
- a report with unresolved critical, high, or release-blocking findings.

No repository script may mutate the formal release gate merely because a review envelope verifies.
