from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase7_second_decompiler_decision as decision


class Phase7SecondDecompilerDecisionTest(unittest.TestCase):
    def test_second_decompiler_verdict_blocks_when_only_ghidra_and_radare2_exist(self) -> None:
        tools = [
            {
                "name": "Ghidra",
                "available": True,
                "compile_ready_c_candidate": False,
            },
            {
                "name": "radare2/r2 pdc",
                "available": True,
                "compile_ready_c_candidate": False,
            },
        ]
        self.assertEqual(
            decision.second_decompiler_verdict(tools),
            "blocked-awaiting-second-decompiler-approval",
        )

    def test_second_decompiler_verdict_passes_for_non_ghidra_compile_ready_tool(self) -> None:
        tools = [
            {
                "name": "Ghidra",
                "available": True,
                "compile_ready_c_candidate": False,
            },
            {
                "name": "RetDec",
                "available": True,
                "compile_ready_c_candidate": True,
            },
        ]
        self.assertEqual(decision.second_decompiler_verdict(tools), "ready-second-decompiler-run")

    def test_recommended_next_action_points_to_gpu_baseline_when_blocked(self) -> None:
        summary = {"verdict": "blocked-awaiting-second-decompiler-approval"}
        self.assertIn("GPU 2/3", decision.recommended_next_action(summary))

    def test_tool_row_records_reason(self) -> None:
        row = decision.tool_row(
            name="Demo",
            available=False,
            detected_path="",
            evidence_kind="candidate",
            compile_ready_c_candidate=False,
            reason="not installed",
        )
        self.assertEqual(row["reason"], "not installed")
        self.assertFalse(row["available"])


if __name__ == "__main__":
    unittest.main()
