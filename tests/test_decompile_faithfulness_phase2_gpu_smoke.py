from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import fixtures
from analysis.decompile_faithfulness import run_phase2_gpu_smoke as gpu_smoke


class DecompileFaithfulnessPhase2GpuSmokeTest(unittest.TestCase):
    def test_extracts_expected_function_from_fence(self) -> None:
        case = fixtures.case_by_id("signum")
        raw = """Here is the function:
```c
int signum(int x) {
    return (x > 0) - (x < 0);
}
```
"""

        result = gpu_smoke.extract_expected_c_function(raw, case)

        self.assertEqual(result.status, "parsed_function")
        self.assertIn("int signum(int x)", result.function_source)
        self.assertNotIn("```", result.function_source)

    def test_rejects_main_and_preprocessor(self) -> None:
        case = fixtures.case_by_id("absdiff")

        with_main = gpu_smoke.extract_expected_c_function(
            "int main(void) { return 0; }\nint absdiff(int a, int b) { return a - b; }",
            case,
        )
        with_include = gpu_smoke.extract_expected_c_function(
            "#include <stdlib.h>\nint absdiff(int a, int b) { return a > b ? a - b : b - a; }",
            case,
        )

        self.assertEqual(with_main.status, "parse_failed")
        self.assertEqual(with_include.status, "parse_failed")

    def test_rejects_ellipsis_and_library_calls(self) -> None:
        case = fixtures.case_by_id("absdiff")

        ellipsis = gpu_smoke.extract_expected_c_function(
            "int absdiff(int a, int b) { ... }",
            case,
        )
        library_call = gpu_smoke.extract_expected_c_function(
            "int absdiff(int a, int b) { return abs(a - b); }",
            case,
        )

        self.assertEqual(ellipsis.status, "parse_failed")
        self.assertEqual(library_call.status, "parse_failed")

    def test_build_generation_requests_are_stable(self) -> None:
        requests = gpu_smoke.build_generation_requests(
            ["absdiff"],
            ["source_rewrite", "signature_spec"],
            candidates_per_prompt=1,
        )

        self.assertEqual(
            [request.candidate_id for request in requests],
            [
                "phase2_gpu_absdiff_source_rewrite_00",
                "phase2_gpu_absdiff_signature_spec_00",
            ],
        )
        self.assertIn("int absdiff(int a, int b)", requests[0].prompt)

    def test_strict_paired_prompts_include_signature_and_intent(self) -> None:
        case = fixtures.case_by_id("max3")

        rewrite = gpu_smoke.build_prompt(case, "strict_rewrite")
        bug = gpu_smoke.build_prompt(case, "strict_bug")

        self.assertIn("int max3(int a, int b, int c)", rewrite)
        self.assertIn("equivalent implementation", rewrite)
        self.assertIn("subtle semantic bug", bug)
        self.assertIn("Forbidden:", bug)

    def test_summarize_no_candidates_fails_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td)
            summary = gpu_smoke.summarize_gpu_smoke(
                output_dir=output_dir,
                output_json=output_dir / "summary.json",
                output_md=output_dir / "summary.md",
                output_zh=output_dir / "summary.zh.md",
                manifest_path=output_dir / "manifest.json",
                generation_path=output_dir / "generation_metadata.jsonl",
                records_path=output_dir / "records.jsonl",
                generation_records=[
                    {
                        "case_id": "signum",
                        "candidate_id": "phase2_gpu_signum_source_rewrite_00",
                        "cleaning_status": "parse_failed",
                    }
                ],
                records=[],
                model_info={"model_loaded": True, "device": "cuda:2"},
            )

        self.assertFalse(summary["gpu_smoke_gate_passed"])
        self.assertEqual(summary["parsed_count"], 0)
        self.assertFalse(summary["paired_generation_gate_passed"])


if __name__ == "__main__":
    unittest.main()
