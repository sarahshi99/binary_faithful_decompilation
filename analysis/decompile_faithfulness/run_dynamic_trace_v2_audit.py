from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from analysis.decompile_faithfulness import dynamic_trace, fixtures
from analysis.decompile_faithfulness import run_dynamic_trace_audit as v1


SourcePaths = v1.SourcePaths
Formula = v1.Formula


def main() -> None:
    args = parse_args()
    summary = run_audit(
        artifact_roots=args.artifact_roots,
        output_json=args.output_json,
        output_md=args.output_md,
        output_zh=args.output_zh,
        output_jsonl=args.output_jsonl,
    )
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-roots", nargs="+", type=Path, required=True)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace_v2.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace_v2.md"),
    )
    parser.add_argument(
        "--output-zh",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace_v2.zh.md"),
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace_v2/records.jsonl"),
    )
    return parser.parse_args()


def run_audit(
    artifact_roots: list[Path],
    output_json: Path,
    output_md: Path,
    output_zh: Path,
    output_jsonl: Path,
) -> dict[str, Any]:
    records = _aggregate_records(artifact_roots)
    formulas = _formulas()
    formula_scores = v1._formula_scores(records, formulas)
    loco = v1._leave_one_case_out(records, formulas)
    hard_cases = ["signum", "gcd_positive", "max3", "sum_to_n"]
    hard_case_auc = {
        case_id: loco["case_pairwise_auc"].get(case_id, 0.0)
        for case_id in hard_cases
    }
    fixture_collapse = v1._fixture_collapse(records)
    summary = {
        "artifact_roots": [str(path) for path in artifact_roots],
        "case_count": len({record["case_id"] for record in records}),
        "candidate_count": len(records),
        "faithful_count": sum(1 for record in records if record["label"] == "faithful"),
        "plausible_wrong_count": sum(1 for record in records if record["label"] == "plausible_wrong"),
        "best_in_sample": formula_scores[0] if formula_scores else {"formula": "", "pairwise_auc": 0.0},
        "formula_scores": formula_scores,
        "leave_one_case_out": loco,
        "hard_case_auc": hard_case_auc,
        "fixture_collapse": fixture_collapse,
        "records_path": str(output_jsonl),
        "verdict": _verdict(loco["pairwise_auc"], hard_case_auc, fixture_collapse),
    }
    _write_json(output_json, summary)
    _write_markdown(output_md, summary)
    _write_markdown_zh(output_zh, summary)
    _write_jsonl(output_jsonl, records)
    return summary


def _aggregate_records(
    artifact_roots: list[Path],
    distance_fn: Callable[[SourcePaths], dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    return v1._aggregate_records(artifact_roots, distance_fn or _dynamic_distance_for_paths)


def _dynamic_distance_for_paths(paths: SourcePaths) -> dict[str, float]:
    case_id = paths.original.name.split("__", 1)[0]
    candidate_id = paths.candidate.name.split("__", 2)[1]
    case = fixtures.case_by_id(case_id)
    original_source = paths.original.read_text(encoding="utf-8")
    candidate_source = paths.candidate.read_text(encoding="utf-8")
    primary_inputs = dynamic_trace.generate_domain_trace_inputs(
        case,
        max_inputs=256,
        include_fixture_tests=False,
    )
    fixture_inputs = [
        dynamic_trace.TraceInput(args=test.args, bucket="fixture")
        for test in case.tests
    ]
    with tempfile.TemporaryDirectory() as td:
        output_dir = Path(td)
        original_run = dynamic_trace.run_trace(
            case,
            "original",
            original_source,
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
            raise RuntimeError(f"failed to run original trace for {case_id}: {original_run.stderr}")
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
            original_source,
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
        **_domain_components(case, primary_inputs),
        "fixture_mismatch_rate": fixture_mismatch_rate,
        "fixture_behavior_passed": 1.0 if fixture_mismatch_rate == 0.0 else 0.0,
    }


def _domain_components(
    case: fixtures.FunctionCase,
    primary_inputs: list[dynamic_trace.TraceInput],
) -> dict[str, float]:
    domain = dynamic_trace.infer_trace_domain(case)
    mixed_inputs = dynamic_trace.generate_trace_inputs(
        case,
        max_inputs=10_000,
        include_fixture_tests=False,
    )
    filtered_count = sum(
        1 for trace_input in mixed_inputs
        if not _args_in_domain(domain, trace_input.args)
    )
    return {
        "trace_domain_positive": 1.0 if domain.all_positive else 0.0,
        "trace_domain_nonnegative": 1.0 if domain.all_nonnegative else 0.0,
        "trace_domain_filtered_count": float(filtered_count),
        "trace_domain_input_count": float(len(primary_inputs)),
    }


def _args_in_domain(domain: dynamic_trace.TraceDomain, args: tuple[int, ...]) -> bool:
    if domain.all_positive:
        return all(value > 0 for value in args)
    if domain.all_nonnegative:
        return all(value >= 0 for value in args)
    return True


def _formulas() -> list[Formula]:
    return v1._formulas()


def _verdict(loco_auc: float, hard_case_auc: dict[str, float], fixture_collapse: bool) -> str:
    if fixture_collapse:
        return "oracle-like-dynamic-trace-v2-not-transfer"
    if loco_auc >= 0.875 and hard_case_auc.get("gcd_positive", 0.0) > 0.5:
        return "pass-dynamic-trace-v2-localized-bug"
    if loco_auc >= 0.85 and hard_case_auc.get("gcd_positive", 0.0) > 0.5:
        return "borderline-dynamic-trace-v2"
    return "fail-dynamic-trace-v2"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
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
        "# Decompilation Faithfulness Phase 1K Dynamic Trace v2 Audit",
        "",
        "## Dataset",
        "",
        f"- Cases: `{payload['case_count']}`",
        f"- Candidates: `{payload['candidate_count']}`",
        f"- Faithful candidates: `{payload['faithful_count']}`",
        f"- Plausible-wrong candidates: `{payload['plausible_wrong_count']}`",
        "",
        "## Leave-One-Case-Out",
        "",
        f"- Pairwise AUC: `{payload['leave_one_case_out']['pairwise_auc']:.4f}`",
        f"- Fixture collapse: `{payload['fixture_collapse']}`",
        f"- Verdict: `{payload['verdict']}`",
        "",
        "| Held-out case | Selected formula | Train AUC | Held-out AUC |",
        "|---|---|---:|---:|",
    ]
    for fold in payload["leave_one_case_out"]["folds"]:
        lines.append(
            "| `{}` | `{}` | `{:.4f}` | `{:.4f}` |".format(
                fold["heldout_case"],
                fold["selected_formula"],
                fold["train_pairwise_auc"],
                fold["heldout_pairwise_auc"],
            )
        )
    lines.extend(["", "## Hard Cases", "", "| Case | Held-out AUC |", "|---|---:|"])
    for case_id, auc in payload["hard_case_auc"].items():
        lines.append(f"| `{case_id}` | `{auc:.4f}` |")
    lines.extend(["", "## Formula Scores", "", "| Formula | Pairwise AUC |", "|---|---:|"])
    for row in payload["formula_scores"]:
        lines.append(f"| `{row['formula']}` | `{row['pairwise_auc']:.4f}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "Dynamic Trace v2 uses fixture-domain-aware generated inputs. It does not use "
                "candidate labels or candidate outputs to choose the input domain."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_markdown_zh(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 1K Dynamic Trace v2 Audit",
        "",
        "## 数据集",
        "",
        f"- Cases: `{payload['case_count']}`",
        f"- Candidates: `{payload['candidate_count']}`",
        f"- Faithful candidates: `{payload['faithful_count']}`",
        f"- Plausible-wrong candidates: `{payload['plausible_wrong_count']}`",
        "",
        "## Leave-One-Case-Out",
        "",
        f"- Pairwise AUC: `{payload['leave_one_case_out']['pairwise_auc']:.4f}`",
        f"- Fixture collapse: `{payload['fixture_collapse']}`",
        f"- Verdict: `{payload['verdict']}`",
        "",
        "| Held-out case | Selected formula | Train AUC | Held-out AUC |",
        "|---|---|---:|---:|",
    ]
    for fold in payload["leave_one_case_out"]["folds"]:
        lines.append(
            "| `{}` | `{}` | `{:.4f}` | `{:.4f}` |".format(
                fold["heldout_case"],
                fold["selected_formula"],
                fold["train_pairwise_auc"],
                fold["heldout_pairwise_auc"],
            )
        )
    lines.extend(["", "## Hard Cases", "", "| Case | Held-out AUC |", "|---|---:|"])
    for case_id, auc in payload["hard_case_auc"].items():
        lines.append(f"| `{case_id}` | `{auc:.4f}` |")
    lines.extend(
        [
            "",
            "## 解释",
            "",
            (
                "Dynamic Trace v2 使用 fixture-domain-aware generated inputs。它只从 "
                "source-known fixture 的参数值推断输入域，不读取 candidate label，也不根据 "
                "candidate output 反向选择输入。"
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
