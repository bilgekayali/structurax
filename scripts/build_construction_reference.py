"""Build deterministic synthetic v0.5 construction-intelligence fixtures and reports."""
from __future__ import annotations

import json
from pathlib import Path

from structurax.construction_intelligence import analyze_construction_case
from structurax.construction_models import ConstructionIntelligenceCase, ConstructionPolicy

ROOT = Path(__file__).resolve().parents[1]
T0 = "2026-08-21T12:00:00Z"
D = lambda ch: ch * 64


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def clean_payload() -> dict[str, object]:
    edges = sorted([
        {"from_artifact_id":"BOQ-001","to_artifact_id":"CONTRACT-001","relation":"authorizes"},
        {"from_artifact_id":"CONTRACT-001","to_artifact_id":"PO-001","relation":"orders_against"},
        {"from_artifact_id":"PO-001","to_artifact_id":"DN-001","relation":"fulfills"},
        {"from_artifact_id":"PO-001","to_artifact_id":"INV-001","relation":"invoices_against"},
    ], key=lambda e:(e["from_artifact_id"], e["to_artifact_id"], e["relation"]))
    return {
        "schema_version":"0.5.0","case_id":"clean-construction-case","project_id":"PRJ-001","generated_at":T0,
        "currency":"TRY","synthetic_data":True,
        "lineage_nodes":[
            {"artifact_id":"BOQ-001","artifact_type":"boq","source_sha256":D("1")},
            {"artifact_id":"CONTRACT-001","artifact_type":"contract","source_sha256":D("2")},
            {"artifact_id":"DN-001","artifact_type":"delivery","source_sha256":D("3")},
            {"artifact_id":"INV-001","artifact_type":"invoice","source_sha256":D("4")},
            {"artifact_id":"PO-001","artifact_type":"purchase_order","source_sha256":D("5")},
        ],
        "lineage_edges":edges,
        "boq_lines":[{"artifact_id":"BOQ-001","item_code":"C30","description":"C30 concrete","unit":"m3","budget_quantity":"100","budget_unit_rate":"1000","budget_amount":"100000"}],
        "contract_lines":[{"artifact_id":"CONTRACT-001","supplier_id":"SUP-001","item_code":"C30","unit":"m3","contracted_quantity":"100","unit_rate":"1000"}],
        "variation_orders":[],
        "purchase_orders":[{"artifact_id":"PO-001","supplier_id":"SUP-001","item_code":"C30","quantity":"50","unit_rate":"1000"}],
        "deliveries":[{"artifact_id":"DN-001","supplier_id":"SUP-001","item_code":"C30","quantity":"50"}],
        "invoices":[{"artifact_id":"INV-001","supplier_id":"SUP-001","item_code":"C30","quantity":"50","unit_rate":"1000"}],
        "supplier_price_history":[
            {"supplier_id":"SUP-001","item_code":"C30","observed_at":"2026-05-01","unit_rate":"990","evidence_sha256":D("a")},
            {"supplier_id":"SUP-001","item_code":"C30","observed_at":"2026-06-01","unit_rate":"1000","evidence_sha256":D("b")},
            {"supplier_id":"SUP-001","item_code":"C30","observed_at":"2026-07-01","unit_rate":"1010","evidence_sha256":D("c")},
        ],
    }


def risky_payload() -> dict[str, object]:
    payload = clean_payload()
    payload["case_id"] = "risky-construction-case"
    payload["lineage_nodes"] = sorted([
        *payload["lineage_nodes"],
        {"artifact_id":"VO-001","artifact_type":"variation_order","source_sha256":D("6")},
    ], key=lambda n:n["artifact_id"])
    payload["lineage_edges"] = sorted([
        *payload["lineage_edges"],
        {"from_artifact_id":"CONTRACT-001","to_artifact_id":"VO-001","relation":"amends"},
    ], key=lambda e:(e["from_artifact_id"], e["to_artifact_id"], e["relation"]))
    payload["variation_orders"] = [{
        "artifact_id":"VO-001","variation_id":"VO-001","supplier_id":"SUP-001","item_code":"C30",
        "status":"approved","quantity_delta":"20","revised_unit_rate":"1100","effective_at":"2026-08-01",
        "approval_evidence_sha256":D("d"),
    }]
    payload["purchase_orders"][0].update({"quantity":"110","unit_rate":"1100"})
    payload["deliveries"][0]["quantity"] = "90"
    payload["invoices"][0].update({"quantity":"120","unit_rate":"1350"})
    return payload


def main() -> None:
    _write(ROOT / "configs" / "construction_policy.json", ConstructionPolicy().model_dump(mode="json"))
    for label, builder in (("clean", clean_payload), ("risky", risky_payload)):
        case = ConstructionIntelligenceCase.model_validate(builder())
        report = analyze_construction_case(case)
        _write(ROOT / "datasets" / "construction" / f"{label}_case.json", case.model_dump(mode="json"))
        _write(ROOT / "reports" / "evaluation" / f"v0.5-{label}-construction.json", report.model_dump(mode="json"))
        print(f"Built {label}: findings={len(report.findings)}")


if __name__ == "__main__":
    main()
