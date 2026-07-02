from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase5b_hard_candidates as hard


class Phase5BHardCandidatesTest(unittest.TestCase):
    def test_fixture_overfit_source_passes_listed_fixtures(self) -> None:
        source = hard.fixture_overfit_source(
            "int f(int a, int b)",
            [
                {"args": [1, 2], "expected": 3},
                {"args": [2, 3], "expected": 5},
            ],
            fallback=0,
            zero_guard=hard.zero_use_expression(["a", "b"]),
        )
        self.assertIn("if (a == 1 && b == 2)", source)
        self.assertIn("return 3 + 0 * ((a) + (b));", source)
        self.assertIn("return 0 + 0 * ((a) + (b));", source)

    def test_hard_trace_inputs_exclude_fixtures(self) -> None:
        entry = {
            "signature": "int f(int x)",
            "fixtures": [
                {"args": [1], "expected": 1},
                {"args": [3], "expected": 3},
            ],
        }
        inputs = hard.phase5b_hard_trace_inputs(entry, max_inputs=10)
        args = {trace_input.args for trace_input in inputs}
        self.assertNotIn((1,), args)
        self.assertNotIn((3,), args)
        self.assertTrue(args)

    def test_phase5b_verdict_requires_all_gates(self) -> None:
        summary = {
            "gate": {
                "scale_gate": True,
                "fixture_passing_wrong_gate": True,
                "v3_auc_gate": True,
                "sota_delta_gate": True,
                "fixture_collapse_gate": True,
            }
        }
        self.assertEqual(hard.phase5b_verdict(summary), "pass-phase5b-hard-candidate-sota-delta")


if __name__ == "__main__":
    unittest.main()
