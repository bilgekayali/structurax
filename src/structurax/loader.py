"""Load and validate StructuraX JSON inputs."""

from __future__ import annotations

import json
from pathlib import Path

from structurax.models import DocumentPack, Policy


def load_pack(path: str | Path) -> DocumentPack:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    return DocumentPack.model_validate(payload)


def load_policy(path: str | Path | None = None) -> Policy:
    if path is None:
        return Policy()
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    return Policy.model_validate(payload)
