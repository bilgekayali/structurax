"""Attach an externally produced Ed25519 signature and verify the resulting evidence envelope."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.release_surface_digest import compute_release_surface_digest  # noqa: E402
from scripts.verify_production_evidence import verify_production_evidence  # noqa: E402


def _load_statement(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("production evidence statement must be a JSON object")
    return payload


def _load_public_key(path: Path) -> tuple[Ed25519PublicKey, str]:
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise SystemExit("production evidence public key must be Ed25519")
    raw = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return key, hashlib.sha256(raw).hexdigest()


def attach_signature(
    statement_path: str | Path,
    signature_path: str | Path,
    trusted_public_key_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    statement = _load_statement(Path(statement_path))
    _, key_id = _load_public_key(Path(trusted_public_key_path))
    signature_b64 = Path(signature_path).read_text(encoding="utf-8").strip()
    try:
        base64.b64decode(signature_b64, validate=True)
    except Exception as exc:
        raise SystemExit("signature file must contain valid base64") from exc

    envelope = {
        "schema_version": "1.0.0",
        "statement": statement,
        "signature": {
            "algorithm": "Ed25519",
            "key_id": key_id,
            "signature_b64": signature_b64,
        },
    }
    with tempfile.TemporaryDirectory() as tmp:
        candidate = Path(tmp) / "candidate.json"
        candidate.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        verification = verify_production_evidence(
            candidate,
            trusted_public_key_path,
            repository_digest=compute_release_surface_digest(ROOT),
        )
    if verification["contract_verified"] is not True:
        raise SystemExit("production evidence envelope failed verification")

    output = Path(output_path)
    output.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "output": str(output),
        "validator_key_id": key_id,
        "contract_verified": True,
        "private_key_handled": False,
        "trusted_key_established_by_tool": False,
        "formal_gate_mutation_authorized": False,
        "production_readiness_claimed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--statement", required=True)
    parser.add_argument("--signature-file", required=True)
    parser.add_argument("--trusted-public-key", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = attach_signature(
        args.statement,
        args.signature_file,
        args.trusted_public_key,
        args.output,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
