from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import fixtures
from analysis.decompile_faithfulness import run_phase7_llm_public_generation as llm_public


class Phase7LlmPublicGenerationTest(unittest.TestCase):
    def test_extract_public_c_function_accepts_non_int_scalar_return(self) -> None:
        entry = {"function_name": "process_char", "signature": "char process_char(char c)"}
        raw = """
```c
char process_char(char c) {
    if (c > 0) {
        return c + 1;
    }
    return c;
}
```
"""
        result = llm_public.extract_public_c_function(raw, entry)
        self.assertEqual(result.status, "parsed_function")
        self.assertIn("char process_char", result.function_source)

    def test_extract_public_c_function_accepts_bool_return(self) -> None:
        entry = {"function_name": "process_bool", "signature": "_Bool process_bool(int x)"}
        raw = "_Bool process_bool(int x) { return x != 0; }"
        result = llm_public.extract_public_c_function(raw, entry)
        self.assertEqual(result.status, "parsed_function")
        self.assertIn("_Bool process_bool", result.function_source)

    def test_extract_public_c_function_rejects_helpers(self) -> None:
        entry = {"function_name": "target", "signature": "int target(int x)"}
        raw = """
int helper(int x) { return x + 1; }
int target(int x) { return helper(x); }
"""
        result = llm_public.extract_public_c_function(raw, entry)
        self.assertNotEqual(result.status, "parsed_function")

    def test_public_function_definition_count_supports_unsigned_int(self) -> None:
        text = "unsigned int f(unsigned int x) { return x + 1; }"
        self.assertEqual(llm_public.public_function_definition_count(text), 1)

    def test_build_generation_requests_partitions_ids_with_shard(self) -> None:
        case = fixtures.FunctionCase(
            case_id="toy",
            function_name="toy",
            function_source="int toy(int x) { return x; }\n",
            tests=(),
        )
        requests = llm_public.build_generation_requests(
            cases={"toy": case},
            entries_by_case={
                "toy": {
                    "signature": "int toy(int x)",
                    "function_name": "toy",
                    "fixtures": [],
                    "risk_families": ["public_benchmark"],
                }
            },
            prompt_ids=["strict_rewrite", "strict_bug"],
            candidates_per_prompt=2,
            shard_index=1,
            run_tag="demo",
        )
        self.assertEqual(len(requests), 4)
        self.assertTrue(all(request.candidate_id.startswith("demo_s1_") for request in requests))

    def test_summary_verdict_requires_model_loaded(self) -> None:
        self.assertEqual(
            llm_public.summary_verdict(
                {
                    "model_info": {"model_loaded": False},
                    "parsed_count": 1,
                    "compile_pass_count": 1,
                    "candidate_manifest_verdict": "pass-phase7-llm-public-candidate-generation",
                }
            ),
            "gpu-model-not-loaded",
        )


if __name__ == "__main__":
    unittest.main()
