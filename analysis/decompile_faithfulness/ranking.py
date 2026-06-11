from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CandidateDistance:
    case_id: str
    candidate_id: str
    label: str
    distance: float
    mutation_type: str


def rank_candidates(rows: list[CandidateDistance]) -> list[CandidateDistance]:
    return sorted(rows, key=lambda row: (row.distance, row.candidate_id))


def pairwise_auc(rows: list[CandidateDistance]) -> float:
    credit = 0.0
    pairs = 0
    for case_rows in _by_case(rows).values():
        faithful = [row for row in case_rows if row.label == "faithful"]
        wrong = [row for row in case_rows if row.label == "plausible_wrong"]
        for faithful_row in faithful:
            for wrong_row in wrong:
                pairs += 1
                if faithful_row.distance < wrong_row.distance:
                    credit += 1.0
                elif faithful_row.distance == wrong_row.distance:
                    credit += 0.5
    return credit / pairs if pairs else 0.0


def compute_ranking_summary(rows: list[CandidateDistance]) -> dict[str, object]:
    grouped = _by_case(rows)
    top1_faithful_count = 0
    for case_rows in grouped.values():
        ranked = rank_candidates(case_rows)
        if ranked and ranked[0].label == "faithful":
            top1_faithful_count += 1

    by_mutation_type: dict[str, dict[str, object]] = {}
    wrong_rows = [row for row in rows if row.label == "plausible_wrong"]
    for mutation_type in sorted({row.mutation_type for row in wrong_rows}):
        bucket = [row for row in wrong_rows if row.mutation_type == mutation_type]
        by_mutation_type[mutation_type] = {
            "candidate_count": len(bucket),
            "mean_distance": _mean(row.distance for row in bucket),
        }

    case_count = len(grouped)
    top1_rate = top1_faithful_count / case_count if case_count else 0.0
    auc = pairwise_auc(rows)
    verdict = verdict_from_metrics(auc, top1_rate)
    return {
        "case_count": case_count,
        "candidate_count": len(rows),
        "faithful_count": sum(1 for row in rows if row.label == "faithful"),
        "plausible_wrong_count": len(wrong_rows),
        "top1_faithful_count": top1_faithful_count,
        "top1_faithful_rate": top1_rate,
        "pairwise_auc": auc,
        "by_mutation_type": by_mutation_type,
        "verdict": verdict,
    }


def verdict_from_metrics(pairwise_auc_value: float, top1_faithful_rate: float) -> str:
    if pairwise_auc_value >= 0.75 and top1_faithful_rate >= 0.67:
        return "continue"
    if pairwise_auc_value < 0.60 or top1_faithful_rate < 0.50:
        return "kill-core-method"
    return "inconclusive"


def _by_case(rows: list[CandidateDistance]) -> dict[str, list[CandidateDistance]]:
    grouped: dict[str, list[CandidateDistance]] = defaultdict(list)
    for row in rows:
        grouped[row.case_id].append(row)
    return dict(grouped)


def _mean(values: Iterable[float]) -> float:
    collected = list(values)
    return sum(collected) / len(collected) if collected else 0.0
