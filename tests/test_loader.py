"""Schema and synthetic-data boundary tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from structurax.loader import load_pack
from structurax.models import DocumentPack


ROOT = Path(__file__).resolve().parents[1]
CLEAN_PACK = ROOT / "datasets" / "demo" / "clean_pack.json"
SCHEMA = ROOT / "schemas" / "document-pack.schema.json"


class LoaderTests(unittest.TestCase):
    def test_demo_pack_loads(self) -> None:
        pack = load_pack(CLEAN_PACK)
        self.assertEqual(pack.pack_id, "clean-pack")
        self.assertEqual(len(pack.documents), 4)

    def test_production_data_is_rejected(self) -> None:
        payload = json.loads(CLEAN_PACK.read_text(encoding="utf-8"))
        payload["synthetic_data"] = False
        with self.assertRaisesRegex(ValidationError, "synthetic data only"):
            DocumentPack.model_validate(payload)

    def test_duplicate_document_ids_are_rejected(self) -> None:
        payload = json.loads(CLEAN_PACK.read_text(encoding="utf-8"))
        payload["documents"][1]["document_id"] = payload["documents"][0][
            "document_id"
        ]
        with self.assertRaisesRegex(ValidationError, "document IDs must be unique"):
            DocumentPack.model_validate(payload)

    def test_committed_schema_matches_model(self) -> None:
        committed = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(committed, DocumentPack.model_json_schema())


if __name__ == "__main__":
    unittest.main()
