# v1.0 Formal Promotion Transaction

StructuraX uses a two-phase release transaction so external security and production evidence can remain bound to the reviewed source while the final package version is still withheld until every non-version gate is satisfied.

## Release-surface digest

`scripts/release_surface_digest.py` computes `sha256-release-surface-v1` across Git-tracked repository content. It excludes only evidence envelopes that would otherwise create circular hashes and canonicalizes only three mechanical release metadata fields:

- `pyproject.toml` project version;
- `pyproject.toml` development-status classifier; and
- `src/structurax/__init__.py` `__version__`.

No source code, schema, workflow, dependency declaration, security policy or other tracked configuration is excluded or normalized. A real implementation or policy change therefore changes the release-surface digest and invalidates evidence bound to the previous surface.

## Phase A — evidence-complete pre-promotion state

The package remains `0.5.0`. Production evidence, repository governance, release supply-chain evidence and the genuine independent security review must all verify against the same release-surface digest. At this point `Promotion Readiness` is expected to have exactly one blocker: `package_version_not_1_0_0`.

`scripts/build_formal_promotion_plan.py` accepts that state only when every formal candidate check is true and the version blocker is the sole remaining blocker. It then emits a non-mutating plan for the exact approved Git head.

## Phase B — mechanical metadata promotion

The plan permits exactly three metadata changes:

1. package version `0.5.0` to `1.0.0` in `pyproject.toml`;
2. development classifier `Alpha` to `Production/Stable`; and
3. `structurax.__version__` `0.5.0` to `1.0.0`.

Those changes must leave the release-surface digest unchanged. After the metadata-only commit, the complete test/gate suite must run again and promotion readiness must pass at `1.0.0` before any tag or publication is authorized.

## Human authority

The transaction is deliberately non-executing. It does not edit files, create `v1.0.0`, publish a package, mutate the formal gate or claim production readiness. `configs/formal_promotion_policy.json` keeps metadata mutation, tag creation and publishing automatic authority disabled.

A human-reviewed release approval must verify the exact commit, unchanged release-surface digest, final attestations, branch protection, production-control evidence and independent review before the release tag is created.

## Why this exists

Binding evidence to the ordinary repository digest would make a final version-only commit invalidate otherwise valid review and production evidence. Binding evidence to a digest that ignored whole metadata files would be too broad. The release-surface digest avoids both problems by normalizing only explicitly enumerated promotion fields while keeping every other byte security-significant.
