from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from analysis.decompile_faithfulness import run_phase8_sota_hardening as phase8


DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase9_input_budget.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase9_input_budget.zh.md")
DEFAULT_BUDGETS = [1, 2, 4, 8, 16, 32, 64, 128]


def main() -> None:
    args = parse_args()
    summary = run_phase9(
        repo_root=args.repo_root,
        output_json=args.output_json,
        output_zh=args.output_zh,
        budgets=args.budget or DEFAULT_BUDGETS,
    )
    primary = summary["datasets"]["phase7c2_static_hard_public"]
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "phase7c2_budget8_auc": primary["budget_curve"]["8"]["auc"],
                "phase7c2_budget8_wrong_mean": primary["budget_curve"]["8"]["wrong_detection_mean"],
                "phase7c2_budget8_wrong_p10": primary["budget_curve"]["8"]["wrong_detection_p10"],
                "v3_hard_family_delta_gate": summary["gate"]["v3_hard_family_delta_gate"],
                "budget8_low_cost_gate": summary["gate"]["budget8_low_cost_gate"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--budget", type=int, action="append", default=None)
    return parser.parse_args()


def run_phase9(
    repo_root: Path,
    output_json: Path,
    output_zh: Path,
    budgets: list[int],
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    datasets: dict[str, Any] = {}
    for spec in phase8.DEFAULT_DATASETS:
        records = phase8.load_dataset_records(repo_root, spec)
        datasets[spec.dataset_id] = analyze_dataset(spec, records, sorted(set(budgets)))
    primary = datasets["phase7c2_static_hard_public"]
    gate = {
        "budget8_low_cost_gate": budget_gate(primary, budget="8"),
        "v3_hard_family_delta_gate": any(
            group["delta_v3_vs_fuzzing_mismatch"] >= 0.03
            for dataset in datasets.values()
            for group in dataset["top_v3_family_deltas"]
        ),
    }
    summary = {
        "phase": "phase9_input_budget",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "budgets": sorted(set(budgets)),
        "datasets": datasets,
        "gate": gate,
        "verdict": phase9_verdict(gate),
        "interpretation": phase9_interpretation(gate),
    }
    write_json(output_json, summary)
    write_markdown(output_zh, summary)
    return summary


def analyze_dataset(
    spec: phase8.DatasetSpec,
    records: list[dict[str, Any]],
    budgets: list[int],
) -> dict[str, Any]:
    eval_records = [
        record for record in records
        if record.get("compiled") and record.get("label") in {"faithful", "plausible_wrong"}
    ]
    wrong_records = [record for record in eval_records if record["label"] == "plausible_wrong"]
    budget_curve = {
        str(budget): budget_metrics(eval_records, wrong_records, budget)
        for budget in budgets
    }
    family_metrics = grouped_family_metrics(eval_records)
    return {
        "dataset_id": spec.dataset_id,
        "title": spec.title,
        "candidate_count": len(records),
        "eval_count": len(eval_records),
        "wrong_count": len(wrong_records),
        "paired_case_count": len(phase8.build_case_stats(eval_records)),
        "label_counts": phase8.count_by(records, "label"),
        "component_auc": component_auc(eval_records),
        "budget_curve": budget_curve,
        "family_metrics": family_metrics,
        "top_v3_family_deltas": top_family_deltas(family_metrics),
    }


def budget_metrics(
    eval_records: list[dict[str, Any]],
    wrong_records: list[dict[str, Any]],
    budget: int,
) -> dict[str, float]:
    probabilities = [budget_hit_probability(record, budget) for record in wrong_records]
    return {
        "budget": float(budget),
        "auc": pairwise_auc(eval_records, lambda record: budget_hit_probability(record, budget)),
        "wrong_detection_mean": mean(probabilities),
        "wrong_detection_min": min(probabilities) if probabilities else 0.0,
        "wrong_detection_p10": percentile(probabilities, 0.10),
        "wrong_detection_p50": percentile(probabilities, 0.50),
    }


def budget_hit_probability(record: dict[str, Any], budget: int) -> float:
    features = record.get("features", {})
    input_count = int(round(float(features.get("trace_input_count", features.get("hard_probe_count", 0.0)))))
    mismatch_count = int(round(float(features.get("trace_mismatch_count", 0.0))))
    if budget <= 0 or input_count <= 0 or mismatch_count <= 0:
        return 0.0
    if mismatch_count >= input_count or budget >= input_count:
        return 1.0
    return 1.0 - no_mismatch_probability(input_count, mismatch_count, budget)


def no_mismatch_probability(input_count: int, mismatch_count: int, budget: int) -> float:
    good_count = input_count - mismatch_count
    if good_count <= 0:
        return 0.0
    if budget > good_count:
        return 0.0
    probability = 1.0
    for offset in range(budget):
        probability *= (good_count - offset) / (input_count - offset)
    return probability


def grouped_family_metrics(eval_records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in eval_records:
        groups[f"mutation:{record.get('mutation_type', '')}"].append(record)
        for risk in record.get("metadata", {}).get("risk_families") or []:
            groups[f"risk:{risk}"].append(record)
    return {
        group_id: group_metrics(group_id, group_records)
        for group_id, group_records in sorted(groups.items())
    }


def group_metrics(group_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    component = component_auc(records)
    return {
        "group_id": group_id,
        "candidate_count": len(records),
        "paired_case_count": len(phase8.build_case_stats(records)),
        "label_counts": phase8.count_by(records, "label"),
        "component_auc": component,
        "delta_v3_vs_fuzzing_mismatch": (
            component["v3_trace_total"] - component["fuzzing_mismatch_rate"]
        ),
    }


def top_family_deltas(family_metrics: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        family_metrics.values(),
        key=lambda item: (item["delta_v3_vs_fuzzing_mismatch"], item["paired_case_count"]),
        reverse=True,
    )
    return [
        {
            "group_id": item["group_id"],
            "paired_case_count": item["paired_case_count"],
            "candidate_count": item["candidate_count"],
            "delta_v3_vs_fuzzing_mismatch": item["delta_v3_vs_fuzzing_mismatch"],
            "v3_trace_total_auc": item["component_auc"]["v3_trace_total"],
            "fuzzing_mismatch_rate_auc": item["component_auc"]["fuzzing_mismatch_rate"],
        }
        for item in ranked[:10]
    ]


def component_auc(records: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "fixture_only": pairwise_auc(
            records,
            lambda record: float(record["features"].get("fixture_mismatch_rate", 1.0)),
        ),
        "static_structured_proxy": pairwise_auc(
            records,
            lambda record: float(record["features"].get("static_structured_total", 0.0)),
        ),
        "fuzzing_mismatch_rate": pairwise_auc(
            records,
            lambda record: float(record["features"].get("trace_mismatch_rate", 0.0)),
        ),
        "fuzzing_any_mismatch": pairwise_auc(
            records,
            lambda record: 1.0 if float(record["features"].get("trace_mismatch_rate", 0.0)) > 0.0 else 0.0,
        ),
        "trace_abs_error_mean": pairwise_auc(
            records,
            lambda record: float(record["features"].get("trace_abs_error_mean", 0.0)),
        ),
        "trace_boundary_mismatch_rate": pairwise_auc(
            records,
            lambda record: float(record["features"].get("trace_boundary_mismatch_rate", 0.0)),
        ),
        "trace_sign_mismatch_rate": pairwise_auc(
            records,
            lambda record: float(record["features"].get("trace_sign_mismatch_rate", 0.0)),
        ),
        "trace_zero_mismatch_rate": pairwise_auc(
            records,
            lambda record: float(record["features"].get("trace_zero_mismatch_rate", 0.0)),
        ),
        "v3_trace_total": pairwise_auc(
            records,
            lambda record: float(record["features"].get("trace_total", 0.0)),
        ),
    }


def pairwise_auc(records: list[dict[str, Any]], score_fn: Callable[[dict[str, Any]], float]) -> float:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["case_id"])].append(record)
    credit = 0.0
    pairs = 0
    for case_records in grouped.values():
        faithful = [record for record in case_records if record.get("label") == "faithful"]
        wrong = [record for record in case_records if record.get("label") == "plausible_wrong"]
        for faithful_record in faithful:
            faithful_score = score_fn(faithful_record)
            for wrong_record in wrong:
                pairs += 1
                wrong_score = score_fn(wrong_record)
                if wrong_score > faithful_score:
                    credit += 1.0
                elif wrong_score == faithful_score:
                    credit += 0.5
    return credit / pairs if pairs else 0.0


def budget_gate(dataset: dict[str, Any], budget: str) -> bool:
    metrics = dataset["budget_curve"].get(budget)
    if metrics is None:
        return False
    return (
        metrics["auc"] >= 0.99
        and metrics["wrong_detection_mean"] >= 0.98
        and metrics["wrong_detection_p10"] >= 0.95
    )


def phase9_verdict(gate: dict[str, bool]) -> str:
    if gate["v3_hard_family_delta_gate"]:
        return "v3-hard-family-claim"
    if gate["budget8_low_cost_gate"]:
        return "low-budget-dynamic-execution-claim"
    return "needs-new-hard-semantic-benchmark"


def phase9_interpretation(gate: dict[str, bool]) -> str:
    if gate["v3_hard_family_delta_gate"]:
        return "At least one current family separates v3 richer trace scoring from simple mismatch."
    if gate["budget8_low_cost_gate"]:
        return (
            "Current records support a low-budget generated-input dynamic execution claim: "
            "simple mismatch saturates ranking, and a small input budget catches most wrong candidates."
        )
    return (
        "Current records do not show v3-only margin and do not support a low-budget detection claim; "
        "a new hard-semantic benchmark is needed."
    )


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] * (1.0 - fraction) + ordered[high] * fraction


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    dataset_rows = []
    for dataset in summary["datasets"].values():
        b8 = dataset["budget_curve"].get("8", {})
        dataset_rows.append(
            "| `{dataset_id}` | `{paired}` | `{auc:.4f}` | `{mean:.4f}` | `{p10:.4f}` | `{minv:.4f}` | `{v3:.4f}` | `{fuzz:.4f}` |".format(
                dataset_id=dataset["dataset_id"],
                paired=dataset["paired_case_count"],
                auc=b8.get("auc", 0.0),
                mean=b8.get("wrong_detection_mean", 0.0),
                p10=b8.get("wrong_detection_p10", 0.0),
                minv=b8.get("wrong_detection_min", 0.0),
                v3=dataset["component_auc"]["v3_trace_total"],
                fuzz=dataset["component_auc"]["fuzzing_mismatch_rate"],
            )
        )
    curve_rows = []
    primary = summary["datasets"]["phase7c2_static_hard_public"]
    for budget, metrics in primary["budget_curve"].items():
        curve_rows.append(
            "| `{budget}` | `{auc:.4f}` | `{mean:.4f}` | `{p10:.4f}` | `{minv:.4f}` |".format(
                budget=budget,
                auc=metrics["auc"],
                mean=metrics["wrong_detection_mean"],
                p10=metrics["wrong_detection_p10"],
                minv=metrics["wrong_detection_min"],
            )
        )
    family_rows = []
    for item in primary["top_v3_family_deltas"][:8]:
        family_rows.append(
            "| `{group_id}` | `{paired}` | `{fuzz:.4f}` | `{v3:.4f}` | `{delta:.4f}` |".format(
                group_id=item["group_id"],
                paired=item["paired_case_count"],
                fuzz=item["fuzzing_mismatch_rate_auc"],
                v3=item["v3_trace_total_auc"],
                delta=item["delta_v3_vs_fuzzing_mismatch"],
            )
        )
    gate_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in summary["gate"].items())
    text = f"""# Decompilation Faithfulness Phase 9 Input Budget

- Verdict: `{summary['verdict']}`
- Interpretation: {summary['interpretation']}

## Dataset Summary

| Dataset | Paired cases | Budget-8 AUC | Budget-8 wrong mean | Budget-8 wrong p10 | Budget-8 wrong min | V3 AUC | Fuzz mismatch AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(dataset_rows)}

## Phase 7C2 Budget Curve

| Budget | AUC | Wrong detect mean | Wrong detect p10 | Wrong detect min |
|---|---:|---:|---:|---:|
{chr(10).join(curve_rows)}

## Phase 7C2 Top V3 Family Deltas

| Group | Paired cases | Fuzz mismatch AUC | V3 AUC | Delta |
|---|---:|---:|---:|---:|
{chr(10).join(family_rows)}

## Gate

| Gate | Passed |
|---|---:|
{gate_rows}

## Interpretation

Phase 9 shows whether the current evidence supports a low-budget dynamic
execution claim or a v3-specific scoring claim. AUC can saturate even at
budget 1 because faithful candidates often have zero mismatch while wrong
candidates have nonzero mismatch. The wrong-candidate detection statistics
therefore matter more for cost-sensitive claims.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
