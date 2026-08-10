"""Credential-free demo behavior tests."""

from __future__ import annotations

import unittest

from app import analyze_scenario


class DemoTests(unittest.TestCase):
    def test_clean_scenario(self) -> None:
        summary, rows = analyze_scenario("Clean synthetic pack")
        self.assertIn("ALLOW", summary)
        self.assertEqual(rows, [])

    def test_risky_scenario(self) -> None:
        summary, rows = analyze_scenario("Risky synthetic pack")
        self.assertIn("BLOCK", summary)
        self.assertEqual(len(rows), 13)
        self.assertTrue(any(row[1] == "EMBEDDED_INSTRUCTION" for row in rows))


if __name__ == "__main__":
    unittest.main()
