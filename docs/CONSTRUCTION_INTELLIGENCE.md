# v0.5 Construction Intelligence

StructuraX v0.5 adds a deterministic construction-commercial evidence layer above the
existing ingestion, AI-adapter and controlled-review boundaries. It remains reference-only
and operates on committed synthetic data.

## Authority model

Commercial authority is explicit rather than inferred:

`BOQ -> contract -> approved/effective linked variation order`

`contract -> purchase order -> delivery`

`contract -> purchase order -> invoice`

A contract establishes baseline quantity and unit rate. A variation order changes current
authority only when all of the following are true:

- status is `approved`;
- approval evidence SHA-256 is present;
- an explicit `contract -> variation_order` `amends` lineage edge exists; and
- `effective_at` is not later than the construction case `generated_at` date.

Pending, rejected, unlinked or future-effective variations are never counted as current
commercial authority.

## Three-way and four-way matching

Three-way matching requires purchase-order and delivery evidence for an invoice line and
checks cumulative quantities. Four-way matching additionally requires contract authority
and a declared lineage path from the invoice back to a contract. Matching results are
`matched`, `review`, or `block`; they never authorize payment, procurement or an ERP change.

## BOQ and project-cost controls

The report reconciles contract-plus-effective-approved-variation quantities to BOQ
quantities and calculates:

- BOQ budget total;
- authorized contract/variation value;
- cumulative invoiced value;
- authorized-vs-budget variance; and
- invoiced-vs-budget variance.

Configured threshold breaches produce deterministic review findings. These signals are not
legal interpretations of contract entitlement, valuation, liability or engineering scope.

## Supplier anomaly evidence

Supplier unit-rate anomaly detection uses a deterministic historical median only after the
configured minimum number of observations is present. Observations after the case timestamp
are rejected so the reference cannot leak future information into historical evidence.

A deviation is a review signal; it is explicitly **not proof of fraud, collusion,
overcharging or supplier misconduct**. Historical observations carry evidence digests, but
StructuraX does not establish authenticity of the underlying source records.

## Typed document lineage

Every BOQ, contract, variation, purchase order, delivery and invoice artifact is represented
as a typed node with a source SHA-256 digest. Edges are explicit, unique and canonical.
Relation semantics are fail-closed:

- `authorizes`: BOQ -> contract
- `amends`: contract -> variation order
- `orders_against`: contract -> purchase order
- `fulfills`: purchase order -> delivery
- `invoices_against`: purchase order -> invoice

Unknown artifacts and relation/type substitutions are rejected before analysis. The analyzer
also retains cycle detection as defense-in-depth and identifies invoices whose declared
lineage does not reach a contract.

The graph is provenance evidence only. It does not prove digital-signature validity,
document authenticity, legal enforceability, receipt quality or engineering correctness.

## Deterministic CLI

```bash
structurax construction-analyze \
  --case datasets/construction/clean_case.json \
  --policy configs/construction_policy.json \
  --output reports/local-construction-clean.json
```

The output includes exact input SHA-256, findings, match decisions, project-cost summary and
lineage summary. Output ordering and reference fixtures are deterministic.

## Execution boundary

The v0.5 construction-intelligence core performs no network request, live OCR/model call,
subprocess execution, deployment, payment, ERP mutation, procurement commitment or external
notification. Reports always carry:

```text
automation_authority = false
operational_side_effects_performed = false
```

Findings and match decisions remain human-review evidence and must be interpreted within
the institution's commercial, legal, security and project-control governance.