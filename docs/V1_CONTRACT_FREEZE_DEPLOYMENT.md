# v1.0 Contract Freeze and Deployment Reference

This milestone freezes the bounded public API and committed schema surface for the v1.0
release candidate while adding executable deployment and observability reference controls.
It does not promote StructuraX to version 1.0.0 and does not claim production readiness.

## Frozen compatibility surface

`configs/stable_api_contract.json` now defines an exact public export set, symbol module/kind
identity, and a deterministic SHA-256 surface digest. Additive exports are not silently
accepted: any change requires explicit compatibility review and a new baseline.

`configs/stable_schema_contract.json` pins all 23 committed `*.schema.json` files by Git blob
content identity. The verifier also requires the exact schema count, root object shape, unique
titles, and no unreviewed additions or removals. Any schema content change therefore requires
an explicit compatibility-baseline update.

The release-candidate gate may mark only the API/schema freeze controls complete. Package
version, deployment validation, repository governance, release evidence and independent review
remain separate fail-closed requirements.

## Deployment reference

`configs/deployment_reference.json` and `structurax.deployment_reference` define a bounded
reference posture:

- non-root runtime;
- read-only root filesystem;
- no privileged execution or privilege escalation;
- outbound network default-deny;
- TLS 1.3 minimum and database TLS required;
- immutable image digest required;
- no runtime dependency installation;
- secrets supplied only as external references;
- no evidence key material in configuration;
- metadata-only OTLP/HTTPS observability reference;
- no raw document, prompt or secret export.

The validation workflow creates a deterministic metadata-only observability record and verifies
these invariants. It does not deploy infrastructure, contact a production telemetry backend,
validate a Kubernetes/ECS/VM policy, or inspect real secret-management configuration.

## Non-claims

A passing reference validation is not evidence that a production environment actually enforces
these controls. `observability_and_deployment_controls_validated` remains false until the exact
production architecture and deployment are independently validated. The same distinction applies
to production PostgreSQL, identity, KMS/HSM, branch protection, release attestations and the
required independent security review.
