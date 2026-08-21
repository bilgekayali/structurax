"""Build the canonical production-evidence signing payload without handling a private key."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.release_surface_digest import compute_release_surface_digest  # noqa: E402
from scripts.verify_production_evidence import canonical_statement  # noqa: E402

_EXPECTED_KEYS = {
    "reviewed_repository_sha256",
    "environment_id",
    "completed_at",
    "production_environment_confirmed",
    "raw_endpoint_metadata_present",
    "raw_secret_material_present",
    "controls",
}


def _load_statement(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("production evidence statement must be a JSON object")
    if set(payload) != _EXPECTED_KEYS:
        raise SystemExit("production evidence statement keys mismatch")
    if payload["reviewed_repository_sha256"] != compute_release_surface_digest(ROOT):
        raise SystemExit("production evidence statement is bound to a different release surface")
    if payload["production_environment_confirmed"] is not True:
        raise SystemExit("production_environment_confirmed must be true")
    if payload["raw_endpoint_metadata_present"] is not False or payload["raw_secret_material_present"] is not False:
        raise SystemExit("raw endpoint or secret metadata is forbidden")
    return payload


def build_signing_payload(statement_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    statement = _load_statement(Path(statement_path))
    payload = canonical_statement(statement)
    output = Path(output_path)
    output.write_bytes(payload)
    return {
        "output": str(output),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "payload_size": len(payload),
        "signature_algorithm": "Ed25519",
        "private_key_handled": False,
        "formal_gate_mutation_authorized": False,
        "production_readiness_claimed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--statement", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(build_signing_payload(args.statement, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
