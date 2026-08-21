"""Regenerate committed v0.2 rule-family regression metrics."""

from __future__ import annotations

import json
from pathlib import Path

from structurax.engine import analyze_pack
from structurax.evaluation import ObservedRuleCase, RuleEvaluationCase, evaluate_rule_families
from structurax.loader import load_pack, load_policy

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "datasets" / "evaluation" / "rule_cases.json"
OUTPUT = ROOT / "reports" / "evaluation" / "v0.2-rule-metrics.json"
POLICY = ROOT / "configs" / "default_policy.json"


def main() -> None:
    payload = json.loads(CASES.read_text(encoding="utf-8"))
    expected: list[RuleEvaluationCase] = []
    observed: list[ObservedRuleCase] = []
    for case in payload["cases"]:
        pack_path = (ROOT / case["pack_path"]).resolve()
        pack_path.relative_to(ROOT.resolve())
        expected.append(
            RuleEvaluationCase(
                case_id=case["case_id"],
                expected_rule_ids=case["expected_rule_ids"],
            )
        )
        report = analyze_pack(load_pack(pack_path), load_policy(POLICY))
        observed.append(
            ObservedRuleCase(
                case_id=case["case_id"],
                observed_rule_ids=sorted({finding.rule_id for finding in report.findings}),
            )
        )
    metrics = evaluate_rule_families(expected, observed)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(metrics.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
