from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase20_paper_tables as phase20


class Phase20PaperTablesTest(unittest.TestCase):
    def test_ghidra_risk_rows_keeps_large_rows_only(self) -> None:
        rows = phase20.ghidra_risk_rows(
            {
                "risk_breakdown": {
                    "phase6r_ghidra_full": [
                        {"risk_family": "tiny", "paired_case_count": 2, "auc": 0.0},
                        {"risk_family": "large", "paired_case_count": 3, "auc": 1.0},
                    ]
                }
            }
        )
        self.assertEqual([row["risk_family"] for row in rows], ["large"])

    def test_markdown_renders_main_table(self) -> None:
        text = phase20.main_result_markdown(
            [
                {
                    "label": "Ghidra",
                    "candidates": 1,
                    "paired_cases": 1,
                    "fixture_auc": 0.5,
                    "static_auc": 0.8,
                    "final_auc": 1.0,
                    "detection": 1.0,
                    "avg_inputs": 7.0,
                    "missed": 0,
                }
            ]
        )
        self.assertIn("Ghidra", text)
        self.assertIn("1.0000", text)


if __name__ == "__main__":
    unittest.main()
