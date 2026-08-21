# v0.2 Fixture Data Lineage

StructuraX v0.2 keeps document-ingestion evaluation fully synthetic and repository-local.
No customer, supplier, employee, project, banking, credential, or production-system data
is used by the committed fixture set.

## Fixture chain

1. Four small synthetic PDF-like files are committed under `datasets/ingestion/`.
2. SHA-256 digests bind every file to `manifest.json`.
3. The manifest is signed with Ed25519; only the public key and signature are committed.
   The one-time private key used to sign this fixture-set revision is intentionally not
   stored in the repository.
4. `recorded_extractions.json` binds accepted source digests to deterministic page text.
   The built-in replay adapter has no network, subprocess, filesystem-write, or external
   model capability.
5. CI verifies the signature and each exact fixture digest before exercising ingestion.

The signature establishes integrity for this committed synthetic fixture revision. It is
not an organizational identity proof, software-supply-chain attestation, or production
trust anchor.

## Adversarial cases

- `clean-invoice.pdf` — accepted and replayed deterministically.
- `embedded-instruction.pdf` — accepted as untrusted content so downstream security rules
  can observe a deliberate control-bypass phrase.
- `active-content.pdf` — rejected before adapter invocation because the strict v0.2 PDF
  preflight detects an active-content marker.
- `truncated.pdf` — rejected before adapter invocation because the terminal PDF marker is
  missing.

These files are a boundary-regression corpus, not a PDF parser conformance suite or
malware-detection benchmark.

## Rule-family labels

`datasets/evaluation/rule_cases.json` contains human-authored expected rule IDs for the
committed clean and risky normalized packs. `scripts/evaluate_rule_cases.py` runs the
actual deterministic engine and calculates precision/recall evidence by rule family.
The resulting metrics are regression evidence only; they must not be represented as
production fraud-detection accuracy.
