# Security Policy

## Reporting a vulnerability

Use GitHub's **Report a vulnerability** flow under the repository Security tab. Do not disclose an unpatched vulnerability in a public issue, discussion, pull request, or social post.

Include the affected version, reproducible steps, expected impact and a minimal proof of concept using synthetic data. Remove credentials, tokens, personal information, banking data and proprietary documents.

## Data and execution boundary

StructuraX v0.4 remains reference-only. The built-in paths use synthetic fixtures and offline recorded replay. Core trust-boundary modules do not perform live OCR/model calls, network requests, tool calls, subprocess execution, deployment, payment, ERP mutation, external notification or autonomous approval.

A finding, AI selection, workflow approval or readiness assessment is evidence for authorized human review; it is not proof of fraud, document authenticity, legal/engineering correctness, regulatory compliance or authorization to act.

## Controlled pilot boundary

v0.4 adds machine-readable RBAC/maker-checker, audit-chain, policy-change, privacy/access/incident and rollback requirements. These contracts describe required controls; they do not prove that an external IAM, network, database, tenant boundary, retention platform or incident process has been deployed correctly.

The committed pilot-readiness artifact is intentionally ineligible without a genuine independent security review. Do not fabricate reviewer identity, independence, findings, evidence, risk acceptance or approval. Follow `security-review/README.md` and bind any real review to the exact repository digest from `scripts/repository_review_digest.py`.

## Supported versions

Security fixes are applied to the latest development minor version. This project remains alpha and does not yet make production-support commitments.
