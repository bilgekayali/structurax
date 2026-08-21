import unittest
from datetime import datetime, timezone

from structurax.construction_intelligence import analyze_construction_case
from structurax.construction_lineage import graph_cycle
from structurax.construction_models import (
    ConstructionIntelligenceCase,
    ConstructionPolicy,
    LineageEdge,
)

D=lambda c:c*64
T0=datetime(2026,8,21,12,0,tzinfo=timezone.utc)


def base_payload():
    nodes=[
        {"artifact_id":"BOQ-001","artifact_type":"boq","source_sha256":D("1")},
        {"artifact_id":"CONTRACT-001","artifact_type":"contract","source_sha256":D("2")},
        {"artifact_id":"DN-001","artifact_type":"delivery","source_sha256":D("3")},
        {"artifact_id":"INV-001","artifact_type":"invoice","source_sha256":D("4")},
        {"artifact_id":"PO-001","artifact_type":"purchase_order","source_sha256":D("5")},
        {"artifact_id":"VO-001","artifact_type":"variation_order","source_sha256":D("6")},
    ]
    edges=sorted([
        {"from_artifact_id":"BOQ-001","to_artifact_id":"CONTRACT-001","relation":"authorizes"},
        {"from_artifact_id":"CONTRACT-001","to_artifact_id":"PO-001","relation":"orders_against"},
        {"from_artifact_id":"CONTRACT-001","to_artifact_id":"VO-001","relation":"amends"},
        {"from_artifact_id":"PO-001","to_artifact_id":"DN-001","relation":"fulfills"},
        {"from_artifact_id":"PO-001","to_artifact_id":"INV-001","relation":"invoices_against"},
    ], key=lambda e:(e["from_artifact_id"],e["to_artifact_id"],e["relation"]))
    return {
        "schema_version":"0.5.0","case_id":"reference-case","project_id":"PRJ-001","generated_at":T0.isoformat(),"currency":"TRY","synthetic_data":True,
        "lineage_nodes":nodes,"lineage_edges":edges,
        "boq_lines":[{"artifact_id":"BOQ-001","item_code":"C30","description":"C30 concrete","unit":"m3","budget_quantity":"100","budget_unit_rate":"1000","budget_amount":"100000"}],
        "contract_lines":[{"artifact_id":"CONTRACT-001","supplier_id":"SUP-001","item_code":"C30","unit":"m3","contracted_quantity":"100","unit_rate":"1000"}],
        "variation_orders":[{"artifact_id":"VO-001","variation_id":"VO-001","supplier_id":"SUP-001","item_code":"C30","status":"approved","quantity_delta":"0","revised_unit_rate":None,"effective_at":"2026-08-01","approval_evidence_sha256":D("a")}],
        "purchase_orders":[{"artifact_id":"PO-001","supplier_id":"SUP-001","item_code":"C30","quantity":"50","unit_rate":"1000"}],
        "deliveries":[{"artifact_id":"DN-001","supplier_id":"SUP-001","item_code":"C30","quantity":"50"}],
        "invoices":[{"artifact_id":"INV-001","supplier_id":"SUP-001","item_code":"C30","quantity":"50","unit_rate":"1000"}],
        "supplier_price_history":[
            {"supplier_id":"SUP-001","item_code":"C30","observed_at":"2026-05-01","unit_rate":"990","evidence_sha256":D("b")},
            {"supplier_id":"SUP-001","item_code":"C30","observed_at":"2026-06-01","unit_rate":"1000","evidence_sha256":D("c")},
            {"supplier_id":"SUP-001","item_code":"C30","observed_at":"2026-07-01","unit_rate":"1010","evidence_sha256":D("d")},
        ],
    }


def case(mutator=None):
    p=base_payload()
    if mutator: mutator(p)
    return ConstructionIntelligenceCase.model_validate(p)


class V05Tests(unittest.TestCase):
    def rules(self, report):
        return {f.rule_id for f in report.findings}

    def test_clean_four_way_match(self):
        r=analyze_construction_case(case())
        self.assertEqual(r.findings, [])
        self.assertEqual(r.matches[0].status.value, "matched")
        self.assertTrue(r.matches[0].four_way_complete)
        self.assertFalse(r.automation_authority)
        self.assertFalse(r.operational_side_effects_performed)

    def test_invoice_quantity_overrun_blocks(self):
        def mutate(p):
            p["invoices"][0]["quantity"]="120"
        r=analyze_construction_case(case(mutate))
        self.assertIn("INVOICE_EXCEEDS_AUTHORIZED_QUANTITY", self.rules(r))
        self.assertIn("THREE_WAY_PO_MISMATCH", self.rules(r))
        self.assertIn("THREE_WAY_DELIVERY_MISMATCH", self.rules(r))
        self.assertIn("PROJECT_INVOICED_COST_OVERRUN", self.rules(r))
        self.assertEqual(r.matches[0].status.value,"block")

    def test_rate_above_authority_blocks(self):
        def mutate(p): p["invoices"][0]["unit_rate"]="1200"
        r=analyze_construction_case(case(mutate))
        self.assertIn("UNIT_RATE_EXCEEDS_AUTHORIZED", self.rules(r))
        self.assertIn("PROJECT_INVOICED_COST_OVERRUN", self.rules(r))
        self.assertEqual(r.matches[0].status.value,"block")

    def test_approved_variation_can_extend_authority(self):
        def mutate(p):
            p["variation_orders"][0]["quantity_delta"]="20"
            p["variation_orders"][0]["revised_unit_rate"]="1100"
            p["boq_lines"][0]["budget_quantity"]="120"
            p["boq_lines"][0]["budget_unit_rate"]="1100"
            p["boq_lines"][0]["budget_amount"]="132000"
            p["purchase_orders"][0]["quantity"]="120"
            p["purchase_orders"][0]["unit_rate"]="1100"
            p["deliveries"][0]["quantity"]="120"
            p["invoices"][0]["quantity"]="120"
            p["invoices"][0]["unit_rate"]="1100"
            p["supplier_price_history"]=[]
        r=analyze_construction_case(case(mutate))
        self.assertNotIn("INVOICE_EXCEEDS_AUTHORIZED_QUANTITY", self.rules(r))
        self.assertNotIn("UNIT_RATE_EXCEEDS_AUTHORIZED", self.rules(r))
        self.assertTrue(r.matches[0].authorized_quantity_ok)
        self.assertTrue(r.matches[0].authorized_rate_ok)

    def test_pending_variation_does_not_extend_authority(self):
        def mutate(p):
            p["variation_orders"][0]["status"]="pending"
            p["variation_orders"][0]["approval_evidence_sha256"]=None
            p["variation_orders"][0]["quantity_delta"]="20"
            p["purchase_orders"][0]["quantity"]="120"
            p["deliveries"][0]["quantity"]="120"
            p["invoices"][0]["quantity"]="120"
        r=analyze_construction_case(case(mutate))
        self.assertIn("INVOICE_EXCEEDS_AUTHORIZED_QUANTITY", self.rules(r))

    def test_future_approved_variation_does_not_extend_current_authority(self):
        def mutate(p):
            p["variation_orders"][0]["effective_at"]="2026-09-01"
            p["variation_orders"][0]["quantity_delta"]="20"
            p["purchase_orders"][0]["quantity"]="120"
            p["deliveries"][0]["quantity"]="120"
            p["invoices"][0]["quantity"]="120"
        r=analyze_construction_case(case(mutate))
        self.assertIn("INVOICE_EXCEEDS_AUTHORIZED_QUANTITY", self.rules(r))
        self.assertFalse(r.matches[0].authorized_quantity_ok)

    def test_approved_variation_requires_contract_lineage(self):
        def mutate(p):
            p["lineage_edges"]=[e for e in p["lineage_edges"] if not (e["from_artifact_id"]=="CONTRACT-001" and e["to_artifact_id"]=="VO-001")]
        r=analyze_construction_case(case(mutate))
        self.assertIn("APPROVED_VARIATION_UNLINKED", self.rules(r))

    def test_supplier_median_anomaly_is_review_signal(self):
        def mutate(p): p["invoices"][0]["unit_rate"]="1300"
        r=analyze_construction_case(case(mutate), ConstructionPolicy(rate_tolerance_percent=50))
        self.assertIn("SUPPLIER_UNIT_RATE_ANOMALY", self.rules(r))
        finding=next(f for f in r.findings if f.rule_id=="SUPPLIER_UNIT_RATE_ANOMALY")
        self.assertEqual(finding.severity.value,"medium")

    def test_future_supplier_history_is_rejected(self):
        p=base_payload()
        p["supplier_price_history"].append(
            {"supplier_id":"SUP-001","item_code":"C30","observed_at":"2026-09-01","unit_rate":"1000","evidence_sha256":D("e")}
        )
        with self.assertRaisesRegex(ValueError,"future observations"):
            ConstructionIntelligenceCase.model_validate(p)

    def test_boq_quantity_variance(self):
        def mutate(p):
            p["variation_orders"][0]["quantity_delta"]="10"
        r=analyze_construction_case(case(mutate))
        self.assertIn("BOQ_QUANTITY_VARIANCE", self.rules(r))

    def test_project_authorized_cost_overrun(self):
        def mutate(p):
            p["variation_orders"][0]["quantity_delta"]="20"
        r=analyze_construction_case(case(mutate))
        self.assertIn("PROJECT_AUTHORIZED_COST_OVERRUN", self.rules(r))

    def test_graph_cycle_helper_detects_cycle(self):
        nodes=["A","B"]
        edges=[
            LineageEdge(from_artifact_id="AAA",to_artifact_id="BBB",relation="amends"),
            LineageEdge(from_artifact_id="BBB",to_artifact_id="AAA",relation="amends"),
        ]
        self.assertTrue(graph_cycle(["AAA","BBB"],edges))

    def test_invalid_lineage_relation_type_pair_fails_closed(self):
        p=base_payload()
        for edge in p["lineage_edges"]:
            if edge["to_artifact_id"]=="INV-001":
                edge["relation"]="authorizes"
        p["lineage_edges"]=sorted(p["lineage_edges"],key=lambda e:(e["from_artifact_id"],e["to_artifact_id"],e["relation"]))
        with self.assertRaisesRegex(ValueError,"authorizes lineage"):
            ConstructionIntelligenceCase.model_validate(p)

    def test_invoice_without_contract_path_is_detected(self):
        def mutate(p):
            p["lineage_edges"]=[e for e in p["lineage_edges"] if e["to_artifact_id"]!="INV-001"]
        r=analyze_construction_case(case(mutate))
        self.assertEqual(r.lineage_summary.invoice_nodes_without_contract_path,["INV-001"])
        self.assertIn("LINEAGE_MISSING_CONTRACT_PATH", self.rules(r))

    def test_line_artifact_type_mismatch_fails_closed(self):
        p=base_payload()
        p["lineage_nodes"][0]["artifact_type"]="invoice"
        with self.assertRaisesRegex(ValueError,"boq"):
            ConstructionIntelligenceCase.model_validate(p)

    def test_nonapproved_variation_cannot_claim_approval_evidence(self):
        p=base_payload()
        p["variation_orders"][0]["status"]="pending"
        with self.assertRaisesRegex(ValueError,"non-approved"):
            ConstructionIntelligenceCase.model_validate(p)

    def test_input_digest_is_deterministic(self):
        r1=analyze_construction_case(case())
        r2=analyze_construction_case(case())
        self.assertEqual(r1.input_sha256,r2.input_sha256)
        self.assertEqual(r1.model_dump(mode="json"),r2.model_dump(mode="json"))


if __name__=='__main__': unittest.main()