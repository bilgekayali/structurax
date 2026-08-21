# v0.5 Construction Intelligence

StructuraX v0.5 adds a deterministic construction-commercial evidence layer above the
existing ingestion, AI-adapter and controlled-review boundaries. It remains reference-only
and operates on committed synthetic data.

## Authority model

The commercial authority chain is explicit rather than inferred:

`BOQ -> contract -> approved, linked variation order -> purchase order -> delivery -> invoice`

A contract establishes the baseline quantity and unit rate. A variation order changes that
authority only when its status is `approved`, approval evidence is present, and an explicit
`contract -> variation_order` `amends` lineage edge exists. Pending, rejected or unlinked
variations are never counted as commercial authority.

## Three-way and four-way matching

Three-way matching requires purchase-order and delivery evidence for an invoice line and
checks cumulative quantities. Four-way matching additionally requires contract authority
and a declared lineage path from the invoice back to a contract. Matching results are
`matched`, `review`, or `block`; they never authorize payment or mutate an operational
system.

## BOQ and project-cost controls

The v0.5 report reconciles contract-plus-approved-variation quantities to BOQ quantities,
calculates BOQ budget, authorized contract cost and invoiced cost, and emits deterministic
review findings when configured variance thresholds are exceeded. These are commercial
control signals, not legal interpretations of contract entitlement.

## Supplier anomaly evidence

Supplier unit-rate anomaly detection uses the deterministic historical median only after
the configured minimum number of observations is present. A deviation is a review signal;
it is explicitly **not proof of fraud, collusion, overcharging or supplier misconduct**.
Historical observations must carry evidence digests, but StructuraX does not establish the
authenticity of the underlying source records.

## Document lineage graph

Every BOQ, contract, variation, purchase order, delivery and invoice artifact is represented
as a typed node with a source SHA-256 digest. Edges are explicit and canonical. The analyzer
checks for cycles and for invoices whose lineage does not reach a contract.

The graph is provenance evidence only. It does not prove digital-signature validity,
document authenticity, legal enforceability, receipt quality or engineering correctness.

## Execution boundary

The v0.5 construction-intelligence core performs no network request, live OCR/model call,
subprocess execution, deployment, payment, ERP mutation or external notification. Reports
always carry:

```text
automation_authority = false
operational_side_effects_performed = false
```

Findings and match decisions remain human-review evidence and must be interpreted within
the institution's commercial, legal, security and project-control governance.
