from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import dynamic_trace
from analysis.decompile_faithfulness import run_phase10_low_budget_rerun as phase10
from analysis.decompile_faithfulness import run_phase11_input_ordering as phase11
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu
from analysis.decompile_faithfulness import run_phase14_paper_readiness as phase14


DEFAULT_PHASE12_DIR = Path("analysis_outputs/decompile_faithfulness/phase12_unified_low_budget")
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase16_runtime_risk")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase16_runtime_risk.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase16_runtime_risk.zh.md")
DEFAULT_BUDGET = 8
DEFAULT_STRATEGY = "fixture_neighbor_first"


def main() -> None:
    args = parse_args()
    summary = run_phase16(
        repo_root=args.repo_root,
        phase12_dir=args.phase12_dir,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
        budget=args.budget,
        strategy_id=args.strategy_id,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "budget": summary["budget"],
                "runtime": {
                    dataset_id: {
                        "candidate_count": item["candidate_count"],
                        "total_seconds": item["total_seconds"],
                        "mean_seconds_per_candidate": item["mean_seconds_per_candidate"],
                    }
                    for dataset_id, item in summary["runtime"].items()
                },
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--phase12-dir", type=Path, default=DEFAULT_PHASE12_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--strategy-id", default=DEFAULT_STRATEGY)
    return parser.parse_args()


def run_phase16(
    repo_root: Path,
    phase12_dir: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    budget: int,
    strategy_id: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    phase12_dir = _resolve(repo_root, phase12_dir)
    output_dir = _resolve(repo_root, output_dir)
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    runtime: dict[str, Any] = {}
    risk_breakdown: dict[str, list[dict[str, Any]]] = {}
    for spec in phase10.DEFAULT_DATASETS:
        manifest = load_manifest(repo_root, spec.manifest_json)
        entries_by_case = {entry["case_id"]: entry for entry in manifest.get("functions", [])}
        runtime[spec.dataset_id] = measure_dataset_runtime(
            repo_root=repo_root,
            output_dir=output_dir / spec.dataset_id,
            spec=spec,
            entries_by_case=entries_by_case,
            budget=budget,
            strategy_id=strategy_id,
        )
        records = [
            record for record in phase14.read_jsonl(phase12_dir / spec.dataset_id / "records_budgeted.jsonl")
            if int(record.get("requested_budget", -1)) == budget
            and record.get("compiled")
            and record.get("label") in {"faithful", "plausible_wrong"}
        ]
        risk_breakdown[spec.dataset_id] = risk_family_breakdown(records, entries_by_case)
    gate = build_gate(runtime, risk_breakdown)
    summary = {
        "phase": "phase16_runtime_risk_breakdown",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "budget": budget,
        "strategy_id": strategy_id,
        "runtime": runtime,
        "risk_breakdown": risk_breakdown,
        "gate": gate,
        "verdict": phase16_verdict(gate),
    }
    write_json(output_json, summary)
    write_markdown(output_zh, summary)
    return summary


def measure_dataset_runtime(
    repo_root: Path,
    output_dir: Path,
    spec: phase10.DatasetSpec,
    entries_by_case: dict[str, dict[str, Any]],
    budget: int,
    strategy_id: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_dir = output_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    records = [
        record for record in phase10.load_records(repo_root, spec)
        if record.get("compiled")
        and record.get("label") in {"faithful", "plausible_wrong"}
        and record.get("metadata", {}).get("function_source")
        and record.get("case_id") in entries_by_case
    ]
    cases = {
        case_id: phase5_gpu._case_from_manifest_entry(repo_root, entry)
        for case_id, entry in entries_by_case.items()
    }
    original_cache: dict[tuple[str, str], dynamic_trace.TraceRun] = {}
    candidate_seconds: list[float] = []
    actual_input_evals = 0
    skipped_no_inputs = 0
    timed_records: list[dict[str, Any]] = []
    dataset_start = time.perf_counter()
    for record in records:
        case_id = str(record["case_id"])
        case = cases[case_id]
        entry = entries_by_case[case_id]
        inputs = phase11.build_ordered_inputs(entry, case, strategy_id, max_inputs=budget)
        if not inputs:
            skipped_no_inputs += 1
            continue
        opt_level = str(record.get("optimization_level", "O0"))
        key = (case_id, opt_level)
        start = time.perf_counter()
        if key not in original_cache:
            original_cache[key] = dynamic_trace.run_trace(
                case=case,
                candidate_id=f"phase16_original_{strategy_id}_{opt_level}",
                function_source=case.function_source,
                inputs=inputs,
                output_dir=trace_dir,
                opt_level=opt_level,
            )
        candidate = phase5_gpu.safe_run_trace(
            case=case,
            candidate_id=f"phase16_{strategy_id}_{record['candidate_id']}",
            function_source=str(record["metadata"]["function_source"]),
            inputs=inputs,
            output_dir=trace_dir,
            opt_level=opt_level,
        )
        elapsed = time.perf_counter() - start
        candidate_seconds.append(elapsed)
        actual_budget = min(budget, len(inputs))
        actual_input_evals += actual_budget
        timed_records.append(
            {
                "case_id": case_id,
                "candidate_id": str(record["candidate_id"]),
                "optimization_level": opt_level,
                "seconds": elapsed,
                "actual_budget": actual_budget,
                "compiled": bool(candidate.compiled),
                "candidate_exit_code": candidate.exit_code,
                "original_exit_code": original_cache[key].exit_code,
            }
        )
    total_seconds = time.perf_counter() - dataset_start
    phase10.write_jsonl(output_dir / "timed_records.jsonl", timed_records)
    summary = summarize_runtime(candidate_seconds, actual_input_evals, total_seconds)
    summary["skipped_no_input_count"] = skipped_no_inputs
    return summary


def summarize_runtime(
    candidate_seconds: list[float],
    actual_input_evals: int,
    total_seconds: float,
) -> dict[str, Any]:
    candidate_count = len(candidate_seconds)
    return {
        "candidate_count": candidate_count,
        "total_seconds": total_seconds,
        "mean_seconds_per_candidate": statistics.mean(candidate_seconds) if candidate_seconds else 0.0,
        "median_seconds_per_candidate": statistics.median(candidate_seconds) if candidate_seconds else 0.0,
        "p95_seconds_per_candidate": percentile(candidate_seconds, 0.95),
        "actual_input_evals": actual_input_evals,
        "input_evals_per_second": actual_input_evals / total_seconds if total_seconds > 0 else 0.0,
    }


def risk_family_breakdown(
    records: list[dict[str, Any]],
    entries_by_case: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        case_id = str(record["case_id"])
        families = entries_by_case.get(case_id, {}).get("risk_families") or ["unlabeled"]
        for family in families:
            by_family[str(family)].append(record)
    rows = []
    for family, family_records in sorted(by_family.items()):
        rows.append(
            {
                "risk_family": family,
                "case_count": len({str(record["case_id"]) for record in family_records}),
                "candidate_count": len(family_records),
                "paired_case_count": phase14.paired_case_count(family_records),
                "auc": phase14.pairwise_auc(family_records),
                "wrong_detection_rate": phase14.wrong_detection_rate(family_records),
                "missed_wrong_count": phase14.miss_taxonomy(family_records)["missed_wrong_count"],
            }
        )
    return rows


def build_gate(
    runtime: dict[str, Any],
    risk_breakdown: dict[str, list[dict[str, Any]]],
) -> dict[str, bool]:
    gate = {
        f"{dataset_id}_runtime_present": item["candidate_count"] > 0 and item["total_seconds"] > 0
        for dataset_id, item in runtime.items()
    }
    gate.update(
        {
            f"{dataset_id}_risk_rows_present": bool(rows)
            for dataset_id, rows in risk_breakdown.items()
        }
    )
    for dataset_id, rows in risk_breakdown.items():
        risky_rows = [row for row in rows if row["paired_case_count"] >= 3]
        gate[f"{dataset_id}_large_risk_family_auc_gate"] = all(row["auc"] >= 0.90 for row in risky_rows)
        gate[f"{dataset_id}_large_risk_family_detection_gate"] = all(
            row["wrong_detection_rate"] >= 0.90 for row in risky_rows
        )
    return gate


def phase16_verdict(gate: dict[str, bool]) -> str:
    if all(gate.values()):
        return "pass-phase16-runtime-risk-breakdown"
    if any(gate.values()):
        return "partial-phase16-runtime-risk-breakdown"
    return "fail-phase16-runtime-risk-breakdown"


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))
    return ordered[index]


def load_manifest(repo_root: Path, manifest_path: Path) -> dict[str, Any]:
    return json.loads(_resolve(repo_root, manifest_path).read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    runtime_rows = []
    risk_sections = []
    for dataset_id, item in summary["runtime"].items():
        runtime_rows.append(
            "| `{dataset}` | `{count}` | `{skipped}` | `{total:.2f}` | `{mean:.4f}` | `{median:.4f}` | `{p95:.4f}` | `{evals}` | `{rate:.2f}` |".format(
                dataset=dataset_id,
                count=item["candidate_count"],
                skipped=item.get("skipped_no_input_count", 0),
                total=item["total_seconds"],
                mean=item["mean_seconds_per_candidate"],
                median=item["median_seconds_per_candidate"],
                p95=item["p95_seconds_per_candidate"],
                evals=item["actual_input_evals"],
                rate=item["input_evals_per_second"],
            )
        )
    for dataset_id, rows in summary["risk_breakdown"].items():
        top_rows = sorted(rows, key=lambda row: (-row["paired_case_count"], row["risk_family"]))[:12]
        rendered = [
            "| `{family}` | `{cases}` | `{candidates}` | `{paired}` | `{auc:.4f}` | `{det:.4f}` | `{missed}` |".format(
                family=row["risk_family"],
                cases=row["case_count"],
                candidates=row["candidate_count"],
                paired=row["paired_case_count"],
                auc=row["auc"],
                det=row["wrong_detection_rate"],
                missed=row["missed_wrong_count"],
            )
            for row in top_rows
        ]
        risk_sections.append(
            "### `{}`\n\n| Risk family | Cases | Candidates | Paired cases | AUC | Detection | Missed wrong |\n|---|---:|---:|---:|---:|---:|---:|\n{}".format(
                dataset_id,
                "\n".join(rendered),
            )
        )
    gate_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in summary["gate"].items())
    text = f"""# Decompilation Faithfulness Phase 16 Runtime And Risk Breakdown

- Verdict: `{summary['verdict']}`
- Strategy: `{summary['strategy_id']}`
- Budget: `{summary['budget']}`

## Runtime

| Dataset | Candidates | Skipped no-input | Total seconds | Mean sec/candidate | Median sec/candidate | P95 sec/candidate | Input evals | Input evals/sec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(runtime_rows)}

Timing includes trace harness compilation and execution inside the current Python
runner. Original traces are cached per case/optimization level, so the timing
matches the deployed auditor's amortized behavior rather than compiling the
original for every candidate.

## Risk-Family Breakdown

{chr(10).join(risk_sections)}

## Gate

| Gate | Passed |
|---|---:|
{gate_rows}

## Interpretation

This phase fills the paper's runtime and risk-family table gaps. Risk-family
rows with at least three paired cases are used for the gate; smaller rows are
reported descriptively but should not be overinterpreted.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
