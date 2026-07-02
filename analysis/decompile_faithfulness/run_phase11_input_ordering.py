from __future__ import annotations

import argparse
import itertools
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import dynamic_trace
from analysis.decompile_faithfulness import run_phase10_low_budget_rerun as phase10
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu
from analysis.decompile_faithfulness import run_phase5b_hard_candidates as phase5b


DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase11_input_ordering")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase11_input_ordering.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase11_input_ordering.zh.md")
DEFAULT_DECISION_ZH = Path("docs/paper_agent/decompile_faithfulness_phase11_decision.zh.md")
DEFAULT_MANIFEST_JSON = Path("docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json")
DEFAULT_RECORDS_PATH = Path("analysis_outputs/decompile_faithfulness/phase6r_ghidra_full/records.jsonl")
DEFAULT_BUDGETS = [1, 2, 4, 8, 16]
STRATEGY_IDS = [
    "phase5b_original",
    "fixture_neighbor_first",
    "operator_char_class_first",
    "source_literal_char_interleave",
    "boundary_first",
    "mixed_boundary_neighbor",
]
OPERATOR_CHAR_CLASS_VALUES = (44, 41, 42, 47, 37, 45, 43, 36, 40, 94, 38, 124)


@dataclass(frozen=True)
class StrategyResult:
    strategy_id: str
    budget_metrics: dict[str, Any]
    rerun_candidate_count: int
    missed_wrong_by_budget: dict[str, list[dict[str, str]]]


def main() -> None:
    args = parse_args()
    summary = run_phase11(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
        decision_zh=args.decision_zh,
        manifest_json=args.manifest_json,
        records_path=args.records_path,
        budgets=args.budget or DEFAULT_BUDGETS,
        strategies=args.strategy or STRATEGY_IDS,
    )
    best8 = summary["best_by_budget"]["8"]
    best16 = summary["best_by_budget"]["16"]
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "best_budget8_strategy": best8["strategy_id"],
                "best_budget8_auc": best8["mismatch_auc"],
                "best_budget8_wrong_detection_rate": best8["wrong_detection_rate"],
                "best_budget16_strategy": best16["strategy_id"],
                "best_budget16_auc": best16["mismatch_auc"],
                "best_budget16_wrong_detection_rate": best16["wrong_detection_rate"],
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
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    parser.add_argument("--records-path", type=Path, default=DEFAULT_RECORDS_PATH)
    parser.add_argument("--budget", type=int, action="append", default=None)
    parser.add_argument("--strategy", action="append", default=None)
    return parser.parse_args()


def run_phase11(
    repo_root: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    decision_zh: Path,
    manifest_json: Path,
    records_path: Path,
    budgets: list[int],
    strategies: list[str],
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_dir = _resolve(repo_root, output_dir)
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    decision_zh = _resolve(repo_root, decision_zh)
    manifest_json = _resolve(repo_root, manifest_json)
    records_path = _resolve(repo_root, records_path)
    budgets = sorted(set(budgets))
    max_budget = max(budgets)

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    entries_by_case = {entry["case_id"]: entry for entry in manifest.get("functions", [])}
    cases = {
        case_id: phase5_gpu._case_from_manifest_entry(repo_root, entry)
        for case_id, entry in entries_by_case.items()
    }
    records = [
        record for record in phase10.read_jsonl(records_path)
        if record.get("compiled")
        and record.get("label") in {"faithful", "plausible_wrong"}
        and record.get("metadata", {}).get("function_source")
        and record.get("case_id") in entries_by_case
    ]

    strategy_results: dict[str, Any] = {}
    for strategy_id in strategies:
        strategy_results[strategy_id] = rerun_strategy(
            records=records,
            entries_by_case=entries_by_case,
            cases=cases,
            strategy_id=strategy_id,
            output_dir=output_dir / strategy_id,
            budgets=budgets,
            max_budget=max_budget,
        )

    best_by_budget = {
        str(budget): best_strategy_for_budget(strategy_results, str(budget))
        for budget in budgets
    }
    gate = {
        "budget8_auc_gate": best_by_budget.get("8", {}).get("mismatch_auc", 0.0) >= 0.98,
        "budget8_detection_gate": best_by_budget.get("8", {}).get("wrong_detection_rate", 0.0) >= 0.95,
        "budget16_auc_gate": best_by_budget.get("16", {}).get("mismatch_auc", 0.0) >= 0.98,
        "budget16_detection_gate": best_by_budget.get("16", {}).get("wrong_detection_rate", 0.0) >= 0.97,
    }
    summary = {
        "phase": "phase11_input_ordering",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_id": "phase6r_ghidra_full",
        "budgets": budgets,
        "max_budget": max_budget,
        "strategy_results": strategy_results,
        "best_by_budget": best_by_budget,
        "gate": gate,
        "verdict": phase11_verdict(gate),
    }
    phase10.write_json(output_json, summary)
    write_markdown(output_zh, summary)
    write_decision(decision_zh, summary)
    return summary


def rerun_strategy(
    records: list[dict[str, Any]],
    entries_by_case: dict[str, dict[str, Any]],
    cases: dict[str, phase5_gpu.fixtures.FunctionCase],
    strategy_id: str,
    output_dir: Path,
    budgets: list[int],
    max_budget: int,
) -> dict[str, Any]:
    trace_dir = output_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    original_cache: dict[tuple[str, str, str], dynamic_trace.TraceRun] = {}
    records_by_budget: dict[str, list[dict[str, Any]]] = {str(budget): [] for budget in budgets}
    input_counts_by_case: dict[str, int] = {}

    for record in records:
        case_id = str(record["case_id"])
        entry = entries_by_case[case_id]
        case = cases[case_id]
        inputs = build_ordered_inputs(entry, case, strategy_id, max_inputs=max_budget)
        input_counts_by_case[case_id] = len(inputs)
        if not inputs:
            continue
        opt_level = str(record.get("optimization_level", "O0"))
        cache_key = (case_id, opt_level, strategy_id)
        if cache_key not in original_cache:
            original_cache[cache_key] = dynamic_trace.run_trace(
                case=case,
                candidate_id=f"phase11_original_{strategy_id}_k{len(inputs)}_{opt_level}",
                function_source=case.function_source,
                inputs=inputs,
                output_dir=trace_dir,
                opt_level=opt_level,
            )
        candidate = phase5_gpu.safe_run_trace(
            case=case,
            candidate_id=f"phase11_{strategy_id}_{record['candidate_id']}_k{len(inputs)}",
            function_source=str(record["metadata"]["function_source"]),
            inputs=inputs,
            output_dir=trace_dir,
            opt_level=opt_level,
        )
        for budget in budgets:
            records_by_budget[str(budget)].append(
                phase10.budget_record(record, inputs, original_cache[cache_key], candidate, budget)
            )

    phase10.write_jsonl(output_dir / "records_budgeted.jsonl", phase10.flatten_budget_records(records_by_budget))
    budget_metrics = {
        budget: summarize_with_misses(rows)
        for budget, rows in records_by_budget.items()
    }
    return {
        "strategy_id": strategy_id,
        "rerun_candidate_count": sum(len(rows) for rows in records_by_budget.values()) // len(budgets),
        "input_counts_by_case": input_counts_by_case,
        "budget_metrics": budget_metrics,
    }


def build_ordered_inputs(
    entry: dict[str, Any],
    case: phase5_gpu.fixtures.FunctionCase,
    strategy_id: str,
    max_inputs: int,
) -> list[dynamic_trace.TraceInput]:
    original = phase5b.phase5b_hard_trace_inputs(entry, max_inputs=10_000)
    if strategy_id == "phase5b_original":
        return original[:max_inputs]
    if strategy_id == "fixture_neighbor_first":
        return dedupe_inputs(fixture_neighbor_inputs(entry) + original)[:max_inputs]
    if strategy_id == "operator_char_class_first":
        return dedupe_inputs(
            operator_char_class_inputs(entry) + fixture_neighbor_inputs(entry) + original
        )[:max_inputs]
    if strategy_id == "source_literal_char_interleave":
        return dedupe_inputs(
            interleave_inputs(
                fixture_neighbor_inputs(entry),
                source_literal_char_inputs(entry, case),
            )
            + original
        )[:max_inputs]
    if strategy_id == "boundary_first":
        return dedupe_inputs(boundary_inputs(entry, case) + original)[:max_inputs]
    if strategy_id == "mixed_boundary_neighbor":
        return dedupe_inputs(
            interleave_inputs(fixture_neighbor_inputs(entry), boundary_inputs(entry, case)) + original
        )[:max_inputs]
    raise ValueError(f"unknown strategy_id: {strategy_id}")


def fixture_neighbor_inputs(entry: dict[str, Any]) -> list[dynamic_trace.TraceInput]:
    fixtures = [tuple(int(value) for value in item["args"]) for item in entry.get("fixtures", [])]
    fixture_set = set(fixtures)
    if not fixtures:
        return []
    char_positions = char_like_positions(entry)
    generated: list[dynamic_trace.TraceInput] = []
    for args in fixtures:
        for index, value in enumerate(args):
            for neighbor in neighbor_values(value, index in char_positions):
                mutated = list(args)
                mutated[index] = neighbor
                candidate = tuple(mutated)
                if candidate in fixture_set or not domain_allows(entry, candidate):
                    continue
                generated.append(dynamic_trace.TraceInput(candidate, "fixture_neighbor"))
    return dedupe_inputs(generated)


def operator_char_class_inputs(entry: dict[str, Any]) -> list[dynamic_trace.TraceInput]:
    char_positions = char_like_positions(entry)
    if not char_positions:
        return []
    fixtures = [tuple(int(value) for value in item["args"]) for item in entry.get("fixtures", [])]
    fixture_set = set(fixtures)
    generated: list[dynamic_trace.TraceInput] = []
    for args in fixtures:
        for value in OPERATOR_CHAR_CLASS_VALUES:
            for index in sorted(char_positions):
                if index >= len(args) or args[index] == value:
                    continue
                mutated = list(args)
                mutated[index] = value
                candidate = tuple(mutated)
                if candidate in fixture_set or not domain_allows(entry, candidate):
                    continue
                generated.append(dynamic_trace.TraceInput(candidate, "operator_char_class"))
    return dedupe_inputs(generated)


def source_literal_char_inputs(
    entry: dict[str, Any],
    case: phase5_gpu.fixtures.FunctionCase,
) -> list[dynamic_trace.TraceInput]:
    char_positions = char_like_positions(entry)
    if not char_positions:
        return []
    values = source_char_literal_values(getattr(case, "function_source", ""))
    if not values:
        return []
    fixtures = [tuple(int(value) for value in item["args"]) for item in entry.get("fixtures", [])]
    fixture_set = set(fixtures)
    generated: list[dynamic_trace.TraceInput] = []
    for args in fixtures:
        for index in sorted(char_positions):
            if index >= len(args):
                continue
            for value in values:
                if args[index] == value:
                    continue
                mutated = list(args)
                mutated[index] = value
                candidate = tuple(mutated)
                if candidate in fixture_set or not domain_allows(entry, candidate):
                    continue
                generated.append(dynamic_trace.TraceInput(candidate, "source_literal_char"))
    return dedupe_inputs(generated)


def source_char_literal_values(source: str) -> list[int]:
    values: list[int] = []
    seen: set[int] = set()
    for match in re.finditer(r"'((?:\\.|[^\\'])*)'", source):
        raw = match.group(1)
        value = parse_c_char_literal_body(raw)
        if value is None or value in seen:
            continue
        seen.add(value)
        values.append(value)
    return values


def parse_c_char_literal_body(raw: str) -> int | None:
    if not raw:
        return None
    if not raw.startswith("\\"):
        return ord(raw[0]) if len(raw) == 1 else None
    if len(raw) == 1:
        return None
    escape = raw[1]
    simple = {
        "0": 0,
        "a": 7,
        "b": 8,
        "t": 9,
        "n": 10,
        "v": 11,
        "f": 12,
        "r": 13,
        "\\": 92,
        "'": 39,
        '"': 34,
        "?": 63,
    }
    if escape in simple and len(raw) == 2:
        return simple[escape]
    if escape == "x" and len(raw) > 2:
        digits = "".join(ch for ch in raw[2:] if ch in "0123456789abcdefABCDEF")
        return int(digits, 16) if digits else None
    if escape in "01234567":
        digits = "".join(ch for ch in raw[1:4] if ch in "01234567")
        return int(digits, 8) if digits else None
    return ord(escape) if len(raw) == 2 else None


def boundary_inputs(
    entry: dict[str, Any],
    case: phase5_gpu.fixtures.FunctionCase,
) -> list[dynamic_trace.TraceInput]:
    fixtures = [tuple(int(value) for value in item["args"]) for item in entry.get("fixtures", [])]
    fixture_set = set(fixtures)
    if not fixtures:
        return []
    arity = len(fixtures[0])
    values_by_position = boundary_values_by_position(entry)
    generated: list[dynamic_trace.TraceInput] = []

    for args in fixtures:
        generated.extend(dynamic_trace.TraceInput(candidate, "fixture_boundary") for candidate in single_position_boundary_args(entry, args))

    if arity == 1:
        for value in values_by_position[0]:
            generated.append(dynamic_trace.TraceInput((value,), "domain_boundary"))
    elif arity <= 4:
        for index in range(arity):
            for left in values_by_position[index]:
                for args in fixtures:
                    candidate = list(args)
                    candidate[index] = left
                    generated.append(dynamic_trace.TraceInput(tuple(candidate), "domain_boundary"))
        if arity == 2:
            for value in values_by_position[0]:
                generated.append(dynamic_trace.TraceInput((value, value), "equal_boundary"))

    dynamic_boundary = dynamic_trace.generate_boundary_trace_inputs(case, max_inputs=64, include_fixture_tests=False)
    generated.extend(
        dynamic_trace.TraceInput(trace_input.args, f"dynamic_{trace_input.bucket}")
        for trace_input in dynamic_boundary
    )
    return [
        trace_input for trace_input in dedupe_inputs(generated)
        if trace_input.args not in fixture_set and domain_allows(entry, trace_input.args)
    ]


def single_position_boundary_args(
    entry: dict[str, Any],
    args: tuple[int, ...],
) -> list[tuple[int, ...]]:
    values_by_position = boundary_values_by_position(entry)
    generated: list[tuple[int, ...]] = []
    for index, values in enumerate(values_by_position):
        for value in values:
            candidate = list(args)
            candidate[index] = value
            generated.append(tuple(candidate))
    return generated


def boundary_values_by_position(entry: dict[str, Any]) -> list[list[int]]:
    fixtures = [tuple(int(value) for value in item["args"]) for item in entry.get("fixtures", [])]
    if not fixtures:
        return []
    arity = len(fixtures[0])
    char_positions = char_like_positions(entry)
    values: list[list[int]] = []
    for index in range(arity):
        observed = {args[index] for args in fixtures}
        pool = set(observed)
        for value in list(observed):
            pool.update({value - 1, value + 1})
        pool.update({-1, 0, 1, 2})
        if all(value >= 0 for value in observed):
            pool = {value for value in pool if value >= 0}
            pool.update({0, 1, 2})
        if all(value > 0 for value in observed):
            pool = {value for value in pool if value > 0}
            pool.update({1, 2})
        if index in char_positions:
            pool = {value for value in pool if 0 <= value <= 127}
            pool.update({64, 65, 66, 73, 74, 75, 90})
        values.append(sorted(pool)[:12])
    return values


def neighbor_values(value: int, char_like: bool) -> list[int]:
    values = [value - 1, value + 1]
    if value != 0:
        values.append(0)
    if value != 1:
        values.append(1)
    if char_like:
        values.extend([64, 65, 66, 73, 74, 75, 90])
        values = [item for item in values if 0 <= item <= 127]
    return sorted(set(values))


def domain_allows(entry: dict[str, Any], args: tuple[int, ...]) -> bool:
    fixtures = [tuple(int(value) for value in item["args"]) for item in entry.get("fixtures", [])]
    if not fixtures:
        return True
    if all(value >= 0 for fixture in fixtures for value in fixture) and any(value < 0 for value in args):
        return False
    if all(value > 0 for fixture in fixtures for value in fixture) and any(value <= 0 for value in args):
        return False
    for index in char_like_positions(entry):
        if index < len(args) and not 0 <= args[index] <= 127:
            return False
    return True


def char_like_positions(entry: dict[str, Any]) -> set[int]:
    signature = entry.get("signature", "")
    if "char" not in signature:
        return set()
    inside = signature[signature.find("(") + 1:signature.rfind(")")]
    positions: set[int] = set()
    for index, part in enumerate(item.strip() for item in inside.split(",") if item.strip()):
        if "char" in part:
            positions.add(index)
    return positions


def interleave_inputs(
    left: list[dynamic_trace.TraceInput],
    right: list[dynamic_trace.TraceInput],
) -> list[dynamic_trace.TraceInput]:
    merged: list[dynamic_trace.TraceInput] = []
    for left_item, right_item in itertools.zip_longest(left, right):
        if left_item is not None:
            merged.append(left_item)
        if right_item is not None:
            merged.append(right_item)
    return merged


def dedupe_inputs(inputs: list[dynamic_trace.TraceInput]) -> list[dynamic_trace.TraceInput]:
    seen: set[tuple[int, ...]] = set()
    deduped: list[dynamic_trace.TraceInput] = []
    for trace_input in inputs:
        if trace_input.args in seen:
            continue
        seen.add(trace_input.args)
        deduped.append(trace_input)
    return deduped


def summarize_with_misses(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary = phase10.summarize_budget(records)
    summary["complete_eval"] = (
        summary["candidate_count"] == summary["compile_pass_count"] == summary["eval_count"]
    )
    missed = [
        {
            "case_id": str(record["case_id"]),
            "candidate_id": str(record["candidate_id"]),
            "optimization_level": str(record.get("optimization_level", "")),
        }
        for record in records
        if record.get("compiled")
        and record.get("source_label") == "plausible_wrong"
        and float(record.get("features", {}).get("trace_mismatch_count", 0.0)) == 0.0
    ]
    summary["missed_wrong_count"] = len(missed)
    summary["missed_wrong"] = missed
    return summary


def best_strategy_for_budget(strategy_results: dict[str, Any], budget: str) -> dict[str, Any]:
    best_id = ""
    best_metrics: dict[str, Any] = {}
    for strategy_id, result in strategy_results.items():
        metrics = result["budget_metrics"].get(budget, {})
        if not best_metrics or strategy_sort_key(metrics) > strategy_sort_key(best_metrics):
            best_id = strategy_id
            best_metrics = metrics
    return {"strategy_id": best_id, **best_metrics}


def strategy_sort_key(metrics: dict[str, Any]) -> tuple[float, float, float]:
    return (
        1.0 if metrics.get("complete_eval") else 0.0,
        float(metrics.get("mismatch_auc", 0.0)),
        float(metrics.get("wrong_detection_rate", 0.0)),
        -float(metrics.get("avg_actual_inputs_per_candidate", 0.0)),
    )


def phase11_verdict(gate: dict[str, bool]) -> str:
    if gate["budget8_auc_gate"] and gate["budget8_detection_gate"]:
        return "pass-ghidra-budget8-input-ordering"
    if gate["budget16_auc_gate"] and gate["budget16_detection_gate"]:
        return "pass-ghidra-adaptive-budget16"
    return "input-ordering-still-insufficient"


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    budget8_rows = []
    budget16_rows = []
    for strategy_id, result in summary["strategy_results"].items():
        for budget, rows in [("8", budget8_rows), ("16", budget16_rows)]:
            metrics = result["budget_metrics"][budget]
            rows.append(
                "| `{strategy}` | `{complete}` | `{auc:.4f}` | `{rate:.4f}` | `{missed}` | `{avg:.2f}` |".format(
                    strategy=strategy_id,
                    complete=metrics["complete_eval"],
                    auc=metrics["mismatch_auc"],
                    rate=metrics["wrong_detection_rate"],
                    missed=metrics["missed_wrong_count"],
                    avg=metrics["avg_actual_inputs_per_candidate"],
                )
            )
    gate_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in summary["gate"].items())
    best8 = summary["best_by_budget"]["8"]
    best16 = summary["best_by_budget"]["16"]
    text = f"""# Decompilation Faithfulness Phase 11 Ghidra Input Ordering

- Verdict: `{summary['verdict']}`
- Dataset: `{summary['dataset_id']}`
- Budgets: `{summary['budgets']}`

## Budget-8 Strategy Comparison

| Strategy | Complete eval | Mismatch AUC | Wrong detection rate | Missed wrong | Avg actual inputs |
|---|---:|---:|---:|---:|---:|
{chr(10).join(budget8_rows)}

## Budget-16 Strategy Comparison

| Strategy | Complete eval | Mismatch AUC | Wrong detection rate | Missed wrong | Avg actual inputs |
|---|---:|---:|---:|---:|---:|
{chr(10).join(budget16_rows)}

## Best Strategies

- Budget-8: `{best8['strategy_id']}` with AUC `{best8['mismatch_auc']:.4f}` and detection `{best8['wrong_detection_rate']:.4f}`.
- Budget-16: `{best16['strategy_id']}` with AUC `{best16['mismatch_auc']:.4f}` and detection `{best16['wrong_detection_rate']:.4f}`.

## Gate

| Gate | Passed |
|---|---:|
{gate_rows}

## Interpretation

This phase keeps candidates fixed and changes only the generated-input order.
The best-strategy selector prioritizes complete evaluations before AUC, so an
ordering that times out original/candidate executions is not allowed to win by
dropping hard cases. It tests whether Phase 10's Ghidra misses were caused by
late coverage of fixture-neighborhood and boundary cases.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_decision(path: Path, summary: dict[str, Any]) -> None:
    verdict = summary["verdict"]
    best8 = summary["best_by_budget"]["8"]
    best16 = summary["best_by_budget"]["16"]
    if verdict == "pass-ghidra-budget8-input-ordering":
        decision = (
            "Phase 11 fixes the Phase 10 Ghidra low-budget weakness. The paper can "
            "claim budget-8 dynamic re-execution across public static-hard, "
            "LLM-public, and Ghidra settings, with input ordering as a necessary "
            "component."
        )
    elif verdict == "pass-ghidra-adaptive-budget16":
        decision = (
            "Phase 11 does not make budget-8 universal, but it supports an adaptive "
            "budget claim: Ghidra needs up to 16 ordered inputs while public "
            "static-hard and LLM-public remain strong at budget-8."
        )
    else:
        decision = (
            "Phase 11 shows deterministic input ordering is still insufficient for "
            "the Ghidra low-budget gate. The paper should avoid universal low-budget "
            "claims and either add a stronger input generator or present Ghidra as a "
            "known limitation."
        )
    text = f"""# Decompilation Faithfulness Phase 11 Decision

## Verdict

`{verdict}`

## Result Meaning

Best budget-8 strategy: `{best8['strategy_id']}` with `Mismatch AUC = {best8['mismatch_auc']:.4f}` and `Wrong detection rate = {best8['wrong_detection_rate']:.4f}`.

Best budget-16 strategy: `{best16['strategy_id']}` with `Mismatch AUC = {best16['mismatch_auc']:.4f}` and `Wrong detection rate = {best16['wrong_detection_rate']:.4f}`.

`Mismatch AUC` measures whether wrong candidates are ranked above faithful ones.
`Wrong detection rate` measures how many wrong candidates are actually exposed by
at least one input in the budget prefix.

## Decision

{decision}

## Next Step

If Phase 11 passes budget-8, update the paper method to include input ordering
and move to broader SOTA comparison tables. If only budget-16 passes, frame the
method as adaptive-budget dynamic re-execution. If neither passes, design a
stronger generated-input policy before making CCF-A-level claims.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
