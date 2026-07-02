from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import fixtures
from analysis.decompile_faithfulness import run_phase7_static_hard_candidates as static_hard


class Phase7StaticHardTest(unittest.TestCase):
    def test_generate_static_hard_mutations_changes_predicates_and_returns(self) -> None:
        source = """int f(int x) {
    if (x > 0) {
        return x * 2;
    }
    return x;
}
"""
        mutations = static_hard.generate_static_hard_mutations(source, max_mutations=4)
        self.assertGreaterEqual(len(mutations), 2)
        self.assertIn("x >= 0", mutations[0].function_source)
        self.assertTrue(all("int f(int x)" in item.function_source for item in mutations))

    def test_generate_static_hard_mutations_does_not_treat_shift_as_comparison(self) -> None:
        source = """int f(int x) {
    return x << 1;
}
"""
        mutations = static_hard.generate_static_hard_mutations(source, max_mutations=3)
        sources = "\n".join(item.function_source for item in mutations)
        self.assertNotIn("<=<", sources)
        self.assertIn("x >> 1", sources)

    def test_strip_c_comments_removes_line_and_block_comments(self) -> None:
        source = """int f(int x) {
    /* block */
    return x; // line
}
"""
        stripped = static_hard.strip_c_comments(source)
        self.assertNotIn("block", stripped)
        self.assertNotIn("line", stripped)

    def test_build_candidates_for_case_adds_control_and_static_hard_roles(self) -> None:
        case = fixtures.FunctionCase(
            case_id="toy",
            function_name="toy",
            function_source="int toy(int x) {\n    return x + 1;\n}\n",
            tests=(fixtures.FunctionTest((1,), 2),),
        )
        mutations = static_hard.generate_static_hard_mutations(case.function_source, max_mutations=2)
        candidates = static_hard.build_candidates_for_case(
            case=case,
            opt_level="O0",
            assembly_context_path="analysis_outputs/toy.objdump.txt",
            mutations=mutations,
        )
        roles = {candidate.expected_role for candidate in candidates}
        self.assertIn("behavior_preserving_original", roles)
        self.assertIn("static_hard_semantic_drift", roles)

    def test_static_hard_verdict_requires_delta_gate(self) -> None:
        summary = {
            "gate": {
                "source_function_scale_gate": True,
                "compile_pass_scale_gate": True,
                "paired_function_gate": True,
                "v3_beats_fixture_gate": True,
                "v3_beats_static_gate": True,
                "sota_delta_gate": True,
                "fixture_collapse_gate": True,
            }
        }
        self.assertEqual(
            static_hard.static_hard_verdict(summary),
            "pass-phase7-static-hard-sota-delta",
        )
        summary["gate"]["sota_delta_gate"] = False
        self.assertEqual(static_hard.static_hard_verdict(summary), "method-negative-static-hard")


if __name__ == "__main__":
    unittest.main()
