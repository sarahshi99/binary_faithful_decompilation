from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import run_phase3_readiness_preflight as preflight


class DecompileFaithfulnessPhase3ReadinessPreflightTest(unittest.TestCase):
    def test_source_scan_excludes_generated_outputs_and_docs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "real.c").write_text("int f(void) { return 1; }\n")
            (root / "analysis_outputs").mkdir()
            (root / "analysis_outputs" / "generated.c").write_text("int g(void) { return 2; }\n")
            (root / "docs").mkdir()
            (root / "docs" / "snippet.c").write_text("int h(void) { return 3; }\n")

            candidates = preflight.find_repository_source_candidates(root)

        self.assertEqual([candidate.path for candidate in candidates], ["src/real.c"])

    def test_method_gate_requires_v3_pass_and_no_blind_spots(self) -> None:
        self.assertTrue(
            preflight._method_gate_passed(
                {
                    "verdict": "pass-v3-boundary-trace",
                    "pairwise_auc": 1.0,
                    "fixture_collapse": False,
                    "trace_zero_blind_spot_wrong_count": 0,
                }
            )
        )
        self.assertFalse(
            preflight._method_gate_passed(
                {
                    "verdict": "pass-v3-boundary-trace",
                    "pairwise_auc": 1.0,
                    "fixture_collapse": False,
                    "trace_zero_blind_spot_wrong_count": 1,
                }
            )
        )

    def test_run_preflight_needs_manifest_after_method_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            phase2_json = root / "phase2_v3.json"
            phase2_json.write_text(
                json.dumps(
                    {
                        "verdict": "pass-v3-boundary-trace",
                        "pairwise_auc": 1.0,
                        "fixture_collapse": False,
                        "trace_zero_blind_spot_wrong_count": 0,
                    }
                )
            )
            output_json = root / "out.json"
            output_zh = root / "out.md"

            summary = preflight.run_preflight(
                repo_root=root,
                phase2_v3_json=phase2_json,
                phase3_manifest=root / "missing_manifest.json",
                output_json=output_json,
                output_zh=output_zh,
            )

            self.assertEqual(summary["verdict"], "needs-phase3-source-manifest")
            self.assertTrue(output_json.exists())
            self.assertTrue(output_zh.exists())

    def test_run_preflight_accepts_ready_source_selection(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            phase2_json = root / "phase2_v3.json"
            phase2_json.write_text(
                json.dumps(
                    {
                        "verdict": "pass-v3-boundary-trace",
                        "pairwise_auc": 1.0,
                        "fixture_collapse": False,
                        "trace_zero_blind_spot_wrong_count": 0,
                    }
                )
            )
            source_pool = root / "source_pool.json"
            source_pool.write_text(
                json.dumps({"functions": [{"case_id": str(index)} for index in range(5)]})
            )
            source_selection = root / "source_selection.json"
            source_selection.write_text(
                json.dumps(
                    {
                        "verdict": "ready-for-combinatorial-phase3-cpu-audit",
                        "eligible_count": 5,
                        "subset_count": 1,
                    }
                )
            )

            summary = preflight.run_preflight(
                repo_root=root,
                phase2_v3_json=phase2_json,
                phase3_manifest=root / "missing_manifest.json",
                phase3_source_pool=source_pool,
                phase3_source_selection=source_selection,
                output_json=root / "out.json",
                output_zh=root / "out.md",
            )

        self.assertEqual(
            summary["verdict"],
            "ready-for-combinatorial-phase3-cpu-audit",
        )


if __name__ == "__main__":
    unittest.main()
