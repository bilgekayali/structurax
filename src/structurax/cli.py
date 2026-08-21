"""Command-line interface for deterministic analysis and v0.2 trust boundaries."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from structurax.engine import analyze_pack
from structurax.explanations import reviewer_explanation
from structurax.feedback import HumanReviewFeedback, feedback_digest
from structurax.fixture_signing import verify_fixture_manifest
from structurax.ingestion import RecordedExtractionAdapter, ingest_pdf_path
from structurax.loader import load_pack, load_policy
from structurax.reporting import write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="structurax",
        description="Analyze construction-document trust signals without autonomous action.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a synthetic document pack")
    validate.add_argument("--pack", required=True)

    analyze = subparsers.add_parser("analyze", help="Run deterministic trust and risk rules")
    analyze.add_argument("--pack", required=True)
    analyze.add_argument("--policy")
    analyze.add_argument("--output-dir", required=True)

    verify = subparsers.add_parser(
        "verify-fixtures", help="Verify the signed v0.2 synthetic fixture manifest"
    )
    verify.add_argument("--root", default=".")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--signature", required=True)
    verify.add_argument("--public-key", required=True)

    ingest = subparsers.add_parser(
        "ingest", help="Preflight a local PDF and replay a digest-bound extraction"
    )
    ingest.add_argument("--source", required=True)
    ingest.add_argument("--recordings", required=True)
    ingest.add_argument("--output", required=True)

    explain = subparsers.add_parser("explain", help="Render a deterministic reviewer explanation")
    explain.add_argument("--rule-id", required=True)
    explain.add_argument("--language", choices=("en", "tr"), required=True)

    feedback = subparsers.add_parser(
        "validate-feedback", help="Validate a side-effect-free human-review feedback record"
    )
    feedback.add_argument("--file", required=True)
    return parser


def _write_json(path: str | Path, payload: object) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "verify-fixtures":
            manifest = verify_fixture_manifest(
                args.root, args.manifest, args.signature, args.public_key
            )
            print(f"Verified signed fixture set {manifest.fixture_set_id} ({len(manifest.entries)} entries)")
            return 0

        if args.command == "ingest":
            adapter = RecordedExtractionAdapter.from_path(args.recordings)
            artifact = ingest_pdf_path(args.source, adapter)
            target = _write_json(args.output, artifact.model_dump(mode="json"))
            print(f"Ingestion artifact: {target}")
            print("External execution performed: false")
            return 0

        if args.command == "explain":
            explanation = reviewer_explanation(args.rule_id, args.language)
            print(json.dumps(explanation.model_dump(mode="json"), ensure_ascii=False, sort_keys=True))
            return 0

        if args.command == "validate-feedback":
            payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
            feedback = HumanReviewFeedback.model_validate(payload)
            print(f"Validated feedback digest: {feedback_digest(feedback)}")
            return 0

        pack = load_pack(args.pack)
        if args.command == "validate":
            print(
                f"Validated {len(pack.documents)} synthetic documents "
                f"from pack {pack.pack_id}"
            )
            return 0

        policy = load_policy(args.policy)
        report = analyze_pack(pack, policy)
        json_path, markdown_path = write_report(report, args.output_dir)
        print(
            f"Disposition: {report.summary.disposition.value}; "
            f"findings: {report.summary.finding_count}"
        )
        print(f"JSON report: {json_path}")
        print(f"Markdown report: {markdown_path}")
        return 0
    except (OSError, ValueError, ValidationError) as exc:
        print(f"StructuraX error: {exc}", file=sys.stderr)
        return 2


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
