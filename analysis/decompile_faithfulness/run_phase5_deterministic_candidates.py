from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import run_phase2_cpu_smoke as cpu_smoke
from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu


DEFAULT_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json")
DEFAULT_PREFLIGHT = Path("docs/paper_agent/decompile_faithfulness_phase5_preflight.json")
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase5_deterministic_candidates")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase5_deterministic_candidates.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase5_deterministic_candidates.zh.md")
DEFAULT_CANDIDATE_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase5_candidate_manifest_deterministic.json")


@dataclass(frozen=True)
class DeterministicCandidate:
    case_id: str
    candidate_id: str
    mutation_type: str
    function_source: str
    expected_layer: str


def main() -> None:
    args = parse_args()
    summary = run_deterministic_candidates(
        repo_root=args.repo_root,
        manifest_json=args.manifest_json,
        preflight_json=args.preflight_json,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
        candidate_manifest_json=args.candidate_manifest_json,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "candidate_count": summary["candidate_count"],
                "compile_pass_count": summary["compile_pass_count"],
                "paired_case_count": summary["paired_case_count"],
                "trace_pairwise_auc": summary["trace_pairwise_auc"],
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
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--candidate-manifest-json", type=Path, default=DEFAULT_CANDIDATE_MANIFEST)
    return parser.parse_args()


def run_deterministic_candidates(
    repo_root: Path,
    manifest_json: Path,
    preflight_json: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    candidate_manifest_json: Path,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    manifest_json = _resolve(repo_root, manifest_json)
    preflight_json = _resolve(repo_root, preflight_json)
    output_dir = _resolve(repo_root, output_dir)
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    candidate_manifest_json = _resolve(repo_root, candidate_manifest_json)

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    preflight = json.loads(preflight_json.read_text(encoding="utf-8"))
    if preflight.get("verdict") != "pass-phase5-preflight":
        raise RuntimeError(f"Phase5 preflight must pass first: {preflight.get('verdict')}")

    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "records.jsonl"
    trace_dir = output_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    candidates_by_case: dict[str, list[dict[str, Any]]] = {}
    for entry in manifest.get("functions", []):
        if not entry.get("counts_for_phase5_real_project_gate"):
            continue
        case = phase5_gpu._case_from_manifest_entry(repo_root, entry)
        candidates = build_candidates_for_entry(case, entry)
        candidates_by_case[entry["case_id"]] = []
        for candidate in candidates:
            features = phase5_gpu.phase5_trace_features(
                entry=entry,
                case=case,
                candidate_id=candidate.candidate_id,
                candidate_source=candidate.function_source,
                trace_dir=trace_dir,
            )
            record = record_from_features(candidate, features)
            records.append(record)
            if record["compiled"]:
                candidates_by_case[entry["case_id"]].append(
                    {
                        "case_id": entry["case_id"],
                        "candidate_id": candidate.candidate_id,
                        "label": record["label"],
                        "mutation_type": candidate.mutation_type,
                        "function_source": candidate.function_source,
                        "source_kind": "deterministic_phase5",
                        "source_name": "phase5_deterministic_candidate_layer",
                        "prompt_id": candidate.expected_layer,
                        "raw_output_path": "",
                        "cleaning_status": "parsed_function",
                        "generation_index": 0,
                        "sampling": {},
                    }
                )

    _write_jsonl(records_path, records)
    candidate_manifest = build_candidate_manifest(
        manifest=manifest,
        records=records,
        records_path=records_path,
        candidates_by_case=candidates_by_case,
    )
    _write_json(candidate_manifest_json, candidate_manifest)

    eval_records = [
        record for record in records
        if record["label"] in {"faithful", "plausible_wrong"}
    ]
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "records_path": str(records_path),
        "source_function_count": manifest.get("function_count", 0),
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record["compiled"]),
        "behavior_label_counts": _count_by(records, "label"),
        "paired_case_count": _paired_case_count(records),
        "fixture_passing_wrong_count": _fixture_passing_wrong_count(records),
        "trace_pairwise_auc": phase3_cpu._pairwise_auc(eval_records, phase3_cpu._trace_score),
        "fixture_collapse": phase3_cpu.v1._fixture_collapse(eval_records),
        "candidate_manifest_verdict": candidate_manifest["verdict"],
    }
    summary["verdict"] = (
        "pass-phase5-deterministic-candidate-layer"
        if candidate_manifest["verdict"] == "pass-phase5-full-candidate-generation"
        else "needs-more-phase5-deterministic-candidates"
    )
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def build_candidates_for_entry(
    case: phase5_gpu.fixtures.FunctionCase,
    entry: dict[str, Any],
) -> list[DeterministicCandidate]:
    signature = entry["signature"]
    param_names = cpu_smoke._parameter_names(signature)
    zero_guard = zero_use_expression(param_names)
    fixtures = entry.get("fixtures", [])
    first_expected = int(fixtures[0]["expected"]) if fixtures else 0
    plus_one = first_expected + 1
    minus_one = first_expected - 1
    return [
        DeterministicCandidate(
            case_id=case.case_id,
            candidate_id=f"phase5_det_{case.case_id}_original",
            mutation_type="deterministic_behavior_preserving_original",
            function_source=case.function_source,
            expected_layer="behavior_preserving",
        ),
        DeterministicCandidate(
            case_id=case.case_id,
            candidate_id=f"phase5_det_{case.case_id}_return_zero",
            mutation_type="deterministic_manual_stress_return_zero",
            function_source=constant_return_source(signature, 0, zero_guard),
            expected_layer="manual_stress_bug",
        ),
        DeterministicCandidate(
            case_id=case.case_id,
            candidate_id=f"phase5_det_{case.case_id}_return_fixture0",
            mutation_type="deterministic_manual_stress_fixture_constant",
            function_source=constant_return_source(signature, first_expected, zero_guard),
            expected_layer="manual_stress_bug",
        ),
        DeterministicCandidate(
            case_id=case.case_id,
            candidate_id=f"phase5_det_{case.case_id}_return_fixture0_plus1",
            mutation_type="deterministic_manual_stress_constant_plus_one",
            function_source=constant_return_source(signature, plus_one, zero_guard),
            expected_layer="manual_stress_bug",
        ),
        DeterministicCandidate(
            case_id=case.case_id,
            candidate_id=f"phase5_det_{case.case_id}_return_fixture0_minus1",
            mutation_type="deterministic_manual_stress_constant_minus_one",
            function_source=constant_return_source(signature, minus_one, zero_guard),
            expected_layer="manual_stress_bug",
        ),
    ]


def zero_use_expression(param_names: list[str]) -> str:
    if not param_names:
        return ""
    joined = " + ".join(f"({name})" for name in param_names)
    return f" + 0 * ({joined})"


def constant_return_source(signature: str, value: int, zero_guard: str) -> str:
    return f"{signature} {{\n    return {value}{zero_guard};\n}}\n"


def record_from_features(
    candidate: DeterministicCandidate,
    features: dict[str, float],
) -> dict[str, Any]:
    if features["compiled"] != 1.0:
        label = "compile_fail"
    elif features["trace_mismatch_rate"] == 0.0:
        label = "faithful"
    else:
        label = "plausible_wrong"
    return {
        "case_id": candidate.case_id,
        "candidate_id": candidate.candidate_id,
        "label": label,
        "mutation_type": candidate.mutation_type,
        "compiled": features["compiled"] == 1.0,
        "behavior_passed": features["fixture_mismatch_rate"] == 0.0,
        "bounded_trace_passed": features["trace_mismatch_rate"] == 0.0,
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
            "function_source": candidate.function_source,
            "source_kind": "deterministic_phase5",
            "source_name": "phase5_deterministic_candidate_layer",
            "prompt_id": candidate.expected_layer,
        },
    }


def build_candidate_manifest(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    records_path: Path,
    candidates_by_case: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    compile_pass_count = sum(1 for record in records if record["compiled"])
    paired_case_count = _paired_case_count(records)
    return {
        "phase": "phase5_candidate_generation_or_import",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest_function_count": manifest.get("function_count", 0),
        "candidate_layers": ["behavior_preserving_original", "deterministic_manual_stress"],
        "candidate_count": len(records),
        "compile_pass_count": compile_pass_count,
        "compile_pass_target_min": 100,
        "compile_pass_target_range": [100, 200],
        "paired_function_count": paired_case_count,
        "paired_function_target_min": 20,
        "records_path": str(records_path),
        "candidates": [
            {"case_id": case_id, "candidates": candidates}
            for case_id, candidates in sorted(candidates_by_case.items())
            if candidates
        ],
        "verdict": _candidate_manifest_verdict(compile_pass_count, paired_case_count),
        "gpu_decision": "not-needed-for-deterministic-layer",
    }


def _candidate_manifest_verdict(compile_pass_count: int, paired_case_count: int) -> str:
    if compile_pass_count >= 100 and paired_case_count >= 20:
        return "pass-phase5-full-candidate-generation"
    return "needs-full-candidate-generation"


def _paired_case_count(records: list[dict[str, Any]]) -> int:
    total = 0
    for case_id in sorted({record["case_id"] for record in records}):
        labels = {record["label"] for record in records if record["case_id"] == case_id}
        if "faithful" in labels and "plausible_wrong" in labels:
            total += 1
    return total


def _fixture_passing_wrong_count(records: list[dict[str, Any]]) -> int:
    return sum(
        1 for record in records
        if record["label"] == "plausible_wrong"
        and record["features"].get("fixture_mismatch_rate") == 0.0
    )


def _count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key, ""))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


def _write_markdown_zh(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Decompilation Faithfulness Phase 5 Deterministic Candidates

- Verdict: `{summary['verdict']}`
- Source functions: `{summary['source_function_count']}`
- Candidates: `{summary['candidate_count']}`
- Compile pass count: `{summary['compile_pass_count']}`
- Behavior labels: `{summary['behavior_label_counts']}`
- Paired case count: `{summary['paired_case_count']}`
- Fixture-passing wrong count: `{summary['fixture_passing_wrong_count']}`
- Trace pairwise AUC: `{summary['trace_pairwise_auc']:.4f}`
- Fixture collapse: `{summary['fixture_collapse']}`
- Candidate manifest verdict: `{summary['candidate_manifest_verdict']}`

## 解释

这是 Phase 5 的 deterministic candidate layer：每个真实项目函数包含一个 behavior-preserving original 和多个 manual stress constants。它用于保证 source-known auditing 方法有 full-scale compile-pass paired data，不替代 LLM/decompiler candidate layer，也不能单独作为 SOTA 生成质量证据。
"""
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
