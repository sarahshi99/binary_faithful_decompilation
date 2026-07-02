from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from analysis.decompile_faithfulness import dynamic_trace, fixtures
from analysis.decompile_faithfulness import run_dynamic_trace_audit as v1


DEFAULT_SOURCE_POOL = Path("docs/paper_agent/decompile_faithfulness_phase3_source_pool.json")
DEFAULT_CANDIDATE_POOL = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_candidate_pool.json"
)
DEFAULT_SOURCE_SELECTION = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_source_selection.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "analysis_outputs/decompile_faithfulness/phase3_combinatorial_cpu_audit"
)
DEFAULT_OUTPUT_JSON = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_combinatorial_cpu_audit.json"
)
DEFAULT_OUTPUT_ZH = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_combinatorial_cpu_audit.zh.md"
)


def main() -> None:
    args = parse_args()
    summary = run_audit(
        repo_root=args.repo_root,
        source_pool=args.source_pool,
        candidate_pool=args.candidate_pool,
        source_selection=args.source_selection,
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
                "recommended_subset_count": len(summary["recommended_subset_metrics"]),
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--source-pool", type=Path, default=DEFAULT_SOURCE_POOL)
    parser.add_argument("--candidate-pool", type=Path, default=DEFAULT_CANDIDATE_POOL)
    parser.add_argument("--source-selection", type=Path, default=DEFAULT_SOURCE_SELECTION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    return parser.parse_args()


def run_audit(
    repo_root: Path,
    source_pool: Path,
    candidate_pool: Path,
    source_selection: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    source_pool = _resolve(repo_root, source_pool)
    candidate_pool = _resolve(repo_root, candidate_pool)
    source_selection = _resolve(repo_root, source_selection)
    output_dir = _resolve(repo_root, output_dir)
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)

    output_dir.mkdir(parents=True, exist_ok=True)
    pool = json.loads(source_pool.read_text(encoding="utf-8"))
    candidate_data = json.loads(candidate_pool.read_text(encoding="utf-8"))
    selection = json.loads(source_selection.read_text(encoding="utf-8"))

    cases = {
        entry["case_id"]: _case_from_pool_entry(repo_root, entry)
        for entry in pool["functions"]
    }
    records = _audit_candidates(
        cases=cases,
        candidate_data=candidate_data.get("candidates", {}),
        output_dir=output_dir / "traces",
    )
    records_path = output_dir / "records.jsonl"
    _write_jsonl(records_path, records)

    case_pairwise_auc = {
        case_id: _pairwise_auc(
            [record for record in records if record["case_id"] == case_id],
            _trace_score,
        )
        for case_id in sorted(cases)
    }
    recommended_subset_metrics = [
        _subset_metrics(index, subset, records)
        for index, subset in enumerate(selection.get("recommended_subsets", []), start=1)
    ]
    fixture_passing_wrong_count = _fixture_passing_wrong_count(records)
    summary: dict[str, Any] = {
        "source_pool": str(source_pool),
        "candidate_pool": str(candidate_pool),
        "source_selection": str(source_selection),
        "records_path": str(records_path),
        "case_count": len(cases),
        "candidate_count": len(records),
        "label_counts": _label_counts(records),
        "pairwise_auc": _pairwise_auc(records, _trace_score),
        "case_pairwise_auc": case_pairwise_auc,
        "fixture_collapse": v1._fixture_collapse(records),
        "fixture_passing_wrong_count": fixture_passing_wrong_count,
        "fixture_passing_wrong_examples": [
            {
                "case_id": record["case_id"],
                "candidate_id": record["candidate_id"],
                "trace_total": record["features"]["trace_total"],
                "trace_mismatch_rate": record["features"]["trace_mismatch_rate"],
            }
            for record in records
            if record["label"] == "plausible_wrong"
            and record["features"]["fixture_mismatch_rate"] == 0.0
            and record["features"]["trace_mismatch_rate"] > 0.0
        ],
        "recommended_subset_metrics": recommended_subset_metrics,
    }
    summary["verdict"] = _verdict(summary)
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def _case_from_pool_entry(repo_root: Path, entry: dict[str, Any]) -> fixtures.FunctionCase:
    tests = tuple(
        fixtures.FunctionTest(tuple(int(value) for value in item["args"]), int(item["expected"]))
        for item in entry.get("fixtures", [])
    )
    return fixtures.FunctionCase(
        case_id=entry["case_id"],
        function_name=entry["function_name"],
        function_source=(repo_root / entry["source_path"]).read_text(encoding="utf-8"),
        tests=tests,
    )


def _audit_candidates(
    cases: dict[str, fixtures.FunctionCase],
    candidate_data: dict[str, list[dict[str, Any]]],
    output_dir: Path,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for case_id, case in cases.items():
        candidates = [
            {
                "candidate_id": f"{case_id}__original",
                "label": "faithful",
                "mutation_type": "original",
                "function_source": case.function_source,
            }
        ] + candidate_data.get(case_id, [])
        for candidate in candidates:
            features = _dynamic_trace_v3_features(
                case=case,
                candidate_id=candidate["candidate_id"],
                candidate_source=candidate["function_source"],
                trace_dir=output_dir,
            )
            records.append(
                {
                    "case_id": case_id,
                    "candidate_id": candidate["candidate_id"],
                    "label": candidate["label"],
                    "mutation_type": candidate.get("mutation_type", "manual"),
                    "compiled": features["compiled"] == 1.0,
                    "features": {
                        key: value
                        for key, value in features.items()
                        if key not in {"compiled", "primary_exit_code", "fixture_exit_code"}
                    },
                    "diagnostics": {
                        "primary_exit_code": features["primary_exit_code"],
                        "fixture_exit_code": features["fixture_exit_code"],
                    },
                }
            )
    return records


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
        if candidate_run.compiled and candidate_run.exit_code == 0:
            components = dynamic_trace.trace_distance(
                primary_inputs,
                original_run.outputs,
                candidate_run.outputs,
            ).components
        else:
            components = _failure_components(len(primary_inputs))

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
        "compiled": 1.0 if candidate_run.compiled else 0.0,
        "primary_exit_code": float(candidate_run.exit_code),
        "fixture_exit_code": float(candidate_fixture.exit_code),
    }


def _failure_components(input_count: int) -> dict[str, float]:
    return {
        "trace_input_count": float(input_count),
        "trace_mismatch_count": float(input_count),
        "trace_mismatch_rate": 1.0,
        "trace_abs_error_mean": 1.0,
        "trace_abs_error_max": 1.0,
        "trace_sign_mismatch_rate": 1.0,
        "trace_zero_mismatch_rate": 1.0,
        "trace_boundary_mismatch_rate": 1.0,
        "trace_total": 2.0,
    }


def _subset_metrics(
    index: int,
    subset: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    case_ids = set(subset["case_ids"])
    subset_records = [record for record in records if record["case_id"] in case_ids]
    return {
        "rank": index,
        "size": subset["size"],
        "case_ids": subset["case_ids"],
        "pairwise_auc": _pairwise_auc(subset_records, _trace_score),
        "pair_count": _pair_count(subset_records),
        "fixture_collapse": v1._fixture_collapse(subset_records),
        "fixture_passing_wrong_count": _fixture_passing_wrong_count(subset_records),
        "label_counts": _label_counts(subset_records),
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
    total = 0
    for case_id in sorted({record["case_id"] for record in records}):
        case_records = [record for record in records if record["case_id"] == case_id]
        total += sum(1 for record in case_records if record["label"] == "faithful") * sum(
            1 for record in case_records if record["label"] == "plausible_wrong"
        )
    return total


def _trace_score(record: dict[str, Any]) -> float:
    return float(record["features"].get("trace_total", 0.0))


def _fixture_passing_wrong_count(records: list[dict[str, Any]]) -> int:
    return sum(
        1
        for record in records
        if record["label"] == "plausible_wrong"
        and float(record["features"].get("fixture_mismatch_rate", 1.0)) == 0.0
        and float(record["features"].get("trace_mismatch_rate", 0.0)) > 0.0
    )


def _label_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        label: sum(1 for record in records if record["label"] == label)
        for label in sorted({record["label"] for record in records})
    }


def _verdict(summary: dict[str, Any]) -> str:
    subset_metrics = summary["recommended_subset_metrics"]
    if (
        summary["pairwise_auc"] >= 0.95
        and not summary["fixture_collapse"]
        and summary["fixture_passing_wrong_count"] >= 3
        and subset_metrics
        and all(item["pairwise_auc"] >= 0.95 for item in subset_metrics)
        and all(not item["fixture_collapse"] for item in subset_metrics)
        and all(item["fixture_passing_wrong_count"] >= 1 for item in subset_metrics)
    ):
        return "pass-combinatorial-phase3-cpu-audit"
    return "needs-phase3-cpu-audit-analysis"


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


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
    case_rows = "\n".join(
        f"| `{case_id}` | `{auc:.4f}` |"
        for case_id, auc in summary["case_pairwise_auc"].items()
    )
    subset_rows = "\n".join(
        "| {rank} | `{size}` | `{auc:.4f}` | `{collapse}` | `{hidden}` | `{cases}` |".format(
            rank=item["rank"],
            size=item["size"],
            auc=item["pairwise_auc"],
            collapse=item["fixture_collapse"],
            hidden=item["fixture_passing_wrong_count"],
            cases=", ".join(item["case_ids"]),
        )
        for item in summary["recommended_subset_metrics"]
    )
    hidden_rows = "\n".join(
        "| `{case_id}` | `{candidate_id}` | `{trace_total:.4f}` | `{trace_mismatch_rate:.4f}` |".format(
            **item
        )
        for item in summary["fixture_passing_wrong_examples"]
    )
    text = f"""# Decompilation Faithfulness Phase 3 Combinatorial CPU Audit

- Verdict: `{summary['verdict']}`
- Case count: `{summary['case_count']}`
- Candidate count: `{summary['candidate_count']}`
- Label counts: `{summary['label_counts']}`
- Overall pairwise AUC: `{summary['pairwise_auc']:.4f}`
- Fixture collapse: `{summary['fixture_collapse']}`
- Fixture-passing wrong count: `{summary['fixture_passing_wrong_count']}`
- Records: `{summary['records_path']}`

## Interpretation

这是 Phase 3 的 CPU-only 组合审计，不使用 GPU。它不再依赖单次选择 5 个函数，而是在 source selection 推荐的 minimal / balanced / broad / low-overlap 子集上同时检查 v3 boundary trace。

本轮候选是 source-known manual stress candidates，标签来自人工语义标注，不是 fixture pass/fail。这样可以显式检查 fixture-passing wrong candidates 是否仍能被 wider v3 trace 抓住。

## Case AUC

| Case | Pairwise AUC |
|---|---:|
{case_rows}

## Recommended Subset Metrics

| Rank | Size | AUC | Fixture Collapse | Fixture-passing Wrong | Cases |
|---:|---:|---:|---:|---:|---|
{subset_rows}

## Fixture-passing Wrong Examples

| Case | Candidate | Trace Total | Trace Mismatch Rate |
|---|---|---:|---:|
{hidden_rows}

## Claim Boundary

这个结果如果通过，只支持 source-known small-function transfer readiness。它仍不等于 arbitrary real-project transfer，也不等于 binary-only semantic equivalence。GPU 2/3 只有在需要生成新 LLM candidates 时才进入下一步。
"""
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
