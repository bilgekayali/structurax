"""Generate compact deterministic JSON Schemas for v0.5 construction intelligence."""
from __future__ import annotations

import json
from pathlib import Path

from structurax.construction_models import (
    ConstructionIntelligenceCase,
    ConstructionIntelligenceReport,
    ConstructionPolicy,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "construction-intelligence-case.schema.json": ConstructionIntelligenceCase,
    "construction-intelligence-report.schema.json": ConstructionIntelligenceReport,
    "construction-policy.schema.json": ConstructionPolicy,
}


def main() -> None:
    target_dir = ROOT / "schemas"
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMAS.items():
        target = target_dir / filename
        target.write_text(
            json.dumps(
                model.model_json_schema(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
