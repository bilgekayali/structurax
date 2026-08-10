"""CLI smoke tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from structurax.cli import main


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "configs" / "default_policy.json"
CLEAN_PACK = ROOT / "datasets" / "demo" / "clean_pack.json"
RISKY_PACK = ROOT / "datasets" / "demo" / "risky_pack.json"


class CliTests(unittest.TestCase):
    def test_validate_command(self) -> None:
        self.assertEqual(main(["validate", "--pack", str(CLEAN_PACK)]), 0)

    def test_analyze_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = main(
                [
                    "analyze",
                    "--pack",
                    str(RISKY_PACK),
                    "--policy",
                    str(POLICY),
                    "--output-dir",
                    temp_dir,
                ]
            )
            self.assertEqual(result, 0)
            self.assertTrue((Path(temp_dir) / "report.json").is_file())


if __name__ == "__main__":
    unittest.main()
