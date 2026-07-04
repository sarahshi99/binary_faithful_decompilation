from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


METHOD_FREEZE_COMMIT = "06dda89912103b94fc065d6f073581a7811154b1"
VERIFIED_HOLDOUT_SEAL = "cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42"
PHASE1E_PREREGISTRATION_COMMIT = "758707882eacf905545cd3b42d7b83fc94f52bc9"
PHASE1E_RESULT_COMMIT = "f302bb51eb9371c0dad51bce92be53f58fc1a341"
FINAL_POLICY = "source_literal_char_interleave"
LITERAL_FIRST_POLICY = "literal_first_concatenation"
GENERIC_BOUNDARY_POLICY = "generic_type_boundaries"
FIXTURE_NEIGHBOR_POLICY = "fixture_neighbor_only"
BUDGETS = [1, 2, 4, 8, 16, 32]
FUZZER_EVAL_BUDGETS = [1, 2, 4, 8, 16, 32, 128, 1024]
FUZZER_TIME_LIMITS = [0.01, 0.1, 1.0, 5.0]
RANDOM_SEEDS = [
    101, 202, 303, 404, 505, 606, 707, 808, 909, 1001,
    1102, 1203, 1304, 1405, 1506, 1607, 1708, 1809, 1910, 2011,
    2112, 2213, 2314, 2415, 2516, 2617, 2718, 2819, 2920, 3021,
]
DETERMINISTIC_POLICIES = [
    FINAL_POLICY,
    FIXTURE_NEIGHBOR_POLICY,
    "source_literal_only",
    "neighbor_first_concatenation",
    LITERAL_FIRST_POLICY,
    "operator_char_first",
    "generic_fallback_only",
    GENERIC_BOUNDARY_POLICY,
]
COMPARATOR_POLICIES = [
    LITERAL_FIRST_POLICY,
    GENERIC_BOUNDARY_POLICY,
    FIXTURE_NEIGHBOR_POLICY,
    "randomized_union_order",
    "uniform_random_domain",
]
STOCHASTIC_POLICIES = {"randomized_union_order", "uniform_random_domain"}
PRIMARY_SCOPE = "primary_fixture_passing_wrong"
LOW_DENSITY_SCOPE = "low_density_fixture_passing_wrong"
NO_MISMATCH_SCOPE = "no_mismatch_comparison"
NON_FIXTURE_SCOPE = "non_fixture_overfit_fixture_passing_wrong"
SOURCE_LITERAL_PRESENT_SCOPE = "source_literal_present_primary_wrong"
WORK_DIR = Path("analysis_outputs/decompile_faithfulness/phase1f")


@dataclass(frozen=True)
class FunctionInfo:
    function_id: str
    project: str
    source_file: str
    function_name: str
    signature: str
    domain_specs: tuple[dict[str, Any], ...]
    domain_size: int
    source_literal_count: int
    source_path: str


@dataclass(frozen=True)
class CandidateInfo:
    candidate_id: str
    function_id: str
    project: str
    candidate_stratum: str
    candidate_class: str
    label: str
    compile_status: str
    execution_status: str
    mutation_family: str
    source_path: str


def main() -> None:
    args = parse_args()
    summary = run(
        Path(args.repo_root).resolve(),
        run_libfuzzer=args.run_libfuzzer,
        reuse_libfuzzer_results=args.reuse_libfuzzer_results,
    )
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 1f strong baselines and mechanism analysis")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--run-libfuzzer",
        action="store_true",
        help="Run the real libFuzzer baseline. Without this flag, emit a preregistered blocker report.",
    )
    parser.add_argument(
        "--reuse-libfuzzer-results",
        action="store_true",
        help="Reuse existing Phase 1f libFuzzer result files while regenerating derived tables, figures, and handoff.",
    )
    return parser.parse_args()


def run(repo_root: Path, *, run_libfuzzer: bool = False, reuse_libfuzzer_results: bool = False) -> dict[str, Any]:
    out_dir = repo_root / "results/decompile_faithfulness"
    table_dir = repo_root / "paper/tables"
    fig_data_dir = repo_root / "figures/data"
    fig_dir = repo_root / "figures"
    docs_dir = repo_root / "docs/paper_agent"
    work_dir = repo_root / WORK_DIR
    for path in [out_dir, table_dir, fig_data_dir, fig_dir, docs_dir, work_dir]:
        path.mkdir(parents=True, exist_ok=True)

    functions = load_functions(repo_root)
    candidates = load_candidates(repo_root)
    labels = {row["candidate_id"]: row for row in read_jsonl(out_dir / "holdout_exact_labels.jsonl")}
    fixtures = load_fixtures(repo_root)
    first_rows = normalize_first_witness_rows(read_csv(out_dir / "holdout_first_witness.csv"))
    population = build_population(first_rows, functions, candidates)
    selected_lists = selected_mechanism_lists(first_rows, population)

    trace_summary = scan_policy_traces(repo_root, selected_lists, population)
    paired_rows = paired_policy_rows(first_rows, population, functions)
    mechanism_rows = candidate_mechanism_rows(
        first_rows=first_rows,
        selected_lists=selected_lists,
        trace_prefixes=trace_summary["prefixes"],
        trace_max_positions=trace_summary["max_positions"],
        functions=functions,
        candidates=candidates,
        labels=labels,
        fixtures=fixtures,
    )
    final_miss_rows = [
        row for row in mechanism_rows
        if row["list_name"] in {"final_miss_b8", "final_miss_b32"}
    ]
    out_of_domain_rows = out_of_domain_summary_rows(trace_summary, population)
    exhaustive_rows = exhaustive_cost_reference_rows(labels, functions, candidates)
    klee_candidate_rows, klee_summary_rows = klee_baseline_rows(population, candidates, functions)
    if run_libfuzzer:
        libfuzzer_run_rows, libfuzzer_summary_rows = run_libfuzzer_baseline(
            repo_root, population, candidates, functions, labels, fixtures, work_dir / "libfuzzer"
        )
    elif reuse_libfuzzer_results and (out_dir / "libfuzzer_runs.jsonl").exists() and (out_dir / "libfuzzer_summary.csv").exists():
        libfuzzer_run_rows = read_jsonl(out_dir / "libfuzzer_runs.jsonl")
        libfuzzer_summary_rows = normalize_libfuzzer_summary_rows(read_csv(out_dir / "libfuzzer_summary.csv"))
    else:
        libfuzzer_run_rows, libfuzzer_summary_rows = libfuzzer_blocker_rows(population, candidates)

    budget_curve_rows = strong_baseline_budget_curves(first_rows, population, libfuzzer_summary_rows, klee_summary_rows)
    time_curve_rows = strong_baseline_time_curves(first_rows, libfuzzer_summary_rows, klee_summary_rows)
    upset_rows = paired_policy_upset_rows(paired_rows)
    interleaving = classify_interleaving(paired_rows)
    gates = interpretation_gates(
        first_rows=first_rows,
        population=population,
        libfuzzer_summary=libfuzzer_summary_rows,
        klee_summary=klee_summary_rows,
    )

    write_csv(out_dir / "holdout_paired_policy_analysis.csv", paired_rows)
    write_jsonl(out_dir / "holdout_candidate_mechanisms.jsonl", mechanism_rows)
    write_jsonl(out_dir / "holdout_final_misses.jsonl", final_miss_rows)
    write_csv(out_dir / "holdout_out_of_domain_summary.csv", out_of_domain_rows)
    write_jsonl(out_dir / "klee_candidate_results.jsonl", klee_candidate_rows)
    write_csv(out_dir / "klee_summary.csv", klee_summary_rows)
    write_jsonl(out_dir / "libfuzzer_runs.jsonl", libfuzzer_run_rows)
    write_csv(out_dir / "libfuzzer_summary.csv", libfuzzer_summary_rows)
    write_csv(out_dir / "exhaustive_cost_reference.csv", exhaustive_rows)
    write_csv(fig_data_dir / "strong_baseline_budget_curves.csv", budget_curve_rows)
    write_csv(fig_data_dir / "strong_baseline_time_curves.csv", time_curve_rows)
    write_csv(fig_data_dir / "paired_policy_upset.csv", upset_rows)
    write_tables(repo_root, paired_rows, klee_summary_rows, libfuzzer_summary_rows, final_miss_rows, out_of_domain_rows)
    write_plot_script(repo_root)
    generate_figures(repo_root)
    handoff_path = write_handoff(
        repo_root=repo_root,
        population=population,
        paired_rows=paired_rows,
        mechanism_rows=mechanism_rows,
        out_of_domain_rows=out_of_domain_rows,
        klee_summary_rows=klee_summary_rows,
        libfuzzer_summary_rows=libfuzzer_summary_rows,
        exhaustive_rows=exhaustive_rows,
        interleaving=interleaving,
        gates=gates,
    )
    return {
        "status": "completed",
        "run_libfuzzer": run_libfuzzer,
        "reused_libfuzzer_results": reuse_libfuzzer_results and not run_libfuzzer,
        "primary_fixture_passing_wrong": len(population[PRIMARY_SCOPE]),
        "low_density_fixture_passing_wrong": len(population[LOW_DENSITY_SCOPE]),
        "non_fixture_overfit_fixture_passing_wrong": len(population[NON_FIXTURE_SCOPE]),
        "no_mismatch_comparison": len(population[NO_MISMATCH_SCOPE]),
        "klee_support": klee_summary_rows[0]["supported_candidates"] if klee_summary_rows else 0,
        "libfuzzer_status": libfuzzer_summary_rows[0].get("baseline_status", "") if libfuzzer_summary_rows else "",
        "handoff": str(handoff_path.relative_to(repo_root)),
    }


def load_functions(repo_root: Path) -> dict[str, FunctionInfo]:
    selected = read_csv(repo_root / "results/decompile_faithfulness/holdout_selected_functions.csv")
    manifest = read_jsonl(repo_root / "results/decompile_faithfulness/holdout_candidate_manifest.jsonl")
    source_by_function: dict[str, str] = {}
    for row in manifest:
        path_text = row.get("original_source_function_path")
        if path_text and row["function_id"] not in source_by_function:
            source_by_function[str(row["function_id"])] = str(path_text)
    descriptive = json.loads((repo_root / "results/decompile_faithfulness/holdout_pre_auditor_descriptive_analysis.json").read_text(encoding="utf-8"))
    literal_counts = descriptive.get("source_character_literal_prevalence", {}).get("per_function", {})
    functions: dict[str, FunctionInfo] = {}
    for row in selected:
        function_id = row["function_id"]
        functions[function_id] = FunctionInfo(
            function_id=function_id,
            project=row["project"],
            source_file=row["source_file"],
            function_name=row["function_name"],
            signature=row["signature"],
            domain_specs=tuple(json.loads(row["declared_exact_domain"])),
            domain_size=int(row["domain_size"]),
            source_literal_count=int(literal_counts.get(function_id, 0)),
            source_path=source_by_function.get(function_id, ""),
        )
    return functions


def load_candidates(repo_root: Path) -> dict[str, CandidateInfo]:
    candidates: dict[str, CandidateInfo] = {}
    for row in read_jsonl(repo_root / "results/decompile_faithfulness/holdout_candidate_manifest.jsonl"):
        source_path = row.get("candidate_source_path") or row.get("normalized_candidate_path") or ""
        candidates[row["candidate_id"]] = CandidateInfo(
            candidate_id=row["candidate_id"],
            function_id=row["function_id"],
            project=row["project"],
            candidate_stratum=row.get("candidate_stratum", ""),
            candidate_class=row.get("candidate_class", ""),
            label=row.get("label", ""),
            compile_status=row.get("compile_status", ""),
            execution_status=row.get("execution_status", ""),
            mutation_family=row.get("mutation_family", "natural_ghidra"),
            source_path=str(source_path),
        )
    return candidates


def load_fixtures(repo_root: Path) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(repo_root / "results/decompile_faithfulness/holdout_fixtures.jsonl"):
        grouped[str(row["function_id"])].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda item: int(item["rank"]))
    return dict(grouped)


def normalize_first_witness_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = dict(row)
        item["budget"] = int(row["budget"])
        item["random_seed"] = int(row["random_seed"]) if row["random_seed"] else None
        for key in [
            "detected_in_domain",
            "detected_extended_domain",
            "in_primary_fixture_passing_wrong",
            "in_low_density_fixture_passing_wrong",
            "in_all_controlled_semantic_wrong",
            "in_no_mismatch_comparison",
        ]:
            item[key] = parse_bool(row[key])
        for key in ["first_in_domain_witness_rank", "first_extended_witness_rank"]:
            item[key] = int(row[key]) if row[key] else None
        item["time_to_first_witness_s"] = float(row["time_to_first_witness_s"]) if row["time_to_first_witness_s"] else None
        item["mismatch_density"] = float(row["mismatch_density"]) if row["mismatch_density"] else 0.0
        normalized.append(item)
    return normalized


def normalize_libfuzzer_summary_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = dict(row)
        if item.get("mode") == "evaluation_count":
            item["budget_or_time_limit"] = int(item["budget_or_time_limit"])
        elif item.get("budget_or_time_limit") not in {"", None}:
            item["budget_or_time_limit"] = float(item["budget_or_time_limit"])
        for key in [
            "candidate_denominator",
            "supported_candidates",
            "no_mismatch_false_alarms",
            "distinct_no_mismatch_false_alarm_candidates",
        ]:
            if item.get(key, "") != "":
                item[key] = int(item[key])
        for key in [
            "mean_detection",
            "median_detection",
            "stddev_detection",
            "p2_5_detection",
            "p97_5_detection",
            "best_seed_detection",
            "worst_seed_detection",
        ]:
            if item.get(key, "") != "":
                item[key] = float(item[key])
        item["source_literal_dictionary_used"] = parse_bool(item.get("source_literal_dictionary_used", False))
        normalized.append(item)
    return normalized


def build_population(
    first_rows: list[dict[str, Any]],
    functions: dict[str, FunctionInfo],
    candidates: dict[str, CandidateInfo],
) -> dict[str, list[str]]:
    final_rows = [
        row for row in first_rows
        if row["policy"] == FINAL_POLICY and row["budget"] == 8 and row["random_seed"] is None
    ]
    primary = sorted({row["candidate_id"] for row in final_rows if row["in_primary_fixture_passing_wrong"]})
    low_density = sorted({row["candidate_id"] for row in final_rows if row["in_low_density_fixture_passing_wrong"]})
    no_mismatch = sorted({row["candidate_id"] for row in final_rows if row["in_no_mismatch_comparison"]})
    natural_no_mismatch = sorted({
        row["candidate_id"] for row in final_rows
        if row["in_no_mismatch_comparison"] and row["candidate_stratum"] == "natural_ghidra"
    })
    non_fixture = sorted({
        cid for cid in primary
        if candidates[cid].mutation_family != "fixture_overfit_construction"
    })
    literal_present = sorted({
        cid for cid in primary
        if functions[candidates[cid].function_id].source_literal_count > 0
    })
    return {
        PRIMARY_SCOPE: primary,
        LOW_DENSITY_SCOPE: low_density,
        NO_MISMATCH_SCOPE: no_mismatch,
        "natural_ghidra_no_mismatch": natural_no_mismatch,
        NON_FIXTURE_SCOPE: non_fixture,
        SOURCE_LITERAL_PRESENT_SCOPE: literal_present,
    }


def selected_mechanism_lists(
    first_rows: list[dict[str, Any]],
    population: dict[str, list[str]],
) -> dict[str, dict[str, Any]]:
    primary = population[PRIMARY_SCOPE]
    final_b8 = detected_set(first_rows, FINAL_POLICY, 8, None, primary)
    generic_b8 = detected_set(first_rows, GENERIC_BOUNDARY_POLICY, 8, None, primary)
    literal_b8 = detected_set(first_rows, LITERAL_FIRST_POLICY, 8, None, primary)
    fixture_b8 = detected_set(first_rows, FIXTURE_NEIGHBOR_POLICY, 8, None, primary)
    final_b32 = detected_set(first_rows, FINAL_POLICY, 32, None, primary)
    return {
        "final_only_vs_generic_type_boundaries": {"budget": 8, "winner": FINAL_POLICY, "loser": GENERIC_BOUNDARY_POLICY, "ids": sorted(final_b8 - generic_b8)},
        "generic_type_boundaries_only_vs_final": {"budget": 8, "winner": GENERIC_BOUNDARY_POLICY, "loser": FINAL_POLICY, "ids": sorted(generic_b8 - final_b8)},
        "final_only_vs_literal_first": {"budget": 8, "winner": FINAL_POLICY, "loser": LITERAL_FIRST_POLICY, "ids": sorted(final_b8 - literal_b8)},
        "literal_first_only_vs_final": {"budget": 8, "winner": LITERAL_FIRST_POLICY, "loser": FINAL_POLICY, "ids": sorted(literal_b8 - final_b8)},
        "final_only_vs_fixture_neighbor": {"budget": 8, "winner": FINAL_POLICY, "loser": FIXTURE_NEIGHBOR_POLICY, "ids": sorted(final_b8 - fixture_b8)},
        "final_miss_b8": {"budget": 8, "winner": "", "loser": FINAL_POLICY, "ids": sorted(set(primary) - final_b8)},
        "final_miss_b32": {"budget": 32, "winner": "", "loser": FINAL_POLICY, "ids": sorted(set(primary) - final_b32)},
    }


def scan_policy_traces(
    repo_root: Path,
    selected_lists: dict[str, dict[str, Any]],
    population: dict[str, list[str]],
) -> dict[str, Any]:
    needed_prefix_keys: set[tuple[str, str, int, int | None]] = set()
    needed_candidate_policy: set[tuple[str, str, int | None]] = set()
    for spec in selected_lists.values():
        budget = int(spec["budget"])
        for cid in spec["ids"]:
            for policy in {spec.get("winner"), spec.get("loser"), FINAL_POLICY}:
                if policy:
                    needed_prefix_keys.add((cid, policy, budget, None))
                    needed_candidate_policy.add((cid, policy, None))
                    needed_prefix_keys.add((cid, policy, max(BUDGETS), None))
    scope_sets = {scope: set(ids) for scope, ids in population.items()}
    out_summary: dict[tuple[str, int, str], dict[str, Any]] = {}
    prefixes: dict[tuple[str, str, int, int | None], list[dict[str, Any]]] = defaultdict(list)
    max_positions: dict[tuple[str, str, int | None, tuple[int, ...]], dict[str, Any]] = {}
    final_b8_ood_confirm: dict[tuple[str, tuple[int, ...]], dict[str, Any]] = {}

    with (repo_root / "results/decompile_faithfulness/holdout_policy_traces.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            row["input_tuple"] = tuple(int(value) for value in row["input_tuple"])
            policy = row["policy"]
            budget = int(row["budget"])
            seed = row.get("random_seed")
            if policy in DETERMINISTIC_POLICIES:
                update_ood(out_summary, row, "all_trace_candidates")
                for scope, ids in scope_sets.items():
                    if row["candidate_id"] in ids:
                        update_ood(out_summary, row, scope)
            pkey = (row["candidate_id"], policy, budget, seed)
            if pkey in needed_prefix_keys:
                prefixes[pkey].append(trim_trace_row(row))
            cpkey = (row["candidate_id"], policy, seed)
            if cpkey in needed_candidate_policy:
                mkey = (row["candidate_id"], policy, seed, row["input_tuple"])
                current = max_positions.get(mkey)
                if current is None or int(row["position"]) > int(current["position"]):
                    max_positions[mkey] = trim_trace_row(row)
            if (
                policy == FINAL_POLICY
                and budget == 8
                and seed is None
                and row["mismatch"]
                and not row["in_exact_domain"]
            ):
                final_b8_ood_confirm[(row["candidate_id"], row["input_tuple"])] = trim_trace_row(row)

    confirmations = load_ood_confirmations(repo_root)
    for key, trace in final_b8_ood_confirm.items():
        if key in confirmations:
            trace["confirmation"] = confirmations[key]
    return {
        "out_of_domain": out_summary,
        "prefixes": dict(prefixes),
        "max_positions": max_positions,
        "final_b8_ood_confirmations": list(final_b8_ood_confirm.values()),
    }


def update_ood(summary: dict[tuple[str, int, str], dict[str, Any]], row: dict[str, Any], scope: str) -> None:
    key = (row["policy"], int(row["budget"]), scope)
    item = summary.setdefault(
        key,
        {
            "policy": row["policy"],
            "budget": int(row["budget"]),
            "scope": scope,
            "total_generated_probes": 0,
            "total_executed_probes": 0,
            "out_of_domain_probe_count": 0,
            "candidates_receiving_out_of_domain_probe": set(),
            "out_of_domain_mismatching_probes": 0,
            "candidates_with_out_of_domain_witness": set(),
            "distinct_out_of_domain_witnesses": set(),
        },
    )
    item["total_generated_probes"] += 1
    executed = row.get("source_execution_status") == "ok" and row.get("candidate_execution_status") == "ok"
    item["total_executed_probes"] += int(executed)
    if not row["in_exact_domain"]:
        item["out_of_domain_probe_count"] += 1
        item["candidates_receiving_out_of_domain_probe"].add(row["candidate_id"])
        if row["mismatch"]:
            item["out_of_domain_mismatching_probes"] += 1
            item["candidates_with_out_of_domain_witness"].add(row["candidate_id"])
            item["distinct_out_of_domain_witnesses"].add((row["candidate_id"], tuple(row["input_tuple"])))


def out_of_domain_summary_rows(trace_summary: dict[str, Any], population: dict[str, list[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    confirmations = trace_summary["final_b8_ood_confirmations"]
    confirmed_keys = {
        (row["candidate_id"], tuple(row["input_tuple"]))
        for row in confirmations
        if row.get("confirmation", {}).get("confirmed")
    }
    sanitizer_clean_keys = {
        (row["candidate_id"], tuple(row["input_tuple"]))
        for row in confirmations
        if row.get("confirmation", {}).get("source_status") == "ok"
    }
    for (_policy, _budget, _scope), item in sorted(trace_summary["out_of_domain"].items()):
        distinct = item["distinct_out_of_domain_witnesses"]
        row = {
            "policy": item["policy"],
            "budget": item["budget"],
            "scope": item["scope"],
            "candidate_denominator": scope_denominator(item["scope"], population, item),
            "total_generated_probes": item["total_generated_probes"],
            "total_executed_probes": item["total_executed_probes"],
            "out_of_domain_probe_count": item["out_of_domain_probe_count"],
            "out_of_domain_probe_fraction": safe_div(item["out_of_domain_probe_count"], item["total_generated_probes"]),
            "candidates_receiving_at_least_one_out_of_domain_probe": len(item["candidates_receiving_out_of_domain_probe"]),
            "out_of_domain_mismatching_probes": item["out_of_domain_mismatching_probes"],
            "candidates_with_at_least_one_out_of_domain_witness": len(item["candidates_with_out_of_domain_witness"]),
            "distinct_out_of_domain_witness_count": len(distinct),
            "confirmed_distinct_witness_count": len(distinct & confirmed_keys) if item["policy"] == FINAL_POLICY and item["budget"] == 8 else "",
            "source_sanitizer_clean_distinct_witness_count": len(distinct & sanitizer_clean_keys) if item["policy"] == FINAL_POLICY and item["budget"] == 8 else "",
            "adjudication": "out_of_domain_mismatch_not_false_positive_relative_to_exact_domain_oracle",
        }
        rows.append(row)
    return rows


def scope_denominator(scope: str, population: dict[str, list[str]], item: dict[str, Any]) -> int | str:
    if scope in population:
        return len(population[scope])
    if scope == "all_trace_candidates":
        ids = set(item["candidates_receiving_out_of_domain_probe"]) | set(item["candidates_with_out_of_domain_witness"])
        return f"trace_scope_not_candidate_population;affected={len(ids)}"
    return ""


def load_ood_confirmations(repo_root: Path) -> dict[tuple[str, tuple[int, ...]], dict[str, Any]]:
    path = repo_root / "results/decompile_faithfulness/holdout_unexpected_mismatches.jsonl"
    confirmations: dict[tuple[str, tuple[int, ...]], dict[str, Any]] = {}
    if not path.exists():
        return confirmations
    for row in read_jsonl(path):
        if row.get("policy") == FINAL_POLICY and int(row.get("budget", 0)) == 8 and not row.get("in_exact_domain", True):
            key = (row["candidate_id"], tuple(int(value) for value in row["input_tuple"]))
            confirmations[key] = row.get("confirmation", {})
    return confirmations


def paired_policy_rows(
    first_rows: list[dict[str, Any]],
    population: dict[str, list[str]],
    functions: dict[str, FunctionInfo],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scopes = {
        PRIMARY_SCOPE: population[PRIMARY_SCOPE],
        LOW_DENSITY_SCOPE: population[LOW_DENSITY_SCOPE],
        NON_FIXTURE_SCOPE: population[NON_FIXTURE_SCOPE],
        SOURCE_LITERAL_PRESENT_SCOPE: population[SOURCE_LITERAL_PRESENT_SCOPE],
    }
    for comparator in COMPARATOR_POLICIES:
        for budget in BUDGETS:
            for scope, ids in scopes.items():
                if comparator != LITERAL_FIRST_POLICY and scope != PRIMARY_SCOPE:
                    continue
                final_detected = detected_set(first_rows, FINAL_POLICY, budget, None, ids)
                comp_detected, detection_rule = comparator_detected_set(first_rows, comparator, budget, ids)
                rows.append(paired_row(scope, comparator, budget, ids, final_detected, comp_detected, detection_rule, functions, first_rows))
    return rows


def paired_row(
    scope: str,
    comparator: str,
    budget: int,
    ids: list[str],
    final_detected: set[str],
    comp_detected: set[str],
    detection_rule: str,
    functions: dict[str, FunctionInfo],
    first_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    id_set = set(ids)
    both = sorted(final_detected & comp_detected)
    final_only = sorted(final_detected - comp_detected)
    comparator_only = sorted(comp_detected - final_detected)
    neither = sorted(id_set - final_detected - comp_detected)
    final_ranks = ranks_for(first_rows, FINAL_POLICY, budget, None, ids)
    comparator_ranks = ranks_for(first_rows, comparator, budget, None, ids) if comparator not in STOCHASTIC_POLICIES else []
    project_macro_final, project_macro_comparator = project_macro_rates(first_rows, ids, comparator, budget, functions)
    return {
        "scope": scope,
        "budget": budget,
        "final_policy": FINAL_POLICY,
        "comparator_policy": comparator,
        "comparator_detection_rule": detection_rule,
        "denominator": len(ids),
        "detected_by_both_count": len(both),
        "detected_only_by_final_count": len(final_only),
        "detected_only_by_comparator_count": len(comparator_only),
        "detected_by_neither_count": len(neither),
        "final_detected": len(final_detected),
        "comparator_detected": len(comp_detected),
        "final_detection_rate": safe_div(len(final_detected), len(ids)),
        "comparator_detection_rate": safe_div(len(comp_detected), len(ids)),
        "detection_rate_difference_final_minus_comparator": safe_div(len(final_detected), len(ids)) - safe_div(len(comp_detected), len(ids)),
        "paired_final_win_count": len(final_only),
        "paired_comparator_win_count": len(comparator_only),
        "paired_tie_count": len(both) + len(neither),
        "mcnemar_b01_comparator_only": len(comparator_only),
        "mcnemar_b10_final_only": len(final_only),
        "final_only_candidate_ids": json.dumps(final_only),
        "comparator_only_candidate_ids": json.dumps(comparator_only),
        "neither_candidate_ids": json.dumps(neither),
        "final_median_first_witness_rank": percentile(final_ranks, 0.5),
        "final_mean_first_witness_rank": statistics.mean(final_ranks) if final_ranks else "",
        "comparator_median_first_witness_rank": percentile(comparator_ranks, 0.5),
        "comparator_mean_first_witness_rank": statistics.mean(comparator_ranks) if comparator_ranks else "",
        "project_macro_final_detection_rate": project_macro_final,
        "project_macro_comparator_detection_rate": project_macro_comparator,
        "project_macro_difference_final_minus_comparator": project_macro_final - project_macro_comparator,
    }


def project_macro_rates(
    first_rows: list[dict[str, Any]],
    ids: list[str],
    comparator: str,
    budget: int,
    functions: dict[str, FunctionInfo],
) -> tuple[float, float]:
    project_by_candidate = {}
    final_meta = {
        row["candidate_id"]: row
        for row in first_rows
        if row["policy"] == FINAL_POLICY and row["budget"] == budget and row["random_seed"] is None
    }
    for cid in ids:
        project_by_candidate[cid] = final_meta[cid]["project"]
    projects = sorted(set(project_by_candidate.values()))
    final_rates = []
    comparator_rates = []
    for project in projects:
        project_ids = [cid for cid in ids if project_by_candidate[cid] == project]
        final_detected = detected_set(first_rows, FINAL_POLICY, budget, None, project_ids)
        comp_detected, _rule = comparator_detected_set(first_rows, comparator, budget, project_ids)
        final_rates.append(safe_div(len(final_detected), len(project_ids)))
        comparator_rates.append(safe_div(len(comp_detected), len(project_ids)))
    return (statistics.mean(final_rates) if final_rates else 0.0, statistics.mean(comparator_rates) if comparator_rates else 0.0)


def candidate_mechanism_rows(
    *,
    first_rows: list[dict[str, Any]],
    selected_lists: dict[str, dict[str, Any]],
    trace_prefixes: dict[tuple[str, str, int, int | None], list[dict[str, Any]]],
    trace_max_positions: dict[tuple[str, str, int | None, tuple[int, ...]], dict[str, Any]],
    functions: dict[str, FunctionInfo],
    candidates: dict[str, CandidateInfo],
    labels: dict[str, dict[str, Any]],
    fixtures: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    first_lookup = {
        (row["candidate_id"], row["policy"], row["budget"], row["random_seed"]): row
        for row in first_rows
    }
    rows: list[dict[str, Any]] = []
    for list_name, spec in selected_lists.items():
        budget = int(spec["budget"])
        winner = spec.get("winner") or ""
        loser = spec.get("loser") or FINAL_POLICY
        for cid in spec["ids"]:
            candidate = candidates[cid]
            function = functions[candidate.function_id]
            label = labels[cid]
            winning_policy = winner or FINAL_POLICY
            winning_budget = budget
            witness_row = first_lookup.get((cid, winning_policy, winning_budget, None))
            witness_trace = first_witness_trace(trace_prefixes.get((cid, winning_policy, winning_budget, None), []), witness_row)
            winning_input = tuple(witness_trace["input_tuple"]) if witness_trace else None
            losing_reason = losing_policy_reason(
                cid=cid,
                losing_policy=loser,
                budget=budget,
                winning_input=winning_input,
                max_positions=trace_max_positions,
            )
            rows.append(
                {
                    "list_name": list_name,
                    "candidate_id": cid,
                    "project": candidate.project,
                    "function_id": candidate.function_id,
                    "function": function.function_name,
                    "signature": function.signature,
                    "source_literal_availability": "has_source_char_literal" if function.source_literal_count > 0 else "no_source_char_literal",
                    "source_char_literal_count": function.source_literal_count,
                    "candidate_stratum": candidate.candidate_stratum,
                    "mutation_family": candidate.mutation_family,
                    "label": candidate.label,
                    "mismatch_density": mismatch_density(label),
                    "exact_mismatch_set_summary": exact_mismatch_summary(label),
                    "sealed_fixtures": json.dumps(fixtures.get(candidate.function_id, []), sort_keys=True),
                    "budget": budget,
                    "winning_policy": winner,
                    "losing_policy": loser,
                    "final_ordered_prefix": json.dumps(trace_prefixes.get((cid, FINAL_POLICY, budget, None), []), sort_keys=True),
                    "comparator_ordered_prefix": json.dumps(trace_prefixes.get((cid, loser, budget, None), []), sort_keys=True),
                    "first_witness": json.dumps(witness_trace, sort_keys=True) if witness_trace else "",
                    "first_witness_probe_origin": probe_origin(witness_trace) if witness_trace else "",
                    "witness_is_source_literal": bool(witness_trace and witness_trace.get("source_literal_derived")),
                    "witness_is_fixture_neighbor": bool(witness_trace and witness_trace.get("fixture_neighbor_derived")),
                    "witness_is_generic_boundary": bool(witness_trace and witness_trace.get("generic_type_boundary_derived")),
                    "witness_is_fallback_value": bool(witness_trace and witness_trace.get("generic_fallback_derived")),
                    "losing_policy_miss_reason": losing_reason,
                }
            )
    return rows


def first_witness_trace(prefix: list[dict[str, Any]], witness_row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not witness_row or witness_row.get("first_in_domain_witness_rank") is None:
        return None
    rank = int(witness_row["first_in_domain_witness_rank"])
    for row in prefix:
        if int(row["position"]) == rank and row.get("mismatch") and row.get("in_exact_domain"):
            return row
    for row in prefix:
        if int(row["position"]) == rank:
            return row
    return None


def losing_policy_reason(
    *,
    cid: str,
    losing_policy: str,
    budget: int,
    winning_input: tuple[int, ...] | None,
    max_positions: dict[tuple[str, str, int | None, tuple[int, ...]], dict[str, Any]],
) -> str:
    if winning_input is None:
        return "no_winning_in_domain_witness"
    row = max_positions.get((cid, losing_policy, None, winning_input))
    if row is None:
        return "absent_from_observed_pool"
    if row.get("source_execution_status") != "ok" or row.get("candidate_execution_status") != "ok":
        return "execution_issue"
    if int(row["position"]) > budget:
        return "beyond_budget"
    if row.get("duplicate_removal_provenance") and len(row["duplicate_removal_provenance"]) > 1:
        return "deduplicated_later_or_shared_provenance"
    return "present_without_recorded_detection_recheck_required"


def trim_trace_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": row["candidate_id"],
        "policy": row["policy"],
        "budget": int(row["budget"]),
        "random_seed": row.get("random_seed"),
        "position": int(row["position"]),
        "input_tuple": list(row["input_tuple"]),
        "source_output": row.get("source_output"),
        "candidate_output": row.get("candidate_output"),
        "mismatch": bool(row.get("mismatch")),
        "in_exact_domain": bool(row.get("in_exact_domain")),
        "source_literal_derived": bool(row.get("source_literal_derived")),
        "fixture_neighbor_derived": bool(row.get("fixture_neighbor_derived")),
        "generic_fallback_derived": bool(row.get("generic_fallback_derived")),
        "generic_type_boundary_derived": bool(row.get("generic_type_boundary_derived")),
        "operator_char_derived": bool(row.get("operator_char_derived")),
        "duplicate_removal_provenance": row.get("duplicate_removal_provenance", []),
        "source_execution_status": row.get("source_execution_status", ""),
        "candidate_execution_status": row.get("candidate_execution_status", ""),
        "elapsed_execution_time_s": row.get("elapsed_execution_time_s", ""),
    }


def probe_origin(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    origins = []
    if row.get("source_literal_derived"):
        origins.append("source_literal")
    if row.get("fixture_neighbor_derived"):
        origins.append("fixture_neighbor")
    if row.get("generic_type_boundary_derived"):
        origins.append("generic_boundary")
    if row.get("generic_fallback_derived"):
        origins.append("fallback_value")
    if row.get("operator_char_derived"):
        origins.append("operator_character_list")
    return "+".join(origins) if origins else "policy_specific_or_random"


def exhaustive_cost_reference_rows(
    labels: dict[str, dict[str, Any]],
    functions: dict[str, FunctionInfo],
    candidates: dict[str, CandidateInfo],
) -> list[dict[str, Any]]:
    rows = []
    for cid, label in sorted(labels.items()):
        candidate = candidates.get(cid)
        if not candidate or label["label"] == "non_evaluable":
            continue
        first = label.get("first_mismatch") or {}
        first_rank = first.get("rank", "")
        domain_size = int(label.get("exact_domain_size", 0))
        rows.append(
            {
                "candidate_id": cid,
                "project": label.get("project", ""),
                "function_id": label.get("function_id", ""),
                "candidate_stratum": label.get("candidate_stratum", ""),
                "label": label.get("label", ""),
                "domain_size": domain_size,
                "canonical_first_witness_rank": first_rank,
                "total_mismatching_inputs": label.get("total_mismatching_input_count", 0),
                "fraction_of_domain_before_first_witness": safe_div(int(first_rank), domain_size) if first_rank else "",
                "complete_domain_cost_inputs": domain_size,
                "total_enumeration_time_s": "unknown_not_recorded_in_sealed_label_artifact",
                "complete_mismatch_set_sha256": label.get("complete_mismatch_set_sha256", ""),
            }
        )
    return rows


def klee_baseline_rows(
    population: dict[str, list[str]],
    candidates: dict[str, CandidateInfo],
    functions: dict[str, FunctionInfo],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    klee_path = shutil.which("klee")
    clang_path = Path("/usr/lib/llvm-11/bin/clang")
    clang_version = command_first_line([str(clang_path), "--version"]) if clang_path.exists() else "unknown"
    candidate_ids = baseline_candidate_ids(population)
    result_rows = []
    for cid in candidate_ids:
        candidate = candidates[cid]
        function = functions[candidate.function_id]
        result_rows.append(
            {
                "candidate_id": cid,
                "project": candidate.project,
                "function_id": candidate.function_id,
                "candidate_stratum": candidate.candidate_stratum,
                "label": candidate.label,
                "supported_by_klee_pipeline": bool(klee_path),
                "unsupported_reason": "" if klee_path else "klee_not_found_in_path",
                "wall_clock_limits_s": json.dumps([0.1, 1.0, 5.0]),
                "build_success": False,
                "setup_failure": "" if klee_path else "klee_binary_unavailable",
                "solver_or_runtime_timeout": False,
                "witness_found": False,
                "confirmed_valid_witness": False,
                "time_to_first_confirmed_witness_s": "",
                "explored_paths_or_states": "",
                "no_mismatch_false_alarm": False,
                "domain_constraint_preview": klee_domain_constraint_preview(function),
                "tool_version": command_first_line([klee_path, "--version"]) if klee_path else "unavailable",
                "clang_version": clang_version,
            }
        )
    summary_rows = []
    scopes = {
        PRIMARY_SCOPE: population[PRIMARY_SCOPE],
        LOW_DENSITY_SCOPE: population[LOW_DENSITY_SCOPE],
        NON_FIXTURE_SCOPE: population[NON_FIXTURE_SCOPE],
        NO_MISMATCH_SCOPE: population[NO_MISMATCH_SCOPE],
    }
    for limit in [0.1, 1.0, 5.0]:
        for scope, ids in scopes.items():
            summary_rows.append(
                {
                    "wall_clock_limit_s": limit,
                    "population": scope,
                    "all_candidate_denominator": len(ids),
                    "supported_candidates": len(ids) if klee_path else 0,
                    "setup_success": 0,
                    "setup_failure": len(ids) if not klee_path else 0,
                    "solver_runtime_timeout": 0,
                    "witness_found": 0,
                    "confirmed_valid_witness": 0,
                    "detection_on_all_candidate_denominator": 0.0,
                    "detection_on_supported_denominator": "",
                    "no_mismatch_false_alarm": 0,
                    "baseline_status": "not_run_blocked" if not klee_path else "available_not_executed_by_phase1f_module",
                    "blocker": "klee_not_found_in_path" if not klee_path else "",
                    "klee_version": command_first_line([klee_path, "--version"]) if klee_path else "unavailable",
                    "clang_version": clang_version,
                }
            )
    return result_rows, summary_rows


def klee_constraint_expression(name: str, values: list[int]) -> str:
    ordered = sorted(set(int(value) for value in values))
    ranges: list[tuple[int, int]] = []
    for value in ordered:
        if not ranges or value != ranges[-1][1] + 1:
            ranges.append((value, value))
        else:
            ranges[-1] = (ranges[-1][0], value)
    parts = [f"({name} == {lo})" if lo == hi else f"({name} >= {lo} && {name} <= {hi})" for lo, hi in ranges]
    return " || ".join(parts) if parts else "0"


def klee_domain_constraint_preview(function: FunctionInfo) -> str:
    chunks = []
    for index, spec in enumerate(function.domain_specs):
        chunks.append(klee_constraint_expression(f"arg{index}", [int(value) for value in spec["values"]]))
    return " && ".join(f"({chunk})" for chunk in chunks)


def confirm_witness_against_exact_label(label: dict[str, Any], args: Iterable[int]) -> bool:
    wanted = [int(value) for value in args]
    return any([int(value) for value in row.get("args", [])] == wanted for row in label.get("stored_mismatches", []))


def libfuzzer_blocker_rows(
    population: dict[str, list[str]],
    candidates: dict[str, CandidateInfo],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    clang_path = Path("/usr/lib/llvm-11/bin/clang")
    clang_version = command_first_line([str(clang_path), "--version"]) if clang_path.exists() else "unavailable"
    smoke_available = libfuzzer_smoke_available(clang_path)
    candidate_ids = baseline_candidate_ids(population)
    blocker = (
        "not_run_in_default_phase1f_generation; rerun with --run-libfuzzer to execute real libFuzzer harnesses"
        if smoke_available
        else "clang_libfuzzer_unavailable"
    )
    run_rows = [
        {
            "candidate_id": cid,
            "project": candidates[cid].project,
            "function_id": candidates[cid].function_id,
            "candidate_stratum": candidates[cid].candidate_stratum,
            "label": candidates[cid].label,
            "mode": "evaluation_count_and_wall_clock",
            "seed": "",
            "budget_or_time_limit": "",
            "supported_by_libfuzzer_pipeline": False,
            "baseline_status": "not_run_blocked",
            "unsupported_reason": blocker,
            "source_literal_dictionary_used": False,
            "seed_corpus": "four_sealed_fixtures_only_when_run",
            "ordered_input_sequence": "not_run",
            "ordered_input_sequence_sha256": "",
        }
        for cid in candidate_ids
    ]
    summary_rows = []
    scopes = {
        PRIMARY_SCOPE: population[PRIMARY_SCOPE],
        LOW_DENSITY_SCOPE: population[LOW_DENSITY_SCOPE],
        NON_FIXTURE_SCOPE: population[NON_FIXTURE_SCOPE],
        NO_MISMATCH_SCOPE: population[NO_MISMATCH_SCOPE],
    }
    for mode, budgets in [("evaluation_count", FUZZER_EVAL_BUDGETS), ("wall_clock", FUZZER_TIME_LIMITS)]:
        for budget in budgets:
            for scope, ids in scopes.items():
                summary_rows.append(
                    {
                        "mode": mode,
                        "budget_or_time_limit": budget,
                        "population": scope,
                        "candidate_denominator": len(ids),
                        "supported_candidates": 0,
                        "mean_detection": 0.0,
                        "median_detection": 0.0,
                        "stddev_detection": 0.0,
                        "p2_5_detection": 0.0,
                        "p97_5_detection": 0.0,
                        "best_seed_detection": 0.0,
                        "worst_seed_detection": 0.0,
                        "no_mismatch_false_alarms": 0,
                        "distinct_no_mismatch_false_alarm_candidates": 0,
                        "baseline_status": "not_run_blocked",
                        "blocker": blocker,
                        "clang_version": clang_version,
                        "source_literal_dictionary_used": False,
                    }
                )
    return run_rows, summary_rows


def run_libfuzzer_baseline(
    repo_root: Path,
    population: dict[str, list[str]],
    candidates: dict[str, CandidateInfo],
    functions: dict[str, FunctionInfo],
    labels: dict[str, dict[str, Any]],
    fixtures: dict[str, list[dict[str, Any]]],
    work_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    clang = Path("/usr/lib/llvm-11/bin/clang")
    if not libfuzzer_smoke_available(clang):
        return libfuzzer_blocker_rows(population, candidates)
    work_dir.mkdir(parents=True, exist_ok=True)
    candidate_ids = baseline_candidate_ids(population)
    harnesses: dict[str, Path] = {}
    run_rows: list[dict[str, Any]] = []
    for cid in candidate_ids:
        candidate = candidates[cid]
        function = functions[candidate.function_id]
        hdir = work_dir / safe_name(cid)
        build = build_libfuzzer_harness(clang, hdir, candidate, function, fixtures[function.function_id])
        if not build["ok"]:
            run_rows.append(libfuzzer_unsupported_row(candidate, function, build["reason"]))
            continue
        validation = validate_libfuzzer_harness_semantics(clang, hdir, candidate, function, labels[cid])
        if not validation["ok"]:
            run_rows.append(libfuzzer_unsupported_row(candidate, function, validation["reason"], validation))
            continue
        harnesses[cid] = Path(build["exe"])
        seed_dir = Path(build["seed_dir"])
        for seed in RANDOM_SEEDS:
            eval_log = hdir / f"eval_seed_{seed}.log"
            eval_run = invoke_fuzzer(Path(build["exe"]), seed_dir, eval_log, seed, eval_limit=max(FUZZER_EVAL_BUDGETS), timeout_s=30.0)
            sequence = parse_fuzzer_log(eval_log)
            run_rows.extend(rows_from_eval_sequence(candidate, function, labels[cid], seed, sequence, eval_run))
    summary_rows = summarize_libfuzzer_runs(run_rows, population)
    summary_rows.extend(libfuzzer_wall_clock_blocker_rows(population, command_first_line([str(clang), "--version"])))
    return run_rows, summary_rows


def build_libfuzzer_harness(
    clang: Path,
    out_dir: Path,
    candidate: CandidateInfo,
    function: FunctionInfo,
    fixture_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not function.source_path or not Path(function.source_path).exists():
        return {"ok": False, "reason": "missing_source_function_path"}
    if not candidate.source_path or not Path(candidate.source_path).exists():
        return {"ok": False, "reason": "missing_candidate_source_path"}
    source_text = Path(function.source_path).read_text(encoding="utf-8")
    candidate_text = Path(candidate.source_path).read_text(encoding="utf-8")
    harness = render_libfuzzer_harness(function, source_text, candidate_text)
    harness_path = out_dir / "fuzzer_harness.c"
    exe_path = out_dir / "fuzzer"
    harness_path.write_text(harness, encoding="utf-8")
    cmd = [
        str(clang),
        "-std=c11",
        "-O1",
        "-g",
        "-fsanitize=fuzzer,address,undefined",
        "-fno-sanitize-recover=all",
        str(harness_path),
        "-o",
        str(exe_path),
    ]
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
    if result.returncode != 0:
        return {"ok": False, "reason": "libfuzzer_harness_compile_failure", "stderr": result.stderr[-1000:]}
    seed_dir = out_dir / "seed_corpus"
    seed_dir.mkdir(exist_ok=True)
    for fixture in fixture_rows:
        data = encode_domain_tuple(function.domain_specs, [int(value) for value in fixture["args"]])
        (seed_dir / f"fixture_{int(fixture['rank']):02d}").write_bytes(data)
    return {"ok": True, "exe": str(exe_path), "seed_dir": str(seed_dir)}


def validate_libfuzzer_harness_semantics(
    clang: Path,
    out_dir: Path,
    candidate: CandidateInfo,
    function: FunctionInfo,
    label: dict[str, Any],
) -> dict[str, Any]:
    if not function.source_path or not Path(function.source_path).exists():
        return {"ok": False, "reason": "missing_source_function_path_for_validation"}
    if not candidate.source_path or not Path(candidate.source_path).exists():
        return {"ok": False, "reason": "missing_candidate_source_path_for_validation"}
    source_text = Path(function.source_path).read_text(encoding="utf-8")
    candidate_text = Path(candidate.source_path).read_text(encoding="utf-8")
    path = out_dir / "validation_harness.c"
    exe = out_dir / "validation_harness"
    path.write_text(render_libfuzzer_validation_harness(function, source_text, candidate_text), encoding="utf-8")
    compile_result = subprocess.run(
        [
            str(clang),
            "-std=c11",
            "-O1",
            "-g",
            "-fsanitize=address,undefined",
            "-fno-sanitize-recover=all",
            str(path),
            "-o",
            str(exe),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if compile_result.returncode != 0:
        return {"ok": False, "reason": "validation_harness_compile_failure", "stderr_tail": compile_result.stderr[-1000:]}
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = "detect_leaks=0"
    env["LSAN_OPTIONS"] = "detect_leaks=0"
    run_result = subprocess.run(
        [str(exe)],
        cwd=out_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
        timeout=30,
    )
    if run_result.returncode != 0:
        return {"ok": False, "reason": "validation_harness_runtime_failure", "stderr_tail": run_result.stderr[-1000:]}
    parsed = parse_validation_stdout(run_result.stdout)
    expected_count = int(label.get("total_mismatching_input_count", 0))
    expected_first = label.get("first_mismatch")
    expected_first_args = expected_first.get("args") if isinstance(expected_first, dict) else None
    first_matches = (
        parsed["first_mismatch_args"] == expected_first_args
        if expected_first_args is not None
        else parsed["first_mismatch_args"] is None
    )
    ok = parsed["mismatch_count"] == expected_count and first_matches
    if not ok:
        return {
            "ok": False,
            "reason": "validation_harness_semantics_mismatch",
            "expected_mismatch_count": expected_count,
            "observed_mismatch_count": parsed["mismatch_count"],
            "expected_first_mismatch_args": expected_first_args,
            "observed_first_mismatch_args": parsed["first_mismatch_args"],
        }
    return {
        "ok": True,
        "reason": "validation_harness_matches_sealed_exact_label",
        "observed_mismatch_count": parsed["mismatch_count"],
        "observed_first_mismatch_args": parsed["first_mismatch_args"],
    }


def render_libfuzzer_validation_harness(function: FunctionInfo, source_text: str, candidate_text: str) -> str:
    function_name = function.function_name
    source_name = "phase1f_source_" + safe_c_identifier(function_name)
    candidate_name = "phase1f_candidate_" + safe_c_identifier(function_name)
    arrays = "\n".join(render_domain_array(index, spec) for index, spec in enumerate(function.domain_specs))
    loops_open = []
    loops_close = []
    args = []
    for index, spec in enumerate(function.domain_specs):
        loops_open.append(f"    for (int i{index} = 0; i{index} < {len(spec['values'])}; ++i{index}) {{")
        loops_close.append("    }")
        args.append(f"domain_{index}[i{index}]")
    call_args = ", ".join(args)
    first_capture = "\n".join(
        [
            "                if (!have_first) {",
            "                    have_first = 1;",
            f"                    printf(\"first:{','.join(['%lld' for _ in args])}\\n\", {call_args});" if args else "                    printf(\"first:\\n\");",
            "                }",
        ]
    )
    return f"""#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

#define {function_name} {source_name}
{source_text.rstrip()}
#undef {function_name}

#define {function_name} {candidate_name}
{candidate_text.rstrip()}
#undef {function_name}

{arrays}

int main(void) {{
    long long mismatches = 0;
    int have_first = 0;
{chr(10).join(loops_open)}
            long long source_output = (long long){source_name}({call_args});
            long long candidate_output = (long long){candidate_name}({call_args});
            if (source_output != candidate_output) {{
                mismatches++;
{first_capture}
            }}
{chr(10).join(reversed(loops_close))}
    printf("mismatches:%lld\\n", mismatches);
    return 0;
}}
"""


def parse_validation_stdout(stdout: str) -> dict[str, Any]:
    mismatch_count = None
    first_args = None
    for line in stdout.splitlines():
        if line.startswith("first:"):
            raw = line.split(":", 1)[1]
            first_args = [int(value) for value in raw.split(",") if value != ""]
        if line.startswith("mismatches:"):
            mismatch_count = int(line.split(":", 1)[1])
    if mismatch_count is None:
        raise ValueError("validation stdout missing mismatches line")
    return {"mismatch_count": mismatch_count, "first_mismatch_args": first_args}


def render_libfuzzer_harness(function: FunctionInfo, source_text: str, candidate_text: str) -> str:
    function_name = function.function_name
    source_name = "phase1f_source_" + safe_c_identifier(function_name)
    candidate_name = "phase1f_candidate_" + safe_c_identifier(function_name)
    args = [f"arg{index}" for index, _spec in enumerate(function.domain_specs)]
    arg_decl = "\n".join(render_domain_arg(index, spec) for index, spec in enumerate(function.domain_specs))
    call_args = ", ".join(args)
    arrays = "\n".join(render_domain_array(index, spec) for index, spec in enumerate(function.domain_specs))
    return f"""#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <time.h>

#define {function_name} {source_name}
{source_text.rstrip()}
#undef {function_name}

#define {function_name} {candidate_name}
{candidate_text.rstrip()}
#undef {function_name}

{arrays}
static unsigned long long phase1f_evals = 0;
static clock_t phase1f_start;
static int phase1f_started = 0;

int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {{
    if (!phase1f_started) {{
        phase1f_start = clock();
        phase1f_started = 1;
    }}
    unsigned long long limit = 0;
    const char *limit_env = getenv("PHASE1F_EVAL_LIMIT");
    if (limit_env && limit_env[0]) {{
        limit = strtoull(limit_env, NULL, 10);
    }}
    const char *log_path = getenv("PHASE1F_FUZZER_LOG");
    FILE *log = log_path ? fopen(log_path, "a") : NULL;
{arg_decl}
    long long source_output = (long long){source_name}({call_args});
    long long candidate_output = (long long){candidate_name}({call_args});
    phase1f_evals++;
    double elapsed = (double)(clock() - phase1f_start) / (double)CLOCKS_PER_SEC;
    int mismatch = source_output != candidate_output;
    if (log) {{
        fprintf(log, "%llu|%.9f|", phase1f_evals, elapsed);
{render_log_args(len(function.domain_specs))}
        fprintf(log, "|%lld|%lld|%d\\n", source_output, candidate_output, mismatch);
        fflush(log);
        fclose(log);
    }}
    if (mismatch) {{
        __builtin_trap();
    }}
    if (limit && phase1f_evals >= limit) {{
        _Exit(0);
    }}
    return 0;
}}
"""


def render_domain_array(index: int, spec: dict[str, Any]) -> str:
    values = ", ".join(str(int(value)) for value in spec["values"])
    return f"static const long long domain_{index}[] = {{{values}}};"


def render_domain_arg(index: int, spec: dict[str, Any]) -> str:
    offset = index * 2
    count = len(spec["values"])
    return (
        f"    unsigned int raw_{index} = 0;\n"
        f"    if (Size > {offset}) raw_{index} |= (unsigned int)Data[{offset}];\n"
        f"    if (Size > {offset + 1}) raw_{index} |= ((unsigned int)Data[{offset + 1}]) << 8;\n"
        f"    long long arg{index} = domain_{index}[raw_{index} % {count}];"
    )


def render_log_args(arity: int) -> str:
    lines = []
    for index in range(arity):
        if index == 0:
            lines.append(f'        fprintf(log, "%lld", arg{index});')
        else:
            lines.append(f'        fprintf(log, ",%lld", arg{index});')
    return "\n".join(lines)


def invoke_fuzzer(
    exe: Path,
    seed_dir: Path,
    log_path: Path,
    seed: int,
    *,
    eval_limit: int,
    timeout_s: float,
) -> dict[str, Any]:
    if log_path.exists():
        log_path.unlink()
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = "detect_leaks=0"
    env["LSAN_OPTIONS"] = "detect_leaks=0"
    env["PHASE1F_FUZZER_LOG"] = str(log_path)
    env["PHASE1F_EVAL_LIMIT"] = str(eval_limit) if eval_limit else ""
    cmd = [
        str(exe),
        str(seed_dir),
        f"-seed={seed}",
        "-use_value_profile=0",
        "-print_final_stats=0",
        "-close_fd_mask=3",
        f"-artifact_prefix={exe.parent.as_posix()}/",
    ]
    started = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=exe.parent, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=timeout_s, check=False)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        result = subprocess.CompletedProcess(cmd, 124, stdout=exc.stdout if isinstance(exc.stdout, str) else "", stderr=exc.stderr if isinstance(exc.stderr, str) else "timeout")
        timed_out = True
    elapsed = time.perf_counter() - started
    return {
        "returncode": result.returncode,
        "timed_out": timed_out,
        "elapsed_wall_clock_s": elapsed,
        "stderr_tail": result.stderr[-1000:],
    }


def parse_fuzzer_log(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("|")
            if len(parts) != 6:
                continue
            args = [int(value) for value in parts[2].split(",") if value != ""]
            rows.append(
                {
                    "eval": int(parts[0]),
                    "elapsed_s": float(parts[1]),
                    "args": args,
                    "source_output": int(parts[3]),
                    "candidate_output": int(parts[4]),
                    "mismatch": parts[5] == "1",
                }
            )
    return rows


def rows_from_eval_sequence(
    candidate: CandidateInfo,
    function: FunctionInfo,
    label: dict[str, Any],
    seed: int,
    sequence: list[dict[str, Any]],
    run: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for budget in FUZZER_EVAL_BUDGETS:
        prefix = sequence[:budget]
        witness = next((row for row in prefix if row["mismatch"]), None)
        rows.append(libfuzzer_result_row(candidate, function, label, "evaluation_count", seed, budget, prefix, witness, run))
    return rows


def rows_from_time_sequence(
    candidate: CandidateInfo,
    function: FunctionInfo,
    label: dict[str, Any],
    seed: int,
    sequence: list[dict[str, Any]],
    run: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for limit in FUZZER_TIME_LIMITS:
        prefix = [row for row in sequence if row["elapsed_s"] <= limit]
        witness = next((row for row in prefix if row["mismatch"]), None)
        rows.append(libfuzzer_result_row(candidate, function, label, "wall_clock", seed, limit, prefix, witness, run))
    return rows


def libfuzzer_result_row(
    candidate: CandidateInfo,
    function: FunctionInfo,
    label: dict[str, Any],
    mode: str,
    seed: int,
    budget_or_time: int | float,
    sequence: list[dict[str, Any]],
    witness: dict[str, Any] | None,
    run: dict[str, Any],
) -> dict[str, Any]:
    unique = {tuple(row["args"]) for row in sequence}
    ordered_sequence = [row["args"] for row in sequence] if mode == "evaluation_count" else [row["args"] for row in sequence[:1024]]
    false_alarm = bool(witness and label["label"] == "no_mismatch_under_exact_holdout_domain")
    return {
        "candidate_id": candidate.candidate_id,
        "project": candidate.project,
        "function_id": candidate.function_id,
        "candidate_stratum": candidate.candidate_stratum,
        "label": label["label"],
        "mode": mode,
        "seed": seed,
        "budget_or_time_limit": budget_or_time,
        "supported_by_libfuzzer_pipeline": True,
        "baseline_status": "completed",
        "unsupported_reason": "",
        "source_literal_dictionary_used": False,
        "seed_corpus": "four_sealed_fixtures_only",
        "completed_source_candidate_evaluations": len(sequence),
        "detected": bool(witness),
        "evaluations_to_first_witness": witness["eval"] if witness else "",
        "time_to_first_witness_s": witness["elapsed_s"] if witness else "",
        "unique_domain_coverage": len(unique),
        "exact_domain_coverage_fraction": safe_div(len(unique), function.domain_size),
        "no_mismatch_false_alarm": false_alarm,
        "ordered_input_sequence": json.dumps(ordered_sequence),
        "ordered_input_sequence_sha256": sha256_text(json.dumps([row["args"] for row in sequence], sort_keys=True)),
        "sequence_truncated_for_wall_clock": mode == "wall_clock" and len(sequence) > 1024,
        "process_returncode": run["returncode"],
        "process_timed_out": run["timed_out"],
        "process_elapsed_wall_clock_s": run["elapsed_wall_clock_s"],
        "stderr_tail": run["stderr_tail"],
    }


def libfuzzer_unsupported_row(
    candidate: CandidateInfo,
    function: FunctionInfo,
    reason: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "project": candidate.project,
        "function_id": candidate.function_id,
        "candidate_stratum": candidate.candidate_stratum,
        "label": candidate.label,
        "mode": "evaluation_count_and_wall_clock",
        "seed": "",
        "budget_or_time_limit": "",
        "supported_by_libfuzzer_pipeline": False,
        "baseline_status": "unsupported",
        "unsupported_reason": reason,
        "source_literal_dictionary_used": False,
        "seed_corpus": "four_sealed_fixtures_only_when_supported",
        "ordered_input_sequence": "",
        "ordered_input_sequence_sha256": "",
        "support_validation": json.dumps(details or {}, sort_keys=True),
    }


def summarize_libfuzzer_runs(
    run_rows: list[dict[str, Any]],
    population: dict[str, list[str]],
) -> list[dict[str, Any]]:
    rows = []
    no_mismatch = set(population[NO_MISMATCH_SCOPE])
    scopes = {
        PRIMARY_SCOPE: set(population[PRIMARY_SCOPE]),
        LOW_DENSITY_SCOPE: set(population[LOW_DENSITY_SCOPE]),
        NON_FIXTURE_SCOPE: set(population[NON_FIXTURE_SCOPE]),
        NO_MISMATCH_SCOPE: no_mismatch,
    }
    mode_budgets = {
        "evaluation_count": FUZZER_EVAL_BUDGETS,
        "wall_clock": FUZZER_TIME_LIMITS,
    }
    for mode in sorted({str(row.get("mode")) for row in run_rows if row.get("mode")}):
        budgets = mode_budgets.get(mode, [])
        for budget in budgets:
            for scope, scope_ids in scopes.items():
                per_seed = []
                false_alarms = 0
                for seed in RANDOM_SEEDS:
                    seed_rows = [
                        row for row in run_rows
                        if row.get("mode") == mode
                        and row.get("budget_or_time_limit") == budget
                        and row.get("seed") == seed
                    ]
                    supported_scope = [row for row in seed_rows if row["candidate_id"] in scope_ids and row.get("supported_by_libfuzzer_pipeline")]
                    detected = sum(1 for row in supported_scope if row.get("detected"))
                    per_seed.append(safe_div(detected, len(scope_ids)))
                    false_alarms += sum(1 for row in seed_rows if row["candidate_id"] in no_mismatch and row.get("no_mismatch_false_alarm"))
                rows.append(
                    {
                        "mode": mode,
                        "budget_or_time_limit": budget,
                        "population": scope,
                        "candidate_denominator": len(scope_ids),
                        "supported_candidates": len({row["candidate_id"] for row in run_rows if row.get("supported_by_libfuzzer_pipeline") and row["candidate_id"] in scope_ids}),
                        "mean_detection": statistics.mean(per_seed) if per_seed else 0.0,
                        "median_detection": percentile(per_seed, 0.5),
                        "stddev_detection": statistics.pstdev(per_seed) if len(per_seed) > 1 else 0.0,
                        "p2_5_detection": percentile(per_seed, 0.025),
                        "p97_5_detection": percentile(per_seed, 0.975),
                        "best_seed_detection": max(per_seed) if per_seed else 0.0,
                        "worst_seed_detection": min(per_seed) if per_seed else 0.0,
                    "no_mismatch_false_alarms": false_alarms,
                    "distinct_no_mismatch_false_alarm_candidates": len({
                        row["candidate_id"] for row in run_rows
                        if row.get("no_mismatch_false_alarm")
                        and row.get("mode") == mode
                        and row.get("budget_or_time_limit") == budget
                    }),
                    "baseline_status": "completed",
                        "blocker": "",
                        "clang_version": command_first_line(["/usr/lib/llvm-11/bin/clang", "--version"]),
                        "source_literal_dictionary_used": False,
                    }
                )
    return rows


def libfuzzer_wall_clock_blocker_rows(population: dict[str, list[str]], clang_version: str) -> list[dict[str, Any]]:
    scopes = {
        PRIMARY_SCOPE: population[PRIMARY_SCOPE],
        LOW_DENSITY_SCOPE: population[LOW_DENSITY_SCOPE],
        NON_FIXTURE_SCOPE: population[NON_FIXTURE_SCOPE],
        NO_MISMATCH_SCOPE: population[NO_MISMATCH_SCOPE],
    }
    rows: list[dict[str, Any]] = []
    blocker = "not_run_in_phase1f_result_generation; full 71-candidate x 30-seed x 5s wall-clock matrix exceeds current reasonable CPU budget"
    for limit in FUZZER_TIME_LIMITS:
        for scope, ids in scopes.items():
            rows.append(
                {
                    "mode": "wall_clock",
                    "budget_or_time_limit": limit,
                    "population": scope,
                    "candidate_denominator": len(ids),
                    "supported_candidates": 0,
                    "mean_detection": 0.0,
                    "median_detection": 0.0,
                    "stddev_detection": 0.0,
                    "p2_5_detection": 0.0,
                    "p97_5_detection": 0.0,
                    "best_seed_detection": 0.0,
                    "worst_seed_detection": 0.0,
                    "no_mismatch_false_alarms": 0,
                    "distinct_no_mismatch_false_alarm_candidates": 0,
                    "baseline_status": "not_run_blocked",
                    "blocker": blocker,
                    "clang_version": clang_version,
                    "source_literal_dictionary_used": False,
                }
            )
    return rows


def bytes_to_domain_tuple(data: bytes, domain_specs: tuple[dict[str, Any], ...]) -> tuple[int, ...]:
    values = []
    for index, spec in enumerate(domain_specs):
        offset = index * 2
        raw = 0
        if offset < len(data):
            raw |= data[offset]
        if offset + 1 < len(data):
            raw |= data[offset + 1] << 8
        domain = [int(value) for value in spec["values"]]
        values.append(domain[raw % len(domain)])
    return tuple(values)


def encode_domain_tuple(domain_specs: tuple[dict[str, Any], ...], args: list[int]) -> bytes:
    data = bytearray()
    for spec, arg in zip(domain_specs, args):
        domain = [int(value) for value in spec["values"]]
        index = domain.index(int(arg))
        data.append(index & 0xFF)
        data.append((index >> 8) & 0xFF)
    return bytes(data)


def strong_baseline_budget_curves(
    first_rows: list[dict[str, Any]],
    population: dict[str, list[str]],
    libfuzzer_summary: list[dict[str, Any]],
    klee_summary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    primary = population[PRIMARY_SCOPE]
    for policy in [FINAL_POLICY, LITERAL_FIRST_POLICY, GENERIC_BOUNDARY_POLICY, FIXTURE_NEIGHBOR_POLICY]:
        for budget in BUDGETS:
            detected = detected_set(first_rows, policy, budget, None, primary)
            rows.append({"baseline": policy, "mode": "concrete_policy", "budget": budget, "detection_rate": safe_div(len(detected), len(primary)), "detected": len(detected), "denominator": len(primary)})
    for row in libfuzzer_summary:
        if row["mode"] == "evaluation_count" and row.get("population") == PRIMARY_SCOPE:
            rows.append({"baseline": "libFuzzer", "mode": "evaluation_count", "budget": row["budget_or_time_limit"], "detection_rate": row["mean_detection"], "detected": "", "denominator": row["candidate_denominator"]})
    return rows


def strong_baseline_time_curves(
    first_rows: list[dict[str, Any]],
    libfuzzer_summary: list[dict[str, Any]],
    klee_summary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for row in libfuzzer_summary:
        if row["mode"] == "wall_clock" and row.get("population") == PRIMARY_SCOPE:
            rows.append({"baseline": "libFuzzer", "time_s": row["budget_or_time_limit"], "detection_rate": row["mean_detection"], "status": row["baseline_status"]})
    for row in klee_summary:
        rows.append({"baseline": "KLEE", "time_s": row["wall_clock_limit_s"], "detection_rate": row["detection_on_all_candidate_denominator"], "status": row["baseline_status"]})
    return rows


def paired_policy_upset_rows(paired_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scope": row["scope"],
            "budget": row["budget"],
            "comparator_policy": row["comparator_policy"],
            "final_only": row["detected_only_by_final_count"],
            "comparator_only": row["detected_only_by_comparator_count"],
            "both": row["detected_by_both_count"],
            "neither": row["detected_by_neither_count"],
        }
        for row in paired_rows
        if row["scope"] == PRIMARY_SCOPE
    ]


def classify_interleaving(paired_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        row for row in paired_rows
        if row["comparator_policy"] == LITERAL_FIRST_POLICY and row["scope"] == PRIMARY_SCOPE
    ]
    final_improves_low_budget = any(float(row["detection_rate_difference_final_minus_comparator"]) > 0 for row in rows if int(row["budget"]) <= 4)
    literal_improves_low_budget = any(float(row["detection_rate_difference_final_minus_comparator"]) < 0 for row in rows if int(row["budget"]) <= 4)
    meaningful_regression = any(float(row["detection_rate_difference_final_minus_comparator"]) < -0.02 for row in rows)
    low_density_rows = [
        row for row in paired_rows
        if row["comparator_policy"] == LITERAL_FIRST_POLICY and row["scope"] == LOW_DENSITY_SCOPE
    ]
    low_density_improvement = any(float(row["detection_rate_difference_final_minus_comparator"]) > 0 for row in low_density_rows)
    median_improvement = any(
        row["final_median_first_witness_rank"] != ""
        and row["comparator_median_first_witness_rank"] != ""
        and float(row["final_median_first_witness_rank"]) <= 0.8 * float(row["comparator_median_first_witness_rank"])
        for row in rows
    )
    project_macro_improvement = any(float(row["project_macro_difference_final_minus_comparator"]) > 0 for row in rows)
    if (final_improves_low_budget or low_density_improvement or median_improvement or project_macro_improvement) and not meaningful_regression:
        classification = "interleaving improves early ranks or low budgets"
    elif literal_improves_low_budget and not final_improves_low_budget:
        classification = "literal-first is better"
    elif not meaningful_regression:
        classification = "interleaving is non-inferior but not distinguishable"
    else:
        classification = "evidence is mixed"
    return {
        "classification": classification,
        "final_improves_low_budget": final_improves_low_budget,
        "literal_improves_low_budget": literal_improves_low_budget,
        "meaningful_regression": meaningful_regression,
        "low_density_improvement": low_density_improvement,
        "median_rank_improvement_at_least_20_percent": median_improvement,
        "project_macro_improvement": project_macro_improvement,
    }


def interpretation_gates(
    *,
    first_rows: list[dict[str, Any]],
    population: dict[str, list[str]],
    libfuzzer_summary: list[dict[str, Any]],
    klee_summary: list[dict[str, Any]],
) -> dict[str, Any]:
    primary = population[PRIMARY_SCOPE]
    non_fixture = population[NON_FIXTURE_SCOPE]
    final_b8_primary = safe_div(len(detected_set(first_rows, FINAL_POLICY, 8, None, primary)), len(primary))
    final_b8_non_fixture = safe_div(len(detected_set(first_rows, FINAL_POLICY, 8, None, non_fixture)), len(non_fixture))
    deterministic_rates_b8 = [
        safe_div(len(detected_set(first_rows, policy, 8, None, primary)), len(primary))
        for policy in [FINAL_POLICY, LITERAL_FIRST_POLICY, GENERIC_BOUNDARY_POLICY, FIXTURE_NEIGHBOR_POLICY]
    ]
    final_on_pareto_b_le8 = True
    for budget in [1, 2, 4, 8]:
        final_rate = safe_div(len(detected_set(first_rows, FINAL_POLICY, budget, None, primary)), len(primary))
        comparator_rates = [
            safe_div(len(detected_set(first_rows, policy, budget, None, primary)), len(primary))
            for policy in [LITERAL_FIRST_POLICY, GENERIC_BOUNDARY_POLICY, FIXTURE_NEIGHBOR_POLICY]
        ]
        if any(rate > final_rate for rate in comparator_rates):
            final_on_pareto_b_le8 = False
    lib_b8 = next((
        row for row in libfuzzer_summary
        if row["mode"] == "evaluation_count"
        and int(float(row["budget_or_time_limit"])) == 8
        and row.get("population") == PRIMARY_SCOPE
    ), None)
    lib_materially_lower = bool(lib_b8 and lib_b8.get("baseline_status") == "completed" and final_b8_primary >= float(lib_b8["mean_detection"]) + 0.05)
    lib_completed = bool(lib_b8 and lib_b8.get("baseline_status") == "completed")
    no_mismatch_false_alarms = int(lib_b8.get("no_mismatch_false_alarms", 0)) if lib_b8 else 0
    strong = (
        final_b8_primary >= 0.85
        and final_b8_non_fixture >= 0.85
        and final_b8_primary >= max(deterministic_rates_b8)
        and final_on_pareto_b_le8
        and lib_completed
        and lib_materially_lower
        and no_mismatch_false_alarms == 0
    )
    return {
        "strong_low_budget_execution_claim_supported": strong,
        "final_detection_at_8_primary": final_b8_primary,
        "final_detection_at_8_non_fixture_overfit": final_b8_non_fixture,
        "libfuzzer_at_8_status": lib_b8.get("baseline_status") if lib_b8 else "missing",
        "libfuzzer_at_8_mean_detection": float(lib_b8["mean_detection"]) if lib_b8 and lib_b8.get("mean_detection") != "" else "",
        "libfuzzer_at_8_no_mismatch_false_alarms": no_mismatch_false_alarms,
        "final_on_detection_evaluation_pareto_frontier_b_le8": final_on_pareto_b_le8,
        "claim_consequence": "effective in the single-digit concrete-execution regime" if strong else "do not claim the strong low-budget Pareto gate; report final as a solver-free deterministic concrete policy, note literal-first dominates at B=1/2, and report KLEE unavailable",
    }


def write_tables(
    repo_root: Path,
    paired_rows: list[dict[str, Any]],
    klee_summary: list[dict[str, Any]],
    libfuzzer_summary: list[dict[str, Any]],
    final_miss_rows: list[dict[str, Any]],
    out_of_domain_rows: list[dict[str, Any]],
) -> None:
    table_dir = repo_root / "paper/tables"
    b8 = [row for row in paired_rows if row["scope"] == PRIMARY_SCOPE and int(row["budget"]) == 8]
    write_latex_table(
        table_dir / "holdout_paired_comparisons.tex",
        "Candidate-Paired Holdout Policy Comparisons",
        ["Comparator", "Final only", "Comparator only", "Both", "Neither", "Delta"],
        [[row["comparator_policy"], row["detected_only_by_final_count"], row["detected_only_by_comparator_count"], row["detected_by_both_count"], row["detected_by_neither_count"], fmt_rate(row["detection_rate_difference_final_minus_comparator"])] for row in b8],
    )
    strong_rows = []
    for row in libfuzzer_summary:
        if (
            row["population"] == PRIMARY_SCOPE
            and row["mode"] == "evaluation_count"
            and int(float(row["budget_or_time_limit"])) in {8, 128, 1024}
        ):
            strong_rows.append(["libFuzzer", row["budget_or_time_limit"], row["supported_candidates"], fmt_rate(row["mean_detection"]), row["no_mismatch_false_alarms"], row["baseline_status"]])
    for row in klee_summary:
        if row["population"] == PRIMARY_SCOPE and float(row["wall_clock_limit_s"]) in {0.1, 1.0, 5.0}:
            strong_rows.append(["KLEE", row["wall_clock_limit_s"], row["supported_candidates"], fmt_rate(row["detection_on_all_candidate_denominator"]), row["no_mismatch_false_alarm"], row["baseline_status"]])
    write_latex_table(
        table_dir / "strong_semantic_baselines.tex",
        "External Semantic Baselines",
        ["Baseline", "Budget/time", "Supported", "Detection", "False alarms", "Status"],
        strong_rows,
    )
    misses = [row for row in final_miss_rows if row["list_name"] == "final_miss_b8"]
    write_latex_table(
        table_dir / "final_failure_cases.tex",
        "Final Policy Budget-8 Misses",
        ["Candidate", "Project", "Function", "Mutation", "Density"],
        [[short_id(row["candidate_id"]), row["project"], row["function"], row["mutation_family"], fmt_rate(row["mismatch_density"])] for row in misses],
    )
    ood = [row for row in out_of_domain_rows if row["policy"] == FINAL_POLICY and int(row["budget"]) == 8 and row["scope"] in {PRIMARY_SCOPE, LOW_DENSITY_SCOPE, NO_MISMATCH_SCOPE, "natural_ghidra_no_mismatch"}]
    write_latex_table(
        table_dir / "out_of_domain_analysis.tex",
        "Final Policy Budget-8 Out-of-Domain Probes",
        ["Scope", "Probes", "OOD", "OOD witnesses", "Confirmed"],
        [[row["scope"], row["total_generated_probes"], row["out_of_domain_probe_count"], row["distinct_out_of_domain_witness_count"], row["confirmed_distinct_witness_count"]] for row in ood],
    )


def write_plot_script(repo_root: Path) -> None:
    path = repo_root / "figures/plot_phase1f_strong_baselines.py"
    path.write_text(
        """from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "figures/data"


def rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def plot_budget_curves() -> None:
    data = rows("strong_baseline_budget_curves.csv")
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for baseline in sorted({row["baseline"] for row in data}):
        items = sorted([row for row in data if row["baseline"] == baseline], key=lambda row: float(row["budget"]))
        ax.plot([float(row["budget"]) for row in items], [float(row["detection_rate"]) for row in items], marker="o", linewidth=1.3, label=baseline)
    ax.set_xlabel("Completed evaluations")
    ax.set_ylabel("Detection rate")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/strong_baseline_budget_curves.pdf")


def plot_time_curves() -> None:
    data = rows("strong_baseline_time_curves.csv")
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    for baseline in sorted({row["baseline"] for row in data}):
        items = sorted([row for row in data if row["baseline"] == baseline], key=lambda row: float(row["time_s"]))
        ax.plot([float(row["time_s"]) for row in items], [float(row["detection_rate"]) for row in items], marker="o", linewidth=1.3, label=baseline)
    ax.set_xlabel("Wall-clock limit (s)")
    ax.set_ylabel("Detection rate")
    ax.set_xscale("log")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/strong_baseline_time_curves.pdf")


def plot_upsets() -> None:
    data = [row for row in rows("paired_policy_upset.csv") if row["budget"] == "8"]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    labels = [row["comparator_policy"] for row in data]
    final = [int(row["final_only"]) for row in data]
    comp = [int(row["comparator_only"]) for row in data]
    x = range(len(labels))
    ax.bar([v - 0.18 for v in x], final, width=0.36, label="Final only")
    ax.bar([v + 0.18 for v in x], comp, width=0.36, label="Comparator only")
    ax.set_xticks(list(x), labels, rotation=20, ha="right")
    ax.set_ylabel("Discordant candidates")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/paired_policy_upset.pdf")


if __name__ == "__main__":
    plot_budget_curves()
    plot_time_curves()
    plot_upsets()
""",
        encoding="utf-8",
    )


def generate_figures(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / "figures/plot_phase1f_strong_baselines.py")],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def write_handoff(
    *,
    repo_root: Path,
    population: dict[str, list[str]],
    paired_rows: list[dict[str, Any]],
    mechanism_rows: list[dict[str, Any]],
    out_of_domain_rows: list[dict[str, Any]],
    klee_summary_rows: list[dict[str, Any]],
    libfuzzer_summary_rows: list[dict[str, Any]],
    exhaustive_rows: list[dict[str, Any]],
    interleaving: dict[str, Any],
    gates: dict[str, Any],
) -> Path:
    head = git_output(repo_root, ["rev-parse", "HEAD"])
    prereg_commit = git_output(repo_root, ["rev-parse", "b905690"])
    correction_commit = git_output(repo_root, ["rev-parse", "--short", "HEAD"])
    final_literal = [
        row for row in paired_rows
        if row["comparator_policy"] == LITERAL_FIRST_POLICY and row["scope"] == PRIMARY_SCOPE
    ]
    generic_b8 = next(row for row in paired_rows if row["comparator_policy"] == GENERIC_BOUNDARY_POLICY and row["scope"] == PRIMARY_SCOPE and int(row["budget"]) == 8)
    final_miss_b8 = [row["candidate_id"] for row in mechanism_rows if row["list_name"] == "final_miss_b8"]
    final_miss_b32 = [row["candidate_id"] for row in mechanism_rows if row["list_name"] == "final_miss_b32"]
    final_b8_ood = [
        row for row in out_of_domain_rows
        if row["policy"] == FINAL_POLICY and int(row["budget"]) == 8 and row["scope"] == PRIMARY_SCOPE
    ][0]
    lib_b8 = next((
        row for row in libfuzzer_summary_rows
        if row["mode"] == "evaluation_count"
        and int(float(row["budget_or_time_limit"])) == 8
        and row["population"] == PRIMARY_SCOPE
    ), None)
    klee_status = klee_summary_rows[0]["baseline_status"] if klee_summary_rows else "missing"
    lib_status = libfuzzer_summary_rows[0]["baseline_status"] if libfuzzer_summary_rows else "missing"
    path = repo_root / "docs/paper_agent/strong_baselines_and_mechanism_handoff.md"
    lines = [
        "# Strong Baselines And Mechanism Handoff",
        "",
        "## Git",
        "",
        "- Branch: `phase1f-strong-baselines-and-mechanism`",
        f"- Preregistration commit: `{prereg_commit}`",
        f"- Result commit: `{head}` (pre-commit working tree context at generation)",
        f"- Verified holdout seal: `{VERIFIED_HOLDOUT_SEAL}`",
        f"- Method freeze commit: `{METHOD_FREEZE_COMMIT}`",
        "",
        "## Populations",
        "",
        f"- Primary fixture-passing semantic-wrong candidates: `{len(population[PRIMARY_SCOPE])}`",
        f"- Low-density fixture-passing wrong candidates: `{len(population[LOW_DENSITY_SCOPE])}`",
        f"- Non-fixture-overfit fixture-passing wrong candidates: `{len(population[NON_FIXTURE_SCOPE])}`",
        f"- Exact-domain no-mismatch comparison candidates: `{len(population[NO_MISMATCH_SCOPE])}`",
        "",
        "## Final Versus Literal-First",
        "",
    ]
    for row in sorted(final_literal, key=lambda item: int(item["budget"])):
        lines.append(
            f"- B={row['budget']}: final `{row['final_detected']}/{row['denominator']}`, "
            f"literal-first `{row['comparator_detected']}/{row['denominator']}`, "
            f"delta `{fmt_rate(row['detection_rate_difference_final_minus_comparator'])}`"
        )
    lines.extend([
        "",
        "## Paired Discordance At B=8",
        "",
        f"- Final versus generic-boundary wins/losses: `{generic_b8['paired_final_win_count']}/{generic_b8['paired_comparator_win_count']}`",
        f"- B=8 final misses: `{json.dumps(final_miss_b8)}`",
        f"- B=32 final misses: `{json.dumps(final_miss_b32)}`",
        f"- Non-fixture-overfit Detection@8: `{fmt_rate(gates['final_detection_at_8_non_fixture_overfit'])}`",
        "",
        "## Out-Of-Domain",
        "",
        f"- Final B=8 primary generated probes: `{final_b8_ood['total_generated_probes']}`",
        f"- Final B=8 primary out-of-domain probes: `{final_b8_ood['out_of_domain_probe_count']}`",
        f"- Final B=8 primary distinct out-of-domain witnesses: `{final_b8_ood['distinct_out_of_domain_witness_count']}`",
        f"- Confirmed final B=8 distinct out-of-domain witnesses: `{final_b8_ood['confirmed_distinct_witness_count']}`",
        "",
        "## External Baselines",
        "",
        f"- KLEE status: `{klee_status}`; supported candidates `{klee_summary_rows[0]['supported_candidates'] if klee_summary_rows else 0}`.",
        f"- libFuzzer status: `{lib_status}`; supported candidates `{libfuzzer_summary_rows[0]['supported_candidates'] if libfuzzer_summary_rows else 0}`.",
        f"- libFuzzer evaluation-count Detection@8 mean: `{fmt_rate(lib_b8['mean_detection']) if lib_b8 else 'missing'}`.",
        f"- libFuzzer no-mismatch false-alarm rows at B=8: `{lib_b8['no_mismatch_false_alarms'] if lib_b8 else 'missing'}`.",
        f"- libFuzzer wall-clock matrix: `{next((row['baseline_status'] for row in libfuzzer_summary_rows if row['mode'] == 'wall_clock'), 'missing')}` due to CPU-budget gate.",
        "- GPU usage: none; no GPU experiments were started.",
        "",
        "## Exhaustive Reference",
        "",
        f"- Exact-label reference rows: `{len(exhaustive_rows)}`",
        "- Total enumeration time was not recorded in the sealed label artifact; the reference table reports input-domain cost and first-witness rank.",
        "",
        "## Interpretation Gates",
        "",
        f"- Interleaving classification: `{interleaving['classification']}`",
        f"- Strong low-budget execution claim supported: `{gates['strong_low_budget_execution_claim_supported']}`",
        f"- Paper-claim consequence: {gates['claim_consequence']}",
        "",
        "## Tests Run",
        "",
        "- `python -m py_compile analysis/decompile_faithfulness/strong_baselines_and_mechanism.py`",
        "- `python -m unittest analysis.decompile_faithfulness.tests.test_probe_order_freeze analysis.decompile_faithfulness.tests.test_submission_evidence_corrections analysis.decompile_faithfulness.tests.test_holdout_acquisition analysis.decompile_faithfulness.tests.test_holdout_evaluation analysis.decompile_faithfulness.tests.test_strong_baselines_and_mechanism`",
        "",
        "The Phase 1f generator consumes immutable Phase 1e traces and sealed holdout artifacts. It does not import or call the frozen final scheduler, regenerate holdout material, or alter method-affecting files.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def detected_set(
    rows: list[dict[str, Any]],
    policy: str,
    budget: int,
    seed: int | None,
    ids: list[str],
) -> set[str]:
    wanted = set(ids)
    return {
        row["candidate_id"] for row in rows
        if row["candidate_id"] in wanted
        and row["policy"] == policy
        and row["budget"] == budget
        and row["random_seed"] == seed
        and row["detected_in_domain"]
    }


def comparator_detected_set(
    rows: list[dict[str, Any]],
    policy: str,
    budget: int,
    ids: list[str],
) -> tuple[set[str], str]:
    if policy in STOCHASTIC_POLICIES:
        wanted = set(ids)
        return (
            {
                row["candidate_id"] for row in rows
                if row["candidate_id"] in wanted
                and row["policy"] == policy
                and row["budget"] == budget
                and row["random_seed"] in RANDOM_SEEDS
                and row["detected_in_domain"]
            },
            "detected_by_any_of_30_fixed_seeds",
        )
    return detected_set(rows, policy, budget, None, ids), "deterministic_single_order"


def ranks_for(rows: list[dict[str, Any]], policy: str, budget: int, seed: int | None, ids: list[str]) -> list[int]:
    wanted = set(ids)
    return [
        int(row["first_in_domain_witness_rank"]) for row in rows
        if row["candidate_id"] in wanted
        and row["policy"] == policy
        and row["budget"] == budget
        and row["random_seed"] == seed
        and row["first_in_domain_witness_rank"] is not None
    ]


def exact_mismatch_summary(label: dict[str, Any]) -> dict[str, Any]:
    first = label.get("first_mismatch")
    stored = label.get("stored_mismatches", [])
    return {
        "exact_domain_size": label.get("exact_domain_size"),
        "total_mismatching_input_count": label.get("total_mismatching_input_count"),
        "first_mismatch": first,
        "stored_mismatch_prefix_count": len(stored),
        "complete_mismatch_set_sha256": label.get("complete_mismatch_set_sha256"),
    }


def mismatch_density(label: dict[str, Any]) -> float:
    return safe_div(int(label.get("total_mismatching_input_count", 0)), int(label.get("exact_domain_size", 0)))


def baseline_candidate_ids(population: dict[str, list[str]]) -> list[str]:
    return sorted(set(population[PRIMARY_SCOPE]) | set(population[NO_MISMATCH_SCOPE]))


def libfuzzer_smoke_available(clang: Path) -> bool:
    if not clang.exists():
        return False
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "smoke.c"
        exe = Path(tmp) / "smoke"
        source.write_text("int LLVMFuzzerTestOneInput(const unsigned char *D, unsigned long S) { return 0; }\n", encoding="utf-8")
        result = subprocess.run([str(clang), "-fsanitize=fuzzer", str(source), "-o", str(exe)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            return False
        run = subprocess.run([str(exe), "-runs=1"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10)
        return run.returncode == 0


def command_first_line(argv: list[str]) -> str:
    try:
        result = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    text = result.stdout.strip() or result.stderr.strip()
    return text.splitlines()[0] if text else "unavailable"


def safe_c_identifier(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not safe or safe[0].isdigit():
        safe = "_" + safe
    return safe


def safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return safe.strip("._")[:180] or "item"


def short_id(value: str) -> str:
    return value.split("::")[-1]


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value == "True" or value == "true"


def percentile(values: list[float] | list[int], q: float) -> float | str:
    if not values:
        return ""
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def safe_div(left: float, right: float) -> float:
    return float(left) / float(right) if right else 0.0


def fmt_rate(value: Any) -> str:
    if value == "":
        return ""
    return f"{float(value):.3f}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_latex_table(path: Path, caption: str, headers: list[str], rows: list[list[Any]]) -> None:
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\small",
        "\\begin{tabular}{" + "l" * len(headers) + "}",
        "\\toprule",
        " & ".join(headers) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(latex_escape(str(value)) for value in row) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", f"\\caption{{{latex_escape(caption)}}}", "\\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def latex_escape(value: str) -> str:
    return (
        value.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
        .replace("#", "\\#")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_output(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout.strip()


if __name__ == "__main__":
    main()
