"""Build reproducible reports for the bundled synthetic demo packs."""

from __future__ import annotations

from pathlib import Path

from structurax.engine import analyze_pack
from structurax.loader import load_pack, load_policy
from structurax.reporting import write_report


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "configs" / "default_policy.json"
SCENARIOS = {
    "clean-pack": ROOT / "datasets" / "demo" / "clean_pack.json",
    "risky-pack": ROOT / "datasets" / "demo" / "risky_pack.json",
}


def main() -> None:
    policy = load_policy(POLICY)
    for name, path in SCENARIOS.items():
        pack = load_pack(path)
        report = analyze_pack(
            pack,
            policy,
            generated_at=pack.generated_at,
        )
        json_path, markdown_path = write_report(
            report,
            ROOT / "reports" / "demo" / name,
        )
        print(f"Wrote {json_path.relative_to(ROOT)}")
        print(f"Wrote {markdown_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
