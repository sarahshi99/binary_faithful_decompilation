from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import platform
import random
import re
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from analysis.decompile_faithfulness import holdout_evaluation as he
from analysis.decompile_faithfulness import prospective_natural_llm as nllm


POLICY = "source_behavioral_diversity"
PAPER_NAME = "Source-Behavioral Diversity Witnessing"
PREREG_COMMIT_ABBREV = "af95093"
METHOD_FREEZE_COMMIT = "06dda89912103b94fc065d6f073581a7811154b1"
PHASE1H_HEAD = "3bdb9f26621d2af4aea87aaa3923457532e549b0"
POOL_SEED = 2026070601
INSTRUMENTATION_VERSION = "clang_trace_pc_guard_v1"
BUILD_CONFIG = "clang_O0_trace_pc_guard_source_only"
MAX_SOURCE_POOL = 4096
BUDGETS = [1, 2, 4, 8, 16, 32]
SBDW_POLICIES = [
    POLICY,
    "output_diversity_only",
    "coverage_diversity_only",
    "output_then_coverage",
    "coverage_then_output",
    "source_behavioral_diversity_no_distance",
]
BASELINE_POLICIES = [
    he.FINAL_POLICY,
    "literal_first_concatenation",
    "generic_type_boundaries",
    "fixture_neighbor_only",
    "uniform_random_domain",
    "randomized_union_order",
]
WORK_DIR = Path("analysis_outputs/decompile_faithfulness/phase2a_sbdw")


@dataclass(frozen=True)
class PoolInput:
    function_id: str
    args: tuple[int, ...]
    canonical_rank: int
    origins: tuple[str, ...]
    is_fixture: bool


@dataclass(frozen=True)
class BehaviorRecord:
    function_id: str
    args: tuple[int, ...]
    normalized_output: int | None
    edge_set: tuple[int, ...]
    edge_coverage_signature: str
    branch_coverage_signature: str
    trace_hash: str
    execution_status: str
    source_execution_time_s: float
    behavior_signature: str


@dataclass(frozen=True)
class SourceInstrumentation:
    ok: bool
    exe_path: Path | None
    source_path: Path
    reason: str
    compile_time_s: float
    stderr_tail: str = ""


def main() -> None:
    args = parse_args()
    summary = run(Path(args.repo_root).resolve())
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 2a Source-Behavioral Diversity Witnessing prototype")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    return parser.parse_args()


def run(repo_root: Path) -> dict[str, Any]:
    out_dir = repo_root / "results/decompile_faithfulness"
    fig_data_dir = repo_root / "figures/data"
    fig_dir = repo_root / "figures"
    table_dir = repo_root / "paper/tables"
    docs_dir = repo_root / "docs/paper_agent"
    work_dir = repo_root / WORK_DIR
    for path in [out_dir, fig_data_dir, fig_dir, table_dir, docs_dir, work_dir]:
        path.mkdir(parents=True, exist_ok=True)

    functions = he.load_functions(repo_root)
    fixtures = he.load_fixtures(repo_root)
    controlled_candidates, controlled_labels, controlled_population = load_controlled_development(repo_root, functions)
    natural_candidates, natural_labels, natural_population = load_natural_development(repo_root, functions)
    labels = {**controlled_labels, **natural_labels}
    all_candidates = controlled_candidates + natural_candidates

    pool_started = time.perf_counter()
    pools = {fid: construct_source_pool(function, fixtures[fid]) for fid, function in functions.items()}
    pool_generation_s = time.perf_counter() - pool_started
    write_jsonl(out_dir / "sbdw_source_pool.jsonl", pool_rows(pools, functions))

    cache_started = time.perf_counter()
    behavior_cache, instrumentation_rows = build_behavior_cache(repo_root, functions, pools, work_dir / "source_behavior")
    source_execution_s = time.perf_counter() - cache_started
    if any(not row["ok"] for row in instrumentation_rows):
        write_jsonl(out_dir / "sbdw_source_behavior_cache.jsonl", behavior_cache_rows(behavior_cache, pools, functions, instrumentation_rows))
        blocker = write_blocker_handoff(repo_root, instrumentation_rows)
        return {"status": "blocked", "reason": "source_instrumentation_unreliable", "handoff": str(blocker.relative_to(repo_root))}

    write_jsonl(out_dir / "sbdw_source_behavior_cache.jsonl", behavior_cache_rows(behavior_cache, pools, functions, instrumentation_rows))

    selection_started = time.perf_counter()
    policy_orders, selection_rows = build_sbdw_policy_orders(functions, pools, behavior_cache, fixtures)
    selection_s = time.perf_counter() - selection_started

    controlled_traces, controlled_first, controlled_unexpected = he.evaluate_policies(
        repo_root=repo_root,
        functions=functions,
        candidates=controlled_candidates,
        labels=controlled_labels,
        population=controlled_population,
        policy_orders=policy_orders,
        generation_times={key: selection_s / max(1, len(policy_orders)) for key in policy_orders},
        work_dir=work_dir / "controlled_policy_execution",
    )
    natural_traces, natural_first, natural_unexpected = he.evaluate_policies(
        repo_root=repo_root,
        functions=functions,
        candidates=natural_candidates,
        labels=natural_labels,
        population=natural_population_adapter(natural_population),
        policy_orders=policy_orders,
        generation_times={key: selection_s / max(1, len(policy_orders)) for key in policy_orders},
        work_dir=work_dir / "natural_policy_execution",
    )

    traces = tag_population(controlled_traces, "controlled") + tag_population(natural_traces, "natural_llm")
    first_rows = tag_population(controlled_first, "controlled") + tag_population(natural_first, "natural_llm")
    unexpected_rows = tag_population(controlled_unexpected, "controlled") + tag_population(natural_unexpected, "natural_llm")
    write_jsonl(out_dir / "sbdw_policy_traces.jsonl", traces)

    budget_curves = sbdw_budget_curves(first_rows, controlled_population, natural_population)
    ablation_summary = sbdw_ablation_summary(budget_curves, first_rows)
    cost_summary = sbdw_cost_summary(
        pool_generation_s=pool_generation_s,
        source_execution_s=source_execution_s,
        selection_s=selection_s,
        instrumentation_compile_s=sum(float(row.get("compile_time_s") or 0.0) for row in instrumentation_rows),
        behavior_cache=behavior_cache,
        traces=traces,
        controlled_population=controlled_population,
        natural_population=natural_population,
    )
    mechanisms = sbdw_candidate_mechanisms(
        first_rows=first_rows,
        traces=traces,
        pools=pools,
        behavior_cache=behavior_cache,
        functions=functions,
        fixtures=fixtures,
        labels=labels,
        controlled_population=controlled_population,
        natural_population=natural_population,
    )
    gates = development_gates(budget_curves, cost_summary, mechanisms)

    write_csv(out_dir / "sbdw_budget_curves.csv", budget_curves)
    write_csv(out_dir / "sbdw_ablation_summary.csv", ablation_summary)
    write_csv(out_dir / "sbdw_cost_summary.csv", cost_summary)
    write_jsonl(out_dir / "sbdw_candidate_mechanisms.jsonl", mechanisms)
    write_csv(fig_data_dir / "sbdw_budget_curves.csv", budget_curves)
    write_csv(fig_data_dir / "sbdw_cost_amortization.csv", [row for row in cost_summary if row["cost_type"] == "amortized_end_to_end"])
    write_csv(fig_data_dir / "sbdw_behavior_selection.csv", behavior_selection_rows(selection_rows, behavior_cache))
    write_tables(repo_root, budget_curves, ablation_summary, cost_summary, mechanisms)
    write_plot_script(repo_root)
    generate_figures(repo_root)
    handoff = write_handoff(
        repo_root=repo_root,
        instrumentation_rows=instrumentation_rows,
        budget_curves=budget_curves,
        ablation_summary=ablation_summary,
        cost_summary=cost_summary,
        mechanisms=mechanisms,
        gates=gates,
    )
    return {
        "status": "completed",
        "supported_source_functions": sum(1 for row in instrumentation_rows if row["ok"]),
        "unsupported_source_functions": sum(1 for row in instrumentation_rows if not row["ok"]),
        "controlled_primary_detection_b8": metric_lookup(budget_curves, POLICY, 8, "controlled_primary_fixture_passing_wrong")["detected"],
        "natural_detection_b8": metric_lookup(budget_curves, POLICY, 8, "natural_llm_primary_fixture_passing_wrong")["detected"],
        "gate_outcome": gates["outcome"],
        "handoff": str(handoff.relative_to(repo_root)),
    }


def load_controlled_development(
    repo_root: Path,
    functions: dict[str, he.HoldoutFunction],
) -> tuple[list[he.CandidateRecord], dict[str, dict[str, Any]], dict[str, Any]]:
    candidates = he.load_candidates(repo_root)
    labels = {row["candidate_id"]: row for row in he.read_jsonl(repo_root / "results/decompile_faithfulness/holdout_exact_labels.jsonl")}
    fixture_replay = he.read_jsonl(repo_root / "results/decompile_faithfulness/holdout_fixture_replay.jsonl")
    population = he.build_population(candidates, labels, fixture_replay, functions)
    ids = set(population["sets"]["primary_fixture_passing_wrong"]) | set(population["sets"]["no_mismatch_comparison"])
    selected = [candidate for candidate in candidates if candidate.candidate_id in ids]
    selected_labels = {cid: labels[cid] for cid in ids}
    return selected, selected_labels, population


def load_natural_development(
    repo_root: Path,
    functions: dict[str, he.HoldoutFunction],
) -> tuple[list[he.CandidateRecord], dict[str, dict[str, Any]], dict[str, Any]]:
    manifest = nllm.read_jsonl(repo_root / "results/decompile_faithfulness/natural_llm_candidate_manifest.jsonl")
    labels = {row["candidate_id"]: row for row in nllm.read_jsonl(repo_root / "results/decompile_faithfulness/natural_llm_exact_labels.jsonl")}
    replay = nllm.read_jsonl(repo_root / "results/decompile_faithfulness/natural_llm_fixture_replay.jsonl")
    population = nllm.build_natural_population(manifest, list(labels.values()), replay, functions)
    ids = set(population["sets"]["primary_fixture_passing_wrong"]) | set(population["sets"]["no_mismatch_comparison"])
    manifest_by_id = {row["candidate_id"]: row for row in manifest}
    candidates: list[he.CandidateRecord] = []
    for cid in sorted(ids):
        row = manifest_by_id[cid]
        label = labels[cid]
        candidates.append(
            he.CandidateRecord(
                candidate_id=cid,
                function_id=row["function_id"],
                project=row["project"],
                candidate_stratum="natural_llm",
                candidate_class="natural_llm_output",
                label=label["label"],
                compile_status=row.get("compile_status", ""),
                execution_status=row.get("execution_status", ""),
                mutation_family=f"{row.get('build_view', '')}::{row.get('prompt_family', '')}",
                source_path=Path(row.get("candidate_source_path") or row.get("normalized_candidate_path", "")),
                total_mismatching_input_count=int(label.get("total_mismatching_input_count", 0)),
                exact_domain_size=int(label.get("exact_domain_size", 0)),
            )
        )
    return candidates, {cid: labels[cid] for cid in ids}, population


def natural_population_adapter(population: dict[str, Any]) -> dict[str, Any]:
    return {
        "sets": {
            "primary_fixture_passing_wrong": population["sets"]["primary_fixture_passing_wrong"],
            "low_density_fixture_passing_wrong": population["sets"]["low_density_fixture_passing_wrong"],
            "all_controlled_semantic_wrong": population["sets"]["semantic_wrong"],
            "no_mismatch_comparison": population["sets"]["no_mismatch_comparison"],
        }
    }


def construct_source_pool(function: he.HoldoutFunction, fixture_rows: list[dict[str, Any]], max_pool: int = MAX_SOURCE_POOL) -> list[PoolInput]:
    entry, case = he.frozen_entry_and_case(function, fixture_rows)
    fixture_args = {tuple(int(value) for value in row["args"]) for row in fixture_rows}
    domain_set = set(function.domain)
    origins: dict[tuple[int, ...], set[str]] = defaultdict(set)

    for args in fixture_args:
        origins[args].add("sealed_fixture")
    provenance = he.component_provenance(entry, case)
    for args, names in provenance.items():
        if args in domain_set:
            for name in names:
                origins[args].add(name)
    for probe in he.generic_type_boundary_order(function, entry):
        if probe.args in domain_set:
            origins[probe.args].add("generic_type_boundary")
    for probe in he.build_policy_order("generic_fallback_only", entry, case, function, seed=None):
        if probe.args in domain_set:
            origins[probe.args].add("generic_fallback")
    for args in deterministic_domain_inputs(function, max_pool=max_pool):
        origins[args].add("complete_domain" if function.domain_size <= max_pool else "deterministic_domain_sample")

    rows = []
    for rank, args in enumerate(sorted(origins), start=1):
        rows.append(PoolInput(function.function_id, args, rank, tuple(sorted(origins[args])), args in fixture_args))
    return rows


def deterministic_domain_inputs(function: he.HoldoutFunction, max_pool: int = MAX_SOURCE_POOL) -> list[tuple[int, ...]]:
    if function.domain_size <= max_pool:
        return list(function.domain)
    rng = random.Random(stable_seed(POOL_SEED, function.function_id, "domain_sample"))
    required: list[tuple[int, ...]] = []
    values_by_pos = [list(map(int, spec["values"])) for spec in function.domain_specs]
    for values in values_by_pos:
        for value in [values[0], values[-1], values[len(values) // 2]]:
            midpoint = tuple(v[len(v) // 2] for v in values_by_pos)
            for index in range(len(values_by_pos)):
                item = list(midpoint)
                item[index] = value
                required.append(tuple(item))
    domain = list(function.domain)
    rng.shuffle(domain)
    result = []
    seen: set[tuple[int, ...]] = set()
    for args in required + domain:
        if args in seen:
            continue
        seen.add(args)
        result.append(args)
        if len(result) >= max_pool:
            break
    return sorted(result)


def build_behavior_cache(
    repo_root: Path,
    functions: dict[str, he.HoldoutFunction],
    pools: dict[str, list[PoolInput]],
    work_dir: Path,
) -> tuple[dict[tuple[str, tuple[int, ...]], BehaviorRecord], list[dict[str, Any]]]:
    clang = find_clang()
    cache: dict[tuple[str, tuple[int, ...]], BehaviorRecord] = {}
    instrumentation_rows: list[dict[str, Any]] = []
    for function_id, function in sorted(functions.items()):
        function_dir = work_dir / he.safe_name(function_id)
        instr = compile_source_instrumentation(clang, function, function_dir)
        instrumentation_rows.append({
            "function_id": function_id,
            "project": function.project,
            "ok": instr.ok,
            "reason": instr.reason,
            "compile_time_s": instr.compile_time_s,
            "instrumentation_version": INSTRUMENTATION_VERSION,
            "clang": str(clang),
            "stderr_tail": instr.stderr_tail,
        })
        if not instr.ok or instr.exe_path is None:
            continue
        for item in pools[function_id]:
            record = execute_source_behavior(instr.exe_path, function, item.args, function_dir / "runs")
            cache[(function_id, item.args)] = record
    return cache, instrumentation_rows


def find_clang() -> Path:
    for candidate in [Path("/usr/lib/llvm-11/bin/clang"), Path("/usr/bin/clang")]:
        if candidate.exists():
            return candidate
    found = shutil.which("clang")
    if found:
        return Path(found)
    raise RuntimeError("clang is required for source-only edge instrumentation")


def compile_source_instrumentation(clang: Path, function: he.HoldoutFunction, output_dir: Path) -> SourceInstrumentation:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_path = output_dir / "source_behavior.c"
    exe_path = output_dir / "source_behavior.exe"
    source_path.write_text(render_source_behavior_harness(function), encoding="utf-8")
    cmd = [
        str(clang),
        "-std=c11",
        "-O0",
        "-w",
        "-fsanitize-coverage=trace-pc-guard,no-prune",
        str(source_path),
        "-o",
        str(exe_path),
    ]
    started = time.perf_counter()
    result = subprocess.run(cmd, cwd=output_dir, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
    elapsed = time.perf_counter() - started
    if result.returncode != 0:
        return SourceInstrumentation(False, None, source_path, "compile_failure", elapsed, result.stderr[-2000:])
    return SourceInstrumentation(True, exe_path, source_path, "ok", elapsed)


def render_source_behavior_harness(function: he.HoldoutFunction) -> str:
    parse_lines = []
    call_args = []
    for index, spec in enumerate(function.domain_specs):
        ctype = c_type_for_spec(spec)
        parse_lines.append(f"    long long raw{index} = atoll(argv[{index + 1}]);")
        parse_lines.append(f"    {ctype} arg{index} = ({ctype}) raw{index};")
        call_args.append(f"arg{index}")
    return "\n".join([
        "#include <stdbool.h>",
        "#include <stdint.h>",
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "",
        function.source.rstrip(),
        "",
        "static unsigned int sbdw_edges[65536];",
        "static unsigned int sbdw_edge_count = 0;",
        "static int sbdw_enabled = 0;",
        "__attribute__((no_sanitize(\"coverage\"))) void __sanitizer_cov_trace_pc_guard_init(uint32_t *start, uint32_t *stop) {",
        "    static uint32_t next_id = 1;",
        "    if (start == stop || *start) return;",
        "    for (uint32_t *x = start; x < stop; x++) *x = next_id++;",
        "}",
        "__attribute__((no_sanitize(\"coverage\"))) void __sanitizer_cov_trace_pc_guard(uint32_t *guard) {",
        "    if (!sbdw_enabled || !*guard) return;",
        "    if (sbdw_edge_count < 65536) sbdw_edges[sbdw_edge_count++] = *guard;",
        "}",
        "int main(int argc, char **argv) {",
        f"    if (argc != {len(function.domain_specs) + 1}) return 2;",
        *parse_lines,
        "    sbdw_enabled = 1;",
        f"    long long out = (long long){function.function_name}({', '.join(call_args)});",
        "    sbdw_enabled = 0;",
        "    printf(\"OUT %lld\\n\", out);",
        "    printf(\"EDGES\");",
        "    for (unsigned int i = 0; i < sbdw_edge_count; i++) printf(\" %u\", sbdw_edges[i]);",
        "    printf(\"\\n\");",
        "    return 0;",
        "}",
        "",
    ])


def c_type_for_spec(spec: dict[str, Any]) -> str:
    text = str(spec.get("type", "int")).strip()
    if text in {"bool", "_Bool"}:
        return "bool"
    return text or "int"


def execute_source_behavior(exe_path: Path, function: he.HoldoutFunction, args: tuple[int, ...], run_dir: Path) -> BehaviorRecord:
    run_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    started = time.perf_counter()
    result = subprocess.run(
        [str(exe_path), *[str(value) for value in args]],
        cwd=run_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
        env=env,
    )
    elapsed = time.perf_counter() - started
    output = None
    edges: tuple[int, ...] = ()
    status = "ok"
    if result.returncode != 0:
        status = f"runtime_failure_{result.returncode}"
    else:
        for line in result.stdout.splitlines():
            if line.startswith("OUT "):
                output = int(line.split()[1])
            elif line.startswith("EDGES"):
                edges = tuple(int(value) for value in line.split()[1:])
        if output is None:
            status = "missing_output"
    edge_set = tuple(sorted(set(edges)))
    edge_sig = sha256_text(json.dumps(edge_set))
    trace_hash = sha256_text(json.dumps(edges))
    behavior_sig = sha256_text(json.dumps([output, edge_sig]))
    return BehaviorRecord(
        function_id=function.function_id,
        args=args,
        normalized_output=output,
        edge_set=edge_set,
        edge_coverage_signature=edge_sig,
        branch_coverage_signature=edge_sig,
        trace_hash=trace_hash,
        execution_status=status,
        source_execution_time_s=elapsed,
        behavior_signature=behavior_sig,
    )


def build_sbdw_policy_orders(
    functions: dict[str, he.HoldoutFunction],
    pools: dict[str, list[PoolInput]],
    behavior_cache: dict[tuple[str, tuple[int, ...]], BehaviorRecord],
    fixtures: dict[str, list[dict[str, Any]]],
) -> tuple[dict[tuple[str, str, int | None], list[he.PolicyProbe]], list[dict[str, Any]]]:
    orders: dict[tuple[str, str, int | None], list[he.PolicyProbe]] = {}
    selection_rows: list[dict[str, Any]] = []
    for function_id, function in sorted(functions.items()):
        for policy in SBDW_POLICIES:
            selected = select_behavioral_prefix(policy, pools[function_id], behavior_cache, fixtures[function_id])
            orders[(function_id, policy, None)] = [
                he.PolicyProbe(
                    args=item.args,
                    bucket=policy,
                    source_literal_derived="source_literal_char" in item.origins,
                    fixture_neighbor_derived="fixture_neighbor" in item.origins,
                    generic_fallback_derived="generic_fallback" in item.origins,
                    generic_type_boundary_derived="generic_type_boundary" in item.origins,
                    duplicate_sources=item.origins,
                )
                for item in selected
            ]
            for rank, item in enumerate(selected, start=1):
                record = behavior_cache[(function_id, item.args)]
                selection_rows.append({
                    "function_id": function_id,
                    "project": function.project,
                    "policy": policy,
                    "rank": rank,
                    "args": list(item.args),
                    "normalized_output": record.normalized_output,
                    "edge_coverage_signature": record.edge_coverage_signature,
                    "trace_hash": record.trace_hash,
                    "origins": list(item.origins),
                    "distance_score": distance_score(item.args, [], [tuple(int(v) for v in row["args"]) for row in fixtures[function_id]]),
                })
    return orders, selection_rows


def select_behavioral_prefix(
    policy: str,
    pool: list[PoolInput],
    behavior_cache: dict[tuple[str, tuple[int, ...]], BehaviorRecord],
    fixture_rows: list[dict[str, Any]],
    max_budget: int = max(BUDGETS),
) -> list[PoolInput]:
    fixtures = [tuple(int(value) for value in row["args"]) for row in fixture_rows]
    candidates = [item for item in pool if not item.is_fixture and behavior_cache.get((item.function_id, item.args), None) is not None]
    selected: list[PoolInput] = []
    seen_outputs: set[int | None] = set()
    seen_edges: set[int] = set()
    seen_traces: set[str] = set()
    while candidates and len(selected) < max_budget:
        best = max(
            candidates,
            key=lambda item: selection_key(policy, item, behavior_cache[(item.function_id, item.args)], selected, fixtures, seen_outputs, seen_edges, seen_traces),
        )
        selected.append(best)
        record = behavior_cache[(best.function_id, best.args)]
        seen_outputs.add(record.normalized_output)
        seen_edges.update(record.edge_set)
        seen_traces.add(record.trace_hash)
        candidates = [item for item in candidates if item.args != best.args]
    return selected


def selection_key(
    policy: str,
    item: PoolInput,
    record: BehaviorRecord,
    selected: list[PoolInput],
    fixtures: list[tuple[int, ...]],
    seen_outputs: set[int | None],
    seen_edges: set[int],
    seen_traces: set[str],
) -> tuple[Any, ...]:
    output_new = int(record.normalized_output not in seen_outputs)
    edge_new = len(set(record.edge_set) - seen_edges)
    trace_new = int(record.trace_hash not in seen_traces)
    distance = 0.0 if policy == "source_behavioral_diversity_no_distance" else distance_score(item.args, [x.args for x in selected], fixtures)
    if policy == "output_diversity_only":
        components = (output_new,)
    elif policy == "coverage_diversity_only":
        components = (edge_new,)
    elif policy == "output_then_coverage":
        components = (output_new, edge_new)
    elif policy == "coverage_then_output":
        components = (edge_new, output_new)
    else:
        components = (output_new, edge_new, trace_new, distance)
    return (*components, -item.canonical_rank)


def distance_score(args: tuple[int, ...], selected: list[tuple[int, ...]], fixtures: list[tuple[int, ...]]) -> float:
    anchors = list(selected) + list(fixtures)
    if not anchors:
        return math.inf
    return float(min(sum(abs(left - right) for left, right in zip(args, anchor)) for anchor in anchors))


def sbdw_budget_curves(
    first_rows: list[dict[str, Any]],
    controlled_population: dict[str, Any],
    natural_population: dict[str, Any],
) -> list[dict[str, Any]]:
    scopes = {
        "controlled_primary_fixture_passing_wrong": controlled_population["sets"]["primary_fixture_passing_wrong"],
        "controlled_low_density_fixture_passing_wrong": controlled_population["sets"]["low_density_fixture_passing_wrong"],
        "controlled_no_mismatch": controlled_population["sets"]["no_mismatch_comparison"],
        "natural_llm_primary_fixture_passing_wrong": natural_population["sets"]["primary_fixture_passing_wrong"],
        "natural_llm_low_density_fixture_passing_wrong": natural_population["sets"]["low_density_fixture_passing_wrong"],
        "natural_llm_no_mismatch": natural_population["sets"]["no_mismatch_comparison"],
    }
    rows: list[dict[str, Any]] = []
    for policy in SBDW_POLICIES:
        for budget in BUDGETS:
            policy_rows = [row for row in first_rows if row["policy"] == policy and int(row["budget"]) == budget]
            for scope, ids in scopes.items():
                rows.append(metric_row(policy, budget, scope, policy_rows, ids))
    rows.extend(reused_phase1_baseline_rows())
    rows.extend(reused_libfuzzer_baseline_rows())
    return rows


def metric_row(policy: str, budget: int, scope: str, rows: list[dict[str, Any]], ids: list[str]) -> dict[str, Any]:
    by_id = {row["candidate_id"]: row for row in rows if row["candidate_id"] in ids}
    detected = [cid for cid, row in by_id.items() if truthy(row.get("detected_in_domain"))]
    ranks = [int(by_id[cid]["first_in_domain_witness_rank"]) for cid in detected if by_id[cid].get("first_in_domain_witness_rank") not in {"", None}]
    unexpected = sum(
        1 for row in rows
        if row["candidate_id"] in ids
        and scope.endswith("no_mismatch")
        and truthy(row.get("detected_in_domain"))
    )
    return {
        "policy": policy,
        "budget": budget,
        "scope": scope,
        "denominator": len(ids),
        "detected": len(detected),
        "detection_rate": safe_div(len(detected), len(ids)),
        "median_first_witness_rank": percentile(ranks, 0.5),
        "unexpected_in_domain_mismatch_count": unexpected,
        "source": "phase2a_sbdw" if policy in SBDW_POLICIES else "reused_phase1",
    }


def reused_phase1_baseline_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    controlled = read_csv(Path("results/decompile_faithfulness/holdout_policy_summary.csv"))
    natural = read_csv(Path("results/decompile_faithfulness/natural_llm_policy_summary.csv"))
    for row in controlled:
        if row["policy"] not in BASELINE_POLICIES:
            continue
        scope = row["scope"]
        if scope == "primary_fixture_passing_wrong":
            out_scope = "controlled_primary_fixture_passing_wrong"
        elif scope == "low_density_fixture_passing_wrong":
            out_scope = "controlled_low_density_fixture_passing_wrong"
        else:
            continue
        rows.append(normalize_baseline_row(row, out_scope))
    for row in natural:
        if row["policy"] not in BASELINE_POLICIES:
            continue
        scope = row["scope"]
        if scope == "primary_fixture_passing_wrong":
            out_scope = "natural_llm_primary_fixture_passing_wrong"
        elif scope == "low_density_fixture_passing_wrong":
            out_scope = "natural_llm_low_density_fixture_passing_wrong"
        else:
            continue
        rows.append(normalize_baseline_row(row, out_scope))
    return rows


def reused_libfuzzer_baseline_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    phase1f = Path("results/decompile_faithfulness/libfuzzer_summary.csv")
    if phase1f.exists():
        for row in read_csv(phase1f):
            if row.get("mode") != "evaluation_count":
                continue
            scope = libfuzzer_scope(row["population"], natural=False)
            if scope:
                rows.append(libfuzzer_budget_row(row, scope, "libfuzzer_eval_count", "reused_phase1f_libfuzzer_eval_count"))
    phase1g = Path("results/decompile_faithfulness/libfuzzer_wallclock_summary.csv")
    if phase1g.exists():
        for row in read_csv(phase1g):
            if str(row.get("wall_clock_budget_s")) != "0.1":
                continue
            scope = libfuzzer_scope(row["population"], natural=False)
            if scope:
                rows.append(libfuzzer_wallclock_row(row, scope, "reused_phase1g_libfuzzer_0.1s_wallclock"))
    phase1h = Path("results/decompile_faithfulness/natural_llm_libfuzzer_summary.csv")
    if phase1h.exists():
        for row in read_csv(phase1h):
            scope = libfuzzer_scope(row["population"], natural=True)
            if not scope:
                continue
            if row.get("mode") == "evaluation_count":
                rows.append(libfuzzer_budget_row(row, scope, "libfuzzer_eval_count", "reused_phase1h_libfuzzer_eval_count"))
            elif row.get("mode") == "wall_clock" and str(row.get("budget_or_time_limit")) == "0.1":
                rows.append(libfuzzer_summary_wallclock_row(row, scope, "reused_phase1h_libfuzzer_0.1s_wallclock"))
    return rows


def libfuzzer_scope(population: str, *, natural: bool) -> str:
    prefix = "natural_llm" if natural else "controlled"
    if population == "primary_fixture_passing_wrong":
        return f"{prefix}_primary_fixture_passing_wrong"
    if population == "low_density_fixture_passing_wrong":
        return f"{prefix}_low_density_fixture_passing_wrong"
    if population == "no_mismatch_comparison":
        return f"{prefix}_no_mismatch"
    return ""


def libfuzzer_budget_row(row: dict[str, str], scope: str, policy: str, source: str) -> dict[str, Any]:
    denominator = int(float(row.get("candidate_denominator", 0) or 0))
    rate = float(row.get("mean_detection", 0.0) or 0.0)
    return {
        "policy": policy,
        "budget": int(float(row["budget_or_time_limit"])),
        "scope": scope,
        "denominator": denominator,
        "detected": rate * denominator,
        "detection_rate": rate,
        "median_first_witness_rank": row.get("median_completed_evaluations", ""),
        "unexpected_in_domain_mismatch_count": row.get("no_mismatch_false_alarms", 0) or 0,
        "source": source,
    }


def libfuzzer_wallclock_row(row: dict[str, str], scope: str, source: str) -> dict[str, Any]:
    denominator = int(float(row.get("candidate_denominator", 0) or 0))
    rate = float(row.get("mean_detection", 0.0) or 0.0)
    return {
        "policy": "libfuzzer_wall_clock_0.1s",
        "budget": 8,
        "scope": scope,
        "denominator": denominator,
        "detected": rate * denominator,
        "detection_rate": rate,
        "median_first_witness_rank": row.get("median_completed_evaluations", ""),
        "unexpected_in_domain_mismatch_count": row.get("no_mismatch_false_alarms", 0) or 0,
        "source": source,
    }


def libfuzzer_summary_wallclock_row(row: dict[str, str], scope: str, source: str) -> dict[str, Any]:
    denominator = int(float(row.get("candidate_denominator", 0) or 0))
    rate = float(row.get("mean_detection", 0.0) or 0.0)
    return {
        "policy": "libfuzzer_wall_clock_0.1s",
        "budget": 8,
        "scope": scope,
        "denominator": denominator,
        "detected": rate * denominator,
        "detection_rate": rate,
        "median_first_witness_rank": row.get("median_completed_evaluations", ""),
        "unexpected_in_domain_mismatch_count": row.get("no_mismatch_false_alarms", 0) or 0,
        "source": source,
    }


def normalize_baseline_row(row: dict[str, str], scope: str) -> dict[str, Any]:
    return {
        "policy": row["policy"],
        "budget": int(float(row["budget"])),
        "scope": scope,
        "denominator": int(float(row["denominator"])),
        "detected": float(row["detected"]),
        "detection_rate": float(row["detection_rate"]),
        "median_first_witness_rank": row.get("median_first_witness_rank", ""),
        "unexpected_in_domain_mismatch_count": row.get("unexpected_in_domain_mismatch_count", 0) or 0,
        "source": "reused_phase1",
    }


def sbdw_ablation_summary(budget_curves: list[dict[str, Any]], first_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for scope in ["controlled_primary_fixture_passing_wrong", "controlled_low_density_fixture_passing_wrong", "natural_llm_primary_fixture_passing_wrong"]:
        for policy in SBDW_POLICIES:
            b8 = metric_lookup(budget_curves, policy, 8, scope)
            rows.append({
                "policy": policy,
                "scope": scope,
                "budget": 8,
                "denominator": b8.get("denominator", 0),
                "detected": b8.get("detected", 0),
                "detection_rate": b8.get("detection_rate", 0.0),
                "median_first_witness_rank": b8.get("median_first_witness_rank", ""),
            })
    return rows


def sbdw_cost_summary(
    *,
    pool_generation_s: float,
    source_execution_s: float,
    selection_s: float,
    instrumentation_compile_s: float = 0.0,
    behavior_cache: dict[tuple[str, tuple[int, ...]], BehaviorRecord],
    traces: list[dict[str, Any]],
    controlled_population: dict[str, Any],
    natural_population: dict[str, Any],
) -> list[dict[str, Any]]:
    source_exec_count = len(behavior_cache)
    candidate_trace_rows = [row for row in traces if row["policy"] == POLICY and int(row["budget"]) == max(BUDGETS)]
    candidate_ids = sorted({row["candidate_id"] for row in candidate_trace_rows})
    per_candidate_times = []
    for cid in candidate_ids:
        times = [float(row.get("elapsed_execution_time_s") or 0.0) for row in candidate_trace_rows if row["candidate_id"] == cid]
        if times:
            per_candidate_times.append(max(times))
    per_candidate_median = float(percentile(per_candidate_times, 0.5) or 0.0)
    source_only_execution_s = max(0.0, source_execution_s - instrumentation_compile_s)
    one_time = pool_generation_s + instrumentation_compile_s + source_only_execution_s + selection_s
    rows = [
        {"cost_type": "source_pool_generation", "candidate_count_per_source": "", "source_execution_count": 0, "elapsed_s": pool_generation_s, "notes": "one_time_source_side"},
        {"cost_type": "source_instrumentation_compile", "candidate_count_per_source": "", "source_execution_count": 0, "elapsed_s": instrumentation_compile_s, "notes": "one_time_source_side"},
        {"cost_type": "source_only_execution", "candidate_count_per_source": "", "source_execution_count": source_exec_count, "elapsed_s": source_only_execution_s, "notes": "one_time_source_side"},
        {"cost_type": "source_only_selection", "candidate_count_per_source": "", "source_execution_count": 0, "elapsed_s": selection_s, "notes": "one_time_source_side"},
        {"cost_type": "per_candidate_audit_execution_median", "candidate_count_per_source": 1, "source_execution_count": 0, "elapsed_s": per_candidate_median, "notes": "candidate_execution_only"},
    ]
    for count in [1, 2, 4, 8, 16]:
        rows.append({
            "cost_type": "amortized_end_to_end",
            "candidate_count_per_source": count,
            "source_execution_count": safe_div(source_exec_count, count),
            "elapsed_s": safe_div(one_time, count) + per_candidate_median,
            "one_time_source_side_elapsed_s": one_time,
            "per_candidate_audit_execution_median_s": per_candidate_median,
            "notes": "source_cost_amortized_plus_one_candidate_audit",
        })
    return rows


def sbdw_candidate_mechanisms(
    *,
    first_rows: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    pools: dict[str, list[PoolInput]],
    behavior_cache: dict[tuple[str, tuple[int, ...]], BehaviorRecord],
    functions: dict[str, he.HoldoutFunction],
    fixtures: dict[str, list[dict[str, Any]]],
    labels: dict[str, dict[str, Any]],
    controlled_population: dict[str, Any],
    natural_population: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    natural_ids = natural_population["sets"]["primary_fixture_passing_wrong"]
    for cid in natural_ids:
        row = next(item for item in first_rows if item["candidate_id"] == cid and item["policy"] == POLICY and int(item["budget"]) == 8)
        function_id = row["function_id"]
        rank_by_policy = selected_rank_by_policy(function_id, [61], traces)
        behavior = behavior_cache.get((function_id, (61,)))
        rows.append({
            "analysis_group": "natural_llm_error",
            "candidate_id": cid,
            "project": row["project"],
            "function_id": function_id,
            "function_name": functions[function_id].function_name,
            "input_61_source_output_class": behavior.normalized_output if behavior else "",
            "input_61_edge_coverage_signature": behavior.edge_coverage_signature if behavior else "",
            "input_61_trace_hash": behavior.trace_hash if behavior else "",
            "selected_rank_input_61_by_policy": json.dumps(rank_by_policy, sort_keys=True),
            "sbdw_detected_b8": truthy(row.get("detected_in_domain")),
            "why_v1_missed": "syntax_conditioned_prefix_did_not_include_input_61_within_B8",
            "selection_cause": natural_selection_cause(rank_by_policy),
            "complete_source_pool_size": len(pools[function_id]),
            "complete_source_pool": json.dumps([list(item.args) for item in pools[function_id]], sort_keys=True),
            "sealed_fixtures": json.dumps([item["args"] for item in fixtures[function_id]], sort_keys=True),
            "mismatch_set_summary": json.dumps(mismatch_set_summary(labels[cid]), sort_keys=True),
        })
    controlled_primary = controlled_population["sets"]["primary_fixture_passing_wrong"]
    sbdw_b8 = detected_ids(first_rows, POLICY, 8, controlled_primary)
    v1_b8 = detected_ids_from_phase1("results/decompile_faithfulness/holdout_first_witness.csv", he.FINAL_POLICY, 8, controlled_primary)
    labels_by_density = {cid: he.density_bucket_for_label(labels[cid]) for cid in controlled_primary if cid in labels}
    for cid in sorted(sbdw_b8):
        witness = first_witness_for(traces, POLICY, 8, cid)
        behavior = behavior_cache.get((witness["function_id"], tuple(witness["input_tuple"]))) if witness else None
        rows.append({
            "analysis_group": "controlled_selected_witness",
            "candidate_id": cid,
            "project": witness.get("project", ""),
            "function_id": witness.get("function_id", ""),
            "function_name": functions[witness["function_id"]].function_name if witness.get("function_id") in functions else "",
            "witness_args": json.dumps(witness.get("input_tuple", "")),
            "witness_rank": witness.get("position", ""),
            "source_behavior_signature": behavior.behavior_signature if behavior else "",
            "source_output_class": behavior.normalized_output if behavior else "",
            "edge_coverage_signature": behavior.edge_coverage_signature if behavior else "",
            "mutation_family": controlled_population["candidate_mutation_family"].get(cid, ""),
            "density_bucket": labels_by_density.get(cid, ""),
            "mismatch_set_summary": json.dumps(mismatch_set_summary(labels[cid]), sort_keys=True),
        })
    for group, ids in [("newly_detected_relative_to_v1", sorted(sbdw_b8 - v1_b8)), ("lost_relative_to_v1", sorted(v1_b8 - sbdw_b8))]:
        for cid in ids:
            witness = first_witness_for(traces, POLICY, 8, cid)
            behavior = behavior_cache.get((witness["function_id"], tuple(witness["input_tuple"]))) if witness else None
            rows.append({
                "analysis_group": group,
                "candidate_id": cid,
                "project": witness.get("project", ""),
                "function_id": witness.get("function_id", ""),
                "function_name": functions[witness["function_id"]].function_name if witness.get("function_id") in functions else "",
                "witness_args": json.dumps(witness.get("input_tuple", "")),
                "witness_rank": witness.get("position", ""),
                "source_behavior_signature": behavior.behavior_signature if behavior else "",
                "source_output_class": behavior.normalized_output if behavior else "",
                "edge_coverage_signature": behavior.edge_coverage_signature if behavior else "",
                "mutation_family": controlled_population["candidate_mutation_family"].get(cid, ""),
                "density_bucket": labels_by_density.get(cid, ""),
                "mismatch_set_summary": json.dumps(mismatch_set_summary(labels[cid]), sort_keys=True),
            })
    for group_name, mapping in [
        ("controlled_result_by_mutation_family", controlled_population["candidate_mutation_family"]),
        ("controlled_result_by_mismatch_density", labels_by_density),
    ]:
        for group_value, ids in sorted(group_by(mapping, controlled_primary).items()):
            detected = sorted(set(ids) & sbdw_b8)
            rows.append({
                "analysis_group": group_name,
                "group": group_value,
                "policy": POLICY,
                "budget": 8,
                "denominator": len(ids),
                "detected": len(detected),
                "detection_rate": safe_div(len(detected), len(ids)),
                "detected_candidate_ids": json.dumps(detected, sort_keys=True),
            })
    return rows


def natural_selection_cause(rank_by_policy: dict[str, int | None]) -> str:
    if rank_by_policy.get("coverage_diversity_only") is not None:
        if rank_by_policy.get("output_diversity_only") is not None:
            return "output_and_coverage_diversity_selected_input_61"
        return "coverage_diversity_selected_input_61"
    if rank_by_policy.get("output_diversity_only") is not None:
        return "output_diversity_selected_input_61_beyond_B8;coverage_only_did_not_select_within_B32"
    if rank_by_policy.get(POLICY) is not None:
        return "combined_sbdw_selected_input_61_beyond_B8"
    return "not_selected_by_sbdw_ablation_prefixes"


def selected_rank_by_policy(function_id: str, args: list[int], traces: list[dict[str, Any]]) -> dict[str, int | None]:
    target = tuple(args)
    result: dict[str, int | None] = {}
    for policy in SBDW_POLICIES:
        positions = [
            int(row["position"]) for row in traces
            if row["function_id"] == function_id
            and row["policy"] == policy
            and int(row["budget"]) == max(BUDGETS)
            and tuple(row["input_tuple"]) == target
        ]
        result[policy] = min(positions) if positions else None
    return result


def first_witness_for(rows: list[dict[str, Any]], policy: str, budget: int, candidate_id: str) -> dict[str, Any]:
    candidates = [
        row for row in rows
        if row["candidate_id"] == candidate_id
        and row["policy"] == policy
        and int(row["budget"]) == budget
        and truthy(row.get("mismatch"))
        and truthy(row.get("in_exact_domain"))
    ]
    if not candidates:
        return {}
    candidates.sort(key=lambda row: int(row["position"]))
    return dict(candidates[0])


def development_gates(budget_curves: list[dict[str, Any]], cost_summary: list[dict[str, Any]], mechanisms: list[dict[str, Any]]) -> dict[str, Any]:
    natural_b8 = metric_lookup(budget_curves, POLICY, 8, "natural_llm_primary_fixture_passing_wrong")
    natural_b4 = metric_lookup(budget_curves, POLICY, 4, "natural_llm_primary_fixture_passing_wrong")
    controlled_b8 = metric_lookup(budget_curves, POLICY, 8, "controlled_primary_fixture_passing_wrong")
    low_b8 = metric_lookup(budget_curves, POLICY, 8, "controlled_low_density_fixture_passing_wrong")
    no_mismatch_unexpected = (
        int(metric_lookup(budget_curves, POLICY, 8, "controlled_no_mismatch").get("unexpected_in_domain_mismatch_count", 0))
        + int(metric_lookup(budget_curves, POLICY, 8, "natural_llm_no_mismatch").get("unexpected_in_domain_mismatch_count", 0))
    )
    generic_b8 = metric_lookup(budget_curves, "generic_type_boundaries", 8, "controlled_primary_fixture_passing_wrong")
    v1_b8 = metric_lookup(budget_curves, he.FINAL_POLICY, 8, "controlled_primary_fixture_passing_wrong")
    sbdw_median = controlled_b8.get("median_first_witness_rank", "")
    v1_median = v1_b8.get("median_first_witness_rank", "")
    amortized8 = next((row for row in cost_summary if row["cost_type"] == "amortized_end_to_end" and int(row["candidate_count_per_source"]) == 8), {})
    minimum = (
        int(natural_b8.get("detected", 0)) >= 2
        and int(controlled_b8.get("detected", 0)) >= 33
        and int(low_b8.get("detected", 0)) >= 14
        and no_mismatch_unexpected == 0
    )
    strong = (
        minimum
        and int(controlled_b8.get("detected", 0)) >= 35
        and int(controlled_b8.get("detected", 0)) >= int(float(generic_b8.get("detected", 0))) + 2
        and comparable_less(sbdw_median, v1_median)
        and int(natural_b4.get("detected", 0)) >= 2
    )
    stop = (
        int(natural_b8.get("detected", 0)) < 2
        or int(controlled_b8.get("detected", 0)) < 33
    )
    if strong:
        outcome = "freeze_sbdw_for_new_holdout"
        recommendation = "freeze SBDW for a new prospective holdout"
    elif stop:
        outcome = "stop_method_redesign"
        recommendation = "stop the method paper or reposition as development characterization"
    else:
        outcome = "revise_design"
        recommendation = "revise design before a new holdout"
    return {
        "minimum_feasibility_gate": minimum,
        "strong_prototype_gate": strong,
        "stop_condition": stop,
        "outcome": outcome,
        "recommendation": recommendation,
        "natural_llm_detected_b8": natural_b8.get("detected", 0),
        "controlled_primary_detected_b8": controlled_b8.get("detected", 0),
        "controlled_low_density_detected_b8": low_b8.get("detected", 0),
        "no_mismatch_unexpected": no_mismatch_unexpected,
        "generic_boundary_detected_b8": generic_b8.get("detected", 0),
        "v1_detected_b8": v1_b8.get("detected", 0),
        "amortized_8_candidate_elapsed_s": amortized8.get("elapsed_s", ""),
    }


def metric_lookup(rows: list[dict[str, Any]], policy: str, budget: int, scope: str) -> dict[str, Any]:
    return next((row for row in rows if row["policy"] == policy and int(row["budget"]) == budget and row["scope"] == scope), {})


def detected_ids(rows: list[dict[str, Any]], policy: str, budget: int, ids: list[str]) -> set[str]:
    return {
        row["candidate_id"] for row in rows
        if row["candidate_id"] in ids
        and row["policy"] == policy
        and int(row["budget"]) == budget
        and truthy(row.get("detected_in_domain"))
    }


def detected_ids_from_phase1(path: str, policy: str, budget: int, ids: list[str]) -> set[str]:
    rows = read_csv(Path(path))
    return {
        row["candidate_id"] for row in rows
        if row["candidate_id"] in ids
        and row["policy"] == policy
        and int(float(row["budget"])) == budget
        and truthy(row.get("detected_in_domain"))
    }


def group_by(mapping: dict[str, str], ids: Iterable[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for cid in ids:
        grouped[mapping.get(cid, "")].append(cid)
    return dict(grouped)


def pool_rows(pools: dict[str, list[PoolInput]], functions: dict[str, he.HoldoutFunction]) -> list[dict[str, Any]]:
    rows = []
    for function_id, items in sorted(pools.items()):
        function = functions[function_id]
        pool_hash = sha256_text(json.dumps([list(item.args) for item in items], sort_keys=True))
        for item in items:
            rows.append({
                "function_id": function_id,
                "project": function.project,
                "function_name": function.function_name,
                "args": list(item.args),
                "canonical_rank": item.canonical_rank,
                "origins": list(item.origins),
                "is_fixture": item.is_fixture,
                "pool_configuration_seed": POOL_SEED,
                "pool_hash": pool_hash,
                "complete_domain_included": function.domain_size <= MAX_SOURCE_POOL,
            })
    return rows


def behavior_cache_rows(
    cache: dict[tuple[str, tuple[int, ...]], BehaviorRecord],
    pools: dict[str, list[PoolInput]],
    functions: dict[str, he.HoldoutFunction],
    instrumentation_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    instrumentation_by_id = {row["function_id"]: row for row in instrumentation_rows}
    rows = []
    for function_id, items in sorted(pools.items()):
        function = functions[function_id]
        cache_key = source_cache_key(function, items)
        if not instrumentation_by_id.get(function_id, {}).get("ok"):
            rows.append({
                "function_id": function_id,
                "project": function.project,
                "cache_key": cache_key,
                "execution_status": instrumentation_by_id.get(function_id, {}).get("reason", "instrumentation_missing"),
            })
            continue
        for item in items:
            record = cache[(function_id, item.args)]
            rows.append({
                "function_id": function_id,
                "project": function.project,
                "function_name": function.function_name,
                "args": list(item.args),
                "normalized_source_output": record.normalized_output,
                "edge_coverage_signature": record.edge_coverage_signature,
                "edge_count": len(record.edge_set),
                "branch_coverage_signature": record.branch_coverage_signature,
                "branch_coverage_available": False,
                "stable_lightweight_trace_hash": record.trace_hash,
                "execution_status": record.execution_status,
                "source_execution_time_s": record.source_execution_time_s,
                "behavior_signature": record.behavior_signature,
                "cache_key": cache_key,
                "instrumentation_version": INSTRUMENTATION_VERSION,
            })
    return rows


def source_cache_key(function: he.HoldoutFunction, pool: list[PoolInput]) -> str:
    payload = {
        "source_function_hash": sha256_text(function.source),
        "build_configuration": BUILD_CONFIG,
        "declared_domain_hash": sha256_text(json.dumps(function.domain_specs, sort_keys=True)),
        "instrumentation_version": INSTRUMENTATION_VERSION,
        "pool_configuration": {
            "seed": POOL_SEED,
            "max_source_pool": MAX_SOURCE_POOL,
            "pool_hash": sha256_text(json.dumps([list(item.args) for item in pool], sort_keys=True)),
        },
    }
    return sha256_text(json.dumps(payload, sort_keys=True))


def behavior_selection_rows(selection_rows: list[dict[str, Any]], cache: dict[tuple[str, tuple[int, ...]], BehaviorRecord]) -> list[dict[str, Any]]:
    return selection_rows


def write_tables(
    repo_root: Path,
    budget_curves: list[dict[str, Any]],
    ablation_summary: list[dict[str, Any]],
    cost_summary: list[dict[str, Any]],
    mechanisms: list[dict[str, Any]],
) -> None:
    table_dir = repo_root / "paper/tables"
    main_rows = []
    for scope in ["controlled_primary_fixture_passing_wrong", "natural_llm_primary_fixture_passing_wrong"]:
        for budget in BUDGETS:
            row = metric_lookup(budget_curves, POLICY, budget, scope)
            main_rows.append([scope, budget, row.get("denominator", 0), row.get("detected", 0), fmt_rate(row.get("detection_rate", 0))])
    write_latex_table(table_dir / "sbdw_development_results.tex", "SBDW development results", ["Scope", "B", "Denom.", "Detected", "Detection"], main_rows)
    write_latex_table(
        table_dir / "sbdw_ablation.tex",
        "SBDW ablations at B=8",
        ["Policy", "Scope", "Detected", "Denom.", "Detection"],
        [[row["policy"], row["scope"], row["detected"], row["denominator"], fmt_rate(row["detection_rate"])] for row in ablation_summary],
    )
    write_latex_table(
        table_dir / "sbdw_cost.tex",
        "SBDW cost accounting",
        ["Cost", "Candidates/source", "Source exec.", "Seconds"],
        [[row["cost_type"], row["candidate_count_per_source"], row["source_execution_count"], f"{float(row['elapsed_s']):.4f}"] for row in cost_summary],
    )
    natural = [row for row in mechanisms if row["analysis_group"] == "natural_llm_error"]
    write_latex_table(
        table_dir / "sbdw_natural_cases.tex",
        "SBDW natural LLM cases",
        ["Candidate", "Function", "Output@61", "SBDW B8", "Ranks"],
        [[row["candidate_id"], row["function_name"], row["input_61_source_output_class"], row["sbdw_detected_b8"], row["selected_rank_input_61_by_policy"]] for row in natural],
    )


def write_latex_table(path: Path, caption: str, headers: list[str], rows: list[list[Any]]) -> None:
    lines = ["\\begin{table}[t]", "\\centering", "\\small", "\\begin{tabular}{" + "l" * len(headers) + "}", "\\toprule", " & ".join(headers) + " \\\\", "\\midrule"]
    for row in rows:
        lines.append(" & ".join(latex_escape(value) for value in row) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", f"\\caption{{{latex_escape(caption)}}}", "\\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_plot_script(repo_root: Path) -> None:
    path = repo_root / "figures/plot_sbdw.py"
    path.write_text(
        '''from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "figures/data"


def rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def plot_budget() -> None:
    data = [row for row in rows("sbdw_budget_curves.csv") if row["scope"] in {"controlled_primary_fixture_passing_wrong", "natural_llm_primary_fixture_passing_wrong"} and row["policy"] in {"source_behavioral_diversity", "source_literal_char_interleave", "generic_type_boundaries"}]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for key in sorted({(row["scope"], row["policy"]) for row in data}):
        series = sorted([row for row in data if (row["scope"], row["policy"]) == key], key=lambda row: int(row["budget"]))
        ax.plot([int(row["budget"]) for row in series], [float(row["detection_rate"]) for row in series], marker="o", linewidth=1.2, label=key[0].replace("_fixture_passing_wrong", "") + ":" + key[1])
    ax.set_xlabel("Budget")
    ax.set_ylabel("Detection")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/sbdw_budget_curves.pdf")


def plot_cost() -> None:
    data = rows("sbdw_cost_amortization.csv")
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    ax.plot([int(row["candidate_count_per_source"]) for row in data], [float(row["elapsed_s"]) for row in data], marker="o")
    ax.set_xlabel("Candidates per source")
    ax.set_ylabel("Amortized seconds")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/sbdw_cost_amortization.pdf")


def plot_behavior() -> None:
    data = [row for row in rows("sbdw_behavior_selection.csv") if row["policy"] == "source_behavioral_diversity"]
    counts = {}
    for row in data:
        key = str(row["normalized_output"])
        counts[key] = counts.get(key, 0) + 1
    top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:20]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.bar([item[0] for item in top], [item[1] for item in top])
    ax.set_xlabel("Selected source output class")
    ax.set_ylabel("Selected probes")
    ax.tick_params(axis="x", labelrotation=45)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/sbdw_behavior_selection.pdf")


if __name__ == "__main__":
    plot_budget()
    plot_cost()
    plot_behavior()
''',
        encoding="utf-8",
    )


def generate_figures(repo_root: Path) -> None:
    result = subprocess.run([sys.executable, str(repo_root / "figures/plot_sbdw.py")], cwd=repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def write_handoff(
    repo_root: Path,
    instrumentation_rows: list[dict[str, Any]],
    budget_curves: list[dict[str, Any]],
    ablation_summary: list[dict[str, Any]],
    cost_summary: list[dict[str, Any]],
    mechanisms: list[dict[str, Any]],
    gates: dict[str, Any],
) -> Path:
    path = repo_root / "docs/paper_agent/source_behavioral_diversity_handoff.md"
    controlled = [metric_lookup(budget_curves, POLICY, budget, "controlled_primary_fixture_passing_wrong") for budget in BUDGETS]
    natural = [metric_lookup(budget_curves, POLICY, budget, "natural_llm_primary_fixture_passing_wrong") for budget in [1, 2, 4, 8]]
    low = [metric_lookup(budget_curves, POLICY, budget, "controlled_low_density_fixture_passing_wrong") for budget in BUDGETS]
    unsupported = [row for row in instrumentation_rows if not row["ok"]]
    lines = [
        "# Source-Behavioral Diversity Handoff",
        "",
        "## Git",
        "",
        f"- Branch: `{git_output(repo_root, ['branch', '--show-current'])}`",
        f"- Preregistration commit: `{git_output(repo_root, ['rev-parse', PREREG_COMMIT_ABBREV])}`",
        "- Result commit and HEAD: the commit containing this handoff.",
        f"- Phase 1h starting HEAD: `{PHASE1H_HEAD}`",
        f"- Development baseline method freeze commit: `{METHOD_FREEZE_COMMIT}`",
        "",
        "## Instrumentation",
        "",
        f"- Implementation: `{INSTRUMENTATION_VERSION}` via clang trace-pc-guard over trusted source only.",
        f"- Supported source-function count: `{sum(1 for row in instrumentation_rows if row['ok'])}`",
        f"- Unsupported functions and reasons: `{json.dumps({row['function_id']: row['reason'] for row in unsupported}, sort_keys=True)}`",
        "- Local GPU usage: `none`; subprocesses clear `CUDA_VISIBLE_DEVICES`.",
        "",
        "## Detection",
        "",
        f"- Natural LLM Detection@1/2/4/8: `{[(row.get('detected', 0), row.get('denominator', 0)) for row in natural]}`",
        f"- Controlled Detection@1/2/4/8/16/32: `{[(row.get('detected', 0), row.get('denominator', 0)) for row in controlled]}`",
        f"- Controlled low-density Detection: `{[(row.get('detected', 0), row.get('denominator', 0)) for row in low]}`",
        f"- No-mismatch unexpected mismatches: `{gates['no_mismatch_unexpected']}`",
        f"- v1 delta at B=8: `{int(metric_lookup(budget_curves, POLICY, 8, 'controlled_primary_fixture_passing_wrong').get('detected', 0)) - int(float(metric_lookup(budget_curves, he.FINAL_POLICY, 8, 'controlled_primary_fixture_passing_wrong').get('detected', 0)))}`",
        f"- Generic-boundary delta at B=8: `{int(metric_lookup(budget_curves, POLICY, 8, 'controlled_primary_fixture_passing_wrong').get('detected', 0)) - int(float(metric_lookup(budget_curves, 'generic_type_boundaries', 8, 'controlled_primary_fixture_passing_wrong').get('detected', 0)))}`",
        f"- libFuzzer eval-count B=8 controlled primary: `{float(metric_lookup(budget_curves, 'libfuzzer_eval_count', 8, 'controlled_primary_fixture_passing_wrong').get('detection_rate', 0.0)):.3f}`",
        f"- libFuzzer 0.1s wall-clock controlled primary: `{float(metric_lookup(budget_curves, 'libfuzzer_wall_clock_0.1s', 8, 'controlled_primary_fixture_passing_wrong').get('detection_rate', 0.0)):.3f}`",
        f"- libFuzzer eval-count B=8 natural LLM primary: `{float(metric_lookup(budget_curves, 'libfuzzer_eval_count', 8, 'natural_llm_primary_fixture_passing_wrong').get('detection_rate', 0.0)):.3f}`",
        f"- libFuzzer 0.1s wall-clock natural LLM primary: `{float(metric_lookup(budget_curves, 'libfuzzer_wall_clock_0.1s', 8, 'natural_llm_primary_fixture_passing_wrong').get('detection_rate', 0.0)):.3f}`",
        "",
        "## Costs",
        "",
    ]
    for row in cost_summary:
        lines.append(f"- {row['cost_type']} candidates/source={row['candidate_count_per_source']}: `{float(row['elapsed_s']):.6f}` seconds; source executions `{row['source_execution_count']}`")
    lines.extend([
        "",
        "## Ablations",
        "",
    ])
    for row in ablation_summary:
        if row["scope"] in {"controlled_primary_fixture_passing_wrong", "natural_llm_primary_fixture_passing_wrong"}:
            lines.append(f"- {row['policy']} {row['scope']} B=8: `{row['detected']}/{row['denominator']}` = `{float(row['detection_rate']):.3f}`")
    lines.extend([
        "",
        "## Natural Cases",
        "",
    ])
    for row in [item for item in mechanisms if item["analysis_group"] == "natural_llm_error"]:
        lines.append(f"- `{row['candidate_id']}` input 61 output `{row['input_61_source_output_class']}`, ranks `{row['selected_rank_input_61_by_policy']}`, SBDW B8 `{row['sbdw_detected_b8']}`")
    lines.extend([
        "",
        "## Development Gate",
        "",
        f"- Outcome: `{gates['outcome']}`",
        f"- Minimum feasibility gate: `{gates['minimum_feasibility_gate']}`",
        f"- Strong prototype gate: `{gates['strong_prototype_gate']}`",
        f"- Stop condition: `{gates['stop_condition']}`",
        f"- Exact recommendation: {gates['recommendation']}.",
        "",
        "This Phase 2a prototype used Phase 1 data only as development data and did not start a new prospective holdout.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_blocker_handoff(repo_root: Path, instrumentation_rows: list[dict[str, Any]]) -> Path:
    path = repo_root / "docs/paper_agent/source_behavioral_diversity_handoff.md"
    unsupported = {row["function_id"]: row["reason"] for row in instrumentation_rows if not row["ok"]}
    path.write_text(
        "\n".join([
            "# Source-Behavioral Diversity Handoff",
            "",
            "Phase 2a stopped before candidate evaluation because source edge instrumentation was unreliable.",
            "",
            f"- Branch: `{git_output(repo_root, ['branch', '--show-current'])}`",
            f"- Preregistration commit: `{git_output(repo_root, ['rev-parse', PREREG_COMMIT_ABBREV])}`",
            f"- Unsupported functions and reasons: `{json.dumps(unsupported, sort_keys=True)}`",
            "- Exact recommendation: stop and repair source instrumentation before any SBDW claims.",
            "",
        ]),
        encoding="utf-8",
    )
    return path


def tag_population(rows: list[dict[str, Any]], population_kind: str) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        item = dict(row)
        item["development_population"] = population_kind
        result.append(item)
    return result


def mismatch_set_summary(label: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_mismatching_input_count": label.get("total_mismatching_input_count", 0),
        "exact_domain_size": label.get("exact_domain_size", 0),
        "first_mismatch": label.get("first_mismatch", ""),
        "complete_mismatch_set_sha256": label.get("complete_mismatch_set_sha256", ""),
    }


def comparable_less(left: Any, right: Any) -> bool:
    try:
        return float(left) < float(right)
    except (TypeError, ValueError):
        return False


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in {"True", "true", "1", 1}:
        return True
    return False


def percentile(values: Iterable[Any], q: float) -> float | str:
    numbers = sorted(float(value) for value in values if value not in {"", None})
    if not numbers:
        return ""
    if len(numbers) == 1:
        return numbers[0]
    pos = q * (len(numbers) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(numbers) - 1)
    frac = pos - lo
    return numbers[lo] * (1 - frac) + numbers[hi] * frac


def safe_div(left: float, right: float) -> float:
    return 0.0 if not right else float(left) / float(right)


def stable_seed(*parts: Any) -> int:
    return int(sha256_text(json.dumps(parts, sort_keys=True))[:16], 16)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fmt_rate(value: Any) -> str:
    return f"{float(value):.3f}"


def latex_escape(value: Any) -> str:
    return str(value).replace("\\", "\\textbackslash{}").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#").replace("{", "\\{").replace("}", "\\}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def git_output(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


if __name__ == "__main__":
    main()
