"""End-to-end deterministic analysis tests."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from structurax.engine import analyze_pack
from structurax.loader import load_pack, load_policy
from structurax.models import Disposition
from structurax.reporting import write_report


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "configs" / "default_policy.json"
CLEAN_PACK = ROOT / "datasets" / "demo" / "clean_pack.json"
RISKY_PACK = ROOT / "datasets" / "demo" / "risky_pack.json"


class EngineTests(unittest.TestCase):
    def test_clean_pack_is_allowed_without_findings(self) -> None:
        report = analyze_pack(load_pack(CLEAN_PACK), load_policy(POLICY))
        self.assertEqual(report.summary.disposition, Disposition.ALLOW)
        self.assertEqual(report.summary.finding_count, 0)
        self.assertFalse(report.summary.requires_human_review)

    def test_risky_pack_is_blocked_with_expected_controls(self) -> None:
        report = analyze_pack(load_pack(RISKY_PACK), load_policy(POLICY))
        rule_ids = {finding.rule_id for finding in report.findings}
        self.assertEqual(report.summary.disposition, Disposition.BLOCK)
        self.assertTrue(report.summary.requires_human_review)
        self.assertTrue(
            {
                "ARITHMETIC_TOTAL",
                "BANK_ACCOUNT_CHANGE",
                "DUPLICATE_INVOICE",
                "EMBEDDED_INSTRUCTION",
                "INVOICE_EXCEEDS_DELIVERY",
                "MISSING_APPROVAL",
                "UNIT_PRICE_VARIANCE",
            }
            <= rule_ids
        )

    def test_input_hash_is_deterministic(self) -> None:
        pack = load_pack(RISKY_PACK)
        policy = load_policy(POLICY)
        timestamp = datetime(2026, 8, 5, tzinfo=UTC)
        first = analyze_pack(pack, policy, generated_at=timestamp)
        second = analyze_pack(pack, policy, generated_at=timestamp)
        self.assertEqual(first.input_sha256, second.input_sha256)
        self.assertEqual(first, second)

    def test_json_and_markdown_reports_are_written(self) -> None:
        report = analyze_pack(load_pack(RISKY_PACK), load_policy(POLICY))
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path, markdown_path = write_report(report, temp_dir)
            self.assertTrue(json_path.is_file())
            self.assertTrue(markdown_path.is_file())
            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("BANK_ACCOUNT_CHANGE", markdown)
            self.assertIn("does not approve payments", markdown)

    def test_committed_demo_reports_are_reproducible(self) -> None:
        policy = load_policy(POLICY)
        for pack_path, report_dir in (
            (CLEAN_PACK, ROOT / "reports" / "demo" / "clean-pack"),
            (RISKY_PACK, ROOT / "reports" / "demo" / "risky-pack"),
        ):
            pack = load_pack(pack_path)
            report = analyze_pack(
                pack,
                policy,
                generated_at=pack.generated_at,
            )
            with tempfile.TemporaryDirectory() as temp_dir:
                json_path, markdown_path = write_report(report, temp_dir)
                self.assertEqual(
                    json_path.read_bytes(),
                    (report_dir / "report.json").read_bytes(),
                )
                self.assertEqual(
                    markdown_path.read_bytes(),
                    (report_dir / "report.md").read_bytes(),
                )


if __name__ == "__main__":
    unittest.main()
