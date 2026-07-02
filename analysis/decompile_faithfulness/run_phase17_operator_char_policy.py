from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import run_phase10_low_budget_rerun as phase10
from analysis.decompile_faithfulness import run_phase12_unified_low_budget_eval as phase12
from analysis.decompile_faithfulness import run_phase14_paper_readiness as phase14
from analysis.decompile_faithfulness import run_phase16_runtime_risk_breakdown as phase16


DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase17_operator_char_policy")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase17_operator_char_policy.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase17_operator_char_policy.zh.md")
DEFAULT_BASELINE_PHASE12_JSON = Path("docs/paper_agent/decompile_faithfulness_phase12_unified_low_budget.json")
DEFAULT_BASELINE_PHASE16_JSON = Path("docs/paper_agent/decompile_faithfulness_phase16_runtime_risk.json")
DEFAULT_PHASE10_JSON = Path("docs/paper_agent/decompile_faithfulness_phase10_low_budget_rerun.json")
DEFAULT_STRATEGY = "operator_char_class_first"
DEFAULT_BUDGETS = [1, 2, 4, 8, 16]
DEFAULT_BUDGET = 8
EPSILON = 1e-12


def main() -> None:
    args = parse_args()
    summary = run_phase17(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
        baseline_phase12_json=args.baseline_phase12_json,
        baseline_phase16_json=args.baseline_phase16_json,
        phase10_json=args.phase10_json,
        strategy_id=args.strategy_id,
        budgets=args.budget or DEFAULT_BUDGETS,
        report_budget=args.report_budget,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "strategy_id": summary["strategy_id"],
                "budget": summary["report_budget"],
                "dataset_comparison": {
                    dataset_id: {
                        "mismatch_auc": item["new"]["mismatch_auc"],
                        "wrong_detection_rate": item["new"]["wrong_detection_rate"],
                        "missed_wrong_count": item["new"].get("missed_wrong_count", 0),
                    }
                    for dataset_id, item in summary["dataset_comparison"].items()
                },
                "ghidra_focus_risk": {
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
    parser.add_argument("--baseline-phase12-json", type=Path, default=DEFAULT_BASELINE_PHASE12_JSON)
    parser.add_argument("--baseline-phase16-json", type=Path, default=DEFAULT_BASELINE_PHASE16_JSON)
    parser.add_argument("--phase10-json", type=Path, default=DEFAULT_PHASE10_JSON)
    parser.add_argument("--strategy-id", default=DEFAULT_STRATEGY)
    parser.add_argument("--budget", type=int, action="append", default=None)
    parser.add_argument("--report-budget", type=int, default=DEFAULT_BUDGET)
    return parser.parse_args()


def run_phase17(
    repo_root: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    baseline_phase12_json: Path,
    baseline_phase16_json: Path,
    phase10_json: Path,
    strategy_id: str,
    budgets: list[int],
    report_budget: int,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_dir = _resolve(repo_root, output_dir)
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    baseline_phase12 = read_json(_resolve(repo_root, baseline_phase12_json))
    baseline_phase16 = read_json(_resolve(repo_root, baseline_phase16_json))
    phase17_phase12 = phase12.run_phase12(
        repo_root=repo_root,
        output_dir=output_dir / "unified_low_budget",
        output_json=output_dir / "phase12_unified_low_budget.json",
        output_zh=output_dir / "phase12_unified_low_budget.zh.md",
        decision_zh=output_dir / "phase12_decision.zh.md",
        phase10_json=_resolve(repo_root, phase10_json),
        strategy_id=strategy_id,
        budgets=budgets,
    )
    dataset_comparison = compare_datasets(
        baseline=baseline_phase12,
        current=phase17_phase12,
        budget=str(report_budget),
    )
    risk_breakdown = build_risk_breakdown(
        repo_root=repo_root,
        records_dir=output_dir / "unified_low_budget",
        budget=report_budget,
    )
    risk_comparison = compare_risk_breakdown(
        baseline=baseline_phase16.get("risk_breakdown", {}),
        current=risk_breakdown,
    )
    focus_risk_rows = {
        family: require_risk_row(risk_breakdown["phase6r_ghidra_full"], family)
        for family in ["char_boundary", "multi_arg"]
    }
    gate = build_gate(
        dataset_comparison=dataset_comparison,
        risk_breakdown=risk_breakdown,
        focus_risk_rows=focus_risk_rows,
    )
    summary = {
        "phase": "phase17_operator_char_policy",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "strategy_id": strategy_id,
        "report_budget": report_budget,
        "budgets": sorted(set(budgets)),
        "phase12_output_dir": str(output_dir / "unified_low_budget"),
        "dataset_comparison": dataset_comparison,
        "risk_breakdown": risk_breakdown,
        "risk_comparison": risk_comparison,
        "focus_risk_rows": focus_risk_rows,
        "gate": gate,
        "verdict": phase17_verdict(gate),
    }
    phase10.write_json(output_json, summary)
    write_markdown(output_zh, summary)
    return summary


def compare_datasets(
    baseline: dict[str, Any],
    current: dict[str, Any],
    budget: str,
) -> dict[str, Any]:
    comparison: dict[str, Any] = {}
    for dataset_id, current_dataset in current["datasets"].items():
        base_metrics = baseline["datasets"][dataset_id]["budget_metrics"][budget]
        new_metrics = current_dataset["budget_metrics"][budget]
        comparison[dataset_id] = {
            "baseline_strategy_id": baseline.get("strategy_id", "unknown"),
            "new_strategy_id": current.get("strategy_id", "unknown"),
            "baseline": compact_budget_metrics(base_metrics),
            "new": compact_budget_metrics(new_metrics),
            "delta": metric_delta(new_metrics, base_metrics),
        }
    return comparison


def compact_budget_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "mismatch_auc": float(metrics["mismatch_auc"]),
        "wrong_detection_rate": float(metrics["wrong_detection_rate"]),
        "missed_wrong_count": int(metrics.get("missed_wrong_count", 0)),
        "avg_actual_inputs_per_candidate": float(metrics["avg_actual_inputs_per_candidate"]),
        "actual_input_evals": int(metrics["actual_input_evals"]),
        "eval_count": int(metrics["eval_count"]),
        "wrong_count": int(metrics["wrong_count"]),
    }


def metric_delta(new_metrics: dict[str, Any], baseline_metrics: dict[str, Any]) -> dict[str, float]:
    return {
        "mismatch_auc_delta": float(new_metrics["mismatch_auc"]) - float(baseline_metrics["mismatch_auc"]),
        "wrong_detection_rate_delta": (
            float(new_metrics["wrong_detection_rate"]) - float(baseline_metrics["wrong_detection_rate"])
        ),
        "missed_wrong_count_delta": (
            float(new_metrics.get("missed_wrong_count", 0)) - float(baseline_metrics.get("missed_wrong_count", 0))
        ),
        "avg_actual_inputs_delta": (
            float(new_metrics["avg_actual_inputs_per_candidate"])
            - float(baseline_metrics["avg_actual_inputs_per_candidate"])
        ),
    }


def build_risk_breakdown(repo_root: Path, records_dir: Path, budget: int) -> dict[str, list[dict[str, Any]]]:
    risk_breakdown: dict[str, list[dict[str, Any]]] = {}
    for spec in phase10.DEFAULT_DATASETS:
        manifest = phase16.load_manifest(repo_root, spec.manifest_json)
        entries_by_case = {entry["case_id"]: entry for entry in manifest.get("functions", [])}
        records = [
            record for record in phase14.read_jsonl(records_dir / spec.dataset_id / "records_budgeted.jsonl")
            if int(record.get("requested_budget", -1)) == budget
            and record.get("compiled")
            and record.get("label") in {"faithful", "plausible_wrong"}
        ]
        risk_breakdown[spec.dataset_id] = phase16.risk_family_breakdown(records, entries_by_case)
    return risk_breakdown


def compare_risk_breakdown(
    baseline: dict[str, list[dict[str, Any]]],
    current: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    comparison: dict[str, list[dict[str, Any]]] = {}
    for dataset_id, current_rows in current.items():
        baseline_rows = {row["risk_family"]: row for row in baseline.get(dataset_id, [])}
        rows = []
        for row in current_rows:
            base = baseline_rows.get(row["risk_family"], {})
            rows.append(
                {
                    "risk_family": row["risk_family"],
                    "paired_case_count": row["paired_case_count"],
                    "auc": row["auc"],
                    "auc_delta": float(row["auc"]) - float(base.get("auc", 0.0)),
                    "wrong_detection_rate": row["wrong_detection_rate"],
                    "wrong_detection_rate_delta": (
                        float(row["wrong_detection_rate"]) - float(base.get("wrong_detection_rate", 0.0))
                    ),
                    "missed_wrong_count": row["missed_wrong_count"],
                    "missed_wrong_count_delta": (
                        int(row["missed_wrong_count"]) - int(base.get("missed_wrong_count", 0))
                    ),
                }
            )
        comparison[dataset_id] = rows
    return comparison


def build_gate(
    dataset_comparison: dict[str, Any],
    risk_breakdown: dict[str, list[dict[str, Any]]],
    focus_risk_rows: dict[str, dict[str, Any]],
) -> dict[str, bool]:
    gate = {
        f"{dataset_id}_budget8_auc_no_regression": item["delta"]["mismatch_auc_delta"] >= -EPSILON
        for dataset_id, item in dataset_comparison.items()
    }
    gate.update(
        {
            f"{dataset_id}_budget8_detection_no_regression": (
                item["delta"]["wrong_detection_rate_delta"] >= -EPSILON
            )
            for dataset_id, item in dataset_comparison.items()
        }
    )
    ghidra = dataset_comparison["phase6r_ghidra_full"]["new"]
    gate["phase6r_ghidra_full_budget8_auc_gate"] = ghidra["mismatch_auc"] >= 0.98
    gate["phase6r_ghidra_full_budget8_detection_gate"] = ghidra["wrong_detection_rate"] >= 0.95
    gate["phase6r_ghidra_full_large_risk_family_auc_gate"] = large_risk_family_gate(
        risk_breakdown["phase6r_ghidra_full"],
        metric="auc",
        threshold=0.90,
    )
    gate["phase6r_ghidra_full_large_risk_family_detection_gate"] = large_risk_family_gate(
        risk_breakdown["phase6r_ghidra_full"],
        metric="wrong_detection_rate",
        threshold=0.90,
    )
    for family, row in focus_risk_rows.items():
        gate[f"phase6r_ghidra_full_{family}_detection_gate"] = row["wrong_detection_rate"] >= 0.90
    return gate


def large_risk_family_gate(rows: list[dict[str, Any]], metric: str, threshold: float) -> bool:
    risky_rows = [row for row in rows if row["paired_case_count"] >= 3]
    return bool(risky_rows) and all(float(row[metric]) >= threshold for row in risky_rows)


def require_risk_row(rows: list[dict[str, Any]], risk_family: str) -> dict[str, Any]:
    for row in rows:
        if row["risk_family"] == risk_family:
            return row
    raise KeyError(f"missing risk family row: {risk_family}")


def phase17_verdict(gate: dict[str, bool]) -> str:
    if all(gate.values()):
        return "pass-phase17-operator-char-policy"
    if any(gate.values()):
        return "partial-phase17-operator-char-policy"
    return "fail-phase17-operator-char-policy"


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    dataset_rows = []
    for dataset_id, item in summary["dataset_comparison"].items():
        new = item["new"]
        delta = item["delta"]
        dataset_rows.append(
            "| `{dataset}` | `{auc:.4f}` | `{dauc:+.4f}` | `{det:.4f}` | `{ddet:+.4f}` | `{miss}` | `{dmiss:+.0f}` | `{avg:.2f}` | `{davg:+.2f}` |".format(
                dataset=dataset_id,
                auc=new["mismatch_auc"],
                dauc=delta["mismatch_auc_delta"],
                det=new["wrong_detection_rate"],
                ddet=delta["wrong_detection_rate_delta"],
                miss=new["missed_wrong_count"],
                dmiss=delta["missed_wrong_count_delta"],
                avg=new["avg_actual_inputs_per_candidate"],
                davg=delta["avg_actual_inputs_delta"],
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
    text = f"""# Decompilation Faithfulness Phase 17 Operator Char Policy

- Verdict: `{summary['verdict']}`
- Strategy: `{summary['strategy_id']}`
- Budget: `{summary['report_budget']}`

## Budget-8 Dataset Comparison

| Dataset | AUC | AUC delta vs Phase12 | Wrong detection | Detection delta vs Phase12 | Missed wrong | Miss delta | Avg inputs | Avg input delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
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

`Mismatch AUC` measures whether wrong candidates are ranked above faithful ones
within each case. `Wrong detection` measures whether each wrong candidate is
actually exposed by at least one budgeted input. Higher is better for both.

Phase 17 is good only if it improves the Ghidra `char_boundary` / `multi_arg`
weakness without making the public or LLM-public full evaluations worse. If it
passes, `operator_char_class_first` is a stronger default low-budget input
policy than plain `fixture_neighbor_first`. If it is partial, keep the result as
a targeted ablation and leave the Phase 16 limitation in the paper.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
