from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import run_phase7_benchmark_feasibility as feasibility


class Phase7BenchmarkFeasibilityTest(unittest.TestCase):
    def test_find_local_matches_detects_benchmark_named_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "external" / "CodeFuse-DeBench").mkdir(parents=True)
            spec = feasibility.benchmark_specs()[3]
            matches = feasibility.find_local_matches(root, spec)
            self.assertEqual(matches, [str(root / "external" / "CodeFuse-DeBench")])

    def test_classify_verdict_requires_available_benchmark(self) -> None:
        rows = [
            {
                "benchmark_name": "DecompileBench",
                "available": False,
                "format_identified": False,
            }
        ]
        self.assertEqual(
            feasibility.classify_verdict(rows),
            "blocked-needs-benchmark-download-approval",
        )
        rows[0]["available"] = True
        self.assertEqual(
            feasibility.classify_verdict(rows),
            "blocked-benchmark-format-unknown",
        )
        rows[0]["format_identified"] = True
        self.assertEqual(
            feasibility.classify_verdict(rows),
            "ready-public-benchmark-import",
        )

    def test_build_row_records_recommended_next_action(self) -> None:
        spec = feasibility.BenchmarkSpec(
            name="DemoBench",
            aliases=("demo-bench",),
            expected_input_format="source/binary pairs",
            source_known_possible=True,
            compile_harness_needed=True,
            license_or_repro_note="check license",
        )
        row = feasibility.build_row(Path("/tmp/repo"), spec, [])
        self.assertFalse(row["available"])
        self.assertIn("download", row["recommended_next_action"])

    def test_tree_names_identify_codefuse_partial_clone(self) -> None:
        self.assertTrue(
            feasibility.tree_names_identify_benchmark(
                ["README.md", "src", "decompiled", "binbench-x64.yaml"]
            )
        )
        self.assertTrue(
            feasibility.tree_names_identify_benchmark(["src", "evaluator"])
        )
        self.assertFalse(
            feasibility.tree_names_identify_benchmark(["docs", "scripts", "notes.txt"])
        )


if __name__ == "__main__":
    unittest.main()
