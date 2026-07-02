from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu
from analysis.decompile_faithfulness import run_phase5b_hard_candidates as phase5b
from analysis.decompile_faithfulness import run_phase6_decompiler_like_candidates as phase6


DEFAULT_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_function_manifest.json")
DEFAULT_PREFLIGHT = Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_import_preflight.json")
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase7_static_hard")
DEFAULT_CANDIDATE_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase7_static_hard_candidate_manifest.json")
DEFAULT_COMPILE_PREFLIGHT = Path("docs/paper_agent/decompile_faithfulness_phase7_static_hard_compile_preflight.json")
DEFAULT_RESULT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase7_static_hard_result.json")
DEFAULT_RESULT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase7_static_hard_result.zh.md")
DEFAULT_OPT_LEVELS = ("O0", "O2")


@dataclass(frozen=True)
class StaticHardMutation:
    suffix: str
    mutation_type: str
    function_source: str
    description: str


def main() -> None:
    args = parse_args()
    summary = run_static_hard(
        repo_root=args.repo_root,
        manifest_json=args.manifest_json,
        preflight_json=args.preflight_json,
        output_dir=args.output_dir,
        candidate_manifest_json=args.candidate_manifest_json,
        compile_preflight_json=args.compile_preflight_json,
        result_json=args.result_json,
        result_zh=args.result_zh,
        opt_levels=args.opt_level,
        max_mutations_per_function=args.max_mutations_per_function,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "source_function_count": summary["source_function_count"],
                "candidate_count": summary["candidate_count"],
                "compile_pass_count": summary["compile_pass_count"],
                "paired_case_count": summary["paired_case_count"],
                "static_auc": summary["baseline_auc"]["static_structured_proxy"],
                "v3_auc": summary["baseline_auc"]["v3_trace_total"],
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
    parser.add_argument("--candidate-manifest-json", type=Path, default=DEFAULT_CANDIDATE_MANIFEST)
    parser.add_argument("--compile-preflight-json", type=Path, default=DEFAULT_COMPILE_PREFLIGHT)
    parser.add_argument("--result-json", type=Path, default=DEFAULT_RESULT_JSON)
    parser.add_argument("--result-zh", type=Path, default=DEFAULT_RESULT_ZH)
    parser.add_argument("--opt-level", action="append", default=list(DEFAULT_OPT_LEVELS))
    parser.add_argument("--max-mutations-per-function", type=int, default=5)
    return parser.parse_args()


def run_static_hard(
    repo_root: Path,
    manifest_json: Path,
    preflight_json: Path,
    output_dir: Path,
    candidate_manifest_json: Path,
    compile_preflight_json: Path,
    result_json: Path,
    result_zh: Path,
    opt_levels: list[str],
    max_mutations_per_function: int,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    manifest_json = _resolve(repo_root, manifest_json)
    preflight_json = _resolve(repo_root, preflight_json)
    output_dir = _resolve(repo_root, output_dir)
    candidate_manifest_json = _resolve(repo_root, candidate_manifest_json)
    compile_preflight_json = _resolve(repo_root, compile_preflight_json)
    result_json = _resolve(repo_root, result_json)
    result_zh = _resolve(repo_root, result_zh)

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    preflight = json.loads(preflight_json.read_text(encoding="utf-8"))
    if preflight.get("verdict") != "pass-phase7-codefuse-import":
        raise RuntimeError(f"Phase7 CodeFuse import must pass first: {preflight.get('verdict')}")

    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir = output_dir / "candidates"
    trace_dir = output_dir / "traces"
    assembly_dir = output_dir / "assembly"
    static_dir = output_dir / "static_compile"
    for path in [candidate_dir, trace_dir, assembly_dir, static_dir]:
        path.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    manifest_candidates: list[dict[str, Any]] = []
    assembly_contexts: list[dict[str, Any]] = []
    original_trace_cache: dict[tuple[str, str, str], Any] = {}
    original_static_cache: dict[tuple[str, str], Any] = {}
    records_path = output_dir / "records.jsonl"

    risk_by_case = {
        entry["case_id"]: list(entry.get("risk_families", []))
        for entry in manifest.get("functions", [])
    }
    entries = [
        entry for entry in manifest.get("functions", [])
        if entry.get("counts_for_phase7_public_benchmark_gate")
    ]
    for entry in entries:
        case = phase5_gpu._case_from_manifest_entry(repo_root, entry)
        hard_inputs = phase5b.phase5b_hard_trace_inputs(entry, max_inputs=128)
        mutations = generate_static_hard_mutations(case.function_source, max_mutations=max_mutations_per_function)
        for opt_level in opt_levels:
            assembly_context = phase6.build_assembly_context(
                case=case,
                opt_level=opt_level,
                assembly_dir=assembly_dir,
            )
            assembly_contexts.append(assembly_context)
            candidates = build_candidates_for_case(
                case=case,
                opt_level=opt_level,
                assembly_context_path=assembly_context["assembly_path"],
                mutations=mutations,
            )
            for candidate in candidates:
                candidate_path = candidate_dir / f"{candidate.candidate_id}.c"
                candidate_path.write_text(candidate.function_source, encoding="utf-8")
                features = phase6.phase6_features(
                    case=case,
                    candidate=candidate,
                    hard_inputs=hard_inputs,
                    trace_dir=trace_dir,
                    static_dir=static_dir,
                    original_trace_cache=original_trace_cache,
                    original_static_cache=original_static_cache,
                )
                record = phase6.record_from_features(candidate, features, candidate_path)
                record["metadata"]["benchmark"] = manifest.get("benchmark", "CodeFuse-DeBench")
                record["metadata"]["risk_families"] = risk_by_case.get(candidate.case_id, [])
                records.append(record)
                manifest_candidates.append(phase6.candidate_manifest_item(candidate, record, candidate_path))

    _write_jsonl(records_path, records)
    candidate_manifest = build_candidate_manifest(
        manifest=manifest,
        records=records,
        manifest_candidates=manifest_candidates,
        records_path=records_path,
        assembly_contexts=assembly_contexts,
        opt_levels=opt_levels,
    )
    compile_preflight = build_compile_preflight(records)
    summary = build_result_summary(
        manifest=manifest,
        records=records,
        records_path=records_path,
        candidate_manifest=candidate_manifest,
        compile_preflight=compile_preflight,
        risk_by_case=risk_by_case,
    )
    _write_json(candidate_manifest_json, candidate_manifest)
    _write_json(compile_preflight_json, compile_preflight)
    _write_json(result_json, summary)
    write_markdown(result_zh, summary)
    return summary


def generate_static_hard_mutations(source: str, max_mutations: int = 5) -> list[StaticHardMutation]:
    normalized = strip_c_comments(source)
    candidates: list[StaticHardMutation] = []
    seen_sources = {normalized}
    rules: list[tuple[str, str, str, str]] = [
        (r"(?<![<>=!])>(?![=>])", ">=", "predicate_strictness", "Change strict greater-than to greater-or-equal."),
        (r"(?<![<>=!])<(?![=<])", "<=", "predicate_strictness", "Change strict less-than to less-or-equal."),
        (r">=", ">", "predicate_strictness", "Change greater-or-equal to strict greater-than."),
        (r"<=", "<", "predicate_strictness", "Change less-or-equal to strict less-than."),
        (r"==", "!=", "predicate_equality", "Invert one equality check."),
        (r"!=", "==", "predicate_equality", "Invert one inequality check."),
        (r"\+=", "-=", "compound_assignment", "Change one additive update to subtraction."),
        (r"-=", "+=", "compound_assignment", "Change one subtractive update to addition."),
        (r"\*=", "+=", "compound_assignment", "Change one multiplicative update to addition."),
        (r"(?<=[A-Za-z0-9_\)])\s*\+\s*(?=[A-Za-z0-9_\(])", " - ", "arithmetic_operator", "Change one addition to subtraction."),
        (r"(?<=[A-Za-z0-9_\)])\s*-\s*(?=[A-Za-z0-9_\(])", " + ", "arithmetic_operator", "Change one subtraction to addition."),
        (r"(?<=[A-Za-z0-9_\)])\s*\*\s*(?=[A-Za-z0-9_\(])", " + ", "arithmetic_operator", "Change one multiplication to addition."),
        (r"(?<=[A-Za-z0-9_\)])\s*/\s*(?=[A-Za-z0-9_\(])", " % ", "arithmetic_operator", "Change one division to modulo."),
        (r"(?<=[A-Za-z0-9_\)])\s*%\s*(?=[A-Za-z0-9_\(])", " / ", "arithmetic_operator", "Change one modulo to division."),
        (r"<<", ">>", "bitshift_direction", "Change one left shift to right shift."),
        (r">>", "<<", "bitshift_direction", "Change one right shift to left shift."),
        (r"(?<=[A-Za-z0-9_\)])\s*&\s*(?=[A-Za-z0-9_\(])", " | ", "bitwise_operator", "Change one bitwise-and to bitwise-or."),
        (r"(?<=[A-Za-z0-9_\)])\s*\|\s*(?=[A-Za-z0-9_\(])", " & ", "bitwise_operator", "Change one bitwise-or to bitwise-and."),
    ]
    for index, (pattern, replacement, mutation_type, description) in enumerate(rules):
        mutated = replace_first_in_body(normalized, pattern, replacement)
        if mutated is None or mutated in seen_sources:
            continue
        seen_sources.add(mutated)
        candidates.append(
            StaticHardMutation(
                suffix=f"{mutation_type}_{index:02d}",
                mutation_type=f"phase7_static_hard_{mutation_type}",
                function_source=mutated,
                description=description,
            )
        )
        if len(candidates) >= max_mutations:
            return candidates

    return_mutation = perturb_first_return_expression(normalized)
    if return_mutation is not None and return_mutation not in seen_sources:
        candidates.append(
            StaticHardMutation(
                suffix="return_expr_plus_one",
                mutation_type="phase7_static_hard_return_expression",
                function_source=return_mutation,
                description="Add one to the first returned expression.",
            )
        )
    if len(candidates) >= max_mutations:
        return candidates[:max_mutations]

    constant_mutation = perturb_first_numeric_constant(normalized)
    if constant_mutation is not None and constant_mutation not in seen_sources:
        candidates.append(
            StaticHardMutation(
                suffix="constant_plus_one",
                mutation_type="phase7_static_hard_constant",
                function_source=constant_mutation,
                description="Increment one numeric constant in the body.",
            )
        )
    return candidates[:max_mutations]


def build_candidates_for_case(
    case: phase5_gpu.fixtures.FunctionCase,
    opt_level: str,
    assembly_context_path: str,
    mutations: list[StaticHardMutation],
) -> list[phase6.Phase6Candidate]:
    candidates = [
        phase6.Phase6Candidate(
            case_id=case.case_id,
            candidate_id=f"phase7c2_{opt_level}_{case.case_id}_original_control",
            mutation_type="phase7_static_hard_original_control",
            function_source=case.function_source,
            expected_role="behavior_preserving_original",
            source_kind="phase7_static_hard_control",
            source_name="source_known_original_with_objdump_context",
            tool="objdump",
            optimization_level=opt_level,
            assembly_context_path=assembly_context_path,
        )
    ]
    for index, mutation in enumerate(mutations):
        candidates.append(
            phase6.Phase6Candidate(
                case_id=case.case_id,
                candidate_id=f"phase7c2_{opt_level}_{case.case_id}_{mutation.suffix}_{index:02d}",
                mutation_type=mutation.mutation_type,
                function_source=mutation.function_source,
                expected_role="static_hard_semantic_drift",
                source_kind="phase7_static_hard_micro_mutation",
                source_name="source_level_single_token_semantic_drift",
                tool="objdump",
                optimization_level=opt_level,
                assembly_context_path=assembly_context_path,
            )
        )
    return candidates


def strip_c_comments(source: str) -> str:
    without_blocks = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//.*", "", without_blocks)


def replace_first_in_body(source: str, pattern: str, replacement: str) -> str | None:
    split = source.find("{")
    if split == -1:
        return None
    head = source[: split + 1]
    body = source[split + 1 :]
    mutated_body, count = re.subn(pattern, replacement, body, count=1)
    if count != 1:
        return None
    mutated = head + mutated_body
    return mutated if mutated != source else None


def perturb_first_return_expression(source: str) -> str | None:
    split = source.find("{")
    if split == -1:
        return None
    head = source[: split + 1]
    body = source[split + 1 :]

    def repl(match: re.Match[str]) -> str:
        expression = match.group("expr").strip()
        if not expression:
            return match.group(0)
        return f"return ({expression}) + 1;"

    mutated_body, count = re.subn(r"return\s+(?P<expr>[^;]+);", repl, body, count=1)
    if count != 1:
        return None
    mutated = head + mutated_body
    return mutated if mutated != source else None


def perturb_first_numeric_constant(source: str) -> str | None:
    split = source.find("{")
    if split == -1:
        return None
    head = source[: split + 1]
    body = source[split + 1 :]

    def repl(match: re.Match[str]) -> str:
        value = int(match.group(0))
        return str(value + 1)

    mutated_body, count = re.subn(r"(?<![A-Za-z0-9_])-?\d+(?![A-Za-z0-9_])", repl, body, count=1)
    if count != 1:
        return None
    mutated = head + mutated_body
    return mutated if mutated != source else None


def build_candidate_manifest(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    manifest_candidates: list[dict[str, Any]],
    records_path: Path,
    assembly_contexts: list[dict[str, Any]],
    opt_levels: list[str],
) -> dict[str, Any]:
    compile_pass = sum(1 for record in records if record["compiled"])
    paired = phase6.paired_case_count(records)
    source_case_count = len({record["case_id"] for record in records})
    return {
        "phase": "phase7_static_hard_candidate_manifest",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": manifest.get("benchmark", "CodeFuse-DeBench"),
        "source_function_count": source_case_count,
        "candidate_count": len(records),
        "compile_pass_count": compile_pass,
        "paired_function_count": paired,
        "records_path": str(records_path),
        "optimization_levels": opt_levels,
        "assembly_context_count": len(assembly_contexts),
        "assembly_contexts": assembly_contexts,
        "candidate_sources": sorted({item["source"] for item in manifest_candidates}),
        "candidates": manifest_candidates,
        "verdict": (
            "pass-phase7-static-hard-candidate-scale"
            if source_case_count >= 50 and compile_pass >= 100 and paired >= 30
            else "needs-more-phase7-static-hard-candidates"
        ),
        "gpu_decision": "not-needed-for-cpu-static-hard-eval",
    }


def build_compile_preflight(records: list[dict[str, Any]]) -> dict[str, Any]:
    compile_pass = sum(1 for record in records if record["compiled"])
    paired = phase6.paired_case_count(records)
    return {
        "phase": "phase7_static_hard_compile_preflight",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(records),
        "compile_pass_count": compile_pass,
        "paired_function_count": paired,
        "failure_counts": {
            "compile_fail": sum(1 for record in records if not record["compiled"]),
            "fixture_runtime_fail": sum(
                1 for record in records
                if record["compiled"] and record["diagnostics"]["fixture_exit_code"] != 0
            ),
            "hard_runtime_fail": sum(
                1 for record in records
                if record["compiled"] and record["diagnostics"]["primary_exit_code"] != 0
            ),
        },
        "verdict": (
            "pass-phase7-static-hard-compile-preflight"
            if compile_pass >= 100 and paired >= 30
            else "needs-more-phase7-static-hard-compile-pass"
        ),
    }


def build_result_summary(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    records_path: Path,
    candidate_manifest: dict[str, Any],
    compile_preflight: dict[str, Any],
    risk_by_case: dict[str, list[str]],
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
        "v3_trace_total": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("trace_total", 0.0)),
        ),
    }
    best_baseline = max(baseline_auc["fixture_only"], baseline_auc["static_structured_proxy"])
    summary: dict[str, Any] = {
        "phase": "phase7_static_hard_result_analysis",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": manifest.get("benchmark", "CodeFuse-DeBench"),
        "records_path": str(records_path),
        "source_function_count": candidate_manifest["source_function_count"],
        "candidate_count": len(records),
        "compile_pass_count": compile_preflight["compile_pass_count"],
        "paired_case_count": phase6.paired_case_count(records),
        "label_counts": phase6.count_by(records, "label"),
        "fixture_passing_wrong_count": phase6.fixture_passing_wrong_count(records),
        "fixture_collapse": phase3_cpu.v1._fixture_collapse(eval_records),
        "baseline_auc": baseline_auc,
        "best_non_oracle_baseline_auc": best_baseline,
        "sota_delta_vs_best_baseline": baseline_auc["v3_trace_total"] - best_baseline,
        "by_mutation_type": {
            mutation: phase6.subset_metrics(
                [record for record in eval_records if record["mutation_type"] == mutation]
            )
            for mutation in sorted({record["mutation_type"] for record in eval_records})
        },
        "by_risk_family": {
            risk: phase6.subset_metrics(
                [record for record in eval_records if risk in risk_by_case.get(record["case_id"], [])]
            )
            for risk in sorted({risk for risks in risk_by_case.values() for risk in risks})
        },
        "failure_taxonomy": {
            "candidate_compile_failure": sum(1 for record in records if not record["compiled"]),
            "fixture_passing_semantic_drift": phase6.fixture_passing_wrong_count(records),
            "trace_domain_miss": sum(
                1 for record in records
                if record["compiled"]
                and record["label"] == "faithful"
                and record["metadata"]["expected_role"] == "static_hard_semantic_drift"
            ),
        },
        "candidate_manifest_verdict": candidate_manifest["verdict"],
        "compile_preflight_verdict": compile_preflight["verdict"],
        "gate": {},
    }
    summary["gate"] = {
        "source_function_scale_gate": summary["source_function_count"] >= 50,
        "compile_pass_scale_gate": summary["compile_pass_count"] >= 100,
        "paired_function_gate": summary["paired_case_count"] >= 30,
        "v3_beats_fixture_gate": baseline_auc["v3_trace_total"] > baseline_auc["fixture_only"],
        "v3_beats_static_gate": baseline_auc["v3_trace_total"] > baseline_auc["static_structured_proxy"],
        "sota_delta_gate": summary["sota_delta_vs_best_baseline"] >= 0.05,
        "fixture_collapse_gate": not summary["fixture_collapse"],
    }
    summary["verdict"] = static_hard_verdict(summary)
    return summary


def static_hard_verdict(summary: dict[str, Any]) -> str:
    if all(summary["gate"].values()):
        return "pass-phase7-static-hard-sota-delta"
    if (
        summary["gate"]["source_function_scale_gate"]
        and summary["gate"]["compile_pass_scale_gate"]
        and summary["gate"]["paired_function_gate"]
    ):
        return "method-negative-static-hard"
    return "needs-more-static-hard-candidates"


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    gate_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in summary["gate"].items())
    mutation_rows = "\n".join(
        "| `{mutation}` | `{candidate_count}` | `{paired_case_count}` | `{fixture_only_auc:.4f}` | "
        "`{static_structured_auc:.4f}` | `{v3_trace_total_auc:.4f}` |".format(
            mutation=mutation,
            **metrics,
        )
        for mutation, metrics in summary["by_mutation_type"].items()
    )
    text = f"""# Decompilation Faithfulness Phase 7 Static-hard Result

- Verdict: `{summary['verdict']}`
- Benchmark: `{summary['benchmark']}`
- Source functions: `{summary['source_function_count']}`
- Candidates: `{summary['candidate_count']}`
- Compile pass count: `{summary['compile_pass_count']}`
- Paired case count: `{summary['paired_case_count']}`
- Label counts: `{summary['label_counts']}`
- Fixture-passing wrong count: `{summary['fixture_passing_wrong_count']}`
- Fixture-only AUC: `{summary['baseline_auc']['fixture_only']:.4f}`
- Static structured proxy AUC: `{summary['baseline_auc']['static_structured_proxy']:.4f}`
- Dynamic Trace v3 AUC: `{summary['baseline_auc']['v3_trace_total']:.4f}`
- Delta vs best non-oracle baseline: `{summary['sota_delta_vs_best_baseline']:.4f}`
- Records: `{summary['records_path']}`

## Gate Check

| Gate | Passed |
|---|---:|
{gate_rows}

## Mutation Breakdown

| Mutation | Candidates | Paired Cases | Fixture AUC | Static AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|
{mutation_rows}

## Interpretation

Phase 7C2 专门补 `static-hard` 候选：每个候选只做一次局部源码微扰，尽量保留原函数控制结构和编译形态，用来检查 Phase 7C 中 static baseline 过强是否只是因为 fixture-ifchain 候选结构太明显。
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
