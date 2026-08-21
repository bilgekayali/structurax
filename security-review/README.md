# StructuraX v0.4 Independent Security Review

A completed independent review is intentionally **not** committed by the implementation milestone.

An independent reviewer should:

1. review the exact source state intended for the controlled pilot;
2. run `python scripts/repository_review_digest.py` and record the resulting SHA-256;
3. review the v0.1-v0.4 trust boundaries, including ingestion, AI replay, workflow RBAC, maker-checker controls, policy replacement, audit-chain integrity, privacy/access/incident requirements, rollback, and non-claims;
4. create `security-review/v0.4-review.json` matching `schemas/independent-security-review.schema.json`;
5. state their real reviewer identity and explicitly confirm independence from implementation;
6. provide a SHA-256 evidence digest that points to their retained review evidence.

Do not infer reviewer independence from repository ownership, PR approval, CI success, merge approval, or release authorization. Do not fabricate reviewer identity, review evidence, findings, or residual-risk acceptance.

The repository digest script excludes only `security-review/v0.4-review.json`; any other tracked change after review changes the digest and requires re-review/revalidation.
