from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LocalizationRecord:
    case_id: str
    candidate_id: str
    expected_slot: str
    ranked_slots: list[str]


def component_to_slot_votes(components: dict[str, float]) -> dict[str, float]:
    votes = {
        "branch_predicate": 0.0,
        "control_structure": 0.0,
        "constant": 0.0,
        "api_call": 0.0,
        "return_value": 0.0,
    }

    branch_score = components.get("branch_count_abs", 0.0)
    opcode_score = components.get("opcode_l1", 0.0)
    signature_score = components.get("instruction_signature_l1", 0.0)

    votes["branch_predicate"] += 3.0 * branch_score
    votes["control_structure"] += 1.5 * branch_score
    votes["control_structure"] += 0.25 * components.get("instruction_count_abs", 0.0)
    votes["control_structure"] += 0.25 * opcode_score
    votes["branch_predicate"] += 0.75 * opcode_score
    votes["constant"] += 2.0 * components.get("immediate_symmetric_diff", 0.0)
    votes["api_call"] += 3.0 * components.get("call_count_abs", 0.0)
    votes["return_value"] += 3.0 * components.get("ret_count_abs", 0.0)
    if opcode_score == 0.0:
        votes["return_value"] += 0.5 * signature_score
    else:
        votes["branch_predicate"] += 0.25 * signature_score
    return votes


def rank_slots(votes: dict[str, float]) -> list[str]:
    return [
        slot
        for slot, _score in sorted(
            votes.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def hit_at_k(ranked_slots: list[str], expected_slot: str, k: int) -> bool:
    return expected_slot in ranked_slots[:k]


def compute_localization_summary(records: list[LocalizationRecord]) -> dict[str, object]:
    record_count = len(records)
    return {
        "record_count": record_count,
        "hit_at_1": _hit_rate(records, 1),
        "hit_at_2": _hit_rate(records, 2),
        "hit_at_3": _hit_rate(records, 3),
        "continue_to_sketch_localization": _hit_rate(records, 3) >= 0.70,
        "do_not_claim_localization": _hit_rate(records, 3) < 0.50,
    }


def _hit_rate(records: list[LocalizationRecord], k: int) -> float:
    if not records:
        return 0.0
    hits = sum(1 for record in records if hit_at_k(record.ranked_slots, record.expected_slot, k))
    return hits / len(records)
