"""Regenerate the committed v0.3 synthetic AI-adapter benchmark report."""

from __future__ import annotations

import json
from pathlib import Path

from structurax.ai_adapters import AITrustPolicy, RecordedAIAdapter
from structurax.ai_evaluation import AIBenchmarkSuite, evaluate_ai_adapters

ROOT = Path(__file__).resolve().parents[1]
AI_DIR = ROOT / "datasets" / "ai"
TARGET = ROOT / "reports" / "evaluation" / "v0.3-ai-adapters.json"


def main() -> None:
    suite = AIBenchmarkSuite.model_validate(
        json.loads((AI_DIR / "benchmark_cases.json").read_text(encoding="utf-8"))
    )
    adapters = [
        RecordedAIAdapter.from_path(AI_DIR / "recorded_adapter_a.json"),
        RecordedAIAdapter.from_path(AI_DIR / "recorded_adapter_b.json"),
    ]
    report = evaluate_ai_adapters(suite, adapters, AITrustPolicy())
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
