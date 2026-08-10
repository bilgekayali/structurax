# Contributing to StructuraX

Thank you for helping improve trustworthy construction document workflows.

## Safety and data rules

- Use synthetic data only.
- Never commit real customer, supplier, employee, project, bank-account, credential, or proprietary document data.
- Keep v0.1 analysis deterministic and free of operational side effects.
- Attach field-level evidence to every new finding.
- Recommend human verification through an independent, authorized channel when appropriate.
- Do not describe a risk signal as confirmed fraud, legal truth, or an engineering determination.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Proposing a rule

A rule contribution should include:

1. A stable rule ID and clearly bounded purpose.
2. Synthetic positive and negative examples.
3. Deterministic logic with explicit policy thresholds where needed.
4. Document-and-field evidence for every result.
5. A safe recommendation that preserves human authority.
6. Tests for detection, non-detection, ordering, and report stability.

After changing models, rules, policy, or demo inputs, regenerate and verify committed artifacts:

```bash
python scripts/generate_schema.py
python scripts/build_demo_reports.py
python -m unittest discover -s tests -v
```

## Pull requests

Keep changes focused, explain their trust impact, and identify any new data or execution boundary. CI must pass without secrets. If a change introduces OCR, a model, a network request, or a side effect, document it as an explicit extension boundary rather than silently adding it to the deterministic core.

