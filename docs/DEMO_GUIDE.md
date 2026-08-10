# Demo Guide

The StructuraX demo is credential-free and runs only against committed synthetic JSON packs. It does not upload files, call a model, access a live system, or perform a paid API request.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[demo]'
python app.py
```

Open `http://localhost:7860`.

## Scenarios

### Clean synthetic pack

Four internally consistent documents produce zero findings and an `allow` disposition. In this demo, `allow` means only that the configured deterministic controls found no signal. It is not an approval, authenticity claim, or authorization to pay.

### Risky synthetic pack

Five documents contain deliberate inconsistencies and unsafe content. The engine produces 13 findings—4 critical and 9 high—and a `block` disposition. The table shows each rule and the source fields supporting the finding.

## Presenter flow

1. Run the clean scenario and explain the limited meaning of `allow`.
2. Run the risky scenario and point to evidence rather than only the severity label.
3. Open the committed Markdown report to show reproducibility.
4. Explain that source authenticity and consequential decisions remain with authorized reviewers.
5. Use the roadmap to distinguish the current deterministic foundation from future OCR or model adapters.

## Safety note

Use the demo only with its synthetic fixtures. Do not paste, upload, or adapt real banking, supplier, employee, customer, or project data into a public deployment.

