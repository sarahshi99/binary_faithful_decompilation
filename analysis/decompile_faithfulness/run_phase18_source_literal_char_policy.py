from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import run_phase10_low_budget_rerun as phase10
from analysis.decompile_faithfulness import run_phase12_unified_low_budget_eval as phase12
from analysis.decompile_faithfulness import run_phase17_operator_char_policy as phase17


DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase18_source_literal_char_policy")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase18_source_literal_char_policy.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase18_source_literal_char_policy.zh.md")
DEFAULT_PHASE10_JSON = Path("docs/paper_agent/decompile_faithfulness_phase10_low_budget_rerun.json")
DEFAULT_BASELINE_PHASE12_JSON = Path("docs/paper_agent/decompile_faithfulness_phase12_unified_low_budget.json")
DEFAULT_BASELINE_PHASE16_JSON = Path("docs/paper_agent/decompile_faithfulness_phase16_runtime_risk.json")
DEFAULT_STRATEGY = "source_literal_char_interleave"
DEFAULT_BUDGETS = [1, 2, 4, 8, 16]
DEFAULT_REPORT_BUDGET = 8


def main() -> None:
    args = parse_args()
    summary = run_phase18(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
        phase10_json=args.phase10_json,
        baseline_phase12_json=args.baseline_phase12_json,
        baseline_phase16_json=args.baseline_phase16_json,
        strategy_id=args.strategy_id,
        budgets=args.budget or DEFAULT_BUDGETS,
        report_budget=args.report_budget,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "strategy_id": summary["strategy_id"],
                "dataset_comparison": {
                    dataset_id: {
                        "mismatch_auc": item["new"]["mismatch_auc"],
                        "wrong_detection_rate": item["new"]["wrong_detection_rate"],
                        "missed_wrong_count": item["new"]["missed_wrong_count"],
                    }
                    for dataset_id, item in summary["dataset_comparison"].items()
                },
                "focus_risk_rows": {
                    family: {
                        "auc": row["auc"],
                        "wrong_detection_rate": row["wrong_detection_rate"],
                        "missed_wrong_count": row["missed_wrong_count"],
                    }
                    for family, row in summary["focus_risk_rows"].items()
                },
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--phase10-json", type=Path, default=DEFAULT_PHASE10_JSON)
    parser.add_argument("--baseline-phase12-json", type=Path, default=DEFAULT_BASELINE_PHASE12_JSON)
    parser.add_argument("--baseline-phase16-json", type=Path, default=DEFAULT_BASELINE_PHASE16_JSON)
    parser.add_argument("--strategy-id", default=DEFAULT_STRATEGY)
    parser.add_argument("--budget", type=int, action="append", default=None)
    parser.add_argument("--report-budget", type=int, default=DEFAULT_REPORT_BUDGET)
    return parser.parse_args()


def run_phase18(
    repo_root: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    phase10_json: Path,
    baseline_phase12_json: Path,
    baseline_phase16_json: Path,
    strategy_id: str,
    budgets: list[int],
    report_budget: int,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_dir = _resolve(repo_root, output_dir)
    baseline_phase12 = phase17.read_json(_resolve(repo_root, baseline_phase12_json))
    baseline_phase16 = phase17.read_json(_resolve(repo_root, baseline_phase16_json))
    phase18_phase12 = phase12.run_phase12(
        repo_root=repo_root,
        output_dir=output_dir / "unified_low_budget",
        output_json=output_dir / "phase12_unified_low_budget.json",
        output_zh=output_dir / "phase12_unified_low_budget.zh.md",
        decision_zh=output_dir / "phase12_decision.zh.md",
        phase10_json=_resolve(repo_root, phase10_json),
        strategy_id=strategy_id,
        budgets=budgets,
    )
    dataset_comparison = phase17.compare_datasets(
        baseline=baseline_phase12,
        current=phase18_phase12,
        budget=str(report_budget),
    )
    risk_breakdown = phase17.build_risk_breakdown(
        repo_root=repo_root,
        records_dir=output_dir / "unified_low_budget",
        budget=report_budget,
    )
    focus_risk_rows = {
        family: phase17.require_risk_row(risk_breakdown["phase6r_ghidra_full"], family)
        for family in ["char_boundary", "multi_arg"]
    }
    gate = phase17.build_gate(
        dataset_comparison=dataset_comparison,
        risk_breakdown=risk_breakdown,
        focus_risk_rows=focus_risk_rows,
    )
    summary = {
        "phase": "phase18_source_literal_char_policy",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "strategy_id": strategy_id,
        "report_budget": report_budget,
        "budgets": sorted(set(budgets)),
        "phase12_output_dir": str(output_dir / "unified_low_budget"),
        "dataset_comparison": dataset_comparison,
        "risk_breakdown": risk_breakdown,
        "risk_comparison": phase17.compare_risk_breakdown(
            baseline=baseline_phase16.get("risk_breakdown", {}),
            current=risk_breakdown,
        ),
        "focus_risk_rows": focus_risk_rows,
        "gate": gate,
        "verdict": phase18_verdict(gate),
    }
    phase10.write_json(_resolve(repo_root, output_json), summary)
    write_markdown(_resolve(repo_root, output_zh), summary)
    return summary


def phase18_verdict(gate: dict[str, bool]) -> str:
    if all(gate.values()):
        return "pass-phase18-source-literal-char-policy"
    if any(gate.values()):
        return "partial-phase18-source-literal-char-policy"
    return "fail-phase18-source-literal-char-policy"


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    dataset_rows = []
    for dataset_id, item in summary["dataset_comparison"].items():
        new = item["new"]
        delta = item["delta"]
        dataset_rows.append(
            "| `{dataset}` | `{auc:.4f}` | `{dauc:+.4f}` | `{det:.4f}` | `{ddet:+.4f}` | `{miss}` | `{dmiss:+.0f}` |".format(
                dataset=dataset_id,
                auc=new["mismatch_auc"],
                dauc=delta["mismatch_auc_delta"],
                det=new["wrong_detection_rate"],
                ddet=delta["wrong_detection_rate_delta"],
                miss=new["missed_wrong_count"],
                dmiss=delta["missed_wrong_count_delta"],
            )
        )
    risk_rows = []
    for row in summary["risk_comparison"]["phase6r_ghidra_full"]:
        if row["paired_case_count"] < 3:
            continue
        risk_rows.append(
            "| `{family}` | `{paired}` | `{auc:.4f}` | `{dauc:+.4f}` | `{det:.4f}` | `{ddet:+.4f}` | `{miss}` | `{dmiss:+d}` |".format(
                family=row["risk_family"],
                paired=row["paired_case_count"],
                auc=row["auc"],
                dauc=row["auc_delta"],
                det=row["wrong_detection_rate"],
                ddet=row["wrong_detection_rate_delta"],
                miss=row["missed_wrong_count"],
                dmiss=row["missed_wrong_count_delta"],
            )
        )
    gate_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in summary["gate"].items())
    text = f"""# Decompilation Faithfulness Phase 18 Source Literal Char Policy

- Verdict: `{summary['verdict']}`
- Strategy: `{summary['strategy_id']}`
- Budget: `{summary['report_budget']}`

## Budget-8 Dataset Comparison

| Dataset | AUC | AUC delta vs Phase12 | Wrong detection | Detection delta vs Phase12 | Missed wrong | Miss delta |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(dataset_rows)}

## Ghidra Risk-Family Comparison

| Risk family | Paired cases | AUC | AUC delta vs Phase16 | Detection | Detection delta vs Phase16 | Missed wrong | Miss delta |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(risk_rows)}

## Gate

| Gate | Passed |
|---|---:|
{gate_rows}

## Interpretation

This phase tests a conservative source-known input policy. It extracts
character literals from the original source and interleaves them with
fixture-neighbor probes, instead of front-loading a generic operator list. A
passing result would support adding source-literal char probes to the final
low-budget auditor. A partial or failed result means Phase 16's char-boundary
miss should remain a limitation rather than be patched into the main claim.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
