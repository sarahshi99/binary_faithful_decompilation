from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase3_gpu_generated_smoke as smoke
from analysis.decompile_faithfulness import fixtures


class DecompileFaithfulnessPhase3GpuGeneratedSmokeTest(unittest.TestCase):
    def test_build_prompt_uses_phase3_case_id_and_signature(self) -> None:
        case = fixtures.FunctionCase(
            case_id="sat_add8",
            function_name="sat_add8",
            function_source="int sat_add8(int a, int b) {\n    return a + b;\n}\n",
            tests=(),
        )

        prompt = smoke.build_prompt(case, "strict_bug")

        self.assertIn("int sat_add8(int a, int b) {", prompt)
        self.assertIn("Mishandle total == 256", prompt)

    def test_record_from_features_labels_fixture_behavior(self) -> None:
        request = smoke.GenerationRequest(
            case_id="sat_add8",
            prompt_id="strict_bug",
            generation_index=0,
            candidate_id="c1",
            prompt="",
        )

        record = smoke._record_from_features(
            request,
            "int sat_add8(int a, int b) { return 0; }",
            {
                "compiled": 1.0,
                "fixture_mismatch_rate": 1.0,
                "trace_mismatch_rate": 1.0,
                "trace_total": 1.0,
                "primary_exit_code": 0.0,
                "fixture_exit_code": 0.0,
            },
            {},
        )

        self.assertEqual(record["label"], "plausible_wrong")

    def test_verdict_reports_model_load_blocker(self) -> None:
        self.assertEqual(
            smoke._verdict(
                {
                    "model_info": {"model_loaded": False},
                    "parsed_count": 0,
                    "compile_pass_count": 0,
                    "paired_case_count": 0,
                    "fixture_collapse": False,
                }
            ),
            "gpu-model-not-loaded",
        )


if __name__ == "__main__":
    unittest.main()
