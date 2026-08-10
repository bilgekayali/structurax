"""Command-line interface for validation and deterministic analysis."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from structurax.engine import analyze_pack
from structurax.loader import load_pack, load_policy
from structurax.reporting import write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="structurax",
        description="Analyze synthetic construction document packs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate", help="Validate a synthetic document pack"
    )
    validate.add_argument("--pack", required=True)

    analyze = subparsers.add_parser(
        "analyze", help="Run deterministic trust and risk rules"
    )
    analyze.add_argument("--pack", required=True)
    analyze.add_argument("--policy")
    analyze.add_argument("--output-dir", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
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
