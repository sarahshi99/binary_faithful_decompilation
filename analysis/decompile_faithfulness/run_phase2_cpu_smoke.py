from __future__ import annotations

import argparse
import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import dynamic_trace, fixtures, ranking
from analysis.decompile_faithfulness import run_dynamic_trace_audit as v1
from analysis.decompile_faithfulness import run_dynamic_trace_v2_audit as v2


@dataclass(frozen=True)
class SmokeCandidate:
    case_id: str
    candidate_id: str
    label: str
    mutation_type: str
    function_source: str
    metadata: dict[str, Any]


def main() -> None:
    args = parse_args()
    summary = run_smoke(
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_md=args.output_md,
        output_zh=args.output_zh,
        manifest_json=args.manifest_json,
    )
    print(
        json.dumps(
            {
                "candidate_count": summary["candidate_count"],
                "compile_pass_count": summary["compile_pass_count"],
                "behavior_label_counts": summary["behavior_label_counts"],
                "fixture_collapse": summary["fixture_collapse"],
                "non_oracle_probe_count": summary["non_oracle_probe_count"],
                "smoke_gate_passed": summary["smoke_gate_passed"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase2_cpu_smoke"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase2_cpu_smoke.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase2_cpu_smoke.md"),
    )
    parser.add_argument(
        "--output-zh",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase2_cpu_smoke.zh.md"),
    )
    parser.add_argument("--manifest-json", type=Path)
    return parser.parse_args()


def build_smoke_manifest(case_ids: list[str] | None = None) -> list[dict[str, Any]]:
    selected = set(case_ids) if case_ids is not None else None
    manifests: list[dict[str, Any]] = []
    for case in fixtures.builtin_cases():
        if selected is not None and case.case_id not in selected:
            continue
        candidates = [
            _candidate_dict(
                case,
                candidate_id=f"phase2_smoke_{case.case_id}_identity",
                mutation_type="phase2_cpu_smoke_identity",
                function_source=case.function_source,
                prompt_id="phase2_cpu_smoke_identity",
                generation_index=0,
            ),
            _candidate_dict(
                case,
                candidate_id=f"phase2_smoke_{case.case_id}_return_zero",
                mutation_type="phase2_cpu_smoke_return_zero",
                function_source=_constant_return_source(case),
                prompt_id="phase2_cpu_smoke_return_zero",
                generation_index=1,
            ),
        ]
        if case.case_id == "absdiff":
            candidates.append(
                _candidate_dict(
                    case,
                    candidate_id="phase2_smoke_absdiff_fixture_overfit",
                    mutation_type="phase2_cpu_smoke_fixture_overfit",
                    function_source=_absdiff_fixture_overfit_source(),
                    prompt_id="phase2_cpu_smoke_fixture_overfit",
                    generation_index=2,
                )
            )
        manifests.append({"case_id": case.case_id, "candidates": candidates})
    return manifests


def run_smoke(
    output_dir: Path,
    output_json: Path,
    output_md: Path,
    output_zh: Path,
    manifest_json: Path | None = None,
    case_ids: list[str] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir = output_dir / "candidates"
    trace_dir = output_dir / "traces"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    trace_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    metadata_path = output_dir / "metadata.jsonl"
    records_path = output_dir / "records.jsonl"

    if manifest_json is None:
        manifest = build_smoke_manifest(case_ids)
        _write_json(manifest_path, manifest)
    else:
        manifest_path = manifest_json
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    candidates = _load_candidates(manifest)
    _write_metadata(metadata_path, candidates)

    records = [
        _evaluate_candidate(candidate, candidate_dir, trace_dir)
        for candidate in candidates
    ]
    _write_jsonl(records_path, records)
    eval_records = [
        record for record in records
        if record["label"] in {"faithful", "plausible_wrong"} and "features" in record
    ]
    behavior_label_counts = {
        "faithful": sum(1 for record in records if record["label"] == "faithful"),
        "plausible_wrong": sum(1 for record in records if record["label"] == "plausible_wrong"),
        "compile_fail": sum(1 for record in records if record["label"] == "compile_fail"),
    }
    by_case_compile = {
        case_id: sum(1 for record in records if record["case_id"] == case_id and record["compiled"])
        for case_id in sorted({record["case_id"] for record in records})
    }
    fixture_collapse = v1._fixture_collapse(eval_records)
    non_oracle_probe_count = sum(
        1
        for record in eval_records
        if record["behavior_passed"]
        and float(record["features"].get("trace_mismatch_rate", 0.0)) > 0.0
    )
    smoke_gate_passed = (
        bool(records)
        and all(count >= 2 for count in by_case_compile.values())
        and behavior_label_counts["faithful"] >= 1
        and behavior_label_counts["plausible_wrong"] >= 1
        and bool(eval_records)
        and not fixture_collapse
        and non_oracle_probe_count >= 1
    )
    summary = {
        "output_dir": str(output_dir),
        "manifest_path": str(manifest_path),
        "metadata_path": str(metadata_path),
        "records_path": str(records_path),
        "case_count": len(by_case_compile),
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record["compiled"]),
        "behavior_label_counts": behavior_label_counts,
        "by_case_compile_count": by_case_compile,
        "fixture_collapse": fixture_collapse,
        "non_oracle_probe_count": non_oracle_probe_count,
        "trace_pairwise_auc": v1._pairwise_auc(
            eval_records,
            lambda record: float(record["features"]["trace_mismatch_rate"]),
        ),
        "smoke_gate_passed": smoke_gate_passed,
        "gpu_started": False,
    }
    _write_json(output_json, summary)
    _write_markdown(output_md, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def _candidate_dict(
    case: fixtures.FunctionCase,
    candidate_id: str,
    mutation_type: str,
    function_source: str,
    prompt_id: str,
    generation_index: int,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "label": "unknown",
        "mutation_type": mutation_type,
        "function_source": function_source,
        "source_kind": "phase2_cpu_smoke",
        "source_name": "deterministic_smoke_manifest",
        "prompt_id": prompt_id,
        "raw_output_path": "",
        "cleaning_status": "parsed_function",
        "generation_index": generation_index,
        "sampling": {
            "temperature": 0.0,
            "top_p": 1.0,
            "max_new_tokens": 0,
        },
        "case_id": case.case_id,
    }


def _constant_return_source(case: fixtures.FunctionCase) -> str:
    signature = _function_signature(case.function_source)
    params = _parameter_names(signature)
    guard = " + ".join(params)
    if guard:
        return f"{signature} {{\n    return 0 + 0 * ({guard});\n}}\n"
    return f"{signature} {{\n    return 0;\n}}\n"


def _absdiff_fixture_overfit_source() -> str:
    return """int absdiff(int a, int b) {
    if (a == 7 && b == 3) {
        return 4;
    }
    if (a == 3 && b == 7) {
        return 4;
    }
    if (a == 5 && b == 5) {
        return 0;
    }
    if (a == -2 && b == 4) {
        return 6;
    }
    return 0 + 0 * (a + b);
}
"""


def _function_signature(function_source: str) -> str:
    return function_source.split("{", 1)[0].strip()


def _parameter_names(signature: str) -> list[str]:
    match = re.search(r"\((.*)\)", signature)
    if not match:
        return []
    params = match.group(1).strip()
    if not params or params == "void":
        return []
    names = []
    for param in params.split(","):
        tokens = param.strip().replace("*", " * ").split()
        if tokens:
            names.append(tokens[-1])
    return names


def _load_candidates(manifest: Any) -> list[SmokeCandidate]:
    manifests = manifest if isinstance(manifest, list) else [manifest]
    candidates: list[SmokeCandidate] = []
    seen: set[tuple[str, str]] = set()
    for item in manifests:
        if not isinstance(item, dict):
            raise ValueError("manifest entries must be objects")
        case_id = _required_string(item, "case_id")
        fixtures.case_by_id(case_id)
        raw_candidates = item.get("candidates")
        if not isinstance(raw_candidates, list):
            raise ValueError("manifest entry must include a candidates list")
        for raw in raw_candidates:
            if not isinstance(raw, dict):
                raise ValueError("candidate entries must be objects")
            candidate_id = _required_string(raw, "candidate_id")
            key = (case_id, candidate_id)
            if key in seen:
                raise ValueError(f"duplicate candidate id for case: {key}")
            seen.add(key)
            label = _required_string(raw, "label")
            if label not in {"unknown", "faithful", "plausible_wrong"}:
                raise ValueError(f"unsupported candidate label: {label}")
            candidates.append(
                SmokeCandidate(
                    case_id=case_id,
                    candidate_id=candidate_id,
                    label=label,
                    mutation_type=_required_string(raw, "mutation_type"),
                    function_source=_required_string(raw, "function_source"),
                    metadata={k: v for k, v in raw.items() if k not in {
                        "candidate_id",
                        "label",
                        "mutation_type",
                        "function_source",
                    }},
                )
            )
    return candidates


def _evaluate_candidate(
    candidate: SmokeCandidate,
    candidate_dir: Path,
    trace_dir: Path,
) -> dict[str, Any]:
    case = fixtures.case_by_id(candidate.case_id)
    compile_result = ccompile.compile_candidate(
        case=case,
        candidate_id=candidate.candidate_id,
        function_source=candidate.function_source,
        output_dir=candidate_dir,
        opt_level="O0",
    )
    if not compile_result.compiled:
        return {
            "case_id": candidate.case_id,
            "candidate_id": candidate.candidate_id,
            "label": "compile_fail",
            "mutation_type": candidate.mutation_type,
            "compiled": False,
            "behavior_passed": False,
            "exit_code": compile_result.exit_code,
            "compile_stdout": compile_result.stdout,
            "compile_stderr": compile_result.stderr,
            "metadata": candidate.metadata,
        }

    label = _resolve_label(candidate.label, compile_result.behavior_passed)
    features = _dynamic_trace_v2_features(case, candidate, trace_dir)
    return {
        "case_id": candidate.case_id,
        "candidate_id": candidate.candidate_id,
        "label": label,
        "original_label": candidate.label,
        "mutation_type": candidate.mutation_type,
        "compiled": True,
        "behavior_passed": compile_result.behavior_passed,
        "exit_code": compile_result.exit_code,
        "features": features,
        "metadata": candidate.metadata,
    }


def _dynamic_trace_v2_features(
    case: fixtures.FunctionCase,
    candidate: SmokeCandidate,
    trace_dir: Path,
) -> dict[str, float]:
    primary_inputs = dynamic_trace.generate_domain_trace_inputs(
        case,
        max_inputs=256,
        include_fixture_tests=False,
    )
    fixture_inputs = [
        dynamic_trace.TraceInput(args=test.args, bucket="fixture")
        for test in case.tests
    ]
    with tempfile.TemporaryDirectory(dir=trace_dir) as td:
        output_dir = Path(td)
        original_run = dynamic_trace.run_trace(
            case,
            "original",
            case.function_source,
            primary_inputs,
            output_dir,
            opt_level="O0",
        )
        candidate_run = dynamic_trace.run_trace(
            case,
            candidate.candidate_id,
            candidate.function_source,
            primary_inputs,
            output_dir,
            opt_level="O0",
        )
        if not original_run.compiled or original_run.exit_code != 0:
            raise RuntimeError(f"original trace failed for {case.case_id}: {original_run.stderr}")
        if not candidate_run.compiled or candidate_run.exit_code != 0:
            components = v1._compile_fail_components(len(primary_inputs))
        else:
            components = dynamic_trace.trace_distance(
                primary_inputs,
                original_run.outputs,
                candidate_run.outputs,
            ).components

        original_fixture = dynamic_trace.run_trace(
            case,
            "original_fixture",
            case.function_source,
            fixture_inputs,
            output_dir,
            opt_level="O0",
        )
        candidate_fixture = dynamic_trace.run_trace(
            case,
            f"{candidate.candidate_id}_fixture",
            candidate.function_source,
            fixture_inputs,
            output_dir,
            opt_level="O0",
        )
        if (
            original_fixture.compiled
            and original_fixture.exit_code == 0
            and candidate_fixture.compiled
            and candidate_fixture.exit_code == 0
            and len(original_fixture.outputs) == len(fixture_inputs)
            and len(candidate_fixture.outputs) == len(fixture_inputs)
        ):
            fixture_components = dynamic_trace.trace_distance(
                fixture_inputs,
                original_fixture.outputs,
                candidate_fixture.outputs,
            ).components
            fixture_mismatch_rate = fixture_components["trace_mismatch_rate"]
        else:
            fixture_mismatch_rate = 1.0
    return {
        **components,
        **v2._domain_components(case, primary_inputs),
        "fixture_mismatch_rate": fixture_mismatch_rate,
        "fixture_behavior_passed": 1.0 if fixture_mismatch_rate == 0.0 else 0.0,
    }


def _resolve_label(label: str, behavior_passed: bool) -> str:
    if label == "unknown":
        return "faithful" if behavior_passed else "plausible_wrong"
    return label


def _write_metadata(path: Path, candidates: list[SmokeCandidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for candidate in candidates:
        payload = {
            "case_id": candidate.case_id,
            "candidate_id": candidate.candidate_id,
            **candidate.metadata,
        }
        lines.append(json.dumps(payload, sort_keys=True))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 2 CPU Smoke",
        "",
        f"- Smoke gate passed: `{payload['smoke_gate_passed']}`",
        f"- Cases: `{payload['case_count']}`",
        f"- Candidates: `{payload['candidate_count']}`",
        f"- Compile pass count: `{payload['compile_pass_count']}`",
        f"- Behavior labels: `{payload['behavior_label_counts']}`",
        f"- Fixture collapse: `{payload['fixture_collapse']}`",
        f"- Non-oracle probe count: `{payload['non_oracle_probe_count']}`",
        f"- Trace pairwise AUC: `{payload['trace_pairwise_auc']:.4f}`",
        "",
        "This smoke validates the manifest, compile/behavior gate, metadata sidecar, and Dynamic Trace v2 path without using GPU.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_markdown_zh(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 2 CPU Smoke",
        "",
        f"- Smoke gate passed: `{payload['smoke_gate_passed']}`",
        f"- Cases: `{payload['case_count']}`",
        f"- Candidates: `{payload['candidate_count']}`",
        f"- Compile pass count: `{payload['compile_pass_count']}`",
        f"- Behavior labels: `{payload['behavior_label_counts']}`",
        f"- Fixture collapse: `{payload['fixture_collapse']}`",
        f"- Non-oracle probe count: `{payload['non_oracle_probe_count']}`",
        f"- Trace pairwise AUC: `{payload['trace_pairwise_auc']:.4f}`",
        "",
        "这个 CPU smoke 验证 manifest、compile/behavior gate、metadata sidecar 和 Dynamic Trace v2 链路，没有使用 GPU。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing non-empty string field: {key}")
    return value


if __name__ == "__main__":
    main()
