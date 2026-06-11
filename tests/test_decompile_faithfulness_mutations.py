from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import fixtures, mutations


class DecompileFaithfulnessMutationTest(unittest.TestCase):
    def test_absdiff_predicate_mutations_are_labeled(self) -> None:
        case = fixtures.case_by_id("absdiff")
        muts = mutations.generate_rule_mutations(case)
        by_id = {mut.candidate_id: mut for mut in muts}
        self.assertIn("mut_predicate_gt_to_ge", by_id)
        self.assertEqual(by_id["mut_predicate_gt_to_ge"].mutation_type, "predicate")
        self.assertEqual(by_id["mut_predicate_gt_to_ge"].expected_slot, "branch_predicate")
        self.assertIn("a >= b", by_id["mut_predicate_gt_to_ge"].function_source)

    def test_clamp_constant_mutations_are_labeled(self) -> None:
        case = fixtures.case_by_id("clamp8")
        muts = mutations.generate_rule_mutations(case)
        by_id = {mut.candidate_id: mut for mut in muts}
        self.assertIn("mut_constant_255_to_256", by_id)
        self.assertEqual(by_id["mut_constant_255_to_256"].mutation_type, "constant")
        self.assertEqual(by_id["mut_constant_255_to_256"].expected_slot, "constant")
        self.assertIn("return 256;", by_id["mut_constant_255_to_256"].function_source)

    def test_count_bits8_loop_mutation_is_labeled(self) -> None:
        case = fixtures.case_by_id("count_bits8")
        muts = mutations.generate_rule_mutations(case)
        by_id = {mut.candidate_id: mut for mut in muts}
        self.assertIn("mut_predicate_ne_to_eq", by_id)
        self.assertEqual(by_id["mut_predicate_ne_to_eq"].expected_slot, "branch_predicate")
        self.assertIn("(x & (1 << i)) == 0", by_id["mut_predicate_ne_to_eq"].function_source)


if __name__ == "__main__":
    unittest.main()
