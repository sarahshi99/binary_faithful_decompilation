from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import phase3a_candidates as candidates
from analysis.decompile_faithfulness import phase3a_corpus as corpus


class Phase3aCandidatesTest(unittest.TestCase):
    def test_candidate_matrix_reconciliation(self) -> None:
        self.assertEqual(len(candidates.PRODUCERS), 4)
        self.assertEqual(set(candidates.BUILD_VIEWS), {"gcc_O0", "clang_O2"})
        self.assertEqual(80 * len(candidates.PRODUCERS) * len(candidates.BUILD_VIEWS), 640)

    def test_producer_version_pinning(self) -> None:
        self.assertEqual(candidates.producer_version("ghidra", {"version": "12.1.2"}), "12.1.2")
        self.assertEqual(candidates.producer_version("angr", {"angr_version": "9.2.102"}), "9.2.102")
        self.assertIn("llm4decompile-22b-v2", candidates.producer_version("llm4decompile", {}))
        self.assertEqual(candidates.producer_version("mycodex_api", {"returned_model": "gpt-5.5"}), "gpt-5.5")

    def test_neural_and_api_prompts_do_not_leak_source_fixture_or_witness(self) -> None:
        function = _function(source="int f(int x) { return x + 12345; }")
        with tempfile.TemporaryDirectory() as tmp:
            disassembly = Path(tmp) / "d.s"
            disassembly.write_text("0000 <f>:\n  add $0x1,%eax\n", encoding="utf-8")
            artifact = candidates.BuildArtifact(
                function_id=function.function_id,
                build_view="gcc_O0",
                ok=True,
                source_path=Path(tmp) / "wrapper.c",
                binary_path=Path(tmp) / "f.exe",
                compiler_command=["gcc"],
                compile_log_path=Path(tmp) / "compile.json",
                symbol_metadata_path=Path(tmp) / "symbols.json",
                disassembly_path=disassembly,
                binary_hash="abc",
            )
            llm_prompt = candidates.llm_prompt_payload(function, artifact)["prompt"]
            api_prompt = candidates.api_prompt_payload(function, artifact)["prompt"]
        for prompt in [llm_prompt, api_prompt]:
            self.assertIn("Required signature: int f(int x)", prompt)
            self.assertIn("Disassembly:", prompt)
            self.assertNotIn("12345", prompt)
            self.assertNotIn("fixture", prompt.lower())
            self.assertNotIn("witness", prompt.lower())
            self.assertNotIn("source_output", prompt)

    def test_deterministic_normalization_and_no_execution_feedback_repair(self) -> None:
        function = _function()
        raw = "```c\nlong decomp(int y) { if (y) return y + 1; return 0; }\n```"
        first = candidates.normalize_candidate(raw, function)
        second = candidates.normalize_candidate(raw, function)
        self.assertEqual(first, second)
        self.assertEqual(first["parse_status"], "parsed_function")
        self.assertIn("int phase3a_candidate(int y)", first["normalized_source"])
        log = first["transform_log"]
        self.assertFalse(log["execution_feedback_repair_used"])
        self.assertFalse(log["source_aware_constant_or_branch_repair_used"])
        self.assertFalse(log["consulted_fixtures_or_labels"])

    def test_candidate_seal_reproducibility_helpers(self) -> None:
        payload = {"b": [2, 1], "a": "x"}
        left = candidates.sha256_text(corpus.canonical_json(payload))
        right = candidates.sha256_text(corpus.canonical_json(payload))
        self.assertEqual(left, right)

    def test_fixture_pass_reconstruction_and_descriptor_calculation(self) -> None:
        function = _function(source="int f(int x) { if (x < 3) return x; return x + 1; }")
        row = {
            "candidate_id": "c0",
            "producer": "ghidra",
            "build_view": "gcc_O0",
            "transformation_log_path": "",
        }
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "log.json"
            log.write_text('{"allowed_operations":["a","b"]}\n', encoding="utf-8")
            row["transformation_log_path"] = str(log)
            label = {
                "domain_size": 8,
                "mismatch_count": 2,
                "mismatch_density": 0.25,
                "first_mismatch": {"domain_index": 3, "args": [3]},
                "mismatch_domain_indices": [3, 4],
            }
            replay = {"fixture_domain_indices": [0, 7]}
            desc = candidates.build_descriptor(row, function, label, replay)
        self.assertEqual(desc["connected_mismatch_intervals_1d"], 1)
        self.assertEqual(desc["fixture_distance"], 3)
        self.assertEqual(desc["compile_normalization_extent"], "2")

    def test_taxonomy_and_census_gate_reconciliation(self) -> None:
        descriptors = []
        for i in range(25):
            descriptors.append(
                {
                    "candidate_id": f"c{i}",
                    "selected_function_id": f"f{i % 15}",
                    "project": f"p{i % 8}",
                    "producer": ["ghidra", "angr", "mycodex_api"][i % 3],
                    "primary_taxonomy_tag": ["condition-boundary error", "arithmetic error", "signedness or width error", "unknown/mixed"][i % 4],
                    "mismatch_density": 0.05 if i < 10 else 0.2,
                    "argument_count": 2,
                    "loop_count": 0,
                    "lookup_table_access": 0,
                }
            )
        gate = candidates.census_gate(descriptors)
        self.assertEqual(gate["minimum_gate_status"], "passed")
        self.assertGreaterEqual(gate["low_density_count"], 10)

    def test_guard_preventing_auditor_imports_or_execution(self) -> None:
        self.assertEqual(candidates.guard_against_auditor_imports(), {"imports_ok": True, "calls_ok": True})
        tree = ast.parse(Path(candidates.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, candidates.FORBIDDEN_AUDITOR_IMPORTS)


def _function(*, source: str = "int f(int x) { return x; }") -> corpus.FunctionRecord:
    params = (corpus.Param("int", "x"),)
    return corpus.FunctionRecord(
        project="p",
        pool="primary",
        project_order=1,
        source_file="f.c",
        function_name="f",
        ordinal=1,
        return_type="int",
        params=params,
        source=source,
        support_source="",
        source_sha256=corpus.sha256_text(source),
        source_file_sha256=corpus.sha256_text(source),
        function_id="p::f",
        domain_values=(tuple(range(8)),),
        domain=tuple((x,) for x in range(8)),
        domain_size=8,
        features=corpus.structural_features(source, list(params)),
    )


if __name__ == "__main__":
    unittest.main()
