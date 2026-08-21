# v0.4 Pilot Security, Privacy, and Incident Boundaries

The v0.4 pilot plan is a machine-readable **reference design**, not a deployed control attestation.

## Privacy and retention

The reference data-handling profile requires a bounded retention period, least privilege, authorized-human deletion, no secrets in evidence, and no raw document text in audit events. A real pilot must separately determine lawful basis, data-subject obligations, retention schedules, cross-border restrictions, records requirements, and contractual duties for its jurisdiction and organization.

## Access control

The reference access profile requires default deny, MFA for human users, non-interactive service accounts, tenant separation, and reviewed break-glass access. These fields express required architecture; they do not prove that an IAM, network, database, or tenant boundary has been deployed correctly.

## Incident response

The pilot profile requires named ownership and defined processes for security incidents, privacy incidents, and AI/control failures. Human notification is required; the reference core cannot autonomously send external notifications or make legal/regulatory reporting decisions.

## Rollback

A pilot plan must name a rollback owner, require backups, bind rollback-test evidence by SHA-256, define a recovery-time bound, and prohibit automatic rollback without a human. The committed rollback evidence is synthetic reference evidence only.

## Independent security review

StructuraX must not self-attest independent review. A genuine reviewer who is independent from implementation must review the exact repository state and create `security-review/v0.4-review.json` according to `independent-security-review.schema.json`.

The reviewer records the exact repository digest from:

```bash
python scripts/repository_review_digest.py
```

The digest covers every Git-tracked regular file except the final review JSON itself. Any other tracked source change after review invalidates the reviewed digest.
