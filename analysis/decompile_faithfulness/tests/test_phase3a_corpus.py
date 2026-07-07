from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from analysis.decompile_faithfulness import phase3a_corpus as corpus


class Phase3aCorpusTest(unittest.TestCase):
    def test_project_pool_disjoint_from_prior_phases(self) -> None:
        names = {name for name, _url in corpus.PRIMARY_PROJECT_POOL + corpus.FALLBACK_PROJECT_POOL}
        self.assertFalse(names & corpus.FORBIDDEN_PRIOR_PROJECTS)

    def test_vendored_prior_phase_source_paths_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            allowed = root / "src" / "scalar.c"
            blocked_musl = root / "deps" / "musl_inet_pton.c"
            blocked_mbedtls = root / "src" / "bufferevent_mbedtls.c"
            for path in [allowed, blocked_musl, blocked_mbedtls]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("int f(int x) { return x; }\n", encoding="utf-8")
            self.assertEqual([path.relative_to(root).as_posix() for path in corpus.iter_source_files(root)], ["src/scalar.c"])

    def test_exact_domain_construction(self) -> None:
        self.assertEqual(corpus.type_domain("char", 1, {}), tuple(range(0, 128)))
        self.assertEqual(corpus.type_domain("int", 1, {}), tuple(range(-64, 64)))
        self.assertEqual(corpus.type_domain("unsigned int", 1, {}), tuple(range(0, 128)))
        self.assertEqual(corpus.type_domain("int", 2, {}), tuple(range(-32, 32)))
        self.assertEqual(corpus.type_domain("uint8_t", 3, {}), tuple(range(0, 16)))

    def test_complete_domain_size_cap(self) -> None:
        params = [corpus.Param("int", "a"), corpus.Param("unsigned int", "b"), corpus.Param("char", "c")]
        values = corpus.declared_domain_values(params, {})
        self.assertIsNotNone(values)
        size = 1
        for domain in values or ():
            size *= len(domain)
        self.assertEqual(size, 4096)
        self.assertLessEqual(size, corpus.MAX_DOMAIN_SIZE)

    def test_source_sanitizer_validation_excludes_ub(self) -> None:
        fn = _function(source="int f(int x) { return x / (x - x); }", domain_values=((0,),), domain=((0,),))
        with tempfile.TemporaryDirectory() as tmp:
            result = corpus.validate_source_function(fn, Path(tmp), Path(tmp) / "log.jsonl")
        self.assertFalse(result["ok"])
        self.assertIn("runtime_failure", result["reason"])

    def test_deterministic_function_extraction_and_features(self) -> None:
        source = "static int f(int x, int y) { if (x < y) return x & y; return x | y; }"
        first = corpus.extract_functions(source)
        second = corpus.extract_functions(source)
        self.assertEqual(first, second)
        parsed = first[0]
        signature = corpus.parse_signature(parsed["header"])
        self.assertIsNotNone(signature)
        _return_type, params = signature or ("", [])
        features = corpus.structural_features(parsed["source"], params)
        self.assertEqual(features["argument_count"], 2)
        self.assertGreaterEqual(features["branch_count"], 1)
        self.assertGreaterEqual(features["bitwise_operation_count"], 2)
        self.assertTrue(features["multiple_interacting_arguments"])

    def test_deterministic_sampling_and_project_cap(self) -> None:
        funcs = [
            _function(project=f"p{project}", function_id=f"p{project}::f{index:02d}", project_order=project)
            for project in range(12)
            for index in range(12)
        ]
        first = corpus.select_functions(funcs, 120)
        second = corpus.select_functions(list(reversed(funcs)), 120)
        self.assertEqual([item.function_id for item in first], [item.function_id for item in second])
        counts = {}
        for item in first:
            counts[item.project] = counts.get(item.project, 0) + 1
        self.assertTrue(all(count <= corpus.PROJECT_CAP for count in counts.values()))
        self.assertEqual(len(first), 120)

    def test_feasibility_amendment_logic(self) -> None:
        funcs = [
            _function(project=f"p{project}", function_id=f"p{project}::f{index:02d}", project_order=project)
            for project in range(12)
            for index in range(7)
        ]
        gate = corpus.corpus_gate(funcs)
        self.assertEqual(gate["status"], "reduced_feasible")
        self.assertEqual(gate["target_selected_functions"], 84)

    def test_feasibility_amendment_is_not_rewritten_after_commit(self) -> None:
        funcs = [_function()]
        gate = {
            "sampling_capacity_under_project_cap": 80,
            "eligible_project_count": 12,
            "target_selected_functions": 80,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "amendment.md"
            path.write_text("already committed\n", encoding="utf-8")
            corpus.write_feasibility_amendment(path, gate, funcs)
            self.assertEqual(path.read_text(encoding="utf-8"), "already committed\n")

    def test_existing_checkout_without_head_is_not_acquired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project"
            (path / ".git").mkdir(parents=True)
            with mock.patch.object(corpus, "git_at", return_value=""):
                result = corpus.acquire_project(Path(tmp), path, "https://example.invalid/repo.git", Path(tmp) / "log.jsonl")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "existing_checkout_without_resolved_head")

    def test_fixture_generation_source_agnostic_and_reproducible(self) -> None:
        left = _function(source="int f(int x) { return x + 'A'; }")
        right = _function(source="int f(int x) { return x + 'Z'; }")

        def fake_execute(function, args_list, output_dir, command_log):
            return {"ok": True, "outputs": [sum(args) for args in args_list]}

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(corpus, "execute_function", side_effect=fake_execute):
                first = corpus.generate_fixtures([left], Path(tmp), Path(tmp) / "log.jsonl")
                second = corpus.generate_fixtures([right], Path(tmp), Path(tmp) / "log.jsonl")
                third = corpus.generate_fixtures([left], Path(tmp), Path(tmp) / "log.jsonl")
        self.assertEqual([row["args"] for row in first], [row["args"] for row in second])
        self.assertEqual(first, third)

    def test_seal_reproducibility_helpers(self) -> None:
        payload = {"b": 2, "a": [1, 2, 3]}
        self.assertEqual(corpus.sha256_text(corpus.canonical_json(payload)), corpus.sha256_text(corpus.canonical_json(payload)))

    def test_guard_preventing_auditor_imports_or_execution(self) -> None:
        self.assertEqual(corpus.guard_against_auditor_imports(), {"imports_ok": True, "calls_ok": True})
        tree = ast.parse(Path(corpus.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, corpus.FORBIDDEN_AUDITOR_IMPORTS)


def _function(
    *,
    project: str = "p0",
    project_order: int = 0,
    function_id: str = "p0::f",
    source: str = "int f(int x) { return x; }",
    domain_values: tuple[tuple[int, ...], ...] = (tuple(range(8)),),
    domain: tuple[tuple[int, ...], ...] = tuple((x,) for x in range(8)),
) -> corpus.FunctionRecord:
    params = (corpus.Param("int", "x"),)
    features = corpus.structural_features(source, list(params))
    return corpus.FunctionRecord(
        project=project,
        pool="primary",
        project_order=project_order,
        source_file="f.c",
        function_name="f",
        ordinal=1,
        return_type="int",
        params=params,
        source=source,
        support_source="",
        source_sha256=corpus.sha256_text(source),
        source_file_sha256=corpus.sha256_text(source),
        function_id=function_id,
        domain_values=domain_values,
        domain=domain,
        domain_size=len(domain),
        features=features,
    )


if __name__ == "__main__":
    unittest.main()
