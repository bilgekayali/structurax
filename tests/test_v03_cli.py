from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from structurax.cli import main

ROOT = Path(__file__).resolve().parents[1]
AI_DIR = ROOT / "datasets" / "ai"


class V03CliTests(unittest.TestCase):
    def test_ai_replay_clean_and_injection_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            clean = Path(temp_dir) / "clean.json"
            injection = Path(temp_dir) / "injection.json"
            self.assertEqual(
                main([
                    "ai-replay",
                    "--cases", str(AI_DIR / "benchmark_cases.json"),
                    "--case-id", "clean-invoice",
                    "--recordings", str(AI_DIR / "recorded_adapter_a.json"),
                    "--output", str(clean),
                ]),
                0,
            )
            self.assertEqual(json.loads(clean.read_text())["status"], "ai_selected")
            self.assertEqual(
                main([
                    "ai-replay",
                    "--cases", str(AI_DIR / "benchmark_cases.json"),
                    "--case-id", "prompt-injection-invoice",
                    "--recordings", str(AI_DIR / "recorded_adapter_a.json"),
                    "--output", str(injection),
                ]),
                0,
            )
            payload = json.loads(injection.read_text())
            self.assertEqual(payload["status"], "deterministic_fallback")
            self.assertFalse(payload["adapter_invoked"])

    def test_ai_benchmark_has_no_live_model_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "benchmark.json"
            self.assertEqual(
                main([
                    "ai-benchmark",
                    "--cases", str(AI_DIR / "benchmark_cases.json"),
                    "--recordings", str(AI_DIR / "recorded_adapter_a.json"),
                    "--recordings", str(AI_DIR / "recorded_adapter_b.json"),
                    "--output", str(target),
                ]),
                0,
            )
            payload = json.loads(target.read_text())
            self.assertFalse(payload["live_model_calls_performed"])
            self.assertEqual(len(payload["metrics"]), 2)


if __name__ == "__main__":
    unittest.main()
