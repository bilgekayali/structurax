"""Credential-free Gradio demo for the bundled synthetic packs."""

from __future__ import annotations

from pathlib import Path

from structurax.engine import analyze_pack
from structurax.loader import load_pack, load_policy


ROOT = Path(__file__).resolve().parent
POLICY = ROOT / "configs" / "default_policy.json"
SCENARIOS = {
    "Clean synthetic pack": ROOT / "datasets" / "demo" / "clean_pack.json",
    "Risky synthetic pack": ROOT / "datasets" / "demo" / "risky_pack.json",
}


def analyze_scenario(scenario: str) -> tuple[str, list[list[str]]]:
    report = analyze_pack(load_pack(SCENARIOS[scenario]), load_policy(POLICY))
    summary = (
        f"## {report.summary.disposition.value.upper()}\n\n"
        f"**{report.summary.finding_count}** deterministic risk signals. "
        "No external API or document side effect was used."
    )
    rows = [
        [
            finding.severity.value,
            finding.rule_id,
            finding.title,
            "; ".join(
                f"{item.document_id}:{item.field}" for item in finding.evidence
            ),
        ]
        for finding in report.findings
    ]
    return summary, rows


def build_demo():
    import gradio as gr

    with gr.Blocks(title="StructuraX") as demo:
        gr.Markdown(
            "# StructuraX\n"
            "Construction document trust and risk analysis using synthetic data."
        )
        scenario = gr.Dropdown(
            choices=list(SCENARIOS),
            value="Risky synthetic pack",
            label="Scenario",
        )
        run = gr.Button("Analyze", variant="primary")
        summary = gr.Markdown()
        findings = gr.Dataframe(
            headers=["Severity", "Rule", "Finding", "Evidence"],
            datatype=["str", "str", "str", "str"],
            interactive=False,
        )
        run.click(analyze_scenario, inputs=scenario, outputs=[summary, findings])
    return demo


if __name__ == "__main__":
    build_demo().launch(server_name="0.0.0.0", server_port=7860)
