from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from analysis.decompile_faithfulness import holdout_acquisition as holdout


class HoldoutAcquisitionTest(unittest.TestCase):
    def test_exact_domain_construction_for_supported_types(self) -> None:
        self.assertEqual(holdout.declared_domain("char"), tuple(range(0, 128)))
        self.assertEqual(holdout.declared_domain("unsigned char"), tuple(range(0, 128)))
        self.assertEqual(holdout.declared_domain("bool"), (0, 1))
        self.assertEqual(holdout.declared_domain("int"), tuple(range(-32, 32)))
        self.assertEqual(holdout.declared_domain("unsigned long"), tuple(range(0, 64)))
        self.assertIsNone(holdout.declared_domain("float"))

    def test_complete_cartesian_enumeration(self) -> None:
        source = "int f(bool a, unsigned char b) { return a + b; }"
        parsed = holdout.extract_functions(source)[0]
        signature = holdout.parse_signature(parsed["header"])
        self.assertIsNotNone(signature)
        _return_type, params = signature
        domains = [holdout.declared_domain(param.type_text) for param in params]
        tuples = list(__import__("itertools").product(*domains))
        self.assertEqual(len(tuples), 256)
        self.assertEqual(tuples[0], (0, 0))
        self.assertEqual(tuples[-1], (1, 127))

    def test_source_domain_sanitizer_exclusion(self) -> None:
        fn = _function(
            source="int f(int x) { return x / (x - x); }",
            domain=((0,),),
        )
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            log = work / "log.jsonl"
            result = holdout.validate_source_function(fn, work, log)
        self.assertFalse(result["ok"])
        self.assertIn("runtime_failure", result["reason"])

    def test_source_agnostic_fixture_generation(self) -> None:
        left = _function(source="int f(int x) { return x + 'A'; }")
        right = _function(source="int f(int x) { return x + 'Z'; }")

        def fake_execute(function, args_list, output_dir, command_log, **_kwargs):
            return {"ok": True, "outputs": [sum(args) for args in args_list]}

        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            log = work / "log.jsonl"
            with mock.patch.object(holdout, "execute_function", side_effect=fake_execute):
                left_rows = holdout.generate_fixtures([left], work, log)
                right_rows = holdout.generate_fixtures([right], work, log)
        self.assertEqual([row["args"] for row in left_rows], [row["args"] for row in right_rows])

    def test_deterministic_function_sampling_and_project_cap(self) -> None:
        candidates = [
            _function(project=f"p{project}", function_id=f"p{project}::f{index:02d}")
            for project in range(8)
            for index in range(10)
        ]
        old_pool = holdout.PROJECT_POOL
        try:
            holdout.PROJECT_POOL = [(f"p{project}", "", "primary") for project in range(8)]
            first = holdout.deterministic_sample(candidates)
            second = holdout.deterministic_sample(candidates)
        finally:
            holdout.PROJECT_POOL = old_pool
        self.assertEqual([item.function_id for item in first], [item.function_id for item in second])
        counts = holdout.count_by(item.project for item in first)
        self.assertEqual(len(first), 48)
        self.assertTrue(all(count <= holdout.PROJECT_CAP for count in counts.values()))

    def test_candidate_stratum_separation(self) -> None:
        fn = _function()
        fixtures = [
            {"function_id": fn.function_id, "args": [0], "source_output": 0},
            {"function_id": fn.function_id, "args": [1], "source_output": 1},
            {"function_id": fn.function_id, "args": [2], "source_output": 2},
            {"function_id": fn.function_id, "args": [3], "source_output": 3},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            rows = holdout.generate_controlled_candidates([fn], fixtures, Path(tmp), Path(tmp) / "log.jsonl")
        self.assertTrue(rows)
        self.assertTrue(all(row["candidate_stratum"] == "controlled_stress" for row in rows))
        self.assertTrue(all(row["candidate_class"] == "controlled_stress_candidate" for row in rows))

    def test_compile_runtime_failures_map_to_non_evaluable(self) -> None:
        fn = _function()
        row = holdout.label_row(
            {"candidate_id": "c", "candidate_stratum": "natural_ghidra", "candidate_class": "non_evaluable_compile_failure"},
            fn,
            "non_evaluable",
            "compile_failure",
            [],
            0,
        )
        self.assertEqual(row["label"], "non_evaluable")
        self.assertEqual(row["total_mismatching_input_count"], 0)

    def test_exact_label_reproducibility(self) -> None:
        fn = _function(source="int f(int x) { return x; }", domain=((0,), (1,), (2,)))
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            candidate = work / "candidate.c"
            candidate.write_text("int f(int x) { return x + 1; }\n", encoding="utf-8")
            candidate_record = {
                "candidate_id": "c",
                "function_id": fn.function_id,
                "project": fn.project,
                "candidate_stratum": "controlled_stress",
                "candidate_class": "controlled_stress_candidate",
                "candidate_source_path": str(candidate),
            }
            labels = holdout.label_candidates([fn], [candidate_record], work, work / "log.jsonl")
        self.assertEqual(labels[0]["label"], "semantic_wrong")
        self.assertEqual(labels[0]["total_mismatching_input_count"], 3)
        self.assertEqual(labels[0]["first_mismatch"]["args"], [0])

    def test_seal_hash_reproducibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            holdout.write_json(path, {"b": 2, "a": 1})
            first = holdout.sha256_path(path)
            holdout.write_json(path, {"b": 2, "a": 1})
            second = holdout.sha256_path(path)
        self.assertEqual(first, second)

    def test_guard_against_final_method_probe_imports_or_calls(self) -> None:
        tree = ast.parse(Path(holdout.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "analysis.decompile_faithfulness.run_phase18_source_literal_char_policy",
            "analysis.decompile_faithfulness.run_phase11_input_ordering",
        }
        forbidden_calls = {
            "build_ordered_inputs",
            "source_literal_char_inputs",
            "fixture_neighbor_inputs",
            "interleave_inputs",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, forbidden_calls)
                if isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_calls)


def _function(
    *,
    project: str = "p0",
    function_id: str = "p0::f",
    source: str = "int f(int x) { return x; }",
    domain: tuple[tuple[int, ...], ...] = ((0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,)),
) -> holdout.FunctionCandidate:
    return holdout.FunctionCandidate(
        project=project,
        source_path="f.c",
        function_name="f",
        ordinal=1,
        return_type="int",
        params=(holdout.Param("int", "x"),),
        source=source,
        source_sha256=holdout.sha256_text(source),
        domain=domain,
        domain_size=len(domain),
        function_id=function_id,
    )


if __name__ == "__main__":
    unittest.main()
