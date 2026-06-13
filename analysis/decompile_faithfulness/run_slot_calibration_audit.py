from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import features, fixtures, localization, ranking


def main() -> None:
    args = parse_args()
    summary = run_audit(
        external_candidates_json=args.external_candidates_json,
        output_json=args.output_json,
        output_md=args.output_md,
        output_jsonl=args.output_jsonl,
        artifact_dir=args.artifact_dir,
        opt_level=args.opt_level,
    )
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-candidates-json", type=Path, required=True)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1d_slot_calibration.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1d_slot_calibration.md"),
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1d_slot_calibration/records.jsonl"),
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1d_slot_calibration/candidates"),
    )
    parser.add_argument("--opt-level", default="O0")
    return parser.parse_args()


def run_audit(
    external_candidates_json: Path,
    output_json: Path,
    output_md: Path,
    output_jsonl: Path,
    artifact_dir: Path,
    opt_level: str,
) -> dict[str, object]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    external_candidates = _load_external_candidates(external_candidates_json)
    external_by_case: dict[str, list[ranking.ExternalCandidate]] = {}
    for external_candidate in external_candidates:
        external_by_case.setdefault(external_candidate.case_id, []).append(external_candidate)

    records: list[dict[str, Any]] = []
    suspicion_records: list[localization.SuspicionRecord] = []

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

        for external_candidate in external_by_case.get(case.case_id, []):
            result = ccompile.compile_candidate(
                case=case,
                candidate_id=external_candidate.candidate_id,
                function_source=external_candidate.function_source,
                output_dir=artifact_dir,
                opt_level=opt_level,
            )
            if not result.compiled:
                continue
            candidate_features = features.extract_binary_features(result.object_path)
            distance = features.feature_distance(original_features, candidate_features)
            votes = localization.component_to_slot_votes(distance.components)
            slot_concentration = localization.slot_vote_concentration(votes)
            label = "faithful" if result.behavior_passed else "plausible_wrong"
            suspicion_records.append(
                localization.SuspicionRecord(
                    case_id=case.case_id,
                    candidate_id=external_candidate.candidate_id,
                    label=label,
                    score=slot_concentration,
                )
            )
            records.append(
                {
                    "case_id": case.case_id,
                    "candidate_id": external_candidate.candidate_id,
                    "label": label,
                    "mutation_type": external_candidate.mutation_type,
                    "global_distance": distance.total,
                    "slot_concentration": slot_concentration,
                    "top_slot": localization.rank_slots(votes)[0],
                    "votes": votes,
                    "components": distance.components,
                }
            )

    summary = {
        "opt_level": opt_level,
        "record_count": len(suspicion_records),
        "faithful_count": sum(1 for record in suspicion_records if record.label == "faithful"),
        "plausible_wrong_count": sum(1 for record in suspicion_records if record.label == "plausible_wrong"),
        "pairwise_slot_concentration_auc": localization.pairwise_suspicion_auc(suspicion_records),
        "mean_faithful_slot_concentration": _mean(
            record.score for record in suspicion_records if record.label == "faithful"
        ),
        "mean_wrong_slot_concentration": _mean(
            record.score for record in suspicion_records if record.label == "plausible_wrong"
        ),
        "verdict": _verdict(localization.pairwise_suspicion_auc(suspicion_records)),
        "records_path": str(output_jsonl),
    }
    _write_json(output_json, summary)
    _write_markdown(output_md, summary)
    _write_jsonl(output_jsonl, records)
    return summary


def _load_external_candidates(path: Path) -> list[ranking.ExternalCandidate]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    manifests = payload if isinstance(payload, list) else [payload]
    candidates: list[ranking.ExternalCandidate] = []
    for manifest in manifests:
        if not isinstance(manifest, dict):
            raise ValueError("external candidate JSON must contain objects")
        candidates.extend(ranking.external_candidates_from_manifest(manifest))
    return candidates


def _verdict(auc: float) -> str:
    if auc >= 0.75:
        return "continue-slot-calibration"
    if auc < 0.60:
        return "inconclusive-or-redesign"
    return "weak-signal"


def _mean(values: object) -> float:
    collected = list(values)
    return sum(collected) / len(collected) if collected else 0.0


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 1D Slot-Calibration Audit",
        "",
        "## Question",
        "",
        (
            "Can slot-vote concentration distinguish localized semantic bugs from broader "
            "behavior-preserving rewrite drift better than raw global feature distance?"
        ),
        "",
        "## Metrics",
        "",
        f"- Compiler optimization: `{payload['opt_level']}`",
        f"- Records: `{payload['record_count']}`",
        f"- Faithful candidates: `{payload['faithful_count']}`",
        f"- Plausible-wrong candidates: `{payload['plausible_wrong_count']}`",
        f"- Pairwise slot-concentration AUC: `{payload['pairwise_slot_concentration_auc']:.4f}`",
        f"- Mean faithful slot concentration: `{payload['mean_faithful_slot_concentration']:.4f}`",
        f"- Mean wrong slot concentration: `{payload['mean_wrong_slot_concentration']:.4f}`",
        f"- Verdict: `{payload['verdict']}`",
        "",
        "## Interpretation",
        "",
        (
            "This audit uses the same realistic manual candidates as Phase 1B, but scores "
            "candidate suspiciousness by concentration of slot-local votes instead of total "
            "binary feature distance. Higher concentration means the mismatch looks more like "
            "a localized source slot error; lower concentration means broader implementation drift."
        ),
        "",
        "## Next Route",
        "",
        (
            "Expand optimization-aware slot-local calibration before real-project transfer. "
            "Add more realistic hard negatives, behavior-preserving rewrites, and compiler "
            "optimization settings, then test whether slot concentration remains calibrated."
        ),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
