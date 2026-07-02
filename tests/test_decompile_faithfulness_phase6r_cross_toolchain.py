from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import analyze_phase6r_cross_toolchain as cross_toolchain


class Phase6RCrossToolchainTest(unittest.TestCase):
    def test_ghidra_row_extracts_main_metrics(self) -> None:
        row = cross_toolchain.ghidra_row(
            {
                "toolchain_label": "gcc-11.4.0",
                "binary_compiler": "/usr/bin/gcc",
                "verdict": "pass-phase6r-real-decompiler-output-main-evidence",
                "candidate_count": 228,
                "compile_pass_count": 166,
                "paired_case_count": 26,
                "baseline_auc": {
                    "fixture_only": 0.5,
                    "static_structured_proxy": 0.82,
                    "v3_trace_total": 1.0,
                },
                "sota_delta_vs_best_baseline": 0.18,
                "failure_taxonomy": {"ghidra_or_normalization_failure": 62},
            },
            Path("result.json"),
        )
        self.assertEqual(row["toolchain_label"], "gcc-11.4.0")
        self.assertEqual(row["static_structured_auc"], 0.82)
        self.assertEqual(row["normalization_or_compile_fail_count"], 62)

    def test_cross_toolchain_verdict_requires_two_passing_ghidra_runs(self) -> None:
        summary = {
            "all_ghidra_main_gates_pass": True,
            "ghidra_run_count": 2,
            "radare2_run_count": 1,
        }
        self.assertEqual(
            cross_toolchain.cross_toolchain_verdict(summary),
            "pass-phase6r-cross-toolchain-ghidra-plus-radare2-importability",
        )
        summary["ghidra_run_count"] = 1
        self.assertEqual(
            cross_toolchain.cross_toolchain_verdict(summary),
            "partial-phase6r-cross-toolchain",
        )

    def test_write_markdown_handles_empty_radare2_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.md"
            cross_toolchain.write_markdown(
                path,
                {
                    "verdict": "partial-phase6r-cross-toolchain",
                    "ghidra_run_count": 1,
                    "radare2_run_count": 0,
                    "all_ghidra_main_gates_pass": True,
                    "min_ghidra_sota_delta": 0.1,
                    "external_sota_claim_ready": False,
                    "external_sota_claim_blocker": "needs baselines",
                    "ghidra_runs": [
                        {
                            "toolchain_label": "gcc-11.4.0",
                            "candidate_count": 228,
                            "compile_pass_count": 166,
                            "paired_case_count": 26,
                            "static_structured_auc": 0.82,
                            "v3_trace_total_auc": 1.0,
                            "sota_delta_vs_best_baseline": 0.18,
                            "normalization_or_compile_fail_count": 62,
                            "verdict": "pass-phase6r-real-decompiler-output-main-evidence",
                        }
                    ],
                    "radare2_runs": [],
                },
            )
            self.assertIn("Ghidra Main Evidence", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
