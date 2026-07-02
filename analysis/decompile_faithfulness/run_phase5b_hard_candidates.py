from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from analysis.decompile_faithfulness import dynamic_trace
from analysis.decompile_faithfulness import run_phase2_cpu_smoke as cpu_smoke
from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu


DEFAULT_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json")
DEFAULT_PREFLIGHT = Path("docs/paper_agent/decompile_faithfulness_phase5_preflight.json")
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase5b_hard_candidates")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase5b_hard_candidates.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase5b_hard_candidates.zh.md")
DEFAULT_CANDIDATE_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase5b_candidate_manifest.json")


@dataclass(frozen=True)
class HardCandidate:
    case_id: str
    candidate_id: str
    mutation_type: str
    function_source: str
    source_kind: str


def main() -> None:
    args = parse_args()
    summary = run_hard_candidates(
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
                "fixture_passing_wrong_count": summary["fixture_passing_wrong_count"],
                "fixture_only_auc": summary["baseline_auc"]["fixture_only"],
                "v3_trace_total_auc": summary["baseline_auc"]["v3_trace_total"],
                "sota_delta": summary["sota_delta_vs_fixture_only"],
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


def run_hard_candidates(
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
    trace_dir = output_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "records.jsonl"

    records: list[dict[str, Any]] = []
    candidates_by_case: dict[str, list[dict[str, Any]]] = {}
    for entry in manifest.get("functions", []):
        if not entry.get("counts_for_phase5_real_project_gate"):
            continue
        case = phase5_gpu._case_from_manifest_entry(repo_root, entry)
        hard_inputs = phase5b_hard_trace_inputs(entry, max_inputs=128)
        candidates = build_hard_candidates(case, entry)
        candidates_by_case[case.case_id] = []
        for candidate in candidates:
            features = phase5b_features(
                entry=entry,
                case=case,
                candidate_id=candidate.candidate_id,
                candidate_source=candidate.function_source,
                hard_inputs=hard_inputs,
                trace_dir=trace_dir,
            )
            record = record_from_features(candidate, features)
            records.append(record)
            if record["compiled"]:
                candidates_by_case[case.case_id].append(
                    {
                        "case_id": case.case_id,
                        "candidate_id": candidate.candidate_id,
                        "label": record["label"],
                        "mutation_type": candidate.mutation_type,
                        "function_source": candidate.function_source,
                        "source_kind": candidate.source_kind,
                        "source_name": "phase5b_fixture_overfit_hard_candidates",
                        "prompt_id": candidate.mutation_type,
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
        and record["compiled"]
    ]
    baseline_auc = {
        "fixture_only": pairwise_auc(eval_records, lambda r: float(r["features"]["fixture_mismatch_rate"])),
        "v3_hard_trace_mismatch_rate": pairwise_auc(eval_records, lambda r: float(r["features"]["trace_mismatch_rate"])),
        "v3_trace_total": pairwise_auc(eval_records, lambda r: float(r["features"]["trace_total"])),
    }
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "records_path": str(records_path),
        "source_function_count": manifest.get("function_count", 0),
        "source_projects": manifest.get("source_projects", []),
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record["compiled"]),
        "behavior_label_counts": count_by(records, "label"),
        "paired_case_count": paired_case_count(records),
        "fixture_passing_wrong_count": fixture_passing_wrong_count(records),
        "fixture_collapse": phase3_cpu.v1._fixture_collapse(eval_records),
        "baseline_auc": baseline_auc,
        "sota_delta_vs_fixture_only": baseline_auc["v3_trace_total"] - baseline_auc["fixture_only"],
        "candidate_manifest_verdict": candidate_manifest["verdict"],
        "gate": {},
    }
    summary["gate"] = {
        "scale_gate": summary["compile_pass_count"] >= 100 and summary["paired_case_count"] >= 20,
        "fixture_passing_wrong_gate": summary["fixture_passing_wrong_count"] >= 5,
        "v3_auc_gate": baseline_auc["v3_trace_total"] >= 0.85,
        "sota_delta_gate": summary["sota_delta_vs_fixture_only"] >= 0.05,
        "fixture_collapse_gate": not summary["fixture_collapse"],
    }
    summary["verdict"] = phase5b_verdict(summary)
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def build_hard_candidates(
    case: phase5_gpu.fixtures.FunctionCase,
    entry: dict[str, Any],
) -> list[HardCandidate]:
    signature = entry["signature"]
    param_names = cpu_smoke._parameter_names(signature)
    zero_guard = zero_use_expression(param_names)
    fixtures = entry.get("fixtures", [])
    candidates = [
        HardCandidate(
            case_id=case.case_id,
            candidate_id=f"phase5b_{case.case_id}_original",
            mutation_type="hard_behavior_preserving_original",
            function_source=case.function_source,
            source_kind="phase5b_hard_control",
        )
    ]
    fallbacks = fallback_values(fixtures)
    for index, fallback in enumerate(fallbacks):
        candidates.append(
            HardCandidate(
                case_id=case.case_id,
                candidate_id=f"phase5b_{case.case_id}_fixture_overfit_{index:02d}",
                mutation_type="hard_fixture_overfit_wrong",
                function_source=fixture_overfit_source(signature, fixtures, fallback, zero_guard),
                source_kind="phase5b_fixture_overfit",
            )
        )
    return candidates


def fallback_values(fixtures: list[dict[str, Any]]) -> list[int]:
    expected = [int(item["expected"]) for item in fixtures]
    base = expected[0] if expected else 0
    values = [0, base + 1, base - 1]
    if expected:
        values.append(expected[-1] + 1)
    deduped: list[int] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped[:4]


def fixture_overfit_source(
    signature: str,
    fixtures: list[dict[str, Any]],
    fallback: int,
    zero_guard: str,
) -> str:
    param_names = cpu_smoke._parameter_names(signature)
    lines = [f"{signature} {{"]
    for fixture in fixtures:
        args = [int(value) for value in fixture["args"]]
        conditions = [
            f"{name} == {value}"
            for name, value in zip(param_names, args)
        ]
        condition = " && ".join(conditions) if conditions else "1"
        lines.append(f"    if ({condition}) {{")
        lines.append(f"        return {int(fixture['expected'])}{zero_guard};")
        lines.append("    }")
    lines.append(f"    return {fallback}{zero_guard};")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def zero_use_expression(param_names: list[str]) -> str:
    if not param_names:
        return ""
    return " + 0 * (" + " + ".join(f"({name})" for name in param_names) + ")"


def phase5b_hard_trace_inputs(
    entry: dict[str, Any],
    max_inputs: int = 128,
) -> list[dynamic_trace.TraceInput]:
    fixtures = [tuple(int(value) for value in item["args"]) for item in entry.get("fixtures", [])]
    if not fixtures:
        return []
    arity = len(fixtures[0])
    fixture_set = set(fixtures)
    positive_only = all(value > 0 for args in fixtures for value in args)
    nonnegative_only = all(value >= 0 for args in fixtures for value in args)
    char_like = "char" in entry.get("signature", "")
    values_by_position: list[list[int]] = []
    for index in range(arity):
        values = {args[index] for args in fixtures}
        for value in list(values):
            values.add(value - 1)
            values.add(value + 1)
        if positive_only:
            values = {value for value in values if value > 0}
            values.update({1, 2})
        elif nonnegative_only:
            values = {value for value in values if value >= 0}
            values.update({0, 1, 2})
        else:
            values.update({-1, 0, 1})
        if char_like:
            values = {value for value in values if 0 <= value <= 127}
            values.update({43, 45, 65, 90, 97, 122})
        values_by_position.append(sorted(values)[:10])

    generated: list[tuple[int, ...]] = []
    for args in itertools.product(*values_by_position):
        if args in fixture_set:
            continue
        generated.append(tuple(args))
        if len(generated) >= max_inputs:
            break
    return [
        dynamic_trace.TraceInput(args=args, bucket="phase5b_hard_probe")
        for args in generated
    ]


def phase5b_features(
    entry: dict[str, Any],
    case: phase5_gpu.fixtures.FunctionCase,
    candidate_id: str,
    candidate_source: str,
    hard_inputs: list[dynamic_trace.TraceInput],
    trace_dir: Path,
) -> dict[str, float]:
    fixture_inputs = [
        dynamic_trace.TraceInput(args=test.args, bucket="fixture")
        for test in case.tests
    ]
    original_hard = dynamic_trace.run_trace(
        case,
        "original_hard",
        case.function_source,
        hard_inputs,
        trace_dir,
        opt_level="O0",
    )
    candidate_hard = phase5_gpu.safe_run_trace(
        case,
        f"{candidate_id}_hard",
        candidate_source,
        hard_inputs,
        trace_dir,
        opt_level="O0",
    )
    if not original_hard.compiled or original_hard.exit_code != 0:
        raise RuntimeError(f"original hard trace failed for {case.case_id}: {original_hard.stderr}")
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

    original_fixture = dynamic_trace.run_trace(
        case,
        "original_fixture",
        case.function_source,
        fixture_inputs,
        trace_dir,
        opt_level="O0",
    )
    candidate_fixture = phase5_gpu.safe_run_trace(
        case,
        f"{candidate_id}_fixture",
        candidate_source,
        fixture_inputs,
        trace_dir,
        opt_level="O0",
    )
    if (
        original_fixture.compiled
        and original_fixture.exit_code == 0
        and candidate_fixture.compiled
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
    return {
        **components,
        "fixture_mismatch_rate": fixture_mismatch_rate,
        "fixture_behavior_passed": 1.0 if fixture_mismatch_rate == 0.0 else 0.0,
        "compiled": 1.0 if candidate_hard.compiled else 0.0,
        "primary_exit_code": float(candidate_hard.exit_code),
        "fixture_exit_code": float(candidate_fixture.exit_code),
        "hard_probe_count": float(len(hard_inputs)),
    }


def record_from_features(
    candidate: HardCandidate,
    features: dict[str, float],
) -> dict[str, Any]:
    if features["compiled"] != 1.0:
        label = "compile_fail"
    elif features["fixture_mismatch_rate"] == 0.0 and features["trace_mismatch_rate"] > 0.0:
        label = "plausible_wrong"
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
            "source_kind": candidate.source_kind,
            "source_name": "phase5b_fixture_overfit_hard_candidates",
            "prompt_id": candidate.mutation_type,
        },
    }


def build_candidate_manifest(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    records_path: Path,
    candidates_by_case: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    compile_pass = sum(1 for record in records if record["compiled"])
    paired = paired_case_count(records)
    return {
        "phase": "phase5b_fixture_passing_hard_candidate_generation",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest_function_count": manifest.get("function_count", 0),
        "candidate_layers": ["behavior_preserving_original", "fixture_overfit_wrong"],
        "candidate_count": len(records),
        "compile_pass_count": compile_pass,
        "compile_pass_target_min": 100,
        "compile_pass_target_range": [100, 200],
        "paired_function_count": paired,
        "paired_function_target_min": 20,
        "records_path": str(records_path),
        "candidates": [
            {"case_id": case_id, "candidates": candidates}
            for case_id, candidates in sorted(candidates_by_case.items())
            if candidates
        ],
        "verdict": "pass-phase5b-full-hard-candidate-generation"
        if compile_pass >= 100 and paired >= 20
        else "needs-more-phase5b-hard-candidates",
    }


def paired_case_count(records: list[dict[str, Any]]) -> int:
    total = 0
    for case_id in sorted({record["case_id"] for record in records}):
        labels = {record["label"] for record in records if record["case_id"] == case_id and record["compiled"]}
        if "faithful" in labels and "plausible_wrong" in labels:
            total += 1
    return total


def fixture_passing_wrong_count(records: list[dict[str, Any]]) -> int:
    return sum(
        1 for record in records
        if record["label"] == "plausible_wrong"
        and record["compiled"]
        and record["features"].get("fixture_mismatch_rate") == 0.0
        and record["features"].get("trace_mismatch_rate", 0.0) > 0.0
    )


def pairwise_auc(
    records: list[dict[str, Any]],
    score: Callable[[dict[str, Any]], float],
) -> float:
    return phase3_cpu._pairwise_auc(records, score)


def count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key, ""))
        counts[value] = counts.get(value, 0) + 1
    return counts


def phase5b_verdict(summary: dict[str, Any]) -> str:
    if all(summary["gate"].values()):
        return "pass-phase5b-hard-candidate-sota-delta"
    if summary["gate"]["scale_gate"] and summary["gate"]["fixture_passing_wrong_gate"]:
        return "phase5b-hard-candidates-positive-needs-analysis"
    return "needs-more-phase5b-hard-candidates"


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
    gate_rows = "\n".join(
        f"| `{key}` | `{value}` |"
        for key, value in summary["gate"].items()
    )
    text = f"""# Decompilation Faithfulness Phase 5B Hard Candidates

- Verdict: `{summary['verdict']}`
- Source functions: `{summary['source_function_count']}`
- Source projects: `{summary['source_projects']}`
- Candidates: `{summary['candidate_count']}`
- Compile pass count: `{summary['compile_pass_count']}`
- Behavior labels: `{summary['behavior_label_counts']}`
- Paired case count: `{summary['paired_case_count']}`
- Fixture-passing wrong count: `{summary['fixture_passing_wrong_count']}`
- Fixture-only AUC: `{summary['baseline_auc']['fixture_only']:.4f}`
- V3 hard trace AUC: `{summary['baseline_auc']['v3_trace_total']:.4f}`
- SOTA delta vs fixture-only: `{summary['sota_delta_vs_fixture_only']:.4f}`
- Fixture collapse: `{summary['fixture_collapse']}`
- Candidate manifest verdict: `{summary['candidate_manifest_verdict']}`

## Gate Check

| Gate | Passed |
|---|---:|
{gate_rows}

## Interpretation

Phase 5B 专门测试 fixture-only 的盲区：candidate 先被构造成通过原始 fixtures，再用独立 hard probes 由 source-known oracle 判定是否存在语义漂移。

如果本结果通过，它说明 Dynamic Trace v3 在 fixture-passing wrong candidates 上确实提供了超出 fixture-only 的审计信号。它仍不是 decompiler-output transfer；Phase 6 还需要真实 decompiler/LLM-decompiler 输出。
"""
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
