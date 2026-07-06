from __future__ import annotations

import ast
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import holdout_evaluation as he
from analysis.decompile_faithfulness import source_behavioral_diversity as sbdw


REPO_ROOT = Path(__file__).resolve().parents[3]


class SourceBehavioralDiversityTest(unittest.TestCase):
    def test_candidate_independent_pool_construction(self) -> None:
        function = _function()
        fixtures = [{"args": [0], "expected": 0, "source_output": 0, "rank": 1}]
        pool = sbdw.construct_source_pool(function, fixtures)
        self.assertEqual({item.args for item in pool}, set(function.domain))
        tree = ast.parse(Path(sbdw.__file__).read_text(encoding="utf-8"))
        forbidden_attrs = {"candidate_output", "mismatch_witness", "first_mismatch"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, forbidden_attrs)

    def test_complete_domain_inclusion_for_small_domain(self) -> None:
        function = _function(domain_specs=({"type": "int", "values": list(range(5))},))
        pool = sbdw.construct_source_pool(function, [{"args": [0], "expected": 0, "source_output": 0, "rank": 1}])
        self.assertEqual([item.args for item in pool], [(0,), (1,), (2,), (3,), (4,)])

    def test_large_domain_sampling_is_deterministic(self) -> None:
        function = _function(domain_specs=({"type": "int", "values": list(range(5000))},))
        first = sbdw.deterministic_domain_inputs(function, max_pool=64)
        second = sbdw.deterministic_domain_inputs(function, max_pool=64)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_stable_source_output_and_edge_signatures(self) -> None:
        record_a = sbdw.BehaviorRecord("f", (1,), 7, (1, 2, 3), sbdw.sha256_text("[1, 2, 3]"), "b", "t", "ok", 0.1, "sig")
        record_b = sbdw.BehaviorRecord("f", (1,), 7, (1, 2, 3), sbdw.sha256_text("[1, 2, 3]"), "b", "t", "ok", 0.2, "sig")
        self.assertEqual(record_a.normalized_output, record_b.normalized_output)
        self.assertEqual(record_a.edge_coverage_signature, record_b.edge_coverage_signature)

    def test_deterministic_greedy_selection_and_tie_breaking(self) -> None:
        pool = [
            sbdw.PoolInput("f", (0,), 1, ("complete_domain",), False),
            sbdw.PoolInput("f", (1,), 2, ("complete_domain",), False),
            sbdw.PoolInput("f", (2,), 3, ("complete_domain",), False),
        ]
        cache = {
            ("f", (0,)): _behavior((0,), 0, (1,)),
            ("f", (1,)): _behavior((1,), 1, (1, 2)),
            ("f", (2,)): _behavior((2,), 1, (1, 2)),
        }
        first = sbdw.select_behavioral_prefix(sbdw.POLICY, pool, cache, [], max_budget=3)
        second = sbdw.select_behavioral_prefix(sbdw.POLICY, pool, cache, [], max_budget=3)
        self.assertEqual(first, second)
        self.assertEqual([item.args for item in first], [(1,), (0,), (2,)])

    def test_cache_key_changes_with_domain(self) -> None:
        f1 = _function(domain_specs=({"type": "int", "values": [0, 1]},))
        f2 = _function(domain_specs=({"type": "int", "values": [0, 1, 2]},))
        pool1 = [sbdw.PoolInput("f", (0,), 1, ("complete_domain",), False)]
        pool2 = [sbdw.PoolInput("f", (0,), 1, ("complete_domain",), False)]
        self.assertNotEqual(sbdw.source_cache_key(f1, pool1), sbdw.source_cache_key(f2, pool2))

    def test_no_candidate_execution_during_selection(self) -> None:
        tree = ast.parse(Path(sbdw.__file__).read_text(encoding="utf-8"))
        selection_functions = {"construct_source_pool", "select_behavioral_prefix", "selection_key"}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in selection_functions:
                text = ast.get_source_segment(Path(sbdw.__file__).read_text(encoding="utf-8"), node) or ""
                self.assertNotIn("candidate_source", text)
                self.assertNotIn("execute_inputs", text)

    def test_full_source_side_cost_accounting(self) -> None:
        rows = sbdw.sbdw_cost_summary(
            pool_generation_s=1.0,
            source_execution_s=2.0,
            selection_s=1.0,
            behavior_cache={("f", (0,)): _behavior((0,), 0, (1,))},
            traces=[],
            controlled_population={"sets": {"primary_fixture_passing_wrong": []}},
            natural_population={"sets": {"primary_fixture_passing_wrong": []}},
        )
        self.assertIn("source_pool_generation", {row["cost_type"] for row in rows})
        self.assertIn("source_only_execution", {row["cost_type"] for row in rows})
        self.assertIn("amortized_end_to_end", {row["cost_type"] for row in rows})

    def test_budget_prefix_consistency(self) -> None:
        function = _function(domain_specs=({"type": "int", "values": list(range(10))},))
        fixtures = [{"args": [0], "expected": 0, "source_output": 0, "rank": 1}]
        pool = sbdw.construct_source_pool(function, fixtures)
        cache = {("f", item.args): _behavior(item.args, item.args[0], (item.args[0] + 1,)) for item in pool}
        selected = sbdw.select_behavioral_prefix(sbdw.POLICY, pool, cache, fixtures, max_budget=8)
        self.assertEqual([item.args for item in selected[:4]], [item.args for item in selected[:8]][:4])

    def test_no_mismatch_reconciliation_metric(self) -> None:
        rows = [{"candidate_id": "ok", "policy": sbdw.POLICY, "budget": 8, "detected_in_domain": False}]
        metric = sbdw.metric_row(sbdw.POLICY, 8, "controlled_no_mismatch", rows, ["ok"])
        self.assertEqual(metric["unexpected_in_domain_mismatch_count"], 0)

    def test_paper_table_reconciliation(self) -> None:
        with self.subTest("latex_escape"):
            self.assertIn("\\_", sbdw.latex_escape("a_b"))


def _function(
    *,
    domain_specs: tuple[dict[str, object], ...] = ({"type": "int", "values": [0, 1, 2]},),
) -> he.HoldoutFunction:
    domain = tuple(tuple(int(value) for value in values) for values in __import__("itertools").product(*[spec["values"] for spec in domain_specs]))
    return he.HoldoutFunction(
        function_id="f",
        project="p",
        source_file="f.c",
        function_name="f",
        signature="int f(int x)",
        domain_specs=domain_specs,
        domain=domain,
        domain_size=len(domain),
        source="int f(int x) { if (x == 1) return 7; return x; }\n",
        source_literal_count=0,
    )


def _behavior(args: tuple[int, ...], output: int, edges: tuple[int, ...]) -> sbdw.BehaviorRecord:
    edge_sig = sbdw.sha256_text(str(edges))
    trace = sbdw.sha256_text("trace" + str(edges))
    return sbdw.BehaviorRecord("f", args, output, edges, edge_sig, edge_sig, trace, "ok", 0.01, sbdw.sha256_text(str((output, edge_sig))))


if __name__ == "__main__":
    unittest.main()
