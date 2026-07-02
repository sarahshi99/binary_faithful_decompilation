from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from analysis.decompile_faithfulness import dynamic_trace, fixtures
from analysis.decompile_faithfulness import run_dynamic_trace_audit as v1


DEFAULT_MANIFEST = Path(
    "analysis_outputs/decompile_faithfulness/phase2_gpu_full_v1_plus_topup/manifest.json"
)
DEFAULT_RECORDS = Path(
    "analysis_outputs/decompile_faithfulness/phase2_gpu_full_v1_plus_topup/records.jsonl"
)


def main() -> None:
    args = parse_args()
    summary = run_audit(
        manifest_json=args.manifest_json,
        records_jsonl=args.records_jsonl,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "candidate_count": summary["candidate_count"],
                "pairwise_auc": summary["pairwise_auc"],
                "fixture_collapse": summary["fixture_collapse"],
                "case_pairwise_auc": summary["case_pairwise_auc"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--records-jsonl", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase2_v3_boundary_trace"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase2_v3_boundary_trace.json"),
    )
    parser.add_argument(
        "--output-zh",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase2_v3_boundary_trace.zh.md"),
    )
    return parser.parse_args()


def run_audit(
    manifest_json: Path,
    records_jsonl: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    source_by_candidate = _source_by_candidate(manifest)
    input_counts = {
        case.case_id: len(dynamic_trace.generate_boundary_trace_inputs(case, max_inputs=256))
        for case in fixtures.builtin_cases()
    }
    records = [
        record for record in _read_jsonl(records_jsonl)
        if record.get("label") in {"faithful", "plausible_wrong"}
        and record.get("compiled")
        and "features" in record
    ]
    v3_records: list[dict[str, Any]] = []
    trace_dir = output_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        source = source_by_candidate.get(record["candidate_id"])
        if source is None:
            raise KeyError(f"missing source for candidate: {record['candidate_id']}")
        features = _dynamic_trace_v3_features(
            fixtures.case_by_id(record["case_id"]),
            record["candidate_id"],
            source,
            trace_dir,
        )
        v3_record = dict(record)
        v3_record["features_v2"] = record["features"]
        v3_record["features"] = features
        v3_records.append(v3_record)

    records_path = output_dir / "records.jsonl"
    _write_jsonl(records_path, v3_records)
    case_pairwise_auc = {
        case_id: _pairwise_auc(
            [record for record in v3_records if record["case_id"] == case_id],
            _trace_score,
        )
        for case_id in sorted({record["case_id"] for record in v3_records})
    }
    summary = {
        "manifest_path": str(manifest_json),
        "source_records_path": str(records_jsonl),
        "records_path": str(records_path),
        "candidate_count": len(v3_records),
        "input_counts": input_counts,
        "label_counts": {
            label: sum(1 for record in v3_records if record["label"] == label)
            for label in ["faithful", "plausible_wrong"]
        },
        "pairwise_auc": _pairwise_auc(v3_records, _trace_score),
        "case_pairwise_auc": case_pairwise_auc,
        "fixture_collapse": v1._fixture_collapse(v3_records),
        "trace_zero_blind_spot_wrong_count": _trace_zero_blind_spot_wrong_count(v3_records),
        "fixture_passing_trace_mismatch_count": _fixture_passing_trace_mismatch_count(v3_records),
    }
    summary["verdict"] = _verdict(summary)
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def _dynamic_trace_v3_features(
    case: fixtures.FunctionCase,
    candidate_id: str,
    candidate_source: str,
    trace_dir: Path,
) -> dict[str, float]:
    primary_inputs = dynamic_trace.generate_boundary_trace_inputs(
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
            candidate_id,
            candidate_source,
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
            f"{candidate_id}_fixture",
            candidate_source,
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
        "fixture_mismatch_rate": fixture_mismatch_rate,
        "fixture_behavior_passed": 1.0 if fixture_mismatch_rate == 0.0 else 0.0,
    }


def _source_by_candidate(manifest: list[dict[str, Any]]) -> dict[str, str]:
    return {
        candidate["candidate_id"]: candidate["function_source"]
        for entry in manifest
        for candidate in entry.get("candidates", [])
    }


def _pairwise_auc(records: list[dict[str, Any]], score: Callable[[dict[str, Any]], float]) -> float:
    credit = 0.0
    pairs = 0
    for case_id in sorted({record["case_id"] for record in records}):
        case_records = [record for record in records if record["case_id"] == case_id]
        faithful = [record for record in case_records if record["label"] == "faithful"]
        wrong = [record for record in case_records if record["label"] == "plausible_wrong"]
        for faithful_record in faithful:
            faithful_score = score(faithful_record)
            for wrong_record in wrong:
                pairs += 1
                wrong_score = score(wrong_record)
                if wrong_score > faithful_score:
                    credit += 1.0
                elif wrong_score == faithful_score:
                    credit += 0.5
    return credit / pairs if pairs else 0.0


def _trace_score(record: dict[str, Any]) -> float:
    return float(record["features"].get("trace_total", 0.0))


def _trace_zero_blind_spot_wrong_count(records: list[dict[str, Any]]) -> int:
    return sum(
        1
        for record in records
        if record["label"] == "plausible_wrong"
        and float(record["features"].get("trace_total", 0.0)) == 0.0
        and float(record["features"].get("fixture_mismatch_rate", 0.0)) > 0.0
    )


def _fixture_passing_trace_mismatch_count(records: list[dict[str, Any]]) -> int:
    return sum(
        1
        for record in records
        if record["label"] == "faithful"
        and float(record["features"].get("trace_mismatch_rate", 0.0)) > 0.0
    )


def _verdict(summary: dict[str, Any]) -> str:
    hard_cases_pass = (
        summary["case_pairwise_auc"].get("signum") == 1.0
        and summary["case_pairwise_auc"].get("is_power_of_two") == 1.0
    )
    if (
        summary["pairwise_auc"] >= 0.9623
        and hard_cases_pass
        and not summary["fixture_collapse"]
        and summary["trace_zero_blind_spot_wrong_count"] == 0
    ):
        return "pass-v3-boundary-trace"
    return "needs-more-v3-work"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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
    lines = [
        "# Decompilation Faithfulness Phase 2 V3 Boundary Trace",
        "",
        f"- Verdict: `{summary['verdict']}`",
        f"- Candidate count: `{summary['candidate_count']}`",
        f"- Label counts: `{summary['label_counts']}`",
        f"- Pairwise AUC: `{summary['pairwise_auc']:.4f}`",
        f"- Case pairwise AUC: `{summary['case_pairwise_auc']}`",
        f"- Fixture collapse: `{summary['fixture_collapse']}`",
        f"- Trace-zero blind spot wrong count: `{summary['trace_zero_blind_spot_wrong_count']}`",
        f"- Fixture-passing trace mismatch count: `{summary['fixture_passing_trace_mismatch_count']}`",
        f"- Input counts: `{summary['input_counts']}`",
        "",
        "## Interpretation",
        "",
        "V3 boundary trace 不使用 `fixture_mismatch_rate` 作为主分数，而是在 primary generated trace inputs 中强制保留通用 boundary probes，例如 `0`, `-1`, `1`。这避免了 v2 因为排除 fixture args 而同时排除通用边界值的问题。",
        "",
        "成功 gate：overall AUC 至少保持 v2 combined 的 `0.9623`，`signum` 和 `is_power_of_two` case AUC 提升到 `1.0000`，`fixture_collapse=False`，且 trace-zero blind spot wrong count 归零。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
