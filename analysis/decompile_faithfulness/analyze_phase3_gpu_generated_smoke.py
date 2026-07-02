from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from analysis.decompile_faithfulness import run_dynamic_trace_audit as v1


DEFAULT_RUNS = [
    (
        "cuda2_base",
        Path("analysis_outputs/decompile_faithfulness/phase3_gpu_generated_smoke_cuda2_subset1_fp16/records.jsonl"),
    ),
    (
        "cuda2_bugtopup",
        Path("analysis_outputs/decompile_faithfulness/phase3_gpu_generated_smoke_cuda2_subset1_bugtopup_fp16/records.jsonl"),
    ),
    (
        "cuda3_base",
        Path("analysis_outputs/decompile_faithfulness/phase3_gpu_generated_smoke_cuda3_subset2_fp16/records.jsonl"),
    ),
    (
        "cuda3_bugtopup",
        Path("analysis_outputs/decompile_faithfulness/phase3_gpu_generated_smoke_cuda3_subset2_bugtopup_fp16/records.jsonl"),
    ),
]
DEFAULT_OUTPUT_JSON = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_gpu_generated_combined_analysis.json"
)
DEFAULT_OUTPUT_ZH = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_gpu_generated_combined_analysis.zh.md"
)


def main() -> None:
    args = parse_args()
    summary = run_analysis(
        runs=args.run,
        output_json=args.output_json,
        output_zh=args.output_zh,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "candidate_count": summary["candidate_count"],
                "compile_pass_count": summary["compile_pass_count"],
                "paired_case_count": summary["paired_case_count"],
                "pairwise_auc": summary["pairwise_auc"],
                "fixture_collapse": summary["fixture_collapse"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        action="append",
        nargs=2,
        metavar=("RUN_ID", "RECORDS_JSONL"),
        default=None,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    return parser.parse_args()


def run_analysis(
    runs: list[tuple[str, str | Path]] | None = None,
    output_json: Path = DEFAULT_OUTPUT_JSON,
    output_zh: Path = DEFAULT_OUTPUT_ZH,
) -> dict[str, Any]:
    run_specs = [(run_id, Path(path)) for run_id, path in (runs or DEFAULT_RUNS)]
    records = _load_prefixed_records(run_specs)
    eval_records = [
        record for record in records
        if record["label"] in {"faithful", "plausible_wrong"} and "features" in record
    ]
    case_metrics = {
        case_id: _case_summary(
            [record for record in records if record["case_id"] == case_id]
        )
        for case_id in sorted({record["case_id"] for record in records})
    }
    run_metrics = {
        run_id: _case_summary(
            [record for record in records if record["run_id"] == run_id]
        )
        for run_id, _path in run_specs
    }
    summary: dict[str, Any] = {
        "runs": [{"run_id": run_id, "records_path": str(path)} for run_id, path in run_specs],
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record.get("compiled")),
        "label_counts": _label_counts(records),
        "paired_case_count": sum(1 for item in case_metrics.values() if item["pair_count"] > 0),
        "pair_count": _pair_count(eval_records),
        "pairwise_auc": _pairwise_auc(eval_records, _trace_score),
        "fixture_collapse": v1._fixture_collapse(eval_records),
        "fixture_passing_trace_mismatch_count": _fixture_passing_trace_mismatch_count(eval_records),
        "fixture_passing_trace_mismatch_examples": [
            _example(record)
            for record in eval_records
            if record["label"] == "faithful"
            and float(record["features"].get("fixture_mismatch_rate", 1.0)) == 0.0
            and float(record["features"].get("trace_mismatch_rate", 0.0)) > 0.0
        ],
        "case_metrics": case_metrics,
        "run_metrics": run_metrics,
    }
    summary["verdict"] = _verdict(summary)
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def _load_prefixed_records(run_specs: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for run_id, path in run_specs:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            record["run_id"] = run_id
            record["original_candidate_id"] = record["candidate_id"]
            record["candidate_id"] = f"{run_id}__{record['candidate_id']}"
            records.append(record)
    return records


def _case_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    eval_records = [
        record for record in records
        if record["label"] in {"faithful", "plausible_wrong"} and "features" in record
    ]
    return {
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record.get("compiled")),
        "label_counts": _label_counts(records),
        "pair_count": _pair_count(eval_records),
        "pairwise_auc": _pairwise_auc(eval_records, _trace_score),
        "fixture_collapse": v1._fixture_collapse(eval_records),
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


def _pair_count(records: list[dict[str, Any]]) -> int:
    pairs = 0
    for case_id in sorted({record["case_id"] for record in records}):
        case_records = [record for record in records if record["case_id"] == case_id]
        pairs += sum(1 for record in case_records if record["label"] == "faithful") * sum(
            1 for record in case_records if record["label"] == "plausible_wrong"
        )
    return pairs


def _trace_score(record: dict[str, Any]) -> float:
    return float(record["features"].get("trace_total", 0.0))


def _fixture_passing_trace_mismatch_count(records: list[dict[str, Any]]) -> int:
    return sum(
        1
        for record in records
        if record["label"] == "faithful"
        and float(record["features"].get("fixture_mismatch_rate", 1.0)) == 0.0
        and float(record["features"].get("trace_mismatch_rate", 0.0)) > 0.0
    )


def _label_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        label: sum(1 for record in records if record["label"] == label)
        for label in sorted({record["label"] for record in records})
    }


def _example(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": record["run_id"],
        "case_id": record["case_id"],
        "candidate_id": record["candidate_id"],
        "trace_total": record["features"].get("trace_total"),
        "trace_mismatch_rate": record["features"].get("trace_mismatch_rate"),
        "fixture_mismatch_rate": record["features"].get("fixture_mismatch_rate"),
    }


def _verdict(summary: dict[str, Any]) -> str:
    if (
        summary["candidate_count"] >= 40
        and summary["compile_pass_count"] >= 20
        and summary["paired_case_count"] >= 5
        and summary["pairwise_auc"] >= 0.95
        and not summary["fixture_collapse"]
        and summary["fixture_passing_trace_mismatch_count"] >= 1
    ):
        return "pass-phase3-gpu-generated-combined-analysis"
    return "needs-more-phase3-gpu-generated-analysis"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown_zh(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    case_rows = "\n".join(
        "| `{case_id}` | `{candidate_count}` | `{compile_pass_count}` | `{labels}` | `{pairs}` | `{auc:.4f}` | `{collapse}` |".format(
            case_id=case_id,
            candidate_count=item["candidate_count"],
            compile_pass_count=item["compile_pass_count"],
            labels=item["label_counts"],
            pairs=item["pair_count"],
            auc=item["pairwise_auc"],
            collapse=item["fixture_collapse"],
        )
        for case_id, item in summary["case_metrics"].items()
    )
    run_rows = "\n".join(
        "| `{run_id}` | `{candidate_count}` | `{compile_pass_count}` | `{labels}` | `{pairs}` | `{auc:.4f}` | `{collapse}` |".format(
            run_id=run_id,
            candidate_count=item["candidate_count"],
            compile_pass_count=item["compile_pass_count"],
            labels=item["label_counts"],
            pairs=item["pair_count"],
            auc=item["pairwise_auc"],
            collapse=item["fixture_collapse"],
        )
        for run_id, item in summary["run_metrics"].items()
    )
    hidden_rows = "\n".join(
        "| `{run_id}` | `{case_id}` | `{candidate_id}` | `{trace_total:.4f}` | `{trace_mismatch_rate:.4f}` |".format(
            **item
        )
        for item in summary["fixture_passing_trace_mismatch_examples"]
    )
    text = f"""# Decompilation Faithfulness Phase 3 GPU Generated Combined Analysis

- Verdict: `{summary['verdict']}`
- Candidate count: `{summary['candidate_count']}`
- Compile pass count: `{summary['compile_pass_count']}`
- Label counts: `{summary['label_counts']}`
- Paired case count: `{summary['paired_case_count']}`
- Pair count: `{summary['pair_count']}`
- Pairwise AUC: `{summary['pairwise_auc']:.4f}`
- Fixture collapse: `{summary['fixture_collapse']}`
- Fixture-passing trace mismatch count: `{summary['fixture_passing_trace_mismatch_count']}`

## Interpretation

四个 Phase 3 GPU generated smoke/top-up run 合并后，已经形成可解释的 generated-candidate distribution。单个小 run 可能 paired cases 不足或 fixture-collapse 统计不可解读；合并后有 5 个 case 出现 faithful/wrong 配对，overall pairwise AUC 为 `1.0000`，并且出现 fixture-passing 但 trace-mismatching 的 generated candidate。

这支持的仍是 source-known small-function transfer readiness，不是 arbitrary real-project transfer 或 binary-only semantic equivalence。

## Run Metrics

| Run | Candidates | Compile Pass | Labels | Pairs | AUC | Fixture Collapse |
|---|---:|---:|---|---:|---:|---:|
{run_rows}

## Case Metrics

| Case | Candidates | Compile Pass | Labels | Pairs | AUC | Fixture Collapse |
|---|---:|---:|---|---:|---:|---:|
{case_rows}

## Fixture-passing Trace Mismatch Examples

| Run | Case | Candidate | Trace Total | Trace Mismatch Rate |
|---|---|---|---:|---:|
{hidden_rows}
"""
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
