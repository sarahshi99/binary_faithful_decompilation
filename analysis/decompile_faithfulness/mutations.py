from __future__ import annotations

from dataclasses import dataclass

from analysis.decompile_faithfulness.fixtures import FunctionCase


@dataclass(frozen=True)
class MutationCandidate:
    candidate_id: str
    function_source: str
    mutation_type: str
    expected_slot: str
    description: str


def replace_once(source: str, old: str, new: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"expected one occurrence of {old!r}, found {count}")
    return source.replace(old, new, 1)


def generate_rule_mutations(case: FunctionCase) -> list[MutationCandidate]:
    if case.case_id == "absdiff":
        candidates = [
            _mutation(
                case,
                "mut_predicate_gt_to_ge",
                "a > b",
                "a >= b",
                "predicate",
                "branch_predicate",
                "Change strict greater-than to greater-or-equal.",
            ),
            _mutation(
                case,
                "mut_predicate_gt_to_lt",
                "a > b",
                "a < b",
                "predicate",
                "branch_predicate",
                "Invert the branch predicate direction.",
            ),
            _mutation(
                case,
                "mut_return_a_minus_b_to_b_minus_a",
                "return a - b;",
                "return b - a;",
                "return_value",
                "return_value",
                "Swap subtraction operands in one return.",
            ),
        ]
    elif case.case_id == "clamp8":
        candidates = [
            _mutation(
                case,
                "mut_predicate_lt_to_le",
                "x < 0",
                "x <= 0",
                "predicate",
                "branch_predicate",
                "Change lower-bound predicate strictness.",
            ),
            _mutation(
                case,
                "mut_predicate_gt_to_ge",
                "x > 255",
                "x >= 255",
                "predicate",
                "branch_predicate",
                "Change upper-bound predicate strictness.",
            ),
            _mutation(
                case,
                "mut_constant_255_to_256",
                "return 255;",
                "return 256;",
                "constant",
                "constant",
                "Change the saturation constant.",
            ),
        ]
    elif case.case_id == "count_bits8":
        candidates = [
            _mutation(
                case,
                "mut_predicate_ne_to_eq",
                "(x & (1 << i)) != 0",
                "(x & (1 << i)) == 0",
                "predicate",
                "branch_predicate",
                "Invert the bit-test predicate.",
            ),
            _mutation(
                case,
                "mut_loop_bound_8_to_9",
                "i < 8",
                "i <= 8",
                "loop_bound",
                "control_structure",
                "Run the loop for one additional bit position.",
            ),
        ]
    else:
        candidates = []
    return sorted(candidates, key=lambda candidate: candidate.candidate_id)


def _mutation(
    case: FunctionCase,
    candidate_id: str,
    old: str,
    new: str,
    mutation_type: str,
    expected_slot: str,
    description: str,
) -> MutationCandidate:
    return MutationCandidate(
        candidate_id=candidate_id,
        function_source=replace_once(case.function_source, old, new),
        mutation_type=mutation_type,
        expected_slot=expected_slot,
        description=description,
    )
