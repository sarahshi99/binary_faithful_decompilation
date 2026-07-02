from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase11_input_ordering as phase11
from analysis.decompile_faithfulness.fixtures import FunctionCase, FunctionTest


def _case(
    case_id: str,
    signature: str,
    source: str,
    fixtures: list[dict[str, object]],
) -> tuple[dict[str, object], FunctionCase]:
    tests = tuple(
        FunctionTest(tuple(int(value) for value in item["args"]), int(item["expected"]))
        for item in fixtures
    )
    entry: dict[str, object] = {
        "case_id": case_id,
        "function_name": "f",
        "signature": signature,
        "fixtures": fixtures,
    }
    return entry, FunctionCase(case_id, "f", source, tests)


def _prefix(entry: dict[str, object], case: FunctionCase, limit: int = 12) -> list[tuple[tuple[int, ...], str]]:
    return [
        (trace_input.args, trace_input.bucket)
        for trace_input in phase11.build_ordered_inputs(
            entry,
            case,
            "source_literal_char_interleave",
            max_inputs=limit,
        )
    ]


class ProbeOrderFreezeTest(unittest.TestCase):
    def test_single_integer_argument_prefix(self) -> None:
        entry, case = _case(
            "single_int",
            "int f(int x)",
            "int f(int x){ return x == 3 ? 1 : 0; }\n",
            [{"args": [2], "expected": 0}, {"args": [5], "expected": 0}],
        )
        self.assertEqual(
            _prefix(entry, case),
            [
                ((1,), "fixture_neighbor"),
                ((3,), "fixture_neighbor"),
                ((4,), "fixture_neighbor"),
                ((6,), "fixture_neighbor"),
            ],
        )

    def test_single_char_argument_prefix(self) -> None:
        entry, case = _case(
            "single_char",
            "int f(char c)",
            "int f(char c){ if (c == '+') return 1; if (c == '-') return 2; return 0; }\n",
            [{"args": [65], "expected": 0}, {"args": [90], "expected": 0}],
        )
        self.assertEqual(
            _prefix(entry, case),
            [
                ((1,), "fixture_neighbor"),
                ((43,), "source_literal_char"),
                ((64,), "fixture_neighbor"),
                ((45,), "source_literal_char"),
                ((66,), "fixture_neighbor"),
                ((73,), "fixture_neighbor"),
                ((74,), "fixture_neighbor"),
                ((75,), "fixture_neighbor"),
                ((89,), "fixture_neighbor"),
                ((91,), "fixture_neighbor"),
                ((2,), "phase5b_hard_probe"),
            ],
        )

    def test_multi_argument_integer_char_prefix(self) -> None:
        entry, case = _case(
            "multi_int_char",
            "int f(int x, char op)",
            "int f(int x, char op){ if (op == '*') return x * 2; if (op == '/') return x / 2; return x; }\n",
            [{"args": [2, 43], "expected": 2}, {"args": [3, 45], "expected": 3}],
        )
        self.assertEqual(
            _prefix(entry, case),
            [
                ((1, 43), "fixture_neighbor"),
                ((2, 42), "source_literal_char"),
                ((3, 43), "fixture_neighbor"),
                ((2, 47), "source_literal_char"),
                ((2, 1), "fixture_neighbor"),
                ((3, 42), "source_literal_char"),
                ((3, 47), "source_literal_char"),
                ((2, 44), "fixture_neighbor"),
                ((2, 64), "fixture_neighbor"),
                ((2, 65), "fixture_neighbor"),
                ((2, 66), "fixture_neighbor"),
                ((2, 73), "fixture_neighbor"),
            ],
        )

    def test_duplicate_producing_source_literal_prefix(self) -> None:
        entry, case = _case(
            "duplicate_literal",
            "int f(char c)",
            "int f(char c){ if (c == 'A') return 1; if (c == 'A') return 2; if (c == '\\n') return 3; return 0; }\n",
            [{"args": [66], "expected": 0}],
        )
        self.assertEqual(
            _prefix(entry, case),
            [
                ((1,), "fixture_neighbor"),
                ((65,), "source_literal_char"),
                ((64,), "fixture_neighbor"),
                ((10,), "source_literal_char"),
                ((67,), "fixture_neighbor"),
                ((73,), "fixture_neighbor"),
                ((74,), "fixture_neighbor"),
                ((75,), "fixture_neighbor"),
                ((90,), "fixture_neighbor"),
                ((2,), "phase5b_hard_probe"),
                ((43,), "phase5b_hard_probe"),
                ((45,), "phase5b_hard_probe"),
            ],
        )

    def test_empty_source_literal_queue_prefix(self) -> None:
        entry, case = _case(
            "empty_literal",
            "int f(char c)",
            "int f(char c){ return c; }\n",
            [{"args": [65], "expected": 65}, {"args": [66], "expected": 66}],
        )
        self.assertEqual(
            _prefix(entry, case),
            [
                ((1,), "fixture_neighbor"),
                ((64,), "fixture_neighbor"),
                ((73,), "fixture_neighbor"),
                ((74,), "fixture_neighbor"),
                ((75,), "fixture_neighbor"),
                ((90,), "fixture_neighbor"),
                ((67,), "fixture_neighbor"),
                ((2,), "phase5b_hard_probe"),
                ((43,), "phase5b_hard_probe"),
                ((45,), "phase5b_hard_probe"),
                ((97,), "phase5b_hard_probe"),
            ],
        )

    def test_one_exhausted_queue_during_interleaving_prefix(self) -> None:
        entry, case = _case(
            "exhausted",
            "int f(char c)",
            "int f(char c){ if (c == 'Q') return 1; return c; }\n",
            [{"args": [65], "expected": 65}, {"args": [66], "expected": 66}],
        )
        self.assertEqual(
            _prefix(entry, case),
            [
                ((1,), "fixture_neighbor"),
                ((81,), "source_literal_char"),
                ((64,), "fixture_neighbor"),
                ((73,), "fixture_neighbor"),
                ((74,), "fixture_neighbor"),
                ((75,), "fixture_neighbor"),
                ((90,), "fixture_neighbor"),
                ((67,), "fixture_neighbor"),
                ((2,), "phase5b_hard_probe"),
                ((43,), "phase5b_hard_probe"),
                ((45,), "phase5b_hard_probe"),
                ((97,), "phase5b_hard_probe"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
