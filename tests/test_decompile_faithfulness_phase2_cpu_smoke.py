from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import fixtures
from analysis.decompile_faithfulness import run_phase2_cpu_smoke as smoke


class DecompileFaithfulnessPhase2CpuSmokeTest(unittest.TestCase):
    def test_build_smoke_manifest_uses_unknown_labels(self) -> None:
        manifest = smoke.build_smoke_manifest(case_ids=["absdiff"])

        self.assertEqual(manifest[0]["case_id"], "absdiff")
        self.assertTrue(manifest[0]["candidates"])
        self.assertTrue(
            all(candidate["label"] == "unknown" for candidate in manifest[0]["candidates"])
        )

    def test_constant_return_candidate_references_parameters(self) -> None:
        source = smoke._constant_return_source(fixtures.case_by_id("gcd_positive"))

        self.assertIn("int gcd_positive(int a, int b)", source)
        self.assertIn("a + b", source)

    def test_run_smoke_labels_and_traces_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td) / "smoke"
            summary = smoke.run_smoke(
                output_dir=output_dir,
                output_json=output_dir / "summary.json",
                output_md=output_dir / "summary.md",
                output_zh=output_dir / "summary.zh.md",
                case_ids=["absdiff"],
            )

        self.assertTrue(summary["smoke_gate_passed"], summary)
        self.assertGreaterEqual(summary["compile_pass_count"], 3)
        self.assertGreaterEqual(summary["behavior_label_counts"]["faithful"], 1)
        self.assertGreaterEqual(summary["behavior_label_counts"]["plausible_wrong"], 1)
        self.assertGreaterEqual(summary["non_oracle_probe_count"], 1)
        self.assertFalse(summary["fixture_collapse"])


if __name__ == "__main__":
    unittest.main()
