from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import features, fixtures


class DecompileFaithfulnessFeatureTest(unittest.TestCase):
    def test_extract_features_from_original_object(self) -> None:
        case = fixtures.case_by_id("clamp8")
        with tempfile.TemporaryDirectory() as td:
            result = ccompile.compile_candidate(
                case,
                "original",
                case.function_source,
                Path(td),
                opt_level="O0",
            )
            vector = features.extract_binary_features(result.object_path)
        self.assertGreater(vector.instruction_count, 0)
        self.assertGreaterEqual(vector.branch_count, 1)
        self.assertIn("clamp8", vector.symbols)
        self.assertGreaterEqual(len(vector.opcode_counts), 1)

    def test_feature_distance_is_zero_for_same_object(self) -> None:
        case = fixtures.case_by_id("absdiff")
        with tempfile.TemporaryDirectory() as td:
            result = ccompile.compile_candidate(
                case,
                "original",
                case.function_source,
                Path(td),
                opt_level="O0",
            )
            left = features.extract_binary_features(result.object_path)
            right = features.extract_binary_features(result.object_path)
        distance = features.feature_distance(left, right)
        self.assertEqual(distance.total, 0.0)
        self.assertEqual(distance.components["opcode_l1"], 0.0)

    def test_feature_distance_detects_constant_change(self) -> None:
        case = fixtures.case_by_id("clamp8")
        wrong_source = case.function_source.replace("return 255;", "return 256;")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            original = ccompile.compile_candidate(
                case,
                "original",
                case.function_source,
                out,
                opt_level="O0",
            )
            wrong = ccompile.compile_candidate(
                case,
                "constant",
                wrong_source,
                out,
                opt_level="O0",
            )
            left = features.extract_binary_features(original.object_path)
            right = features.extract_binary_features(wrong.object_path)
        distance = features.feature_distance(left, right)
        self.assertGreater(distance.total, 0.0)
        self.assertGreaterEqual(distance.components["immediate_symmetric_diff"], 1.0)

    def test_feature_distance_detects_operand_order_return_change(self) -> None:
        case = fixtures.case_by_id("absdiff")
        wrong_source = case.function_source.replace("return a - b;", "return b - a;")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            original = ccompile.compile_candidate(
                case,
                "original",
                case.function_source,
                out,
                opt_level="O0",
            )
            wrong = ccompile.compile_candidate(
                case,
                "return_swap",
                wrong_source,
                out,
                opt_level="O0",
            )
            left = features.extract_binary_features(original.object_path)
            right = features.extract_binary_features(wrong.object_path)
        distance = features.feature_distance(left, right)
        self.assertGreater(distance.total, 0.0)
        self.assertGreater(distance.components["instruction_signature_l1"], 0.0)

    def test_feature_distance_detects_same_instruction_bag_order_change(self) -> None:
        case = fixtures.case_by_id("signum")
        wrong_source = """int signum(int x) {
    if (x < 0) {
        return 1;
    }
    if (x > 0) {
        return -1;
    }
    return 0;
}
"""
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            original = ccompile.compile_candidate(
                case,
                "original",
                case.function_source,
                out,
                opt_level="O0",
            )
            wrong = ccompile.compile_candidate(
                case,
                "reversed_signs",
                wrong_source,
                out,
                opt_level="O0",
            )
            left = features.extract_binary_features(original.object_path)
            right = features.extract_binary_features(wrong.object_path)
        distance = features.feature_distance(left, right)
        self.assertEqual(distance.components["instruction_signature_l1"], 0.0)
        self.assertGreater(distance.components["instruction_bigram_l1"], 0.0)
        self.assertGreater(distance.components["branch_return_immediate_pair_l1"], 0.0)


if __name__ == "__main__":
    unittest.main()
