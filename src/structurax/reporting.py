"""Write audit-friendly JSON and Markdown reports."""

from __future__ import annotations

from pathlib import Path

from structurax.models import AnalysisReport


def _safe_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_markdown(report: AnalysisReport) -> str:
    summary = report.summary
    lines = [
        "# StructuraX Analysis Report",
        "",
        f"- Pack: `{report.pack_id}`",
        f"- Engine: `{report.engine_version}`",
        f"- Policy: `{report.policy_version}`",
        f"- Input SHA-256: `{report.input_sha256}`",
        f"- Disposition: **{summary.disposition.value.upper()}**",
        f"- Findings: **{summary.finding_count}**",
        "",
        "> This deterministic report identifies review signals; it does not "
        "approve payments, authenticate documents, or replace professional review.",
        "",
        "## Severity summary",
        "",
        "| Critical | High | Medium | Low |",
        "|---:|---:|---:|---:|",
        (
            f"| {summary.severity_counts['critical']} | "
            f"{summary.severity_counts['high']} | "
            f"{summary.severity_counts['medium']} | "
            f"{summary.severity_counts['low']} |"
        ),
        "",
        "## Findings",
        "",
    ]
    if not report.findings:
        lines.append("No deterministic risk signals were found.")
        lines.append("")
        return "\n".join(lines)
    lines.extend(
        [
            "| Severity | Rule | Finding | Evidence |",
            "|---|---|---|---|",
        ]
    )
    for finding in report.findings:
        evidence = "; ".join(
            f"{item.document_id}:{item.field}={item.observed}"
            for item in finding.evidence
        )
        lines.append(
            "| {severity} | `{rule}` | {title} | {evidence} |".format(
                severity=finding.severity.value,
                rule=finding.rule_id,
                title=_safe_cell(finding.title),
                evidence=_safe_cell(evidence),
            )
        )
    lines.extend(["", "## Required follow-up", ""])
    for finding in report.findings:
        lines.append(
            f"- **{finding.rule_id}:** {finding.recommendation}"
        )
    lines.append("")
    return "\n".join(lines)


def write_report(
    report: AnalysisReport, output_dir: str | Path
) -> tuple[Path, Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "report.json"
    markdown_path = target / "report.md"
    json_path.write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path
