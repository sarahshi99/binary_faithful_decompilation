from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase6r_radare2_smoke as smoke


class Phase6RRadare2SmokeTest(unittest.TestCase):
    def test_parse_nm_symbol_address(self) -> None:
        nm_stdout = """
0000000000401126 T GCD
0000000000401150 T main
"""
        self.assertEqual(smoke.parse_nm_symbol_address(nm_stdout, "GCD"), "0x0000000000401126")
        self.assertIsNone(smoke.parse_nm_symbol_address(nm_stdout, "missing"))

    def test_is_pdc_c_like_accepts_radare2_pseudo_c_shape(self) -> None:
        text = """function fcn.GCD () {
    loc_0x112d:
       eax = dword [var_4h]
       return
}
"""
        self.assertTrue(smoke.is_pdc_c_like(text))
        self.assertFalse(smoke.is_pdc_c_like("Cannot find function at 0x0"))

    def test_smoke_verdict_for_importability(self) -> None:
        summary = {
            "binary_count": 76,
            "compile_pass_count": 76,
            "symbol_found_count": 76,
            "pdc_c_like_count": 76,
        }
        self.assertEqual(
            smoke.smoke_verdict(summary),
            "pass-phase6r-radare2-importability-smoke",
        )
        summary["pdc_c_like_count"] = 1
        self.assertEqual(
            smoke.smoke_verdict(summary),
            "partial-phase6r-radare2-importability-smoke",
        )


if __name__ == "__main__":
    unittest.main()
