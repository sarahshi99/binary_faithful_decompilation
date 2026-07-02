from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu
from analysis.decompile_faithfulness import run_phase5_source_preflight as phase5_preflight


class Phase5GpuGeneratedFullTest(unittest.TestCase):
    def test_shard_entries_partitions_without_overlap(self) -> None:
        entries = [{"case_id": f"c{i}"} for i in range(7)]
        left = phase5_gpu.shard_entries(entries, shard_index=0, shard_count=2)
        right = phase5_gpu.shard_entries(entries, shard_index=1, shard_count=2)
        self.assertEqual(len(left) + len(right), len(entries))
        self.assertFalse({item["case_id"] for item in left} & {item["case_id"] for item in right})

    def test_build_prompt_uses_manifest_risk_and_signature(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            manifest = phase5_preflight.build_manifest(
                repo_root=repo_root,
                source_dir=Path(tmp) / "sources",
            )
            entry = manifest["functions"][0]
            case = phase5_gpu._case_from_manifest_entry(repo_root, entry)
            prompt = phase5_gpu.build_prompt(case, entry, "strict_bug")
        self.assertIn(entry["signature"] + " {", prompt)
        self.assertIn("risk areas", prompt)
        self.assertIn("exactly one subtle semantic bug", prompt)

    def test_candidate_manifest_verdict_requires_full_scale(self) -> None:
        self.assertEqual(
            phase5_gpu._candidate_manifest_verdict(compile_pass_count=99, paired_case_count=25),
            "needs-full-candidate-generation",
        )
        self.assertEqual(
            phase5_gpu._candidate_manifest_verdict(compile_pass_count=100, paired_case_count=20),
            "pass-phase5-full-candidate-generation",
        )

    def test_phase5_cleaning_drops_include_and_extracts_target_only(self) -> None:
        case = phase5_gpu.fixtures.FunctionCase(
            case_id="demo",
            function_name="target",
            function_source="int target(int x) { return x; }\n",
            tests=(),
        )
        raw = """
#include <stdio.h>
int helper(int x) { return x + 1; }
int target(int x) { return x - 1; }
"""
        result = phase5_gpu.extract_phase5_c_function(raw, case)
        self.assertEqual(result.status, "parsed_function")
        self.assertEqual(result.function_source, "int target(int x) { return x - 1; }\n")


if __name__ == "__main__":
    unittest.main()
