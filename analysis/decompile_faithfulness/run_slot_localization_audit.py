from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import features, fixtures, localization, mutations


def main() -> None:
    args = parse_args()
    summary = run_audit(
        output_jsonl=args.output_jsonl,
        artifact_dir=args.artifact_dir,
        opt_level=args.opt_level,
    )
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1c/localization_records.jsonl"),
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1c/candidates"),
    )
    parser.add_argument("--opt-level", default="O0")
    return parser.parse_args()


def run_audit(
    output_jsonl: Path,
    artifact_dir: Path,
    opt_level: str,
) -> dict[str, object]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    localization_records: list[localization.LocalizationRecord] = []

    for case in fixtures.builtin_cases():
        original_result = ccompile.compile_candidate(
            case=case,
            candidate_id="original",
            function_source=case.function_source,
            output_dir=artifact_dir,
            opt_level=opt_level,
        )
        if not original_result.compiled or not original_result.behavior_passed:
            raise RuntimeError(f"original case failed compile/behavior gate: {case.case_id}")
        original_features = features.extract_binary_features(original_result.object_path)

        for mutation in mutations.generate_rule_mutations(case):
            result = ccompile.compile_candidate(
                case=case,
                candidate_id=mutation.candidate_id,
                function_source=mutation.function_source,
                output_dir=artifact_dir,
                opt_level=opt_level,
            )
            if not result.compiled or result.behavior_passed:
                continue
            candidate_features = features.extract_binary_features(result.object_path)
            distance = features.feature_distance(original_features, candidate_features)
            votes = localization.component_to_slot_votes(distance.components)
            ranked_slots = localization.rank_slots(votes)
            record = localization.LocalizationRecord(
                case_id=case.case_id,
                candidate_id=mutation.candidate_id,
                expected_slot=mutation.expected_slot,
                ranked_slots=ranked_slots,
            )
            localization_records.append(record)
            records.append(
                {
                    "case_id": record.case_id,
                    "candidate_id": record.candidate_id,
                    "expected_slot": record.expected_slot,
                    "ranked_slots": record.ranked_slots,
                    "hit_at_1": localization.hit_at_k(record.ranked_slots, record.expected_slot, 1),
                    "hit_at_2": localization.hit_at_k(record.ranked_slots, record.expected_slot, 2),
                    "hit_at_3": localization.hit_at_k(record.ranked_slots, record.expected_slot, 3),
                    "components": distance.components,
                    "votes": votes,
                }
            )

    summary = localization.compute_localization_summary(localization_records)
    summary["records_path"] = str(output_jsonl)
    _write_jsonl(output_jsonl, records)
    return summary


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
