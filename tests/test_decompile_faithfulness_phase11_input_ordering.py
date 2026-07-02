from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import dynamic_trace
from analysis.decompile_faithfulness import run_phase11_input_ordering as phase11


class Phase11InputOrderingTest(unittest.TestCase):
    def test_fixture_neighbors_prioritize_non_fixture_points(self) -> None:
        entry = get_point_key_entry()
        inputs = phase11.fixture_neighbor_inputs(entry)
        fixture_args = {tuple(item["args"]) for item in entry["fixtures"]}
        self.assertGreaterEqual(len(inputs), 8)
        self.assertTrue(all(trace_input.args not in fixture_args for trace_input in inputs[:8]))
        self.assertTrue(
            any(original_get_point_key(item.args) != fixture_ifchain_get_point_key(item.args) for item in inputs[:8])
        )

    def test_fixture_neighbor_order_exposes_fixture_ifchain_by_budget8(self) -> None:
        entry = get_point_key_entry()
        case = fake_case()
        inputs = phase11.build_ordered_inputs(entry, case, "fixture_neighbor_first", max_inputs=8)
        self.assertTrue(any(original_get_point_key(item.args) != fixture_ifchain_get_point_key(item.args) for item in inputs))

    def test_operator_char_class_exposes_precedence_fixture_ifchain_by_budget8(self) -> None:
        entry = precedence_entry()
        case = fake_case(function_source=precedence_source())
        inputs = phase11.build_ordered_inputs(entry, case, "operator_char_class_first", max_inputs=8)
        self.assertTrue(
            any(
                original_precedence(item.args) != fixture_ifchain_precedence(item.args)
                for item in inputs
            )
        )

    def test_source_literal_char_interleave_exposes_precedence_by_budget8(self) -> None:
        entry = precedence_entry()
        case = fake_case(function_source=precedence_source())
        inputs = phase11.build_ordered_inputs(entry, case, "source_literal_char_interleave", max_inputs=8)
        self.assertTrue(
            any(
                original_precedence(item.args) != fixture_ifchain_precedence(item.args)
                for item in inputs
            )
        )

    def test_source_literal_char_interleave_preserves_neighbor_when_no_literals(self) -> None:
        entry = operand_entry()
        case = fake_case(function_source=operand_numeric_ascii_source())
        interleaved = phase11.build_ordered_inputs(entry, case, "source_literal_char_interleave", max_inputs=8)
        baseline = phase11.build_ordered_inputs(entry, case, "fixture_neighbor_first", max_inputs=8)
        self.assertEqual([item.args for item in interleaved], [item.args for item in baseline])

    def test_source_char_literal_values(self) -> None:
        self.assertEqual(
            phase11.source_char_literal_values(precedence_source()),
            [36, 42, 47, 37, 43, 45],
        )
        self.assertEqual(phase11.source_char_literal_values(r"char c = '\n'; char d = '\x41';"), [10, 65])

    def test_dedupe_preserves_first_bucket(self) -> None:
        inputs = [
            dynamic_trace.TraceInput((1, 2), "first"),
            dynamic_trace.TraceInput((1, 2), "second"),
            dynamic_trace.TraceInput((2, 3), "third"),
        ]
        deduped = phase11.dedupe_inputs(inputs)
        self.assertEqual([item.args for item in deduped], [(1, 2), (2, 3)])
        self.assertEqual(deduped[0].bucket, "first")

    def test_phase11_verdicts(self) -> None:
        self.assertEqual(
            phase11.phase11_verdict(
                {
                    "budget8_auc_gate": True,
                    "budget8_detection_gate": True,
                    "budget16_auc_gate": False,
                    "budget16_detection_gate": False,
                }
            ),
            "pass-ghidra-budget8-input-ordering",
        )
        self.assertEqual(
            phase11.phase11_verdict(
                {
                    "budget8_auc_gate": False,
                    "budget8_detection_gate": False,
                    "budget16_auc_gate": True,
                    "budget16_detection_gate": True,
                }
            ),
            "pass-ghidra-adaptive-budget16",
        )
        self.assertEqual(
            phase11.phase11_verdict(
                {
                    "budget8_auc_gate": False,
                    "budget8_detection_gate": False,
                    "budget16_auc_gate": False,
                    "budget16_detection_gate": True,
                }
            ),
            "input-ordering-still-insufficient",
        )

    def test_best_strategy_prefers_complete_eval_before_auc(self) -> None:
        results = {
            "incomplete_high_auc": {
                "budget_metrics": {
                    "8": {
                        "complete_eval": False,
                        "mismatch_auc": 1.0,
                        "wrong_detection_rate": 1.0,
                        "avg_actual_inputs_per_candidate": 8.0,
                    }
                }
            },
            "complete_lower_auc": {
                "budget_metrics": {
                    "8": {
                        "complete_eval": True,
                        "mismatch_auc": 0.99,
                        "wrong_detection_rate": 0.97,
                        "avg_actual_inputs_per_candidate": 8.0,
                    }
                }
            },
        }
        self.assertEqual(
            phase11.best_strategy_for_budget(results, "8")["strategy_id"],
            "complete_lower_auc",
        )


def get_point_key_entry() -> dict[str, object]:
    return {
        "case_id": "ta_leetcode_get_point_key",
        "function_name": "getPointKey",
        "signature": "int getPointKey(int i, int j, int boardSize, int boardColSize)",
        "fixtures": [
            {"args": [0, 0, 3, 4], "expected": 0},
            {"args": [1, 2, 3, 4], "expected": 14},
            {"args": [2, 1, 5, 5], "expected": 51},
        ],
    }


def fake_case(function_source: str = "") -> object:
    return type(
        "FakeCase",
        (),
        {
            "tests": [],
            "case_id": "ta_leetcode_get_point_key",
            "function_source": function_source,
        },
    )()


def original_get_point_key(args: tuple[int, ...]) -> int:
    i, j, board_size, board_col_size = args
    return board_size * board_col_size * i + j


def fixture_ifchain_get_point_key(args: tuple[int, ...]) -> int:
    if args == (0, 0, 3, 4):
        return 0
    if args == (1, 2, 3, 4):
        return 14
    if args == (2, 1, 5, 5):
        return 51
    return 0


def precedence_entry() -> dict[str, object]:
    return {
        "case_id": "ta_infix_precedence_two",
        "function_name": "getPrecedence",
        "signature": "int getPrecedence (char op1, char op2)",
        "fixtures": [
            {"args": [42, 43], "expected": 1},
            {"args": [43, 42], "expected": 0},
            {"args": [36, 43], "expected": 1},
            {"args": [43, 36], "expected": 0},
        ],
    }


def precedence_source() -> str:
    return """int getPrecedence (char op1, char op2)
{
    if (op2 == '$') return 0;
    else if (op1 == '$') return 1;
    else if (op2 == '*' || op2 == '/' || op2 == '%') return 0;
    else if (op1 == '*' || op1 == '/' || op1 == '%') return 1;
    else if (op2 == '+' || op2 == '-') return 0;
    return 1;
}
"""


def operand_entry() -> dict[str, object]:
    return {
        "case_id": "ta_infix_is_operand",
        "function_name": "isOprnd",
        "signature": "int isOprnd(char ch)",
        "fixtures": [
            {"args": [65], "expected": 1},
            {"args": [122], "expected": 1},
            {"args": [48], "expected": 1},
            {"args": [43], "expected": 0},
        ],
    }


def operand_numeric_ascii_source() -> str:
    return """int isOprnd(char ch)
{
    if ((ch >= 65 && ch <= 90) || (ch >= 97 && ch <= 122) || (ch >= 48 && ch <= 57)) {
        return 1;
    }
    return 0;
}
"""


def original_precedence(args: tuple[int, ...]) -> int:
    op1, op2 = args
    if op2 == 36:
        return 0
    if op1 == 36:
        return 1
    if op2 in {42, 47, 37}:
        return 0
    if op1 in {42, 47, 37}:
        return 1
    if op2 in {43, 45}:
        return 0
    return 1


def fixture_ifchain_precedence(args: tuple[int, ...]) -> int:
    if args == (42, 43):
        return 1
    if args == (43, 42):
        return 0
    if args == (36, 43):
        return 1
    if args == (43, 36):
        return 0
    return 0


if __name__ == "__main__":
    unittest.main()
