from __future__ import annotations

import unittest
from pathlib import Path

from analysis.decompile_faithfulness import fixtures
from analysis.decompile_faithfulness import run_phase6_decompiler_like_candidates as phase6


class Phase6DecompilerLikeTest(unittest.TestCase):
    def test_insert_noop_guard_preserves_function_name_and_adds_guard(self) -> None:
        source = """int f(int x) {
    return x + 1;
}
"""
        rewritten = phase6.insert_noop_guard(
            source,
            {"function_name": "f", "signature": "int f(int x)"},
        )
        self.assertIn("volatile int phase6_decompiler_like_guard = 0;", rewritten)
        self.assertIn("int f(int x)", rewritten)
        self.assertIn("return x + 1;", rewritten)

    def test_build_phase6_candidates_includes_control_rewrite_and_ifchains(self) -> None:
        case = fixtures.FunctionCase(
            case_id="toy",
            function_name="toy",
            function_source="int toy(int x) {\n    return x + 1;\n}\n",
            tests=(fixtures.FunctionTest((1,), 2), fixtures.FunctionTest((2,), 3)),
        )
        entry = {
            "signature": "int toy(int x)",
            "function_name": "toy",
            "fixtures": [
                {"args": [1], "expected": 2},
                {"args": [2], "expected": 3},
            ],
        }
        candidates = phase6.build_phase6_candidates(
            case=case,
            entry=entry,
            opt_level="O0",
            assembly_context_path="analysis_outputs/toy.objdump.txt",
        )
        roles = {candidate.expected_role for candidate in candidates}
        self.assertIn("behavior_preserving_original", roles)
        self.assertIn("behavior_preserving_rewrite", roles)
        self.assertIn("fixture_passing_semantic_drift", roles)
        self.assertGreaterEqual(len(candidates), 4)

    def test_phase6_verdict_requires_v3_to_beat_static_and_fixture(self) -> None:
        summary = {
            "gate": {
                "source_function_scale_gate": True,
                "compile_pass_scale_gate": True,
                "paired_function_gate": True,
                "v3_beats_fixture_gate": True,
                "v3_beats_static_gate": True,
                "behavior_preserving_fp_gate": True,
            },
            "real_decompiler_output_available": False,
        }
        self.assertEqual(
            phase6.phase6_verdict(summary),
            "pass-phase6-decompiler-like-ccfa-proxy",
        )
        summary["gate"]["v3_beats_static_gate"] = False
        self.assertEqual(
            phase6.phase6_verdict(summary),
            "method-negative-realistic-candidates",
        )

    def test_gate_decision_keeps_proxy_below_real_decompiler_output(self) -> None:
        summary = {
            "verdict": "pass-phase6-decompiler-like-ccfa-proxy",
            "real_decompiler_output_available": False,
            "tool_probe_verdict": "ready-for-assembly-context-decompiler-like-generation",
            "gate": {
                "source_function_scale_gate": True,
                "compile_pass_scale_gate": True,
                "paired_function_gate": True,
                "v3_beats_fixture_gate": True,
                "v3_beats_static_gate": True,
                "behavior_preserving_fp_gate": True,
            },
        }
        gate = phase6.build_gate_decision(summary)
        self.assertEqual(gate["decision"], "needs-decompiler-dependency-plan")

    def test_probe_tools_reports_objdump_and_gcc_when_available(self) -> None:
        probe = phase6.probe_tools()
        self.assertIn(probe["verdict"], {
            "ready-for-real-decompiler-output-import",
            "ready-for-assembly-context-decompiler-like-generation",
            "needs-decompiler-dependency-plan",
        })
        self.assertIn("objdump", probe["availability"])
        self.assertIn("gcc", probe["availability"])


if __name__ == "__main__":
    unittest.main()
