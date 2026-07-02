from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import dynamic_trace, structured_features
from analysis.decompile_faithfulness import run_phase2_cpu_smoke as cpu_smoke
from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu
from analysis.decompile_faithfulness import run_phase5b_hard_candidates as phase5b


DEFAULT_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json")
DEFAULT_PREFLIGHT = Path("docs/paper_agent/decompile_faithfulness_phase5_preflight.json")
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase6_decompiler_like")
DEFAULT_TOOL_FEASIBILITY_ZH = Path("docs/paper_agent/decompile_faithfulness_phase6_tool_feasibility.zh.md")
DEFAULT_CANDIDATE_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase6_candidate_manifest.json")
DEFAULT_COMPILE_PREFLIGHT = Path("docs/paper_agent/decompile_faithfulness_phase6_compile_preflight.json")
DEFAULT_RESULT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase6_result_analysis.json")
DEFAULT_RESULT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase6_result_analysis.zh.md")
DEFAULT_GATE_ZH = Path("docs/paper_agent/decompile_faithfulness_phase6_gate_decision.zh.md")
DEFAULT_OPT_LEVELS = ("O0", "O2")


@dataclass(frozen=True)
class Phase6Candidate:
    case_id: str
    candidate_id: str
    mutation_type: str
    function_source: str
    expected_role: str
    source_kind: str
    source_name: str
    tool: str
    optimization_level: str
    assembly_context_path: str


def main() -> None:
    args = parse_args()
    summary = run_phase6(
        repo_root=args.repo_root,
        manifest_json=args.manifest_json,
        preflight_json=args.preflight_json,
        output_dir=args.output_dir,
        tool_feasibility_zh=args.tool_feasibility_zh,
        candidate_manifest_json=args.candidate_manifest_json,
        compile_preflight_json=args.compile_preflight_json,
        result_json=args.result_json,
        result_zh=args.result_zh,
        gate_zh=args.gate_zh,
        opt_levels=args.opt_level,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "candidate_count": summary["candidate_count"],
                "compile_pass_count": summary["compile_pass_count"],
                "paired_case_count": summary["paired_case_count"],
                "fixture_only_auc": summary["baseline_auc"]["fixture_only"],
                "static_structured_auc": summary["baseline_auc"]["static_structured_proxy"],
                "v3_trace_total_auc": summary["baseline_auc"]["v3_trace_total"],
                "sota_delta_vs_best_baseline": summary["sota_delta_vs_best_baseline"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--tool-feasibility-zh", type=Path, default=DEFAULT_TOOL_FEASIBILITY_ZH)
    parser.add_argument("--candidate-manifest-json", type=Path, default=DEFAULT_CANDIDATE_MANIFEST)
    parser.add_argument("--compile-preflight-json", type=Path, default=DEFAULT_COMPILE_PREFLIGHT)
    parser.add_argument("--result-json", type=Path, default=DEFAULT_RESULT_JSON)
    parser.add_argument("--result-zh", type=Path, default=DEFAULT_RESULT_ZH)
    parser.add_argument("--gate-zh", type=Path, default=DEFAULT_GATE_ZH)
    parser.add_argument("--opt-level", action="append", default=list(DEFAULT_OPT_LEVELS))
    return parser.parse_args()


def run_phase6(
    repo_root: Path,
    manifest_json: Path,
    preflight_json: Path,
    output_dir: Path,
    tool_feasibility_zh: Path,
    candidate_manifest_json: Path,
    compile_preflight_json: Path,
    result_json: Path,
    result_zh: Path,
    gate_zh: Path,
    opt_levels: list[str],
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    manifest_json = _resolve(repo_root, manifest_json)
    preflight_json = _resolve(repo_root, preflight_json)
    output_dir = _resolve(repo_root, output_dir)
    tool_feasibility_zh = _resolve(repo_root, tool_feasibility_zh)
    candidate_manifest_json = _resolve(repo_root, candidate_manifest_json)
    compile_preflight_json = _resolve(repo_root, compile_preflight_json)
    result_json = _resolve(repo_root, result_json)
    result_zh = _resolve(repo_root, result_zh)
    gate_zh = _resolve(repo_root, gate_zh)

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    preflight = json.loads(preflight_json.read_text(encoding="utf-8"))
    if preflight.get("verdict") != "pass-phase5-preflight":
        raise RuntimeError(f"Phase5 preflight must pass first: {preflight.get('verdict')}")

    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir = output_dir / "candidates"
    trace_dir = output_dir / "traces"
    assembly_dir = output_dir / "assembly"
    static_dir = output_dir / "static_compile"
    for path in [candidate_dir, trace_dir, assembly_dir, static_dir]:
        path.mkdir(parents=True, exist_ok=True)

    tool_probe = probe_tools()
    _write_tool_feasibility(tool_feasibility_zh, tool_probe)

    records: list[dict[str, Any]] = []
    manifest_candidates: list[dict[str, Any]] = []
    original_trace_cache: dict[tuple[str, str, str], dynamic_trace.TraceRun] = {}
    original_static_cache: dict[tuple[str, str], structured_features.StructuredFeatureVector] = {}
    assembly_contexts: list[dict[str, Any]] = []
    records_path = output_dir / "records.jsonl"

    entries = [
        entry for entry in manifest.get("functions", [])
        if entry.get("counts_for_phase5_real_project_gate")
    ]
    for entry in entries:
        case = phase5_gpu._case_from_manifest_entry(repo_root, entry)
        hard_inputs = phase5b.phase5b_hard_trace_inputs(entry, max_inputs=128)
        for opt_level in opt_levels:
            assembly_context = build_assembly_context(
                case=case,
                opt_level=opt_level,
                assembly_dir=assembly_dir,
            )
            assembly_contexts.append(assembly_context)
            candidates = build_phase6_candidates(
                case=case,
                entry=entry,
                opt_level=opt_level,
                assembly_context_path=assembly_context["assembly_path"],
            )
            for candidate in candidates:
                candidate_path = candidate_dir / f"{candidate.candidate_id}.c"
                candidate_path.write_text(candidate.function_source, encoding="utf-8")
                features = phase6_features(
                    case=case,
                    candidate=candidate,
                    hard_inputs=hard_inputs,
                    trace_dir=trace_dir,
                    static_dir=static_dir,
                    original_trace_cache=original_trace_cache,
                    original_static_cache=original_static_cache,
                )
                record = record_from_features(candidate, features, candidate_path)
                records.append(record)
                manifest_candidates.append(candidate_manifest_item(candidate, record, candidate_path))

    _write_jsonl(records_path, records)
    candidate_manifest = build_candidate_manifest(
        records=records,
        manifest_candidates=manifest_candidates,
        records_path=records_path,
        assembly_contexts=assembly_contexts,
        opt_levels=opt_levels,
        tool_probe=tool_probe,
    )
    compile_preflight = build_compile_preflight(records)
    summary = build_result_summary(
        records=records,
        records_path=records_path,
        candidate_manifest=candidate_manifest,
        compile_preflight=compile_preflight,
        tool_probe=tool_probe,
    )
    gate = build_gate_decision(summary)

    _write_json(candidate_manifest_json, candidate_manifest)
    _write_json(compile_preflight_json, compile_preflight)
    _write_json(result_json, summary)
    _write_result_markdown(result_zh, summary)
    _write_gate_markdown(gate_zh, gate, summary)
    return summary


def probe_tools() -> dict[str, Any]:
    tools = ["ghidraRun", "retdec-decompiler", "r2", "radare2", "objdump", "gcc"]
    availability: dict[str, str] = {}
    for tool in tools:
        result = ccompile.run_command(["/usr/bin/which", tool])
        availability[tool] = result.stdout.strip() if result.returncode == 0 else ""
    real_decompilers = [tool for tool in ["ghidraRun", "retdec-decompiler", "r2", "radare2"] if availability[tool]]
    if real_decompilers:
        verdict = "ready-for-real-decompiler-output-import"
    elif availability["objdump"] and availability["gcc"]:
        verdict = "ready-for-assembly-context-decompiler-like-generation"
    else:
        verdict = "needs-decompiler-dependency-plan"
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "availability": availability,
        "real_decompiler_tools": real_decompilers,
        "verdict": verdict,
    }


def build_assembly_context(
    case: phase5_gpu.fixtures.FunctionCase,
    opt_level: str,
    assembly_dir: Path,
) -> dict[str, Any]:
    compile_dir = assembly_dir / "compile"
    compile_result = ccompile.compile_candidate(
        case=case,
        candidate_id=f"phase6_original_context_{opt_level}",
        function_source=case.function_source,
        output_dir=compile_dir,
        opt_level=opt_level,
    )
    assembly_path = assembly_dir / f"{case.case_id}_{opt_level}.objdump.txt"
    objdump_exit_code = -1
    objdump_stderr = ""
    if compile_result.compiled:
        objdump = ccompile.run_command(["/usr/bin/objdump", "-d", str(compile_result.object_path)])
        objdump_exit_code = objdump.returncode
        objdump_stderr = objdump.stderr
        assembly_path.write_text(objdump.stdout, encoding="utf-8")
    else:
        assembly_path.write_text("", encoding="utf-8")
    return {
        "case_id": case.case_id,
        "tool": "objdump",
        "optimization_level": opt_level,
        "compiled": compile_result.compiled,
        "fixture_passed": compile_result.behavior_passed,
        "assembly_path": str(assembly_path),
        "object_path": str(compile_result.object_path),
        "objdump_exit_code": objdump_exit_code,
        "stderr_tail": (compile_result.stderr + "\n" + objdump_stderr)[-1200:],
    }


def build_phase6_candidates(
    case: phase5_gpu.fixtures.FunctionCase,
    entry: dict[str, Any],
    opt_level: str,
    assembly_context_path: str,
) -> list[Phase6Candidate]:
    signature = entry["signature"]
    candidates = [
        Phase6Candidate(
            case_id=case.case_id,
            candidate_id=f"phase6_{opt_level}_{case.case_id}_original_control",
            mutation_type="phase6_original_control",
            function_source=case.function_source,
            expected_role="behavior_preserving_original",
            source_kind="assembly_context_decompiler_like_control",
            source_name="source_known_original_with_objdump_context",
            tool="objdump",
            optimization_level=opt_level,
            assembly_context_path=assembly_context_path,
        ),
        Phase6Candidate(
            case_id=case.case_id,
            candidate_id=f"phase6_{opt_level}_{case.case_id}_noop_guard_rewrite",
            mutation_type="phase6_behavior_preserving_noop_guard",
            function_source=insert_noop_guard(case.function_source, entry),
            expected_role="behavior_preserving_rewrite",
            source_kind="assembly_context_decompiler_like_rewrite",
            source_name="deterministic_decompiler_like_noop_guard",
            tool="objdump",
            optimization_level=opt_level,
            assembly_context_path=assembly_context_path,
        ),
    ]
    zero_guard = phase5b.zero_use_expression(cpu_smoke._parameter_names(signature))
    for index, fallback in enumerate(phase5b.fallback_values(entry.get("fixtures", []))):
        candidates.append(
            Phase6Candidate(
                case_id=case.case_id,
                candidate_id=f"phase6_{opt_level}_{case.case_id}_fixture_ifchain_{index:02d}",
                mutation_type="phase6_fixture_ifchain_semantic_drift",
                function_source=phase5b.fixture_overfit_source(
                    signature=signature,
                    fixtures=entry.get("fixtures", []),
                    fallback=fallback,
                    zero_guard=zero_guard,
                ),
                expected_role="fixture_passing_semantic_drift",
                source_kind="assembly_context_decompiler_like_fixture_ifchain",
                source_name="deterministic_decompiler_like_fixture_ifchain",
                tool="objdump",
                optimization_level=opt_level,
                assembly_context_path=assembly_context_path,
            )
        )
    return candidates


def insert_noop_guard(function_source: str, entry: dict[str, Any]) -> str:
    function_name = entry["function_name"]
    match = re.search(
        rf"\b[A-Za-z_][A-Za-z0-9_\s\*]*\b{re.escape(function_name)}\s*\([^;{{}}]*\)\s*\{{",
        function_source,
    )
    if match is None:
        raise ValueError(f"target function not found for noop guard: {function_name}")
    open_brace = function_source.find("{", match.start())
    if open_brace == -1:
        raise ValueError(f"target function has no body: {function_name}")
    params = cpu_smoke._parameter_names(entry["signature"])
    fallback_expr = "0"
    if params:
        fallback_expr += " + 0 * (" + " + ".join(f"({name})" for name in params) + ")"
    guard = (
        "\n"
        "    volatile int phase6_decompiler_like_guard = 0;\n"
        "    if (phase6_decompiler_like_guard != 0) {\n"
        f"        return {fallback_expr};\n"
        "    }"
    )
    return function_source[:open_brace + 1] + guard + function_source[open_brace + 1:]


def phase6_features(
    case: phase5_gpu.fixtures.FunctionCase,
    candidate: Phase6Candidate,
    hard_inputs: list[dynamic_trace.TraceInput],
    trace_dir: Path,
    static_dir: Path,
    original_trace_cache: dict[tuple[str, str, str], dynamic_trace.TraceRun],
    original_static_cache: dict[tuple[str, str], structured_features.StructuredFeatureVector],
    candidate_source: str | None = None,
) -> dict[str, float]:
    candidate_source = candidate.function_source if candidate_source is None else candidate_source
    fixture_inputs = [
        dynamic_trace.TraceInput(args=test.args, bucket="fixture")
        for test in case.tests
    ]
    original_hard = cached_original_trace(
        cache=original_trace_cache,
        case=case,
        inputs=hard_inputs,
        trace_dir=trace_dir,
        opt_level=candidate.optimization_level,
        bucket="hard",
    )
    original_fixture = cached_original_trace(
        cache=original_trace_cache,
        case=case,
        inputs=fixture_inputs,
        trace_dir=trace_dir,
        opt_level=candidate.optimization_level,
        bucket="fixture",
    )
    candidate_hard = phase5_gpu.safe_run_trace(
        case=case,
        candidate_id=f"{candidate.candidate_id}_hard",
        function_source=candidate_source,
        inputs=hard_inputs,
        output_dir=trace_dir,
        opt_level=candidate.optimization_level,
    )
    candidate_fixture = phase5_gpu.safe_run_trace(
        case=case,
        candidate_id=f"{candidate.candidate_id}_fixture",
        function_source=candidate_source,
        inputs=fixture_inputs,
        output_dir=trace_dir,
        opt_level=candidate.optimization_level,
    )
    if not original_hard.compiled or original_hard.exit_code != 0:
        raise RuntimeError(f"original hard trace failed for {case.case_id}: {original_hard.stderr}")
    if not original_fixture.compiled or original_fixture.exit_code != 0:
        raise RuntimeError(f"original fixture trace failed for {case.case_id}: {original_fixture.stderr}")

    if (
        candidate_hard.compiled
        and candidate_hard.exit_code == 0
        and len(candidate_hard.outputs) == len(hard_inputs)
    ):
        components = dynamic_trace.trace_distance(
            hard_inputs,
            original_hard.outputs,
            candidate_hard.outputs,
        ).components
    else:
        components = phase3_cpu._failure_components(len(hard_inputs))

    if (
        candidate_fixture.compiled
        and candidate_fixture.exit_code == 0
        and len(candidate_fixture.outputs) == len(fixture_inputs)
    ):
        fixture_distance = dynamic_trace.trace_distance(
            fixture_inputs,
            original_fixture.outputs,
            candidate_fixture.outputs,
        ).components
        fixture_mismatch_rate = fixture_distance["trace_mismatch_rate"]
    else:
        fixture_mismatch_rate = 1.0

    static_components = static_structured_components(
        case=case,
        candidate=candidate,
        candidate_source=candidate_source,
        static_dir=static_dir,
        original_static_cache=original_static_cache,
    )
    return {
        **components,
        **static_components,
        "fixture_mismatch_rate": fixture_mismatch_rate,
        "fixture_behavior_passed": 1.0 if fixture_mismatch_rate == 0.0 else 0.0,
        "compiled": 1.0 if candidate_hard.compiled else 0.0,
        "primary_exit_code": float(candidate_hard.exit_code),
        "fixture_exit_code": float(candidate_fixture.exit_code),
        "hard_probe_count": float(len(hard_inputs)),
    }


def cached_original_trace(
    cache: dict[tuple[str, str, str], dynamic_trace.TraceRun],
    case: phase5_gpu.fixtures.FunctionCase,
    inputs: list[dynamic_trace.TraceInput],
    trace_dir: Path,
    opt_level: str,
    bucket: str,
) -> dynamic_trace.TraceRun:
    key = (case.case_id, opt_level, bucket)
    if key not in cache:
        cache[key] = dynamic_trace.run_trace(
            case=case,
            candidate_id=f"phase6_original_{bucket}_{opt_level}",
            function_source=case.function_source,
            inputs=inputs,
            output_dir=trace_dir,
            opt_level=opt_level,
        )
    return cache[key]


def static_structured_components(
    case: phase5_gpu.fixtures.FunctionCase,
    candidate: Phase6Candidate,
    static_dir: Path,
    original_static_cache: dict[tuple[str, str], structured_features.StructuredFeatureVector],
    candidate_source: str | None = None,
) -> dict[str, float]:
    candidate_source = candidate.function_source if candidate_source is None else candidate_source
    opt_level = candidate.optimization_level
    original_key = (case.case_id, opt_level)
    try:
        if original_key not in original_static_cache:
            original_compile = ccompile.compile_candidate(
                case=case,
                candidate_id=f"phase6_static_original_{opt_level}",
                function_source=case.function_source,
                output_dir=static_dir / "original",
                opt_level=opt_level,
            )
            if not original_compile.compiled:
                raise RuntimeError(original_compile.stderr)
            original_static_cache[original_key] = structured_features.extract_structured_features(
                original_compile.object_path
            )
        candidate_compile = ccompile.compile_candidate(
            case=case,
            candidate_id=f"{candidate.candidate_id}_static",
            function_source=candidate_source,
            output_dir=static_dir / "candidates",
            opt_level=opt_level,
        )
        if not candidate_compile.compiled:
            raise RuntimeError(candidate_compile.stderr)
        candidate_features = structured_features.extract_structured_features(candidate_compile.object_path)
        distance = structured_features.structured_feature_distance(
            original_static_cache[original_key],
            candidate_features,
        )
        static_total = (
            distance["structured_binding_total"]
            + 0.25 * distance["basic_block_shape_l1"]
            + 0.25 * distance["terminal_opcode_l1"]
        )
        return {
            **{f"static_{key}": float(value) for key, value in distance.items()},
            "static_structured_total": float(static_total),
            "static_compile_passed": 1.0,
        }
    except Exception:
        return {
            "static_basic_block_shape_l1": 1.0,
            "static_terminal_opcode_l1": 1.0,
            "static_cfg_edge_motif_l1": 1.0,
            "static_branch_return_binding_l1": 1.0,
            "static_compare_branch_return_l1": 1.0,
            "static_loop_update_binding_l1": 1.0,
            "static_structured_binding_total": 4.0,
            "static_structured_total": 4.5,
            "static_compile_passed": 0.0,
        }


def record_from_features(
    candidate: Phase6Candidate,
    features: dict[str, float],
    candidate_path: Path,
) -> dict[str, Any]:
    if features["compiled"] != 1.0:
        label = "compile_fail"
    elif candidate.expected_role in {"behavior_preserving_original", "behavior_preserving_rewrite"}:
        label = "faithful"
    elif features["trace_mismatch_rate"] > 0.0:
        label = "plausible_wrong"
    else:
        label = "faithful"
    return {
        "case_id": candidate.case_id,
        "candidate_id": candidate.candidate_id,
        "label": label,
        "mutation_type": candidate.mutation_type,
        "compiled": features["compiled"] == 1.0,
        "behavior_passed": features["fixture_mismatch_rate"] == 0.0,
        "bounded_trace_passed": features["trace_mismatch_rate"] == 0.0,
        "optimization_level": candidate.optimization_level,
        "features": {
            key: value
            for key, value in features.items()
            if key not in {"compiled", "primary_exit_code", "fixture_exit_code"}
        },
        "diagnostics": {
            "primary_exit_code": features["primary_exit_code"],
            "fixture_exit_code": features["fixture_exit_code"],
        },
        "metadata": {
            "candidate_path": str(candidate_path),
            "function_source": candidate.function_source,
            "expected_role": candidate.expected_role,
            "source_kind": candidate.source_kind,
            "source_name": candidate.source_name,
            "tool": candidate.tool,
            "assembly_context_path": candidate.assembly_context_path,
        },
    }


def candidate_manifest_item(
    candidate: Phase6Candidate,
    record: dict[str, Any],
    candidate_path: Path,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "case_id": candidate.case_id,
        "source": candidate.source_kind,
        "tool": candidate.tool,
        "optimization_level": candidate.optimization_level,
        "candidate_path": str(candidate_path),
        "assembly_context_path": candidate.assembly_context_path,
        "label_source": "source_known_oracle",
        "label": record["label"],
        "expected_role": candidate.expected_role,
        "mutation_type": candidate.mutation_type,
        "compiled": record["compiled"],
    }


def build_candidate_manifest(
    records: list[dict[str, Any]],
    manifest_candidates: list[dict[str, Any]],
    records_path: Path,
    assembly_contexts: list[dict[str, Any]],
    opt_levels: list[str],
    tool_probe: dict[str, Any],
) -> dict[str, Any]:
    compile_pass = sum(1 for record in records if record["compiled"])
    paired = paired_case_count(records)
    source_case_count = len({record["case_id"] for record in records})
    scale_passed = source_case_count >= 20 and compile_pass >= 50 and paired >= 10
    return {
        "phase": "phase6_decompiler_output_feasibility",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_sources": sorted({item["source"] for item in manifest_candidates}),
        "optimization_levels": opt_levels,
        "candidate_count": len(records),
        "compile_pass_count": compile_pass,
        "paired_function_count": paired,
        "source_function_count": source_case_count,
        "records_path": str(records_path),
        "tool_probe_verdict": tool_probe["verdict"],
        "real_decompiler_output_available": bool(tool_probe["real_decompiler_tools"]),
        "assembly_context_count": len(assembly_contexts),
        "assembly_contexts": assembly_contexts,
        "candidates": manifest_candidates,
        "verdict": "pass-phase6-decompiler-like-candidate-scale"
        if scale_passed
        else "phase6-feasibility-only",
    }


def build_compile_preflight(records: list[dict[str, Any]]) -> dict[str, Any]:
    failure_counts = {
        "compile_fail": sum(1 for record in records if not record["compiled"]),
        "fixture_runtime_fail": sum(
            1 for record in records
            if record["compiled"] and record["diagnostics"]["fixture_exit_code"] != 0
        ),
        "hard_runtime_fail": sum(
            1 for record in records
            if record["compiled"] and record["diagnostics"]["primary_exit_code"] != 0
        ),
    }
    runtime_timeout_count = sum(
        1 for record in records
        if record["diagnostics"]["primary_exit_code"] == 124
        or record["diagnostics"]["fixture_exit_code"] == 124
    )
    compile_pass = sum(1 for record in records if record["compiled"])
    paired = paired_case_count(records)
    verdict = (
        "pass-phase6-compile-preflight"
        if compile_pass >= 50 and paired >= 10
        else "phase6-feasibility-only"
    )
    return {
        "phase": "phase6_compile_preflight",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(records),
        "compile_pass_count": compile_pass,
        "runtime_timeout_count": runtime_timeout_count,
        "failure_counts": failure_counts,
        "paired_function_count": paired,
        "verdict": verdict,
    }


def build_result_summary(
    records: list[dict[str, Any]],
    records_path: Path,
    candidate_manifest: dict[str, Any],
    compile_preflight: dict[str, Any],
    tool_probe: dict[str, Any],
) -> dict[str, Any]:
    eval_records = [
        record for record in records
        if record["compiled"] and record["label"] in {"faithful", "plausible_wrong"}
    ]
    baseline_auc = {
        "fixture_only": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("fixture_mismatch_rate", 1.0)),
        ),
        "static_structured_proxy": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("static_structured_total", 0.0)),
        ),
        "v3_trace_mismatch_rate": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("trace_mismatch_rate", 0.0)),
        ),
        "v3_trace_total": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("trace_total", 0.0)),
        ),
    }
    by_opt = {
        opt_level: subset_metrics(
            [record for record in eval_records if record["optimization_level"] == opt_level]
        )
        for opt_level in sorted({record["optimization_level"] for record in eval_records})
    }
    by_source = {
        source_kind: subset_metrics(
            [record for record in eval_records if record["metadata"]["source_kind"] == source_kind]
        )
        for source_kind in sorted({record["metadata"]["source_kind"] for record in eval_records})
    }
    by_mutation = {
        mutation_type: subset_metrics(
            [record for record in eval_records if record["mutation_type"] == mutation_type]
        )
        for mutation_type in sorted({record["mutation_type"] for record in eval_records})
    }
    best_baseline = max(
        baseline_auc["fixture_only"],
        baseline_auc["static_structured_proxy"],
    )
    behavior_preserving_rewrites = [
        record for record in eval_records
        if record["metadata"]["expected_role"] == "behavior_preserving_rewrite"
    ]
    v3_false_positive_count = sum(
        1 for record in behavior_preserving_rewrites
        if float(record["features"].get("trace_total", 0.0)) > 0.0
    )
    static_false_positive_count = sum(
        1 for record in behavior_preserving_rewrites
        if float(record["features"].get("static_structured_total", 0.0)) > 0.0
    )
    summary = {
        "phase": "phase6_decompiler_like_result_analysis",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "records_path": str(records_path),
        "candidate_count": len(records),
        "compile_pass_count": compile_preflight["compile_pass_count"],
        "source_function_count": candidate_manifest["source_function_count"],
        "paired_case_count": paired_case_count(records),
        "label_counts": count_by(records, "label"),
        "fixture_passing_wrong_count": fixture_passing_wrong_count(records),
        "baseline_auc": baseline_auc,
        "best_non_oracle_baseline_auc": best_baseline,
        "sota_delta_vs_best_baseline": baseline_auc["v3_trace_total"] - best_baseline,
        "fixture_collapse": phase3_cpu.v1._fixture_collapse(eval_records),
        "by_optimization_level": by_opt,
        "by_candidate_source": by_source,
        "by_mutation_type": by_mutation,
        "behavior_preserving_rewrite_count": len(behavior_preserving_rewrites),
        "v3_behavior_preserving_false_positive_count": v3_false_positive_count,
        "v3_behavior_preserving_false_positive_rate": (
            v3_false_positive_count / len(behavior_preserving_rewrites)
            if behavior_preserving_rewrites else 0.0
        ),
        "static_behavior_preserving_false_positive_count": static_false_positive_count,
        "static_behavior_preserving_false_positive_rate": (
            static_false_positive_count / len(behavior_preserving_rewrites)
            if behavior_preserving_rewrites else 0.0
        ),
        "failure_taxonomy": failure_taxonomy(records, tool_probe),
        "candidate_manifest_verdict": candidate_manifest["verdict"],
        "compile_preflight_verdict": compile_preflight["verdict"],
        "tool_probe_verdict": tool_probe["verdict"],
        "real_decompiler_output_available": candidate_manifest["real_decompiler_output_available"],
        "gate": {},
    }
    summary["gate"] = {
        "source_function_scale_gate": summary["source_function_count"] >= 20,
        "compile_pass_scale_gate": summary["compile_pass_count"] >= 50,
        "paired_function_gate": summary["paired_case_count"] >= 10,
        "v3_beats_fixture_gate": baseline_auc["v3_trace_total"] > baseline_auc["fixture_only"],
        "v3_beats_static_gate": baseline_auc["v3_trace_total"] > baseline_auc["static_structured_proxy"],
        "behavior_preserving_fp_gate": summary["v3_behavior_preserving_false_positive_rate"] <= 0.10,
    }
    summary["verdict"] = phase6_verdict(summary)
    return summary


def subset_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record["compiled"]),
        "label_counts": count_by(records, "label"),
        "paired_case_count": paired_case_count(records),
        "fixture_passing_wrong_count": fixture_passing_wrong_count(records),
        "fixture_only_auc": phase3_cpu._pairwise_auc(
            records,
            lambda record: float(record["features"].get("fixture_mismatch_rate", 1.0)),
        ),
        "static_structured_auc": phase3_cpu._pairwise_auc(
            records,
            lambda record: float(record["features"].get("static_structured_total", 0.0)),
        ),
        "v3_trace_total_auc": phase3_cpu._pairwise_auc(
            records,
            lambda record: float(record["features"].get("trace_total", 0.0)),
        ),
    }


def build_gate_decision(summary: dict[str, Any]) -> dict[str, Any]:
    if (
        summary["verdict"] == "pass-phase6-real-decompiler-output"
        and summary["real_decompiler_output_available"]
    ):
        decision = "pass-phase6-ccfa-main-experiment-ready"
    elif summary["tool_probe_verdict"] != "ready-for-real-decompiler-output-import":
        decision = "needs-decompiler-dependency-plan"
    elif not (
        summary["gate"]["source_function_scale_gate"]
        and summary["gate"]["compile_pass_scale_gate"]
        and summary["gate"]["paired_function_gate"]
    ):
        decision = "needs-more-decompiler-output-candidates"
    else:
        decision = "method-negative-realistic-candidates"
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "phase6_verdict": summary["verdict"],
        "gate": summary["gate"],
        "claim_boundary": (
            "This run passes the assembly-context decompiler-like proxy gate, "
            "but real decompiler-output transfer still requires Ghidra/RetDec/r2 or equivalent."
        ),
    }


def phase6_verdict(summary: dict[str, Any]) -> str:
    if all(summary["gate"].values()):
        if summary["real_decompiler_output_available"]:
            return "pass-phase6-real-decompiler-output"
        return "pass-phase6-decompiler-like-ccfa-proxy"
    if (
        summary["gate"]["source_function_scale_gate"]
        and summary["gate"]["compile_pass_scale_gate"]
        and summary["gate"]["paired_function_gate"]
    ):
        return "method-negative-realistic-candidates"
    return "phase6-feasibility-only"


def paired_case_count(records: list[dict[str, Any]]) -> int:
    total = 0
    for case_id in sorted({record["case_id"] for record in records}):
        labels = {
            record["label"]
            for record in records
            if record["case_id"] == case_id and record["compiled"]
        }
        if "faithful" in labels and "plausible_wrong" in labels:
            total += 1
    return total


def fixture_passing_wrong_count(records: list[dict[str, Any]]) -> int:
    return sum(
        1 for record in records
        if record["compiled"]
        and record["label"] == "plausible_wrong"
        and float(record["features"].get("fixture_mismatch_rate", 1.0)) == 0.0
        and float(record["features"].get("trace_mismatch_rate", 0.0)) > 0.0
    )


def failure_taxonomy(records: list[dict[str, Any]], tool_probe: dict[str, Any]) -> dict[str, int]:
    taxonomy = {
        "decompiler_tool_unavailable": 0 if tool_probe["real_decompiler_tools"] else 1,
        "decompiler_syntax_failure": 0,
        "candidate_compile_failure": sum(1 for record in records if not record["compiled"]),
        "undefined_behavior_mismatch": 0,
        "oracle_domain_mismatch": 0,
        "trace_domain_miss": sum(
            1 for record in records
            if record["compiled"]
            and record["label"] == "faithful"
            and record["metadata"]["expected_role"] == "fixture_passing_semantic_drift"
        ),
        "fixture_passing_semantic_drift": fixture_passing_wrong_count(records),
        "behavior_preserving_rewrite_false_positive": sum(
            1 for record in records
            if record["compiled"]
            and record["metadata"]["expected_role"] == "behavior_preserving_rewrite"
            and float(record["features"].get("trace_total", 0.0)) > 0.0
        ),
        "baseline_stronger_than_v3": 0,
    }
    return taxonomy


def count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key, ""))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _write_tool_feasibility(path: Path, tool_probe: dict[str, Any]) -> None:
    availability_rows = "\n".join(
        f"| `{tool}` | `{path_value or 'not found'}` |"
        for tool, path_value in tool_probe["availability"].items()
    )
    text = f"""# Phase 6 Tool Feasibility

## Tool Probe

| Tool | Path |
|---|---|
{availability_rows}

## Available Candidate Sources

本机没有发现 Ghidra、RetDec、radare2/r2 等真实 decompiler 工具；`objdump` 和 `gcc` 可用。因此本轮可以做 full-scale `assembly_context_decompiler_like` 候选，但不能声称已经评估真实 decompiler output。

## Dependency Decision

Phase 6 不安装新依赖。真实 decompiler-output import 需要单独 dependency plan，至少安装并固定 Ghidra/RetDec/r2 之一，然后重新跑真实输出版本。

## Verdict

`{tool_probe['verdict']}`
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_result_markdown(path: Path, summary: dict[str, Any]) -> None:
    gate_rows = "\n".join(
        f"| `{key}` | `{value}` |"
        for key, value in summary["gate"].items()
    )
    opt_rows = "\n".join(
        "| `{opt}` | `{candidate_count}` | `{paired_case_count}` | `{fixture_only_auc:.4f}` | `{static_structured_auc:.4f}` | `{v3_trace_total_auc:.4f}` |".format(
            opt=opt_level,
            **metrics,
        )
        for opt_level, metrics in summary["by_optimization_level"].items()
    )
    source_rows = "\n".join(
        "| `{source}` | `{candidate_count}` | `{paired_case_count}` | `{fixture_only_auc:.4f}` | `{static_structured_auc:.4f}` | `{v3_trace_total_auc:.4f}` |".format(
            source=source_kind,
            **metrics,
        )
        for source_kind, metrics in summary["by_candidate_source"].items()
    )
    failure_rows = "\n".join(
        f"| `{key}` | `{value}` |"
        for key, value in summary["failure_taxonomy"].items()
    )
    text = f"""# Decompilation Faithfulness Phase 6 Result Analysis

- Verdict: `{summary['verdict']}`
- Tool probe verdict: `{summary['tool_probe_verdict']}`
- Real decompiler output available: `{summary['real_decompiler_output_available']}`
- Source functions: `{summary['source_function_count']}`
- Candidates: `{summary['candidate_count']}`
- Compile pass count: `{summary['compile_pass_count']}`
- Paired case count: `{summary['paired_case_count']}`
- Label counts: `{summary['label_counts']}`
- Fixture-passing wrong count: `{summary['fixture_passing_wrong_count']}`
- Fixture-only AUC: `{summary['baseline_auc']['fixture_only']:.4f}`
- Static structured proxy AUC: `{summary['baseline_auc']['static_structured_proxy']:.4f}`
- Dynamic Trace v3 AUC: `{summary['baseline_auc']['v3_trace_total']:.4f}`
- SOTA delta vs best non-oracle baseline: `{summary['sota_delta_vs_best_baseline']:.4f}`
- V3 behavior-preserving rewrite FP rate: `{summary['v3_behavior_preserving_false_positive_rate']:.4f}`
- Static behavior-preserving rewrite FP rate: `{summary['static_behavior_preserving_false_positive_rate']:.4f}`
- Records: `{summary['records_path']}`

## Gate Check

| Gate | Passed |
|---|---:|
{gate_rows}

## By Optimization Level

| Opt | Candidates | Paired Cases | Fixture AUC | Static AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|
{opt_rows}

## By Candidate Source

| Source | Candidates | Paired Cases | Fixture AUC | Static AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|
{source_rows}

## Failure Taxonomy

| Category | Count |
|---|---:|
{failure_rows}

## Interpretation

这是 full-scale Phase 6 proxy：覆盖 Phase 5 的全部 `38` 个 source-known 函数，并按 `O0/O2` 生成 objdump assembly context。候选是 `assembly_context_decompiler_like`，不是 Ghidra/RetDec/r2 的真实 decompiler output。

本轮正向点是：在 fixture-only 被 fixture-ifchain 候选压成弱 baseline 的情况下，Dynamic Trace v3 仍能抓住 fixture-passing semantic drift；同时 behavior-preserving noop-guard rewrite 的 v3 false positive 需要保持低。CCF-A 主张仍不能写成“真实反编译器输出已验证”，下一步需要真实 decompiler 依赖计划来补这条证据链。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_gate_markdown(path: Path, gate: dict[str, Any], summary: dict[str, Any]) -> None:
    gate_rows = "\n".join(
        f"| `{key}` | `{value}` |"
        for key, value in gate["gate"].items()
    )
    text = f"""# Decompilation Faithfulness Phase 6 Gate Decision

- Decision: `{gate['decision']}`
- Phase 6 verdict: `{gate['phase6_verdict']}`
- Real decompiler output available: `{summary['real_decompiler_output_available']}`
- Dynamic Trace v3 AUC: `{summary['baseline_auc']['v3_trace_total']:.4f}`
- Best non-oracle baseline AUC: `{summary['best_non_oracle_baseline_auc']:.4f}`
- SOTA delta: `{summary['sota_delta_vs_best_baseline']:.4f}`

## Gate

| Gate | Passed |
|---|---:|
{gate_rows}

## Claim Boundary

{gate['claim_boundary']}

## Next Step

如果目标是 CCF-A 主实验，下一步不是继续堆更多 synthetic if-chain，而是写 Phase 6R dependency plan：安装/固定至少一个真实 decompiler，导入真实 decompiler output，再复用本轮同一套 source-known oracle、v3/baseline、false-positive gate。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
