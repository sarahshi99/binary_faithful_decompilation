from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from analysis.decompile_faithfulness import dynamic_trace
from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu
from analysis.decompile_faithfulness import run_phase5b_hard_candidates as phase5b
from analysis.decompile_faithfulness import run_phase8_sota_hardening as phase8


DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase10_low_budget_rerun")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase10_low_budget_rerun.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase10_low_budget_rerun.zh.md")
DEFAULT_DECISION_ZH = Path("docs/paper_agent/decompile_faithfulness_phase10_decision.zh.md")
DEFAULT_BUDGETS = [1, 2, 4, 8, 16]


@dataclass(frozen=True)
class DatasetSpec:
    dataset_id: str
    title: str
    manifest_json: Path
    records_path: Path | None = None
    combined_summary_path: Path | None = None


DEFAULT_DATASETS = [
    DatasetSpec(
        dataset_id="phase7c2_static_hard_public",
        title="Phase 7C2 static-hard public",
        manifest_json=Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_function_manifest.json"),
        records_path=Path("analysis_outputs/decompile_faithfulness/phase7_static_hard/records.jsonl"),
    ),
    DatasetSpec(
        dataset_id="phase7e_llm_public_full_topup",
        title="Phase 7E LLM public full+top-up",
        manifest_json=Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_function_manifest.json"),
        combined_summary_path=Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public_combined.json"),
    ),
    DatasetSpec(
        dataset_id="phase6r_ghidra_full",
        title="Phase 6R Ghidra full",
        manifest_json=Path("docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json"),
        records_path=Path("analysis_outputs/decompile_faithfulness/phase6r_ghidra_full/records.jsonl"),
    ),
]


def main() -> None:
    args = parse_args()
    summary = run_phase10(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
        decision_zh=args.decision_zh,
        budgets=args.budget or DEFAULT_BUDGETS,
    )
    p7 = summary["datasets"]["phase7c2_static_hard_public"]["budget_metrics"]["8"]
    p6 = summary["datasets"]["phase6r_ghidra_full"]["budget_metrics"]["8"]
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "phase7c2_budget8_auc": p7["mismatch_auc"],
                "phase7c2_budget8_wrong_detection_rate": p7["wrong_detection_rate"],
                "phase6r_budget8_auc": p6["mismatch_auc"],
                "phase6r_budget8_wrong_detection_rate": p6["wrong_detection_rate"],
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
    parser.add_argument("--budget", type=int, action="append", default=None)
    return parser.parse_args()


def run_phase10(
    repo_root: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    decision_zh: Path,
    budgets: list[int],
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_dir = _resolve(repo_root, output_dir)
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    decision_zh = _resolve(repo_root, decision_zh)
    budgets = sorted(set(budgets))
    max_budget = max(budgets)
    datasets: dict[str, Any] = {}
    for spec in DEFAULT_DATASETS:
        datasets[spec.dataset_id] = rerun_dataset(
            repo_root=repo_root,
            output_dir=output_dir / spec.dataset_id,
            spec=spec,
            budgets=budgets,
            max_budget=max_budget,
        )
    gate = {
        "phase7c2_budget8_auc_gate": budget_metric(datasets, "phase7c2_static_hard_public", "8", "mismatch_auc") >= 0.98,
        "phase7c2_budget8_detection_gate": budget_metric(datasets, "phase7c2_static_hard_public", "8", "wrong_detection_rate") >= 0.95,
        "phase6r_budget8_auc_gate": budget_metric(datasets, "phase6r_ghidra_full", "8", "mismatch_auc") >= 0.98,
        "phase6r_budget8_detection_gate": budget_metric(datasets, "phase6r_ghidra_full", "8", "wrong_detection_rate") >= 0.95,
    }
    summary = {
        "phase": "phase10_low_budget_rerun",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "budgets": budgets,
        "max_budget": max_budget,
        "datasets": datasets,
        "gate": gate,
        "verdict": phase10_verdict(gate),
    }
    write_json(output_json, summary)
    write_markdown(output_zh, summary)
    write_decision(decision_zh, summary)
    return summary


def rerun_dataset(
    repo_root: Path,
    output_dir: Path,
    spec: DatasetSpec,
    budgets: list[int],
    max_budget: int,
) -> dict[str, Any]:
    records = load_records(repo_root, spec)
    eval_records = [
        record for record in records
        if record.get("compiled")
        and record.get("label") in {"faithful", "plausible_wrong"}
        and record.get("metadata", {}).get("function_source")
    ]
    manifest = json.loads(_resolve(repo_root, spec.manifest_json).read_text(encoding="utf-8"))
    entries_by_case = {entry["case_id"]: entry for entry in manifest.get("functions", [])}
    cases = {
        case_id: phase5_gpu._case_from_manifest_entry(repo_root, entry)
        for case_id, entry in entries_by_case.items()
    }
    trace_dir = output_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    original_cache: dict[tuple[str, str], dynamic_trace.TraceRun] = {}
    budget_records: dict[str, list[dict[str, Any]]] = {str(budget): [] for budget in budgets}
    skipped: list[dict[str, str]] = []
    for record in eval_records:
        case_id = str(record["case_id"])
        entry = entries_by_case.get(case_id)
        case = cases.get(case_id)
        if entry is None or case is None:
            skipped.append({"case_id": case_id, "candidate_id": str(record.get("candidate_id")), "reason": "missing_manifest_entry"})
            continue
        inputs = phase5b.phase5b_hard_trace_inputs(entry, max_inputs=max_budget)
        if not inputs:
            skipped.append({"case_id": case_id, "candidate_id": str(record.get("candidate_id")), "reason": "no_inputs"})
            continue
        opt_level = str(record.get("optimization_level", "O0"))
        original = cached_original_run(original_cache, case, inputs, trace_dir, opt_level)
        candidate = phase5_gpu.safe_run_trace(
            case=case,
            candidate_id=f"phase10_{record['candidate_id']}_k{max_budget}",
            function_source=str(record["metadata"]["function_source"]),
            inputs=inputs,
            output_dir=trace_dir,
            opt_level=opt_level,
        )
        for budget in budgets:
            budget_records[str(budget)].append(
                budget_record(record, inputs, original, candidate, budget)
            )
    write_jsonl(output_dir / "records_budgeted.jsonl", flatten_budget_records(budget_records))
    return {
        "dataset_id": spec.dataset_id,
        "title": spec.title,
        "source_candidate_count": len(records),
        "eval_candidate_count": len(eval_records),
        "rerun_candidate_count": sum(len(items) for items in budget_records.values()) // len(budgets),
        "skipped_count": len(skipped),
        "skipped": skipped[:20],
        "budget_metrics": {
            budget: summarize_budget(records_for_budget)
            for budget, records_for_budget in budget_records.items()
        },
    }


def load_records(repo_root: Path, spec: DatasetSpec) -> list[dict[str, Any]]:
    if spec.records_path is not None:
        return read_jsonl(_resolve(repo_root, spec.records_path))
    if spec.combined_summary_path is None:
        raise ValueError(f"dataset has no records path: {spec.dataset_id}")
    summary = json.loads(_resolve(repo_root, spec.combined_summary_path).read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for run_dir in summary.get("run_dirs", []):
        records.extend(read_jsonl(Path(run_dir) / "records.jsonl"))
    return phase8.dedupe_records(records)


def cached_original_run(
    cache: dict[tuple[str, str], dynamic_trace.TraceRun],
    case: phase5_gpu.fixtures.FunctionCase,
    inputs: list[dynamic_trace.TraceInput],
    trace_dir: Path,
    opt_level: str,
) -> dynamic_trace.TraceRun:
    key = (case.case_id, opt_level)
    if key not in cache:
        cache[key] = dynamic_trace.run_trace(
            case=case,
            candidate_id=f"phase10_original_k{len(inputs)}_{opt_level}",
            function_source=case.function_source,
            inputs=inputs,
            output_dir=trace_dir,
            opt_level=opt_level,
        )
    return cache[key]


def budget_record(
    source_record: dict[str, Any],
    inputs: list[dynamic_trace.TraceInput],
    original: dynamic_trace.TraceRun,
    candidate: dynamic_trace.TraceRun,
    budget: int,
) -> dict[str, Any]:
    actual_budget = min(budget, len(inputs))
    if (
        original.compiled
        and original.exit_code == 0
        and candidate.compiled
        and candidate.exit_code == 0
        and len(original.outputs) >= actual_budget
        and len(candidate.outputs) >= actual_budget
    ):
        components = dynamic_trace.trace_distance(
            inputs[:actual_budget],
            original.outputs[:actual_budget],
            candidate.outputs[:actual_budget],
        ).components
        compiled = True
        exit_code = candidate.exit_code
    else:
        components = phase3_cpu._failure_components(actual_budget)
        compiled = False
        exit_code = candidate.exit_code
    return {
        "case_id": source_record["case_id"],
        "candidate_id": source_record["candidate_id"],
        "label": source_record["label"] if compiled else "compile_fail",
        "source_label": source_record["label"],
        "compiled": compiled,
        "optimization_level": source_record.get("optimization_level", "O0"),
        "requested_budget": budget,
        "actual_budget": actual_budget,
        "features": {
            **components,
            "fixture_mismatch_rate": float(source_record["features"].get("fixture_mismatch_rate", 1.0)),
            "static_structured_total": float(source_record["features"].get("static_structured_total", 0.0)),
        },
        "diagnostics": {
            "candidate_exit_code": exit_code,
            "original_exit_code": original.exit_code,
        },
    }


def summarize_budget(records: list[dict[str, Any]]) -> dict[str, Any]:
    eval_records = [
        record for record in records
        if record.get("compiled") and record.get("label") in {"faithful", "plausible_wrong"}
    ]
    wrong_records = [record for record in eval_records if record["label"] == "plausible_wrong"]
    detected_wrong = [
        record for record in wrong_records
        if float(record["features"].get("trace_mismatch_count", 0.0)) > 0.0
    ]
    requested_budget = int(records[0]["requested_budget"]) if records else 0
    actual_input_evals = sum(int(record.get("actual_budget", 0)) for record in records)
    return {
        "requested_budget": requested_budget,
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record.get("compiled")),
        "eval_count": len(eval_records),
        "paired_case_count": paired_case_count(eval_records),
        "wrong_count": len(wrong_records),
        "wrong_detection_count": len(detected_wrong),
        "wrong_detection_rate": len(detected_wrong) / len(wrong_records) if wrong_records else 0.0,
        "actual_input_evals": actual_input_evals,
        "avg_actual_inputs_per_candidate": actual_input_evals / len(records) if records else 0.0,
        "mismatch_auc": pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("trace_mismatch_rate", 0.0)),
        ),
        "v3_auc": pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("trace_total", 0.0)),
        ),
        "fixture_auc": pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("fixture_mismatch_rate", 1.0)),
        ),
        "static_auc": pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("static_structured_total", 0.0)),
        ),
    }


def paired_case_count(records: list[dict[str, Any]]) -> int:
    total = 0
    for case_id in sorted({record.get("case_id") for record in records}):
        labels = {
            record.get("label")
            for record in records
            if record.get("case_id") == case_id
        }
        if "faithful" in labels and "plausible_wrong" in labels:
            total += 1
    return total


def pairwise_auc(records: list[dict[str, Any]], score_fn: Callable[[dict[str, Any]], float]) -> float:
    credit = 0.0
    pairs = 0
    for case_id in sorted({record.get("case_id") for record in records}):
        case_records = [record for record in records if record.get("case_id") == case_id]
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


def budget_metric(datasets: dict[str, Any], dataset_id: str, budget: str, metric: str) -> float:
    return float(datasets[dataset_id]["budget_metrics"].get(budget, {}).get(metric, 0.0))


def phase10_verdict(gate: dict[str, bool]) -> str:
    if all(gate.values()):
        return "pass-phase10-low-budget-rerun"
    if gate["phase7c2_budget8_auc_gate"] and gate["phase6r_budget8_auc_gate"]:
        return "low-budget-rerun-partial"
    return "low-budget-proxy-overestimated"


def flatten_budget_records(records_by_budget: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for budget in sorted(records_by_budget, key=lambda value: int(value)):
        rows.extend(records_by_budget[budget])
    return rows


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    rows = []
    for dataset in summary["datasets"].values():
        b8 = dataset["budget_metrics"].get("8", {})
        rows.append(
            "| `{dataset_id}` | `{rerun}` | `{auc:.4f}` | `{v3:.4f}` | `{rate:.4f}` | `{wrong}` | `{avg_inputs:.2f}` | `{inputs}` |".format(
                dataset_id=dataset["dataset_id"],
                rerun=dataset["rerun_candidate_count"],
                auc=b8.get("mismatch_auc", 0.0),
                v3=b8.get("v3_auc", 0.0),
                rate=b8.get("wrong_detection_rate", 0.0),
                wrong=b8.get("wrong_detection_count", 0),
                avg_inputs=b8.get("avg_actual_inputs_per_candidate", 0.0),
                inputs=b8.get("actual_input_evals", 0),
            )
        )
    curve_rows = []
    primary = summary["datasets"]["phase7c2_static_hard_public"]
    for budget, metrics in primary["budget_metrics"].items():
        curve_rows.append(
            "| `{budget}` | `{auc:.4f}` | `{v3:.4f}` | `{rate:.4f}` | `{wrong}` | `{avg_inputs:.2f}` | `{inputs}` |".format(
                budget=budget,
                auc=metrics["mismatch_auc"],
                v3=metrics["v3_auc"],
                rate=metrics["wrong_detection_rate"],
                wrong=metrics["wrong_detection_count"],
                avg_inputs=metrics["avg_actual_inputs_per_candidate"],
                inputs=metrics["actual_input_evals"],
            )
        )
    gate_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in summary["gate"].items())
    text = f"""# Decompilation Faithfulness Phase 10 Actual Low-Budget Rerun

- Verdict: `{summary['verdict']}`
- Budgets: `{summary['budgets']}`

## Budget-8 Summary

| Dataset | Rerun candidates | Mismatch AUC | V3 AUC | Wrong detection rate | Wrong detected | Avg actual inputs | Actual input evals |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Phase 7C2 Budget Curve

| Requested budget | Mismatch AUC | V3 AUC | Wrong detection rate | Wrong detected | Avg actual inputs | Actual input evals |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(curve_rows)}

## Gate

| Gate | Passed |
|---|---:|
{gate_rows}

## Interpretation

This is an actual low-budget rerun over deterministic generated-input prefixes.
Unlike Phase 9, it does not infer budget behavior from the full 128-input
mismatch count. Each candidate is re-executed on the first `max_budget` inputs,
and each budget is computed from that output prefix.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_decision(path: Path, summary: dict[str, Any]) -> None:
    verdict = summary["verdict"]
    if verdict == "pass-phase10-low-budget-rerun":
        decision = (
            "Phase 10 confirms the Phase 9 proxy. The defensible paper route is a "
            "low-budget generated-input dynamic re-execution auditor."
        )
    elif verdict == "low-budget-rerun-partial":
        decision = (
            "Phase 10 confirms low-budget ranking but not all detection-rate gates. "
            "The paper route needs a careful cost/recall tradeoff table."
        )
    else:
        decision = (
            "Phase 10 shows the Phase 9 proxy was too optimistic. The next step is a "
            "new hard-semantic benchmark or a better input generator."
        )
    text = f"""# Decompilation Faithfulness Phase 10 Decision

## Verdict

`{verdict}`

## Decision

{decision}

## Next Step

Use the Phase 10 table to decide whether the paper should pivot to
low-budget dynamic re-execution or return to hard-semantic benchmark design.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
