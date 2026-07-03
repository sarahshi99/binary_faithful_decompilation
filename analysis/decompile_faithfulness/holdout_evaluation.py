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
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import dynamic_trace
from analysis.decompile_faithfulness import fixtures
from analysis.decompile_faithfulness import run_phase5b_hard_candidates as phase5b


METHOD_FREEZE_COMMIT = "06dda89912103b94fc065d6f073581a7811154b1"
PHASE1D_FINAL_HEAD = "ef2d721202d19f8aed55ac10db6e96b6770a722c"
EXPECTED_HOLDOUT_SEAL = "cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42"
FINAL_POLICY = "source_literal_char_interleave"
PREREG_PATH = Path("docs/paper_agent/frozen_holdout_evaluation_preregistration.md")
SEALED_MANIFEST_PATH = Path("analysis/decompile_faithfulness/holdout_sealed_manifest_v2.json")
PREFLIGHT_PATH = Path("results/decompile_faithfulness/holdout_evaluation_preflight.json")
WORK_DIR = Path("analysis_outputs/decompile_faithfulness/holdout_phase1e")
BUDGETS = [1, 2, 4, 8, 16, 32]
RANDOM_SEEDS = [
    101, 202, 303, 404, 505, 606, 707, 808, 909, 1001,
    1102, 1203, 1304, 1405, 1506, 1607, 1708, 1809, 1910, 2011,
    2112, 2213, 2314, 2415, 2516, 2617, 2718, 2819, 2920, 3021,
]
DETERMINISTIC_POLICIES = [
    FINAL_POLICY,
    "fixture_neighbor_only",
    "source_literal_only",
    "neighbor_first_concatenation",
    "literal_first_concatenation",
    "operator_char_first",
    "generic_fallback_only",
    "generic_type_boundaries",
]
RANDOM_POLICIES = ["uniform_random_domain", "randomized_union_order"]
GENERIC_TYPE_BOUNDARIES_CHAR = [0, 1, 31, 32, 47, 48, 57, 64, 65, 90, 97, 122, 127]
GENERIC_TYPE_BOUNDARIES_SIGNED = [-32, -1, 0, 1, 31]
GENERIC_TYPE_BOUNDARIES_UNSIGNED = [0, 1, 63]


@dataclass(frozen=True)
class HoldoutFunction:
    function_id: str
    project: str
    source_file: str
    function_name: str
    signature: str
    domain_specs: tuple[dict[str, Any], ...]
    domain: tuple[tuple[int, ...], ...]
    domain_size: int
    source: str
    source_literal_count: int


@dataclass(frozen=True)
class CandidateRecord:
    candidate_id: str
    function_id: str
    project: str
    candidate_stratum: str
    candidate_class: str
    label: str
    compile_status: str
    execution_status: str
    mutation_family: str
    source_path: Path
    total_mismatching_input_count: int
    exact_domain_size: int


@dataclass(frozen=True)
class PolicyProbe:
    args: tuple[int, ...]
    bucket: str
    source_literal_derived: bool = False
    fixture_neighbor_derived: bool = False
    generic_fallback_derived: bool = False
    operator_char_derived: bool = False
    generic_type_boundary_derived: bool = False
    duplicate_sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    outputs: tuple[int, ...]
    reason: str
    elapsed_s: float
    source_path: str
    stderr_tail: str = ""


def main() -> None:
    args = parse_args()
    summary = run(args.repo_root.resolve())
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args()


def run(repo_root: Path) -> dict[str, Any]:
    out = repo_root / "results/decompile_faithfulness"
    fig_data = repo_root / "figures/data"
    fig_dir = repo_root / "figures"
    table_dir = repo_root / "paper/tables"
    docs_dir = repo_root / "docs/paper_agent"
    work = repo_root / WORK_DIR
    for path in [out, fig_data, fig_dir, table_dir, docs_dir, work]:
        path.mkdir(parents=True, exist_ok=True)

    preflight = run_preflight(repo_root)
    if not preflight["ok"]:
        raise RuntimeError("holdout evaluation preflight failed")

    functions = load_functions(repo_root)
    candidates = load_candidates(repo_root)
    labels = {row["candidate_id"]: row for row in read_jsonl(repo_root / "results/decompile_faithfulness/holdout_exact_labels.jsonl")}
    fixtures_by_function = load_fixtures(repo_root)

    compile_ready = [
        candidate for candidate in candidates
        if candidate.compile_status == "compile_ready"
        and candidate.label in {"semantic_wrong", "no_mismatch_under_exact_holdout_domain"}
    ]
    controlled_compile_ready = [candidate for candidate in compile_ready if candidate.candidate_stratum == "controlled_stress"]
    fixture_replay = replay_fixtures(repo_root, functions, controlled_compile_ready, fixtures_by_function, work / "fixture_replay")
    write_jsonl(out / "holdout_fixture_replay.jsonl", fixture_replay)
    fixture_summary = summarize_fixture_replay(fixture_replay, functions, labels)
    write_csv(out / "holdout_fixture_replay_summary.csv", fixture_summary)

    population = build_population(candidates, labels, fixture_replay, functions)
    policy_orders, generation_times = build_all_policy_orders(functions, fixtures_by_function)
    traces, first_witness_rows, unexpected_rows = evaluate_policies(
        repo_root=repo_root,
        functions=functions,
        candidates=compile_ready,
        labels=labels,
        population=population,
        policy_orders=policy_orders,
        generation_times=generation_times,
        work_dir=work / "policy_execution",
    )
    write_jsonl(out / "holdout_policy_traces.jsonl", traces)
    write_csv(out / "holdout_first_witness.csv", first_witness_rows)
    write_jsonl(out / "holdout_unexpected_mismatches.jsonl", unexpected_rows)

    policy_summary, budget_curves, random_seed_summary = summarize_policy_results(
        traces=traces,
        first_witness_rows=first_witness_rows,
        population=population,
    )
    write_csv(out / "holdout_policy_summary.csv", policy_summary)
    write_csv(out / "holdout_budget_curves.csv", budget_curves)
    write_csv(out / "holdout_random_seed_summary.csv", random_seed_summary)
    write_csv(fig_data / "holdout_budget_curves.csv", budget_curves)

    stratified = stratified_results(
        functions=functions,
        candidates=compile_ready,
        labels=labels,
        population=population,
        first_witness_rows=first_witness_rows,
    )
    write_csv(out / "holdout_stratified_results.csv", stratified)
    density_rows = density_results(population, first_witness_rows)
    write_csv(fig_data / "holdout_density_results.csv", density_rows)
    ecdf_rows = first_witness_ecdf(first_witness_rows, population)
    write_csv(fig_data / "holdout_first_witness_ecdf.csv", ecdf_rows)

    comparisons = statistical_comparisons(population, first_witness_rows)
    write_json(out / "holdout_statistical_comparisons.json", comparisons)

    write_tables(repo_root, policy_summary, stratified, population, unexpected_rows)
    write_plot_script(repo_root)
    generate_figures(repo_root)
    gate = interpretation_gate(policy_summary, first_witness_rows, population, unexpected_rows)
    handoff = write_handoff(
        repo_root=repo_root,
        preflight=preflight,
        population=population,
        policy_summary=policy_summary,
        stratified=stratified,
        first_witness_rows=first_witness_rows,
        unexpected_rows=unexpected_rows,
        gate=gate,
    )
    return {
        "status": "completed",
        "preflight_ok": preflight["ok"],
        "fixture_passing_wrong_count": population["counts"]["primary_fixture_passing_wrong"],
        "low_density_fixture_passing_wrong_count": population["counts"]["low_density_fixture_passing_wrong"],
        "trace_rows": len(traces),
        "unexpected_mismatches": len(unexpected_rows),
        "gate": gate["outcome"],
        "handoff": str(handoff.relative_to(repo_root)),
    }


def run_preflight(repo_root: Path) -> dict[str, Any]:
    manifest_path = repo_root / SEALED_MANIFEST_PATH
    manifest_sha = sha256_path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_checks = verify_sealed_artifacts(repo_root, manifest)
    method_checks = verify_method_hashes(repo_root, manifest)
    current_commit = git_output(repo_root, ["rev-parse", "HEAD"])
    gcc_version = ccompile.run_command(["/usr/bin/gcc", "--version"]).stdout.splitlines()[0]
    payload = {
        "created_at_utc": now_utc(),
        "current_result_producing_commit": current_commit,
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "expected_holdout_seal": EXPECTED_HOLDOUT_SEAL,
        "holdout_manifest_sha256": manifest_sha,
        "holdout_manifest_sha256_matches_expected": manifest_sha == EXPECTED_HOLDOUT_SEAL,
        "sealed_artifact_checks": artifact_checks,
        "method_hash_checks": method_checks,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "gcc": gcc_version,
            "cwd": str(repo_root),
        },
    }
    payload["ok"] = (
        payload["holdout_manifest_sha256_matches_expected"]
        and artifact_checks["all_ok"]
        and method_checks["all_ok"]
    )
    write_json(repo_root / PREFLIGHT_PATH, payload)
    return payload


def verify_sealed_artifacts(repo_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    all_ok = True
    for rel, expected in sorted(manifest.get("artifact_hashes", {}).items()):
        path = repo_root / rel
        if expected.get("type") == "file":
            current = sha256_path(path) if path.exists() else ""
            ok = path.exists() and current == expected.get("sha256")
            checks.append({"path": rel, "type": "file", "ok": ok, "expected_sha256": expected.get("sha256", ""), "current_sha256": current})
            all_ok = all_ok and ok
        elif expected.get("type") == "directory":
            current_dir = directory_hash(path) if path.exists() else {"file_count": 0, "tree_sha256": "", "files": []}
            ok = (
                path.exists()
                and current_dir["file_count"] == expected.get("file_count")
                and current_dir["tree_sha256"] == expected.get("tree_sha256")
            )
            if ok:
                expected_files = {item["path"]: item["sha256"] for item in expected.get("files", [])}
                current_files = {item["path"]: item["sha256"] for item in current_dir.get("files", [])}
                ok = expected_files == current_files
            checks.append({
                "path": rel,
                "type": "directory",
                "ok": ok,
                "expected_file_count": expected.get("file_count"),
                "current_file_count": current_dir["file_count"],
                "expected_tree_sha256": expected.get("tree_sha256", ""),
                "current_tree_sha256": current_dir["tree_sha256"],
            })
            all_ok = all_ok and ok
    return {"all_ok": all_ok, "checked_count": len(checks), "checks": checks}


def verify_method_hashes(repo_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    sources = []
    all_ok = True
    for item in manifest.get("method_affecting_hashes_unchanged", {}).get("sources", []):
        path = repo_root / item["path"]
        current = sha256_path(path) if path.exists() else ""
        ok = path.exists() and current == item.get("method_freeze_sha256")
        all_ok = all_ok and ok
        sources.append({
            "path": item["path"],
            "method_freeze_sha256": item.get("method_freeze_sha256", ""),
            "current_sha256": current,
            "ok": ok,
        })
    return {"all_ok": all_ok, "checked_count": len(sources), "sources": sources}


def load_functions(repo_root: Path) -> dict[str, HoldoutFunction]:
    selected = read_csv(repo_root / "results/decompile_faithfulness/holdout_selected_functions.csv")
    candidates = read_jsonl(repo_root / "results/decompile_faithfulness/holdout_candidate_manifest.jsonl")
    source_by_function: dict[str, str] = {}
    for row in candidates:
        path_text = row.get("original_source_function_path")
        if path_text and row.get("function_id") not in source_by_function:
            source_by_function[str(row["function_id"])] = Path(path_text).read_text(encoding="utf-8")
    descriptive = json.loads((repo_root / "results/decompile_faithfulness/holdout_pre_auditor_descriptive_analysis.json").read_text(encoding="utf-8"))
    literal_counts = descriptive.get("source_character_literal_prevalence", {}).get("per_function", {})
    functions: dict[str, HoldoutFunction] = {}
    for row in selected:
        domain_specs = tuple(json.loads(row["declared_exact_domain"]))
        domain = tuple(tuple(int(value) for value in values) for values in itertools.product(*[spec["values"] for spec in domain_specs]))
        function_id = row["function_id"]
        functions[function_id] = HoldoutFunction(
            function_id=function_id,
            project=row["project"],
            source_file=row["source_file"],
            function_name=row["function_name"],
            signature=row["signature"],
            domain_specs=domain_specs,
            domain=domain,
            domain_size=int(row["domain_size"]),
            source=source_by_function[function_id],
            source_literal_count=int(literal_counts.get(function_id, 0)),
        )
    return functions


def load_candidates(repo_root: Path) -> list[CandidateRecord]:
    rows = read_jsonl(repo_root / "results/decompile_faithfulness/holdout_candidate_manifest.jsonl")
    candidates: list[CandidateRecord] = []
    for row in rows:
        source_path = row.get("candidate_source_path") or row.get("normalized_candidate_path") or ""
        candidates.append(
            CandidateRecord(
                candidate_id=str(row["candidate_id"]),
                function_id=str(row["function_id"]),
                project=str(row["project"]),
                candidate_stratum=str(row["candidate_stratum"]),
                candidate_class=str(row.get("candidate_class", "")),
                label=str(row["label"]),
                compile_status=str(row.get("compile_status", "")),
                execution_status=str(row.get("execution_status", "")),
                mutation_family=str(row.get("mutation_family", "natural_ghidra")),
                source_path=Path(source_path),
                total_mismatching_input_count=int(row.get("total_mismatching_input_count", 0)),
                exact_domain_size=int(row.get("exact_domain_size", 0)),
            )
        )
    return candidates


def load_fixtures(repo_root: Path) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(repo_root / "results/decompile_faithfulness/holdout_fixtures.jsonl"):
        grouped[str(row["function_id"])].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda item: int(item["rank"]))
    return dict(grouped)


def replay_fixtures(
    repo_root: Path,
    functions: dict[str, HoldoutFunction],
    candidates: list[CandidateRecord],
    fixtures_by_function: dict[str, list[dict[str, Any]]],
    output_dir: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_cache: dict[str, ExecutionResult] = {}
    for candidate in candidates:
        function = functions[candidate.function_id]
        fixture_rows = fixtures_by_function[function.function_id]
        args = [tuple(int(value) for value in row["args"]) for row in fixture_rows]
        if function.function_id not in source_cache:
            source_cache[function.function_id] = execute_inputs(function, function.source, args, output_dir, "trusted_source_fixture_replay")
        source_run = source_cache[function.function_id]
        candidate_source = candidate.source_path.read_text(encoding="utf-8")
        candidate_run = execute_inputs(function, candidate_source, args, output_dir, candidate.candidate_id)
        agreement = 0
        first_mismatch = None
        if source_run.ok and candidate_run.ok:
            for index, (fixture, left, right) in enumerate(zip(fixture_rows, source_run.outputs, candidate_run.outputs), start=1):
                if left == right:
                    agreement += 1
                elif first_mismatch is None:
                    first_mismatch = {"rank": index, "args": fixture["args"], "source_output": left, "candidate_output": right}
        status = "ok" if source_run.ok and candidate_run.ok else f"source:{source_run.reason};candidate:{candidate_run.reason}"
        rows.append({
            "candidate_id": candidate.candidate_id,
            "function_id": candidate.function_id,
            "project": candidate.project,
            "candidate_stratum": candidate.candidate_stratum,
            "label": candidate.label,
            "mutation_family": candidate.mutation_family,
            "fixture_count": len(fixture_rows),
            "fixture_agreement_count": agreement,
            "fixture_pass": bool(source_run.ok and candidate_run.ok and agreement == len(fixture_rows)),
            "first_fixture_mismatch": first_mismatch,
            "execution_status": status,
        })
    return rows


def summarize_fixture_replay(
    replay_rows: list[dict[str, Any]],
    functions: dict[str, HoldoutFunction],
    labels: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in replay_rows:
        label = row["label"]
        groups[("label", label)].append(row)
        groups[("project", row["project"])].append(row)
        groups[("mutation_family", row["mutation_family"])].append(row)
        density_bucket = density_bucket_for_label(labels[row["candidate_id"]])
        groups[("mismatch_density_bucket", density_bucket)].append(row)
        source_bucket = "has_source_char_literal" if functions[row["function_id"]].source_literal_count > 0 else "no_source_char_literal"
        groups[("source_literal_availability", source_bucket)].append(row)
    return [
        {
            "group_type": group_type,
            "group": group,
            "candidate_count": len(rows),
            "fixture_pass_count": sum(1 for row in rows if row["fixture_pass"]),
            "fixture_fail_count": sum(1 for row in rows if not row["fixture_pass"]),
        }
        for (group_type, group), rows in sorted(groups.items())
    ]


def build_population(
    candidates: list[CandidateRecord],
    labels: dict[str, dict[str, Any]],
    fixture_replay: list[dict[str, Any]],
    functions: dict[str, HoldoutFunction],
) -> dict[str, Any]:
    replay_by_id = {row["candidate_id"]: row for row in fixture_replay}
    natural_no_mismatch = [
        c.candidate_id for c in candidates
        if c.candidate_stratum == "natural_ghidra"
        and c.compile_status == "compile_ready"
        and c.label == "no_mismatch_under_exact_holdout_domain"
    ]
    controlled_no_mismatch = [
        c.candidate_id for c in candidates
        if c.candidate_stratum == "controlled_stress"
        and c.compile_status == "compile_ready"
        and c.label == "no_mismatch_under_exact_holdout_domain"
    ]
    all_wrong = [
        c.candidate_id for c in candidates
        if c.candidate_stratum == "controlled_stress"
        and c.compile_status == "compile_ready"
        and c.label == "semantic_wrong"
    ]
    primary = [
        cid for cid in all_wrong
        if replay_by_id.get(cid, {}).get("fixture_pass")
    ]
    low_density = [
        cid for cid in primary
        if mismatch_density(labels[cid]) <= 0.10
    ]
    no_mismatch = natural_no_mismatch + controlled_no_mismatch
    candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    return {
        "sets": {
            "natural_ghidra_no_mismatch": natural_no_mismatch,
            "controlled_no_mismatch": controlled_no_mismatch,
            "all_controlled_semantic_wrong": all_wrong,
            "primary_fixture_passing_wrong": primary,
            "low_density_fixture_passing_wrong": low_density,
            "no_mismatch_comparison": no_mismatch,
        },
        "counts": {
            "natural_ghidra_no_mismatch": len(natural_no_mismatch),
            "controlled_no_mismatch": len(controlled_no_mismatch),
            "all_controlled_semantic_wrong": len(all_wrong),
            "primary_fixture_passing_wrong": len(primary),
            "low_density_fixture_passing_wrong": len(low_density),
            "no_mismatch_comparison": len(no_mismatch),
        },
        "candidate_project": {cid: candidates_by_id[cid].project for cid in candidates_by_id},
        "candidate_function": {cid: candidates_by_id[cid].function_id for cid in candidates_by_id},
        "candidate_mutation_family": {cid: candidates_by_id[cid].mutation_family for cid in candidates_by_id},
        "candidate_source_literal_availability": {
            cid: ("has_source_char_literal" if functions[candidates_by_id[cid].function_id].source_literal_count > 0 else "no_source_char_literal")
            for cid in candidates_by_id
        },
    }


def build_all_policy_orders(
    functions: dict[str, HoldoutFunction],
    fixtures_by_function: dict[str, list[dict[str, Any]]],
) -> tuple[dict[tuple[str, str, int | None], list[PolicyProbe]], dict[tuple[str, str, int | None], float]]:
    orders: dict[tuple[str, str, int | None], list[PolicyProbe]] = {}
    generation_times: dict[tuple[str, str, int | None], float] = {}
    for function in functions.values():
        entry, case = frozen_entry_and_case(function, fixtures_by_function[function.function_id])
        for policy in DETERMINISTIC_POLICIES:
            started = time.perf_counter()
            probes = build_policy_order(policy, entry, case, function, seed=None)
            generation_times[(function.function_id, policy, None)] = time.perf_counter() - started
            orders[(function.function_id, policy, None)] = probes
        for policy in RANDOM_POLICIES:
            for seed in RANDOM_SEEDS:
                started = time.perf_counter()
                probes = build_policy_order(policy, entry, case, function, seed=seed)
                generation_times[(function.function_id, policy, seed)] = time.perf_counter() - started
                orders[(function.function_id, policy, seed)] = probes
    return orders, generation_times


def frozen_entry_and_case(
    function: HoldoutFunction,
    fixture_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], fixtures.FunctionCase]:
    tests = tuple(
        fixtures.FunctionTest(tuple(int(value) for value in row["args"]), int(row["source_output"]))
        for row in fixture_rows
    )
    fixture_dicts = [
        {"args": list(test.args), "expected": test.expected}
        for test in tests
    ]
    entry = {
        "case_id": function.function_id,
        "function_name": function.function_name,
        "signature": function.signature,
        "fixtures": fixture_dicts,
    }
    case = fixtures.FunctionCase(function.function_id, function.function_name, function.source, tests)
    return entry, case


def build_policy_order(
    policy: str,
    entry: dict[str, Any],
    case: fixtures.FunctionCase,
    function: HoldoutFunction,
    seed: int | None,
) -> list[PolicyProbe]:
    from analysis.decompile_faithfulness import run_phase11_input_ordering as phase11

    if policy == FINAL_POLICY:
        frozen = phase11.build_ordered_inputs(entry, case, FINAL_POLICY, max_inputs=max(BUDGETS))
        provenance = component_provenance(entry, case)
        return [probe_from_trace_input(item, provenance) for item in frozen]
    if policy == "fixture_neighbor_only":
        return wrap_trace_inputs(phase11.fixture_neighbor_inputs(entry), component_provenance(entry, case))
    if policy == "source_literal_only":
        return wrap_trace_inputs(phase11.source_literal_char_inputs(entry, case), component_provenance(entry, case))
    if policy == "neighbor_first_concatenation":
        inputs = phase11.dedupe_inputs(
            phase11.fixture_neighbor_inputs(entry)
            + phase11.source_literal_char_inputs(entry, case)
            + phase5b.phase5b_hard_trace_inputs(entry, max_inputs=10_000)
        )
        return wrap_trace_inputs(inputs, component_provenance(entry, case))
    if policy == "literal_first_concatenation":
        inputs = phase11.dedupe_inputs(
            phase11.source_literal_char_inputs(entry, case)
            + phase11.fixture_neighbor_inputs(entry)
            + phase5b.phase5b_hard_trace_inputs(entry, max_inputs=10_000)
        )
        return wrap_trace_inputs(inputs, component_provenance(entry, case))
    if policy == "operator_char_first":
        inputs = phase11.dedupe_inputs(
            phase11.operator_char_class_inputs(entry)
            + phase11.fixture_neighbor_inputs(entry)
            + phase11.source_literal_char_inputs(entry, case)
            + phase5b.phase5b_hard_trace_inputs(entry, max_inputs=10_000)
        )
        return wrap_trace_inputs(inputs, component_provenance(entry, case))
    if policy == "generic_fallback_only":
        return wrap_trace_inputs(phase5b.phase5b_hard_trace_inputs(entry, max_inputs=10_000), component_provenance(entry, case))
    if policy == "generic_type_boundaries":
        return generic_type_boundary_order(function, entry)
    if policy == "uniform_random_domain":
        if seed is None:
            raise ValueError("uniform_random_domain requires a seed")
        domain = list(function.domain)
        random.Random(stable_seed(seed, function.function_id, "uniform_random_domain")).shuffle(domain)
        return [PolicyProbe(args=args, bucket="uniform_random_domain") for args in domain[:max(BUDGETS)]]
    if policy == "randomized_union_order":
        if seed is None:
            raise ValueError("randomized_union_order requires a seed")
        union = phase11.dedupe_inputs(
            phase11.fixture_neighbor_inputs(entry)
            + phase11.source_literal_char_inputs(entry, case)
            + phase5b.phase5b_hard_trace_inputs(entry, max_inputs=10_000)
        )
        probes = wrap_trace_inputs(union, component_provenance(entry, case))
        random.Random(stable_seed(seed, function.function_id, "randomized_union_order")).shuffle(probes)
        return probes[:max(BUDGETS)]
    raise ValueError(f"unknown policy: {policy}")


def component_provenance(entry: dict[str, Any], case: fixtures.FunctionCase) -> dict[tuple[int, ...], tuple[str, ...]]:
    from analysis.decompile_faithfulness import run_phase11_input_ordering as phase11

    sources: dict[tuple[int, ...], list[str]] = defaultdict(list)
    for name, items in [
        ("fixture_neighbor", phase11.fixture_neighbor_inputs(entry)),
        ("source_literal_char", phase11.source_literal_char_inputs(entry, case)),
        ("operator_char_class", phase11.operator_char_class_inputs(entry)),
        ("generic_fallback", phase5b.phase5b_hard_trace_inputs(entry, max_inputs=10_000)),
    ]:
        for item in items:
            if name not in sources[item.args]:
                sources[item.args].append(name)
    return {args: tuple(names) for args, names in sources.items()}


def wrap_trace_inputs(
    inputs: list[dynamic_trace.TraceInput],
    provenance: dict[tuple[int, ...], tuple[str, ...]],
) -> list[PolicyProbe]:
    return [probe_from_trace_input(item, provenance) for item in inputs[:max(BUDGETS)]]


def probe_from_trace_input(
    item: dynamic_trace.TraceInput,
    provenance: dict[tuple[int, ...], tuple[str, ...]],
) -> PolicyProbe:
    sources = provenance.get(item.args, (item.bucket,))
    return PolicyProbe(
        args=item.args,
        bucket=item.bucket,
        source_literal_derived="source_literal_char" in sources or item.bucket == "source_literal_char",
        fixture_neighbor_derived="fixture_neighbor" in sources or item.bucket == "fixture_neighbor",
        generic_fallback_derived="generic_fallback" in sources or item.bucket == "phase5b_hard_probe",
        operator_char_derived="operator_char_class" in sources or item.bucket == "operator_char_class",
        duplicate_sources=sources,
    )


def generic_type_boundary_order(function: HoldoutFunction, entry: dict[str, Any]) -> list[PolicyProbe]:
    fixture_args = [tuple(int(value) for value in row["args"]) for row in entry["fixtures"]]
    values_by_position = [boundary_values_for_spec(spec) for spec in function.domain_specs]
    domain_sets = [set(spec["values"]) for spec in function.domain_specs]
    generated: list[PolicyProbe] = []
    for args in fixture_args:
        for index, values in enumerate(values_by_position):
            for value in values:
                candidate = list(args)
                candidate[index] = value
                tuple_args = tuple(candidate)
                if tuple_args == args or not exact_domain_contains_tuple(tuple_args, domain_sets):
                    continue
                generated.append(PolicyProbe(tuple_args, "generic_type_boundary", generic_type_boundary_derived=True))
    for tuple_args in itertools.product(*values_by_position):
        if exact_domain_contains_tuple(tuple_args, domain_sets):
            generated.append(PolicyProbe(tuple(int(value) for value in tuple_args), "generic_type_boundary_cartesian", generic_type_boundary_derived=True))
    return dedupe_policy_probes(generated)[:max(BUDGETS)]


def boundary_values_for_spec(spec: dict[str, Any]) -> list[int]:
    type_text = str(spec.get("type", ""))
    values = set(int(value) for value in spec["values"])
    if "char" in type_text:
        pool = GENERIC_TYPE_BOUNDARIES_CHAR
    elif type_text.strip().startswith("unsigned") or type_text in {"bool", "_Bool"}:
        pool = GENERIC_TYPE_BOUNDARIES_UNSIGNED
    else:
        pool = GENERIC_TYPE_BOUNDARIES_SIGNED
    return [value for value in pool if value in values]


def dedupe_policy_probes(probes: Iterable[PolicyProbe]) -> list[PolicyProbe]:
    seen: set[tuple[int, ...]] = set()
    result: list[PolicyProbe] = []
    for probe in probes:
        if probe.args in seen:
            continue
        seen.add(probe.args)
        result.append(probe)
    return result


def evaluate_policies(
    repo_root: Path,
    functions: dict[str, HoldoutFunction],
    candidates: list[CandidateRecord],
    labels: dict[str, dict[str, Any]],
    population: dict[str, Any],
    policy_orders: dict[tuple[str, str, int | None], list[PolicyProbe]],
    generation_times: dict[tuple[str, str, int | None], float],
    work_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    traces: list[dict[str, Any]] = []
    first_witness_rows: list[dict[str, Any]] = []
    unexpected_rows: list[dict[str, Any]] = []
    source_output_cache: dict[tuple[str, tuple[tuple[int, ...], ...]], ExecutionResult] = {}
    for candidate in candidates:
        function = functions[candidate.function_id]
        candidate_source = candidate.source_path.read_text(encoding="utf-8")
        candidate_policy_orders = {
            key: order for key, order in policy_orders.items()
            if key[0] == function.function_id
        }
        union_args = ordered_union_args(order for order in candidate_policy_orders.values())
        source_key = (function.function_id, tuple(union_args))
        if source_key not in source_output_cache:
            source_output_cache[source_key] = execute_inputs(function, function.source, union_args, work_dir / "source", "trusted_source_policy")
        source_run = source_output_cache[source_key]
        candidate_run = execute_inputs(function, candidate_source, union_args, work_dir / "candidate", candidate.candidate_id)
        source_outputs = output_map(union_args, source_run)
        candidate_outputs = output_map(union_args, candidate_run)
        for (function_id, policy, seed), order in sorted(candidate_policy_orders.items()):
            for budget in BUDGETS:
                prefix = order[:budget]
                first_in_domain = None
                first_extended = None
                elapsed_to_first = None
                for position, probe in enumerate(prefix, start=1):
                    source_output = source_outputs.get(probe.args)
                    candidate_output = candidate_outputs.get(probe.args)
                    execution_ok = source_run.ok and candidate_run.ok and source_output is not None and candidate_output is not None
                    mismatch = bool(execution_ok and source_output != candidate_output)
                    in_domain = exact_domain_contains(function, probe.args)
                    if mismatch and first_extended is None:
                        first_extended = position
                    if mismatch and in_domain and first_in_domain is None:
                        first_in_domain = position
                        elapsed_to_first = candidate_run.elapsed_s
                    if mismatch and (candidate.label == "no_mismatch_under_exact_holdout_domain" or not in_domain):
                        unexpected = unexpected_mismatch_row(candidate, function, policy, seed, budget, position, probe, source_output, candidate_output, in_domain)
                        if unexpected not in unexpected_rows:
                            unexpected_rows.append(unexpected)
                    traces.append({
                        "candidate_id": candidate.candidate_id,
                        "function_id": candidate.function_id,
                        "project": candidate.project,
                        "candidate_stratum": candidate.candidate_stratum,
                        "label": candidate.label,
                        "mutation_family": candidate.mutation_family,
                        "policy": policy,
                        "budget": budget,
                        "random_seed": seed,
                        "position": position,
                        "input_tuple": list(probe.args),
                        "source_output": source_output,
                        "candidate_output": candidate_output,
                        "mismatch": mismatch,
                        "in_exact_domain": in_domain,
                        "source_literal_derived": probe.source_literal_derived,
                        "fixture_neighbor_derived": probe.fixture_neighbor_derived,
                        "generic_fallback_derived": probe.generic_fallback_derived,
                        "operator_char_derived": probe.operator_char_derived,
                        "generic_type_boundary_derived": probe.generic_type_boundary_derived,
                        "duplicate_removal_provenance": list(probe.duplicate_sources),
                        "elapsed_generation_time_s": generation_times[(function_id, policy, seed)],
                        "elapsed_execution_time_s": candidate_run.elapsed_s,
                        "source_execution_status": source_run.reason,
                        "candidate_execution_status": candidate_run.reason,
                    })
                first_witness_rows.append({
                    "candidate_id": candidate.candidate_id,
                    "function_id": candidate.function_id,
                    "project": candidate.project,
                    "candidate_stratum": candidate.candidate_stratum,
                    "label": candidate.label,
                    "mutation_family": candidate.mutation_family,
                    "policy": policy,
                    "budget": budget,
                    "random_seed": seed,
                    "first_in_domain_witness_rank": first_in_domain,
                    "first_extended_witness_rank": first_extended,
                    "detected_in_domain": first_in_domain is not None,
                    "detected_extended_domain": first_extended is not None,
                    "time_to_first_witness_s": elapsed_to_first,
                    "mismatch_density": mismatch_density(labels[candidate.candidate_id]),
                    "density_bucket": density_bucket_for_label(labels[candidate.candidate_id]),
                    "in_primary_fixture_passing_wrong": candidate.candidate_id in population["sets"]["primary_fixture_passing_wrong"],
                    "in_low_density_fixture_passing_wrong": candidate.candidate_id in population["sets"]["low_density_fixture_passing_wrong"],
                    "in_all_controlled_semantic_wrong": candidate.candidate_id in population["sets"]["all_controlled_semantic_wrong"],
                    "in_no_mismatch_comparison": candidate.candidate_id in population["sets"]["no_mismatch_comparison"],
                })
    confirmed = confirm_unexpected_mismatches(functions, candidates, unexpected_rows, work_dir / "unexpected_confirm")
    by_key = {unexpected_key(row): row for row in confirmed}
    unexpected_rows = [by_key.get(unexpected_key(row), row) for row in unexpected_rows]
    return traces, first_witness_rows, unexpected_rows


def ordered_union_args(orders: Iterable[list[PolicyProbe]]) -> list[tuple[int, ...]]:
    seen: set[tuple[int, ...]] = set()
    result: list[tuple[int, ...]] = []
    for order in orders:
        for probe in order[:max(BUDGETS)]:
            if probe.args in seen:
                continue
            seen.add(probe.args)
            result.append(probe.args)
    return result


def output_map(args: list[tuple[int, ...]], run: ExecutionResult) -> dict[tuple[int, ...], int]:
    if not run.ok:
        return {}
    return {arg: output for arg, output in zip(args, run.outputs)}


def execute_inputs(
    function: HoldoutFunction,
    function_source: str,
    args_list: list[tuple[int, ...]],
    output_dir: Path,
    candidate_id: str,
) -> ExecutionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = safe_name(function.function_id + "_" + candidate_id + "_" + sha256_text(json.dumps(args_list))[:12])[:190]
    source_path = output_dir / f"{stem}.c"
    exe_path = output_dir / f"{stem}.exe"
    source_path.write_text(render_harness(function, function_source, args_list), encoding="utf-8")
    compile_cmd = [
        "/usr/bin/gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O0",
        "-fsanitize=undefined,address", "-fno-sanitize-recover=all",
        str(source_path), "-o", str(exe_path),
    ]
    compile_result = ccompile.run_command(compile_cmd, output_dir, timeout_s=20)
    if compile_result.returncode != 0:
        return ExecutionResult(False, (), "compile_failure", 0.0, str(source_path), compile_result.stderr[-1000:])
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = "detect_leaks=0"
    env["LSAN_OPTIONS"] = "detect_leaks=0"
    started = time.perf_counter()
    run_result = subprocess.run(
        [str(exe_path)],
        cwd=output_dir,
        timeout=20,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )
    elapsed = time.perf_counter() - started
    if run_result.returncode != 0:
        return ExecutionResult(False, (), f"runtime_failure_{run_result.returncode}", elapsed, str(source_path), run_result.stderr[-1000:])
    lines = [line.strip() for line in run_result.stdout.splitlines() if line.strip()]
    if len(lines) != len(args_list):
        return ExecutionResult(False, (), "harness_output_count_mismatch", elapsed, str(source_path), run_result.stderr[-1000:])
    try:
        outputs = tuple(int(line) for line in lines)
    except ValueError:
        return ExecutionResult(False, (), "non_integer_output", elapsed, str(source_path), run_result.stderr[-1000:])
    return ExecutionResult(True, outputs, "ok", elapsed, str(source_path))


def render_harness(function: HoldoutFunction, function_source: str, args_list: list[tuple[int, ...]]) -> str:
    lines = [
        "#include <stdbool.h>",
        "#include <stdint.h>",
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "",
        function_source.rstrip(),
        "",
        "int main(void) {",
    ]
    for args in args_list:
        rendered = ", ".join(str(value) for value in args)
        lines.append(f'    printf("%lld\\n", (long long){function.function_name}({rendered}));')
    lines.append("    return 0;")
    lines.append("}")
    return "\n".join(lines) + "\n"


def unexpected_mismatch_row(
    candidate: CandidateRecord,
    function: HoldoutFunction,
    policy: str,
    seed: int | None,
    budget: int,
    position: int,
    probe: PolicyProbe,
    source_output: int | None,
    candidate_output: int | None,
    in_domain: bool,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "function_id": candidate.function_id,
        "project": candidate.project,
        "candidate_stratum": candidate.candidate_stratum,
        "label": candidate.label,
        "policy": policy,
        "random_seed": seed,
        "budget": budget,
        "position": position,
        "input_tuple": list(probe.args),
        "source_output": source_output,
        "candidate_output": candidate_output,
        "in_exact_domain": in_domain,
        "adjudication": "unexpected_in_domain_mismatch" if in_domain else "out_of_domain_mismatch_not_false_positive",
        "confirmation": {"confirmed": False},
    }


def confirm_unexpected_mismatches(
    functions: dict[str, HoldoutFunction],
    candidates: list[CandidateRecord],
    unexpected_rows: list[dict[str, Any]],
    output_dir: Path,
) -> list[dict[str, Any]]:
    candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    confirmed: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in unexpected_rows:
        key = unexpected_key(row)
        if key in seen:
            continue
        seen.add(key)
        candidate = candidates_by_id[row["candidate_id"]]
        function = functions[candidate.function_id]
        args = [tuple(int(value) for value in row["input_tuple"])]
        source_run = execute_inputs(function, function.source, args, output_dir / "source", "unexpected_source")
        candidate_run = execute_inputs(function, candidate.source_path.read_text(encoding="utf-8"), args, output_dir / "candidate", candidate.candidate_id)
        confirmed_row = dict(row)
        confirmed_row["confirmation"] = {
            "confirmed": bool(source_run.ok and candidate_run.ok and source_run.outputs and candidate_run.outputs and source_run.outputs[0] != candidate_run.outputs[0]),
            "source_output": source_run.outputs[0] if source_run.ok and source_run.outputs else None,
            "candidate_output": candidate_run.outputs[0] if candidate_run.ok and candidate_run.outputs else None,
            "source_status": source_run.reason,
            "candidate_status": candidate_run.reason,
        }
        confirmed.append(confirmed_row)
    return confirmed


def unexpected_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row["candidate_id"], row["policy"], row.get("random_seed"), tuple(row["input_tuple"]))


def summarize_policy_results(
    traces: list[dict[str, Any]],
    first_witness_rows: list[dict[str, Any]],
    population: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    summary_rows: list[dict[str, Any]] = []
    budget_rows: list[dict[str, Any]] = []
    random_rows: list[dict[str, Any]] = []
    scopes = {
        "primary_fixture_passing_wrong": population["sets"]["primary_fixture_passing_wrong"],
        "low_density_fixture_passing_wrong": population["sets"]["low_density_fixture_passing_wrong"],
        "all_controlled_semantic_wrong": population["sets"]["all_controlled_semantic_wrong"],
    }
    trace_index = group_traces(traces)
    rows_by_key = group_first_witness(first_witness_rows)
    for policy in DETERMINISTIC_POLICIES:
        for budget in BUDGETS:
            rows = [row for row in rows_by_key.get((policy, budget, None), [])]
            for scope, candidates in scopes.items():
                metrics = detection_metrics(rows, candidates, trace_index, policy, budget, None)
                item = {"policy": policy, "policy_class": "deterministic", "budget": budget, "scope": scope, "random_seed": ""}
                item.update(metrics)
                summary_rows.append(item)
                budget_rows.append(item)
    for policy in RANDOM_POLICIES:
        for budget in BUDGETS:
            per_seed_scope_metrics: dict[str, list[dict[str, Any]]] = {scope: [] for scope in scopes}
            for seed in RANDOM_SEEDS:
                rows = rows_by_key.get((policy, budget, seed), [])
                for scope, candidates in scopes.items():
                    metrics = detection_metrics(rows, candidates, trace_index, policy, budget, seed)
                    random_rows.append({"policy": policy, "budget": budget, "scope": scope, "random_seed": seed, **metrics})
                    per_seed_scope_metrics[scope].append(metrics)
            for scope, metrics_list in per_seed_scope_metrics.items():
                aggregate = stochastic_aggregate(metrics_list)
                summary_rows.append({"policy": policy, "policy_class": "stochastic", "budget": budget, "scope": scope, "random_seed": "30_fixed_seeds", **aggregate})
                budget_rows.append({"policy": policy, "policy_class": "stochastic", "budget": budget, "scope": scope, "random_seed": "30_fixed_seeds", **aggregate})
    return summary_rows, budget_rows, random_rows


def group_traces(traces: list[dict[str, Any]]) -> dict[tuple[str, int, int | None, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, int, int | None, str], list[dict[str, Any]]] = defaultdict(list)
    for row in traces:
        grouped[(row["policy"], int(row["budget"]), row["random_seed"], row["candidate_id"])].append(row)
    return grouped


def group_first_witness(rows: list[dict[str, Any]]) -> dict[tuple[str, int, int | None], list[dict[str, Any]]]:
    grouped: dict[tuple[str, int, int | None], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["policy"], int(row["budget"]), row["random_seed"])].append(row)
    return grouped


def detection_metrics(
    rows: list[dict[str, Any]],
    denominator_ids: list[str],
    trace_index: dict[tuple[str, int, int | None, str], list[dict[str, Any]]],
    policy: str,
    budget: int,
    seed: int | None,
) -> dict[str, Any]:
    by_id = {row["candidate_id"]: row for row in rows}
    detected = [cid for cid in denominator_ids if by_id.get(cid, {}).get("detected_in_domain")]
    ranks = [
        int(by_id[cid]["first_in_domain_witness_rank"])
        for cid in detected
        if by_id[cid].get("first_in_domain_witness_rank") is not None
    ]
    times = [
        float(by_id[cid]["time_to_first_witness_s"])
        for cid in detected
        if by_id[cid].get("time_to_first_witness_s") is not None
    ]
    probe_count = 0
    in_domain_count = 0
    out_domain_witnesses = 0
    unexpected_in_domain = 0
    for row in rows:
        cid = row["candidate_id"]
        for trace in trace_index.get((policy, budget, seed, cid), []):
            probe_count += 1
            in_domain_count += int(trace["in_exact_domain"])
            out_domain_witnesses += int(trace["mismatch"] and not trace["in_exact_domain"])
            unexpected_in_domain += int(trace["mismatch"] and trace["in_exact_domain"] and row.get("in_no_mismatch_comparison"))
    denominator = len(denominator_ids)
    return {
        "denominator": denominator,
        "detected": len(detected),
        "detection_rate": safe_div(len(detected), denominator),
        "survivors": denominator - len(detected),
        "median_first_witness_rank": percentile(ranks, 0.50),
        "p95_first_witness_rank": percentile(ranks, 0.95),
        "median_time_to_first_witness_s": percentile(times, 0.50),
        "p95_time_to_first_witness_s": percentile(times, 0.95),
        "exact_domain_probe_fraction": safe_div(in_domain_count, probe_count),
        "out_of_domain_witness_count": out_domain_witnesses,
        "unexpected_in_domain_mismatch_count": unexpected_in_domain,
    }


def stochastic_aggregate(metrics_list: list[dict[str, Any]]) -> dict[str, Any]:
    rates = [float(item["detection_rate"]) for item in metrics_list]
    detected = [float(item["detected"]) for item in metrics_list]
    return {
        "denominator": metrics_list[0]["denominator"] if metrics_list else 0,
        "detected": statistics.mean(detected) if detected else 0.0,
        "detection_rate": statistics.mean(rates) if rates else 0.0,
        "detection_rate_stddev": statistics.pstdev(rates) if len(rates) > 1 else 0.0,
        "detection_rate_median": percentile(rates, 0.50),
        "detection_rate_p2_5": percentile(rates, 0.025),
        "detection_rate_p97_5": percentile(rates, 0.975),
        "detection_rate_best_seed": max(rates) if rates else 0.0,
        "detection_rate_worst_seed": min(rates) if rates else 0.0,
        "survivors": metrics_list[0]["denominator"] - statistics.mean(detected) if metrics_list else 0.0,
        "median_first_witness_rank": percentile([float(item["median_first_witness_rank"]) for item in metrics_list if item["median_first_witness_rank"] != ""], 0.50),
        "p95_first_witness_rank": percentile([float(item["p95_first_witness_rank"]) for item in metrics_list if item["p95_first_witness_rank"] != ""], 0.95),
        "median_time_to_first_witness_s": percentile([float(item["median_time_to_first_witness_s"]) for item in metrics_list if item["median_time_to_first_witness_s"] != ""], 0.50),
        "p95_time_to_first_witness_s": percentile([float(item["p95_time_to_first_witness_s"]) for item in metrics_list if item["p95_time_to_first_witness_s"] != ""], 0.95),
        "exact_domain_probe_fraction": statistics.mean([float(item["exact_domain_probe_fraction"]) for item in metrics_list]) if metrics_list else 0.0,
        "out_of_domain_witness_count": statistics.mean([float(item["out_of_domain_witness_count"]) for item in metrics_list]) if metrics_list else 0.0,
        "unexpected_in_domain_mismatch_count": statistics.mean([float(item["unexpected_in_domain_mismatch_count"]) for item in metrics_list]) if metrics_list else 0.0,
    }


def stratified_results(
    functions: dict[str, HoldoutFunction],
    candidates: list[CandidateRecord],
    labels: dict[str, dict[str, Any]],
    population: dict[str, Any],
    first_witness_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    rows: list[dict[str, Any]] = []
    primary = population["sets"]["primary_fixture_passing_wrong"]
    all_wrong = population["sets"]["all_controlled_semantic_wrong"]
    for group_type, groups in stratification_groups(functions, candidates_by_id, labels, primary).items():
        for group, ids in groups.items():
            for policy in DETERMINISTIC_POLICIES:
                detected = detected_ids(first_witness_rows, policy, 8, None, ids)
                ranks = witness_ranks(first_witness_rows, policy, 8, None, ids)
                rows.append({
                    "group_type": group_type,
                    "group": group,
                    "policy": policy,
                    "budget": 8,
                    "denominator": len(ids),
                    "detected": len(detected),
                    "detection_rate": safe_div(len(detected), len(ids)),
                    "median_witness_rank": percentile(ranks, 0.50),
                })
    for family, ids in sorted(group_by(population["candidate_mutation_family"], all_wrong).items()):
        attempts = sum(1 for candidate in candidates if candidate.mutation_family == family)
        compile_ready = sum(1 for candidate in candidates if candidate.mutation_family == family and candidate.compile_status == "compile_ready")
        semantic_wrong = len(ids)
        fixture_passing = len([cid for cid in ids if cid in primary])
        low_density = len([cid for cid in ids if cid in population["sets"]["low_density_fixture_passing_wrong"]])
        for policy in DETERMINISTIC_POLICIES:
            detected = detected_ids(first_witness_rows, policy, 8, None, [cid for cid in ids if cid in primary])
            rows.append({
                "group_type": "mutation_family_realized",
                "group": family,
                "policy": policy,
                "budget": 8,
                "attempts": attempts,
                "compile_ready": compile_ready,
                "semantic_wrong": semantic_wrong,
                "fixture_passing_semantic_wrong": fixture_passing,
                "low_density_semantic_wrong": low_density,
                "denominator": fixture_passing,
                "detected": len(detected),
                "detection_rate": safe_div(len(detected), fixture_passing),
                "median_witness_rank": percentile(witness_ranks(first_witness_rows, policy, 8, None, [cid for cid in ids if cid in primary]), 0.50),
            })
    return rows


def stratification_groups(
    functions: dict[str, HoldoutFunction],
    candidates_by_id: dict[str, CandidateRecord],
    labels: dict[str, dict[str, Any]],
    ids: list[str],
) -> dict[str, dict[str, list[str]]]:
    groups: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for cid in ids:
        candidate = candidates_by_id[cid]
        function = functions[candidate.function_id]
        groups["project"][candidate.project].append(cid)
        groups["density_bucket"][density_bucket_for_label(labels[cid])].append(cid)
        groups["source_literal_availability"]["has_source_char_literal" if function.source_literal_count > 0 else "no_source_char_literal"].append(cid)
        groups["argument_count"]["one_argument" if len(function.domain_specs) == 1 else "two_arguments"].append(cid)
        has_char = any("char" in str(spec.get("type", "")) for spec in function.domain_specs)
        groups["signature_character"]["character_like_argument_present" if has_char else "integer_only"].append(cid)
        groups["exact_domain_size"][str(function.domain_size)].append(cid)
    return {kind: dict(values) for kind, values in groups.items()}


def density_results(population: dict[str, Any], first_witness_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    buckets = sorted({row["density_bucket"] for row in first_witness_rows if row["in_primary_fixture_passing_wrong"]})
    for bucket in buckets:
        ids = [
            row["candidate_id"] for row in first_witness_rows
            if row["policy"] == FINAL_POLICY
            and row["budget"] == 8
            and row["random_seed"] is None
            and row["in_primary_fixture_passing_wrong"]
            and row["density_bucket"] == bucket
        ]
        for policy in DETERMINISTIC_POLICIES:
            detected = detected_ids(first_witness_rows, policy, 8, None, ids)
            rows.append({"density_bucket": bucket, "policy": policy, "budget": 8, "denominator": len(ids), "detected": len(detected), "detection_rate": safe_div(len(detected), len(ids))})
    return rows


def first_witness_ecdf(first_witness_rows: list[dict[str, Any]], population: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    denominator_ids = set(population["sets"]["primary_fixture_passing_wrong"])
    for policy in DETERMINISTIC_POLICIES:
        ranks = sorted(
            int(row["first_in_domain_witness_rank"])
            for row in first_witness_rows
            if row["policy"] == policy
            and row["budget"] == max(BUDGETS)
            and row["random_seed"] is None
            and row["candidate_id"] in denominator_ids
            and row["first_in_domain_witness_rank"] is not None
        )
        denom = len(denominator_ids)
        for rank in BUDGETS:
            count = sum(1 for value in ranks if value <= rank)
            rows.append({"policy": policy, "rank": rank, "detected": count, "denominator": denom, "detection_rate": safe_div(count, denom)})
    return rows


def statistical_comparisons(population: dict[str, Any], first_witness_rows: list[dict[str, Any]]) -> dict[str, Any]:
    primary = population["sets"]["primary_fixture_passing_wrong"]
    final_detected = set(detected_ids(first_witness_rows, FINAL_POLICY, 8, None, primary))
    comparisons: dict[str, Any] = {}
    for policy in ["fixture_neighbor_only", "source_literal_only", "generic_type_boundaries"]:
        other = set(detected_ids(first_witness_rows, policy, 8, None, primary))
        comparisons[policy] = comparison_record(primary, final_detected, other, population)
    for policy in RANDOM_POLICIES:
        seed_sets = [set(detected_ids(first_witness_rows, policy, 8, seed, primary)) for seed in RANDOM_SEEDS]
        per_candidate_other = {cid: statistics.mean([1.0 if cid in seed_set else 0.0 for seed_set in seed_sets]) for cid in primary}
        other_rate = statistics.mean(per_candidate_other.values()) if per_candidate_other else 0.0
        final_rate = safe_div(len(final_detected), len(primary))
        comparisons[policy] = {
            "absolute_detection_at_8_difference": final_rate - other_rate,
            "other_detection_at_8_mean": other_rate,
            "final_detection_at_8": final_rate,
        }
    return comparisons


def comparison_record(
    ids: list[str],
    final_detected: set[str],
    other_detected: set[str],
    population: dict[str, Any],
) -> dict[str, Any]:
    wins = sum(1 for cid in ids if cid in final_detected and cid not in other_detected)
    losses = sum(1 for cid in ids if cid not in final_detected and cid in other_detected)
    ties = len(ids) - wins - losses
    return {
        "absolute_detection_at_8_difference": safe_div(len(final_detected), len(ids)) - safe_div(len(other_detected), len(ids)),
        "win_count": wins,
        "tie_count": ties,
        "loss_count": losses,
        "function_level_bootstrap_interval": bootstrap_difference_interval(ids, final_detected, other_detected, population["candidate_function"]),
        "project_level_sensitivity": project_sensitivity(ids, final_detected, other_detected, population["candidate_project"]),
    }


def bootstrap_difference_interval(
    ids: list[str],
    final_detected: set[str],
    other_detected: set[str],
    candidate_function: dict[str, str],
    iterations: int = 500,
) -> dict[str, float]:
    by_function = group_by(candidate_function, ids)
    function_ids = sorted(by_function)
    if not function_ids:
        return {"p2_5": 0.0, "p97_5": 0.0}
    rng = random.Random(2026070304)
    deltas: list[float] = []
    for _ in range(iterations):
        sample_functions = [rng.choice(function_ids) for _ in function_ids]
        sample_ids = [cid for function_id in sample_functions for cid in by_function[function_id]]
        deltas.append(safe_div(sum(cid in final_detected for cid in sample_ids), len(sample_ids)) - safe_div(sum(cid in other_detected for cid in sample_ids), len(sample_ids)))
    return {"p2_5": float(percentile(deltas, 0.025)), "p97_5": float(percentile(deltas, 0.975))}


def project_sensitivity(
    ids: list[str],
    final_detected: set[str],
    other_detected: set[str],
    candidate_project: dict[str, str],
) -> list[dict[str, Any]]:
    projects = sorted({candidate_project[cid] for cid in ids})
    rows = []
    for project in projects:
        kept = [cid for cid in ids if candidate_project[cid] != project]
        rows.append({
            "left_out_project": project,
            "remaining_denominator": len(kept),
            "delta": safe_div(sum(cid in final_detected for cid in kept), len(kept)) - safe_div(sum(cid in other_detected for cid in kept), len(kept)),
        })
    return rows


def write_tables(
    repo_root: Path,
    policy_summary: list[dict[str, Any]],
    stratified: list[dict[str, Any]],
    population: dict[str, Any],
    unexpected_rows: list[dict[str, Any]],
) -> None:
    table_dir = repo_root / "paper/tables"
    final_rows = [row for row in policy_summary if row["policy"] == FINAL_POLICY and row["scope"] in {"primary_fixture_passing_wrong", "low_density_fixture_passing_wrong", "all_controlled_semantic_wrong"}]
    write_latex_table(
        table_dir / "holdout_main_results.tex",
        "Held-out Detection for Frozen Final Policy",
        ["Scope", "B", "Denom.", "Detected", "Detection"],
        [[row["scope"], row["budget"], row["denominator"], row["detected"], fmt_rate(row["detection_rate"])] for row in final_rows],
    )
    b8_rows = [row for row in policy_summary if int(row["budget"]) == 8 and row["scope"] == "primary_fixture_passing_wrong"]
    write_latex_table(
        table_dir / "holdout_budget8_baselines.tex",
        "Budget-8 Held-out Baselines",
        ["Policy", "Class", "Denom.", "Detected", "Detection"],
        [[row["policy"], row["policy_class"], row["denominator"], row["detected"], fmt_rate(row["detection_rate"])] for row in b8_rows],
    )
    family_rows = [
        row for row in stratified
        if row["group_type"] == "mutation_family_realized" and row["policy"] == FINAL_POLICY
    ]
    write_latex_table(
        table_dir / "holdout_mutation_family_results.tex",
        "Realized Controlled-Mutation Families",
        ["Family", "Attempts", "Compile-ready", "Wrong", "Fixture-pass wrong", "Detection@8"],
        [[row["group"], row.get("attempts", ""), row.get("compile_ready", ""), row.get("semantic_wrong", ""), row.get("fixture_passing_semantic_wrong", ""), fmt_rate(row["detection_rate"])] for row in family_rows],
    )
    in_domain_unexpected = sum(1 for row in unexpected_rows if row["in_exact_domain"])
    out_domain = sum(1 for row in unexpected_rows if not row["in_exact_domain"])
    write_latex_table(
        table_dir / "holdout_no_mismatch_results.tex",
        "No-Mismatch Comparison Population",
        ["Population", "Candidates", "Unexpected in-domain", "Out-of-domain witnesses"],
        [["Natural + controlled no-mismatch", population["counts"]["no_mismatch_comparison"], in_domain_unexpected, out_domain]],
    )


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
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        f"\\caption{{{latex_escape(caption)}}}",
        "\\end{table}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_plot_script(repo_root: Path) -> None:
    path = repo_root / "figures/plot_holdout_evaluation.py"
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
    data = [row for row in rows("holdout_budget_curves.csv") if row["scope"] == "primary_fixture_passing_wrong"]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for policy in sorted({row["policy"] for row in data}):
        policy_rows = sorted([row for row in data if row["policy"] == policy], key=lambda row: int(row["budget"]))
        ax.plot([int(row["budget"]) for row in policy_rows], [float(row["detection_rate"]) for row in policy_rows], marker="o", linewidth=1.3, label=policy)
    ax.set_xlabel("Budget")
    ax.set_ylabel("Detection rate")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/holdout_budget_curves.pdf")


def plot_ecdf() -> None:
    data = rows("holdout_first_witness_ecdf.csv")
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for policy in sorted({row["policy"] for row in data}):
        policy_rows = sorted([row for row in data if row["policy"] == policy], key=lambda row: int(row["rank"]))
        ax.step([int(row["rank"]) for row in policy_rows], [float(row["detection_rate"]) for row in policy_rows], where="post", label=policy)
    ax.set_xlabel("First witness rank")
    ax.set_ylabel("Cumulative detected fraction")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/holdout_first_witness_ecdf.pdf")


def plot_density() -> None:
    data = [row for row in rows("holdout_density_results.csv") if row["policy"] == "source_literal_char_interleave"]
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    ax.bar([row["density_bucket"] for row in data], [float(row["detection_rate"]) for row in data])
    ax.set_xlabel("Mismatch-density bucket")
    ax.set_ylabel("Detection@8")
    ax.set_ylim(0, 1.02)
    ax.tick_params(axis="x", labelrotation=20)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/holdout_density_results.pdf")


if __name__ == "__main__":
    plot_budget_curves()
    plot_ecdf()
    plot_density()
""",
        encoding="utf-8",
    )


def generate_figures(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / "figures/plot_holdout_evaluation.py")],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def interpretation_gate(
    policy_summary: list[dict[str, Any]],
    first_witness_rows: list[dict[str, Any]],
    population: dict[str, Any],
    unexpected_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    lookup = {
        (row["policy"], int(row["budget"]), row["scope"]): row
        for row in policy_summary
    }
    final_primary = float(lookup[(FINAL_POLICY, 8, "primary_fixture_passing_wrong")]["detection_rate"])
    final_low = float(lookup[(FINAL_POLICY, 8, "low_density_fixture_passing_wrong")]["detection_rate"])
    fixture_neighbor = float(lookup[("fixture_neighbor_only", 8, "primary_fixture_passing_wrong")]["detection_rate"])
    source_agnostic = max(
        float(lookup[(policy, 8, "primary_fixture_passing_wrong")]["detection_rate"])
        for policy in ["fixture_neighbor_only", "generic_fallback_only", "generic_type_boundaries"]
    )
    unexpected_in_domain = sum(1 for row in unexpected_rows if row["in_exact_domain"])
    strong = (
        final_primary >= 0.85
        and final_low >= 0.70
        and final_primary >= fixture_neighbor - 0.02
        and final_primary >= source_agnostic + 0.05
        and unexpected_in_domain == 0
    )
    weak = final_primary < 0.70 or final_low < 0.50
    if strong:
        outcome = "strong_held_out_mechanism_support"
        claim = "Held-out results support the frozen mechanism under the preregistered gates."
    elif weak:
        outcome = "weak_support"
        claim = "Do not broaden claims; report weak held-out support under the preregistered gates."
    else:
        outcome = "moderate_support_requiring_claim_narrowing"
        claim = "Narrow claims to represented controlled-drift families and exact-domain holdout conditions."
    return {
        "outcome": outcome,
        "claim_consequence": claim,
        "final_detection_at_8_primary": final_primary,
        "final_detection_at_8_low_density": final_low,
        "fixture_neighbor_detection_at_8_primary": fixture_neighbor,
        "strongest_source_agnostic_detection_at_8_primary": source_agnostic,
        "unexpected_in_domain_mismatch_count": unexpected_in_domain,
    }


def write_handoff(
    repo_root: Path,
    preflight: dict[str, Any],
    population: dict[str, Any],
    policy_summary: list[dict[str, Any]],
    stratified: list[dict[str, Any]],
    first_witness_rows: list[dict[str, Any]],
    unexpected_rows: list[dict[str, Any]],
    gate: dict[str, Any],
) -> Path:
    path = repo_root / "docs/paper_agent/frozen_holdout_evaluation_handoff.md"
    prereg_commit = git_output(repo_root, ["rev-parse", "7587078"])
    head = git_output(repo_root, ["rev-parse", "HEAD"])
    final_by_budget = [
        row for row in policy_summary
        if row["policy"] == FINAL_POLICY and row["scope"] == "primary_fixture_passing_wrong"
    ]
    baseline_b8 = [
        row for row in policy_summary
        if int(row["budget"]) == 8 and row["scope"] == "primary_fixture_passing_wrong" and row["policy"] != FINAL_POLICY
    ]
    family_counts = [
        row for row in stratified
        if row["group_type"] == "mutation_family_realized" and row["policy"] == FINAL_POLICY
    ]
    source_literal_rows = [
        row for row in stratified
        if row["group_type"] == "source_literal_availability"
        and row["policy"] in {
            FINAL_POLICY,
            "fixture_neighbor_only",
            "source_literal_only",
            "generic_type_boundaries",
        }
    ]
    natural_rows = [row for row in first_witness_rows if row["candidate_stratum"] == "natural_ghidra" and row["budget"] == 8 and row["policy"] == FINAL_POLICY]
    lines = [
        "# Frozen Holdout Evaluation Handoff",
        "",
        "## Git",
        "",
        "- Branch: `phase1e-frozen-holdout-evaluation`",
        f"- Preregistration commit: `{prereg_commit}`",
        f"- Result-producing HEAD at run: `{head}`",
        f"- Verified holdout seal: `{preflight['holdout_manifest_sha256']}`",
        f"- Method freeze commit: `{METHOD_FREEZE_COMMIT}`",
        "",
        "## Populations",
        "",
        f"- Fixture-passing wrong count: `{population['counts']['primary_fixture_passing_wrong']}`",
        f"- Low-density fixture-passing wrong count: `{population['counts']['low_density_fixture_passing_wrong']}`",
        f"- All controlled semantic-wrong count: `{population['counts']['all_controlled_semantic_wrong']}`",
        f"- No-mismatch comparison count: `{population['counts']['no_mismatch_comparison']}`",
        "",
        "## Final Detection",
        "",
    ]
    for row in sorted(final_by_budget, key=lambda item: int(item["budget"])):
        lines.append(f"- B={row['budget']}: `{row['detected']}/{row['denominator']}` = `{fmt_rate(row['detection_rate'])}`")
    lines.extend(["", "## Budget-8 Baselines", ""])
    for row in baseline_b8:
        lines.append(f"- {row['policy']}: `{row['detected']}/{row['denominator']}` = `{fmt_rate(row['detection_rate'])}`")
    lines.extend(["", "## Realized Mutation Families", ""])
    for row in family_counts:
        lines.append(f"- {row['group']}: attempts `{row.get('attempts')}`, compile-ready `{row.get('compile_ready')}`, semantic wrong `{row.get('semantic_wrong')}`, fixture-passing wrong `{row.get('fixture_passing_semantic_wrong')}`, final Detection@8 `{fmt_rate(row['detection_rate'])}`")
    lines.extend(["", "## Source-Literal Strata", ""])
    for row in sorted(source_literal_rows, key=lambda item: (item["group"], item["policy"])):
        lines.append(f"- {row['group']} / {row['policy']}: `{row['detected']}/{row['denominator']}` = `{fmt_rate(row['detection_rate'])}`")
    lines.extend([
        "",
        "## Natural Ghidra Execution",
        "",
        f"- Natural Ghidra no-mismatch candidates executed by final policy at B=8: `{len(natural_rows)}`",
        f"- Natural Ghidra in-domain unexpected mismatches: `{sum(1 for row in unexpected_rows if row['candidate_stratum'] == 'natural_ghidra' and row['in_exact_domain'])}`",
        "",
        "## No-Mismatch And Out-of-Domain",
        "",
        f"- No-mismatch unexpected in-domain mismatches: `{sum(1 for row in unexpected_rows if row['in_exact_domain'])}`",
        f"- Out-of-domain probe/witness rows requiring separate reporting: `{sum(1 for row in unexpected_rows if not row['in_exact_domain'])}`",
        "",
        "## Gate Outcome",
        "",
        f"- Outcome: `{gate['outcome']}`",
        f"- Claim consequence: {gate['claim_consequence']}",
        "",
        "## Tests Run",
        "",
        "- `python -m py_compile analysis/decompile_faithfulness/holdout_evaluation.py`",
        "- `python -m unittest analysis.decompile_faithfulness.tests.test_probe_order_freeze analysis.decompile_faithfulness.tests.test_submission_evidence_corrections analysis.decompile_faithfulness.tests.test_holdout_acquisition analysis.decompile_faithfulness.tests.test_holdout_evaluation`",
        "",
        "The frozen final auditor was evaluated only after the preregistration commit and successful seal preflight. No holdout candidates, fixtures, labels, domains, mutation grammar, or sealed manifest artifacts were regenerated or modified.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def detected_ids(rows: list[dict[str, Any]], policy: str, budget: int, seed: int | None, ids: list[str]) -> list[str]:
    wanted = set(ids)
    return [
        row["candidate_id"] for row in rows
        if row["policy"] == policy
        and int(row["budget"]) == budget
        and row["random_seed"] == seed
        and row["candidate_id"] in wanted
        and row["detected_in_domain"]
    ]


def witness_ranks(rows: list[dict[str, Any]], policy: str, budget: int, seed: int | None, ids: list[str]) -> list[int]:
    wanted = set(ids)
    return [
        int(row["first_in_domain_witness_rank"]) for row in rows
        if row["policy"] == policy
        and int(row["budget"]) == budget
        and row["random_seed"] == seed
        and row["candidate_id"] in wanted
        and row["first_in_domain_witness_rank"] is not None
    ]


def exact_domain_contains(function: HoldoutFunction, args: tuple[int, ...]) -> bool:
    domain_sets = [set(spec["values"]) for spec in function.domain_specs]
    return exact_domain_contains_tuple(args, domain_sets)


def exact_domain_contains_tuple(args: tuple[int, ...], domain_sets: list[set[int]]) -> bool:
    return len(args) == len(domain_sets) and all(int(value) in domain_sets[index] for index, value in enumerate(args))


def mismatch_density(label: dict[str, Any]) -> float:
    return safe_div(int(label.get("total_mismatching_input_count", 0)), int(label.get("exact_domain_size", 0)))


def density_bucket_for_label(label: dict[str, Any]) -> str:
    rho = mismatch_density(label)
    if rho <= 0:
        return "rho=0"
    if rho <= 0.01:
        return "0<rho<=0.01"
    if rho <= 0.10:
        return "0.01<rho<=0.10"
    if rho <= 0.50:
        return "0.10<rho<=0.50"
    return "0.50<rho<=1.00"


def stable_seed(seed: int, function_id: str, policy: str) -> int:
    digest = hashlib.sha256(f"{seed}\0{function_id}\0{policy}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def group_by(mapping: dict[str, str], ids: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for cid in ids:
        grouped[mapping[cid]].append(cid)
    return dict(grouped)


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
    return f"{float(value):.3f}"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


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
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def directory_hash(path: Path) -> dict[str, Any]:
    files = []
    digest_lines = []
    for item in sorted(child for child in path.rglob("*") if child.is_file()):
        rel = item.relative_to(path).as_posix()
        digest = sha256_path(item)
        files.append({"path": rel, "sha256": digest})
        digest_lines.append(f"{rel}\0{digest}")
    return {
        "type": "directory",
        "file_count": len(files),
        "tree_sha256": sha256_text("\n".join(digest_lines)),
        "files": files,
    }


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return safe.strip("._") or "candidate"


def git_output(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout.strip()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def latex_escape(value: str) -> str:
    return (
        value.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
        .replace("#", "\\#")
    )


if __name__ == "__main__":
    main()
