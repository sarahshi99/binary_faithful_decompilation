from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import run_phase10_low_budget_rerun as phase10
from analysis.decompile_faithfulness import run_phase11_input_ordering as phase11
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu


DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase12_unified_low_budget")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase12_unified_low_budget.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase12_unified_low_budget.zh.md")
DEFAULT_DECISION_ZH = Path("docs/paper_agent/decompile_faithfulness_phase12_decision.zh.md")
DEFAULT_PHASE10_JSON = Path("docs/paper_agent/decompile_faithfulness_phase10_low_budget_rerun.json")
DEFAULT_BUDGETS = [1, 2, 4, 8, 16]
DEFAULT_STRATEGY = "fixture_neighbor_first"


def main() -> None:
    args = parse_args()
    summary = run_phase12(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
        decision_zh=args.decision_zh,
        phase10_json=args.phase10_json,
        strategy_id=args.strategy_id,
        budgets=args.budget or DEFAULT_BUDGETS,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "strategy_id": summary["strategy_id"],
                "budget8": {
                    dataset_id: {
                        "mismatch_auc": result["budget_metrics"]["8"]["mismatch_auc"],
                        "wrong_detection_rate": result["budget_metrics"]["8"]["wrong_detection_rate"],
                    }
                    for dataset_id, result in summary["datasets"].items()
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
    parser.add_argument("--decision-zh", type=Path, default=DEFAULT_DECISION_ZH)
    parser.add_argument("--phase10-json", type=Path, default=DEFAULT_PHASE10_JSON)
    parser.add_argument("--strategy-id", default=DEFAULT_STRATEGY)
    parser.add_argument("--budget", type=int, action="append", default=None)
    return parser.parse_args()


def run_phase12(
    repo_root: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    decision_zh: Path,
    phase10_json: Path,
    strategy_id: str,
    budgets: list[int],
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_dir = _resolve(repo_root, output_dir)
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    decision_zh = _resolve(repo_root, decision_zh)
    phase10_json = _resolve(repo_root, phase10_json)
    phase10_summary = json.loads(phase10_json.read_text(encoding="utf-8"))
    budgets = sorted(set(budgets))
    max_budget = max(budgets)

    datasets: dict[str, Any] = {}
    for spec in phase10.DEFAULT_DATASETS:
        datasets[spec.dataset_id] = rerun_dataset(
            repo_root=repo_root,
            output_dir=output_dir / spec.dataset_id,
            spec=spec,
            strategy_id=strategy_id,
            budgets=budgets,
            max_budget=max_budget,
            phase10_summary=phase10_summary,
        )
    gate = {
        f"{dataset_id}_budget8_auc_gate": dataset["budget_metrics"]["8"]["mismatch_auc"] >= 0.98
        for dataset_id, dataset in datasets.items()
    }
    gate.update(
        {
            f"{dataset_id}_budget8_detection_gate": dataset["budget_metrics"]["8"]["wrong_detection_rate"] >= 0.95
            for dataset_id, dataset in datasets.items()
        }
    )
    summary = {
        "phase": "phase12_unified_low_budget_eval",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "strategy_id": strategy_id,
        "budgets": budgets,
        "max_budget": max_budget,
        "datasets": datasets,
        "gate": gate,
        "verdict": phase12_verdict(gate),
    }
    phase10.write_json(output_json, summary)
    write_markdown(output_zh, summary)
    write_decision(decision_zh, summary)
    return summary


def rerun_dataset(
    repo_root: Path,
    output_dir: Path,
    spec: phase10.DatasetSpec,
    strategy_id: str,
    budgets: list[int],
    max_budget: int,
    phase10_summary: dict[str, Any],
) -> dict[str, Any]:
    records = [
        record for record in phase10.load_records(repo_root, spec)
        if record.get("compiled")
        and record.get("label") in {"faithful", "plausible_wrong"}
        and record.get("metadata", {}).get("function_source")
    ]
    manifest = json.loads(_resolve(repo_root, spec.manifest_json).read_text(encoding="utf-8"))
    entries_by_case = {entry["case_id"]: entry for entry in manifest.get("functions", [])}
    records = [record for record in records if record.get("case_id") in entries_by_case]
    cases = {
        case_id: phase5_gpu._case_from_manifest_entry(repo_root, entry)
        for case_id, entry in entries_by_case.items()
    }
    result = phase11.rerun_strategy(
        records=records,
        entries_by_case=entries_by_case,
        cases=cases,
        strategy_id=strategy_id,
        output_dir=output_dir,
        budgets=budgets,
        max_budget=max_budget,
    )
    baseline_budget8 = phase10_summary["datasets"][spec.dataset_id]["budget_metrics"]["8"]
    budget8 = result["budget_metrics"]["8"]
    result["dataset_id"] = spec.dataset_id
    result["title"] = spec.title
    result["source_eval_candidate_count"] = len(records)
    result["phase10_budget8_baseline"] = baseline_budget8
    result["budget8_delta_vs_phase10"] = metric_delta(budget8, baseline_budget8)
    return result


def metric_delta(metrics: dict[str, Any], baseline: dict[str, Any]) -> dict[str, float]:
    return {
        "mismatch_auc_delta": float(metrics["mismatch_auc"]) - float(baseline["mismatch_auc"]),
        "wrong_detection_rate_delta": float(metrics["wrong_detection_rate"]) - float(baseline["wrong_detection_rate"]),
        "avg_actual_inputs_delta": float(metrics["avg_actual_inputs_per_candidate"]) - float(baseline["avg_actual_inputs_per_candidate"]),
    }


def phase12_verdict(gate: dict[str, bool]) -> str:
    passed = sum(1 for value in gate.values() if value)
    if passed == len(gate):
        return "pass-unified-budget8-low-budget-eval"
    if passed:
        return "partial-unified-low-budget-eval"
    return "fail-unified-low-budget-eval"


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    rows = []
    for dataset_id, dataset in summary["datasets"].items():
        b8 = dataset["budget_metrics"]["8"]
        delta = dataset["budget8_delta_vs_phase10"]
        rows.append(
            "| `{dataset}` | `{auc:.4f}` | `{rate:.4f}` | `{missed}` | `{avg:.2f}` | `{dauc:+.4f}` | `{drate:+.4f}` | `{davg:+.2f}` |".format(
                dataset=dataset_id,
                auc=b8["mismatch_auc"],
                rate=b8["wrong_detection_rate"],
                missed=b8["missed_wrong_count"],
                avg=b8["avg_actual_inputs_per_candidate"],
                dauc=delta["mismatch_auc_delta"],
                drate=delta["wrong_detection_rate_delta"],
                davg=delta["avg_actual_inputs_delta"],
            )
        )
    gate_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in summary["gate"].items())
    text = f"""# Decompilation Faithfulness Phase 12 Unified Low-Budget Evaluation

- Verdict: `{summary['verdict']}`
- Strategy: `{summary['strategy_id']}`
- Budgets: `{summary['budgets']}`

## Budget-8 Summary

| Dataset | Mismatch AUC | Wrong detection rate | Missed wrong | Avg actual inputs | AUC delta vs Phase10 | Detection delta vs Phase10 | Avg input delta |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Gate

| Gate | Passed |
|---|---:|
{gate_rows}

## Interpretation

This phase uses one input-ordering policy, `fixture_neighbor_first`, across all
current datasets. `Mismatch AUC` measures ranking quality; `Wrong detection
rate` measures how many wrong candidates are actually exposed by at least one
budgeted input. The deltas compare against Phase 10's original input order at
budget-8.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_decision(path: Path, summary: dict[str, Any]) -> None:
    verdict = summary["verdict"]
    if verdict == "pass-unified-budget8-low-budget-eval":
        decision = (
            "Phase 12 supports a unified final method: fixture-neighbor-first "
            "low-budget dynamic re-execution passes budget-8 gates on public "
            "static-hard, LLM-public, and Ghidra datasets."
        )
    elif verdict == "partial-unified-low-budget-eval":
        decision = (
            "Phase 12 is promising but not enough for a single universal budget-8 "
            "claim. The paper should either use dataset-specific/adaptive input "
            "ordering or add another input policy."
        )
    else:
        decision = (
            "Phase 12 fails the unified budget-8 gate. Do not make a CCF-A-level "
            "unified low-budget claim before improving input generation."
        )
    text = f"""# Decompilation Faithfulness Phase 12 Decision

## Verdict

`{verdict}`

## Decision

{decision}

## Next Step

If Phase 12 passes, update the method description and SOTA comparison tables to
use `fixture_neighbor_first` as the default low-budget input policy. If it is
partial or failed, inspect the failing datasets before writing the paper claim.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
