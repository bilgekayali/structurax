# v0.4 Controlled Pilot Deployment Reference

This document describes the checkpoints a future controlled pilot must satisfy. It is not a deployment procedure and the repository performs no deployment.

## Required checkpoints

The machine contract requires exactly four human checkpoints:

1. business owner approval;
2. privacy review;
3. security review;
4. workflow owner approval.

The committed checkpoint evidence is explicitly `synthetic_reference`. It demonstrates schema and gating behavior only.

## Readiness gate

`scripts/evaluate_pilot_controls.py` produces two deterministic reports:

- `reports/evaluation/v0.4-red-team.json`;
- `reports/evaluation/v0.4-pilot-readiness.json`.

The red-team exercise attacks the reference controls for audit tampering, maker-checker self-approval, unauthorized approval ownership, policy substitution, and missing independent review.

The committed readiness result is intentionally **ineligible** because a genuine independent security review is absent. Source code may be reviewed and merged without fabricating that evidence, but no pilot-ready claim should be made until the independent review exists, binds the exact repository digest, and all gates are re-run.

## Rollback and stop conditions

A real pilot should stop or roll back on evidence-chain integrity failure, access-control failure, unexplained model/provider behavior, privacy or security incident, policy mismatch, missing human checkpoint, or inability to preserve required records. Any operational rollback remains an authorized human action outside StructuraX core.

## Non-claims

v0.4 does not prove deployed tenant isolation, IAM correctness, malware safety, legal compliance, contractual correctness, fraud detection, model safety, factuality, or supervisory acceptance. It does not perform live OCR/model calls, deployment, payment, ERP mutation, or autonomous approval.
