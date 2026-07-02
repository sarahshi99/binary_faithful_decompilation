from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from analysis.decompile_faithfulness import dynamic_trace, fixtures


@dataclass(frozen=True)
class SourcePaths:
    original: Path
    candidate: Path


@dataclass(frozen=True)
class Formula:
    name: str
    score: Callable[[dict[str, float]], float]


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
        default=Path("docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.md"),
    )
    parser.add_argument(
        "--output-zh",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.zh.md"),
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace/records.jsonl"),
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
    formula_scores = _formula_scores(records, formulas)
    loco = _leave_one_case_out(records, formulas)
    hard_cases = ["signum", "gcd_positive", "max3", "sum_to_n"]
    hard_case_auc = {
        case_id: loco["case_pairwise_auc"].get(case_id, 0.0)
        for case_id in hard_cases
    }
    fixture_collapse = _fixture_collapse(records)
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


def _source_paths_for_record(artifact_root: Path, record: dict[str, Any]) -> SourcePaths:
    case_id = str(record["case_id"])
    candidate_id = str(record["candidate_id"])
    candidates_dir = artifact_root / "o0" / "candidates"
    return SourcePaths(
        original=candidates_dir / f"{case_id}__original__O0.function.c",
        candidate=candidates_dir / f"{case_id}__{candidate_id}__O0.function.c",
    )


def _aggregate_records(
    artifact_roots: list[Path],
    distance_fn: Callable[[SourcePaths], dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    distance = distance_fn or _dynamic_distance_for_paths
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for artifact_root in artifact_roots:
        records_path = artifact_root / "o0" / "records.jsonl"
        if not records_path.exists():
            continue
        for record in _read_jsonl(records_path):
            key = (str(record["case_id"]), str(record["candidate_id"]))
            if key in seen:
                raise ValueError(f"duplicate candidate across artifact roots: {key}")
            seen.add(key)
            paths = _source_paths_for_record(artifact_root, record)
            trace_components = {
                str(component): float(value)
                for component, value in distance(paths).items()
            }
            features = {
                "min_slot": float(record.get("slot_concentration", 0.0)),
                **trace_components,
            }
            rows.append(
                {
                    "case_id": record["case_id"],
                    "candidate_id": record["candidate_id"],
                    "label": record["label"],
                    "mutation_type": record.get("mutation_type", "unknown"),
                    "features": features,
                    "source_paths": {
                        "original": str(paths.original),
                        "candidate": str(paths.candidate),
                    },
                }
            )
    return sorted(rows, key=lambda row: (row["case_id"], row["candidate_id"]))


def _dynamic_distance_for_paths(paths: SourcePaths) -> dict[str, float]:
    case_id = paths.original.name.split("__", 1)[0]
    candidate_id = paths.candidate.name.split("__", 2)[1]
    case = fixtures.case_by_id(case_id)
    original_source = paths.original.read_text(encoding="utf-8")
    candidate_source = paths.candidate.read_text(encoding="utf-8")
    primary_inputs = dynamic_trace.generate_trace_inputs(
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
            components = _compile_fail_components(len(primary_inputs))
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
    }


def _compile_fail_components(input_count: int) -> dict[str, float]:
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


def _formulas() -> list[Formula]:
    return [
        Formula("trace_mismatch_rate", lambda f: f["trace_mismatch_rate"]),
        Formula("trace_total", lambda f: f["trace_total"]),
        Formula("trace_total_plus_min_slot_0.10", lambda f: f["trace_total"] + 0.10 * f["min_slot"]),
        Formula("trace_total_plus_min_slot_0.25", lambda f: f["trace_total"] + 0.25 * f["min_slot"]),
        Formula("min_slot", lambda f: f["min_slot"]),
    ]


def _formula_scores(records: list[dict[str, Any]], formulas: list[Formula]) -> list[dict[str, Any]]:
    formula_order = {formula.name: index for index, formula in enumerate(formulas)}
    rows = [
        {
            "formula": formula.name,
            "pairwise_auc": _pairwise_auc(records, lambda record, formula=formula: formula.score(record["features"])),
        }
        for formula in formulas
    ]
    return sorted(rows, key=lambda row: (-row["pairwise_auc"], formula_order[row["formula"]]))


def _leave_one_case_out(records: list[dict[str, Any]], formulas: list[Formula]) -> dict[str, Any]:
    case_ids = sorted({record["case_id"] for record in records})
    formula_order = {formula.name: index for index, formula in enumerate(formulas)}
    folds: list[dict[str, Any]] = []
    heldout_scores: dict[tuple[str, str], float] = {}
    case_pairwise_auc: dict[str, float] = {}
    for case_id in case_ids:
        train = [record for record in records if record["case_id"] != case_id]
        heldout = [record for record in records if record["case_id"] == case_id]
        ranked = sorted(
            (
                (
                    _pairwise_auc(train, lambda record, formula=formula: formula.score(record["features"])),
                    formula_order[formula.name],
                    formula,
                )
                for formula in formulas
            ),
            key=lambda row: (-row[0], row[1]),
        )
        train_auc, _order, formula = ranked[0]
        heldout_auc = _pairwise_auc(heldout, lambda record, formula=formula: formula.score(record["features"]))
        folds.append(
            {
                "heldout_case": case_id,
                "selected_formula": formula.name,
                "train_pairwise_auc": train_auc,
                "heldout_pairwise_auc": heldout_auc,
            }
        )
        case_pairwise_auc[str(case_id)] = heldout_auc
        for record in heldout:
            heldout_scores[(record["case_id"], record["candidate_id"])] = formula.score(record["features"])
    return {
        "pairwise_auc": _pairwise_auc(
            records,
            lambda record: heldout_scores[(record["case_id"], record["candidate_id"])],
        ),
        "folds": folds,
        "case_pairwise_auc": case_pairwise_auc,
    }


def _pairwise_auc(records: list[dict[str, Any]], score: Callable[[dict[str, Any]], float]) -> float:
    credit = 0.0
    pairs = 0
    for case_id in sorted({record["case_id"] for record in records}):
        case_records = [record for record in records if record["case_id"] == case_id]
        faithful = [record for record in case_records if record["label"] == "faithful"]
        wrong = [record for record in case_records if record["label"] == "plausible_wrong"]
        for faithful_record in faithful:
            for wrong_record in wrong:
                pairs += 1
                wrong_score = score(wrong_record)
                faithful_score = score(faithful_record)
                if wrong_score > faithful_score:
                    credit += 1.0
                elif wrong_score == faithful_score:
                    credit += 0.5
    return credit / pairs if pairs else 0.0


def _fixture_collapse(records: list[dict[str, Any]]) -> bool:
    if not records:
        return False
    return all(
        (record["features"].get("trace_mismatch_rate", 0.0) > 0.0)
        == (record["features"].get("fixture_mismatch_rate", 0.0) > 0.0)
        for record in records
    )


def _verdict(loco_auc: float, hard_case_auc: dict[str, float], fixture_collapse: bool) -> str:
    if fixture_collapse:
        return "oracle-like-dynamic-trace-not-transfer"
    if loco_auc >= 0.85 and all(value >= 0.75 for value in hard_case_auc.values()):
        return "continue-dynamic-trace"
    if loco_auc < 0.75 or sum(1 for value in hard_case_auc.values() if value < 0.667) >= 2:
        return "pivot-or-narrow-scope"
    return "borderline-dynamic-trace"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
        "# Decompilation Faithfulness Phase 1K Dynamic Trace Audit",
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
                "This is Route A of the Phase 1K three-route scout. The primary score uses "
                "generated trace inputs, while fixture-test behavior is reported separately "
                "to detect oracle-like collapse."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_markdown_zh(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 1K Dynamic Trace Audit",
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
                "这是 Phase 1K 三路线 scout 的 Route A。主分数使用 generated trace inputs；"
                "fixture-test 行为只作为诊断字段，用来判断结果是否退化成已有测试 oracle。"
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
