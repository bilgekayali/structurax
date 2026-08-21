"""Command-line interface for deterministic StructuraX trust boundaries through v0.5."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from structurax.ai_adapters import AITrustPolicy, RecordedAIAdapter, resolve_ai_extraction
from structurax.ai_evaluation import AIBenchmarkSuite, evaluate_ai_adapters
from structurax.construction_intelligence import analyze_construction_case
from structurax.construction_models import ConstructionIntelligenceCase, ConstructionPolicy
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

    ai_replay = subparsers.add_parser(
        "ai-replay",
        help="Replay one synthetic v0.3 AI extraction case through the closed trust policy",
    )
    ai_replay.add_argument("--cases", required=True)
    ai_replay.add_argument("--case-id", required=True)
    ai_replay.add_argument("--recordings", required=True)
    ai_replay.add_argument("--policy")
    ai_replay.add_argument("--output", required=True)

    ai_benchmark = subparsers.add_parser(
        "ai-benchmark",
        help="Compare offline recorded v0.3 AI adapters without live model calls",
    )
    ai_benchmark.add_argument("--cases", required=True)
    ai_benchmark.add_argument("--recordings", action="append", required=True)
    ai_benchmark.add_argument("--policy")
    ai_benchmark.add_argument("--output", required=True)

    construction = subparsers.add_parser(
        "construction-analyze",
        help="Run deterministic v0.5 BOQ/contract/variation/matching/lineage analysis",
    )
    construction.add_argument("--case", required=True)
    construction.add_argument("--policy")
    construction.add_argument("--output", required=True)
    return parser


def _write_json(path: str | Path, payload: object) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def _load_ai_policy(path: str | Path | None) -> AITrustPolicy:
    if path is None:
        return AITrustPolicy()
    return AITrustPolicy.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def _load_ai_suite(path: str | Path) -> AIBenchmarkSuite:
    return AIBenchmarkSuite.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def _load_construction_policy(path: str | Path | None) -> ConstructionPolicy:
    if path is None:
        return ConstructionPolicy()
    return ConstructionPolicy.model_validate(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def _load_construction_case(path: str | Path) -> ConstructionIntelligenceCase:
    return ConstructionIntelligenceCase.model_validate(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


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

        if args.command == "ai-replay":
            suite = _load_ai_suite(args.cases)
            try:
                case = next(item for item in suite.cases if item.case_id == args.case_id)
            except StopIteration as exc:
                raise ValueError(f"unknown AI benchmark case {args.case_id}") from exc
            adapter = RecordedAIAdapter.from_path(args.recordings)
            resolution = resolve_ai_extraction(
                case.request,
                adapter,
                _load_ai_policy(args.policy),
                case.fallback,
            )
            target = _write_json(args.output, resolution.model_dump(mode="json"))
            print(f"AI resolution: {target}")
            print(f"Status: {resolution.status}; adapter invoked: {str(resolution.adapter_invoked).lower()}")
            return 0

        if args.command == "ai-benchmark":
            suite = _load_ai_suite(args.cases)
            adapters = [RecordedAIAdapter.from_path(path) for path in args.recordings]
            report = evaluate_ai_adapters(suite, adapters, _load_ai_policy(args.policy))
            target = _write_json(args.output, report.model_dump(mode="json"))
            print(f"AI benchmark report: {target}")
            print("Live model calls performed: false")
            return 0

        if args.command == "construction-analyze":
            construction_case = _load_construction_case(args.case)
            report = analyze_construction_case(
                construction_case,
                _load_construction_policy(args.policy),
            )
            target = _write_json(args.output, report.model_dump(mode="json"))
            print(f"Construction intelligence report: {target}")
            print(
                f"Findings: {len(report.findings)}; "
                f"human review: {str(report.requires_human_review).lower()}"
            )
            print("Automation authority: false; operational side effects performed: false")
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