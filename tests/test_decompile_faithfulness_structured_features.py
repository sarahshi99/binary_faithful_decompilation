from __future__ import annotations

import unittest
from pathlib import Path

from analysis.decompile_faithfulness import structured_features as sf


class DecompileFaithfulnessStructuredFeatureTest(unittest.TestCase):
    def test_parse_objdump_instructions_keeps_address_opcode_operands_and_target(self) -> None:
        text = """
0000000000000000 <signum>:
   0:   83 7d fc 00             cmpl   $0x0,-0x4(%rbp)
   4:   7d 07                   jge    d <signum+0xd>
   6:   b8 ff ff ff ff          mov    $0xffffffff,%eax
   b:   eb 10                   jmp    1d <signum+0x1d>
   d:   b8 00 00 00 00          mov    $0x0,%eax
  12:   c3                      ret
"""

        instructions = sf.parse_objdump_instructions(text)

        self.assertEqual(instructions[0].address, 0)
        self.assertEqual(instructions[0].opcode, "cmpl")
        self.assertEqual(instructions[0].operands, "$0x0,-0x4(%rbp)")
        self.assertEqual(instructions[1].opcode, "jge")
        self.assertEqual(instructions[1].target, 0xD)
        self.assertEqual(instructions[-1].opcode, "ret")

    def test_build_basic_blocks_splits_on_branch_targets_and_fallthrough(self) -> None:
        instructions = sf.parse_objdump_instructions(
            """
   0:   83 7d fc 00             cmpl   $0x0,-0x4(%rbp)
   4:   7d 07                   jge    d <f+0xd>
   6:   b8 ff ff ff ff          mov    $0xffffffff,%eax
   b:   c3                      ret
   d:   b8 00 00 00 00          mov    $0x0,%eax
  12:   c3                      ret
"""
        )

        blocks = sf.build_basic_blocks(instructions)

        self.assertEqual([block.start_address for block in blocks], [0x0, 0x6, 0xD])
        self.assertEqual(blocks[0].terminal_opcode, "jge")
        self.assertEqual(blocks[0].successors, (0xD, 0x6))
        self.assertEqual(blocks[1].terminal_opcode, "ret")
        self.assertEqual(blocks[2].terminal_opcode, "ret")

    def test_features_capture_signum_like_branch_return_bindings(self) -> None:
        instructions = sf.parse_objdump_instructions(
            """
   0:   83 7d fc 00             cmpl   $0x0,-0x4(%rbp)
   4:   7d 07                   jge    d <signum+0xd>
   6:   b8 ff ff ff ff          mov    $0xffffffff,%eax
   b:   c3                      ret
   d:   83 7d fc 00             cmpl   $0x0,-0x4(%rbp)
  11:   7e 07                   jle    1a <signum+0x1a>
  13:   b8 01 00 00 00          mov    $0x1,%eax
  18:   c3                      ret
  1a:   b8 00 00 00 00          mov    $0x0,%eax
  1f:   c3                      ret
"""
        )

        vector = sf.features_from_instructions(instructions, object_path=Path("signum.o"))

        self.assertGreaterEqual(vector.block_count, 5)
        self.assertIn("jge->target_return:0|fallthrough_return:-1", vector.branch_return_binding_counts)
        self.assertIn("jle->target_return:0|fallthrough_return:1", vector.branch_return_binding_counts)
        self.assertIn("cmp:0|jge->target_return:0|fallthrough_return:-1", vector.compare_branch_return_counts)

    def test_structured_distance_detects_reversed_return_bindings(self) -> None:
        faithful = sf.features_from_instructions(
            sf.parse_objdump_instructions(
                """
   0:   83 7d fc 00             cmpl   $0x0,-0x4(%rbp)
   4:   7d 07                   jge    d <signum+0xd>
   6:   b8 ff ff ff ff          mov    $0xffffffff,%eax
   b:   c3                      ret
   d:   b8 01 00 00 00          mov    $0x1,%eax
  12:   c3                      ret
"""
            ),
            object_path=Path("faithful.o"),
        )
        reversed_returns = sf.features_from_instructions(
            sf.parse_objdump_instructions(
                """
   0:   83 7d fc 00             cmpl   $0x0,-0x4(%rbp)
   4:   7d 07                   jge    d <signum+0xd>
   6:   b8 01 00 00 00          mov    $0x1,%eax
   b:   c3                      ret
   d:   b8 ff ff ff ff          mov    $0xffffffff,%eax
  12:   c3                      ret
"""
            ),
            object_path=Path("reversed.o"),
        )

        distance = sf.structured_feature_distance(faithful, reversed_returns)

        self.assertEqual(distance["basic_block_shape_l1"], 0.0)
        self.assertGreater(distance["branch_return_binding_l1"], 0.0)
        self.assertGreater(distance["compare_branch_return_l1"], 0.0)
        self.assertGreater(distance["structured_binding_total"], 0.0)

    def test_independent_instruction_reordering_does_not_force_structured_binding_distance(self) -> None:
        left = sf.features_from_instructions(
            sf.parse_objdump_instructions(
                """
   0:   b8 01 00 00 00          mov    $0x1,%eax
   5:   ba 02 00 00 00          mov    $0x2,%edx
   a:   c3                      ret
"""
            ),
            object_path=Path("left.o"),
        )
        right = sf.features_from_instructions(
            sf.parse_objdump_instructions(
                """
   0:   ba 02 00 00 00          mov    $0x2,%edx
   5:   b8 01 00 00 00          mov    $0x1,%eax
   a:   c3                      ret
"""
            ),
            object_path=Path("right.o"),
        )

        distance = sf.structured_feature_distance(left, right)

        self.assertEqual(distance["branch_return_binding_l1"], 0.0)
        self.assertEqual(distance["compare_branch_return_l1"], 0.0)
        self.assertEqual(distance["structured_binding_total"], 0.0)


if __name__ == "__main__":
    unittest.main()
