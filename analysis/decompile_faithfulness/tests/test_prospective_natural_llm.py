from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import holdout_evaluation as he
from analysis.decompile_faithfulness import prospective_natural_llm as nllm
from analysis.decompile_faithfulness import strong_baselines_and_mechanism as sbm


REPO_ROOT = Path(__file__).resolve().parents[3]


class ProspectiveNaturalLlmTest(unittest.TestCase):
    def test_prompt_payload_has_no_forbidden_artifact_fields(self) -> None:
        prompt = nllm.render_prompt(
            prompt_family="P1",
            function_id="f",
            project="p",
            build_view="gcc_O0",
            architecture="x86_64",
            signature="int f(int x)",
            disassembly="0000 <f>:\n  retq",
            raw_ghidra="int f(int x) { return x; }",
        )
        payload = nllm.response_api_payload(prompt)
        payload["phase1h_metadata"] = {"candidate_id": "c"}
        self.assertTrue(nllm.prompt_leak_guard(payload)["ok"])
        text = json.dumps(payload)
        self.assertNotIn("original_source_function_path", text)
        self.assertNotIn("holdout_fixtures", text)
        self.assertNotIn("first_mismatch", text)
        self.assertNotIn("source_literal_char_interleave", text)

    def test_request_matrix_coverage_is_exact_for_sealed_views(self) -> None:
        requests = nllm.build_request_matrix(REPO_ROOT)
        self.assertEqual(len(requests), 42 * 2 * 2)
        self.assertEqual({request.prompt_family for request in requests}, {"P1", "P2"})
        self.assertEqual({request.build_view for request in requests}, {"gcc_O0", "clang_O2"})
        self.assertTrue(all(nllm.prompt_leak_guard(request.payload)["ok"] for request in requests))

    def test_deterministic_parsing_and_normalization(self) -> None:
        raw = """
```c
int guessed(int y) {
    if (y < 0) return 0;
    return y + 1;
}
```
"""
        first = nllm.process_model_response(raw, "int target(int x)")
        second = nllm.process_model_response(raw, "int target(int x)")
        self.assertEqual(first, second)
        self.assertEqual(first["parse_status"], "parsed_function")
        self.assertIn("int target(int x)", first["normalized_source"])
        self.assertIn("return x + 1", first["normalized_source"])

    def test_no_semantic_repair_in_transform_log_shape(self) -> None:
        processed = nllm.process_model_response("int f(int x) { return 7; }", "int f(int x)")
        self.assertIn("replace_declaration_with_required_signature", processed["operations"])
        self.assertNotIn("execute", " ".join(processed["operations"]))
        self.assertNotIn("repair", " ".join(processed["operations"]).lower())

    def test_candidate_seal_hash_is_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seal.json"
            payload = {"b": 2, "a": 1}
            nllm.write_json(path, payload)
            first = nllm.sha256_path(path)
            nllm.write_json(path, payload)
            second = nllm.sha256_path(path)
            self.assertEqual(first, second)

    def test_exact_domain_labeling_and_confirmation(self) -> None:
        function = _function(source="int f(int x) { return x; }\n")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_path = root / "candidate.c"
            candidate_path.write_text("int f(int x) { return x + 1; }\n", encoding="utf-8")
            rows = [{
                "candidate_id": "c",
                "function_id": "f",
                "project": "p",
                "candidate_stratum": "natural_llm",
                "candidate_class": "natural_llm_output",
                "build_view": "gcc_O0",
                "prompt_family": "P1",
                "compile_status": "compile_ready",
                "normalized_candidate_path": str(candidate_path),
            }]
            labels = nllm.label_candidates_exact({"f": function}, rows, root / "work")
        self.assertEqual(labels[0]["label"], "semantic_wrong")
        self.assertEqual(labels[0]["total_inputs_enumerated"], 3)
        self.assertEqual(labels[0]["total_mismatching_input_count"], 3)
        self.assertTrue(labels[0]["first_mismatch_confirmation"]["confirmed"])

    def test_fixture_pass_reconstruction_population(self) -> None:
        manifest = [_manifest("a", "semantic_wrong"), _manifest("b", "no_mismatch_under_exact_holdout_domain")]
        labels = [
            _label("a", "semantic_wrong", mismatches=1),
            _label("b", "no_mismatch_under_exact_holdout_domain", mismatches=0),
        ]
        replay = [{"candidate_id": "a", "fixture_pass": True}]
        pop = nllm.build_natural_population(manifest, labels, replay, {"f": _function()})
        self.assertEqual(pop["sets"]["primary_fixture_passing_wrong"], ["a"])
        self.assertEqual(pop["sets"]["no_mismatch_comparison"], ["b"])

    def test_macro_calculations(self) -> None:
        population = {
            "candidate_project": {"a": "p", "b": "p", "c": "q"},
            "candidate_function": {"a": "f1", "b": "f2", "c": "f2"},
        }
        rows = [
            {"candidate_id": "a", "detected_in_domain": True},
            {"candidate_id": "b", "detected_in_domain": False},
            {"candidate_id": "c", "detected_in_domain": True},
        ]
        self.assertAlmostEqual(nllm.project_macro_detection(rows, ["a", "b", "c"], population), 0.75)
        self.assertAlmostEqual(nllm.function_macro_detection(rows, ["a", "b", "c"], population), 0.75)

    def test_libfuzzer_harness_reuse_and_seed_list(self) -> None:
        self.assertIs(nllm.sbm.build_libfuzzer_harness, sbm.build_libfuzzer_harness)
        self.assertIs(nllm.lw.build_harnesses, __import__("analysis.decompile_faithfulness.libfuzzer_wallclock", fromlist=["build_harnesses"]).build_harnesses)
        self.assertEqual(len(sbm.RANDOM_SEEDS), 30)

    def test_final_method_guard_has_no_direct_scheduler_import(self) -> None:
        tree = ast.parse(Path(nllm.__file__).read_text(encoding="utf-8"))
        forbidden = {
            "analysis.decompile_faithfulness.run_phase11_input_ordering",
            "analysis.decompile_faithfulness.run_phase18_source_literal_char_policy",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden)

    def test_paper_table_reconciliation_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "paper/tables").mkdir(parents=True)
            manifest = [_manifest("a", "semantic_wrong")]
            labels = {"a": _label("a", "semantic_wrong", mismatches=1)}
            population = {
                "counts": {
                    "compile_ready": 1,
                    "semantic_wrong": 1,
                    "primary_fixture_passing_wrong": 1,
                    "low_density_fixture_passing_wrong": 1,
                    "no_mismatch": 0,
                    "non_evaluable": 0,
                },
            }
            policy = [{"policy": he.FINAL_POLICY, "budget": 8, "scope": "primary_fixture_passing_wrong", "detected": 1, "denominator": 1, "detection_rate": 1.0}]
            lib = [{"mode": "evaluation_count", "budget_or_time_limit": 8, "population": "primary_fixture_passing_wrong", "mean_detection": 0.0, "no_mismatch_false_alarms": 0}]
            nllm.write_tables(root, manifest, labels, [], policy, lib, [], population)
            self.assertTrue((root / "paper/tables/natural_llm_dataset.tex").exists())
            self.assertTrue((root / "paper/tables/natural_llm_main_results.tex").exists())


def _function(*, source: str = "int f(int x) { return x; }\n") -> he.HoldoutFunction:
    return he.HoldoutFunction(
        function_id="f",
        project="p",
        source_file="f.c",
        function_name="f",
        signature="int f(int x)",
        domain_specs=({"type": "int", "values": [-1, 0, 1]},),
        domain=((-1,), (0,), (1,)),
        domain_size=3,
        source=source,
        source_literal_count=0,
    )


def _manifest(candidate_id: str, label: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "function_id": "f",
        "project": "p",
        "function_name": "f",
        "signature": "int f(int x)",
        "build_view": "gcc_O0",
        "prompt_family": "P1",
        "compile_status": "compile_ready",
        "execution_status": "exact_domain_execution_complete",
        "label": label,
        "normalized_candidate_path": "candidate.c",
        "parse_status": "parsed_function",
        "candidate_status": "natural_llm_minimally_normalized",
    }


def _label(candidate_id: str, label: str, *, mismatches: int) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "label": label,
        "reason": "exact_domain_exhaustive_comparison",
        "total_mismatching_input_count": mismatches,
        "exact_domain_size": 3,
        "mismatch_density": mismatches / 3,
    }


if __name__ == "__main__":
    unittest.main()
