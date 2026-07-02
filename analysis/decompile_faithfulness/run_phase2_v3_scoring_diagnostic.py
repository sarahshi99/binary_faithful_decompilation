from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


DEFAULT_RECORDS = Path(
    "analysis_outputs/decompile_faithfulness/phase2_gpu_full_v1_plus_topup/records.jsonl"
)


@dataclass(frozen=True)
class ScoreFormula:
    name: str
    risk: str
    description: str
    score: Callable[[dict[str, float]], float]


def main() -> None:
    args = parse_args()
    summary = run_diagnostic(
        records_jsonl=args.records_jsonl,
        output_json=args.output_json,
        output_zh=args.output_zh,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "baseline_auc": summary["baseline"]["pairwise_auc"],
                "best_non_fixture": summary["best_non_fixture"],
                "best_fixture_diagnostic": summary["best_fixture_diagnostic"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-jsonl", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase2_v3_scoring_diagnostic.json"),
    )
    parser.add_argument(
        "--output-zh",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase2_v3_scoring_diagnostic.zh.md"),
    )
    return parser.parse_args()


def run_diagnostic(
    records_jsonl: Path,
    output_json: Path,
    output_zh: Path,
) -> dict[str, Any]:
    records = [
        record for record in _read_jsonl(records_jsonl)
        if record.get("label") in {"faithful", "plausible_wrong"} and "features" in record
    ]
    summary = build_summary(records, records_jsonl)
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def build_summary(
    records: list[dict[str, Any]],
    records_jsonl: Path | None = None,
) -> dict[str, Any]:
    formulas = _formulas()
    formula_rows = [_score_formula(records, formula) for formula in formulas]
    baseline = next(row for row in formula_rows if row["formula"] == "trace_total_v2")
    non_fixture_rows = [row for row in formula_rows if row["risk"] == "method_candidate"]
    fixture_rows = [row for row in formula_rows if row["risk"] == "diagnostic_fixture_aware"]
    best_non_fixture = max(non_fixture_rows, key=lambda row: row["pairwise_auc"])
    best_fixture = max(fixture_rows, key=lambda row: row["pairwise_auc"])
    blind_spots = _blind_spot_candidates(records, formulas)
    verdict = _verdict(baseline, best_non_fixture, best_fixture, blind_spots)
    return {
        "records_path": str(records_jsonl) if records_jsonl else "",
        "verdict": verdict,
        "baseline": baseline,
        "best_non_fixture": best_non_fixture,
        "best_fixture_diagnostic": best_fixture,
        "formula_table": formula_rows,
        "blind_spot_candidates": blind_spots,
        "interpretation": {
            "fixture_aware_warning": (
                "fixture-aware formulas are diagnostic upper bounds because fixture_mismatch "
                "is adjacent to the behavior gate used for labels; they should not be claimed "
                "as the final method."
            ),
            "method_candidate_rule": (
                "A publishable v3 method should improve boundary blind spots without directly "
                "using fixture_mismatch as a score input."
            ),
        },
    }


def _formulas() -> list[ScoreFormula]:
    return [
        ScoreFormula(
            "trace_total_v2",
            "method_candidate",
            "Current Dynamic Trace v2 score.",
            lambda f: f.get("trace_total", 0.0),
        ),
        ScoreFormula(
            "trace_total_plus_boundary_0.25",
            "method_candidate",
            "Adds existing generated boundary mismatch to v2 score.",
            lambda f: f.get("trace_total", 0.0) + 0.25 * f.get("trace_boundary_mismatch_rate", 0.0),
        ),
        ScoreFormula(
            "trace_total_plus_boundary_1.00",
            "method_candidate",
            "Strongly weights existing generated boundary mismatch.",
            lambda f: f.get("trace_total", 0.0) + f.get("trace_boundary_mismatch_rate", 0.0),
        ),
        ScoreFormula(
            "trace_total_plus_zero_1.00",
            "method_candidate",
            "Strongly weights zero-output mismatch already present in trace features.",
            lambda f: f.get("trace_total", 0.0) + f.get("trace_zero_mismatch_rate", 0.0),
        ),
        ScoreFormula(
            "trace_total_plus_fixture_0.25",
            "diagnostic_fixture_aware",
            "Diagnostic upper-bound probe that adds fixture mismatch lightly.",
            lambda f: f.get("trace_total", 0.0) + 0.25 * f.get("fixture_mismatch_rate", 0.0),
        ),
        ScoreFormula(
            "trace_total_plus_fixture_1.00",
            "diagnostic_fixture_aware",
            "Diagnostic upper-bound probe that adds fixture mismatch strongly.",
            lambda f: f.get("trace_total", 0.0) + f.get("fixture_mismatch_rate", 0.0),
        ),
        ScoreFormula(
            "max_trace_fixture",
            "diagnostic_fixture_aware",
            "Diagnostic upper-bound probe using max(trace_total, fixture_mismatch).",
            lambda f: max(f.get("trace_total", 0.0), f.get("fixture_mismatch_rate", 0.0)),
        ),
    ]


def _score_formula(records: list[dict[str, Any]], formula: ScoreFormula) -> dict[str, Any]:
    stats = _pair_stats(records, lambda record: formula.score(record["features"]))
    case_auc = {
        case_id: _pair_stats(case_records, lambda record: formula.score(record["features"]))["auc"]
        for case_id, case_records in _records_by_case(records).items()
    }
    zero_wrong_count = sum(
        1
        for record in records
        if record["label"] == "plausible_wrong"
        and formula.score(record["features"]) == 0.0
    )
    blind_spot_wrong_count = sum(
        1
        for record in records
        if record["label"] == "plausible_wrong"
        and record["features"].get("trace_total", 0.0) == 0.0
        and formula.score(record["features"]) == 0.0
    )
    return {
        "formula": formula.name,
        "risk": formula.risk,
        "description": formula.description,
        "pairwise_auc": stats["auc"],
        "pair_count": stats["pair_count"],
        "misordered_or_tied_pairs": stats["misordered_or_tied_pairs"],
        "zero_scored_wrong_count": zero_wrong_count,
        "remaining_trace_zero_blind_spot_wrong_count": blind_spot_wrong_count,
        "case_pairwise_auc": case_auc,
        "weak_cases": {
            case_id: auc for case_id, auc in case_auc.items() if auc < 1.0
        },
    }


def _blind_spot_candidates(
    records: list[dict[str, Any]],
    formulas: list[ScoreFormula],
) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        features = record["features"]
        if (
            record["label"] == "plausible_wrong"
            and features.get("trace_total", 0.0) == 0.0
            and features.get("fixture_mismatch_rate", 0.0) > 0.0
        ):
            rows.append(
                {
                    "case_id": record["case_id"],
                    "candidate_id": record["candidate_id"],
                    "prompt_id": record.get("metadata", {}).get("prompt_id", ""),
                    "trace_total": features.get("trace_total", 0.0),
                    "fixture_mismatch_rate": features.get("fixture_mismatch_rate", 0.0),
                    "trace_boundary_mismatch_rate": features.get("trace_boundary_mismatch_rate", 0.0),
                    "trace_zero_mismatch_rate": features.get("trace_zero_mismatch_rate", 0.0),
                    "formula_scores": {
                        formula.name: formula.score(features) for formula in formulas
                    },
                }
            )
    return rows


def _verdict(
    baseline: dict[str, Any],
    best_non_fixture: dict[str, Any],
    best_fixture: dict[str, Any],
    blind_spots: list[dict[str, Any]],
) -> str:
    baseline_auc = baseline["pairwise_auc"]
    if (
        best_non_fixture["pairwise_auc"] > baseline_auc
        and best_non_fixture["remaining_trace_zero_blind_spot_wrong_count"]
        < baseline["remaining_trace_zero_blind_spot_wrong_count"]
    ):
        return "continue-boundary-formula-v3"
    if (
        best_fixture["pairwise_auc"] > baseline_auc
        or best_fixture["remaining_trace_zero_blind_spot_wrong_count"]
        < baseline["remaining_trace_zero_blind_spot_wrong_count"]
    ) and blind_spots:
        return "needs-boundary-input-regeneration"
    return "no-v3-scoring-gain"


def _records_by_case(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_case[record["case_id"]].append(record)
    return dict(by_case)


def _pair_stats(records: list[dict[str, Any]], score: Callable[[dict[str, Any]], float]) -> dict[str, Any]:
    credit = 0.0
    pairs = 0
    misordered_or_tied = 0
    for case_records in _records_by_case(records).values():
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
                    misordered_or_tied += 1
                else:
                    misordered_or_tied += 1
    return {
        "auc": credit / pairs if pairs else 0.0,
        "pair_count": pairs,
        "misordered_or_tied_pairs": misordered_or_tied,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown_zh(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 2 V3 Scoring Diagnostic",
        "",
        f"- Verdict: `{summary['verdict']}`",
        f"- Baseline AUC: `{summary['baseline']['pairwise_auc']:.4f}`",
        f"- Best non-fixture formula: `{summary['best_non_fixture']['formula']}` "
        f"AUC `{summary['best_non_fixture']['pairwise_auc']:.4f}`",
        f"- Best fixture-aware diagnostic: `{summary['best_fixture_diagnostic']['formula']}` "
        f"AUC `{summary['best_fixture_diagnostic']['pairwise_auc']:.4f}`",
        f"- Trace-zero blind spot candidates: `{len(summary['blind_spot_candidates'])}`",
        "",
        "## Formula Table",
        "",
        "| Formula | Risk | AUC | Misordered/Tied | Zero-scored Wrong | Remaining Trace-zero Blind Spots | Weak Cases |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in summary["formula_table"]:
        lines.append(
            "| "
            f"`{row['formula']}` | `{row['risk']}` | {row['pairwise_auc']:.4f} | "
            f"{row['misordered_or_tied_pairs']} / {row['pair_count']} | "
            f"{row['zero_scored_wrong_count']} | "
            f"{row['remaining_trace_zero_blind_spot_wrong_count']} | "
            f"`{row['weak_cases']}` |"
        )
    lines.extend([
        "",
        "## Trace-zero Blind Spots",
        "",
    ])
    for row in summary["blind_spot_candidates"]:
        lines.append(
            f"- `{row['case_id']}` `{row['prompt_id']}` `{row['candidate_id']}`: "
            f"fixture_mismatch `{row['fixture_mismatch_rate']:.4f}`, "
            f"boundary_mismatch `{row['trace_boundary_mismatch_rate']:.4f}`, "
            f"zero_mismatch `{row['trace_zero_mismatch_rate']:.4f}`"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "这个诊断只复用 Phase 2 combined records，不重新生成候选，也不重跑 trace。",
        "",
        "如果 boundary/zero-only formula 没有优于 v2，而 fixture-aware diagnostic 能消除 blind spot，则说明问题不只是 scoring weight，而是 primary generated trace inputs 缺少必要 boundary cases。此时 v3 应优先重新生成 boundary-aware trace inputs，而不是把 fixture_mismatch 直接加入主方法。",
        "",
        f"Fixture-aware warning: {summary['interpretation']['fixture_aware_warning']}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
