from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu
from analysis.decompile_faithfulness import run_phase5b_hard_candidates as phase5b
from analysis.decompile_faithfulness import run_phase6_decompiler_like_candidates as phase6


DEFAULT_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_function_manifest.json")
DEFAULT_PREFLIGHT = Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_import_preflight.json")
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase7_public_benchmark_eval")
DEFAULT_CANDIDATE_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase7_public_candidate_manifest.json")
DEFAULT_COMPILE_PREFLIGHT = Path("docs/paper_agent/decompile_faithfulness_phase7_public_compile_preflight.json")
DEFAULT_RESULT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase7_public_benchmark_result.json")
DEFAULT_RESULT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase7_public_benchmark_result.zh.md")
DEFAULT_GATE_ZH = Path("docs/paper_agent/decompile_faithfulness_phase7_sota_gate_decision.zh.md")
DEFAULT_OPT_LEVELS = ("O0", "O2")


def main() -> None:
    args = parse_args()
    summary = run_phase7_public_eval(
        repo_root=args.repo_root,
        manifest_json=args.manifest_json,
        preflight_json=args.preflight_json,
        output_dir=args.output_dir,
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
    parser.add_argument("--gate-zh", type=Path, default=DEFAULT_GATE_ZH)
    parser.add_argument("--opt-level", action="append", default=list(DEFAULT_OPT_LEVELS))
    return parser.parse_args()


def run_phase7_public_eval(
    repo_root: Path,
    manifest_json: Path,
    preflight_json: Path,
    output_dir: Path,
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
    candidate_manifest_json = _resolve(repo_root, candidate_manifest_json)
    compile_preflight_json = _resolve(repo_root, compile_preflight_json)
    result_json = _resolve(repo_root, result_json)
    result_zh = _resolve(repo_root, result_zh)
    gate_zh = _resolve(repo_root, gate_zh)

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
    records_path = output_dir / "records.jsonl"
    original_trace_cache: dict[tuple[str, str, str], Any] = {}
    original_static_cache: dict[tuple[str, str], Any] = {}
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
        for opt_level in opt_levels:
            assembly_context = phase6.build_assembly_context(
                case=case,
                opt_level=opt_level,
                assembly_dir=assembly_dir,
            )
            assembly_contexts.append(assembly_context)
            for candidate in build_phase7_candidates(case, entry, opt_level, assembly_context["assembly_path"]):
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
    gate = build_gate_decision(summary)

    _write_json(candidate_manifest_json, candidate_manifest)
    _write_json(compile_preflight_json, compile_preflight)
    _write_json(result_json, summary)
    write_result_markdown(result_zh, summary)
    write_gate_markdown(gate_zh, gate, summary)
    return summary


def build_phase7_candidates(
    case: phase5_gpu.fixtures.FunctionCase,
    entry: dict[str, Any],
    opt_level: str,
    assembly_context_path: str,
) -> list[phase6.Phase6Candidate]:
    candidates = phase6.build_phase6_candidates(
        case=case,
        entry=entry,
        opt_level=opt_level,
        assembly_context_path=assembly_context_path,
    )
    updated: list[phase6.Phase6Candidate] = []
    for candidate in candidates:
        updated.append(
            replace(
                candidate,
                candidate_id=candidate.candidate_id.replace("phase6_", "phase7_", 1),
                mutation_type=candidate.mutation_type.replace("phase6_", "phase7_"),
                source_kind=candidate.source_kind.replace(
                    "assembly_context_decompiler_like",
                    "phase7_public_benchmark_decompiler_like",
                ),
                source_name=candidate.source_name.replace(
                    "deterministic_decompiler_like",
                    "phase7_public_benchmark_deterministic",
                ),
            )
        )
    return updated


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
        "phase": "phase7_public_benchmark_candidate_manifest",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": manifest.get("benchmark", "CodeFuse-DeBench"),
        "source_function_count": source_case_count,
        "candidate_count": len(records),
        "compile_pass_count": compile_pass,
        "paired_function_count": paired,
        "compile_pass_target_min": 100,
        "paired_function_target_min": 30,
        "optimization_levels": opt_levels,
        "records_path": str(records_path),
        "assembly_context_count": len(assembly_contexts),
        "assembly_contexts": assembly_contexts,
        "candidate_sources": sorted({item["source"] for item in manifest_candidates}),
        "candidates": manifest_candidates,
        "verdict": (
            "pass-phase7-public-candidate-scale"
            if source_case_count >= 50 and compile_pass >= 100 and paired >= 30
            else "needs-more-phase7-public-candidates"
        ),
        "gpu_decision": "not-needed-for-cpu-public-benchmark-eval",
    }


def build_compile_preflight(records: list[dict[str, Any]]) -> dict[str, Any]:
    compile_pass = sum(1 for record in records if record["compiled"])
    paired = phase6.paired_case_count(records)
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
    return {
        "phase": "phase7_public_compile_preflight",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(records),
        "compile_pass_count": compile_pass,
        "paired_function_count": paired,
        "failure_counts": failure_counts,
        "verdict": (
            "pass-phase7-public-compile-preflight"
            if compile_pass >= 100 and paired >= 30
            else "needs-more-phase7-public-compile-pass"
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
        "v3_trace_mismatch_rate": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("trace_mismatch_rate", 0.0)),
        ),
        "v3_trace_total": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("trace_total", 0.0)),
        ),
    }
    best_baseline = max(baseline_auc["fixture_only"], baseline_auc["static_structured_proxy"])
    behavior_preserving_rewrites = [
        record for record in eval_records
        if record["metadata"]["expected_role"] == "behavior_preserving_rewrite"
    ]
    v3_fp_count = sum(
        1 for record in behavior_preserving_rewrites
        if float(record["features"].get("trace_total", 0.0)) > 0.0
    )
    static_fp_count = sum(
        1 for record in behavior_preserving_rewrites
        if float(record["features"].get("static_structured_total", 0.0)) > 0.0
    )
    risk_breakdown = {
        risk: phase6.subset_metrics(
            [record for record in eval_records if risk in risk_by_case.get(record["case_id"], [])]
        )
        for risk in sorted({risk for risks in risk_by_case.values() for risk in risks})
    }
    summary: dict[str, Any] = {
        "phase": "phase7_public_benchmark_result_analysis",
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
        "behavior_preserving_rewrite_count": len(behavior_preserving_rewrites),
        "v3_behavior_preserving_false_positive_count": v3_fp_count,
        "v3_behavior_preserving_false_positive_rate": (
            v3_fp_count / len(behavior_preserving_rewrites)
            if behavior_preserving_rewrites else 0.0
        ),
        "static_behavior_preserving_false_positive_count": static_fp_count,
        "static_behavior_preserving_false_positive_rate": (
            static_fp_count / len(behavior_preserving_rewrites)
            if behavior_preserving_rewrites else 0.0
        ),
        "by_optimization_level": {
            opt: phase6.subset_metrics(
                [record for record in eval_records if record["optimization_level"] == opt]
            )
            for opt in sorted({record["optimization_level"] for record in eval_records})
        },
        "by_candidate_source": {
            source: phase6.subset_metrics(
                [record for record in eval_records if record["metadata"]["source_kind"] == source]
            )
            for source in sorted({record["metadata"]["source_kind"] for record in eval_records})
        },
        "by_mutation_type": {
            mutation: phase6.subset_metrics(
                [record for record in eval_records if record["mutation_type"] == mutation]
            )
            for mutation in sorted({record["mutation_type"] for record in eval_records})
        },
        "by_risk_family": risk_breakdown,
        "candidate_manifest_verdict": candidate_manifest["verdict"],
        "compile_preflight_verdict": compile_preflight["verdict"],
        "failure_taxonomy": phase7_failure_taxonomy(records),
        "external_sota_claim_ready": False,
        "external_sota_claim_blocker": (
            "This run is a public benchmark alignment row, not yet a direct reproduction of "
            "LLM4Decompile/DecompileBench generation metrics or a second compile-ready decompiler."
        ),
        "gate": {},
    }
    summary["gate"] = {
        "source_function_scale_gate": summary["source_function_count"] >= 50,
        "compile_pass_scale_gate": summary["compile_pass_count"] >= 100,
        "paired_function_gate": summary["paired_case_count"] >= 30,
        "v3_beats_fixture_gate": baseline_auc["v3_trace_total"] > baseline_auc["fixture_only"],
        "v3_beats_static_gate": baseline_auc["v3_trace_total"] > baseline_auc["static_structured_proxy"],
        "sota_delta_gate": summary["sota_delta_vs_best_baseline"] >= 0.05,
        "behavior_preserving_fp_gate": summary["v3_behavior_preserving_false_positive_rate"] <= 0.10,
        "fixture_collapse_gate": not summary["fixture_collapse"],
        "risk_breakdown_gate": bool(risk_breakdown),
    }
    summary["verdict"] = phase7_verdict(summary)
    return summary


def phase7_failure_taxonomy(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "candidate_compile_failure": sum(1 for record in records if not record["compiled"]),
        "fixture_passing_semantic_drift": phase6.fixture_passing_wrong_count(records),
        "trace_domain_miss": sum(
            1 for record in records
            if record["compiled"]
            and record["label"] == "faithful"
            and record["metadata"]["expected_role"] == "fixture_passing_semantic_drift"
        ),
        "behavior_preserving_rewrite_false_positive": sum(
            1 for record in records
            if record["compiled"]
            and record["metadata"]["expected_role"] == "behavior_preserving_rewrite"
            and float(record["features"].get("trace_total", 0.0)) > 0.0
        ),
    }


def phase7_verdict(summary: dict[str, Any]) -> str:
    if all(summary["gate"].values()):
        return "pass-phase7-public-benchmark-main-evidence"
    if (
        summary["gate"]["source_function_scale_gate"]
        and summary["gate"]["compile_pass_scale_gate"]
        and summary["gate"]["paired_function_gate"]
    ):
        return "method-negative-public-benchmark"
    return "needs-more-phase7-public-benchmark-scale"


def build_gate_decision(summary: dict[str, Any]) -> dict[str, Any]:
    if summary["verdict"] == "pass-phase7-public-benchmark-main-evidence":
        decision = "ready-for-phase7d-second-decompiler-or-llm-baseline"
        claim_boundary = (
            "Positive Phase7C means the method has a public CodeFuse-DeBench source-known row. "
            "It still cannot claim external-paper SOTA until direct related-work baselines and "
            "at least one additional compile-ready decompiler or LLM baseline are added."
        )
        next_step = (
            "继续 Phase 7D/7E：补第二 compile-ready decompiler 或 LLM baseline。"
            "GPU 2/3 只在 LLM candidate generation / LLM judge / repair baseline 时使用。"
        )
    elif summary["verdict"] == "method-negative-public-benchmark":
        decision = "revise-method-before-sota-claim"
        claim_boundary = (
            "Phase7C reaches public benchmark scale and v3 beats fixture/static, but the delta "
            "against the best static baseline is below the CCF-A/SOTA gate. This row is useful "
            "as public alignment evidence, not sufficient as the main SOTA claim."
        )
        next_step = (
            "先补 static-hard 或 LLM-generated public benchmark candidates，检查 v3 是否在更接近真实生成错误的"
            "候选上拉开 delta；同时继续 Phase 7D 的第二 decompiler feasibility。"
        )
    else:
        decision = "needs-more-public-benchmark-scale"
        claim_boundary = (
            "Phase7C has not reached public benchmark scale, so it cannot support a CCF-A main table."
        )
        next_step = "先扩大或修复 public benchmark candidate scale，再重新评估 SOTA gate。"
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "phase7_verdict": summary["verdict"],
        "gate": summary["gate"],
        "claim_boundary": claim_boundary,
        "next_step": next_step,
    }


def write_result_markdown(path: Path, summary: dict[str, Any]) -> None:
    gate_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in summary["gate"].items())
    risk_rows = "\n".join(
        "| `{risk}` | `{candidate_count}` | `{paired_case_count}` | `{fixture_only_auc:.4f}` | "
        "`{static_structured_auc:.4f}` | `{v3_trace_total_auc:.4f}` |".format(
            risk=risk,
            **metrics,
        )
        for risk, metrics in summary["by_risk_family"].items()
    )
    mutation_rows = "\n".join(
        "| `{mutation}` | `{candidate_count}` | `{paired_case_count}` | `{fixture_only_auc:.4f}` | "
        "`{static_structured_auc:.4f}` | `{v3_trace_total_auc:.4f}` |".format(
            mutation=mutation,
            **metrics,
        )
        for mutation, metrics in summary["by_mutation_type"].items()
    )
    failure_rows = "\n".join(
        f"| `{key}` | `{value}` |" for key, value in summary["failure_taxonomy"].items()
    )
    text = f"""# Decompilation Faithfulness Phase 7 Public Benchmark Result

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
- V3 behavior-preserving FP rate: `{summary['v3_behavior_preserving_false_positive_rate']:.4f}`
- External-paper SOTA claim ready: `{summary['external_sota_claim_ready']}`
- External-paper SOTA blocker: {summary['external_sota_claim_blocker']}
- Records: `{summary['records_path']}`

## Gate Check

| Gate | Passed |
|---|---:|
{gate_rows}

## Risk-family Breakdown

| Risk | Candidates | Paired Cases | Fixture AUC | Static AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|
{risk_rows}

## Mutation Breakdown

| Mutation | Candidates | Paired Cases | Fixture AUC | Static AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|
{mutation_rows}

## Failure Taxonomy

| Category | Count |
|---|---:|
{failure_rows}

## Interpretation

这是 Phase 7C 的 full public benchmark row：输入来自 CodeFuse-DeBench 的保守 source-known scalar C 主集，候选为 CPU-only deterministic/decompiler-like controls 和 fixture-overfit semantic drift variants，覆盖 `O0/O2`。这一步回答的是“Dynamic Trace v3 能否在公开 benchmark 对齐行上超过 fixture/static auditor”，不是“生成模型是否超过相关工作”。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_gate_markdown(path: Path, gate: dict[str, Any], summary: dict[str, Any]) -> None:
    gate_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in gate["gate"].items())
    text = f"""# Decompilation Faithfulness Phase 7 SOTA Gate Decision

- Decision: `{gate['decision']}`
- Phase 7 verdict: `{gate['phase7_verdict']}`
- Dynamic Trace v3 AUC: `{summary['baseline_auc']['v3_trace_total']:.4f}`
- Best non-oracle baseline AUC: `{summary['best_non_oracle_baseline_auc']:.4f}`
- Delta: `{summary['sota_delta_vs_best_baseline']:.4f}`
- External-paper SOTA ready: `{summary['external_sota_claim_ready']}`

## Gate

| Gate | Passed |
|---|---:|
{gate_rows}

## Claim Boundary

{gate['claim_boundary']}

## Next Step

{gate['next_step']}
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
