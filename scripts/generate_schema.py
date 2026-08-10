"""Generate the committed document-pack JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path

from structurax.models import DocumentPack


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "schemas" / "document-pack.schema.json"


def main() -> None:
    TARGET.write_text(
        json.dumps(
            DocumentPack.model_json_schema(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
