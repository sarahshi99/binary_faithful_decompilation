from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import features, fixtures, mutations, ranking, report


def main() -> None:
    args = parse_args()
    payload = run_audit(
        output_json=args.output_json,
        output_md=args.output_md,
        artifact_dir=args.artifact_dir,
        opt_level=args.opt_level,
    )
    print(
        json.dumps(
            {
                "case_count": payload["case_count"],
                "candidate_count": payload["candidate_count"],
                "pairwise_auc": payload["pairwise_auc"],
                "top1_faithful_rate": payload["top1_faithful_rate"],
                "verdict": payload["verdict"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1_audit.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1_audit.md"),
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1a"),
    )
    parser.add_argument("--opt-level", default="O0")
    return parser.parse_args()


def run_audit(
    output_json: Path,
    output_md: Path,
    artifact_dir: Path,
    opt_level: str,
) -> dict[str, Any]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir = artifact_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    records_path = artifact_dir / "records.jsonl"

    distance_rows: list[ranking.CandidateDistance] = []
    records: list[dict[str, Any]] = []
    excluded_compile_fail = 0
    equivalent_or_weak_count = 0

    for case in fixtures.builtin_cases():
        original_result = ccompile.compile_candidate(
            case=case,
            candidate_id="original",
            function_source=case.function_source,
            output_dir=candidate_dir,
            opt_level=opt_level,
        )
        if not original_result.compiled or not original_result.behavior_passed:
            raise RuntimeError(f"original case failed compile/behavior gate: {case.case_id}")
        original_features = features.extract_binary_features(original_result.object_path)
        original_distance = ranking.CandidateDistance(
            case_id=case.case_id,
            candidate_id="original",
            label="faithful",
            distance=0.0,
            mutation_type="original",
        )
        distance_rows.append(original_distance)
        records.append(
            _record(
                original_distance,
                compiled=True,
                behavior_passed=True,
                exit_code=0,
                components={},
                expected_slot="original",
            )
        )

        for mutation in mutations.generate_rule_mutations(case):
            result = ccompile.compile_candidate(
                case=case,
                candidate_id=mutation.candidate_id,
                function_source=mutation.function_source,
                output_dir=candidate_dir,
                opt_level=opt_level,
            )
            if not result.compiled:
                excluded_compile_fail += 1
                records.append(
                    {
                        "case_id": case.case_id,
                        "candidate_id": mutation.candidate_id,
                        "label": "compile_fail",
                        "mutation_type": mutation.mutation_type,
                        "expected_slot": mutation.expected_slot,
                        "compiled": False,
                        "behavior_passed": False,
                        "exit_code": result.exit_code,
                    }
                )
                continue

            candidate_features = features.extract_binary_features(result.object_path)
            distance = features.feature_distance(original_features, candidate_features)
            if result.behavior_passed:
                equivalent_or_weak_count += 1
                label = "equivalent_or_weak"
            else:
                label = "plausible_wrong"

            row = ranking.CandidateDistance(
                case_id=case.case_id,
                candidate_id=mutation.candidate_id,
                label=label,
                distance=distance.total,
                mutation_type=mutation.mutation_type,
            )
            if label == "plausible_wrong":
                distance_rows.append(row)
            records.append(
                _record(
                    row,
                    compiled=True,
                    behavior_passed=result.behavior_passed,
                    exit_code=result.exit_code,
                    components=distance.components,
                    expected_slot=mutation.expected_slot,
                )
            )

    summary = ranking.compute_ranking_summary(distance_rows)
    summary.update(
        {
            "opt_level": opt_level,
            "excluded_compile_fail": excluded_compile_fail,
            "equivalent_or_weak_count": equivalent_or_weak_count,
            "records_path": str(records_path),
        }
    )

    _write_jsonl(records_path, records)
    report.write_json(output_json, summary)
    report.write_markdown(output_md, summary)
    return summary


def _record(
    row: ranking.CandidateDistance,
    compiled: bool,
    behavior_passed: bool,
    exit_code: int,
    components: dict[str, float],
    expected_slot: str,
) -> dict[str, Any]:
    return {
        "case_id": row.case_id,
        "candidate_id": row.candidate_id,
        "label": row.label,
        "mutation_type": row.mutation_type,
        "expected_slot": expected_slot,
        "distance": row.distance,
        "components": components,
        "compiled": compiled,
        "behavior_passed": behavior_passed,
        "exit_code": exit_code,
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
